#!/usr/bin/env python3
"""Generate n2d episode images through the official Dreamina CLI.

This backend is for projects that cannot use Codex's text-only image path for
high-risk character shots.  It reuses the prompt/target/reference resolution
from ``codex_image_runner.py`` but submits real local reference images to
``dreamina image2image``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import codex_image_runner as base


SOURCE = "skills/n2d-image/scripts/dreamina_image_runner.py"
LOG_REL = Path("生产数据") / "dreamina_image_runner.jsonl"
MAX_REFERENCES = 10
SIGNOFF_REL = Path("合规") / "image_backend_override.json"


def dreamina_image_signoff_allows(root: Path) -> bool:
    """Dreamina image spend is a signed exception; Codex image2 remains default."""
    try:
        payload = json.loads((root / SIGNOFF_REL).read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict) or payload.get("approved") is not True:
        return False
    scope = str(payload.get("scope") or payload.get("stage") or "image").lower()
    if "image" not in scope and "生图" not in scope:
        return False
    backend = str(
        payload.get("backend")
        or payload.get("canonical")
        or payload.get("image_backend")
        or ""
    ).lower()
    return "dreamina" in backend or "即梦" in backend or backend == "dreamina_official"


def require_dreamina_image_signoff(root: Path) -> None:
    if dreamina_image_signoff_allows(root):
        return
    raise RuntimeError(
        "全项目生图优先 Codex image2；n2d 的 Dreamina/即梦图片 runner 只能作为签核例外。"
        f"如确需使用，请先写 {SIGNOFF_REL.as_posix()}，包含 "
        '{"approved": true, "scope": "image", "backend": "dreamina_official", "reason": "..."}'
    )


def _field(body: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}\*\*：([^\n]+)$", body, re.M)
    if not m:
        m = re.search(rf"^{re.escape(label)}：([^\n]+)$", body, re.M)
    return m.group(1).strip() if m else ""


def dreamina_reference_inputs(
    root: Path,
    target: base.Target,
    refs: Sequence[Path],
    episode: str,
) -> List[Dict[str, Any]]:
    """Describe the exact Dreamina attachments, including complete hashes."""
    role_by_path: Dict[str, tuple[str, str]] = {}
    try:
        bundle = base.reference_bundle_for_target(root, episode, target)
    except Exception:
        bundle = {}
    for item in bundle.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("kind") or item.get("role") or "reference")
        owner = str(
            item.get("owner") or item.get("character") or item.get("asset_id") or
            item.get("id") or item.get("ref") or ""
        )
        for raw in item.get("paths") or []:
            role_by_path[str(raw)] = (role, owner)

    inputs: List[Dict[str, Any]] = []
    for index, path in enumerate(refs, 1):
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = str(path)
        role, owner = role_by_path.get(rel, ("reference", path.stem))
        if index == 1 and target.mode in {"midframe", "tailframe"}:
            role = "source_frame"
            owner = target.clip
        inputs.append({
            "index": index,
            "role": role,
            "owner": owner,
            "actual_path": str(path),
            "rel_path": rel,
            "sha256": base.file_sha256(path),
        })
    return inputs


def build_dreamina_compiled_request(
    root: Path,
    episode: str,
    target: base.Target,
    reference_inputs: Sequence[Mapping[str, Any]],
    *,
    model_version: str = "",
    resolution_type: str = "",
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if model_version:
        params["model_version"] = model_version
    if resolution_type:
        params["resolution_type"] = resolution_type
    compiled = base.compile_target_image_request(
        root,
        episode,
        target,
        reference_inputs,
        backend="dreamina",
        model=model_version,
        channel="official_cli",
        request_params_override=params,
    )
    lint = base.lint_compiled_image_prompt(compiled)
    if lint.get("errors"):
        raise ValueError("compiled Dreamina image request invalid: " + ", ".join(lint["errors"]))
    return compiled


def build_dreamina_prompt(
    root: Path,
    episode: str,
    target: base.Target,
    reference_inputs: Sequence[Mapping[str, Any]] = (),
    *,
    model_version: str = "",
    resolution_type: str = "",
    compiled_request: Optional[Mapping[str, Any]] = None,
) -> str:
    """Return exactly the compiler text submitted to Dreamina."""
    compiled = dict(compiled_request or build_dreamina_compiled_request(
        root,
        episode,
        target,
        reference_inputs,
        model_version=model_version,
        resolution_type=resolution_type,
    ))
    return str(compiled.get("prompt") or "").strip()


def _reference_block(body: str) -> str:
    m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^\*\*导演视角八维\*\*|^##\s+|\Z)", body)
    return m.group(0) if m else ""


def prompt_reference_paths(root: Path, target: base.Target, episode: str) -> List[Path]:
    paths: List[Path] = []
    seen: set[Path] = set()

    def add(rel: str) -> None:
        text = rel.strip().strip("`")
        if not text.startswith("出图/"):
            return
        path = root / text
        if path in seen or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            return
        if not path.is_file():
            return
        seen.add(path)
        paths.append(path)

    if target.mode != "firstframe":
        try:
            source = root / base.target_for_shot(target.clip, target.section, episode).rel_path
            if source.is_file():
                seen.add(source)
                paths.append(source)
        except Exception:
            pass

    block = _reference_block(target.section.body)
    for raw in base.backticked(block):
        add(raw)

    # Always merge the registry-resolved bundle (not only when prose is empty):
    # a hand-written 参考图 block listing any one placeholder image must NOT
    # suppress the carried-identity face anchors — that was the Dreamina-side
    # replica of the 定妆 face-drift bug. Character (carried-identity) face anchors
    # are prepended so they survive the MAX_REFERENCES cap; everything else appends.
    bundle = base.reference_bundle_for_target(root, episode, target)
    face_first: List[Path] = []
    for item in bundle.get("items") or []:
        if str(item.get("kind")) != "character":
            continue
        for rel in item.get("paths") or []:
            p = root / str(rel)
            if p.is_file() and p not in seen and p not in face_first:
                face_first.append(p)
    paths = face_first + [p for p in paths if p not in face_first]
    for item in bundle.get("items") or []:
        if str(item.get("kind")) == "character":
            continue
        for rel in item.get("paths") or []:
            add(str(rel))

    return paths[:MAX_REFERENCES]


def submit_id_from(text: str) -> str:
    patterns = [
        r'"submit_id"\s*:\s*"([^"]+)"',
        r"submit_id\s*[=:]\s*([A-Za-z0-9._-]+)",
        r"submit id\s*[=:]\s*([A-Za-z0-9._-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1)
    return ""


def image_candidates(path: Path) -> List[Path]:
    if not path.is_dir():
        return []
    candidates: List[Path] = []
    for suffix in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        candidates.extend(path.rglob(suffix))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def materialize_png(src: Path, out_path: Path) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".png":
        shutil.copy2(src, out_path)
        return base.png_valid(out_path)
    proc = subprocess.run(
        ["sips", "-s", "format", "png", str(src), "--out", str(out_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode == 0 and base.png_valid(out_path)


def run_dreamina(
    target: base.Target,
    *,
    root: Path,
    episode: str,
    temp_path: Path,
    timeout_sec: Optional[float],
    poll_sec: int,
    model_version: str,
    resolution_type: str,
    refs: Optional[Sequence[Path]] = None,
    compiled_request: Optional[Mapping[str, Any]] = None,
) -> tuple[bool, str, str, List[Path]]:
    resolved_refs = list(refs) if refs is not None else prompt_reference_paths(root, target, episode)
    if not resolved_refs:
        return False, "", "no ready reference images resolved for Dreamina image2image", resolved_refs
    reference_inputs = dreamina_reference_inputs(root, target, resolved_refs, episode)
    compiled = dict(compiled_request or build_dreamina_compiled_request(
        root,
        episode,
        target,
        reference_inputs,
        model_version=model_version,
        resolution_type=resolution_type,
    ))
    prompt = build_dreamina_prompt(
        root,
        episode,
        target,
        reference_inputs,
        model_version=model_version,
        resolution_type=resolution_type,
        compiled_request=compiled,
    )
    ratio = base.aspect_ratio(root)
    download_dir = temp_path.parent / f"{temp_path.stem}_download"
    if download_dir.exists():
        shutil.rmtree(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "dreamina",
        "image2image",
        "--images",
        ",".join(str(p) for p in resolved_refs),
        "--prompt",
        prompt,
        "--ratio",
        ratio,
        "--poll",
        str(max(0, min(poll_sec, int(timeout_sec or poll_sec)))),
    ]
    if model_version:
        cmd.extend(["--model_version", model_version])
    if resolution_type:
        cmd.extend(["--resolution_type", resolution_type])
    proc = subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_sec,
    )
    combined = "\n".join(p for p in (proc.stdout, proc.stderr) if p)
    if proc.returncode != 0:
        return False, "", f"dreamina image2image exit {proc.returncode}: {combined}", resolved_refs
    sid = submit_id_from(combined)
    if not sid:
        return False, "", f"dreamina output did not include submit_id: {combined[:1000]}", resolved_refs
    query = subprocess.run(
        ["dreamina", "query_result", "--submit_id", sid, "--download_dir", str(download_dir)],
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_sec,
    )
    qout = "\n".join(p for p in (query.stdout, query.stderr) if p)
    if query.returncode != 0:
        return False, sid, f"dreamina query_result exit {query.returncode}: {qout}", resolved_refs
    candidates = image_candidates(download_dir)
    if not candidates:
        return False, sid, f"dreamina query_result downloaded no image files: {qout[:1000]}", resolved_refs
    if not materialize_png(candidates[0], temp_path):
        return False, sid, f"downloaded result is not a valid PNG and conversion failed: {candidates[0]}", resolved_refs
    return True, sid, "", resolved_refs


def archive_existing(root: Path, rel_path: str, task_id: str) -> Optional[Path]:
    final = root / rel_path
    if not final.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = root / "废料" / "出图" / rel_path.replace("出图/", "").rsplit("/", 1)[0] / f"dreamina_rerun_{task_id}_{stamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / final.name
    shutil.copy2(final, archive_path)
    return archive_path


def append_log(root: Path, row: dict) -> None:
    path = root / LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def record_event(
    root: Path,
    episode: str,
    target: base.Target,
    *,
    status: str,
    duration_sec: float,
    task_id: str,
    seed: str,
    temp_path: Path,
    submit_id: str,
    refs: List[Path],
    archive_path: Optional[Path],
    compiled_request: Optional[Mapping[str, Any]] = None,
    submitted_prompt: str = "",
    compiled_receipt: Optional[Path] = None,
    error: str = "",
) -> None:
    compiled = dict(compiled_request or {})
    metrics = compiled.get("metrics") if isinstance(compiled.get("metrics"), Mapping) else {}
    experiment = compiled.get("experiment") if isinstance(compiled.get("experiment"), Mapping) else {}
    prompt_sha = base.sha256_text(submitted_prompt)
    event = "redraw" if archive_path or os.environ.get("N2D_REASON") == "rerun" else "generation"
    cmd = [
        sys.executable,
        str(base.repo_root() / base.DASHBOARD),
        "record",
        str(root),
        "--episode",
        episode,
        "--stage",
        "image",
        "--event",
        event,
        "--asset",
        target.rel_path,
        "--status",
        status,
        "--provider",
        "Dreamina",
        "--duration-sec",
        f"{duration_sec:.3f}",
        "--unit",
        "credits",
        "--meta",
        f"mode=dreamina_image2image_{target.mode}",
        "--meta",
        f"task={task_id}",
        "--meta",
        f"shot={target.shot}",
        "--meta",
        f"submit_id={submit_id}",
        "--meta",
        f"requested_seed={seed}",
        "--meta",
        "effective_seed=",
        "--meta",
        "seed_effective=false",
        "--meta",
        "seed_support=unsupported_or_unknown",
        "--meta",
        "seed_strategy=fixed_pool",
        "--meta",
        f"reference_count={len(refs)}",
        "--meta",
        f"actual_submit_prompt_sha256={prompt_sha}",
        "--meta",
        f"prompt_compiler_kind={compiled.get('kind') or ''}",
        "--meta",
        f"prompt_compiler_version={compiled.get('version') or ''}",
        "--meta",
        f"prompt_profile_version={compiled.get('profile_version') or ''}",
        "--meta",
        f"prompt_profile={compiled.get('profile') or ''}",
        "--meta",
        f"prompt_task_type={compiled.get('task_type') or ''}",
        "--meta",
        f"source_contract_sha256={compiled.get('source_contract_sha256') or ''}",
        "--meta",
        f"source_contract_text_sha256={compiled.get('source_contract_text_sha256') or ''}",
        "--meta",
        f"execution_context_sha256={compiled.get('execution_context_sha256') or ''}",
        "--meta",
        f"compiled_request_sha256={compiled.get('compiled_request_sha256') or ''}",
        "--meta",
        f"compiled_prompt_chars={metrics.get('prompt_chars') or 0}",
        "--meta",
        f"compiled_estimated_text_tokens={metrics.get('estimated_text_tokens') or 0}",
        "--meta",
        f"image_prompt_experiment_id={experiment.get('experiment_id') or ''}",
        "--meta",
        f"image_prompt_variant={experiment.get('variant') or ''}",
        "--meta",
        "compiled_request_params=" + json.dumps(compiled.get("request_params") or {}, ensure_ascii=False, sort_keys=True),
        "--meta",
        f"temp_output={temp_path}",
        "--meta",
        f"source={SOURCE}",
    ]
    for ref in refs[:MAX_REFERENCES]:
        try:
            rel = ref.relative_to(root)
        except ValueError:
            rel = ref
        cmd.extend(["--meta", f"reference={rel}"])
        if ref.is_file():
            cmd.extend(["--meta", f"reference_sha256={rel}#{base.file_sha256(ref)}"])
    if compiled_receipt:
        cmd.extend(["--meta", f"compiled_request_receipt={compiled_receipt}"])
    if archive_path:
        cmd.extend(["--redraw-reason", f"{task_id} Dreamina image2image 真实参考图重出 {target.shot}", "--redraw-category", "backend_migration"])
        cmd.extend(["--meta", f"archived_previous={archive_path}"])
    if error:
        cmd.extend(["--meta", f"error={error[:500]}"])
    subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def latest_recorded_status(root: Path, task_id: str, rel_path: str) -> str:
    path = root / "生产数据" / "production_events.jsonl"
    if not path.is_file():
        return ""
    status = ""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("stage") != "image":
                continue
            generation = event.get("generation")
            meta = event.get("meta")
            if not isinstance(generation, dict) or not isinstance(meta, dict):
                continue
            if generation.get("asset") == rel_path and str(meta.get("task") or "") == task_id:
                status = str(generation.get("status") or "")
    return status.lower()


def process_target(
    root: Path,
    episode: str,
    target: base.Target,
    *,
    task_id: str,
    timeout_sec: Optional[float],
    poll_sec: int,
    model_version: str,
    resolution_type: str,
    dry_run: bool,
    force: bool,
) -> bool:
    seed = base.logical_seed(root, episode, target.shot, target.rel_path)
    final = root / target.rel_path
    temp_dir = Path(tempfile.gettempdir()) / "n2d_dreamina_image_runner" / (task_id or "manual")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{episode}_{base.temp_token(target.shot)}_{Path(target.rel_path).stem}.png"
    previous_status = latest_recorded_status(root, task_id, target.rel_path)
    refs = prompt_reference_paths(root, target, episode)
    reference_inputs = dreamina_reference_inputs(root, target, refs, episode)
    try:
        compiled_request = build_dreamina_compiled_request(
            root,
            episode,
            target,
            reference_inputs,
            model_version=model_version,
            resolution_type=resolution_type,
        )
    except ValueError as exc:
        print(f"[fail] {target.shot}: {exc}", file=sys.stderr)
        return False
    submitted_prompt = build_dreamina_prompt(
        root,
        episode,
        target,
        reference_inputs,
        model_version=model_version,
        resolution_type=resolution_type,
        compiled_request=compiled_request,
    )
    if dry_run:
        print(json.dumps({
            "shot": target.shot,
            "mode": target.mode,
            "target": target.rel_path,
            "references": [str(p) for p in refs],
            "reference_count": len(refs),
            "logical_seed": seed,
            "skip_existing_pass": (not force and previous_status == "pass" and base.png_valid(final)),
            "prompt_compiler": {
                "profile_version": compiled_request.get("profile_version"),
                "profile": compiled_request.get("profile"),
                "task_type": compiled_request.get("task_type"),
                "compiled_request_sha256": compiled_request.get("compiled_request_sha256"),
                "actual_submit_prompt_sha256": base.sha256_text(submitted_prompt),
                "metrics": compiled_request.get("metrics"),
                "lint": compiled_request.get("lint"),
            },
        }, ensure_ascii=False))
        return True
    if not force and previous_status == "pass" and base.png_valid(final):
        print(f"[skip] {target.shot} already has Dreamina pass record for {task_id}: {target.rel_path}")
        return True

    # Pre-spend interlock (same as the Codex backend): a plate that depicts a
    # character must attach a real face anchor, else it renders a new drifting face.
    bundle = base.reference_bundle_for_target(root, episode, target)
    attached_rel: List[str] = []
    for p in refs:
        try:
            attached_rel.append(str(p.relative_to(root)))
        except ValueError:
            attached_rel.append(str(p))
    if (
        base.carried_identity_unanchored(bundle, attached_rel)
        and os.environ.get("N2D_ALLOW_UNANCHORED_IDENTITY_PLATE") != "1"
    ):
        carried = "、".join(str(c) for c in bundle.get("carried_identity") or [])
        print(
            f"[fail] {target.shot}: 本图声明承载角色身份（carries_identity={carried}），"
            "但没有任何角色脸锚作为 Dreamina image2image 参考传入——会另画一张新脸（定妆脸漂成因）。"
            "请把承载角色的脸部特写/正面参考置 ready，或设 N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1 显式豁免。",
            file=sys.stderr,
        )
        base.log_unanchored_friction(root, episode, target.shot, bundle.get("carried_identity"), "Dreamina")
        return False

    started = time.monotonic()
    archive_path: Optional[Path] = None
    submit_id = ""
    error = ""
    ok = False
    compiled_receipt: Optional[Path] = None
    try:
        if temp_path.exists():
            temp_path.unlink()
        compiled_receipt = base.write_compiled_request_receipt(
            root,
            episode,
            target,
            compiled_request,
            submitted_prompt,
        )
        ok, submit_id, error, refs = run_dreamina(
            target,
            root=root,
            episode=episode,
            temp_path=temp_path,
            timeout_sec=timeout_sec,
            poll_sec=poll_sec,
            model_version=model_version,
            resolution_type=resolution_type,
            refs=refs,
            compiled_request=compiled_request,
        )
        if ok:
            archive_path = archive_existing(root, target.rel_path, task_id)
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temp_path, final)
            ok = base.png_valid(final)
            if not ok:
                error = f"moved Dreamina output is not a valid PNG: {final}"
    except subprocess.TimeoutExpired:
        error = f"dreamina timed out after {timeout_sec}s"
    except Exception as exc:  # pragma: no cover
        error = f"{type(exc).__name__}: {exc}"

    duration = time.monotonic() - started
    record_event(
        root,
        episode,
        target,
        status="pass" if ok else "fail",
        duration_sec=duration,
        task_id=task_id,
        seed=seed,
        temp_path=temp_path,
        submit_id=submit_id,
        refs=refs,
        archive_path=archive_path,
        compiled_request=compiled_request,
        submitted_prompt=submitted_prompt,
        compiled_receipt=compiled_receipt,
        error=error,
    )
    append_log(root, {
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "episode": episode,
        "shot": target.shot,
        "mode": target.mode,
        "target": target.rel_path,
        "status": "pass" if ok else "fail",
        "duration_sec": round(duration, 3),
        "submit_id": submit_id,
        "reference_count": len(refs),
        "reference_sha256": [base.file_sha256(path) for path in refs if path.is_file()],
        "logical_seed": seed,
        "seed_effective": False,
        "prompt_compiler_kind": compiled_request.get("kind"),
        "prompt_compiler_version": compiled_request.get("version"),
        "prompt_profile_version": compiled_request.get("profile_version"),
        "prompt_profile": compiled_request.get("profile"),
        "prompt_task_type": compiled_request.get("task_type"),
        "source_contract_sha256": compiled_request.get("source_contract_sha256"),
        "execution_context_sha256": compiled_request.get("execution_context_sha256"),
        "compiled_request_sha256": compiled_request.get("compiled_request_sha256"),
        "actual_submit_prompt_sha256": base.sha256_text(submitted_prompt),
        "compiled_request_receipt": str(compiled_receipt or ""),
        "request_params": compiled_request.get("request_params") or {},
        "prompt_metrics": compiled_request.get("metrics") or {},
        "image_prompt_experiment_id": (compiled_request.get("experiment") or {}).get("experiment_id"),
        "image_prompt_variant": (compiled_request.get("experiment") or {}).get("variant"),
        "error": error[:1000],
    })
    if ok:
        print(f"[pass] {target.shot} -> {target.rel_path} ({submit_id})")
    else:
        print(f"[fail] {target.shot}: {error}", file=sys.stderr)
    return ok


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Dreamina official CLI image2image adapter for n2d image tasks")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--shots", default=os.environ.get("N2D_AFFECTED_SHOTS", ""))
    ap.add_argument("--max-shots", type=int)
    ap.add_argument("--timeout-sec", type=float, default=float(os.environ.get("N2D_DREAMINA_IMAGE_TIMEOUT", "900")))
    ap.add_argument("--poll-sec", type=int, default=int(os.environ.get("N2D_DREAMINA_IMAGE_POLL", "300")))
    ap.add_argument("--model-version", default=os.environ.get("N2D_DREAMINA_IMAGE_MODEL", "5.0"))
    ap.add_argument("--resolution-type", default=os.environ.get("N2D_DREAMINA_IMAGE_RESOLUTION", "2k"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-image-qc", action="store_true")
    ap.add_argument("--skip-final-gate", action="store_true")
    ap.add_argument("--skip-preflight", action="store_true", help="skip the pre-spend image_preflight gate (logs a dashboard waiver)")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    episode = base.normalize_episode(ns.episode)
    if not ns.dry_run:
        try:
            require_dreamina_image_signoff(root)
        except RuntimeError as exc:
            print(f"[block] {exc}", file=sys.stderr)
            return 1
    shots = base.split_csv(ns.shots)
    if not shots:
        raise SystemExit("--shots or N2D_AFFECTED_SHOTS is required")
    if ns.max_shots is not None:
        shots = shots[: ns.max_shots]
    targets = base.build_targets(root, episode, shots)
    if not targets:
        raise SystemExit("no targets resolved")
    task_id = os.environ.get("N2D_TASK_ID") or f"dreamina-{episode}"

    # Non-waivable ordering lock shared with codex_image_runner: --skip-preflight
    # cannot spend on Clip PNGs before the episode shared library is complete.
    if not ns.dry_run and not base.enforce_shared_first_interlock(root, episode):
        return 1

    # Pre-spend interlock: 生成前先跑 image_preflight 硬闸门，block 即拒绝生成不花钱；
    # 逃生口 --skip-preflight 留痕成 dashboard waiver（与 codex_image_runner 同源）。
    if not ns.dry_run:
        if ns.skip_preflight:
            base.record_waiver(root, episode, "image_preflight", "skip-preflight",
                               "operator passed --skip-preflight; pre-spend image_preflight gate not run")
        elif not base.run_image_gate(root, episode, stage="image_preflight"):
            print("[gate] image_preflight blocked — refusing to spend on generation; fix upstream or pass --skip-preflight", file=sys.stderr)
            return 1

    ok_all = True
    for target in targets:
        ok = process_target(
            root,
            episode,
            target,
            task_id=task_id,
            timeout_sec=ns.timeout_sec,
            poll_sec=ns.poll_sec,
            model_version=ns.model_version,
            resolution_type=ns.resolution_type,
            dry_run=ns.dry_run,
            force=ns.force,
        )
        if ok and not ns.dry_run and not ns.skip_image_qc:
            ok = base.run_target_image_qc(root, episode, target)
        ok_all = ok_all and ok
        if not ok and ns.stop_on_fail:
            break
    if ns.skip_image_qc and not ns.dry_run:
        base.record_waiver(root, episode, "image", "skip-image-qc",
                           "operator passed --skip-image-qc; per-target landed-frame QC not run")
    if ok_all and not ns.dry_run:
        if ns.skip_final_gate:
            base.record_waiver(root, episode, "image", "skip-final-gate",
                               "operator passed --skip-final-gate; whole-episode image gate not run")
        else:
            ok_all = base.run_image_gate(root, episode)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
