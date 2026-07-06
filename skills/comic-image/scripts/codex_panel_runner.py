#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Codex image_generation 为 comic panel_jobs.json 逐格生成 PNG。"""
from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


PNG_SIG = b"\x89PNG\r\n\x1a\n"
CODEX_MODEL = "OpenAI image_generation（Codex 内置）"
CODEX_CHANNEL = "Codex CLI"


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / "skills").is_dir() and (parent / "创作区").is_dir():
            return parent
    return start.resolve()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def png_valid(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 64 and path.read_bytes()[:8] == PNG_SIG
    except OSError:
        return False


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def codex_version() -> str:
    proc = subprocess.run(["codex", "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return (proc.stdout or proc.stderr or "codex unknown").strip().splitlines()[0]


def image_payload_from_jsonl(text: str) -> str:
    payload = ""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        data = event.get("payload") if isinstance(event, dict) else None
        if not isinstance(data, dict) or data.get("type") != "image_generation_end":
            continue
        result = data.get("result")
        if isinstance(result, str) and result.strip():
            payload = result.strip()
    return payload


def codex_thread_id(stdout: str) -> str:
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            return event["thread_id"]
    return ""


def codex_session_path(thread_id: str) -> Path | None:
    sessions = Path.home() / ".codex" / "sessions"
    if not thread_id or not sessions.is_dir():
        return None
    matches = list(sessions.glob(f"**/*{thread_id}.jsonl"))
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def write_image_payload(payload: str, out_path: Path) -> bool:
    if payload.startswith("data:"):
        payload = payload.split(",", 1)[-1]
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw)
    return png_valid(out_path)


def decode_image_event(stdout: str, out_path: Path) -> bool:
    payload = image_payload_from_jsonl(stdout)
    thread_id = codex_thread_id(stdout)
    if not payload and thread_id:
        session = codex_session_path(thread_id)
        if session and session.is_file():
            payload = image_payload_from_jsonl(session.read_text(encoding="utf-8", errors="ignore"))
    return write_image_payload(payload, out_path) if payload else False


def resize_png(path: Path, size: dict[str, int]) -> None:
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return
    width = int(size.get("width") or 0)
    height = int(size.get("height") or 0)
    if width <= 0 or height <= 0:
        return
    image = Image.open(path).convert("RGB")
    if image.size == (width, height):
        return
    fitted = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    fitted.save(path)


def build_prompt(job: dict[str, Any], chapter: str) -> str:
    size = job.get("size") or {}
    width = int(size.get("width") or 1296)
    height = int(size.get("height") or 900)
    return f"""请用内置 image_generation 工具生成一张漫画分格 PNG。

项目：《那妖魔是姜大人》漫画第1话《百妖谱》
面板：{job.get('panel_id')}
目标尺寸：{width}x{height}，长宽比约 {width / max(height, 1):.3f}

正向要求：
{job.get('prompt', '')}

负向要求：
{job.get('negative_prompt', '')}

硬性要求：
1. 只生成一张无字漫画画面，不要水印、logo、签名、字幕、中文、英文或乱码字。
2. 如果画面需要对白/旁白区域，只画干净空白气泡或留白，不要把台词画进图里。
3. 暗黑国风彩色条漫，电影感荒野，血色夕阳与冷青阴影，高反差但主体清晰。
4. 血腥只做叙事必要表现，避免内脏、碎尸或过度 gore 特写。
5. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
"""


def run_codex(prompt: str, root: Path, timeout_sec: int) -> subprocess.CompletedProcess[str]:
    cmd = [
        "codex",
        "exec",
        "--json",
        "--enable",
        "image_generation",
        "-s",
        "read-only",
        "-C",
        str(root),
        prompt,
    ]
    model = os.environ.get("COMIC_CODEX_MODEL")
    if model:
        cmd[2:2] = ["-m", model]
    return subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_sec,
    )


def format_failure(proc: subprocess.CompletedProcess[str]) -> str:
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    parts = []
    if stderr:
        parts.append("stderr=" + stderr[-2000:])
    if stdout:
        parts.append("stdout=" + stdout[-4000:])
    return f"codex exit {proc.returncode}: " + (" | ".join(parts) if parts else "no output")


def update_progress(root: Path, chapter: str, stage: str, value: str) -> None:
    path = root / "_进度.md"
    if not path.is_file():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    headers: list[str] = []
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and cells[0] == "话":
                headers = cells
            elif headers and len(cells) >= len(headers) and cells[0] == chapter and stage in headers:
                cells[headers.index(stage)] = value
                line = "| " + " | ".join(cells) + " |"
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def append_event(root: Path, row: dict[str, Any]) -> None:
    path = root / "生产数据" / "comic_image_generation.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def selected_jobs(jobs: list[dict], targets: set[str], limit: int) -> list[dict]:
    pending = []
    for job in jobs:
        if targets and job.get("panel_id") not in targets:
            continue
        if job.get("status") == "ready" and job.get("result_path"):
            continue
        pending.append(job)
    return pending[:limit] if limit > 0 else pending


def all_ready(root: Path, jobs: list[dict]) -> bool:
    for job in jobs:
        rel = job.get("result_path")
        if job.get("status") != "ready" or not rel or not png_valid(root / rel):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="用 Codex 生成 comic panel PNG")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--targets", default="", help="逗号分隔 panel_id；默认全部未完成")
    parser.add_argument("--limit", type=int, default=0, help="最多生成多少张；0 表示不限")
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument("--no-resize", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    jobs_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    data = load_json(jobs_path)
    data["model"] = CODEX_MODEL
    data["channel"] = CODEX_CHANNEL
    targets = {item.strip() for item in args.targets.split(",") if item.strip()}
    jobs = selected_jobs(data.get("jobs") or [], targets, args.limit)
    if not jobs:
        print("[ok] no pending jobs")
        return 0
    if not shutil.which("codex"):
        print("[err] codex not found in PATH", file=sys.stderr)
        return 2
    backend_version = codex_version()
    panel_dir = root / "出图" / args.chapter / "panels"
    failures = 0
    for job in jobs:
        pid = job.get("panel_id")
        final = panel_dir / f"{pid}.png"
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix=f"comic-codex-{pid}-") as tmp:
            temp_path = Path(tmp) / f"{pid}.png"
            prompt = build_prompt(job, args.chapter)
            proc = run_codex(prompt, repo, args.timeout_sec)
            error = ""
            if proc.returncode != 0:
                error = format_failure(proc)
            elif not decode_image_event(proc.stdout, temp_path):
                error = "codex completed but no image_generation_end payload was available"
            if error:
                failures += 1
                job["status"] = "failed"
                job["error"] = error
                append_event(root, {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "panel_id": pid,
                    "status": "failed",
                    "backend": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "error": error,
                    "duration_sec": round(time.monotonic() - started, 2),
                })
                print(f"[fail] {pid}: {error}", file=sys.stderr)
                write_json(jobs_path, data)
                continue
            if not args.no_resize:
                resize_png(temp_path, job.get("size") or {})
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temp_path, final)
            rel = str(final.relative_to(root))
            job.update(
                {
                    "status": "ready",
                    "result_path": rel,
                    "source": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                    "backend_version": backend_version,
                    "artifact_sha256": file_sha256(final),
                }
            )
            job.pop("error", None)
            append_event(root, {
                "ts": job["generated_at"],
                "panel_id": pid,
                "status": "ready",
                "backend": CODEX_CHANNEL,
                "model": CODEX_MODEL,
                "path": rel,
                "sha256": job["artifact_sha256"],
                "duration_sec": round(time.monotonic() - started, 2),
                "backend_version": backend_version,
            })
            write_json(jobs_path, data)
            print(f"[ok] {pid} -> {rel}")
    if all_ready(root, data.get("jobs") or []):
        update_progress(root, args.chapter, "出图", "✅")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
