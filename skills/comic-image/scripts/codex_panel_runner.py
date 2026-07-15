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
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from comic_image_prompt_compiler import (  # noqa: E402
    KIND as COMPILER_KIND,
    VERSION as COMPILER_VERSION,
    lint as lint_compiled_prompt,
    normalize_backend,
    safety_shape_visual_text as safety_shape_visual_prompt,
)
from contracts import stage_inputs_fingerprint  # noqa: E402


PNG_SIG = b"\x89PNG\r\n\x1a\n"
CODEX_MODEL = "GPT Image 2"
CODEX_CHANNEL = "Codex CLI"
SKILLS_ROOT = Path(__file__).resolve().parents[2]
CODEX_IMAGE_GENERATION_REFERENCE_LIMIT = 5


def run_preflight_gate(root: Path, chapter: str) -> int:
    """付费出图入口自带闸门：跑 comic-review image_preflight gate。

    gate 脚本缺失也按阻断处理——离钱最近的入口不能把"没闸"当"通过"；
    确认误报或特殊场景用 --skip-gate 显式豁免（豁免会打印在输出里留痕）。
    """
    gate_script = SKILLS_ROOT / "comic-review" / "scripts" / "gate.py"
    if not gate_script.is_file():
        print(f"[err] preflight gate 不可用（缺 {gate_script}）；如确要跳过请显式传 --skip-gate", file=sys.stderr)
        return 2
    proc = subprocess.run(
        [sys.executable, str(gate_script), str(root), "--chapter", chapter, "--stage", "image_preflight"],
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode != 0:
        print("[err] image_preflight gate blocked；先按 gate 报告返修，或确认误报后显式传 --skip-gate", file=sys.stderr)
        return 2
    return 0


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


def gate_receipt_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / "gate_receipts" / f"image_preflight_{chapter}.json"


def validate_gate_receipt(root: Path, chapter: str, jobs_path: Path) -> dict[str, Any]:
    path = gate_receipt_path(root, chapter)
    try:
        receipt = load_json(path)
    except Exception:
        return {"status": "missing", "path": rel_to_root(root, path), "reason": "receipt_missing_or_unreadable"}
    recorded_sha = str(
        receipt.get("panel_jobs_sha256")
        or (receipt.get("inputs") or {}).get("panel_jobs_sha256")
        or (receipt.get("artifacts") or {}).get("panel_jobs_sha256")
        or ""
    )
    actual_sha = file_sha256(jobs_path) if jobs_path.is_file() else ""
    verdict = str(receipt.get("verdict") or receipt.get("status") or receipt.get("result") or "").lower()
    kind_ok = str(receipt.get("kind") or "") == "comic_gate_receipt"
    stage_ok = str(receipt.get("stage") or "") == "image_preflight"
    chapter_ok = str(receipt.get("chapter") or "") == chapter
    current_inputs = stage_inputs_fingerprint(root, chapter, "image_preflight")
    fingerprint_ok = bool(
        receipt.get("inputs_fingerprint_sha256")
        and receipt.get("inputs_fingerprint_sha256") == current_inputs.get("sha256")
    )
    report_raw = str(receipt.get("report_path") or "").strip()
    report_path = resolve_path(root, report_raw) if report_raw else Path()
    report: dict[str, Any] = {}
    report_hash_ok = False
    report_contract_ok = False
    if report_raw and report_path.is_file():
        try:
            report = load_json(report_path)
        except Exception:
            report = {}
        report_hash_ok = str(receipt.get("report_sha256") or "") == file_sha256(report_path)
        report_inputs = report.get("inputs_fingerprint") if isinstance(report.get("inputs_fingerprint"), dict) else {}
        report_contract_ok = bool(
            report.get("kind") == "comic_gate"
            and report.get("stage") == "image_preflight"
            and report.get("chapter") == chapter
            and str(report.get("verdict") or "").lower() == verdict
            and report_inputs.get("sha256") == current_inputs.get("sha256")
            and report_inputs.get("sha256") == receipt.get("inputs_fingerprint_sha256")
        )
    authorized = (
        verdict in {"pass", "passed", "ok", "clean"}
        or (verdict in {"warn", "warning", "pass_with_warnings"} and receipt.get("execution_authorized") is True)
    )
    current = bool(
        recorded_sha
        and recorded_sha == actual_sha
        and kind_ok
        and stage_ok
        and chapter_ok
        and fingerprint_ok
        and report_hash_ok
        and report_contract_ok
        and authorized
    )
    return {
        "status": "current_pass" if current else "stale_or_not_passed",
        "path": rel_to_root(root, path),
        "receipt_sha256": file_sha256(path),
        "panel_jobs_sha256": actual_sha,
        "recorded_panel_jobs_sha256": recorded_sha,
        "inputs_fingerprint_sha256": current_inputs.get("sha256", ""),
        "recorded_inputs_fingerprint_sha256": str(receipt.get("inputs_fingerprint_sha256") or ""),
        "report_path": rel_to_root(root, report_path) if report_raw else "",
        "verdict": verdict,
        "reason": "" if current else (
            "receipt/report must be authentic, have no block, explicitly authorize execution, "
            "and bind the current full preflight fingerprint plus panel_jobs SHA"
        ),
    }


def write_gate_waiver(root: Path, chapter: str, jobs_path: Path, reason: str, targets: str, receipt_status: dict[str, Any]) -> Path:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    payload = {
        "schema_version": 1,
        "kind": "comic_gate_waiver",
        "stage": "image_preflight",
        "chapter": chapter,
        "decision": "waive_for_this_runner_invocation",
        "reason": reason.strip(),
        "created_at": now.isoformat(),
        "panel_jobs_path": rel_to_root(root, jobs_path),
        "panel_jobs_sha256": file_sha256(jobs_path),
        "targets": [item.strip() for item in targets.split(",") if item.strip()],
        "prior_gate_receipt": receipt_status,
        "scope": "current panel_jobs SHA only; any rebuild invalidates this waiver",
    }
    out_dir = root / "生产数据" / "gate_waivers"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"image_preflight_{chapter}_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    write_json(path, payload)
    write_json(out_dir / f"image_preflight_{chapter}_latest.json", payload)
    return path


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
        current_sha = file_sha256(path)
        expected_sha = str(ref.get("sha256") or "")
        if expected_sha and expected_sha != current_sha:
            raise ValueError(f"reference changed after panel job planning: {raw}")
        records.append(
            {
                "id": str(ref.get("id") or path.stem),
                "path": rel_to_root(root, path),
                "abs_path": str(path),
                "sha256": current_sha,
                "role": str(ref.get("role") or ref.get("view") or "reference"),
                "required": bool(ref.get("required")),
            }
        )
    return records


def reference_attachment_priority(record: dict[str, str]) -> int:
    """Codex image_generation 参考槽优先级：身份 > 场景 > 道具 > 风格 > 特效。"""
    ref_id = str(record.get("id") or "").upper()
    if ref_id.startswith("CHAR_"):
        return 0
    if ref_id.startswith(("LOC_", "MON_")):
        return 1
    if ref_id.startswith("PROP_"):
        return 2
    if ref_id.startswith("STYLE_"):
        return 3
    if ref_id.startswith(("FX_", "VFX_")):
        return 4
    return 5


def select_reference_attachments(
    records: list[dict[str, str]],
    limit: int = CODEX_IMAGE_GENERATION_REFERENCE_LIMIT,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Fairly allocate executable slots; never spend all slots on one face."""
    mandatory_indices: list[int] = []
    seen_characters: set[str] = set()
    for index, record in enumerate(records):
        rid = str(record.get("id") or "")
        if record.get("required"):
            mandatory_indices.append(index)
        elif rid.startswith(("CHAR_", "MON_")) and rid not in seen_characters:
            mandatory_indices.append(index)
            seen_characters.add(rid)
    # Legacy jobs did not mark required; preserve one scene and each named prop
    # before allocating second/third portraits for a character.
    if not any(record.get("required") for record in records):
        loc_added = False
        seen_props: set[str] = set()
        for index, record in enumerate(records):
            rid = str(record.get("id") or "")
            if rid.startswith("LOC_") and not loc_added:
                mandatory_indices.append(index)
                loc_added = True
            elif rid.startswith("PROP_") and rid not in seen_props:
                mandatory_indices.append(index)
                seen_props.add(rid)
    mandatory_indices = list(dict.fromkeys(mandatory_indices))
    remaining = [
        (index, record) for index, record in enumerate(records) if index not in mandatory_indices
    ]
    ranked = sorted(remaining, key=lambda item: (reference_attachment_priority(item[1]), item[0]))
    selected_indices = set(mandatory_indices[: max(0, limit)])
    for index, _record in ranked:
        if len(selected_indices) >= max(0, limit):
            break
        selected_indices.add(index)
    selected = [record for index, record in enumerate(records) if index in selected_indices]
    omitted = [record for index, record in enumerate(records) if index not in selected_indices]
    return selected, omitted


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


def write_reference_manifest(
    root: Path,
    chapter: str,
    panel_id: str,
    records: list[dict[str, str]],
    omitted: list[dict[str, str]] | None = None,
    attachment_limit: int = CODEX_IMAGE_GENERATION_REFERENCE_LIMIT,
) -> Path:
    omitted = omitted or []
    path = root / "生产数据" / "codex_reference_bundles" / chapter / f"{panel_id}.json"
    payload = {
        "schema_version": 1,
        "kind": "comic_codex_reference_bundle",
        "chapter": chapter,
        "panel_id": panel_id,
        "reference_input_mode": "codex_exec_image_flags",
        "reference_attachment_limit": attachment_limit,
        "cli_image_input_count": len(records),
        "references": [
            {key: value for key, value in record.items() if key != "abs_path"}
            for record in records
        ],
        "omitted_attachment_count": len(omitted),
        "omitted_attachments": [
            {
                "id": record.get("id", ""),
                "path": record.get("path", ""),
                "reason": "codex_image_generation_reference_limit; textual_contract_retained",
            }
            for record in omitted
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
    omitted_reference_records: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    omitted_reference_records = omitted_reference_records or []
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
    unresolved_reference_count = max(
        0, len(declared_refs) - len(reference_records) - len(omitted_reference_records)
    )
    if unresolved_reference_count:
        issues.append(
            {
                "severity": "block",
                "category": "reference",
                "reason": (
                    f"{unresolved_reference_count} declared reference(s) are neither attached nor "
                    "disclosed as tool-limit omissions"
                ),
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
        "omitted_attachment_count": len(omitted_reference_records),
        "omitted_attachment_ids": [record.get("id", "") for record in omitted_reference_records],
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
    """Build the small execution wrapper around the compiled provider prompt."""
    validate_compiled_job(job, expected_backend=CODEX_MODEL + " " + CODEX_CHANNEL)
    size = job.get("size") or {}
    width = int(size.get("width") or 1296)
    height = int(size.get("height") or 900)
    ref_line = (
        f"已随请求附入 {len(reference_records)} 张真实参考图；按附件中的角色、场景、道具与画风保持一致。"
        if reference_records else
        "本格没有参考图附件，只按可见画面描述生成。"
    )
    submit_prompt = safety_shape_visual_prompt(str(job.get("submit_prompt") or ""))
    negative_prompt = safety_shape_visual_prompt(str(job.get("negative_prompt") or ""))
    negative = f"\n独立负向字段：{negative_prompt}" if negative_prompt else ""
    return f"""请用内置 image_generation 工具生成一张漫画分格 PNG。

目标尺寸：{width}x{height}，长宽比约 {width / max(height, 1):.3f}
{ref_line}

模型提交 prompt：
{submit_prompt}{negative}

安全呈现硬约束：这是非血腥奇幻漫画。只允许静止无面剪影、破损衣物、黑色墨气、暗红布片与冲击线；禁止可见伤口、穿刺细节、体液、残肢或痛苦特写。用遮挡、剪影和动作前后瞬间保留剧情因果。

本格人体/接触点补充：
{anatomy_guidance(job)}

执行约束：
1. 只生成一个铺满画布的完整面板，不要外框、截图边、画中画、内部漫画分格或拼贴。
2. 参考图作为真实图片输入，优先于与其冲突的泛化文字；多角色不得串脸、串发型、串服装。
3. 生成完成后只回复一句完成，不要写文件、搜索文件系统或输出 Markdown。
"""


def validate_compiled_job(job: dict[str, Any], expected_backend: str = "") -> None:
    compiler = job.get("prompt_compiler") if isinstance(job.get("prompt_compiler"), dict) else {}
    payload = {
        **compiler,
        "prompt": str(job.get("submit_prompt") or ""),
        "negative_prompt": str(job.get("negative_prompt") or ""),
        "source_contract_sha256": str(job.get("source_contract_sha256") or ""),
    }
    errors: list[str] = []
    if job.get("prompt_source_kind") != "compiled_submit_prompt":
        errors.append("prompt_source_kind_invalid")
    if compiler.get("kind") != COMPILER_KIND or compiler.get("version") != COMPILER_VERSION:
        errors.append("prompt_compiler_incompatible")
    if str(job.get("prompt") or "") != str(job.get("submit_prompt") or ""):
        errors.append("prompt_alias_mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", str(job.get("source_contract_sha256") or "")):
        errors.append("source_contract_hash_invalid")
    actual_hash = hashlib.sha256(str(job.get("submit_prompt") or "").encode("utf-8")).hexdigest()
    if str(job.get("submit_prompt_sha256") or "") != actual_hash:
        errors.append("submit_prompt_hash_mismatch")
    execution_hash = str(job.get("execution_input_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", execution_hash):
        errors.append("execution_input_hash_invalid")
    else:
        consumed = job.get("consumed_contracts") if isinstance(job.get("consumed_contracts"), dict) else {}
        reference_plan = consumed.get("reference_plan") if isinstance(consumed.get("reference_plan"), dict) else {}
        material = {
            "submit_prompt_sha256": actual_hash,
            "size": job.get("size") or {},
            "references": [
                {"id": ref.get("id"), "path": ref.get("path"), "sha256": ref.get("sha256")}
                for ref in job.get("references") or [] if isinstance(ref, dict)
            ],
            "character_bindings": [
                {key: binding.get(key) for key in ("character_id", "form_id", "outfit_id", "expression_id", "state_id")}
                for binding in job.get("character_bindings") or [] if isinstance(binding, dict)
            ],
            "panel_plan_sha256": str(reference_plan.get("panel_plan_sha256") or ""),
        }
        actual_execution_hash = hashlib.sha256(
            json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if actual_execution_hash != execution_hash:
            errors.append("execution_input_hash_mismatch")
    if expected_backend and normalize_backend(compiler.get("backend")) != normalize_backend(expected_backend):
        errors.append(f"prompt_backend_mismatch:{compiler.get('backend')}!={normalize_backend(expected_backend)}")
    errors.extend(lint_compiled_prompt(payload)["errors"])
    if errors:
        raise ValueError(f"{job.get('panel_id')} compiled prompt invalid: {errors}")


def anatomy_guidance(job: dict[str, Any]) -> str:
    text = " ".join(
        str(job.get(key, ""))
        for key in ("panel_id", "production_contract_prompt", "production_negative_contract", "submit_prompt")
    )
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
    parser.add_argument(
        "--reference-limit",
        type=int,
        default=CODEX_IMAGE_GENERATION_REFERENCE_LIMIT,
        help="每格实际传给 Codex Image 2 的参考图上限（1-5）；多参考超时格可降到关键主体+场景三张",
    )
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
    parser.add_argument("--continue-on-qc-block", action="store_true", help="调试用：遇到 post_qc=block 仍继续后续格；默认立即停下")
    parser.add_argument(
        "--recheck-existing",
        action="store_true",
        help="只对目标格现有 PNG 重跑 post-QC 并刷新 job 状态，不调用生图模型、不归档或重抽",
    )
    parser.add_argument(
        "--adopt-builtin",
        action="store_true",
        help="配合 --recheck-existing：把现有 PNG 登记为内置 Codex Image 2 路由降级产物并补齐 provenance",
    )
    parser.add_argument(
        "--skip-gate",
        action="store_true",
        help="显式跳过内置 image_preflight gate（编排层刚跑过 gate、或人工确认误报时用；跳过会留痕）",
    )
    parser.add_argument(
        "--waiver-reason",
        default="",
        help="--skip-gate 且没有绑定当前 panel_jobs SHA 的 pass receipt 时必填；会写持久 waiver receipt",
    )
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    jobs_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    if not jobs_path.is_file():
        print(f"[err] missing panel jobs: {jobs_path}", file=sys.stderr)
        return 2
    if args.skip_gate:
        receipt_status = validate_gate_receipt(root, args.chapter, jobs_path)
        if receipt_status.get("status") == "current_pass":
            print(f"[ok] --skip-gate 复用当前 pass receipt：{receipt_status['path']}", flush=True)
        elif not args.waiver_reason.strip():
            print(
                "[err] --skip-gate 没有绑定当前 panel_jobs SHA 的 pass receipt；必须提供 --waiver-reason 并留下持久审计记录",
                file=sys.stderr,
            )
            return 2
        else:
            waiver = write_gate_waiver(
                root, args.chapter, jobs_path, args.waiver_reason, args.targets, receipt_status
            )
            print(f"[warn] --skip-gate 显式豁免已留痕：{rel_to_root(root, waiver)}", flush=True)
    else:
        rc = run_preflight_gate(root, args.chapter)
        if rc != 0:
            return rc
    data = load_json(jobs_path)
    data["model"] = CODEX_MODEL
    data["channel"] = CODEX_CHANNEL
    targets = {item.strip() for item in args.targets.split(",") if item.strip()}
    max_attempts = max(1, args.max_attempts)
    reference_limit = max(1, min(CODEX_IMAGE_GENERATION_REFERENCE_LIMIT, int(args.reference_limit)))
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
    qc_blocked = 0
    for job in jobs:
        pid = job.get("panel_id")
        final = panel_dir / f"{pid}.png"
        archived_existing = archive_existing(final, candidate_root / str(pid), "previous") if args.force else ""
        started = time.monotonic()
        last_error = ""
        all_reference_records = collect_reference_images(root, job)
        reference_records, omitted_reference_records = select_reference_attachments(all_reference_records, reference_limit)
        omitted_required = [record for record in omitted_reference_records if record.get("required")]
        selected_subjects = {str(record.get("id") or "") for record in reference_records if str(record.get("id") or "").startswith(("CHAR_", "MON_"))}
        required_subjects = {str(binding.get("character_id") or "") for binding in job.get("character_bindings") or [] if isinstance(binding, dict)}
        if omitted_required or not required_subjects.issubset(selected_subjects):
            missing_subjects = sorted(required_subjects - selected_subjects)
            print(
                f"[err] {pid} executable reference budget cannot carry all critical contracts; "
                f"omitted_required={','.join(str(item.get('id')) for item in omitted_required) or '-'} "
                f"missing_subjects={','.join(missing_subjects) or '-'}；先拆格/分区生成后合成",
                file=sys.stderr,
            )
            return 2
        reference_manifest = write_reference_manifest(
            root, args.chapter, str(pid), reference_records, omitted_reference_records, reference_limit
        )
        if omitted_reference_records:
            omitted_ids = ", ".join(record["id"] for record in omitted_reference_records)
            print(
                f"[warn] {pid} reference attachments capped at "
                f"{reference_limit}; textual contracts retained for: {omitted_ids}",
                flush=True,
            )
        reference_paths = [Path(record["abs_path"]) for record in reference_records]
        if args.recheck_existing:
            if not png_valid(final):
                print(f"[err] {pid} has no valid existing PNG to recheck: {final}", file=sys.stderr)
                failures += 1
                continue
            post_qc = post_qc_panel(
                root,
                args.chapter,
                job,
                final,
                reference_records,
                omitted_reference_records,
            )
            verdict = str(post_qc.get("verdict") or "block")
            job["status"] = "qc_block" if verdict == "block" else "ready"
            job["result_path"] = rel_to_root(root, final)
            job["post_qc"] = verdict
            job["reference_manifest"] = rel_to_root(root, reference_manifest)
            if args.adopt_builtin:
                job.update({
                    "source": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "execution_backend_override": "Codex built-in image_generation（同模型路由降级，CLI 子代理连续只读说明超时）",
                    "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                    "artifact_sha256": file_sha256(final),
                    "reference_input_mode": "builtin_image_generation_referenced_image_paths",
                    "reference_input_count": len(reference_records),
                    "generated_from_contract_sha256": str(job.get("source_contract_sha256") or ""),
                    "generated_from_submit_prompt_sha256": str(job.get("submit_prompt_sha256") or ""),
                    "generated_from_execution_input_sha256": str(job.get("execution_input_sha256") or ""),
                })
                job.pop("error", None)
            write_json(jobs_path, data)
            print(f"[recheck] {pid} -> post_qc={verdict}", flush=True)
            if verdict == "block":
                qc_blocked += 1
                if not args.continue_on_qc_block:
                    return 3
            continue
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
                post_qc = (
                    {}
                    if args.no_post_qc
                    else post_qc_panel(
                        root,
                        args.chapter,
                        job,
                        final,
                        reference_records,
                        omitted_reference_records,
                    )
                )
                post_qc_verdict = str(post_qc.get("verdict") or "skipped")
                history = job.get("history") if isinstance(job.get("history"), list) else []
                if archived_existing:
                    history.append({"kind": "archived_previous", "path": archived_existing})
                generated_at = dt.datetime.now().isoformat(timespec="seconds")
                status = "qc_block" if post_qc_verdict == "block" else "ready"
                job.update(
                    {
                        "status": status,
                        "result_path": rel,
                        "source": CODEX_CHANNEL,
                        "model": CODEX_MODEL,
                        "generated_at": generated_at,
                        "backend_version": backend_version,
                        "artifact_sha256": file_sha256(final),
                        "attempt": attempt,
                        "reference_input_mode": "codex_exec_image_flags",
                        "reference_input_count": len(reference_records),
                        "reference_manifest": rel_to_root(root, reference_manifest),
                        "generated_from_contract_sha256": str(job.get("source_contract_sha256") or ""),
                        "generated_from_submit_prompt_sha256": str(job.get("submit_prompt_sha256") or ""),
                        "generated_from_execution_input_sha256": str(job.get("execution_input_sha256") or ""),
                        "post_qc": post_qc,
                    }
                )
                if history:
                    job["history"] = history[-10:]
                job.pop("error", None)
                append_event(root, {
                    "ts": generated_at,
                    "panel_id": pid,
                    "status": status,
                    "backend": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "path": rel,
                    "sha256": job["artifact_sha256"],
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "reference_manifest": rel_to_root(root, reference_manifest),
                    "reference_input_count": len(reference_records),
                    "reference_input_paths": [record["path"] for record in reference_records],
                    "post_qc_verdict": post_qc_verdict,
                    "duration_sec": round(time.monotonic() - started, 2),
                    "backend_version": backend_version,
                })
                write_json(jobs_path, data)
                if post_qc_verdict == "block":
                    qc_blocked += 1
                    print(f"[qc-block] {pid} -> {rel}; see {rel_to_root(root, root / '生产数据' / 'panel_qc' / args.chapter / f'{pid}.json')}", file=sys.stderr, flush=True)
                    if not args.continue_on_qc_block:
                        return 3
                else:
                    print(f"[ok] {pid} -> {rel} (attempt {attempt}/{max_attempts}, post_qc={post_qc_verdict})", flush=True)
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
    if qc_blocked:
        return 3
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
