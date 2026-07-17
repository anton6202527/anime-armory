#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用即梦官方 CLI 为 comic panel_jobs.json 逐格生成 PNG。"""
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
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from codex_panel_runner import (  # noqa: E402
    all_ready,
    anatomy_guidance,
    append_event,
    archive_existing,
    collect_reference_images,
    file_sha256,
    load_json,
    missing_reference_ids,
    png_valid,
    post_qc_panel,
    rel_to_root,
    resize_png,
    run_preflight_gate,
    selected_jobs,
    update_progress,
    validate_compiled_job,
    validate_gate_receipt,
    write_gate_waiver,
    write_json,
)


DREAMINA_MODEL = "Seedream 5.0"
DREAMINA_CHANNEL = "Dreamina/即梦官方 CLI"
DREAMINA_MODEL_VERSION = "5.0"
DREAMINA_REFERENCE_LIMIT = 10
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
SUPPORTED_RATIOS = ("21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16")


def closest_ratio(width: int, height: int) -> str:
    target = max(1, width) / max(1, height)

    def distance(raw: str) -> float:
        left, right = (int(item) for item in raw.split(":", 1))
        return abs(target - left / right)

    return min(SUPPORTED_RATIOS, key=distance)


def submit_id_from(text: str) -> str:
    patterns = (
        r'"submit_id"\s*:\s*"([^"]+)"',
        r"submit_id\s*[=:]\s*([A-Za-z0-9._-]+)",
        r"submit id\s*[=:]\s*([A-Za-z0-9._-]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return ""


def json_payload_from(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def image_candidates(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    candidates: list[Path] = []
    for suffix in IMAGE_EXTS:
        candidates.extend(path.rglob(f"*{suffix}"))
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates


def materialize_png(src: Path, out_path: Path) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".png":
        shutil.copy2(src, out_path)
        return png_valid(out_path)
    try:
        from PIL import Image

        Image.open(src).convert("RGB").save(out_path)
        return png_valid(out_path)
    except Exception:
        return False


def dreamina_version() -> str:
    proc = subprocess.run(
        ["dreamina", "--version"],
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    payload = json_payload_from(proc.stdout or "")
    version = str(payload.get("version") or "").strip()
    return version or (proc.stdout or proc.stderr or "dreamina unknown").strip().splitlines()[-1]


def build_prompt(job: dict[str, Any], reference_count: int) -> str:
    validate_compiled_job(job, expected_backend=f"{DREAMINA_MODEL} {DREAMINA_CHANNEL}")
    submit_prompt = str(job.get("submit_prompt") or "").strip()
    negative_prompt = str(job.get("negative_prompt") or "").strip()
    reference_line = (
        f"本次已附入 {reference_count} 张真实参考图；严格按角色、场景、道具和画风参考保持一致，"
        "参考图中的平台 UI、水印和文字一律不继承。"
        if reference_count
        else "本格没有图片参考，仅按画面合同生成。"
    )
    negative_line = f"\n独立负向约束：{negative_prompt}" if negative_prompt else ""
    return (
        f"{submit_prompt}{negative_line}\n"
        f"{reference_line}\n"
        "安全呈现：这是非血腥奇幻漫画；用衣物遮挡、剪影、黑色墨气、暗红布片与冲击线表达因果，"
        "禁止可见伤口、穿刺断面、体液、残肢或写实痛苦特写。\n"
        f"人体和接触点补充：\n{anatomy_guidance(job)}\n"
        "只生成一个铺满画布的完整单格，不要外框、截图边、画中画、内部多面板或拼贴；"
        "不生成可读文字、气泡、文字框、字幕、Logo、水印或平台 UI。"
    )


def write_reference_manifest(
    root: Path,
    chapter: str,
    panel_id: str,
    records: list[dict[str, str]],
) -> Path:
    path = root / "生产数据" / "dreamina_reference_bundles" / chapter / f"{panel_id}.json"
    payload = {
        "schema_version": 1,
        "kind": "comic_dreamina_reference_bundle",
        "chapter": chapter,
        "panel_id": panel_id,
        "model": DREAMINA_MODEL,
        "channel": DREAMINA_CHANNEL,
        "reference_input_mode": "dreamina_official_cli_image2image",
        "reference_attachment_limit": DREAMINA_REFERENCE_LIMIT,
        "reference_input_count": len(records),
        "references": [
            {key: value for key, value in record.items() if key != "abs_path"}
            for record in records
        ],
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    write_json(path, payload)
    return path


def run_dreamina(
    prompt: str,
    reference_paths: list[Path],
    temp_png: Path,
    *,
    ratio: str,
    resolution_type: str,
    model_version: str,
    poll_sec: int,
    timeout_sec: int,
) -> tuple[bool, str, dict[str, Any], str]:
    download_dir = temp_png.parent / "download"
    download_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["dreamina", "image2image" if reference_paths else "text2image"]
    if reference_paths:
        # Dreamina CLI exposes images as one StringSlice flag; comma separation
        # is the stable multi-reference form used by the official CLI.
        cmd.extend(["--images", ",".join(str(path) for path in reference_paths)])
    cmd.extend(
        [
            "--prompt",
            prompt,
            "--ratio",
            ratio,
            "--resolution_type",
            resolution_type,
            "--model_version",
            model_version,
            "--poll",
            str(max(0, min(poll_sec, timeout_sec))),
        ]
    )
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return False, "", {}, f"dreamina submit timed out after {timeout_sec}s"
    combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    payload = json_payload_from(proc.stdout or "")
    submit_id = str(payload.get("submit_id") or submit_id_from(combined))
    if proc.returncode != 0:
        return False, submit_id, payload, f"dreamina submit exit {proc.returncode}: {combined[-4000:]}"
    if not submit_id:
        return False, "", payload, f"dreamina output did not include submit_id: {combined[-2000:]}"

    try:
        query = subprocess.run(
            ["dreamina", "query_result", "--submit_id", submit_id, "--download_dir", str(download_dir)],
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return False, submit_id, payload, f"dreamina query_result timed out after {timeout_sec}s"
    qout = "\n".join(part for part in (query.stdout, query.stderr) if part)
    query_payload = json_payload_from(query.stdout or "")
    if query_payload:
        payload = {**payload, **query_payload}
    if query.returncode != 0:
        return False, submit_id, payload, f"dreamina query_result exit {query.returncode}: {qout[-4000:]}"
    candidates = image_candidates(download_dir)
    if not candidates:
        return False, submit_id, payload, f"dreamina query_result downloaded no image files: {qout[-2000:]}"
    if not materialize_png(candidates[0], temp_png):
        return False, submit_id, payload, f"downloaded result is not a valid image: {candidates[0]}"
    return True, submit_id, payload, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="用即梦官方 CLI 生成 comic panel PNG")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--targets", default="", help="逗号分隔 panel_id；默认全部未完成")
    parser.add_argument("--limit", type=int, default=0, help="最多生成多少张；0 表示不限")
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--force", action="store_true", help="强制重抽；旧正式图归档到 candidates/")
    parser.add_argument("--allow-missing-refs", action="store_true")
    parser.add_argument("--model-version", default=DREAMINA_MODEL_VERSION)
    parser.add_argument("--resolution-type", choices=("2k", "4k"), default="2k")
    parser.add_argument("--poll-sec", type=int, default=180)
    parser.add_argument("--timeout-sec", type=int, default=600)
    parser.add_argument("--no-resize", action="store_true")
    parser.add_argument("--no-post-qc", action="store_true")
    parser.add_argument("--continue-on-qc-block", action="store_true")
    parser.add_argument("--skip-gate", action="store_true")
    parser.add_argument("--waiver-reason", default="")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    jobs_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    if not jobs_path.is_file():
        print(f"[err] missing panel jobs: {jobs_path}", file=sys.stderr)
        return 2
    if args.skip_gate:
        receipt = validate_gate_receipt(root, args.chapter, jobs_path)
        if receipt.get("status") == "current_pass":
            print(f"[ok] --skip-gate 复用当前 pass receipt：{receipt['path']}", flush=True)
        elif not args.waiver_reason.strip():
            print("[err] --skip-gate 必须提供 --waiver-reason 并留下持久审计记录", file=sys.stderr)
            return 2
        else:
            waiver = write_gate_waiver(
                root, args.chapter, jobs_path, args.waiver_reason, args.targets, receipt
            )
            print(f"[warn] --skip-gate 显式豁免已留痕：{rel_to_root(root, waiver)}", flush=True)
    elif run_preflight_gate(root, args.chapter) != 0:
        return 2

    if not shutil.which("dreamina"):
        print("[err] dreamina not found in PATH", file=sys.stderr)
        return 2
    data = load_json(jobs_path)
    if str(data.get("model") or "") != DREAMINA_MODEL or str(data.get("channel") or "") != DREAMINA_CHANNEL:
        print(
            f"[err] panel jobs backend mismatch: {data.get('model')} / {data.get('channel')}; "
            "先用 comic-settings 切换并重建 panel_jobs",
            file=sys.stderr,
        )
        return 2
    targets = {item.strip() for item in args.targets.split(",") if item.strip()}
    jobs = selected_jobs(data.get("jobs") or [], targets, args.limit, args.force)
    if not jobs:
        print("[ok] no pending jobs")
        return 0
    if not args.allow_missing_refs:
        missing = {str(job.get("panel_id")): missing_reference_ids(root, job) for job in jobs}
        missing = {pid: refs for pid, refs in missing.items() if refs}
        if missing:
            for pid, refs in missing.items():
                print(f"[err] {pid} missing shared references: {', '.join(refs)}", file=sys.stderr)
            return 2

    backend_version = dreamina_version()
    panel_dir = root / "出图" / args.chapter / "panels"
    candidate_root = root / "出图" / args.chapter / "candidates"
    failures = 0
    qc_blocked = 0
    max_attempts = max(1, args.max_attempts)
    for job in jobs:
        pid = str(job.get("panel_id") or "")
        final = panel_dir / f"{pid}.png"
        records = collect_reference_images(root, job)
        if len(records) > DREAMINA_REFERENCE_LIMIT:
            print(f"[err] {pid} references={len(records)} exceeds Dreamina limit=10", file=sys.stderr)
            return 2
        manifest = write_reference_manifest(root, args.chapter, pid, records)
        archived_existing = ""
        should_archive_existing = png_valid(final) and (
            args.force
            or job.get("status") != "ready"
            or job.get("model") != DREAMINA_MODEL
            or job.get("source") != DREAMINA_CHANNEL
        )
        size = job.get("size") or {}
        ratio = closest_ratio(int(size.get("width") or 1), int(size.get("height") or 1))
        prompt = build_prompt(job, len(records))
        started = time.monotonic()
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            with tempfile.TemporaryDirectory(prefix=f"comic-dreamina-{pid}-") as temp:
                temp_png = Path(temp) / f"{pid}.png"
                ok, submit_id, payload, error = run_dreamina(
                    prompt,
                    [Path(record["abs_path"]) for record in records],
                    temp_png,
                    ratio=ratio,
                    resolution_type=args.resolution_type,
                    model_version=args.model_version,
                    poll_sec=args.poll_sec,
                    timeout_sec=args.timeout_sec,
                )
                if not ok:
                    last_error = error
                    append_event(
                        root,
                        {
                            "ts": dt.datetime.now().isoformat(timespec="seconds"),
                            "panel_id": pid,
                            "status": "attempt_failed",
                            "backend": DREAMINA_CHANNEL,
                            "model": DREAMINA_MODEL,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "submit_id": submit_id,
                            "reference_manifest": rel_to_root(root, manifest),
                            "reference_input_count": len(records),
                            "error": error,
                            "duration_sec": round(time.monotonic() - started, 2),
                        },
                    )
                    print(f"[retry] {pid} attempt {attempt}/{max_attempts}: {error}", file=sys.stderr, flush=True)
                    continue
                if not args.no_resize:
                    resize_png(temp_png, size)
                if should_archive_existing and not archived_existing:
                    archived_existing = archive_existing(
                        final, candidate_root / pid, "previous_backend_or_take"
                    )
                final.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_png, final)
                post_qc = (
                    {}
                    if args.no_post_qc
                    else post_qc_panel(root, args.chapter, job, final, records, [])
                )
                verdict = str(post_qc.get("verdict") or "skipped")
                status = "qc_block" if verdict == "block" else "ready"
                generated_at = dt.datetime.now().isoformat(timespec="seconds")
                history = job.get("history") if isinstance(job.get("history"), list) else []
                if archived_existing:
                    history.append(
                        {
                            "kind": "archived_previous",
                            "path": rel_to_root(root, Path(archived_existing)),
                        }
                    )
                job.update(
                    {
                        "status": status,
                        "result_path": rel_to_root(root, final),
                        "source": DREAMINA_CHANNEL,
                        "model": DREAMINA_MODEL,
                        "model_version": args.model_version,
                        "backend_version": backend_version,
                        "generated_at": generated_at,
                        "artifact_sha256": file_sha256(final),
                        "attempt": attempt,
                        "submit_id": submit_id,
                        "credit_count": payload.get("credit_count"),
                        "dreamina_ratio": ratio,
                        "resolution_type": args.resolution_type,
                        "reference_input_mode": "dreamina_official_cli_image2image" if records else "dreamina_official_cli_text2image",
                        "reference_input_count": len(records),
                        "reference_manifest": rel_to_root(root, manifest),
                        "generated_from_contract_sha256": str(job.get("source_contract_sha256") or ""),
                        "generated_from_submit_prompt_sha256": str(job.get("submit_prompt_sha256") or ""),
                        "generated_from_execution_input_sha256": str(job.get("execution_input_sha256") or ""),
                        "post_qc": post_qc,
                    }
                )
                if history:
                    job["history"] = history[-10:]
                job.pop("error", None)
                append_event(
                    root,
                    {
                        "ts": generated_at,
                        "panel_id": pid,
                        "status": status,
                        "backend": DREAMINA_CHANNEL,
                        "model": DREAMINA_MODEL,
                        "model_version": args.model_version,
                        "path": job["result_path"],
                        "sha256": job["artifact_sha256"],
                        "submit_id": submit_id,
                        "credit_count": payload.get("credit_count"),
                        "reference_manifest": rel_to_root(root, manifest),
                        "reference_input_count": len(records),
                        "post_qc_verdict": verdict,
                        "duration_sec": round(time.monotonic() - started, 2),
                        "backend_version": backend_version,
                    },
                )
                write_json(jobs_path, data)
                print(
                    f"[ok] {pid} -> {job['result_path']} submit_id={submit_id} "
                    f"(attempt {attempt}/{max_attempts}, ratio={ratio}, post_qc={verdict})",
                    flush=True,
                )
                if verdict == "block":
                    qc_blocked += 1
                    if not args.continue_on_qc_block:
                        return 3
                break
        else:
            failures += 1
            job["status"] = "failed"
            job["error"] = last_error
            write_json(jobs_path, data)
            print(f"[fail] {pid}: {last_error}", file=sys.stderr, flush=True)

    if all_ready(root, data.get("jobs") or []):
        update_progress(root, args.chapter, "出图", "✅")
    if qc_blocked:
        return 3
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
