#!/usr/bin/env python3
"""Execute opt-in native multi-shot groups through video adapter v2.

The provider returns one group master.  ``accept`` deterministically splits that
master back into the original Clip units, preserving per-Clip QC, lineage,
redraw and progress semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
LIB = SCRIPT_DIR.parents[1] / "n2d" / "_lib"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import multishot_plan
import video_execution_adapter as vea
import video_runner

try:
    from flow_telemetry import record_milestone as _record_flow_milestone
except Exception:  # pragma: no cover
    _record_flow_milestone = None


def _record(root: Path, manifest: Mapping[str, Any], milestone: str, **extra: Any) -> None:
    if _record_flow_milestone is None:
        return
    try:
        _record_flow_milestone(
            root, milestone, episode=str(manifest.get("episode") or ""), stage="video",
            extra={"group_id": manifest.get("group_id"), **extra},
        )
    except Exception:
        pass


KIND = "n2d_multishot_batch"
VERSION = 1


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def clip_number(value: Any) -> int:
    match = re.search(r"(?:Clip[_-]?|CLIP)(\d+)", str(value or ""), re.I)
    return int(match.group(1)) if match else 0


def manifest_path(root: Path, episode: str, group_id: str) -> Path:
    return root / "生产数据" / "multishot_batches" / episode / f"{group_id}.json"


def _group(root: Path, episode: str, group_id: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    plan_path = root / "出视频" / episode / "prompt" / "multishot_plan.json"
    plan = load_json(plan_path)
    if not plan:
        plan = multishot_plan.build(str(root), episode)
        multishot_plan.write_plan(str(root), episode, plan)
    if not plan.get("active"):
        raise RuntimeError("原生多镜生成未激活；先在 _设置.md 开启该选择点并重跑 multishot_plan.py --write")
    for group in plan.get("groups") or []:
        if isinstance(group, dict) and str(group.get("group_id")) == group_id:
            return plan, group
    raise KeyError(f"multishot group not found: {group_id}")


def _member_items(root: Path, episode: str, members: Sequence[str]) -> list[Dict[str, Any]]:
    numbers = [clip_number(value) for value in members]
    if not numbers or any(number <= 0 for number in numbers):
        raise ValueError(f"invalid multishot members: {members}")
    parsed = video_runner.parse_prompt_pack(root, episode, min(numbers), max(numbers))
    by_number = {clip_number(item.get("clip")): item for item in parsed}
    out: list[Dict[str, Any]] = []
    for member, number in zip(members, numbers):
        item = dict(by_number.get(number) or {})
        if not item:
            raise RuntimeError(f"compiled prompt missing for multishot member {member}")
        prompt = str(item.pop("prompt_text", ""))
        duration = float(item.get("edit_target_duration") or item.get("story_duration") or 0)
        if duration <= 0:
            raise RuntimeError(f"{member} missing edit_target duration")
        item.update({
            "clip": str(member),
            "prompt": prompt,
            "duration_sec": duration,
            "edit_target_sec": duration,
        })
        out.append(item)
    return out


def _group_prompt(shots: Sequence[Mapping[str, Any]]) -> str:
    rows = [
        "一次生成以下连续镜头；严格保持角色、场景、光位与运动方向跨镜连续。每个 SHOT 是明确剪辑边界。",
    ]
    for idx, shot in enumerate(shots, 1):
        rows.append(
            f"SHOT {idx} [{shot.get('clip')} | {float(shot.get('edit_target_sec') or 0):.3f}s]: "
            f"{str(shot.get('prompt') or '').strip()}"
        )
    rows.append("只演完这些镜头，不增加片头片尾、额外对白、文字、水印或新人物。")
    return "\n".join(rows)


def prepare(root: Path, episode: str, group_id: str, *, force: bool = False) -> Dict[str, Any]:
    path = manifest_path(root, episode, group_id)
    if path.is_file() and not force:
        return load_json(path)
    plan, group = _group(root, episode, group_id)
    shots = _member_items(root, episode, list(group.get("members") or []))
    backend = str(group.get("backend") or "")
    adapter = vea.adapter_for(root, backend, "")
    status = vea.execution_status(
        root, backend, "", required_operations=("multishot_submit", "multishot_query")
    )
    prompt_dir = path.parent / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    # Keep one immutable compiled prompt per logical Clip.  The group prompt is
    # what the provider receives; the per-Clip files are what the existing
    # acceptance recipe hashes after the master is split back into Clip units.
    # Without both, multi-shot output could pass visually while losing the
    # prompt lineage required by n2d-video QC/reproducibility.
    for shot in shots:
        shot_prompt_file = prompt_dir / f"{str(shot.get('clip') or 'Clip')}.prompt.txt"
        shot_prompt_file.write_text(str(shot.get("prompt") or "").strip() + "\n", encoding="utf-8")
        shot["prompt_file"] = str(shot_prompt_file)
        shot["prompt_sha256"] = sha256_file(shot_prompt_file)
    prompt_file = prompt_dir / f"{group_id}.prompt.txt"
    prompt_file.write_text(_group_prompt(shots) + "\n", encoding="utf-8")
    total = round(sum(float(row.get("edit_target_sec") or 0) for row in shots), 3)
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "group_id": group_id,
        "backend": backend,
        "members": list(group.get("members") or []),
        "status": "prepared" if status.get("automated") and status.get("supports_multishot") else "job_package_only",
        "execution_adapter": status,
        "adapter": adapter or {},
        "prompt_file": str(prompt_file),
        "group_prompt_sha256": hashlib.sha256(prompt_file.read_bytes()).hexdigest(),
        "submit_duration": total,
        "shots": shots,
        "master_target": str(root / "生产数据" / "multishot_raw" / episode / f"{group_id}.mp4"),
        "model_handled_seams": [member for member in group.get("members") or []][1:],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "lineage_policy": "one provider master -> deterministic time split -> original per-Clip QC/progress units",
    }
    atomic_json(path, payload)
    return payload


def _adapter(manifest: Mapping[str, Any], root: Path, operation: str) -> Dict[str, Any]:
    adapter = vea.adapter_for(root, manifest.get("backend"), "")
    if not adapter:
        raise RuntimeError("multishot adapter v2 is not registered")
    if operation not in set(adapter.get("operations") or []):
        raise RuntimeError(f"adapter {adapter.get('adapter_id')} does not support {operation}")
    command = list(adapter.get("command") or [])
    binary = str(command[0]) if command else ""
    ready = (
        Path(binary).is_file() and os.access(binary, os.X_OK)
        if (os.path.isabs(binary) or "/" in binary)
        else shutil.which(binary)
    )
    if not ready:
        raise RuntimeError(f"adapter {adapter.get('adapter_id')} command unavailable: {binary}")
    return adapter


def _group_item(manifest: Mapping[str, Any]) -> Dict[str, Any]:
    frames: list[str] = []
    for shot in manifest.get("shots") or []:
        if not isinstance(shot, Mapping):
            continue
        for key in ("image", "end_image"):
            value = str(shot.get(key) or "")
            if value and value not in frames:
                frames.append(value)
    return {
        "group_id": manifest.get("group_id"),
        "clip": manifest.get("group_id"),
        "prompt_file": manifest.get("prompt_file"),
        "submit_duration": manifest.get("submit_duration"),
        "model_version": manifest.get("model_version") or "",
        "multiframe_images": frames,
        "target": Path(str(manifest.get("master_target") or "master.mp4")).name,
        "submit_id": manifest.get("submit_id") or "",
        "idempotency_key": manifest.get("idempotency_key") or "",
    }


def _invoke(root: Path, path: Path, manifest: Dict[str, Any], operation: str, *, dry_run: bool = False) -> Dict[str, Any]:
    adapter = _adapter(manifest, root, operation)
    item = _group_item(manifest)
    request = vea.build_request(
        operation=operation,
        root=root,
        manifest=manifest,
        item=item,
        adapter=adapter,
        extra={
            "group": {"group_id": manifest.get("group_id"), "members": manifest.get("members") or []},
            "shots": manifest.get("shots") or [],
            "output": {"target": manifest.get("master_target"), "directory": str(Path(str(manifest.get("master_target"))).parent)},
        },
    )
    request_path = vea.write_request(root, str(manifest.get("episode") or ""), request)
    args = vea.wrapper_args(adapter, operation, request_path)
    if dry_run:
        return {"dry_run": True, "adapter_id": adapter.get("adapter_id"), "request_path": str(request_path), "cmd_argv": args}
    if operation == "multishot_submit":
        video_runner.run_identity_handoff_guard(root, str(manifest.get("episode") or ""))
        video_runner.run_preflight_gate(root, str(manifest.get("episode") or ""))
    started = time.monotonic()
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    elapsed = round(time.monotonic() - started, 3)
    raw = vea.parse_result(proc.stdout or "", proc.stderr or "")
    result = vea.normalize_result(adapter, raw)
    failure = vea.classify_failure(proc.returncode, result, proc.stderr or "")
    manifest["last_operation"] = {
        "operation": operation,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "returncode": proc.returncode,
        "request_path": str(request_path),
        "request_sha256": request.get("request_sha256"),
        "idempotency_key": request.get("idempotency_key"),
        "elapsed_sec": elapsed,
        "result": result,
        "failure": failure,
    }
    manifest["idempotency_key"] = request.get("idempotency_key")
    if operation == "multishot_submit":
        manifest["submit_id"] = result.get("submit_id") or manifest.get("submit_id")
        manifest["status"] = "submitted" if proc.returncode == 0 and manifest.get("submit_id") else "submit_unknown"
    elif operation == "multishot_query":
        output = Path(str(result.get("output_path") or ""))
        target = Path(str(manifest.get("master_target")))
        if output.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            if output.resolve() != target.resolve():
                shutil.copy2(output, target)
        if target.is_file():
            manifest["status"] = "downloaded"
            manifest["master_sha256"] = sha256_file(target)
        else:
            manifest["status"] = "queried"
    elif operation == "multishot_cancel":
        manifest["status"] = "cancelled" if proc.returncode == 0 else "cancel_unknown"
    atomic_json(path, manifest)
    milestone = {
        "multishot_submit": "multishot_submitted",
        "multishot_query": "multishot_downloaded" if manifest.get("status") == "downloaded" else "multishot_queried",
        "multishot_cancel": "multishot_cancelled" if manifest.get("status") == "cancelled" else "multishot_cancel_unknown",
    }[operation]
    _record(
        root, manifest, milestone, adapter_id=adapter.get("adapter_id"), provider=adapter.get("provider"),
        status=manifest.get("status"), returncode=proc.returncode, elapsed_sec=elapsed,
        failure_class=failure.get("class"), retryable=failure.get("retryable"),
        paid_state_uncertain=failure.get("paid_state_uncertain"),
    )
    return manifest


def _split_master(root: Path, manifest: Dict[str, Any]) -> Path:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg unavailable; cannot split multi-shot master back into Clip units")
    master = Path(str(manifest.get("master_target") or ""))
    if not master.is_file():
        raise FileNotFoundError(master)
    derived_items: list[Dict[str, Any]] = []
    cursor = 0.0
    formal = video_runner.formal_video_dir(root, str(manifest.get("episode") or ""))
    formal.mkdir(parents=True, exist_ok=True)
    for shot in manifest.get("shots") or []:
        if not isinstance(shot, Mapping):
            continue
        duration = float(shot.get("edit_target_sec") or 0)
        target = formal / str(shot.get("target") or f"{shot.get('clip')}.mp4")
        proc = subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-ss", f"{cursor:.3f}", "-i", str(master),
            "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", str(target),
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0 or not target.is_file():
            raise RuntimeError(f"split failed for {shot.get('clip')}: {proc.stderr[-400:]}")
        derived_items.append({
            **dict(shot),
            "status": "downloaded",
            "target": target.name,
            "target_path": str(target),
            "anchor_consumption_mode": "model_native_multishot",
            "multishot_lineage": {
                "group_id": manifest.get("group_id"),
                "master": str(master),
                "master_sha256": sha256_file(master),
                "start_sec": round(cursor, 3),
                "end_sec": round(cursor + duration, 3),
            },
            "cost_provider": (manifest.get("adapter") or {}).get("provider") or manifest.get("backend"),
            "last_submit_elapsed_sec": (manifest.get("last_operation") or {}).get("elapsed_sec"),
        })
        cursor += duration
    derived_path = manifest_path(root, str(manifest.get("episode") or ""), str(manifest.get("group_id") or "group")).with_name(
        f"{manifest.get('group_id')}_derived_clips.json"
    )
    derived = {
        "kind": "n2d_video_batch",
        "version": 2,
        "episode": manifest.get("episode"),
        "batch": manifest.get("group_id"),
        "batch_id": manifest.get("group_id"),
        "backend": manifest.get("backend"),
        "model_version": manifest.get("model_version") or "",
        "items": derived_items,
        "multishot_parent": str(manifest_path(root, str(manifest.get("episode")), str(manifest.get("group_id")))),
    }
    atomic_json(derived_path, derived)
    return derived_path


def accept(root: Path, path: Path, manifest: Dict[str, Any], *, allow_qc_block: bool = False) -> Dict[str, Any]:
    derived_path = _split_master(root, manifest)
    accepted = []
    for shot in manifest.get("shots") or []:
        clip = str((shot or {}).get("clip") or "")
        accepted.append(video_runner.accept_clip(
            root, derived_path, clip,
            no_record=False, no_progress=False, allow_qc_block=allow_qc_block,
        ))
    manifest["status"] = "accepted"
    manifest["accepted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest["derived_manifest"] = str(derived_path)
    manifest["derived_clips"] = [row.get("target_path") for row in accepted]
    atomic_json(path, manifest)
    _record(root, manifest, "multishot_accepted", status=manifest.get("status"), count=len(accepted),
            artifact=str(manifest.get("master_target") or ""), artifact_sha256=manifest.get("master_sha256"))
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--group", required=True)
    p.add_argument("--force", action="store_true")
    for name in ("submit", "query", "cancel", "accept", "status"):
        p = sub.add_parser(name)
        p.add_argument("root")
        p.add_argument("manifest")
        if name in {"submit", "query", "cancel"}:
            p.add_argument("--dry-run", action="store_true")
        if name == "accept":
            p.add_argument("--allow-qc-block", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    if ns.cmd == "prepare":
        payload = prepare(root, ns.episode, ns.group, force=ns.force)
        path = manifest_path(root, ns.episode, ns.group)
    else:
        path = Path(ns.manifest).expanduser().resolve()
        payload = load_json(path)
        if ns.cmd == "submit":
            payload = _invoke(root, path, payload, "multishot_submit", dry_run=ns.dry_run)
        elif ns.cmd == "query":
            payload = _invoke(root, path, payload, "multishot_query", dry_run=ns.dry_run)
        elif ns.cmd == "cancel":
            payload = _invoke(root, path, payload, "multishot_cancel", dry_run=ns.dry_run)
        elif ns.cmd == "accept":
            payload = accept(root, path, payload, allow_qc_block=ns.allow_qc_block)
    print(json.dumps({"manifest": str(path), "payload": payload}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
