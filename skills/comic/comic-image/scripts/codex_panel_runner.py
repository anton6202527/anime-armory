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
import uuid
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))

import reference_composite  # noqa: E402
from comic_image_prompt_compiler import (  # noqa: E402
    KIND as COMPILER_KIND,
    VERSION as COMPILER_VERSION,
    lint as lint_compiled_prompt,
    normalize_backend,
    safety_shape_visual_text as safety_shape_visual_prompt,
)
from contracts import stage_inputs_fingerprint  # noqa: E402
from image_backend_adapter import resolve_capabilities  # noqa: E402
from progress import update_stage  # noqa: E402
from visual_authorization import (  # noqa: E402
    VisualAuthorizationError,
    authorization_errors as visual_authorization_errors,
    delegated_visual_authorization,
)
import spend_envelope  # noqa: E402


PNG_SIG = b"\x89PNG\r\n\x1a\n"
CODEX_MODEL = "GPT Image 2"
CODEX_CHANNEL = "Codex CLI"
BUILTIN_CHANNEL = "内置 imagegen"
SKILLS_ROOT = Path(__file__).resolve().parents[2]
# 实机附件上限的唯一真值在 comic/_lib/image_backend_adapter；此处只解引用，不再双写数字。
CODEX_IMAGE_GENERATION_REFERENCE_LIMIT = resolve_capabilities(
    CODEX_MODEL, CODEX_CHANNEL
).executable_attachment_limit


def recorded_channel(*, adopt_builtin: bool) -> str:
    """Return the truthful recipe channel written into jobs/provenance."""
    return BUILTIN_CHANNEL if adopt_builtin else CODEX_CHANNEL


def run_preflight_gate(root: Path, chapter: str) -> int:
    """付费出图入口自带闸门：跑 comic-review image_preflight gate。

    gate 脚本缺失也按阻断处理——离钱最近的入口不能把"没闸"当"通过"；
    ``--skip-gate`` 也只能复用绑定当前输入的真实已授权非 block receipt，不能创建豁免。
    """
    gate_script = SKILLS_ROOT / "comic-review" / "scripts" / "gate.py"
    if not gate_script.is_file():
        print(f"[err] preflight gate 不可用（缺 {gate_script}）", file=sys.stderr)
        return 2
    proc = subprocess.run(
        [sys.executable, str(gate_script), str(root), "--chapter", chapter, "--stage", "image_preflight"],
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode != 0:
        print("[err] image_preflight gate blocked；先按 gate 报告返修并重新取得当前 receipt", file=sys.stderr)
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


def atomic_write_text(path: Path, text: str) -> None:
    """Crash-safe text write: temp file in the same dir + os.replace.

    panel_jobs.json is the single source of truth for every panel's status /
    result_path / SHA provenance and is rewritten after every panel inside a
    long, network-bound, kill-prone generation loop.  A bare write_text leaves
    it truncated on interruption; downstream loaders swallow the JSONDecodeError
    and report the whole chapter as "missing".  Writing the temp file in the
    same directory keeps os.replace on one filesystem (no cross-device rename).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def write_json(path: Path, data: dict) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


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
    if ref_id.startswith(("LOC_", "MON_", "BEAST_", "ANIMAL_")):
        return 1
    if ref_id.startswith(("PROP_", "WEAPON_")):
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
    """Fairly allocate executable slots; never spend all slots on one face.

    Style anchors get one guaranteed slot: a dropped style anchor silently
    breaks whole-chapter style cohesion (observed as style_anchor_drift), so
    the first STYLE_ record is mandatory alongside one anchor per subject.
    """
    mandatory_indices: list[int] = []
    seen_characters: set[str] = set()
    style_reserved = False
    for index, record in enumerate(records):
        rid = str(record.get("id") or "")
        role = str(record.get("role") or "").lower()
        if record.get("required"):
            mandatory_indices.append(index)
            if rid.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")):
                seen_characters.add(rid)
            if rid.startswith("STYLE_") or role == "style":
                style_reserved = True
        elif rid.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")) and rid not in seen_characters:
            mandatory_indices.append(index)
            seen_characters.add(rid)
        elif not style_reserved and (rid.startswith("STYLE_") or role == "style"):
            mandatory_indices.append(index)
            style_reserved = True
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


def likely_large_edge_blank_bands(path: Path) -> list[dict[str, Any]]:
    """Find bright, low-detail paper-like bands touching a panel edge.

    This is intentionally heuristic: a legitimate fog bank or pale sky can look
    similar, so callers must keep the finding at WARN and request visual review.
    """
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return []
    try:
        image = Image.open(path).convert("L")
    except OSError:
        return []

    src_w, src_h = image.size
    max_w = 420
    scale = min(1.0, max_w / max(src_w, 1))
    if scale < 1.0:
        image = image.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))))
    w, h = image.size

    def metrics(box: tuple[int, int, int, int]) -> tuple[float, float, float]:
        band = image.crop(box)
        stats = ImageStat.Stat(band)
        dx = ImageChops.difference(
            band.crop((1, 0, band.width, band.height)),
            band.crop((0, 0, band.width - 1, band.height)),
        )
        dy = ImageChops.difference(
            band.crop((0, 1, band.width, band.height)),
            band.crop((0, 0, band.width, band.height - 1)),
        )
        edge_energy = (ImageStat.Stat(dx).mean[0] + ImageStat.Stat(dy).mean[0]) / 2
        return stats.mean[0], stats.stddev[0], edge_energy

    candidates: list[dict[str, Any]] = []
    # Keep the largest matching band per edge. Fifteen percent is large enough
    # to be compositionally material while avoiding ordinary gutters.
    for edge in ("top", "bottom", "left", "right"):
        match: dict[str, Any] | None = None
        for fraction in (0.15, 0.20, 0.25, 0.30):
            if edge == "top":
                box = (0, 0, w, max(2, int(h * fraction)))
            elif edge == "bottom":
                box = (0, min(h - 2, int(h * (1 - fraction))), w, h)
            elif edge == "left":
                box = (0, 0, max(2, int(w * fraction)), h)
            else:
                box = (min(w - 2, int(w * (1 - fraction))), 0, w, h)
            mean_luma, stddev, edge_energy = metrics(box)
            if mean_luma >= 180 and stddev <= 12 and edge_energy <= 2.5:
                match = {
                    "edge": edge,
                    "fraction": round(fraction, 2),
                    "mean_luma": round(mean_luma, 2),
                    "stddev": round(stddev, 2),
                    "edge_energy": round(edge_energy, 2),
                }
        if match:
            candidates.append(match)
    return candidates


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


def _review_input_record(root: Path, path: Path, role: str, label: str) -> dict[str, str] | None:
    try:
        if not path.is_file():
            return None
        return {
            "role": role,
            "label": label,
            "path": rel_to_root(root, path),
            "sha256": file_sha256(path),
        }
    except OSError:
        return None


def comparison_inputs_sha256(inputs: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_visual_review_packet(
    root: Path,
    chapter: str,
    job: dict[str, Any],
    panel_path: Path,
    reference_records: list[dict[str, str]],
    adjacent_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Build a SHA-bound refs/current/adjacent contact sheet for one panel.

    The packet is deliberately per-image.  It is not a human verdict: it only
    makes the exact pixels that must be reviewed auditable before the runner can
    promote the job to ``ready``.
    """
    adjacent_paths = adjacent_paths or []
    inputs: list[dict[str, str]] = []
    current = _review_input_record(root, panel_path, "current_panel", str(job.get("panel_id") or panel_path.stem))
    if current:
        inputs.append(current)
    seen = {str(panel_path.resolve())}
    for record in reference_records:
        raw = str(record.get("abs_path") or record.get("path") or "").strip()
        if not raw:
            continue
        path = Path(raw) if Path(raw).is_absolute() else root / raw
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        item = _review_input_record(
            root,
            path,
            "reference",
            f"{record.get('id') or path.stem}:{record.get('role') or 'reference'}",
        )
        if item:
            inputs.append(item)
    for index, path in enumerate(adjacent_paths, start=1):
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        item = _review_input_record(root, path, "adjacent_accepted_panel", f"adjacent_{index}:{path.stem}")
        if item:
            inputs.append(item)

    fingerprint = comparison_inputs_sha256(inputs)
    packet: dict[str, Any] = {
        "status": "unverifiable",
        "comparison_inputs": inputs,
        "comparison_inputs_sha256": fingerprint,
        "required_axes": [
            "subject_identity_and_face",
            "hair_outfit_body_and_state",
            "location_prop_structure",
            "style_light_color",
            "composition_axis_and_adjacent_continuity",
        ],
        "human_review_status": "pending",
    }
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        packet["reason"] = "Pillow unavailable; cannot build the mandatory per-image visual review packet"
        return packet

    opened: list[tuple[dict[str, str], Any]] = []
    for item in inputs:
        try:
            image = Image.open(resolve_path(root, item["path"])).convert("RGB")
        except (OSError, ValueError):
            packet["reason"] = f"review input cannot be decoded: {item['path']}"
            return packet
        opened.append((item, image))
    if not opened or not current:
        packet["reason"] = "current panel is missing from the visual review packet"
        return packet

    cell_w, cell_h, caption_h = 360, 360, 34
    columns = min(4, max(1, len(opened)))
    rows = (len(opened) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_w, rows * (cell_h + caption_h)), (35, 35, 38))
    draw = ImageDraw.Draw(canvas)
    for index, (item, image) in enumerate(opened):
        col, row = index % columns, index // columns
        image.thumbnail((cell_w - 12, cell_h - 12), Image.Resampling.LANCZOS)
        x = col * cell_w + (cell_w - image.width) // 2
        y = row * (cell_h + caption_h) + (cell_h - image.height) // 2
        canvas.paste(image, (x, y))
        label = f"{item['role']} | {item['label']} | {item['sha256'][:12]}"
        draw.text((col * cell_w + 8, row * (cell_h + caption_h) + cell_h + 8), label[:54], fill=(235, 235, 235))
    out = root / "生产数据" / "panel_qc" / chapter / f"{job.get('panel_id') or panel_path.stem}_contact_sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")
    packet.update(
        {
            "status": "ready_for_human_review",
            "contact_sheet_path": rel_to_root(root, out),
            "contact_sheet_sha256": file_sha256(out),
        }
    )
    return packet


def declared_reference_attachment_count(root: Path, job: dict[str, Any]) -> int:
    """Count executable attachments, not semantic bindings.

    One image may intentionally satisfy more than one semantic role (for example
    the same character close-up can bind both ``face`` and ``outfit``). Reference
    collection de-duplicates those paths before invoking a backend, so post-QC
    must use the same unit or it will report a reference that never existed as a
    distinct attachment.
    """
    keys: set[str] = set()
    for ref in job.get("references") or []:
        if not isinstance(ref, dict) or not ref.get("id"):
            continue
        raw = str(ref.get("path") or "").strip()
        if raw:
            keys.add(f"path:{resolve_path(root, raw).resolve()}")
            continue
        role = str(ref.get("role") or ref.get("view") or "reference")
        keys.add(f"semantic:{ref.get('id')}:{role}")
    return len(keys)


def warning_findings(post_qc: dict[str, Any]) -> list[dict[str, str]]:
    """Return stable warning codes/reasons that a named reviewer must acknowledge."""
    findings: list[dict[str, str]] = []
    for issue in post_qc.get("issues") or []:
        if not isinstance(issue, dict) or str(issue.get("severity") or "").lower() != "warn":
            continue
        findings.append(
            {
                "code": str(issue.get("code") or issue.get("category") or "unspecified_warning"),
                "reason": str(issue.get("reason") or ""),
            }
        )
    return findings


def machine_review_sha256(
    artifact_sha256: str,
    verdict: str,
    issues: list[dict[str, Any]],
    comparison_inputs_sha256: str,
) -> str:
    """Bind a human disposition to the exact deterministic/heuristic findings."""
    payload = {
        "artifact_sha256": artifact_sha256,
        "verdict": verdict,
        "issues": issues,
        "comparison_inputs_sha256": comparison_inputs_sha256,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def post_qc_panel(
    root: Path,
    chapter: str,
    job: dict[str, Any],
    path: Path,
    reference_records: list[dict[str, str]],
    omitted_reference_records: list[dict[str, str]] | None = None,
    adjacent_paths: list[Path] | None = None,
) -> dict[str, Any]:
    omitted_reference_records = omitted_reference_records or []
    issues: list[dict[str, str]] = []
    pid = str(job.get("panel_id") or path.stem)
    artifact_sha256 = file_sha256(path) if path.is_file() else ""
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

    resolution_policy = str(job.get("resolution_policy") or "")
    provenance = job.get("resolution_provenance") if isinstance(job.get("resolution_provenance"), dict) else {}
    if resolution_policy == "后端最高可达":
        if not provenance.get("master_path") or not provenance.get("native_sha256"):
            issues.append(
                {
                    "severity": "block",
                    "category": "resolution_lineage",
                    "reason": "最高分辨率策略缺少独立原生 master 路径或 SHA，不能证明该格不是低分图/整话图裁切放大",
                }
            )
        if provenance.get("upscaled"):
            issues.append(
                {
                    "severity": "block",
                    "category": "resolution_upscale",
                    "reason": "layout 派生图需要放大原生 master；必须改用更高原生档重新生成，不能插值冒充高清",
                }
            )

    declared_bindings = [
        ref for ref in job.get("references") or []
        if isinstance(ref, dict) and ref.get("id")
    ]
    declared_attachment_count = declared_reference_attachment_count(root, job)
    attached_equivalent_count = reference_composite.attachment_equivalent_count(reference_records)
    unresolved_reference_count = max(
        0, declared_attachment_count - attached_equivalent_count - len(omitted_reference_records)
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

    edge_blank_bands = likely_large_edge_blank_bands(path)
    if edge_blank_bands:
        edges = ", ".join(str(candidate["edge"]) for candidate in edge_blank_bands)
        issues.append(
            {
                "severity": "warn",
                "category": "large_edge_blank_band",
                "confidence": "heuristic",
                "reason": (
                    f"found bright low-detail blank band(s) touching panel edge(s): {edges}; "
                    "verify a text reservation was not rendered as empty paper"
                ),
            }
        )

    visual_review_packet = build_visual_review_packet(
        root,
        chapter,
        job,
        path,
        reference_records,
        adjacent_paths=adjacent_paths,
    )
    if visual_review_packet.get("status") != "ready_for_human_review":
        issues.append(
            {
                "severity": "block",
                "category": "visual_review_packet_unavailable",
                "reason": str(visual_review_packet.get("reason") or "mandatory visual review packet unavailable"),
            }
        )

    verdict = "pass"
    if any(issue["severity"] == "block" for issue in issues):
        verdict = "block"
    elif any(issue["severity"] == "warn" for issue in issues):
        verdict = "warn"

    review_fingerprint = machine_review_sha256(
        artifact_sha256,
        verdict,
        issues,
        str(visual_review_packet.get("comparison_inputs_sha256") or ""),
    )
    payload = {
        "schema_version": 1,
        "kind": "comic_panel_post_qc",
        "chapter": chapter,
        "panel_id": pid,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "verdict": verdict,
        "path": rel_to_root(root, path),
        "artifact_sha256": artifact_sha256,
        "size": {"width": actual_w, "height": actual_h},
        "expected_size": {"width": expected_w, "height": expected_h},
        "resolution_policy": resolution_policy or "legacy_unspecified",
        "resolution_provenance": provenance,
        "declared_reference_count": declared_attachment_count,
        "declared_reference_binding_count": len(declared_bindings),
        "reference_input_count": len(reference_records),
        "attached_equivalent_count": attached_equivalent_count,
        "composite_attachment_count": sum(1 for record in reference_records if record.get("composite")),
        "omitted_attachment_count": len(omitted_reference_records),
        "omitted_attachment_ids": [record.get("id", "") for record in omitted_reference_records],
        "blank_region_candidates": blank_regions,
        "large_edge_blank_band_candidates": edge_blank_bands,
        "machine_review": {
            "status": verdict,
            "sha256": review_fingerprint,
            "coverage": [
                "artifact_decode",
                "canvas_size",
                "resolution_lineage",
                "reference_execution_coverage",
                "baked_text_container_heuristics",
            ],
            "semantic_axes_require_visual_review": True,
        },
        "visual_review_packet": visual_review_packet,
        "issues": issues,
        "machine_review_sha256": review_fingerprint,
        "manual_review_required": True,
    }
    previous: dict[str, Any] = {}
    out = root / "生产数据" / "panel_qc" / chapter / f"{pid}.json"
    if out.is_file():
        try:
            previous = load_json(out)
        except (OSError, json.JSONDecodeError):
            previous = {}
    old_review = previous.get("manual_review") if isinstance(previous.get("manual_review"), dict) else {}
    if (
        verdict in {"pass", "warn"}
        and str(old_review.get("verdict") or "").lower()
        == ("accepted_with_warnings" if verdict == "warn" else "accepted")
        and str(old_review.get("artifact_sha256") or "") == artifact_sha256
        and str(old_review.get("comparison_inputs_sha256") or "")
        == str(visual_review_packet.get("comparison_inputs_sha256") or "")
        and str(old_review.get("machine_review_sha256") or "") == review_fingerprint
    ):
        payload["manual_review"] = old_review
        payload["visual_review_packet"]["human_review_status"] = str(old_review.get("verdict") or "accepted")
    write_json(out, payload)
    return payload


def panel_acceptance_status(root: Path, job: dict[str, Any]) -> dict[str, Any]:
    """Validate that ``ready`` means exact current pixels passed both gates.

    Deterministic ``block``/unverifiable results can never be accepted.  A
    heuristic ``warn`` is eligible only for a named, reasoned
    ``accepted_with_warnings`` disposition bound to the same machine findings.
    """
    rel = str(job.get("result_path") or "").strip()
    if not rel:
        return {"accepted": False, "reason": "result_path_missing"}
    path = resolve_path(root, rel)
    if not png_valid(path):
        return {"accepted": False, "reason": "result_png_missing_or_invalid"}
    current_sha = file_sha256(path)
    if str(job.get("artifact_sha256") or "") != current_sha:
        return {"accepted": False, "reason": "job_artifact_sha_mismatch", "artifact_sha256": current_sha}
    post_qc = job.get("post_qc") if isinstance(job.get("post_qc"), dict) else {}
    if str(post_qc.get("artifact_sha256") or "") != current_sha:
        return {"accepted": False, "reason": "post_qc_artifact_sha_mismatch", "artifact_sha256": current_sha}
    chapter = str(post_qc.get("chapter") or "").strip()
    panel_id = str(post_qc.get("panel_id") or job.get("panel_id") or "").strip()
    receipt_path = root / "生产数据" / "panel_qc" / chapter / f"{panel_id}.json"
    try:
        receipt = load_json(receipt_path)
    except (OSError, json.JSONDecodeError):
        return {"accepted": False, "reason": "post_qc_receipt_missing", "artifact_sha256": current_sha}
    embedded_sha = hashlib.sha256(
        json.dumps(post_qc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    receipt_sha = hashlib.sha256(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if embedded_sha != receipt_sha:
        return {"accepted": False, "reason": "post_qc_receipt_job_mismatch", "artifact_sha256": current_sha}
    verdict = str(post_qc.get("verdict") or "").lower()
    if verdict not in {"pass", "warn"}:
        return {"accepted": False, "reason": "post_qc_block_or_unverifiable", "artifact_sha256": current_sha}
    packet = post_qc.get("visual_review_packet") if isinstance(post_qc.get("visual_review_packet"), dict) else {}
    if packet.get("status") != "ready_for_human_review":
        return {"accepted": False, "reason": "visual_review_packet_unavailable", "artifact_sha256": current_sha}
    comparison_inputs = [item for item in packet.get("comparison_inputs") or [] if isinstance(item, dict)]
    recorded_comparison_sha = str(packet.get("comparison_inputs_sha256") or "")
    if not comparison_inputs or comparison_inputs_sha256(comparison_inputs) != recorded_comparison_sha:
        return {"accepted": False, "reason": "comparison_packet_fingerprint_invalid", "artifact_sha256": current_sha}
    current_inputs = [
        item
        for item in comparison_inputs
        if str(item.get("role") or "") == "current_panel"
        and resolve_path(root, str(item.get("path") or "")).resolve() == path.resolve()
        and str(item.get("sha256") or "") == current_sha
    ]
    if len(current_inputs) != 1:
        return {"accepted": False, "reason": "comparison_packet_current_panel_missing", "artifact_sha256": current_sha}
    contact_sheet_raw = str(packet.get("contact_sheet_path") or "").strip()
    contact_sheet = resolve_path(root, contact_sheet_raw) if contact_sheet_raw else root / "__missing_contact_sheet__"
    if not contact_sheet.is_file() or file_sha256(contact_sheet) != str(packet.get("contact_sheet_sha256") or ""):
        return {"accepted": False, "reason": "visual_review_contact_sheet_changed", "artifact_sha256": current_sha}
    expected_machine_sha = machine_review_sha256(
        current_sha,
        verdict,
        [issue for issue in post_qc.get("issues") or [] if isinstance(issue, dict)],
        str(packet.get("comparison_inputs_sha256") or ""),
    )
    if str(post_qc.get("machine_review_sha256") or "") != expected_machine_sha:
        return {"accepted": False, "reason": "machine_review_receipt_invalid", "artifact_sha256": current_sha}
    manual = post_qc.get("manual_review") if isinstance(post_qc.get("manual_review"), dict) else {}
    required_manual_verdict = "accepted_with_warnings" if verdict == "warn" else "accepted"
    if str(manual.get("verdict") or "").lower() != required_manual_verdict:
        return {"accepted": False, "reason": "human_review_pending", "artifact_sha256": current_sha}
    reviewer = str(manual.get("reviewed_by") or "").strip()
    if not reviewer or not str(manual.get("reason") or "").strip():
        return {"accepted": False, "reason": "human_review_identity_or_reason_missing", "artifact_sha256": current_sha}
    delegated_errors = visual_authorization_errors(
        root, reviewer, "panel_pixels", manual.get("authorization")
    )
    if delegated_errors:
        return {
            "accepted": False, "reason": "delegated_visual_authorization_stale",
            "authorization_errors": delegated_errors, "artifact_sha256": current_sha,
        }
    if reviewer.startswith("delegate:") and manual.get("human_signoff") is not False:
        return {"accepted": False, "reason": "delegated_review_mislabelled_as_human", "artifact_sha256": current_sha}
    if not reviewer.startswith("delegate:") and manual.get("human_signoff") is False:
        return {"accepted": False, "reason": "human_review_mislabelled_as_delegate", "artifact_sha256": current_sha}
    if str(manual.get("artifact_sha256") or "") != current_sha:
        return {"accepted": False, "reason": "human_review_artifact_sha_mismatch", "artifact_sha256": current_sha}
    comparison_sha = str(packet.get("comparison_inputs_sha256") or "")
    if not comparison_sha or str(manual.get("comparison_inputs_sha256") or "") != comparison_sha:
        return {"accepted": False, "reason": "human_review_comparison_packet_stale", "artifact_sha256": current_sha}
    if str(manual.get("machine_review_sha256") or "") != expected_machine_sha:
        return {"accepted": False, "reason": "human_review_machine_findings_stale", "artifact_sha256": current_sha}
    if str(manual.get("contact_sheet_sha256") or "") != str(packet.get("contact_sheet_sha256") or ""):
        return {"accepted": False, "reason": "human_review_contact_sheet_stale", "artifact_sha256": current_sha}
    findings = warning_findings(post_qc)
    if verdict == "warn" and manual.get("acknowledged_warnings") != findings:
        return {"accepted": False, "reason": "warning_disposition_incomplete", "artifact_sha256": current_sha}
    for item in comparison_inputs:
        if not isinstance(item, dict) or not item.get("path") or not item.get("sha256"):
            return {"accepted": False, "reason": "comparison_input_incomplete", "artifact_sha256": current_sha}
        comparison_path = resolve_path(root, str(item["path"]))
        if not comparison_path.is_file() or file_sha256(comparison_path) != str(item["sha256"]):
            return {
                "accepted": False,
                "reason": "comparison_input_changed",
                "changed_path": str(item["path"]),
                "artifact_sha256": current_sha,
            }
    return {
        "accepted": True,
        "reason": (
            "current_pixel_sha_warn_and_named_human_acceptance"
            if verdict == "warn"
            else "current_pixel_sha_machine_pass_and_human_acceptance"
        ),
        "artifact_sha256": current_sha,
        "reviewed_by": reviewer,
        "human_signoff": bool(manual.get("human_signoff", True)),
        "disposition": required_manual_verdict,
    }


def accept_panel_review(
    root: Path,
    chapter: str,
    data: dict[str, Any],
    jobs_path: Path,
    panel_id: str,
    reviewer: str,
    reason: str,
) -> dict[str, Any]:
    """Record the subjective gate for one exact pixel SHA.

    Heuristic warnings require an explicit named disposition.  Deterministic
    blocks and unverifiable/skipped results remain ineligible.
    """
    if not reviewer.strip() or not reason.strip():
        raise ValueError("--reviewer and --review-notes are required for per-panel acceptance")
    job = next(
        (item for item in data.get("jobs") or [] if isinstance(item, dict) and str(item.get("panel_id") or "") == panel_id),
        None,
    )
    if not isinstance(job, dict):
        raise ValueError(f"unknown panel_id: {panel_id}")
    rel = str(job.get("result_path") or "").strip()
    path = resolve_path(root, rel) if rel else root / "__missing__"
    if not png_valid(path):
        raise ValueError(f"{panel_id} has no valid current PNG")
    artifact_sha256 = file_sha256(path)
    post_qc = job.get("post_qc") if isinstance(job.get("post_qc"), dict) else {}
    if str(post_qc.get("artifact_sha256") or "") != artifact_sha256:
        raise ValueError(f"{panel_id} post-QC is stale for the current pixel SHA; run --recheck-existing first")
    qc_path = root / "生产数据" / "panel_qc" / chapter / f"{panel_id}.json"
    try:
        receipt = load_json(qc_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{panel_id} has no readable post-QC receipt; run --recheck-existing") from exc
    if hashlib.sha256(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest() != hashlib.sha256(
        json.dumps(post_qc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest():
        raise ValueError(f"{panel_id} job/receipt post-QC disagree; run --recheck-existing")
    verdict = str(post_qc.get("verdict") or "").lower()
    if verdict not in {"pass", "warn"}:
        raise ValueError(f"{panel_id} machine post-QC={verdict or 'missing'}; block/unverifiable cannot be accepted")
    packet = post_qc.get("visual_review_packet") if isinstance(post_qc.get("visual_review_packet"), dict) else {}
    if packet.get("status") != "ready_for_human_review":
        raise ValueError(f"{panel_id} has no complete refs/current/adjacent visual review packet")
    comparison_inputs = [item for item in packet.get("comparison_inputs") or [] if isinstance(item, dict)]
    if not comparison_inputs or comparison_inputs_sha256(comparison_inputs) != str(packet.get("comparison_inputs_sha256") or ""):
        raise ValueError(f"{panel_id} comparison packet fingerprint is invalid; run --recheck-existing")
    if len(
        [
            item for item in comparison_inputs
            if str(item.get("role") or "") == "current_panel"
            and resolve_path(root, str(item.get("path") or "")).resolve() == path.resolve()
            and str(item.get("sha256") or "") == artifact_sha256
        ]
    ) != 1:
        raise ValueError(f"{panel_id} comparison packet does not bind the current panel; run --recheck-existing")
    contact_sheet_raw = str(packet.get("contact_sheet_path") or "").strip()
    contact_sheet = resolve_path(root, contact_sheet_raw) if contact_sheet_raw else root / "__missing_contact_sheet__"
    if not contact_sheet.is_file() or file_sha256(contact_sheet) != str(packet.get("contact_sheet_sha256") or ""):
        raise ValueError(f"{panel_id} contact sheet changed or is missing; run --recheck-existing")
    for item in comparison_inputs:
        compare_path = resolve_path(root, str(item.get("path") or ""))
        if not compare_path.is_file() or file_sha256(compare_path) != str(item.get("sha256") or ""):
            raise ValueError(f"{panel_id} comparison input changed: {item.get('path')}; run --recheck-existing")
    now = dt.datetime.now().isoformat(timespec="seconds")
    findings = warning_findings(post_qc)
    machine_sha = str(post_qc.get("machine_review_sha256") or "")
    expected_machine_sha = machine_review_sha256(
        artifact_sha256,
        verdict,
        [issue for issue in post_qc.get("issues") or [] if isinstance(issue, dict)],
        str(packet.get("comparison_inputs_sha256") or ""),
    )
    if not machine_sha or machine_sha != expected_machine_sha:
        raise ValueError(f"{panel_id} machine post-QC receipt is incomplete or stale; run --recheck-existing")
    try:
        authorization = delegated_visual_authorization(root, reviewer, "panel_pixels")
    except VisualAuthorizationError as exc:
        raise ValueError(f"{panel_id} delegated visual review is not authorized: {exc}") from exc
    is_delegate = reviewer.strip().startswith("delegate:")
    manual = {
        "verdict": "accepted_with_warnings" if verdict == "warn" else "accepted",
        "artifact_sha256": artifact_sha256,
        "comparison_inputs_sha256": str(packet.get("comparison_inputs_sha256") or ""),
        "contact_sheet_sha256": str(packet.get("contact_sheet_sha256") or ""),
        "machine_review_sha256": machine_sha,
        "acknowledged_warnings": findings,
        "reviewed_by": reviewer.strip(),
        "human_signoff": not is_delegate,
        "review_kind": "delegated_current_pixel_review" if is_delegate else "named_human_current_pixel_review",
        "reviewed_at": now,
        "reason": reason.strip(),
        "confirmations": {
            axis: True for axis in packet.get("required_axes") or []
        },
        "policy": (
            "heuristic warnings explicitly dispositioned by named reviewer; deterministic blocks remain non-waivable"
            if verdict == "warn"
            else "subjective visual gate accepted; deterministic blocks remain non-waivable"
        ),
    }
    if authorization is not None:
        manual["authorization"] = authorization
    post_qc["manual_review"] = manual
    post_qc["visual_review_packet"]["human_review_status"] = manual["verdict"]
    job.update(
        {
            "status": "ready",
            "artifact_sha256": artifact_sha256,
            "post_qc": post_qc,
            "accepted_at": now,
        }
    )
    write_json(qc_path, post_qc)
    status = panel_acceptance_status(root, job)
    if not status.get("accepted"):
        raise ValueError(f"acceptance receipt failed current-pixel validation: {status.get('reason')}")
    write_json(jobs_path, data)
    return status


def status_after_post_qc(post_qc: dict[str, Any]) -> str:
    verdict = str(post_qc.get("verdict") or "").lower()
    if verdict == "pass":
        return "awaiting_review"
    if verdict == "warn":
        return "qc_warn"
    return "qc_block"


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

目标画幅：{width}x{height}，长宽比约 {width / max(height, 1):.3f}。请使用当前工具可返回的最高原生分辨率生成；不要为了匹配目标画布先缩小输出。
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
        if job.get("resolution_policy"):
            material["resolution_policy"] = str(job.get("resolution_policy"))
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


def prepare_spend_context(
    root: Path,
    chapter: str,
    data: dict[str, Any],
    jobs: list[dict[str, Any]],
    *,
    force: bool,
    model: str,
    channel: str,
    envelope_raw: str = "",
    actual_cost_raw: str = "",
) -> dict[str, Any]:
    """Verify the whole requested paid scope without consuming it."""
    raw_path = Path(envelope_raw).expanduser() if envelope_raw.strip() else spend_envelope.default_envelope_path(root, chapter)
    envelope_path = raw_path if raw_path.is_absolute() else root / raw_path
    input_sha = spend_envelope.panel_jobs_input_sha256(data, chapter)
    panel_ids = [str(job.get("panel_id") or "") for job in jobs]
    scope = spend_envelope.requested_scope(chapter, panel_ids, force=force)
    status = spend_envelope.inspect_authorization(
        envelope_path,
        root,
        stage=spend_envelope.STAGE,
        input_sha256=input_sha,
        model=model,
        channel=channel,
        scope=scope,
        next_attempt_id=f"{chapter}:{spend_envelope.STAGE}:retry-round:1",
    )
    if status.get("status") != "authorized":
        raise spend_envelope.SpendAuthorizationError(
            "envelope_exhausted",
            "the human-approved spend envelope has no room for another worst-case paid call",
            authorization=status,
        )
    # A provider-reported actual may be supplied.  Validate it before the paid
    # boundary; otherwise settle conservatively at the approved per-call max.
    actual = (
        spend_envelope.money(actual_cost_raw, field="actual_cost_per_call", allow_zero=True)
        if actual_cost_raw.strip()
        else spend_envelope.money(status["max_cost_per_call"], field="max_cost_per_call")
    )
    maximum = spend_envelope.money(status["max_cost_per_call"], field="max_cost_per_call")
    if actual > maximum:
        raise spend_envelope.SpendAuthorizationError(
            "actual_cost_exceeded_authorization",
            "declared actual cost exceeds the approved per-call maximum",
            actual_cost=spend_envelope.money_text(actual),
            max_cost_per_call=spend_envelope.money_text(maximum),
        )
    return {
        "root": root,
        "chapter": chapter,
        "data_input_sha256": input_sha,
        "force": force,
        "model": model,
        "channel": channel,
        "envelope_path": envelope_path,
        "actual_cost": spend_envelope.money_text(actual),
        "authorization": status,
    }


def run_paid_submission(
    context: dict[str, Any],
    *,
    panel_id: str,
    retry_round: int,
    submit: Any,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Reserve once, call the provider once, then settle once.

    The random consumption ID is intentionally *not* a provider idempotency
    key.  If the process crashes after reserve, that in-flight ID remains
    ambiguous/fail-closed and is never reused for another submit.
    """
    scope = spend_envelope.requested_scope(
        str(context["chapter"]), [panel_id], force=bool(context["force"])
    )
    consumption_id = f"comic-image-{uuid.uuid4().hex}"
    attempt_id = f"{context['chapter']}:{spend_envelope.STAGE}:retry-round:{int(retry_round)}"
    reservation = spend_envelope.reserve_submission(
        Path(context["envelope_path"]),
        Path(context["root"]),
        stage=spend_envelope.STAGE,
        input_sha256=str(context["data_input_sha256"]),
        model=str(context["model"]),
        channel=str(context["channel"]),
        scope=scope,
        consumption_id=consumption_id,
        attempt_id=attempt_id,
    )
    try:
        result = submit()
    except BaseException:
        # The paid boundary may already have been crossed; charge the approved
        # conservative amount before propagating the unexpected local failure.
        spend_envelope.settle_submission(
            Path(context["envelope_path"]),
            Path(context["root"]),
            consumption_id=consumption_id,
            actual_cost=context["actual_cost"],
        )
        raise
    settlement = spend_envelope.settle_submission(
        Path(context["envelope_path"]),
        Path(context["root"]),
        consumption_id=consumption_id,
        actual_cost=context["actual_cost"],
    )
    return result, reservation, settlement


def print_spend_stop(exc: spend_envelope.SpendAuthorizationError, envelope_path: Path | None = None) -> None:
    print(
        spend_envelope.structured_stop(exc, envelope_path=envelope_path),
        file=sys.stderr,
        flush=True,
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


def previous_accepted_panel_paths(root: Path, jobs: list[dict], panel_id: str) -> list[Path]:
    previous: Path | None = None
    for job in jobs:
        if str(job.get("panel_id") or "") == panel_id:
            break
        if not panel_acceptance_status(root, job).get("accepted"):
            continue
        raw = str(job.get("result_path") or "").strip()
        if raw:
            previous = resolve_path(root, raw)
    return [previous] if previous is not None else []


def first_sequence_barrier(root: Path, jobs: list[dict]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Return the first job not backed by a current two-gate acceptance."""
    for job in jobs:
        status = panel_acceptance_status(root, job)
        if not status.get("accepted"):
            return job, status
    return None, {"accepted": True, "reason": "all_panels_accepted"}


def all_ready(root: Path, jobs: list[dict]) -> bool:
    for job in jobs:
        if job.get("status") != "ready" or not panel_acceptance_status(root, job).get("accepted"):
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
        "--accept-reviewed",
        action="store_true",
        help="对唯一当前 panel 写入 SHA 绑定签收；pass 或启发式 warn 可用，确定性 block 不可用",
    )
    parser.add_argument("--reviewer", default="", help="--accept-reviewed 必填：实际查看 contact sheet 的审核人；delegate:* 还需项目当前视觉授权")
    parser.add_argument("--review-notes", default="", help="--accept-reviewed 必填：逐轴目检结论与理由")
    parser.add_argument(
        "--spend-envelope",
        default="",
        help="人工签发的阶段预算 envelope；默认 生产数据/spend_envelopes/image_<chapter>.json",
    )
    parser.add_argument(
        "--actual-cost-per-call",
        default="",
        help="已知的供应商单次实际成本；缺省按 envelope 单次上限保守结算，非法/越界值在提交前阻断",
    )
    parser.add_argument(
        "--skip-gate",
        action="store_true",
        help="仅复用绑定当前完整输入与 panel_jobs SHA 的已授权非 block receipt；不能用 waiver 绕过 preflight",
    )
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    jobs_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    if not jobs_path.is_file():
        print(f"[err] missing panel jobs: {jobs_path}", file=sys.stderr)
        return 2
    data = load_json(jobs_path)
    data["model"] = CODEX_MODEL
    data["channel"] = recorded_channel(adopt_builtin=args.adopt_builtin)
    targets = {item.strip() for item in args.targets.split(",") if item.strip()}
    if args.accept_reviewed:
        if args.recheck_existing or args.force:
            print("[err] --accept-reviewed 不能与 --recheck-existing/--force 同用", file=sys.stderr)
            return 2
        if len(targets) != 1:
            print("[err] --accept-reviewed 每次必须且只能 --targets 一个 panel", file=sys.stderr)
            return 2
        panel_id = next(iter(targets))
        try:
            accepted = accept_panel_review(
                root,
                args.chapter,
                data,
                jobs_path,
                panel_id,
                args.reviewer,
                args.review_notes,
            )
        except ValueError as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 3
        if all_ready(root, data.get("jobs") or []):
            update_stage(
                root,
                args.chapter,
                "出图",
                "✅",
                evidence=f"生产数据/panel_qc/{args.chapter}",
                actor="comic-image.panel_acceptance",
            )
        print(f"[accepted] {panel_id} sha256={accepted['artifact_sha256']}", flush=True)
        return 0
    if args.recheck_existing and len(targets) != 1:
        print("[err] --recheck-existing 每次必须且只能 --targets 一个 panel", file=sys.stderr)
        return 2

    all_jobs = [job for job in data.get("jobs") or [] if isinstance(job, dict)]
    barrier, barrier_status = first_sequence_barrier(root, all_jobs)
    if barrier is None:
        if not args.force:
            print("[ok] no pending jobs")
            return 0
    elif not args.recheck_existing:
        barrier_id = str(barrier.get("panel_id") or "")
        if args.force:
            if len(targets) != 1:
                print("[err] --force 在逐图双闸模式下每次必须且只能 --targets 一个 panel", file=sys.stderr)
                return 2
            forced_id = next(iter(targets))
            forced_index = next((i for i, row in enumerate(all_jobs) if str(row.get("panel_id") or "") == forced_id), -1)
            if forced_index < 0:
                print(f"[err] unknown target: {forced_id}", file=sys.stderr)
                return 2
            prior_unaccepted = [
                str(row.get("panel_id") or "")
                for row in all_jobs[:forced_index]
                if not panel_acceptance_status(root, row).get("accepted")
            ]
            if prior_unaccepted:
                print(f"[err] 不能重抽 {forced_id}：此前图片尚未 accepted：{prior_unaccepted[0]}", file=sys.stderr)
                return 3
        else:
            if targets and barrier_id not in targets:
                print(f"[err] 逐图顺序闸要求先处理 {barrier_id}，不能越过它生成后续格", file=sys.stderr)
                return 3
            barrier_rel = str(barrier.get("result_path") or "").strip()
            if barrier_rel and png_valid(resolve_path(root, barrier_rel)):
                print(
                    f"[review-required] {barrier_id} 尚未 accepted（{barrier_status.get('reason')}）；"
                    f"先查看 panel_qc contact sheet，再用 --accept-reviewed --targets {barrier_id}，"
                    "启发式 warn 可具名带警告签收，确定性 block 才须修复/重抽。",
                    file=sys.stderr,
                )
                return 4

    if not args.recheck_existing:
        if args.skip_gate:
            receipt_status = validate_gate_receipt(root, args.chapter, jobs_path)
            if receipt_status.get("status") != "current_pass":
                print("[err] --skip-gate 只允许复用绑定当前完整输入的已授权非 block receipt；不接受 waiver", file=sys.stderr)
                return 2
            print(f"[ok] --skip-gate 复用当前已授权 receipt：{receipt_status['path']}", flush=True)
        else:
            rc = run_preflight_gate(root, args.chapter)
            if rc != 0:
                return rc
    max_attempts = max(1, args.max_attempts)
    reference_limit = max(1, min(CODEX_IMAGE_GENERATION_REFERENCE_LIMIT, int(args.reference_limit)))
    jobs = selected_jobs(data.get("jobs") or [], targets, args.limit, args.force or args.recheck_existing)
    if not jobs:
        print("[ok] no pending jobs")
        return 0
    missing = {str(job.get("panel_id")): missing_reference_ids(root, job) for job in jobs}
    missing = {pid: refs for pid, refs in missing.items() if refs}
    if missing:
        for pid, refs in missing.items():
            print(f"[err] {pid} missing shared references: {', '.join(refs)}", file=sys.stderr)
        print("[err] seed or place accepted shared reference images before generating panels", file=sys.stderr)
        return 2
    spend_context: dict[str, Any] | None = None
    if not args.recheck_existing:
        try:
            spend_context = prepare_spend_context(
                root,
                args.chapter,
                data,
                jobs,
                force=args.force,
                model=CODEX_MODEL,
                channel=CODEX_CHANNEL,
                envelope_raw=args.spend_envelope,
                actual_cost_raw=args.actual_cost_per_call,
            )
        except spend_envelope.SpendAuthorizationError as exc:
            raw = Path(args.spend_envelope).expanduser() if args.spend_envelope else spend_envelope.default_envelope_path(root, args.chapter)
            print_spend_stop(exc, raw if raw.is_absolute() else root / raw)
            return 5
        print(
            "[spend-authorized] "
            f"envelope={spend_context['authorization']['envelope_id']} "
            f"remaining_calls={spend_context['authorization']['remaining_calls']} "
            f"remaining_cost={spend_context['authorization']['remaining_cost']} "
            f"{spend_context['authorization']['currency']}",
            flush=True,
        )
    if not args.recheck_existing and not shutil.which("codex"):
        print("[err] codex not found in PATH", file=sys.stderr)
        return 2
    backend_version = codex_version() if not args.recheck_existing else str(data.get("backend_version") or "")
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
        all_reference_records, composite_disclosure = reference_composite.compact_records_with_composites(
            root, all_reference_records, reference_limit
        )
        for note in composite_disclosure.get("notes") or []:
            print(f"[warn] {pid} composite: {note}", flush=True)
        if composite_disclosure.get("applied"):
            sheets = ", ".join(
                f"{item['id']}({item['part_count']}视图)" for item in composite_disclosure["composites"]
            )
            print(f"[info] {pid} 多视图折叠为拼板参考：{sheets}", flush=True)
        reference_records, omitted_reference_records = select_reference_attachments(all_reference_records, reference_limit)
        omitted_required = [record for record in omitted_reference_records if record.get("required")]
        selected_subjects = {str(record.get("id") or "") for record in reference_records if str(record.get("id") or "").startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_"))}
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
                adjacent_paths=previous_accepted_panel_paths(root, all_jobs, str(pid)),
            )
            verdict = str(post_qc.get("verdict") or "block")
            job["status"] = status_after_post_qc(post_qc)
            job["result_path"] = rel_to_root(root, final)
            job["artifact_sha256"] = file_sha256(final)
            job["post_qc"] = post_qc
            job["reference_manifest"] = rel_to_root(root, reference_manifest)
            if args.adopt_builtin:
                job.update({
                    "source": recorded_channel(adopt_builtin=True),
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
            if panel_acceptance_status(root, job).get("accepted"):
                job["status"] = "ready"
            write_json(jobs_path, data)
            print(f"[recheck] {pid} -> post_qc={verdict}, status={job['status']}", flush=True)
            return 0 if job["status"] == "ready" else (4 if verdict in {"pass", "warn"} else 3)
        final.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(1, max_attempts + 1):
            # Temp dir under the panel dir (not $TMPDIR): keeps os.replace on one
            # filesystem so the atomic rename can't raise cross-device link after
            # the paid image is already generated.
            with tempfile.TemporaryDirectory(prefix=f".comic-codex-{pid}-", dir=str(final.parent)) as tmp:
                temp_path = Path(tmp) / f"{pid}.png"
                prompt = build_prompt(job, root.name, args.chapter, reference_records)
                assert spend_context is not None
                try:
                    proc, spend_reservation, spend_settlement = run_paid_submission(
                        spend_context,
                        panel_id=str(pid),
                        retry_round=attempt,
                        submit=lambda: run_codex(
                            prompt,
                            repo,
                            args.timeout_sec,
                            reference_paths,
                            ignore_user_config=args.ignore_user_config,
                            ignore_rules=args.ignore_rules,
                        ),
                    )
                except spend_envelope.SpendAuthorizationError as exc:
                    print_spend_stop(exc, Path(spend_context["envelope_path"]))
                    return 5
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
                        "spend_consumption_id": spend_reservation["consumption_id"],
                        "spend_actual_cost": spend_settlement["actual_cost"],
                        "spend_currency": spend_reservation["currency"],
                        "error": error,
                        "duration_sec": round(time.monotonic() - started, 2),
                    })
                    print(f"[retry] {pid} attempt {attempt}/{max_attempts}: {error}", file=sys.stderr, flush=True)
                    continue
                native_w, native_h = image_size(temp_path)
                master = root / "出图" / args.chapter / "masters" / f"{pid}.png"
                master.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(temp_path, master)
                target_size = job.get("size") or {}
                target_w = int(target_size.get("width") or native_w)
                target_h = int(target_size.get("height") or native_h)
                fit_scale = max(target_w / max(native_w, 1), target_h / max(native_h, 1))
                job["master_path"] = rel_to_root(root, master)
                job["resolution_provenance"] = {
                    "requested_resolution_tier": "highest_available",
                    "maximum_verified": False,
                    "native_size": {"width": native_w, "height": native_h},
                    "native_sha256": file_sha256(master),
                    "master_path": rel_to_root(root, master),
                    "derivative_size": {"width": target_w, "height": target_h},
                    "normalization_scale": round(fit_scale, 6),
                    "upscaled": fit_scale > 1.0,
                }
                if not args.no_resize:
                    resize_png(temp_path, job.get("size") or {})
                final.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_path, final)
                rel = str(final.relative_to(root))
                post_qc = post_qc_panel(
                    root,
                    args.chapter,
                    job,
                    final,
                    reference_records,
                    omitted_reference_records,
                    adjacent_paths=previous_accepted_panel_paths(root, all_jobs, str(pid)),
                )
                post_qc_verdict = str(post_qc.get("verdict") or "block")
                history = job.get("history") if isinstance(job.get("history"), list) else []
                if archived_existing:
                    history.append({"kind": "archived_previous", "path": archived_existing})
                generated_at = dt.datetime.now().isoformat(timespec="seconds")
                status = status_after_post_qc(post_qc)
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
                    "spend_consumption_id": spend_reservation["consumption_id"],
                    "spend_actual_cost": spend_settlement["actual_cost"],
                    "spend_currency": spend_reservation["currency"],
                    "post_qc_verdict": post_qc_verdict,
                    "duration_sec": round(time.monotonic() - started, 2),
                    "backend_version": backend_version,
                })
                write_json(jobs_path, data)
                if post_qc_verdict in {"pass", "warn"}:
                    warning_note = (
                        f"；须在 review notes 中处置 warning codes={','.join(item['code'] for item in warning_findings(post_qc))}"
                        if post_qc_verdict == "warn"
                        else ""
                    )
                    print(
                        f"[review-required] {pid} -> {rel}; machine post-QC={post_qc_verdict}，"
                        f"查看 {post_qc['visual_review_packet']['contact_sheet_path']} 后逐图签收{warning_note}；"
                        "未签收前不会生成下一张。",
                        file=sys.stderr,
                        flush=True,
                    )
                    return 4
                print(
                    f"[qc-{post_qc_verdict}] {pid} -> {rel}; 确定性 block 不可人工豁免，必须修复并 --force 重抽",
                    file=sys.stderr,
                    flush=True,
                )
                return 3
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
                return 1
    if all_ready(root, data.get("jobs") or []):
        update_stage(
            root,
            args.chapter,
            "出图",
            "✅",
            evidence=f"出图/{args.chapter}/prompt/panel_jobs.json",
            actor="comic-image.panel_runner",
        )
    if qc_blocked:
        return 3
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
