#!/usr/bin/env python3
"""Run local SDXL LoRA training from n2d LoRA manifests.

This is a thin, auditable wrapper around kohya-ss/sd-scripts. It keeps all
project outputs inside the n2d project root and updates train_job.json with the
exact command and result.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


DEFAULT_SDSCRIPTS_HOME = Path(os.environ.get("N2D_SDSCRIPTS_HOME", str(Path.home() / "sd-scripts")))
DEFAULT_ENV = os.environ.get("N2D_SDXL_CONDA_ENV", "sdxl-comfy")
DEFAULT_CHECKPOINT = Path(os.environ.get("N2D_SDXL_CHECKPOINT", str(Path.home() / "ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors")))
DEFAULT_TOKENIZER_CACHE = os.environ.get("N2D_SDXL_TOKENIZER_CACHE", "")
SDXL_TOKENIZER_IDS = (
    "openai/clip-vit-large-patch14",
    "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def slugify(text: str) -> str:
    import re

    text = text.strip()
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-_.")
    return text or "asset"


def resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def local_tokenizer_name(model_id: str) -> str:
    return model_id.replace("/", "_")


def tokenizer_ready(path: Path) -> bool:
    required = ("tokenizer_config.json", "special_tokens_map.json", "tokenizer.json", "merges.txt", "vocab.json")
    return all((path / name).exists() for name in required)


def hf_snapshot_for(model_id: str) -> Optional[Path]:
    hub_dir = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + model_id.replace("/", "--")) / "snapshots"
    if not hub_dir.is_dir():
        return None
    candidates = [p for p in hub_dir.iterdir() if p.is_dir() and tokenizer_ready(p)]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def ensure_tokenizer_cache(cache_dir: Path) -> Dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    copied: List[Dict[str, str]] = []
    missing: List[str] = []
    for model_id in SDXL_TOKENIZER_IDS:
        dest = cache_dir / local_tokenizer_name(model_id)
        if tokenizer_ready(dest):
            copied.append({"model_id": model_id, "path": str(dest), "status": "ready"})
            continue
        src = hf_snapshot_for(model_id)
        if src is None:
            missing.append(model_id)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, dirs_exist_ok=True, symlinks=False)
        copied.append({"model_id": model_id, "path": str(dest), "source": str(src), "status": "copied"})
    return {"cache_dir": str(cache_dir), "ready": not missing, "tokenizers": copied, "missing": missing}


def lora_dir(root: Path, character_id: str, form: str) -> Path:
    return root / "设定库" / "lora" / slugify(character_id) / slugify(form or "常态")


def load_job(root: Path, character_id: str, form: str) -> Dict[str, Any]:
    path = lora_dir(root, character_id, form) / "train_job.json"
    if not path.is_file():
        raise FileNotFoundError(f"train_job.json not found: {path}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"train_job.json is not an object: {path}")
    return data


def load_dataset(root: Path, job: Mapping[str, Any]) -> Dict[str, Any]:
    path = root / str(job.get("dataset_manifest", ""))
    if not path.is_file():
        raise FileNotFoundError(f"dataset manifest not found: {path}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"dataset manifest is not an object: {path}")
    summary = data.get("summary") if isinstance(data.get("summary"), Mapping) else {}
    if summary.get("warnings"):
        raise ValueError("dataset has warnings: " + ", ".join(str(x) for x in summary.get("warnings", [])))
    if not summary.get("ready_for_training"):
        raise ValueError("dataset is not ready_for_training")
    return data


def write_dataset_config(
    root: Path,
    out_dir: Path,
    dataset: Mapping[str, Any],
    *,
    repeats: int,
    batch_size: int,
    resolution: int,
    shuffle_caption: bool = True,
) -> Path:
    dataset_dir = root / str(dataset.get("dataset_dir", ""))
    if not dataset_dir.is_dir():
        raise FileNotFoundError(f"dataset dir not found: {dataset_dir}")
    config = out_dir / "sdxl_dataset_config.toml"
    shuffle_caption_toml = "true" if shuffle_caption else "false"
    text = f"""[general]
caption_extension = ".txt"
shuffle_caption = {shuffle_caption_toml}
keep_tokens = 1
enable_bucket = true
bucket_no_upscale = false
min_bucket_reso = 512
max_bucket_reso = 1024
bucket_reso_steps = 64

[[datasets]]
resolution = [{resolution}, {resolution}]
batch_size = {batch_size}
enable_bucket = true

  [[datasets.subsets]]
  image_dir = {json.dumps(str(dataset_dir.resolve()), ensure_ascii=False)}
  caption_extension = ".txt"
  num_repeats = {repeats}
  shuffle_caption = {shuffle_caption_toml}
  keep_tokens = 1
"""
    config.write_text(text, encoding="utf-8")
    return config


def build_command(
    *,
    env: str,
    sdscripts_home: Path,
    checkpoint: Path,
    dataset_config: Path,
    output_dir: Path,
    output_name: str,
    trigger: str,
    steps: int,
    rank: int,
    learning_rate: str,
    seed: int,
    tokenizer_cache_dir: Path,
    lowram: bool,
    unet_only: bool,
    cache_text_encoder_outputs: bool,
    shuffle_caption: bool,
) -> List[str]:
    script = sdscripts_home / "sdxl_train_network.py"
    if not script.is_file():
        raise FileNotFoundError(f"sdxl_train_network.py not found: {script}")
    if not checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint}")
    cmd = [
        "conda", "run", "-n", env,
        "accelerate", "launch",
        "--num_processes", "1",
        "--num_machines", "1",
        "--mixed_precision", "no",
        "--num_cpu_threads_per_process", "1",
        str(script),
        "--pretrained_model_name_or_path", str(checkpoint),
        "--dataset_config", str(dataset_config),
        "--output_dir", str(output_dir),
        "--output_name", output_name,
        "--save_model_as", "safetensors",
        "--save_precision", "fp16",
        "--network_module", "networks.lora",
        "--network_dim", str(rank),
        "--network_alpha", str(rank),
        "--learning_rate", str(learning_rate),
        "--unet_lr", str(learning_rate),
        "--text_encoder_lr", "5e-5", "5e-5",
        "--max_train_steps", str(steps),
        "--train_batch_size", "1",
        "--mixed_precision", "no",
        "--optimizer_type", "AdamW",
        "--lr_scheduler", "constant",
        "--gradient_checkpointing",
        "--cache_latents",
        "--cache_latents_to_disk",
        "--max_data_loader_n_workers", "0",
        "--seed", str(seed),
        "--caption_extension", ".txt",
        "--keep_tokens", "1",
        "--tokenizer_cache_dir", str(tokenizer_cache_dir),
        "--metadata_trigger_phrase", trigger,
        "--training_comment", f"n2d local SDXL LoRA training; trigger={trigger}",
    ]
    if shuffle_caption:
        cmd.append("--shuffle_caption")
    if lowram:
        cmd.append("--lowram")
    if unet_only:
        cmd.append("--network_train_unet_only")
    if cache_text_encoder_outputs:
        cmd.extend(["--cache_text_encoder_outputs", "--cache_text_encoder_outputs_to_disk"])
    return cmd


def update_job(root: Path, character_id: str, form: str, patch: Mapping[str, Any]) -> None:
    path = lora_dir(root, character_id, form) / "train_job.json"
    job = read_json(path)
    if not isinstance(job, dict):
        raise ValueError(f"train_job.json is not an object: {path}")
    job.update(patch)
    write_json(path, job)


def cmd_prepare(args: argparse.Namespace) -> int:
    root = resolve_path(args.project_root)
    job = load_job(root, args.character_id, args.form)
    dataset = load_dataset(root, job)
    out_dir = root / str(job.get("output_dir", ""))
    out_dir.mkdir(parents=True, exist_ok=True)
    shuffle_caption = not bool(args.cache_text_encoder_outputs)
    dataset_config = write_dataset_config(
        root,
        out_dir,
        dataset,
        repeats=args.repeats,
        batch_size=1,
        resolution=args.resolution,
        shuffle_caption=shuffle_caption,
    )
    tokenizer_cache = resolve_path(args.tokenizer_cache_dir) if args.tokenizer_cache_dir else root / "生产数据" / "local_sdxl_cache" / "tokenizers"
    tokenizer_status = ensure_tokenizer_cache(tokenizer_cache)
    if not tokenizer_status["ready"] and args.offline:
        raise FileNotFoundError("missing local SDXL tokenizers for offline training: " + ", ".join(tokenizer_status["missing"]))
    sdscripts_home = resolve_path(args.sdscripts_home)
    checkpoint = resolve_path(args.checkpoint)
    expected = Path(str(job.get("expected_model_path", "")))
    output_name = expected.stem if expected.name else f"{slugify(args.character_id)}_{slugify(args.form)}_v1"
    command = build_command(
        env=args.env,
        sdscripts_home=sdscripts_home,
        checkpoint=checkpoint,
        dataset_config=dataset_config.resolve(),
        output_dir=out_dir.resolve(),
        output_name=output_name if not args.suffix else f"{output_name}_{args.suffix}",
        trigger=str(job.get("trigger", "")),
        steps=args.steps or int((job.get("hyperparameters") or {}).get("steps") or 1000),
        rank=args.rank or int((job.get("hyperparameters") or {}).get("rank") or 8),
        learning_rate=args.learning_rate or str((job.get("hyperparameters") or {}).get("learning_rate") or "5e-4"),
        seed=args.seed,
        tokenizer_cache_dir=tokenizer_cache,
        lowram=bool(args.lowram),
        unet_only=bool(args.unet_only),
        cache_text_encoder_outputs=bool(args.cache_text_encoder_outputs),
        shuffle_caption=shuffle_caption,
    )
    train_dir = out_dir / "local_train"
    train_dir.mkdir(parents=True, exist_ok=True)
    command_path = train_dir / (f"train_command_{args.suffix}.sh" if args.suffix else "train_command.sh")
    command_path.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        + "# Audit command file. On macOS, executing conda from bash/zsh/Python wrappers can disable PyTorch MPS.\n"
        + "if [[ \"$(uname -s)\" == \"Darwin\" ]]; then\n"
        + "  echo '[error] macOS MPS-safe launch requires running the printed conda command directly from top-level zsh, not this script file.' >&2\n"
        + "  exit 64\n"
        + "fi\n"
        + "cd "
        + shlex.quote(str(sdscripts_home))
        + "\n"
        + " ".join(shlex.quote(x) for x in command)
        + "\n",
        encoding="utf-8",
    )
    command_path.chmod(0o755)
    update_job(
        root,
        args.character_id,
        args.form,
        {
            "local_training": {
                "prepared_at": now_iso(),
                "dataset_config": rel(root, dataset_config),
                "command_file": rel(root, command_path),
                "command": command,
                "checkpoint": str(checkpoint),
                "sdscripts_home": str(sdscripts_home),
                "conda_env": args.env,
                "steps": args.steps or int((job.get("hyperparameters") or {}).get("steps") or 1000),
                "rank": args.rank or int((job.get("hyperparameters") or {}).get("rank") or 8),
                "learning_rate": args.learning_rate or str((job.get("hyperparameters") or {}).get("learning_rate") or "5e-4"),
                "repeats": args.repeats,
                "resolution": args.resolution,
                "tokenizer_cache": tokenizer_status,
                "offline": bool(args.offline),
                "lowram": bool(args.lowram),
                "unet_only": bool(args.unet_only),
                "cache_text_encoder_outputs": bool(args.cache_text_encoder_outputs),
                "shuffle_caption": shuffle_caption,
                "caption_shuffle_disabled_for_text_encoder_cache": bool(args.cache_text_encoder_outputs and not shuffle_caption),
            }
        },
    )
    print(f"[ok] wrote dataset config: {dataset_config}")
    print(f"[ok] wrote command file: {command_path}")
    print(" ".join(shlex.quote(x) for x in command))
    return 0


def training_env(root: Path, *, offline: bool) -> Dict[str, str]:
    cache_root = root / "生产数据" / "local_sdxl_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    env = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HOME": str(cache_root / "hf"),
        "TRANSFORMERS_CACHE": str(cache_root / "transformers"),
        "TORCH_HOME": str(cache_root / "torch"),
        "XDG_CACHE_HOME": str(cache_root / "xdg"),
    }
    if offline:
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
    return env


def cmd_run(args: argparse.Namespace) -> int:
    if sys.platform == "darwin" and not getattr(args, "allow_nested_run", False):
        print(
            "[error] macOS MPS-safe launch requires `prepare` plus running the printed conda command directly from top-level zsh; "
            "`run` uses a Python subprocess and falls back to CPU on this host. Pass --allow-nested-run only for CPU diagnostics.",
            file=sys.stderr,
        )
        return 64
    root = resolve_path(args.project_root)
    suffix = args.suffix or ("smoke" if args.smoke else "")
    prep_args = argparse.Namespace(**vars(args))
    prep_args.steps = args.steps if args.steps is not None else (1 if args.smoke else None)
    prep_args.suffix = suffix
    cmd_prepare(prep_args)
    job = load_job(root, args.character_id, args.form)
    command = list(((job.get("local_training") or {}).get("command") or []))
    if not command:
        raise ValueError("local_training.command missing after prepare")
    out_dir = root / str(job.get("output_dir", ""))
    log_dir = out_dir / "local_train"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / (f"train_{suffix or 'final'}.log")
    started = now_iso()
    update_job(root, args.character_id, args.form, {"status": "running", "local_training_run": {"started_at": started, "log": rel(root, log_path), "smoke": bool(args.smoke)}})
    print(f"[run] log: {log_path}")
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(shlex.quote(x) for x in command) + "\n")
        log.flush()
        proc = subprocess.Popen(command, cwd=str(resolve_path(args.sdscripts_home)), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
            print(line, end="")
        rc = proc.wait()
    ended = now_iso()
    expected = Path(str(job.get("expected_model_path", "")))
    if suffix:
        expected = expected.with_name(f"{expected.stem}_{suffix}{expected.suffix}")
    model_path = root / expected
    update_job(
        root,
        args.character_id,
        args.form,
        {
            "status": "completed" if rc == 0 else "failed",
            "local_training_run": {
                "started_at": started,
                "ended_at": ended,
                "returncode": rc,
                "log": rel(root, log_path),
                "smoke": bool(args.smoke),
                "model_path": rel(root, model_path) if model_path.exists() else "",
            },
        },
    )
    if rc == 0:
        print(f"[ok] training completed: {model_path if model_path.exists() else '(model path not found; check log)'}")
    else:
        print(f"[error] training failed, log: {log_path}", file=sys.stderr)
    return rc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Prepare/run local SDXL LoRA training")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        s = sub.add_parser(name)
        s.add_argument("project_root")
        s.add_argument("--character-id", required=True)
        s.add_argument("--form", required=True)
        s.add_argument("--sdscripts-home", default=str(DEFAULT_SDSCRIPTS_HOME))
        s.add_argument("--env", default=DEFAULT_ENV)
        s.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
        s.add_argument("--tokenizer-cache-dir", default=DEFAULT_TOKENIZER_CACHE)
        s.add_argument("--offline", dest="offline", action="store_true", default=True)
        s.add_argument("--allow-network", dest="offline", action="store_false")
        s.add_argument("--lowram", dest="lowram", action="store_true", default=True)
        s.add_argument("--no-lowram", dest="lowram", action="store_false")
        s.add_argument("--unet-only", action="store_true")
        s.add_argument("--cache-text-encoder-outputs", action="store_true")
        s.add_argument("--steps", type=int, default=None)
        s.add_argument("--rank", type=int, default=None)
        s.add_argument("--learning-rate", default="")
        s.add_argument("--repeats", type=int, default=10)
        s.add_argument("--resolution", type=int, default=1024)
        s.add_argument("--seed", type=int, default=4242)
        s.add_argument("--suffix", default="")
        if name == "run":
            s.add_argument("--smoke", action="store_true")
            s.add_argument("--allow-nested-run", action="store_true")
            s.set_defaults(func=cmd_run)
        else:
            s.set_defaults(func=cmd_prepare)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
