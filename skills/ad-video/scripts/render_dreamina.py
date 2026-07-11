#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render ad-video jobs through the official Dreamina CLI.

Reads 出视频/分镜/video_jobs_manifest.json, calls either `dreamina frames2video`
or `dreamina image2video`, downloads the resulting MP4 to expected_output, and
records provenance. This script uses only the official Dreamina CLI path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence


KEY_SECTIONS = (
    "上游视觉契约",
    "画面连续性",
    "运镜与动作",
    "产品/品牌身份锁定",
    "文字与安全区",
    "负向",
)

AD_LIB = Path(__file__).resolve().parents[2] / "ad" / "_lib"
if str(AD_LIB) not in sys.path:
    sys.path.insert(0, str(AD_LIB))
from ad_video_prompt_compiler import parse_markdown  # noqa: E402
from ad_video_prompt_compiler import normalize_backend  # noqa: E402
SUCCESS_STATUSES = {"success", "succeeded", "completed", "done"}
PENDING_STATUSES = {"querying", "queueing", "queued", "processing", "running", "pending", "submitted", "created"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")


def extract_sections(markdown: str, wanted: Iterable[str] = KEY_SECTIONS) -> Dict[str, str]:
    wanted_set = set(wanted)
    sections: Dict[str, list[str]] = {}
    current: Optional[str] = None
    for raw in markdown.splitlines():
        if raw.startswith("## "):
            heading = raw[3:].strip()
            current = heading if heading in wanted_set else None
            if current:
                sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(raw)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def build_prompt(prompt_file: Path) -> str:
    text = prompt_file.read_text(encoding="utf-8")
    compiled = parse_markdown(text)
    if compiled and str(compiled.get("prompt") or "").strip():
        return str(compiled["prompt"]).strip()
    raise RuntimeError("缺后端编译提交 prompt；拒绝把完整生产合同回退提交给模型")


def submit_duration(seconds: float, model_version: str) -> int:
    """Dreamina video duration is integer seconds; Seedance family supports 4-15s."""
    dur = int(math.ceil(float(seconds or 4.0)))
    model = (model_version or "").lower()
    if "seedance2.0" in model or model == "seedance2.0fast":
        return max(4, min(15, dur))
    if "3.5" in model:
        return max(4, min(12, dur))
    return max(3, min(10, dur))


def _find_media_url(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        for key in ("video_url", "video", "url", "download_url", "media_url"):
            raw = value.get(key)
            if isinstance(raw, str) and raw.startswith(("http://", "https://")):
                return raw
        for item in value.values():
            found = _find_media_url(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_media_url(item)
            if found:
                return found
    return None


def run_dreamina_video(
    job: Mapping[str, Any],
    root: Path,
    *,
    model_version: str,
    video_resolution: str,
    poll: int,
) -> Dict[str, Any]:
    mode = str(job.get("mode") or "image2video")
    prompt = build_prompt(root / str(job.get("prompt")))
    duration = submit_duration(float(job.get("duration") or 4.0), model_version)
    cmd = ["dreamina", mode, "--prompt", prompt, "--duration", str(duration),
           "--video_resolution", video_resolution, "--model_version", model_version, "--poll", str(poll)]
    if mode == "frames2video":
        cmd.extend(["--first", str(root / str(job.get("first_frame"))),
                    "--last", str(root / str(job.get("end_frame")))])
    elif mode == "image2video":
        cmd.extend(["--image", str(root / str(job.get("first_frame")))])
    else:
        raise RuntimeError(f"unsupported video mode: {mode}")
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"dreamina {mode} failed")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"dreamina returned non-JSON output: {exc}") from exc
    status = str(payload.get("gen_status") or payload.get("status") or "").lower()
    if status and status not in SUCCESS_STATUSES:
        submit_id = str(payload.get("submit_id") or "")
        if submit_id:
            try:
                checked = query_dreamina_result(submit_id)
                checked.setdefault("submit_id", submit_id)
                checked.setdefault("credit_count", payload.get("credit_count"))
                checked["_submitted_duration"] = duration
                checked["_mode"] = mode
                return checked
            except Exception:
                if status in PENDING_STATUSES:
                    payload["_pending_status"] = status
                else:
                    raise RuntimeError(f"dreamina task not successful: {status}; submit_id={submit_id}")
        elif status in PENDING_STATUSES:
            payload["_pending_status"] = status
        else:
            raise RuntimeError(f"dreamina task not successful: {status}; submit_id={payload.get('submit_id')}")
    payload["_submitted_duration"] = duration
    payload["_mode"] = mode
    return payload


def query_dreamina_result(submit_id: str) -> Dict[str, Any]:
    proc = subprocess.run(["dreamina", "query_result", "--submit_id", submit_id], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "dreamina query_result failed")
    payload = load_json_from_text(proc.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("dreamina query_result returned non-JSON object")
    status = str(payload.get("gen_status") or payload.get("status") or "").lower()
    if status and status not in SUCCESS_STATUSES:
        if status in PENDING_STATUSES:
            payload["_pending_status"] = status
        else:
            raise RuntimeError(f"dreamina task not successful: {status}; submit_id={submit_id}")
    return payload


def download_url(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as resp:
        data = resp.read()
    if len(data) < 100_000:
        raise RuntimeError(f"download too small: {target} bytes={len(data)}")
    target.write_bytes(data)


def download_via_query(submit_id: str, target: Path) -> None:
    dl_dir = target.parent / ".dreamina_downloads" / submit_id
    dl_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["dreamina", "query_result", "--submit_id", submit_id, "--download_dir", str(dl_dir)],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "dreamina query_result failed")
    candidates = sorted(dl_dir.glob("*.mp4"), key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
    if not candidates:
        payload = load_json_from_text(proc.stdout)
        url = _find_media_url(payload)
        if url:
            download_url(url, target)
            return
        raise RuntimeError(f"query_result downloaded no mp4 for submit_id={submit_id}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidates[0], target)


def load_json_from_text(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return {}


def download_result(payload: Mapping[str, Any], target: Path) -> None:
    url = _find_media_url(payload.get("result_json") or payload)
    if url:
        download_url(url, target)
        return
    submit_id = str(payload.get("submit_id") or "")
    if not submit_id:
        raise RuntimeError("dreamina result has no video URL or submit_id")
    download_via_query(submit_id, target)
    if target.stat().st_size < 100_000:
        raise RuntimeError(f"download too small: {target} bytes={target.stat().st_size}")


def job_matches(job: Mapping[str, Any], only: set[str]) -> bool:
    if not only:
        return True
    keys = {str(job.get("job_id") or ""), str(job.get("clip") or ""), Path(str(job.get("prompt") or "")).stem}
    return bool(keys & only)


def enforce_gate(root: Path) -> None:
    gate_cmd = [sys.executable, str(Path(__file__).resolve().parents[2] / "ad-craft" / "scripts" / "gate.py"),
                str(root), "--stage", "video"]
    gate = subprocess.run(gate_cmd, text=True)
    if gate.returncode:
        raise RuntimeError("ad video gate blocked paid generation")


def render_jobs(
    root: Path,
    *,
    only: set[str],
    limit: Optional[int],
    force: bool,
    model_version: str,
    video_resolution: str,
    poll: int,
    submit_only: bool = False,
    collect_only: bool = False,
) -> Dict[str, Any]:
    root = root.resolve()
    if not collect_only:
        enforce_gate(root)
    manifest_path = root / "出视频" / "分镜" / "video_jobs_manifest.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise FileNotFoundError(f"缺 video_jobs_manifest.json: {manifest_path}")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list):
        raise RuntimeError("video_jobs_manifest.json 缺 jobs[]")
    rendered = skipped = failed = submitted = pending = 0
    events_path = root / "生产数据" / "production_events.jsonl"
    for job in jobs:
        if not isinstance(job, dict) or not job_matches(job, only):
            continue
        if limit is not None and rendered >= limit:
            break
        target = root / str(job.get("expected_output"))
        if target.exists() and not force:
            job["status"] = "done"
            job.setdefault("backend", "Dreamina/即梦官方 CLI")
            job.setdefault("output", str(job.get("expected_output")))
            skipped += 1
            continue
        existing_submit_id = str(job.get("submit_id") or "")
        if existing_submit_id and not force:
            try:
                payload = query_dreamina_result(existing_submit_id)
                if payload.get("_pending_status"):
                    job["status"] = "submitted"
                    job["pending_status"] = payload.get("_pending_status")
                    pending += 1
                    print(f"[pending] {job.get('job_id')} submit_id={existing_submit_id} status={payload.get('_pending_status')}", flush=True)
                    continue
                download_result(payload, target)
                job.update({
                    "status": "done",
                    "backend": "Dreamina/即梦官方 CLI",
                    "model_version": model_version,
                    "video_resolution": video_resolution,
                    "output": str(job.get("expected_output")),
                    "generated_at": now_iso(),
                })
                rendered += 1
                print(f"[ok] {job.get('job_id')} -> {job.get('expected_output')} submit_id={existing_submit_id}", flush=True)
                continue
            except Exception as exc:
                if collect_only:
                    pending += 1
                    job["status"] = "submitted"
                    job["last_query_error"] = str(exc)
                    print(f"[pending] {job.get('job_id')} query_error={exc}", flush=True)
                    continue
                failed += 1
                job["status"] = "failed"
                job["error"] = str(exc)
                print(f"[block] {job.get('job_id')} {exc}", file=sys.stderr, flush=True)
                if not force:
                    break
                continue
        if collect_only:
            pending += 1
            job.setdefault("status", "planned")
            print(f"[pending] {job.get('job_id')} no submit_id yet", flush=True)
            continue
        try:
            prompt_path = root / str(job.get("prompt") or "")
            if not prompt_path.is_file():
                raise RuntimeError(f"缺 prompt：{prompt_path}")
            actual_prompt_sha = hashlib.sha256(build_prompt(prompt_path).encode("utf-8")).hexdigest()
            expected_prompt_sha = str(job.get("submit_prompt_sha256") or "")
            if expected_prompt_sha and actual_prompt_sha != expected_prompt_sha:
                raise RuntimeError("模型提交 prompt 已变更但 manifest 未重建")
            for frame_key in ("first_frame", "end_frame"):
                rel = job.get(frame_key)
                if rel and not (root / str(rel)).is_file():
                    raise RuntimeError(f"缺真实输入帧：{rel}")
            expected_backend = normalize_backend(((job.get("route") or {}).get("primary")))
            actual_backend = "seedance" if "seedance" in model_version.lower() else "dreamina"
            if expected_backend not in {actual_backend, "generic"}:
                raise RuntimeError(f"路由 primary={expected_backend} 与 Dreamina runner 实际模型={actual_backend} 不一致")
            payload = run_dreamina_video(
                job,
                root,
                model_version=model_version,
                video_resolution=video_resolution,
                poll=0 if submit_only else poll,
            )
            if payload.get("_pending_status"):
                job.update({
                    "status": "submitted",
                    "pending_status": payload.get("_pending_status"),
                    "backend": "Dreamina/即梦官方 CLI",
                    "model_version": model_version,
                    "video_resolution": video_resolution,
                    "submit_id": payload.get("submit_id"),
                    "credit_count": payload.get("credit_count"),
                    "submitted_duration": payload.get("_submitted_duration"),
                    "submitted_at": now_iso(),
                })
                append_jsonl(events_path, {
                    "ts": now_iso(),
                    "stage": "video",
                    "event": "submission",
                    "generation": {
                        "method": f"dreamina_official_cli_{payload.get('_mode')}",
                        "asset": str(job.get("expected_output")),
                        "prompt": str(job.get("prompt")),
                        "first_frame": str(job.get("first_frame")),
                        "end_frame": job.get("end_frame"),
                        "submit_id": payload.get("submit_id"),
                        "model_version": model_version,
                        "video_resolution": video_resolution,
                        "duration": payload.get("_submitted_duration"),
                        "credit_count": payload.get("credit_count"),
                        "pending_status": payload.get("_pending_status"),
                    },
                })
                submitted += 1
                print(f"[submitted] {job.get('job_id')} submit_id={payload.get('submit_id')} status={payload.get('_pending_status')}", flush=True)
                continue
            download_result(payload, target)
            job.update({
                "status": "done",
                "backend": "Dreamina/即梦官方 CLI",
                "model_version": model_version,
                "video_resolution": video_resolution,
                "actual_model_backend": actual_backend,
                "submit_id": payload.get("submit_id"),
                        "credit_count": payload.get("credit_count"),
                        "submit_prompt_sha256": actual_prompt_sha,
                "submitted_duration": payload.get("_submitted_duration"),
                "output": str(job.get("expected_output")),
                "generated_at": now_iso(),
            })
            append_jsonl(events_path, {
                "ts": now_iso(),
                "stage": "video",
                "event": "generation",
                "generation": {
                    "method": f"dreamina_official_cli_{payload.get('_mode')}",
                    "asset": str(job.get("expected_output")),
                    "prompt": str(job.get("prompt")),
                    "first_frame": str(job.get("first_frame")),
                    "end_frame": job.get("end_frame"),
                    "submit_id": payload.get("submit_id"),
                    "model_version": model_version,
                "video_resolution": video_resolution,
                "actual_model_backend": actual_backend,
                    "duration": payload.get("_submitted_duration"),
                    "credit_count": payload.get("credit_count"),
                    "submit_prompt_sha256": actual_prompt_sha,
                },
            })
            rendered += 1
            print(f"[ok] {job.get('job_id')} -> {job.get('expected_output')} submit_id={payload.get('submit_id')}", flush=True)
        except Exception as exc:
            failed += 1
            job["status"] = "failed"
            job["error"] = str(exc)
            print(f"[block] {job.get('job_id')} {exc}", file=sys.stderr, flush=True)
            if not force:
                break
        finally:
            write_json(manifest_path, manifest)
            time.sleep(0.2)
    manifest["render_summary"] = {
        "backend": "Dreamina/即梦官方 CLI",
        "model_version": model_version,
        "video_resolution": video_resolution,
        "rendered": rendered,
        "skipped": skipped,
        "submitted": submitted,
        "pending": pending,
        "failed": failed,
        "updated_at": now_iso(),
    }
    write_json(manifest_path, manifest)
    return manifest["render_summary"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Dreamina 官方 CLI 渲染广告逐镜视频 MP4")
    ap.add_argument("project_root")
    ap.add_argument("--only", nargs="*", default=[], help="job_id / 镜头NN / prompt stem")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model-version", default="seedance2.0fast")
    ap.add_argument("--video-resolution", default="720p")
    ap.add_argument("--poll", type=int, default=900)
    ap.add_argument("--submit-only", action="store_true", help="只提交并登记 submit_id，不等待下载")
    ap.add_argument("--collect-only", action="store_true", help="只查询已登记 submit_id 并下载完成结果，不提交新任务")
    ns = ap.parse_args(argv)
    try:
        summary = render_jobs(
            Path(ns.project_root),
            only=set(ns.only),
            limit=ns.limit,
            force=ns.force,
            model_version=ns.model_version,
            video_resolution=ns.video_resolution,
            poll=ns.poll,
            submit_only=ns.submit_only,
            collect_only=ns.collect_only,
        )
    except Exception as exc:
        print(f"[block] {exc}", file=sys.stderr, flush=True)
        return 2
    print(
        "# Dreamina video render "
        f"rendered={summary['rendered']} skipped={summary['skipped']} "
        f"submitted={summary['submitted']} pending={summary['pending']} failed={summary['failed']}",
        flush=True,
    )
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
