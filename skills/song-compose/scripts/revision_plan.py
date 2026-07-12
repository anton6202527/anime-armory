#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn structured listening notes into non-destructive revision jobs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date
from typing import Any


KIND = "song_revision_plan"
LOCAL_EDIT_BACKENDS = {"ace-step", "ace-step v1.5", "acestep"}


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seconds(value: str) -> float | None:
    match = re.fullmatch(r"(?:(\d+):)?(\d+(?:\.\d+)?)", value.strip())
    if not match:
        return None
    return int(match.group(1) or 0) * 60 + float(match.group(2))


def time_range(value: str) -> tuple[float | None, float | None]:
    parts = [item.strip() for item in value.split("-", 1)]
    start = seconds(parts[0]) if parts and parts[0] else None
    end = seconds(parts[1]) if len(parts) > 1 else None
    if start is not None and end is None:
        return max(0.0, start - 3.0), start + 3.0
    return start, end


def build(root: str, take_id: str = "", backend: str = "") -> dict[str, Any]:
    manifest = load_json(os.path.join(root, "歌", "takes_manifest.json"), {}) or {}
    review = load_json(os.path.join(root, "歌", "take_review.json"), {}) or {}
    take_id = take_id or review.get("recommended_take") or manifest.get("selected_take") or ""
    take = next((row for row in manifest.get("takes", []) if row.get("take_id") == take_id), {})
    review_row = next((row for row in review.get("reviews", []) if row.get("take_id") == take_id), {})
    backend = backend or take.get("backend") or manifest.get("backend") or "manual"
    audio_rel = str(take.get("audio_path") or "")
    audio_path = os.path.join(root, audio_rel)
    jobs = []
    for index, note in enumerate(review_row.get("timecode_notes") or [], 1):
        if str(note.get("status") or "open").lower() in {"resolved", "accepted", "fixed", "已解决", "接受"}:
            continue
        start, end = time_range(str(note.get("timecode") or ""))
        interval = (end - start) if start is not None and end is not None else None
        can_repaint = backend.lower() in LOCAL_EDIT_BACKENDS and interval is not None and 3.0 <= interval <= 90.0
        jobs.append({
            "job_id": f"revision_{index:02d}",
            "source_take": take_id,
            "source_audio_path": audio_rel,
            "source_audio_sha256": sha256_file(audio_path) if os.path.isfile(audio_path) else "",
            "backend": backend,
            "task_type": "repaint" if can_repaint else "text2music_regenerate",
            "repainting_start": round(start, 3) if can_repaint else None,
            "repainting_end": round(end, 3) if can_repaint else None,
            "instruction": str(note.get("note") or "修复试听问题"),
            "severity": note.get("severity") or "note",
            "status": "planned",
            "fallback_reason": "" if can_repaint else "后端无 repaint 或区间不在 ACE-Step 3-90 秒范围内",
            "output_rule": "输出必须登记为新 take；不得覆盖原 take 或当前 pre-master。",
        })
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "take_id": take_id,
        "backend": backend,
        "jobs": jobs,
        "next_action": "执行 revision jobs -> 作为新 take 登记 -> 重跑盲听与 select gate",
    }


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "歌")
    os.makedirs(out_dir, exist_ok=True)
    json_path, md_path = os.path.join(out_dir, "revision_jobs.json"), os.path.join(out_dir, "revision_jobs.md")
    with open(json_path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(json_path + ".tmp", json_path)
    lines = ["# Song Revision Jobs", "", f"- take: {report.get('take_id')}", f"- backend: {report.get('backend')}", ""]
    for job in report.get("jobs") or []:
        lines.extend([f"## {job['job_id']}", f"- task: {job['task_type']}", f"- range: {job.get('repainting_start')} - {job.get('repainting_end')}", f"- instruction: {job['instruction']}", f"- rule: {job['output_rule']}", ""])
    with open(md_path + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    os.replace(md_path + ".tmp", md_path)
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="把试听 timecode 问题编排成局部返修/重生成任务")
    ap.add_argument("project_root")
    ap.add_argument("--take", default="")
    ap.add_argument("--backend", default="")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    report = build(root, args.take, args.backend)
    if args.write:
        print("[ok] revision jobs -> " + " / ".join(write_report(root, report)))
    if args.json or not args.write:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
