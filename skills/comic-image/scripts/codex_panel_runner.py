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
CODEX_MODEL = "GPT Image 2"
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


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def collect_reference_images(root: Path, job: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    seen: set[Path] = set()
    for ref in job.get("references") or []:
        if not isinstance(ref, dict):
            continue
        raw = str(ref.get("path") or "").strip()
        if not raw:
            continue
        path = resolve_path(root, raw)
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        records.append(
            {
                "id": str(ref.get("id") or path.stem),
                "path": rel_to_root(root, path),
                "abs_path": str(path),
                "sha256": file_sha256(path),
            }
        )
    return records


def missing_reference_ids(root: Path, job: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for ref in job.get("references") or []:
        if not isinstance(ref, dict):
            continue
        rid = str(ref.get("id") or "").strip()
        raw = str(ref.get("path") or "").strip()
        if not rid:
            continue
        if not raw or not resolve_path(root, raw).is_file():
            missing.append(rid)
    return missing


def write_reference_manifest(root: Path, chapter: str, panel_id: str, records: list[dict[str, str]]) -> Path:
    path = root / "生产数据" / "codex_reference_bundles" / chapter / f"{panel_id}.json"
    payload = {
        "schema_version": 1,
        "kind": "comic_codex_reference_bundle",
        "chapter": chapter,
        "panel_id": panel_id,
        "reference_input_mode": "codex_exec_image_flags",
        "cli_image_input_count": len(records),
        "references": [
            {key: value for key, value in record.items() if key != "abs_path"}
            for record in records
        ],
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    write_json(path, payload)
    return path


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


def likely_blank_bubble_regions(path: Path) -> list[dict[str, int]]:
    """Conservative hint for baked blank bubbles/text boxes in raw panel art."""
    try:
        from PIL import Image
    except ImportError:
        return []
    try:
        image = Image.open(path).convert("RGB")
    except OSError:
        return []

    src_w, src_h = image.size
    max_w = 420
    scale = min(1.0, max_w / max(src_w, 1))
    if scale < 1.0:
        image = image.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))))
    w, h = image.size
    pixels = image.load()
    mask = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            if r >= 238 and g >= 238 and b >= 230 and max(r, g, b) - min(r, g, b) <= 35:
                mask[y][x] = True

    seen = [[False] * w for _ in range(h)]
    regions: list[dict[str, int]] = []
    min_area = max(220, int(w * h * 0.003))
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            area = 0
            min_x = max_x = x
            min_y = max_y = y
            while stack:
                cx, cy = stack.pop()
                area += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            bw = max_x - min_x + 1
            bh = max_y - min_y + 1
            if area < min_area or bw < 30 or bh < 18:
                continue
            inv = 1.0 / scale if scale else 1.0
            regions.append(
                {
                    "x": int(min_x * inv),
                    "y": int(min_y * inv),
                    "w": int(bw * inv),
                    "h": int(bh * inv),
                    "area": int(area * inv * inv),
                }
            )
    return regions[:8]


def image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError:
        return (0, 0)
    try:
        with Image.open(path) as image:
            return image.size
    except OSError:
        return (0, 0)


def post_qc_panel(
    root: Path,
    chapter: str,
    job: dict[str, Any],
    path: Path,
    reference_records: list[dict[str, str]],
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    pid = str(job.get("panel_id") or path.stem)
    if not png_valid(path):
        issues.append(
            {
                "severity": "block",
                "category": "artifact",
                "reason": "generated file is missing or not a valid PNG",
            }
        )

    actual_w, actual_h = image_size(path)
    expected = job.get("size") or {}
    expected_w = int(expected.get("width") or 0)
    expected_h = int(expected.get("height") or 0)
    if expected_w > 0 and expected_h > 0 and (actual_w, actual_h) != (expected_w, expected_h):
        issues.append(
            {
                "severity": "warn",
                "category": "size",
                "reason": f"image size {actual_w}x{actual_h} differs from job size {expected_w}x{expected_h}",
            }
        )

    declared_refs = [ref for ref in job.get("references") or [] if isinstance(ref, dict) and ref.get("id")]
    if declared_refs and len(reference_records) < len(declared_refs):
        issues.append(
            {
                "severity": "block",
                "category": "reference",
                "reason": f"only {len(reference_records)} real reference inputs for {len(declared_refs)} declared references",
            }
        )

    blank_regions = likely_blank_bubble_regions(path)
    if blank_regions:
        issues.append(
            {
                "severity": "warn",
                "category": "baked_text_container",
                "reason": f"found {len(blank_regions)} likely blank white region(s); manually verify this is not a baked bubble",
            }
        )

    verdict = "pass"
    if any(issue["severity"] == "block" for issue in issues):
        verdict = "block"
    elif any(issue["severity"] == "warn" for issue in issues):
        verdict = "warn"

    payload = {
        "schema_version": 1,
        "kind": "comic_panel_post_qc",
        "chapter": chapter,
        "panel_id": pid,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "verdict": verdict,
        "path": rel_to_root(root, path),
        "size": {"width": actual_w, "height": actual_h},
        "expected_size": {"width": expected_w, "height": expected_h},
        "declared_reference_count": len(declared_refs),
        "reference_input_count": len(reference_records),
        "blank_region_candidates": blank_regions,
        "issues": issues,
        "manual_review_required": verdict != "pass",
    }
    out = root / "生产数据" / "panel_qc" / chapter / f"{pid}.json"
    write_json(out, payload)
    return payload


def archive_existing(path: Path, archive_dir: Path, reason: str) -> str:
    if not png_valid(path):
        return ""
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = archive_dir / f"{path.stem}_{ts}_{reason}.png"
    shutil.copy2(path, archived)
    return str(archived)


def build_prompt(job: dict[str, Any], project_name: str, chapter: str, reference_records: list[dict[str, str]]) -> str:
    size = job.get("size") or {}
    width = int(size.get("width") or 1296)
    height = int(size.get("height") or 900)
    if reference_records:
        ref_lines = "\n".join(
            f"- {record['id']}: 已作为 --image 附件传入，路径 {record['path']}"
            for record in reference_records
        )
    else:
        ref_lines = "- 无真实参考图附件；只按文字 prompt 生成"
    anatomy = anatomy_guidance(job)
    return f"""请用内置 image_generation 工具生成一张漫画分格 PNG。

项目：《{project_name}》漫画{chapter}
面板：{job.get('panel_id')}
目标尺寸：{width}x{height}，长宽比约 {width / max(height, 1):.3f}

已附共享参考图：
{ref_lines}

正向要求：
{job.get('prompt', '')}

负向要求：
{job.get('negative_prompt', '')}

人体与动作要求：
{anatomy}

硬性要求：
1. 已附参考图优先级高于文字；同一个 CHAR/MON/PROP/LOC/SYS 参考 ID 在所有面板中必须保持同一角色、同一妖物、同一道具或同一场景资产，不得换脸、换发型、换服装主色、换体型或换关键结构。
2. 多角色同框时，按参考 ID 分别锁定身份，不要把一个角色的脸、发型、衣服套到另一个角色身上。
3. 只生成一张无字漫画画面，不要水印、logo、签名、印章、角标、字幕、中文、英文或乱码字；画面四角必须干净，不能出现任何小字或作者署名。
4. 不要画对白气泡、空白气泡、旁白框、标题框或任何文字容器；如需要后期嵌字，只在不挡脸、不挡手脚、不挡关键道具的位置保留低细节留白区域，由 comic-compose 另行绘制气泡和文字。
5. 画面必须铺满整张画布，不要外框、截图边、白色斜线边、相框、胶片边、画中画边框、内部漫画分格线或拼贴式多面板版式；当前任务只输出一个完整面板。
6. 画风、题材、色彩和光效必须服从“正向要求”中的项目风格锚与当前面板事实，不要套用其它项目的默认风格。
7. 危险、受伤或压迫感只做叙事必要表现，避免内脏、碎尸或过度 gore 特写。
8. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
"""


def anatomy_guidance(job: dict[str, Any]) -> str:
    text = " ".join(str(job.get(key, "")) for key in ("panel_id", "prompt", "negative_prompt"))
    lines = [
        "- 人物最多两条手臂两只手；每只可见手必须自然连接同侧手腕、前臂、肘部和肩线。",
        "- 禁止额外手掌、漂浮断手、手从刀柄/地面/光效中长出、左右手归属互换、同一只手重复出现。",
    ]
    if any(token in text for token in ("脚", "足", "鞋", "腿", "膝", "踝", "脚尖", "脚步", "踩", "踏", "跪", "蹲", "踢")):
        lines.append(
            "- 本格含脚部/落点叙事：必须清楚显示脚/鞋/小腿和地面受力关系；禁止把脚画成手、用手掌替代脚掌、脚趾像手指，禁止把“脚前半步/脚尖僵住”画成手撑地。"
        )
    if any(token in text for token in ("刀", "剑", "武器", "横刀", "断刀", "握", "持", "劈", "斩", "刺")):
        lines.append("- 武器必须有明确握持或落点关系；刀柄、刀刃、手、脚和地面接触点不要穿模或融合。")
    return "\n".join(lines)


def run_codex(
    prompt: str,
    root: Path,
    timeout_sec: int,
    image_paths: list[Path],
    *,
    ignore_user_config: bool = False,
    ignore_rules: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        "codex",
        "exec",
        "--json",
        "--enable",
        "image_generation",
    ]
    if os.environ.get("COMIC_CODEX_DISABLE_RESPECT_SYSTEM_PROXY", "").lower() in {"1", "true", "yes"}:
        cmd.extend(["--disable", "respect_system_proxy"])
    if ignore_user_config:
        cmd.append("--ignore-user-config")
    if ignore_rules:
        cmd.append("--ignore-rules")
    for path in image_paths:
        cmd.extend(["--image", str(path)])
    cmd.extend(["-s", "read-only", "-C", str(root), prompt])
    model = os.environ.get("COMIC_CODEX_MODEL")
    if model:
        cmd[2:2] = ["-m", model]
    try:
        return subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stderr = (stderr + f"\ntimeout after {timeout_sec}s").strip()
        return subprocess.CompletedProcess(cmd, 124, stdout=stdout, stderr=stderr)


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


def selected_jobs(jobs: list[dict], targets: set[str], limit: int, force: bool) -> list[dict]:
    pending = []
    for job in jobs:
        if targets and job.get("panel_id") not in targets:
            continue
        if not force and job.get("status") == "ready" and job.get("result_path"):
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
    parser.add_argument("--max-attempts", type=int, default=1, help="每格最多尝试次数；适合预算充足时重试失败请求")
    parser.add_argument("--force", action="store_true", help="即使 job 已 ready 也重新生成；原图会归档到 candidates/")
    parser.add_argument("--allow-missing-refs", action="store_true", help="允许带 references 的格子在参考图缺失时继续文生图")
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument(
        "--ignore-user-config",
        action="store_true",
        help="不加载用户 Codex 配置/技能，用干净的 image_generation 子进程重试卡在说明文档输出的请求",
    )
    parser.add_argument(
        "--ignore-rules",
        action="store_true",
        help="不加载用户/项目 execpolicy 规则；用于继续隔离卡在说明文档输出的 Codex 子进程",
    )
    parser.add_argument("--no-resize", action="store_true")
    parser.add_argument("--no-post-qc", action="store_true", help="跳过每格落盘后的 deterministic QC 记录")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    jobs_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    data = load_json(jobs_path)
    data["model"] = CODEX_MODEL
    data["channel"] = CODEX_CHANNEL
    targets = {item.strip() for item in args.targets.split(",") if item.strip()}
    max_attempts = max(1, args.max_attempts)
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
            print("[err] seed or place shared reference images before generating panels, or pass --allow-missing-refs for a deliberate text-only run", file=sys.stderr)
            return 2
    if not shutil.which("codex"):
        print("[err] codex not found in PATH", file=sys.stderr)
        return 2
    backend_version = codex_version()
    panel_dir = root / "出图" / args.chapter / "panels"
    candidate_root = root / "出图" / args.chapter / "candidates"
    failures = 0
    for job in jobs:
        pid = job.get("panel_id")
        final = panel_dir / f"{pid}.png"
        archived_existing = archive_existing(final, candidate_root / str(pid), "previous") if args.force else ""
        started = time.monotonic()
        last_error = ""
        reference_records = collect_reference_images(root, job)
        reference_manifest = write_reference_manifest(root, args.chapter, str(pid), reference_records)
        reference_paths = [Path(record["abs_path"]) for record in reference_records]
        for attempt in range(1, max_attempts + 1):
            with tempfile.TemporaryDirectory(prefix=f"comic-codex-{pid}-") as tmp:
                temp_path = Path(tmp) / f"{pid}.png"
                prompt = build_prompt(job, root.name, args.chapter, reference_records)
                proc = run_codex(
                    prompt,
                    repo,
                    args.timeout_sec,
                    reference_paths,
                    ignore_user_config=args.ignore_user_config,
                    ignore_rules=args.ignore_rules,
                )
                error = ""
                if proc.returncode != 0:
                    error = format_failure(proc)
                elif not decode_image_event(proc.stdout, temp_path):
                    error = "codex completed but no image_generation_end payload was available"
                if error:
                    last_error = error
                    append_event(root, {
                        "ts": dt.datetime.now().isoformat(timespec="seconds"),
                        "panel_id": pid,
                        "status": "attempt_failed",
                        "backend": CODEX_CHANNEL,
                        "model": CODEX_MODEL,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "reference_manifest": rel_to_root(root, reference_manifest),
                        "reference_input_count": len(reference_records),
                        "reference_input_paths": [record["path"] for record in reference_records],
                        "error": error,
                        "duration_sec": round(time.monotonic() - started, 2),
                    })
                    print(f"[retry] {pid} attempt {attempt}/{max_attempts}: {error}", file=sys.stderr, flush=True)
                    continue
                if not args.no_resize:
                    resize_png(temp_path, job.get("size") or {})
                final.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_path, final)
                rel = str(final.relative_to(root))
                post_qc = {} if args.no_post_qc else post_qc_panel(root, args.chapter, job, final, reference_records)
                history = job.get("history") if isinstance(job.get("history"), list) else []
                if archived_existing:
                    history.append({"kind": "archived_previous", "path": archived_existing})
                job.update(
                    {
                        "status": "ready",
                        "result_path": rel,
                        "source": CODEX_CHANNEL,
                        "model": CODEX_MODEL,
                        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                        "backend_version": backend_version,
                        "artifact_sha256": file_sha256(final),
                        "attempt": attempt,
                        "reference_input_mode": "codex_exec_image_flags",
                        "reference_input_count": len(reference_records),
                        "reference_manifest": rel_to_root(root, reference_manifest),
                        "post_qc": post_qc,
                    }
                )
                if history:
                    job["history"] = history[-10:]
                job.pop("error", None)
                append_event(root, {
                    "ts": job["generated_at"],
                    "panel_id": pid,
                    "status": "ready",
                    "backend": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "path": rel,
                    "sha256": job["artifact_sha256"],
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "reference_manifest": rel_to_root(root, reference_manifest),
                    "reference_input_count": len(reference_records),
                    "reference_input_paths": [record["path"] for record in reference_records],
                    "post_qc_verdict": post_qc.get("verdict") if post_qc else "skipped",
                    "duration_sec": round(time.monotonic() - started, 2),
                    "backend_version": backend_version,
                })
                write_json(jobs_path, data)
                print(f"[ok] {pid} -> {rel} (attempt {attempt}/{max_attempts})", flush=True)
                break
        else:
            if last_error:
                failures += 1
                job["status"] = "failed"
                job["error"] = last_error
                append_event(root, {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "panel_id": pid,
                    "status": "failed",
                    "backend": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "attempts": max_attempts,
                    "reference_manifest": rel_to_root(root, reference_manifest),
                    "reference_input_count": len(reference_records),
                    "reference_input_paths": [record["path"] for record in reference_records],
                    "error": last_error,
                    "duration_sec": round(time.monotonic() - started, 2),
                })
                print(f"[fail] {pid}: {last_error}", file=sys.stderr, flush=True)
                write_json(jobs_path, data)
    if all_ready(root, data.get("jobs") or []):
        update_progress(root, args.chapter, "出图", "✅")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
