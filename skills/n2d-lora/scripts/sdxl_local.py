#!/usr/bin/env python3
"""Local SDXL/ComfyUI sidechain utilities for n2d LoRA workflows.

This tool deliberately models SDXL as a sidechain for LoRA validation and
selected hero shots. It does not change the project's main image backend.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


KIND_PROFILE = "n2d_local_sdxl_profile"
KIND_WORKFLOW = "n2d_comfyui_sdxl_workflow"
KIND_EVENT = "n2d_production_event"
KIND_ROUTE = "n2d_lora_runtime_route"
DEFAULT_COMFY_HOME = Path(os.environ.get("N2D_COMFYUI_HOME", str(Path.home() / "ComfyUI")))
DEFAULT_ENV = os.environ.get("N2D_SDXL_CONDA_ENV", "sdxl-comfy")
DEFAULT_URL = os.environ.get("N2D_COMFYUI_URL", "http://127.0.0.1:8188")
DEFAULT_TRAIN_CMD = os.environ.get("N2D_LORA_TRAIN_CMD", "")


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-_.")
    return text or "asset"


def run_capture(cmd: List[str], timeout: int = 20) -> Dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}


def conda_env_exists(name: str) -> bool:
    result = run_capture(["conda", "env", "list"], timeout=20)
    if not result["ok"]:
        return False
    return any(line.split() and line.split()[0] == name for line in result["stdout"].splitlines())


def torch_probe(env: str) -> Dict[str, Any]:
    code = (
        "import json\n"
        "try:\n"
        " import torch\n"
        " mps_built = torch.backends.mps.is_built()\n"
        " mps_reported = torch.backends.mps.is_available()\n"
        " mps_tensor_ok = False\n"
        " mps_error = ''\n"
        " if mps_built:\n"
        "  try:\n"
        "   _ = torch.ones(1, device='mps')\n"
        "   mps_tensor_ok = True\n"
        "  except Exception as e:\n"
        "   mps_error = str(e)\n"
        " print(json.dumps({'torch': torch.__version__, 'mps_built': mps_built,"
        " 'mps_reported_available': mps_reported, 'mps_tensor_ok': mps_tensor_ok,"
        " 'mps_available': bool(mps_reported or mps_tensor_ok), 'mps_error': mps_error}))\n"
        "except Exception as e:\n"
        " print(json.dumps({'error': str(e)}))\n"
    )
    result = run_capture(["conda", "run", "-n", env, "python", "-c", code], timeout=30)
    payload: Dict[str, Any] = {"probe_ok": result["ok"]}
    try:
        payload.update(json.loads(result["stdout"].splitlines()[-1]))
    except Exception:
        payload["error"] = result["stderr"] or result["stdout"] or "torch probe failed"
    return payload


def list_names(path: Path, suffixes: tuple[str, ...]) -> List[str]:
    if not path.is_dir():
        return []
    return sorted(p.name for p in path.iterdir() if p.is_file() and p.suffix.lower() in suffixes)


def command_probe(command: str) -> Dict[str, Any]:
    command = str(command or "").strip()
    if not command:
        return {"available": False, "reason": "command_empty"}
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return {"available": False, "reason": f"command_parse_failed:{exc}"}
    if not parts:
        return {"available": False, "reason": "command_empty"}
    executable = Path(parts[0]).expanduser()
    executable_ok = executable.is_file() if executable.is_absolute() or "/" in parts[0] else bool(shutil.which(parts[0]))
    missing_scripts: List[str] = []
    for raw in parts[1:]:
        if "{" in raw or "}" in raw:
            continue
        if not (raw.endswith(".py") or "/" in raw):
            continue
        candidate = Path(raw).expanduser()
        if candidate.suffix == ".py" and not candidate.is_file():
            missing_scripts.append(str(candidate))
    return {
        "available": bool(executable_ok and not missing_scripts),
        "executable_ok": bool(executable_ok),
        "missing_scripts": missing_scripts,
        "executable": parts[0],
    }


def known_trainer_candidates(home: Optional[Path] = None) -> List[Path]:
    base = home or Path.home()
    return [
        base / "kohya_ss" / "sd-scripts" / "sdxl_train_network.py",
        base / "sd-scripts" / "sdxl_train_network.py",
        base / "kohya_ss" / "sdxl_train_network.py",
    ]


def detect_lora_trainer(command: str = "") -> Dict[str, Any]:
    configured = str(command or DEFAULT_TRAIN_CMD or "").strip()
    if configured:
        probe = command_probe(configured)
        return {
            "available": bool(probe.get("available")),
            "source": "configured_command",
            "command": configured,
            "probe": probe,
        }
    for candidate in known_trainer_candidates():
        if not candidate.is_file():
            continue
        launcher = "accelerate" if shutil.which("accelerate") else "python3"
        command_text = f"{launcher} {candidate}"
        probe = command_probe(command_text)
        return {
            "available": bool(probe.get("available")),
            "source": "known_path",
            "command": command_text,
            "probe": probe,
        }
    return {
        "available": False,
        "source": "not_found",
        "command": "",
        "checked": [str(p) for p in known_trainer_candidates()],
    }


def project_image_backend(root: Path) -> str:
    settings = root / "_设置.md"
    if settings.is_file():
        text = settings.read_text(encoding="utf-8")
        for key in ("生图AI", "生图模型", "生图渠道"):
            match = re.search(rf"{re.escape(key)}\s*[：:]\s*([^\n#]+)", text)
            if match:
                return match.group(1).strip().strip("`") or "Codex"
    return "Codex"


def dataset_manifest_path(root: Path, character_id: str, form: str) -> Path:
    return root / "设定库" / "lora" / slugify(character_id) / slugify(form or "常态") / "dataset_manifest.json"


def runtime_route_path(root: Path, character_id: str = "", form: str = "") -> Path:
    if character_id or form:
        key = "__".join(part for part in (slugify(character_id), slugify(form or "常态")) if part)
        return root / "生产数据" / f"lora_runtime_route_{key}.json"
    return root / "生产数据" / "lora_runtime_route.json"


def dataset_readiness(root: Path, character_id: str, form: str, *, allow_warnings: bool = False) -> Dict[str, Any]:
    path = dataset_manifest_path(root, character_id, form)
    if not path.is_file():
        return {"available": False, "path": str(path), "missing": "dataset_manifest_missing"}
    try:
        data = read_json(path)
    except Exception as exc:
        return {"available": False, "path": str(path), "missing": f"dataset_manifest_invalid:{exc}"}
    summary = data.get("summary") if isinstance(data, Mapping) else {}
    warnings = list(summary.get("warnings", []) or []) if isinstance(summary, Mapping) else []
    ready = bool(summary.get("ready_for_training")) if isinstance(summary, Mapping) else False
    available = ready or (allow_warnings and bool(summary.get("images")))
    return {
        "available": available,
        "path": str(path),
        "images": summary.get("images") if isinstance(summary, Mapping) else None,
        "warnings": warnings,
        "ready_for_training": ready,
        "allow_warnings": allow_warnings,
    }


def local_training_readiness(
    comfy_home: Path,
    env: str,
    *,
    project_root: Optional[Path] = None,
    character_id: str = "",
    form: str = "",
    trainer_cmd: str = "",
    allow_dataset_warnings: bool = False,
    assume_accelerator: bool = False,
) -> Dict[str, Any]:
    payload = profile_payload(comfy_home, env, DEFAULT_URL)
    conda_ok = conda_env_exists(env)
    torch = torch_probe(env) if conda_ok else {"probe_ok": False, "error": "conda env missing"}
    trainer = detect_lora_trainer(trainer_cmd)
    checkpoints = payload["inventory"]["checkpoints"]
    missing: List[str] = []
    if not comfy_home.is_dir():
        missing.append("comfy_home_missing")
    if not (comfy_home / "main.py").is_file():
        missing.append("comfy_main_missing")
    if not conda_ok:
        missing.append("conda_env_missing")
    accelerator_override = bool(assume_accelerator or os.environ.get("N2D_ASSUME_LOCAL_ACCELERATOR", "") == "1")
    if not torch.get("mps_available") and not accelerator_override:
        missing.append("mps_not_available")
    if not checkpoints:
        missing.append("sdxl_checkpoint_missing")
    if not trainer.get("available"):
        missing.append("lora_trainer_missing")

    dataset: Dict[str, Any] = {"required": False}
    if project_root and character_id:
        dataset = dataset_readiness(project_root, character_id, form, allow_warnings=allow_dataset_warnings)
        dataset["required"] = True
        if not dataset.get("available"):
            missing.append(str(dataset.get("missing") or "dataset_not_ready_for_training"))

    return {
        "available": not missing,
        "provider": "local_sdxl" if not missing else "",
        "missing_requirements": missing,
        "checks": {
            "comfy_home_exists": comfy_home.is_dir(),
            "comfy_main_exists": (comfy_home / "main.py").is_file(),
            "conda_env_exists": conda_ok,
            "checkpoint_count": len(checkpoints),
            "torch": torch,
            "accelerator_override_assumed": accelerator_override,
            "accelerator_override_reason": (
                "operator supplied --assume-local-accelerator after an external/top-level MPS probe"
                if assume_accelerator
                else ("N2D_ASSUME_LOCAL_ACCELERATOR=1" if accelerator_override else "")
            ),
            "trainer": trainer,
            "dataset": dataset,
        },
        "paths": payload["paths"],
        "inventory": payload["inventory"],
    }


def profile_payload(comfy_home: Path, env: str, url: str) -> Dict[str, Any]:
    checkpoints = list_names(comfy_home / "models" / "checkpoints", (".safetensors", ".ckpt", ".pt"))
    loras = list_names(comfy_home / "models" / "loras", (".safetensors", ".pt"))
    return {
        "kind": KIND_PROFILE,
        "version": 1,
        "created_at": now_iso(),
        "purpose": ["lora_validation", "hero_shot_sidechain"],
        "not_a_project_model_switch": True,
        "main_image_backend_policy": "unchanged; use only with lora_exception_scope hero shots",
        "backend": {
            "model_family": "sdxl",
            "channel": "local_comfyui",
            "comfy_home": str(comfy_home),
            "conda_env": env,
            "server_url": url.rstrip("/"),
            "launch_script": str(comfy_home / "launch_n2d_sdxl.sh"),
        },
        "paths": {
            "checkpoints": str(comfy_home / "models" / "checkpoints"),
            "loras": str(comfy_home / "models" / "loras"),
            "output": str(comfy_home / "output"),
        },
        "inventory": {
            "checkpoints": checkpoints,
            "loras": loras,
        },
        "qc_required": [
            "full image_qc face_reference_coverage",
            "style_consistency",
            "local_face_patch_guard",
            "human hero-shot signoff",
        ],
    }


def runtime_route_payload(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root)
    comfy_home = Path(args.comfy_home).expanduser()
    local = local_training_readiness(
        comfy_home,
        args.env,
        project_root=root,
        character_id=args.character_id,
        form=args.form,
        trainer_cmd=args.trainer_cmd,
        allow_dataset_warnings=args.allow_dataset_warnings,
        assume_accelerator=args.assume_local_accelerator,
    )
    fallback_backend = project_image_backend(root)
    use_local = bool(local.get("available"))
    decision = "local_lora_training" if use_local else "cloud_image_generation_fallback"
    return {
        "kind": KIND_ROUTE,
        "version": 1,
        "created_at": now_iso(),
        "project_root": str(root),
        "character_id": args.character_id,
        "form": args.form,
        "policy": {
            "prefer_local_lora_training_when_complete": True,
            "fallback_to_project_image_backend_when_local_incomplete": True,
            "not_a_project_model_switch": True,
            "local_training_requires": [
                "ComfyUI files",
                "sdxl-comfy conda env",
                "MPS accelerator",
                "at least one SDXL checkpoint",
                "configured LoRA trainer command or known trainer script",
                "ready dataset manifest when character_id is provided",
            ],
        },
        "decision": {
            "route": decision,
            "use_local_lora_training": use_local,
            "fallback_image_backend": fallback_backend,
            "reason": "local LoRA training environment is complete" if use_local else "local LoRA training environment is incomplete; keep image production on the project backend",
        },
        "local_training": local,
        "fallback": {
            "image_backend": fallback_backend,
            "action": "use n2d-image main/cloud backend for generation",
            "do_not_block_image_generation_on_missing_local_lora": True,
        },
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    comfy_home = Path(args.comfy_home).expanduser()
    env = args.env
    payload = profile_payload(comfy_home, env, args.url)
    checks = {
        "comfy_home_exists": comfy_home.is_dir(),
        "comfy_main_exists": (comfy_home / "main.py").is_file(),
        "launch_script_exists": (comfy_home / "launch_n2d_sdxl.sh").is_file(),
        "conda_env_exists": conda_env_exists(env),
        "checkpoint_count": len(payload["inventory"]["checkpoints"]),
        "lora_count": len(payload["inventory"]["loras"]),
    }
    if checks["conda_env_exists"]:
        checks["torch"] = torch_probe(env)
    payload["checks"] = checks
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("# Local SDXL/ComfyUI doctor")
        for key, value in checks.items():
            print(f"- {key}: {value}")
        if not checks["checkpoint_count"]:
            print(f"[next] put an SDXL checkpoint in {comfy_home / 'models' / 'checkpoints'}")
    return 0 if checks["comfy_main_exists"] and checks["conda_env_exists"] else 1


def cmd_write_profile(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    payload = profile_payload(Path(args.comfy_home).expanduser(), args.env, args.url)
    out = root / "生产数据" / "local_sdxl_profile.json"
    write_json(out, payload)
    print(f"[ok] wrote {out}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    payload = runtime_route_payload(args)
    if args.write:
        root = Path(args.project_root)
        legacy = runtime_route_path(root)
        write_json(legacy, payload)
        print(f"[ok] wrote {legacy}")
        scoped = runtime_route_path(root, args.character_id, args.form)
        if scoped != legacy:
            write_json(scoped, payload)
            print(f"[ok] wrote {scoped}")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        decision = payload["decision"]
        print("# LoRA runtime route")
        print(f"- route: {decision['route']}")
        print(f"- use_local_lora_training: {decision['use_local_lora_training']}")
        print(f"- fallback_image_backend: {decision['fallback_image_backend']}")
        missing = payload["local_training"].get("missing_requirements") or []
        if missing:
            print(f"- missing: {', '.join(missing)}")
    return 0


def build_prompt(args: argparse.Namespace) -> Dict[str, Any]:
    positive = args.prompt.strip()
    if args.trigger and args.trigger not in positive:
        positive = f"{args.trigger}, {positive}"
    negative = args.negative.strip() or "low quality, blurry, deformed face, wrong identity, extra fingers"
    ckpt_node = "1"
    model_out: List[Any] = [ckpt_node, 0]
    clip_out: List[Any] = [ckpt_node, 1]
    nodes: Dict[str, Any] = {
        ckpt_node: {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": args.checkpoint},
        }
    }
    if args.lora:
        nodes["2"] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": model_out,
                "clip": clip_out,
                "lora_name": args.lora,
                "strength_model": args.lora_strength,
                "strength_clip": args.lora_clip_strength,
            },
        }
        model_out = ["2", 0]
        clip_out = ["2", 1]
    nodes.update(
        {
            "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": clip_out, "text": positive}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": clip_out, "text": negative}},
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": args.width, "height": args.height, "batch_size": 1},
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "model": model_out,
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0],
                    "seed": args.seed,
                    "steps": args.steps,
                    "cfg": args.cfg,
                    "sampler_name": args.sampler,
                    "scheduler": args.scheduler,
                    "denoise": args.denoise,
                },
            },
            "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": [ckpt_node, 2]}},
            "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": args.prefix}},
        }
    )
    return nodes


def cmd_workflow(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    prompt = build_prompt(args)
    out = root / "生产数据" / "comfyui_workflows" / f"{args.episode}_{args.clip}_sdxl_lora.json"
    payload = {
        "kind": KIND_WORKFLOW,
        "version": 1,
        "created_at": now_iso(),
        "episode": args.episode,
        "clip": args.clip,
        "character_id": args.character_id,
        "form": args.form,
        "backend": "local_comfyui_sdxl",
        "not_a_project_model_switch": True,
        "workflow_use": "hero_shot_sidechain",
        "checkpoint": args.checkpoint,
        "lora": args.lora,
        "prompt": prompt,
    }
    write_json(out, payload)
    print(f"[ok] wrote {out}")
    print("[next] ensure lora_exception_scope covers this clip before accepting output")
    return 0


def cmd_enqueue(args: argparse.Namespace) -> int:
    workflow = read_json(Path(args.workflow))
    prompt = workflow.get("prompt") if isinstance(workflow, Mapping) else None
    if not isinstance(prompt, Mapping):
        raise ValueError("workflow file must contain a prompt object")
    body = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(
        args.url.rstrip("/") + "/prompt",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            print(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"[error] ComfyUI enqueue failed: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_record_output(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    output = Path(args.output)
    asset_rel = rel(root, output) if output.exists() else str(args.output)
    event = {
        "kind": KIND_EVENT,
        "time": now_iso(),
        "provider": "ComfyUI SDXL LoRA",
        "method": "sdxl_lora",
        "asset": asset_rel,
        "generation": {
            "backend": "comfyui",
            "model": "sdxl",
            "workflow": str(args.workflow or ""),
            "clip": args.clip,
            "lora_model": args.lora_model or "",
            "lora_base_model": "sdxl",
            "not_a_project_model_switch": True,
        },
        "meta": {
            "episode": args.episode,
            "clip": args.clip,
            "character_id": args.character_id,
            "form": args.form,
        },
    }
    append_jsonl(root / "生产数据" / "production_events.jsonl", event)
    print(f"[ok] recorded sidechain event for {args.clip}: {asset_rel}")
    print("[next] run lora.py exception-scope --check and image gate before video")
    return 0


def add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--comfy-home", default=str(DEFAULT_COMFY_HOME))
    p.add_argument("--env", default=DEFAULT_ENV)
    p.add_argument("--url", default=DEFAULT_URL)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="n2d local SDXL/ComfyUI sidechain")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor")
    add_common(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("write-profile")
    p.add_argument("project_root")
    add_common(p)
    p.set_defaults(func=cmd_write_profile)

    p = sub.add_parser("route")
    p.add_argument("project_root")
    add_common(p)
    p.add_argument("--character-id", default="")
    p.add_argument("--form", default="")
    p.add_argument("--trainer-cmd", default=DEFAULT_TRAIN_CMD)
    p.add_argument("--allow-dataset-warnings", action="store_true")
    p.add_argument(
        "--assume-local-accelerator",
        action="store_true",
        help="Audit override for hosts where subprocess MPS probes fail but a top-level conda MPS tensor probe has passed.",
    )
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_route)

    p = sub.add_parser("workflow")
    p.add_argument("project_root")
    p.add_argument("episode")
    p.add_argument("--clip", required=True)
    p.add_argument("--character-id", required=True)
    p.add_argument("--form", default="")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--lora", default="")
    p.add_argument("--trigger", default="")
    p.add_argument("--prompt", required=True)
    p.add_argument("--negative", default="")
    p.add_argument("--prefix", default="n2d_sdxl_lora")
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--steps", type=int, default=24)
    p.add_argument("--cfg", type=float, default=6.0)
    p.add_argument("--sampler", default="dpmpp_2m")
    p.add_argument("--scheduler", default="karras")
    p.add_argument("--denoise", type=float, default=1.0)
    p.add_argument("--lora-strength", type=float, default=0.75)
    p.add_argument("--lora-clip-strength", type=float, default=0.75)
    p.set_defaults(func=cmd_workflow)

    p = sub.add_parser("enqueue")
    p.add_argument("workflow")
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--timeout", type=int, default=20)
    p.set_defaults(func=cmd_enqueue)

    p = sub.add_parser("record-output")
    p.add_argument("project_root")
    p.add_argument("episode")
    p.add_argument("--clip", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--character-id", default="")
    p.add_argument("--form", default="")
    p.add_argument("--lora-model", default="")
    p.add_argument("--workflow", default="")
    p.set_defaults(func=cmd_record_output)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
