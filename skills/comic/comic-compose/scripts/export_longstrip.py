#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成漫画导出 manifest，并可选用 Pillow 渲染条漫长图。"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Iterator


COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from platform_profiles import is_publish_like_usage, profile_for_platform, validate_manifest
from progress import update_checklist, update_stage
from text_metadata import infer_language_metadata, normalize_text_language, text_from_item, unsupported_lettering_items
import text_renderer_adapter
import lettering_contract


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
WEBP_MAX_DIMENSION = 16383
FONT_CANDIDATES = (
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)

FORMAT_ALIASES = {
    "webp": "webp",
    "png": "png",
    "jpg": "jpg",
    "jpeg": "jpg",
    "pdf": "pdf",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_setting(root: Path, key: str, default: str = "") -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def collect_platform_assets(root: Path, raw_items: list[str], profile: Any) -> tuple[dict[str, Any], list[str]]:
    """Register only real, decodable thumbnail files; never synthesize claims."""
    registered: dict[str, Any] = {}
    for raw in raw_items:
        if "=" not in raw:
            continue
        asset_name, raw_path = (part.strip() for part in raw.split("=", 1))
        if asset_name not in profile.thumbnail_assets:
            continue
        path = Path(raw_path).expanduser()
        path = path.resolve() if path.is_absolute() else (root / path).resolve()
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if not path.is_file():
            continue
        try:
            from PIL import Image
            with Image.open(path) as image:
                image.load()
                width, height = image.width, image.height
                fmt = str(image.format or path.suffix.lstrip(".")).lower().replace("jpeg", "jpg")
        except (ImportError, OSError, ValueError):
            continue
        registered[asset_name] = {
            "path": str(relative),
            "sha256": sha256_file(path),
            "size": {"width": width, "height": height},
            "format": fmt,
            "size_bytes": path.stat().st_size,
        }
    missing = sorted(set(profile.thumbnail_assets) - set(registered))
    return registered, missing


def parse_max_height(value: str | int | None, default: int = 0) -> int:
    if value is None:
        return default
    raw = str(value).strip()
    if not raw:
        return default
    lowered = raw.lower()
    if raw == "0" or any(token in lowered for token in ("不分段", "不限", "单张", "single", "none", "no-split", "unlimited")):
        return 0
    match = re.search(r"\d+", raw)
    return int(match.group(0)) if match else default


def parse_export_formats(value: str | None) -> list[str]:
    raw = str(value or "").strip().lower()
    if not raw:
        return ["webp"]
    formats: list[str] = []
    for token in re.split(r"[+,\s/]+", raw):
        fmt = FORMAT_ALIASES.get(token.strip())
        if fmt and fmt not in formats:
            formats.append(fmt)
    # An explicit but unsupported value must not silently become WebP.  The
    # caller records a deterministic format error and leaves a resumable
    # manifest.  In particular, PDF is a first-class document format.
    return formats


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def print_resolution(root: Path, chapter: str) -> tuple[int, str]:
    contract_path = root / "排版" / chapter / "print_delivery_contract.json"
    if not contract_path.is_file():
        return 300, "default_unverified"
    try:
        payload = load_json(contract_path)
        dpi = int(payload.get("dpi") or 300)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 300, "contract_invalid"
    return (dpi if dpi > 0 else 300), "print_delivery_contract"


def pdf_structural_evidence(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    media_boxes = [
        {"width": float(width), "height": float(height)}
        for width, height in re.findall(
            rb"/MediaBox\s*\[\s*0(?:\.0+)?\s+0(?:\.0+)?\s+([0-9.]+)\s+([0-9.]+)\s*\]",
            data,
        )
    ]
    return {
        "header_valid": data.startswith(b"%PDF-"),
        "eof_marker_present": b"%%EOF" in data[-1024:],
        "page_object_count": len(re.findall(rb"/Type\s*/Page\b", data)),
        "image_object_count": len(re.findall(rb"/Subtype\s*/Image\b", data)),
        "font_object_count": len(re.findall(rb"/Type\s*/Font\b", data)),
        "icc_object_present": b"/ICCBased" in data or b"/OutputIntent" in data,
        "media_boxes_points": media_boxes,
    }


def choose_output_format(formats: list[str], width: int, height: int) -> str:
    for fmt in formats:
        if fmt == "webp" and max(width, height) <= WEBP_MAX_DIMENSION:
            return fmt
        if fmt in {"png", "jpg"}:
            return fmt
    return "png"


def save_canvas(image: Any, path: Path, fmt: str, dpi: float | None = None) -> None:
    dpi_kwargs = {"dpi": (float(dpi), float(dpi))} if dpi else {}
    if fmt == "webp":
        image.save(path, quality=92, **dpi_kwargs)
    elif fmt == "jpg":
        image.save(path, quality=92, **dpi_kwargs)
    else:
        image.save(path, **dpi_kwargs)


def segment_panels_in_reading_order(seg: dict) -> list[dict]:
    """Panels in the segment's authored reading order.

    The layout's `reading_order` (== the authored `panels` array order,
    validated by build_layout) is authoritative.  A `(y,x)` coordinate sort
    reverses RTL rows (reader-first panel has the larger x), silently recording
    the sequence backwards, so it must not be used to derive reading order.
    """
    panels = [p for p in seg.get("panels", []) if isinstance(p, dict)]
    order = seg.get("reading_order")
    if isinstance(order, list) and order:
        by_id = {str(p.get("panel_id")): p for p in panels}
        listed = {str(pid) for pid in order}
        ordered = [by_id[str(pid)] for pid in order if str(pid) in by_id]
        ordered.extend(p for p in panels if str(p.get("panel_id")) not in listed)
        return ordered
    return panels


def ordered_panel_ids(layout: dict) -> list[str]:
    ids: list[str] = []
    for seg in layout.get("segments", []):
        for panel in segment_panels_in_reading_order(seg):
            pid = panel.get("panel_id")
            if pid and pid not in ids:
                ids.append(pid)
    return ids


def panel_slot_map(layout: dict) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for seg in layout.get("segments", []):
        for panel in seg.get("panels", []):
            pid = panel.get("panel_id")
            if not pid:
                continue
            slots = {}
            for slot in panel.get("bubble_slots", []):
                sid = slot.get("slot_id")
                if sid:
                    slots[sid] = slot
            out[pid] = {"panel": panel, "slots": slots}
    return out


def lettering_by_panel(lettering: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for item in lettering.get("items") or []:
        pid = item.get("panel_id")
        if pid:
            out.setdefault(pid, []).append(item)
    return out


def find_panel_image(panel_dir: Path, panel_id: str) -> Path | None:
    for ext in IMAGE_EXTS:
        candidate = panel_dir / f"{panel_id}{ext}"
        if candidate.is_file():
            return candidate
    matches = sorted(panel_dir.glob(f"{panel_id}.*"))
    return next((m for m in matches if m.suffix.lower() in IMAGE_EXTS), None)


def resolve_font_path(raw: str | None) -> str:
    if raw:
        path = Path(raw).expanduser()
        if path.is_file():
            return str(path)
    for item in FONT_CANDIDATES:
        if Path(item).is_file():
            return item
    return ""


def load_font(size: int, font_path: str):
    from PIL import ImageFont

    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def text_size(draw, text: str, font) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=0)
    return box[2] - box[0], box[3] - box[1]


def mostly_latin(text: str) -> bool:
    chars = [ch for ch in text if not ch.isspace()]
    if not chars:
        return False
    latin = sum(1 for ch in chars if ord(ch) < 128)
    return latin / len(chars) >= 0.75


def split_long_token(draw, token: str, font, max_width: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for char in token:
        test = current + char
        if current and text_size(draw, test, font)[0] > max_width:
            parts.append(current)
            current = char
        else:
            current = test
    if current:
        parts.append(current)
    return parts


KINSOKU_LINE_START_FORBIDDEN = set("、。，．？！：；)]}〉》」』】〕〗〙〛’”ー々ぁぃぅぇぉっゃゅょァィゥェォッャュョヵヶ")
KINSOKU_LINE_END_FORBIDDEN = set("([{〈《「『【〔〖〘〚‘“")


def wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    text = str(text).strip()
    if not text:
        return []
    if mostly_latin(text):
        lines: list[str] = []
        for paragraph in text.splitlines():
            words = paragraph.split()
            current = ""
            for word in words:
                test = word if not current else f"{current} {word}"
                if text_size(draw, test, font)[0] <= max_width:
                    current = test
                    continue
                if current:
                    lines.append(current)
                if text_size(draw, word, font)[0] <= max_width:
                    current = word
                else:
                    parts = split_long_token(draw, word, font, max_width)
                    lines.extend(parts[:-1])
                    current = parts[-1] if parts else ""
            if current:
                lines.append(current)
        return lines
    lines: list[str] = []
    current = ""
    for char in text:
        if char == "\n":
            if current:
                lines.append(current)
            current = ""
            continue
        test = current + char
        if current and text_size(draw, test, font)[0] > max_width:
            if char in KINSOKU_LINE_START_FORBIDDEN:
                current += char
                continue
            if current[-1] in KINSOKU_LINE_END_FORBIDDEN and len(current) > 1:
                opener = current[-1]
                lines.append(current[:-1])
                current = opener + char
            else:
                lines.append(current)
                current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def line_height(draw, font, sample: str, fallback: int) -> int:
    _, height = text_size(draw, sample, font)
    return max(height, fallback)


def fit_lines(draw, text: str, font_path: str, target_size: int, max_width: int, max_height: int) -> tuple[object, list[str], int]:
    size = max(12, int(target_size))
    while size >= 10:
        font = load_font(size, font_path)
        lines = wrap_text(draw, text, font, max_width)
        line_h = line_height(draw, font, "国Ag", size)
        total_h = len(lines) * line_h + max(0, len(lines) - 1) * 6
        if lines and total_h <= max_height and all(text_size(draw, line, font)[0] <= max_width for line in lines):
            return font, lines, line_h
        size -= 2
    font = load_font(10, font_path)
    return font, wrap_text(draw, text, font, max_width), 12


def fit_bilingual_lines(
    draw,
    text_zh: str,
    text_en: str,
    font_path: str,
    target_size: int,
    max_width: int,
    max_height: int,
) -> tuple[object, list[str], int, object | None, list[str], int, int]:
    zh = str(text_zh or "").strip()
    en = str(text_en or "").strip()
    size = max(12, int(target_size))
    while size >= 10:
        zh_font = load_font(size, font_path)
        en_size = max(9, int(size * 0.56))
        en_font = load_font(en_size, font_path) if en else None
        zh_lines = wrap_text(draw, zh, zh_font, max_width) if zh else []
        en_lines = wrap_text(draw, en, en_font, max_width) if en and en_font else []
        zh_h = line_height(draw, zh_font, "国Ag", size)
        en_h = line_height(draw, en_font, "Ag", en_size) if en_font else 0
        zh_total = len(zh_lines) * zh_h + max(0, len(zh_lines) - 1) * 4
        en_total = len(en_lines) * en_h + max(0, len(en_lines) - 1) * 3
        gap = 8 if zh_lines and en_lines else 0
        total_h = zh_total + gap + en_total
        widths_ok = all(text_size(draw, line, zh_font)[0] <= max_width for line in zh_lines)
        if en_font:
            widths_ok = widths_ok and all(text_size(draw, line, en_font)[0] <= max_width for line in en_lines)
        if (zh_lines or en_lines) and total_h <= max_height and widths_ok:
            return zh_font, zh_lines, zh_h, en_font, en_lines, en_h, gap
        size -= 2
    zh_font = load_font(10, font_path)
    en_font = load_font(9, font_path) if en else None
    return (
        zh_font,
        wrap_text(draw, zh, zh_font, max_width) if zh else [],
        12,
        en_font,
        wrap_text(draw, en, en_font, max_width) if en and en_font else [],
        11 if en else 0,
        5 if zh and en else 0,
    )


def slot_rect(panel: dict, slot: dict, image) -> tuple[int, int, int, int]:
    px = float(panel.get("x", 0) or 0)
    py = float(panel.get("y", 0) or 0)
    pw = float(panel.get("w", image.width) or image.width)
    ph = float(panel.get("h", image.height) or image.height)
    sx = (float(slot.get("x", px) or px) - px) / max(pw, 1.0) * image.width
    sy = (float(slot.get("y", py) or py) - py) / max(ph, 1.0) * image.height
    sw = float(slot.get("w", 420) or 420) / max(pw, 1.0) * image.width
    sh = float(slot.get("h", 130) or 130) / max(ph, 1.0) * image.height
    return int(sx), int(sy), int(sw), int(sh)


def stable_unit(seed: str, offset: int = 0) -> float:
    digest = hashlib.sha256(f"{seed}:{offset}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


def irregular_points(x: int, y: int, w: int, h: int, seed: str, tail: bool) -> tuple[list[tuple[int, int]], int]:
    tail_h = max(0, min(int(h * 0.22), 42)) if tail and h >= 90 else 0
    body_h = max(24, h - tail_h)
    jitter_x = max(2, int(w * 0.025))
    jitter_y = max(2, int(body_h * 0.035))
    points: list[tuple[int, int]] = []
    steps_x = 5
    steps_y = 3
    for i in range(steps_x + 1):
        px = x + int(w * i / steps_x)
        py = y + int((stable_unit(seed, i) - 0.5) * jitter_y * 2)
        points.append((px, py))
    for i in range(1, steps_y + 1):
        px = x + w + int((stable_unit(seed, 20 + i) - 0.5) * jitter_x * 2)
        py = y + int(body_h * i / steps_y)
        points.append((px, py))
    if tail_h:
        tail_base = x + int(w * (0.56 + (stable_unit(seed, 40) - 0.5) * 0.18))
        base_half = max(18, min(44, w // 8))
        points.extend(
            [
                (x + w + int((stable_unit(seed, 50) - 0.5) * jitter_x), y + body_h),
                (tail_base + base_half, y + body_h),
                (tail_base, y + body_h + tail_h),
                (tail_base - base_half, y + body_h),
            ]
        )
    for i in range(steps_x, -1, -1):
        px = x + int(w * i / steps_x)
        py = y + body_h + int((stable_unit(seed, 60 + i) - 0.5) * jitter_y * 2)
        points.append((px, py))
    for i in range(steps_y, 0, -1):
        px = x + int((stable_unit(seed, 80 + i) - 0.5) * jitter_x * 2)
        py = y + int(body_h * i / steps_y)
        points.append((px, py))
    return points, tail_h


def _anchor_point_from_geometry(panel: dict[str, Any], image: Any, value: Any) -> tuple[int, int] | None:
    """Map an authored point/bbox in layout or normalized coordinates to panel pixels."""
    if not isinstance(value, dict):
        return None
    geometry = value.get("bbox") if isinstance(value.get("bbox"), dict) else value.get("rect") if isinstance(value.get("rect"), dict) else value
    if not isinstance(geometry, dict) or "x" not in geometry or "y" not in geometry:
        return None
    raw_x, raw_y = float(geometry.get("x") or 0), float(geometry.get("y") or 0)
    gw, gh = float(geometry.get("w") or 0), float(geometry.get("h") or 0)
    normalized = all(0.0 <= value <= 1.0 for value in (raw_x, raw_y, gw, gh)) and (raw_x or raw_y or gw or gh)
    gx, gy = raw_x, raw_y
    gx += gw / 2
    gy += gh / 2
    px, py = float(panel.get("x") or 0), float(panel.get("y") or 0)
    pw, ph = max(1.0, float(panel.get("w") or image.width)), max(1.0, float(panel.get("h") or image.height))
    if normalized:
        mapped_x, mapped_y = gx * image.width, gy * image.height
    else:
        mapped_x = (gx - px) / pw * image.width
        mapped_y = (gy - py) / ph * image.height
    return (
        max(0, min(image.width - 1, int(round(mapped_x)))),
        max(0, min(image.height - 1, int(round(mapped_y)))),
    )


def resolve_tail_target(panel: dict[str, Any], slot: dict[str, Any], image: Any) -> dict[str, Any]:
    """Resolve a dialogue tail against an explicit speaker target/anchor only."""
    tail = slot.get("tail") if isinstance(slot.get("tail"), dict) else {}
    speaker = str(slot.get("speaker") or "").strip()
    raw_target = tail.get("target")
    target = str(raw_target or speaker).strip()

    for key in ("target_point", "target_bbox", "anchor", "bbox", "rect"):
        if isinstance(tail.get(key), dict):
            point = _anchor_point_from_geometry(panel, image, tail[key])
            if point is not None:
                return {"point": point, "resolution": f"tail.{key}", "target": target, "speaker": speaker}
    if isinstance(raw_target, dict):
        point = _anchor_point_from_geometry(panel, image, raw_target)
        if point is not None:
            return {"point": point, "resolution": "tail.target_geometry", "target": target, "speaker": speaker}

    anchors = panel.get("speaker_anchors")
    candidates: list[tuple[str, Any]] = []
    if isinstance(anchors, dict):
        for key, value in anchors.items():
            candidates.append((str(key), value))
    elif isinstance(anchors, list):
        for value in anchors:
            if isinstance(value, dict):
                key = next((str(value.get(field) or "") for field in ("speaker", "character_id", "subject_id", "id", "name") if value.get(field)), "")
                candidates.append((key, value))
    for key, value in candidates:
        if target and key not in {target, speaker}:
            continue
        point = _anchor_point_from_geometry(panel, image, value)
        if point is not None:
            return {"point": point, "resolution": "panel.speaker_anchors", "target": target or key, "speaker": speaker}

    for collection in ("character_regions", "subject_regions"):
        for value in panel.get(collection) or []:
            if not isinstance(value, dict):
                continue
            labels = {str(value.get(field) or "") for field in ("speaker", "character_id", "subject_id", "region_id", "id", "name") if value.get(field)}
            if target and target not in labels and speaker not in labels:
                continue
            point = _anchor_point_from_geometry(panel, image, value)
            if point is not None:
                return {"point": point, "resolution": f"panel.{collection}", "target": target, "speaker": speaker}
    return {"point": None, "resolution": "deterministic_legacy_fallback", "target": target, "speaker": speaker}


def _tail_triangle(rect: tuple[int, int, int, int], target: tuple[int, int]) -> list[tuple[int, int]]:
    x, y, w, h = rect
    cx, cy = x + w / 2, y + h / 2
    tx, ty = target
    dx, dy = tx - cx, ty - cy
    base_half = max(12, min(34, min(w, h) // 8))
    if abs(dx) / max(1, w) >= abs(dy) / max(1, h):
        edge_x = x + w if dx >= 0 else x
        edge_y = max(y + base_half, min(y + h - base_half, int(ty)))
        base = [(edge_x, edge_y - base_half), (edge_x, edge_y + base_half)]
    else:
        edge_y = y + h if dy >= 0 else y
        edge_x = max(x + base_half, min(x + w - base_half, int(tx)))
        base = [(edge_x - base_half, edge_y), (edge_x + base_half, edge_y)]
    return [base[0], (int(tx), int(ty)), base[1]]


def draw_irregular_bubble(
    draw,
    rect: tuple[int, int, int, int],
    item_type: str,
    seed: str,
    *,
    target_point: tuple[int, int] | None = None,
) -> tuple[tuple[int, int, int, int], dict[str, Any]]:
    x, y, w, h = rect
    fill = (252, 248, 238) if item_type == "dialogue" else (244, 238, 220)
    tail = item_type == "dialogue"
    # A resolved speaker target gets a real directional tail outside the body.
    # Legacy layouts retain the deterministic in-slot tail for compatibility,
    # but the receipt truthfully marks that fallback.
    points, tail_h = irregular_points(x, y, w, h, seed, tail and target_point is None)
    tail_points: list[tuple[int, int]] = []
    legacy_tip: tuple[int, int] | None = None
    if tail_h and target_point is None:
        body_h = max(24, h - tail_h)
        tail_base = x + int(w * (0.56 + (stable_unit(seed, 40) - 0.5) * 0.18))
        legacy_tip = (tail_base, y + body_h + tail_h)
    if tail and target_point is not None:
        tail_points = _tail_triangle((x, y, w, h), target_point)
        draw.polygon(tail_points, fill=fill)
        draw.line(tail_points + [tail_points[0]], fill=(20, 20, 20), width=3, joint="curve")
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=(20, 20, 20), width=3, joint="curve")
    receipt = {
        "rendered": bool(tail),
        "tail_tip": list(target_point) if target_point is not None else list(legacy_tip) if legacy_tip is not None else [],
        "target_resolved": target_point is not None,
    }
    return (x, y, w, max(24, h - tail_h)), receipt


def draw_centered_lines(draw, x: int, y: int, w: int, lines: list[str], font, line_h: int, fill: tuple[int, int, int], spacing: int) -> int:
    yy = y
    for line in lines:
        tw, _ = text_size(draw, line, font)
        draw.text((x + max(0, (w - tw) // 2), yy), line, font=font, fill=fill)
        yy += line_h + spacing
    return yy - spacing if lines else yy


def draw_text_block(
    image,
    draw,
    rect: tuple[int, int, int, int],
    text_zh: str,
    text_en: str,
    item_type: str,
    style: dict,
    font_path: str,
    seed: str,
    *,
    panel: dict[str, Any] | None = None,
    slot: dict[str, Any] | None = None,
    renderer_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    x, y, w, h = rect
    pad = max(14, int(min(w, h) * 0.12))
    size = int(style.get("size") or (72 if item_type == "sfx" else 44))
    if item_type == "sfx":
        zh = str(text_zh or "").strip()
        en = str(text_en or "").strip()
        text = zh if not en else f"{zh}\n{en}"
        font, lines, line_h = fit_lines(draw, text, font_path, size, max(40, w), max(30, h))
        total_h = len(lines) * line_h + max(0, len(lines) - 1) * 4
        yy = y + max(0, (h - total_h) // 2)
        for line in lines:
            tw, _ = text_size(draw, line, font)
            draw.text((x + max(0, (w - tw) // 2), yy), line, font=font, fill=(245, 239, 220), stroke_width=4, stroke_fill=(25, 20, 18))
            yy += line_h + 4
        return {"rendered": False, "reason": "sfx_has_no_dialogue_tail"}

    target_receipt = resolve_tail_target(panel or {}, slot or {}, image) if item_type == "dialogue" else {
        "point": None, "resolution": "not_dialogue", "target": "", "speaker": ""
    }
    (body_x, body_y, body_w, body_h), tail_receipt = draw_irregular_bubble(
        draw,
        rect,
        item_type,
        seed,
        target_point=target_receipt.get("point"),
    )
    text_x = body_x + pad
    text_y = body_y + pad
    text_w = max(40, body_w - pad * 2)
    text_h = max(30, body_h - pad * 2)
    renderer_context = renderer_context or {}
    professional_receipt: dict[str, Any] = {}
    glyph_receipt: dict[str, Any] = {}
    if renderer_context:
        full_text = "\n".join(part for part in (str(text_zh or "").strip(), str(text_en or "").strip()) if part)
        metadata = infer_language_metadata(full_text, str(renderer_context.get("text_language") or ""))
        raw_direction = str(style.get("direction") or "horizontal").strip().lower()
        writing_mode = "vertical-rl" if raw_direction in {"vertical", "竖排", "縦書き", "縦書"} else "horizontal-tb"
        selection = text_renderer_adapter.select_renderer(
            language_mode=str(renderer_context.get("text_language") or metadata.get("lang") or "中文"),
            direction=str(metadata.get("dir") or "ltr"),
            writing_mode=writing_mode,
            root=renderer_context.get("root"),
        )
        glyph_receipt = text_renderer_adapter.validate_glyph_coverage(full_text, font_path=font_path)
        needs_professional = bool(renderer_context.get("publication_required")) or writing_mode.startswith("vertical") or metadata.get("dir") == "rtl" or metadata.get("line_break") in {"dictionary_required", "bidi_required"}
        if selection.get("publication_claim_allowed"):
            overlay_dir = Path(renderer_context["overlay_dir"])
            overlay_path = overlay_dir / f"{re.sub(r'[^0-9A-Za-z_.-]+', '_', seed)}.png"
            professional_receipt = text_renderer_adapter.render_text_rgba(
                {
                    "text": full_text,
                    "language_mode": str(renderer_context.get("text_language") or metadata.get("lang") or ""),
                    "direction": str(metadata.get("dir") or "ltr"),
                    "writing_mode": writing_mode,
                    "font_path": font_path,
                    "font_size": size,
                    "width": text_w,
                    "height": text_h,
                    "fill": "#141414",
                },
                overlay_path,
                root=renderer_context.get("root"),
                adapter=selection,
            )
            if professional_receipt.get("status") == "rendered":
                from PIL import Image

                with Image.open(overlay_path) as rendered_text:
                    overlay = rendered_text.convert("RGBA")
                    overlay.thumbnail((text_w, text_h), getattr(Image, "Resampling", Image).LANCZOS)
                    pos = (text_x + max(0, (text_w - overlay.width) // 2), text_y + max(0, (text_h - overlay.height) // 2))
                    image.paste(overlay, pos, overlay)
                professional_receipt["output_path"] = str(overlay_path.relative_to(renderer_context["root"]))
                return {
                    **tail_receipt,
                    "speaker": target_receipt.get("speaker", ""),
                    "target": target_receipt.get("target", ""),
                    "target_resolution": target_receipt.get("resolution", ""),
                    "target_point": list(target_receipt["point"]) if target_receipt.get("point") is not None else [],
                    "text_renderer_receipt": professional_receipt,
                    "glyph_coverage_receipt": glyph_receipt,
                }
        if needs_professional:
            reason = professional_receipt.get("reason") or selection.get("reason") or "professional text renderer did not produce current pixels"
            raise RuntimeError(f"文字 {seed} 需要专业 shaping/竖排或发布级 renderer：{reason}")
    zh_font, zh_lines, zh_h, en_font, en_lines, en_h, gap = fit_bilingual_lines(
        draw, text_zh, text_en, font_path, size, text_w, text_h
    )
    zh_total = len(zh_lines) * zh_h + max(0, len(zh_lines) - 1) * 4
    en_total = len(en_lines) * en_h + max(0, len(en_lines) - 1) * 3
    total_h = zh_total + gap + en_total
    yy = text_y + max(0, (text_h - total_h) // 2)
    yy = draw_centered_lines(draw, text_x, yy, text_w, zh_lines, zh_font, zh_h, (20, 20, 20), 4)
    if en_lines and en_font:
        yy += gap
        draw_centered_lines(draw, text_x, yy, text_w, en_lines, en_font, en_h, (58, 58, 58), 3)
    return {
        **tail_receipt,
        "speaker": target_receipt.get("speaker", ""),
        "target": target_receipt.get("target", ""),
        "target_resolution": target_receipt.get("resolution", ""),
        "target_point": list(target_receipt["point"]) if target_receipt.get("point") is not None else [],
        "text_renderer_receipt": {
            "kind": "comic_text_render_receipt",
            "status": "draft_fallback",
            "renderer": "pillow_draft",
            "publication_claim_allowed": False,
        },
        "glyph_coverage_receipt": glyph_receipt,
    }


def collect_group_text(group: list[dict], fields: tuple[str, ...], *, sfx: bool) -> str:
    chunks: list[str] = []
    for item in group:
        text = ""
        for field in fields:
            text = str(item.get(field, "") or "").strip()
            if text:
                break
        if text:
            chunks.append(text)
    return ("  " if sfx else "\n").join(chunks)


def display_text_pair(group: list[dict], item_type: str, text_language: str) -> tuple[str, str]:
    mode = normalize_text_language(text_language)
    sfx = item_type == "sfx"
    zh = collect_group_text(group, ("text_zh", "text"), sfx=sfx)
    en = collect_group_text(group, ("text_en",), sfx=sfx)
    custom = collect_group_text(group, ("text_custom", "text"), sfx=sfx)

    if mode == "英文":
        return en or zh, ""
    if mode == "中上英下":
        return zh, en
    if mode == "英上中下":
        return en or zh, zh if en else ""
    if mode.startswith("自定义语言"):
        return custom or zh, ""
    return zh, ""


def apply_lettering(
    image,
    panel_id: str,
    slot_info: dict[str, Any],
    items: list[dict],
    font_path: str,
    text_language: str,
    renderer_context: dict[str, Any] | None = None,
):
    from PIL import ImageDraw

    panel = slot_info.get("panel") or {"w": image.width, "h": image.height}
    slots = slot_info.get("slots") or {}
    draw = ImageDraw.Draw(image)
    groups: dict[str, list[dict]] = {}
    for item in items:
        sid = item.get("slot_id") or item.get("item_id")
        groups.setdefault(str(sid), []).append(item)
    fallback_y = 32
    stats = {
        "drawn_items": 0,
        "skipped_empty_items": [],
        "empty_slots_removed": [],
        "tail_receipts": [],
        "text_renderer_receipts": [],
        "glyph_coverage_receipts": [],
    }
    used_slots: set[str] = set()
    for sid, group in groups.items():
        first = group[0]
        item_type = first.get("type", "dialogue")
        style = first.get("style") or {}
        primary_text, secondary_text = display_text_pair(group, item_type, text_language)
        if not primary_text and not secondary_text:
            stats["skipped_empty_items"].extend(item.get("item_id", sid) for item in group)
            continue
        slot = slots.get(sid)
        if slot:
            rect = slot_rect(panel, slot, image)
            used_slots.add(sid)
        else:
            rect = (32, fallback_y, min(560, image.width - 64), 140)
            fallback_y += 160
            slot = {"slot_id": sid, "type": item_type, "speaker": first.get("speaker", ""), "tail": first.get("tail") or {}}
        tail_receipt = draw_text_block(
            image,
            draw,
            rect,
            primary_text,
            secondary_text,
            item_type,
            style,
            font_path,
            f"{panel_id}:{sid}",
            panel=panel,
            slot=slot,
            renderer_context=renderer_context,
        )
        if item_type == "dialogue":
            stats["tail_receipts"].append({"panel_id": panel_id, "slot_id": sid, **tail_receipt})
        if tail_receipt.get("text_renderer_receipt"):
            stats["text_renderer_receipts"].append({"panel_id": panel_id, "slot_id": sid, **tail_receipt["text_renderer_receipt"]})
        if tail_receipt.get("glyph_coverage_receipt"):
            stats["glyph_coverage_receipts"].append({"panel_id": panel_id, "slot_id": sid, **tail_receipt["glyph_coverage_receipt"]})
        stats["drawn_items"] += len(group)
    for sid in slots:
        if sid not in used_slots:
            stats["empty_slots_removed"].append(f"{panel_id}:{sid}")
    return image, stats


def build_manifest(
    root: Path,
    chapter: str,
    layout_path: Path,
    panel_dir: Path,
    out_dir: Path,
    page_dir: Path,
    max_height: int,
    lettering_path: Path | None,
    font_path: str,
    export_formats: list[str],
) -> dict:
    layout = load_json(layout_path)
    panel_ids = ordered_panel_ids(layout)
    panels = []
    missing = []
    for pid in panel_ids:
        img = find_panel_image(panel_dir, pid)
        if img:
            panels.append({"panel_id": pid, "path": str(img.relative_to(root)), "sha256": sha256_file(img), "size_bytes": img.stat().st_size})
        else:
            missing.append(pid)
    return {
        "schema_version": 2,
        "kind": "comic_export_manifest",
        "chapter": chapter,
        "layout": str(layout_path.relative_to(root)),
        "panel_dir": str(panel_dir.relative_to(root)),
        "out_dir": str(out_dir.relative_to(root)),
        "page_dir": str(page_dir.relative_to(root)),
        "lettering": str(lettering_path.relative_to(root)) if lettering_path and lettering_path.is_file() else "",
        "lettering_sha256": sha256_file(lettering_path) if lettering_path and lettering_path.is_file() else "",
        "font": font_path,
        "font_status": "system_font_draft" if font_path else "pillow_default_fallback",
        "export_formats": export_formats,
        "max_segment_height": max_height,
        "split_mode": "height" if max_height > 0 else "single",
        "panels": panels,
        "missing_panels": missing,
        "pages": [],
        "rendered": [],
        "documents": [],
        "delivery_mediums": [
            medium
            for medium, enabled in (
                ("web_images", any(fmt in {"webp", "png", "jpg"} for fmt in export_formats)),
                ("print_pdf", "pdf" in export_formats),
            )
            if enabled
        ],
    }


def text_renderer_preflight(
    root: Path,
    lettering: dict | None,
    text_language: str,
    font_path: str,
    usage: str,
) -> dict[str, Any]:
    """Select real renderers and glyph proof for the current lettering bytes."""
    publication_required = is_publish_like_usage(usage)
    selections: dict[str, dict[str, Any]] = {}
    glyph_receipts: list[dict[str, Any]] = []
    blockers: list[dict[str, str]] = []
    item_count = 0
    for item in (lettering or {}).get("items") or []:
        if not isinstance(item, dict):
            continue
        text = text_from_item(item, text_language)
        if not text:
            continue
        item_count += 1
        metadata = infer_language_metadata(text, text_language)
        style = item.get("style") if isinstance(item.get("style"), dict) else {}
        raw_direction = str(style.get("direction") or "horizontal").strip().lower()
        writing_mode = "vertical-rl" if raw_direction in {"vertical", "竖排", "縦書き", "縦書"} else "horizontal-tb"
        selection = text_renderer_adapter.select_renderer(
            language_mode=text_language,
            direction=str(metadata.get("dir") or "ltr"),
            writing_mode=writing_mode,
            root=root,
        )
        selections[str(selection.get("selection_sha256") or selection.get("adapter_id") or len(selections))] = selection
        glyph = text_renderer_adapter.validate_glyph_coverage(text, font_path=font_path)
        glyph_receipts.append({"item_id": str(item.get("item_id") or ""), **glyph})
        advanced = writing_mode.startswith("vertical") or metadata.get("dir") == "rtl" or metadata.get("line_break") in {"dictionary_required", "bidi_required"}
        if (publication_required or advanced) and not selection.get("publication_claim_allowed"):
            blockers.append({
                "item_id": str(item.get("item_id") or ""),
                "reason": "current text requires a real publication/complex-shaping renderer receipt",
            })
        if publication_required and glyph.get("status") != "pass":
            blockers.append({
                "item_id": str(item.get("item_id") or ""),
                "reason": f"glyph coverage is {glyph.get('status') or 'unknown'}; publication cannot claim complete font coverage",
            })
    return {
        "kind": "comic_text_renderer_preflight",
        "publication_required": publication_required,
        "item_count": item_count,
        "selections": list(selections.values()),
        "glyph_coverage_receipts": glyph_receipts,
        "blockers": blockers,
        "verdict": "block" if blockers else "pass",
    }


def panel_slot_info(panel: dict) -> dict[str, Any]:
    slots = {}
    for slot in panel.get("bubble_slots", []):
        sid = slot.get("slot_id")
        if sid:
            slots[sid] = slot
    return {"panel": panel, "slots": slots}


def cleanup_outputs(out_dir: Path, page_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    page_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("part_*.webp", "part_*.png", "part_*.jpg", "longstrip.webp", "longstrip.png", "longstrip.jpg"):
        for stale in out_dir.glob(pattern):
            stale.unlink()
    for pattern in ("page_*.webp", "page_*.png", "page_*.jpg"):
        for stale in page_dir.glob(pattern):
            stale.unlink()


def _canonical_json_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_input_digest(
    manifest: dict[str, Any],
    layout_path: Path,
    *,
    gap: int,
    background: str,
) -> str:
    preflight = (manifest.get("text_layout_qc") or {}).get("renderer_preflight") or {}
    stable_preflight = {
        "publication_required": preflight.get("publication_required"),
        "selections": [
            {
                key: item.get(key)
                for key in ("adapter_id", "status", "supports", "required_capabilities", "publication_claim_allowed", "selection_sha256")
            }
            for item in preflight.get("selections") or []
            if isinstance(item, dict)
        ],
        "glyph_coverage": [
            {
                key: item.get(key)
                for key in ("item_id", "status", "text_sha256", "font_sha256", "missing_glyphs")
            }
            for item in preflight.get("glyph_coverage_receipts") or []
            if isinstance(item, dict)
        ],
    }
    subject = {
        "layout_sha256": sha256_file(layout_path),
        "lettering_sha256": manifest.get("lettering_sha256", ""),
        "panels": [
            {key: item.get(key) for key in ("panel_id", "path", "sha256", "size_bytes")}
            for item in manifest.get("panels") or []
        ],
        "missing_panels": manifest.get("missing_panels") or [],
        "formats": manifest.get("export_formats") or [],
        "max_segment_height": manifest.get("max_segment_height"),
        "gap": int(gap),
        "background": str(background),
        "font": manifest.get("font", ""),
        "font_sha256": sha256_file(Path(str(manifest.get("font") or ""))) if manifest.get("font") else "",
        "text_language": manifest.get("text_language", ""),
        "target_platform": manifest.get("target_platform", ""),
        "platform_profile": manifest.get("platform_profile") or {},
        "platform_assets": manifest.get("platform_assets") or {},
        "text_renderer_preflight": stable_preflight,
    }
    return _canonical_json_sha(subject)


def _remove_exact(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.replace(pending, path)
    finally:
        if pending.exists():
            pending.unlink()


def begin_render_staging(chapter_dir: Path, digest: str) -> Path:
    # A digest identifies the render inputs, not a mutable scratch directory.
    # The attempt id prevents two equal-input renderers from deleting or
    # writing into each other's staging tree before the chapter promotion lock.
    attempt_id = uuid.uuid4().hex
    staging = chapter_dir / ".render_staging" / f"{digest}.{attempt_id}"
    (staging / "pages").mkdir(parents=True, exist_ok=True)
    (staging / "longstrip").mkdir(parents=True, exist_ok=True)
    (staging / "print").mkdir(parents=True, exist_ok=True)
    return staging


def stamp_and_validate_rendered_artifacts(manifest: dict[str, Any], root: Path) -> list[str]:
    """Decode every staged byte and bind its SHA/size before promotion."""
    errors: list[str] = []
    try:
        from PIL import Image
    except ImportError:
        Image = None  # type: ignore[assignment]
    for collection in ("pages", "rendered"):
        for item in manifest.get(collection) or []:
            if not isinstance(item, dict) or not item.get("path"):
                errors.append(f"{collection}: artifact path missing")
                continue
            path = root / str(item["path"])
            if not path.is_file():
                errors.append(f"{collection}: missing {item['path']}")
                continue
            try:
                if Image is None:
                    raise OSError("Pillow unavailable")
                with Image.open(path) as image:
                    image.load()
                    actual_size = {"width": int(image.width), "height": int(image.height)}
                if item.get("size") and item.get("size") != actual_size:
                    errors.append(f"{collection}: size mismatch {item['path']}")
                item["size"] = actual_size
                item["sha256"] = sha256_file(path)
                item["size_bytes"] = path.stat().st_size
            except (OSError, ValueError) as exc:
                errors.append(f"{collection}: undecodable {item['path']}: {exc}")
    for item in manifest.get("documents") or []:
        if not isinstance(item, dict) or not item.get("path"):
            errors.append("documents: artifact path missing")
            continue
        path = root / str(item["path"])
        if not path.is_file():
            errors.append(f"documents: missing {item['path']}")
            continue
        structural = pdf_structural_evidence(path) if str(item.get("format") or "").lower() == "pdf" else {}
        if structural and (not structural.get("header_valid") or not structural.get("eof_marker_present")):
            errors.append(f"documents: structurally invalid {item['path']}")
        item["sha256"] = sha256_file(path)
        item["size_bytes"] = path.stat().st_size
    for receipt in (manifest.get("lettering_stats") or {}).get("text_renderer_receipts") or []:
        if not isinstance(receipt, dict) or receipt.get("status") != "rendered":
            continue
        path = root / str(receipt.get("output_path") or "")
        if not path.is_file():
            errors.append(f"text overlay missing: {receipt.get('output_path') or '<empty>'}")
            continue
        if receipt.get("output_sha256") != sha256_file(path):
            errors.append(f"text overlay SHA mismatch: {receipt.get('output_path')}")
        try:
            if Image is None:
                raise OSError("Pillow unavailable")
            with Image.open(path) as image:
                image.verify()
        except (OSError, ValueError) as exc:
            errors.append(f"text overlay undecodable {receipt.get('output_path')}: {exc}")
    expected = [str(item.get("panel_id") or "") for item in manifest.get("panels") or []]
    actual = [str(pid) for page in manifest.get("pages") or [] for pid in page.get("panel_ids") or []]
    if not manifest.get("missing_panels") and expected != actual:
        errors.append("page panel order/coverage does not match the bound panel sequence")
    return errors


def _remap_strings(value: Any, replacements: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        for source, target in replacements:
            if value == source or value.startswith(source + "/"):
                return target + value[len(source):]
        return value
    if isinstance(value, list):
        return [_remap_strings(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _remap_strings(item, replacements) for key, item in value.items()}
    return value


def remap_staged_manifest(
    manifest: dict[str, Any],
    root: Path,
    mappings: list[tuple[Path, Path]],
) -> dict[str, Any]:
    replacements = [
        (str(source.relative_to(root)), str(target.relative_to(root)))
        for source, target in mappings
    ]
    return _remap_strings(manifest, replacements)


def _safe_journal_path(root: Path, raw: str) -> Path:
    if not str(raw or "").strip() or str(raw).strip() in {".", "/"}:
        raise RuntimeError("render promotion journal contains an empty/broad path")
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"render promotion journal escaped project root: {raw}") from exc
    if path == root.resolve():
        raise RuntimeError("render promotion journal may not target the project root")
    return path


@contextmanager
def chapter_render_lock(chapter_dir: Path) -> Iterator[None]:
    """Serialize chapter mirror/pointer mutations across OS processes."""
    chapter_dir.mkdir(parents=True, exist_ok=True)
    lock_path = chapter_dir / ".render_promotion.lock"
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _path_snapshot(path: Path) -> dict[str, Any]:
    """Content identity used by journal CAS; timestamps never count."""
    if path.is_symlink():
        raise RuntimeError(f"render transaction refuses symlink target: {path}")
    if not path.exists():
        return {"kind": "absent"}
    if path.is_file():
        return {
            "kind": "file",
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    if not path.is_dir():
        raise RuntimeError(f"unsupported render transaction path: {path}")
    entries: list[dict[str, Any]] = []
    total_size = 0
    for child in sorted(path.rglob("*"), key=lambda value: value.as_posix()):
        if child.is_symlink():
            raise RuntimeError(f"render transaction refuses symlink member: {child}")
        if not child.is_file():
            continue
        size_bytes = child.stat().st_size
        total_size += size_bytes
        entries.append({
            "path": child.relative_to(path).as_posix(),
            "sha256": sha256_file(child),
            "size_bytes": size_bytes,
        })
    return {
        "kind": "directory",
        "sha256": _canonical_json_sha(entries),
        "file_count": len(entries),
        "size_bytes": total_size,
    }


def _snapshot_matches(path: Path, expected: dict[str, Any]) -> bool:
    return _path_snapshot(path) == expected


def _asset_format(value: Any) -> str:
    return str(value or "").strip().lower().replace("jpeg", "jpg")


def _validate_bound_artifact(path: Path, item: dict[str, Any], collection: str) -> list[str]:
    errors: list[str] = []
    label = str(item.get("path") or path)
    if path.is_symlink() or not path.is_file():
        return [f"{collection}: missing/non-regular bound asset {label}"]
    expected_sha = str(item.get("sha256") or "")
    expected_size = item.get("size_bytes")
    if len(expected_sha) != 64:
        errors.append(f"{collection}: manifest SHA missing/invalid {label}")
    elif sha256_file(path) != expected_sha:
        errors.append(f"{collection}: SHA mismatch {label}")
    if not isinstance(expected_size, int):
        errors.append(f"{collection}: manifest byte size missing/invalid {label}")
    elif path.stat().st_size != expected_size:
        errors.append(f"{collection}: byte size mismatch {label}")

    expected_format = _asset_format(item.get("format"))
    if collection in {"pages", "rendered"}:
        try:
            from PIL import Image

            with Image.open(path) as image:
                image.load()
                actual_format = _asset_format(image.format or path.suffix.lstrip("."))
                actual_size = {"width": int(image.width), "height": int(image.height)}
            if not expected_format:
                errors.append(f"{collection}: manifest format missing {label}")
            elif actual_format != expected_format:
                errors.append(f"{collection}: decoded format mismatch {label}: {actual_format} != {expected_format}")
            if item.get("size") != actual_size:
                errors.append(f"{collection}: decoded geometry mismatch {label}")
        except (ImportError, OSError, ValueError) as exc:
            errors.append(f"{collection}: undecodable bound asset {label}: {exc}")
    elif collection == "documents":
        if expected_format == "pdf":
            structural = pdf_structural_evidence(path)
            if not structural.get("header_valid") or not structural.get("eof_marker_present"):
                errors.append(f"documents: structurally invalid PDF {label}")
        elif not expected_format:
            errors.append(f"documents: manifest format missing {label}")
    return errors


def _path_from_mapping(
    root: Path,
    raw_path: str,
    mappings: list[dict[str, str]],
    *,
    destination_key: str,
) -> Path:
    canonical = _safe_journal_path(root, raw_path)
    for mapping in mappings:
        source = _safe_journal_path(root, str(mapping.get("canonical") or ""))
        destination = _safe_journal_path(root, str(mapping.get(destination_key) or ""))
        kind = str(mapping.get("kind") or "directory")
        if kind == "file":
            if canonical == source:
                return destination
            continue
        try:
            relative = canonical.relative_to(source)
        except ValueError:
            continue
        return destination / relative
    raise RuntimeError(f"manifest asset is outside the render mapping contract: {raw_path}")


def validate_bound_manifest_assets(
    root: Path,
    manifest: dict[str, Any],
    *,
    mappings: list[dict[str, str]] | None = None,
    destination_key: str = "bundle",
) -> list[str]:
    """Validate every canonical page/rendered/document record without restamping it."""
    errors: list[str] = []
    for collection in ("pages", "rendered", "documents"):
        for item in manifest.get(collection) or []:
            if not isinstance(item, dict) or not item.get("path"):
                errors.append(f"{collection}: artifact path missing")
                continue
            try:
                path = (
                    _path_from_mapping(root, str(item["path"]), mappings, destination_key=destination_key)
                    if mappings is not None
                    else _safe_journal_path(root, str(item["path"]))
                )
            except RuntimeError as exc:
                errors.append(f"{collection}: {exc}")
                continue
            errors.extend(_validate_bound_artifact(path, item, collection))
    return errors


def _artifact_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    keys = ("path", "format", "size", "sha256", "size_bytes", "panel_ids")
    return {
        collection: [
            {key: item.get(key) for key in keys if key in item}
            for item in manifest.get(collection) or []
            if isinstance(item, dict)
        ]
        for collection in ("pages", "rendered", "documents")
    }


def _load_bundle_manifest(bundle: Path) -> dict[str, Any]:
    manifest_path = bundle / "export_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError(f"immutable render bundle manifest is missing/non-regular: {manifest_path}")
    return load_json(manifest_path)


def validate_active_render_state(root: Path, pointer: dict[str, Any]) -> list[str]:
    """Prove bundle, canonical manifest and canonical pixels are one transaction."""
    errors: list[str] = []
    try:
        bundle = _safe_journal_path(root, str(pointer.get("bundle") or ""))
        canonical_manifest_path = _safe_journal_path(root, str(pointer.get("manifest") or ""))
        bundle_manifest = _load_bundle_manifest(bundle)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]
    if bundle_manifest.get("render_digest") != pointer.get("render_digest"):
        errors.append("active pointer digest does not match immutable bundle manifest")
    bundle_manifest_path = bundle / "export_manifest.json"
    expected_manifest_sha = str(pointer.get("manifest_sha256") or "")
    if len(expected_manifest_sha) != 64 or sha256_file(bundle_manifest_path) != expected_manifest_sha:
        errors.append("active pointer bundle manifest SHA mismatch")
    if canonical_manifest_path.is_symlink() or not canonical_manifest_path.is_file():
        errors.append("canonical export manifest missing/non-regular")
    elif sha256_file(canonical_manifest_path) != expected_manifest_sha:
        errors.append("canonical export manifest differs from active bundle manifest")
    else:
        try:
            canonical_manifest = load_json(canonical_manifest_path)
            if canonical_manifest.get("render_digest") != pointer.get("render_digest"):
                errors.append("canonical export manifest digest differs from active pointer")
            if _artifact_contract(canonical_manifest) != _artifact_contract(bundle_manifest):
                errors.append("canonical export manifest artifact contract differs from active bundle")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"canonical export manifest unreadable: {exc}")
    mappings = pointer.get("asset_mappings") if isinstance(pointer.get("asset_mappings"), list) else []
    if not mappings:
        errors.append("active pointer lacks canonical-to-bundle asset mappings")
    else:
        errors.extend(validate_bound_manifest_assets(root, bundle_manifest, mappings=mappings, destination_key="bundle"))
    errors.extend(validate_bound_manifest_assets(root, bundle_manifest))
    return errors


def _journal_entries(root: Path, journal: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [item for item in journal.get("entries") or [] if isinstance(item, dict)]
    if not entries:
        raise RuntimeError("render promotion journal has no entries")
    targets: set[Path] = set()
    for item in entries:
        target = _safe_journal_path(root, str(item.get("target") or ""))
        _safe_journal_path(root, str(item.get("backup") or ""))
        _safe_journal_path(root, str(item.get("pending") or ""))
        if target in targets:
            raise RuntimeError(f"duplicate render promotion target: {target}")
        targets.add(target)
        if not isinstance(item.get("old_snapshot"), dict) or not isinstance(item.get("new_snapshot"), dict):
            raise RuntimeError("render promotion journal lacks content snapshots")
    return entries


def _cleanup_journal_entries(root: Path, entries: list[dict[str, Any]]) -> None:
    for item in entries:
        for key in ("backup", "pending"):
            path = _safe_journal_path(root, str(item.get(key) or ""))
            if path.exists() or path.is_symlink():
                _remove_exact(path)


def _rollback_journal_entries(root: Path, entries: list[dict[str, Any]]) -> None:
    for item in reversed(entries):
        target = _safe_journal_path(root, str(item.get("target") or ""))
        backup = _safe_journal_path(root, str(item.get("backup") or ""))
        pending = _safe_journal_path(root, str(item.get("pending") or ""))
        old_snapshot = item["old_snapshot"]
        new_snapshot = item["new_snapshot"]
        target_snapshot = _path_snapshot(target)
        backup_snapshot = _path_snapshot(backup)
        if old_snapshot.get("kind") != "absent":
            if backup_snapshot.get("kind") != "absent":
                if backup_snapshot != old_snapshot:
                    raise RuntimeError(f"rollback backup content mismatch: {backup}")
                if target_snapshot not in ({"kind": "absent"}, new_snapshot):
                    raise RuntimeError(f"rollback target contains an unknown concurrent value: {target}")
                if target_snapshot.get("kind") != "absent":
                    _remove_exact(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup, target)
            elif target_snapshot != old_snapshot:
                raise RuntimeError(f"rollback lost the expected old target: {target}")
        else:
            if backup_snapshot.get("kind") != "absent":
                raise RuntimeError(f"rollback found an unexpected backup: {backup}")
            if target_snapshot == new_snapshot and target_snapshot.get("kind") != "absent":
                _remove_exact(target)
            elif target_snapshot.get("kind") != "absent":
                raise RuntimeError(f"rollback target contains an unknown concurrent value: {target}")
        if pending.exists() or pending.is_symlink():
            if not _snapshot_matches(pending, new_snapshot):
                raise RuntimeError(f"rollback pending content mismatch: {pending}")
            _remove_exact(pending)
        if not _snapshot_matches(target, old_snapshot):
            raise RuntimeError(f"rollback could not restore target identity: {target}")


def _recover_interrupted_promotion_locked(root: Path, chapter_dir: Path) -> bool:
    journal_path = chapter_dir / ".render_promotion.json"
    if not journal_path.is_file():
        return False
    journal = load_json(journal_path)
    if int(journal.get("schema_version") or 0) < 2 or not journal.get("transaction_id"):
        raise RuntimeError("legacy digest-only promotion journal cannot be recovered safely; manual inspection required")
    pointer = _safe_journal_path(root, str(journal.get("active_pointer") or ""))
    entries = _journal_entries(root, journal)
    current_snapshot = _path_snapshot(pointer)
    expected_old = journal.get("expected_old_pointer") or {}
    expected_new = journal.get("new_pointer_snapshot") or {}
    active: dict[str, Any] = {}
    if pointer.is_file():
        try:
            active = load_json(pointer)
        except (OSError, ValueError, json.JSONDecodeError):
            active = {}
    committed = (
        current_snapshot == expected_new
        and active.get("transaction_id") == journal.get("transaction_id")
        and active.get("render_digest") == journal.get("render_digest")
    )
    pointer_entry = next(
        (
            item
            for item in entries
            if _safe_journal_path(root, str(item.get("target") or "")) == pointer
        ),
        None,
    )
    pointer_between_renames = False
    if pointer_entry is not None and current_snapshot.get("kind") == "absent":
        pointer_backup = _safe_journal_path(root, str(pointer_entry.get("backup") or ""))
        pointer_between_renames = _path_snapshot(pointer_backup) == expected_old
    if committed:
        snapshot_errors = []
        for item in entries:
            target = _safe_journal_path(root, str(item.get("target") or ""))
            if not _snapshot_matches(target, item["new_snapshot"]):
                snapshot_errors.append(f"promoted target identity mismatch: {target}")
        state_errors = validate_active_render_state(root, active)
        if snapshot_errors or state_errors:
            _rollback_journal_entries(root, entries)
        else:
            _cleanup_journal_entries(root, entries)
    elif current_snapshot == expected_old or pointer_between_renames:
        _rollback_journal_entries(root, entries)
    else:
        raise RuntimeError(
            "active pointer CAS conflict: it matches neither the journal's expected old pointer nor this transaction"
        )
    journal_path.unlink()
    return True


def recover_interrupted_promotion(root: Path, chapter_dir: Path) -> bool:
    """Recover under the chapter flock; transaction id prevents digest ABA."""
    with chapter_render_lock(chapter_dir):
        return _recover_interrupted_promotion_locked(root, chapter_dir)


def _prepare_copy(source: Path | None, target: Path, digest: str, transaction_id: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_name(f".{target.name}.{digest}.{transaction_id}.pending")
    if pending.exists() or pending.is_symlink():
        _remove_exact(pending)
    if source is not None:
        if source.is_dir():
            shutil.copytree(source, pending)
        else:
            shutil.copy2(source, pending)
    return pending


def _atomic_promote_bundle_mirrors_locked(
    root: Path,
    chapter_dir: Path,
    digest: str,
    prepared: list[tuple[Path, Path]],
    active_pointer: Path,
    *,
    transaction_id: str,
    expected_old_pointer: dict[str, Any],
    pointer_payload: dict[str, Any],
) -> None:
    """Promote verified mirrors with byte-level pointer CAS; lock is held."""
    if not prepared or prepared[-1][1].resolve() != active_pointer.resolve():
        raise RuntimeError("active pointer must be the final promotion entry")
    if not _snapshot_matches(active_pointer, expected_old_pointer):
        raise RuntimeError("active pointer changed before promotion (CAS failed)")
    entries: list[dict[str, Any]] = []
    for pending, target in prepared:
        backup = target.with_name(f".{target.name}.{digest}.{transaction_id}.backup")
        if backup.exists() or backup.is_symlink():
            _remove_exact(backup)
        new_snapshot = _path_snapshot(pending)
        entries.append({
            "pending": str(pending.relative_to(root)),
            "target": str(target.relative_to(root)),
            "backup": str(backup.relative_to(root)),
            "old_snapshot": _path_snapshot(target),
            "new_snapshot": new_snapshot,
        })
    pointer_new_snapshot = entries[-1]["new_snapshot"]
    journal = {
        "schema_version": 2,
        "kind": "comic_render_promotion_journal",
        "transaction_id": transaction_id,
        "render_digest": digest,
        "active_pointer": str(active_pointer.relative_to(root)),
        "expected_old_pointer": expected_old_pointer,
        "new_pointer_snapshot": pointer_new_snapshot,
        "bundle": pointer_payload.get("bundle", ""),
        "bundle_manifest_sha256": pointer_payload.get("manifest_sha256", ""),
        "entries": entries,
    }
    journal_path = chapter_dir / ".render_promotion.json"
    _atomic_write_json(journal_path, journal)
    try:
        for item in entries:
            target = _safe_journal_path(root, item["target"])
            backup = _safe_journal_path(root, item["backup"])
            pending = _safe_journal_path(root, item["pending"])
            if not _snapshot_matches(target, item["old_snapshot"]):
                raise RuntimeError(f"promotion target changed after journal creation: {target}")
            if not _snapshot_matches(pending, item["new_snapshot"]):
                raise RuntimeError(f"promotion pending bytes changed after journal creation: {pending}")
            if item["old_snapshot"].get("kind") != "absent":
                os.replace(target, backup)
            if item["new_snapshot"].get("kind") != "absent":
                os.replace(pending, target)
            if not _snapshot_matches(target, item["new_snapshot"]):
                raise RuntimeError(f"promotion target verification failed: {target}")
            if target.resolve() == active_pointer.resolve():
                active = load_json(active_pointer)
                if active.get("transaction_id") != transaction_id:
                    raise RuntimeError("active pointer transaction id mismatch after CAS")
        state_errors = validate_active_render_state(root, pointer_payload)
        if state_errors:
            raise RuntimeError("promoted render state failed validation: " + "; ".join(state_errors))
        _cleanup_journal_entries(root, entries)
        journal_path.unlink()
    except BaseException:
        _recover_interrupted_promotion_locked(root, chapter_dir)
        raise


def atomic_promote_bundle_mirrors(
    root: Path,
    chapter_dir: Path,
    digest: str,
    prepared: list[tuple[Path, Path]],
    active_pointer: Path,
    *,
    transaction_id: str,
    expected_old_pointer: dict[str, Any],
    pointer_payload: dict[str, Any],
) -> None:
    """Public locked wrapper for direct callers and fault-injection tests."""
    with chapter_render_lock(chapter_dir):
        _recover_interrupted_promotion_locked(root, chapter_dir)
        _atomic_promote_bundle_mirrors_locked(
            root,
            chapter_dir,
            digest,
            prepared,
            active_pointer,
            transaction_id=transaction_id,
            expected_old_pointer=expected_old_pointer,
            pointer_payload=pointer_payload,
        )


def finalize_render_bundle(
    root: Path,
    chapter_dir: Path,
    staging: Path,
    digest: str,
    manifest: dict[str, Any],
    *,
    page_dir: Path,
    out_dir: Path,
    pdf_path: Path,
    manifest_path: Path,
    qc_target: Path | None,
    activate: bool,
) -> Path:
    bundle = chapter_dir / ".render_bundles" / digest
    bundle.parent.mkdir(parents=True, exist_ok=True)
    (staging / "export_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    asset_mappings = [
        {
            "kind": "directory",
            "canonical": str(page_dir.relative_to(root)),
            "bundle": str((bundle / "pages").relative_to(root)),
            "staging": str((staging / "pages").relative_to(root)),
        },
        {
            "kind": "directory",
            "canonical": str(out_dir.relative_to(root)),
            "bundle": str((bundle / "longstrip").relative_to(root)),
            "staging": str((staging / "longstrip").relative_to(root)),
        },
        {
            "kind": "file",
            "canonical": str(pdf_path.relative_to(root)),
            "bundle": str((bundle / "print" / pdf_path.name).relative_to(root)),
            "staging": str((staging / "print" / pdf_path.name).relative_to(root)),
        },
    ]
    staging_errors = validate_bound_manifest_assets(root, manifest, mappings=asset_mappings, destination_key="staging")
    if staging_errors:
        raise RuntimeError("staged render bundle failed immutable validation: " + "; ".join(staging_errors))

    with chapter_render_lock(chapter_dir):
        _recover_interrupted_promotion_locked(root, chapter_dir)
        if bundle.exists():
            existing = _load_bundle_manifest(bundle)
            bundle_errors = validate_bound_manifest_assets(root, existing, mappings=asset_mappings, destination_key="bundle")
            if existing.get("render_digest") != digest:
                bundle_errors.append("render digest collision with an incompatible immutable bundle")
            active_pointer_path = chapter_dir / "active_render_bundle.json"
            if active_pointer_path.is_file():
                try:
                    current_pointer = load_json(active_pointer_path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    bundle_errors.append(f"active pointer unreadable while reusing bundle: {exc}")
                else:
                    if str(current_pointer.get("bundle") or "") == str(bundle.relative_to(root)):
                        if current_pointer.get("manifest_sha256") != sha256_file(bundle / "export_manifest.json"):
                            bundle_errors.append("active pointer proves the same-digest bundle manifest was mutated")
            if _artifact_contract(existing) != _artifact_contract(manifest):
                bundle_errors.append("same-digest immutable bundle artifact contract differs from current validated staging")
            if bundle_errors:
                # Preserve both the suspect immutable directory and the newly
                # validated attempt for diagnosis; never silently discard the
                # only safe reconstruction candidate.
                raise RuntimeError("existing immutable render bundle is untrusted: " + "; ".join(bundle_errors))
            _remove_exact(staging)
        else:
            os.replace(staging, bundle)
            bundle_errors = validate_bound_manifest_assets(root, manifest, mappings=asset_mappings, destination_key="bundle")
            if bundle_errors:
                raise RuntimeError("new immutable render bundle failed post-move validation: " + "; ".join(bundle_errors))

        transaction_id = uuid.uuid4().hex
        prepared: list[tuple[Path, Path]] = [
            (_prepare_copy(bundle / "pages", page_dir, digest, transaction_id), page_dir),
            (_prepare_copy(bundle / "longstrip", out_dir, digest, transaction_id), out_dir),
        ]
        bundle_pdf = bundle / "print" / pdf_path.name
        prepared.append((_prepare_copy(bundle_pdf if bundle_pdf.is_file() else None, pdf_path, digest, transaction_id), pdf_path))
        if qc_target is not None:
            bundle_qc = bundle / "qc" / qc_target.name
            if bundle_qc.is_file():
                prepared.append((_prepare_copy(bundle_qc, qc_target, digest, transaction_id), qc_target))
        prepared.append((_prepare_copy(bundle / "export_manifest.json", manifest_path, digest, transaction_id), manifest_path))

        active_pointer = chapter_dir / "active_render_bundle.json"
        expected_old_pointer = _path_snapshot(active_pointer)
        if not activate:
            raise RuntimeError("validated render bundles currently require active-pointer promotion")
        pointer_payload = {
            "schema_version": 2,
            "kind": "comic_active_render_bundle",
            "transaction_id": transaction_id,
            "chapter": manifest.get("chapter", ""),
            "render_digest": digest,
            "bundle": str(bundle.relative_to(root)),
            "manifest": str(manifest_path.relative_to(root)),
            "manifest_sha256": sha256_file(bundle / "export_manifest.json"),
            "previous_pointer": expected_old_pointer,
            "asset_mappings": [
                {key: value for key, value in mapping.items() if key != "staging"}
                for mapping in asset_mappings
            ],
        }
        pointer_pending = _prepare_copy(None, active_pointer, digest, transaction_id)
        pointer_pending.write_text(json.dumps(pointer_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        prepared.append((pointer_pending, active_pointer))
        _atomic_promote_bundle_mirrors_locked(
            root,
            chapter_dir,
            digest,
            prepared,
            active_pointer,
            transaction_id=transaction_id,
            expected_old_pointer=expected_old_pointer,
            pointer_payload=pointer_payload,
        )
    return bundle


def render_pdf_document(
    manifest: dict[str, Any],
    root: Path,
    chapter: str,
    page_canvases: list[tuple[dict[str, Any], Any]],
    pdf_path: Path,
) -> dict[str, Any]:
    """Write a rasterized multi-page PDF and register reproducible evidence.

    Pillow's PDF backend is deliberately treated as an interior-page raster
    package, not as a PDF/X substitute.  Fonts are flattened into page pixels;
    ICC/output intent and printer-specific boxes remain print-preflight facts.
    """
    if not page_canvases:
        raise RuntimeError("没有可写入 PDF 的页面图。")
    dpi, dpi_source = print_resolution(root, chapter)
    pages = [canvas.convert("RGB") for _meta, canvas in page_canvases]
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pending = pdf_path.with_name(f".{pdf_path.name}.{os.getpid()}.pending")
    try:
        pages[0].save(
            pending,
            format="PDF",
            save_all=True,
            append_images=pages[1:],
            resolution=float(dpi),
        )
        os.replace(pending, pdf_path)
    finally:
        if pending.exists():
            pending.unlink()
    source_pages: list[dict[str, Any]] = []
    for (meta, _canvas), page in zip(page_canvases, pages):
        source_path = root / str(meta.get("path") or "")
        source_pages.append(
            {
                "path": str(meta.get("path") or ""),
                "sha256": sha256_file(source_path) if source_path.is_file() else "",
                "pixel_size": {"width": page.width, "height": page.height},
                "mode": page.mode,
                "has_alpha": "A" in page.getbands(),
                "physical_size_mm": {
                    "width": round(page.width / dpi * 25.4, 4),
                    "height": round(page.height / dpi * 25.4, 4),
                },
            }
        )
    structural = pdf_structural_evidence(pdf_path)
    return {
        "path": str(pdf_path.relative_to(root)),
        "format": "pdf",
        "mime_type": "application/pdf",
        "role": "print_interior_raster_pdf",
        "sha256": sha256_file(pdf_path),
        "size_bytes": pdf_path.stat().st_size,
        "page_count": len(pages),
        "page_order": [str(meta.get("path") or "") for meta, _canvas in page_canvases],
        "dpi": dpi,
        "dpi_source": dpi_source,
        "color_mode": "RGB",
        "transparency": "flattened",
        "font_handling": {
            "mode": "rasterized",
            "embedded_fonts_required": False,
            "proof": "page text flattened before PDF serialization; structural scan must show zero /Font objects",
        },
        "source_pages": source_pages,
        "structural_evidence": structural,
        "generator": "Pillow multi-page PDF",
        "limitations": [
            "Raster interior-page PDF; not automatically PDF/X compliant.",
            "No automatic crop/trim/bleed box, output intent, overprint, spine or cover imposition.",
            "Print readiness requires print_delivery_contract.json plus SHA-bound print_readiness_receipt.",
        ],
    }


def merge_lettering_stats(total: dict[str, Any], stats: dict[str, Any]) -> None:
    total["drawn_items"] += stats["drawn_items"]
    total["skipped_empty_items"].extend(stats["skipped_empty_items"])
    total["empty_slots_removed"].extend(stats["empty_slots_removed"])
    total["tail_receipts"].extend(stats.get("tail_receipts") or [])
    total["text_renderer_receipts"].extend(stats.get("text_renderer_receipts") or [])
    total["glyph_coverage_receipts"].extend(stats.get("glyph_coverage_receipts") or [])


def render_layout_pages(
    manifest: dict,
    root: Path,
    page_dir: Path,
    background: str,
    layout: dict,
    lettering: dict | None,
    text_language: str,
    export_formats: list[str],
    raster_dpi: float | None = None,
) -> tuple[list[tuple[dict[str, Any], Any]], dict[str, Any]]:
    from PIL import Image

    panel_items = {item["panel_id"]: item for item in manifest["panels"]}
    lettering_items = lettering_by_panel(lettering or {})
    font_path = manifest.get("font", "")
    language_mode = normalize_text_language(text_language)
    rendered_pages: list[tuple[dict[str, Any], Any]] = []
    lettering_stats = {
        "drawn_items": 0,
        "skipped_empty_items": [],
        "empty_slots_removed": [],
        "tail_receipts": [],
        "text_renderer_receipts": [],
        "glyph_coverage_receipts": [],
    }

    for idx, segment in enumerate(layout.get("segments", []), 1):
        panels = segment_panels_in_reading_order(segment)
        width = int(segment.get("width") or max((float(p.get("x", 0)) + float(p.get("w", 0)) for p in panels), default=0))
        height = int(segment.get("height") or max((float(p.get("y", 0)) + float(p.get("h", 0)) for p in panels), default=0))
        if width <= 0 or height <= 0:
            continue
        canvas = Image.new("RGB", (width, height), background)
        page_panel_ids: list[str] = []
        for panel in panels:
            pid = str(panel.get("panel_id") or "")
            item = panel_items.get(pid)
            if not item:
                continue
            try:
                image = Image.open(root / item["path"]).convert("RGB")
            except (OSError, ValueError):
                # Present but truncated/corrupt panel: surface it through the same
                # missing-panels channel that already blocks completion, instead
                # of aborting the whole deliverable render with a traceback.
                if pid not in manifest["missing_panels"]:
                    manifest["missing_panels"].append(pid)
                continue
            item["source_size"] = {"width": image.width, "height": image.height}
            target_w = int(panel.get("w") or image.width)
            target_h = int(panel.get("h") or image.height)
            if image.size != (target_w, target_h):
                image = image.resize((target_w, target_h))
            image, stats = apply_lettering(
                image,
                pid,
                panel_slot_info(panel),
                lettering_items.get(pid, []),
                font_path,
                language_mode,
                {
                    "root": root,
                    "overlay_dir": page_dir / "text_overlays",
                    "text_language": language_mode,
                    "publication_required": bool(manifest.get("publication_text_required")),
                },
            )
            merge_lettering_stats(lettering_stats, stats)
            item["size"] = {"width": image.width, "height": image.height}
            canvas.paste(image, (int(panel.get("x") or 0), int(panel.get("y") or 0)))
            page_panel_ids.append(pid)

        fmt = choose_output_format(export_formats, canvas.width, canvas.height)
        page_path = page_dir / f"page_{idx:03d}.{fmt}"
        save_canvas(canvas, page_path, fmt, raster_dpi)
        meta = {
            "path": str(page_path.relative_to(root)),
            "segment_id": segment.get("segment_id", f"S{idx:03d}"),
            "panel_ids": page_panel_ids,
            "size": {"width": canvas.width, "height": canvas.height},
            "format": fmt,
            "dpi": raster_dpi,
        }
        rendered_pages.append((meta, canvas))

    return rendered_pages, lettering_stats


def combine_pages(page_canvases: list[tuple[dict[str, Any], Any]], gap: int, background: str):
    from PIL import Image

    width = max(canvas.width for _meta, canvas in page_canvases)
    height = sum(canvas.height for _meta, canvas in page_canvases) + gap * max(0, len(page_canvases) - 1)
    combined = Image.new("RGB", (width, height), background)
    y = 0
    panel_ids: list[str] = []
    for meta, canvas in page_canvases:
        x = math.floor((width - canvas.width) / 2)
        combined.paste(canvas, (x, y))
        y += canvas.height + gap
        panel_ids.extend(meta.get("panel_ids") or [])
    return combined, panel_ids


def render_longstrip(
    manifest: dict,
    root: Path,
    out_dir: Path,
    page_dir: Path,
    max_height: int,
    gap: int,
    background: str,
    layout: dict,
    lettering: dict | None,
    text_language: str,
    export_formats: list[str],
    chapter: str,
    pdf_path: Path,
    raster_dpi: float | None = None,
) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow 未安装；已可生成 manifest，如需渲染长图请先安装 Pillow。") from exc

    language_mode = normalize_text_language(text_language)
    cleanup_outputs(out_dir, page_dir)
    page_canvases, lettering_stats = render_layout_pages(
        manifest, root, page_dir, background, layout, lettering, language_mode, export_formats, raster_dpi
    )
    manifest["pages"] = [meta for meta, _canvas in page_canvases]
    if not page_canvases:
        return

    if "pdf" in export_formats:
        manifest["documents"] = [render_pdf_document(manifest, root, chapter, page_canvases, pdf_path)]

    raster_formats = [fmt for fmt in export_formats if fmt in {"webp", "png", "jpg"}]
    if not raster_formats:
        manifest["rendered"] = []
        manifest["lettering_rendered"] = lettering_stats["drawn_items"] > 0
        manifest["text_language"] = language_mode
        manifest["bilingual_lettering"] = bool(
            language_mode in ("中上英下", "英上中下")
            and any(item.get("text_en") for item in (lettering or {}).get("items", []))
        )
        manifest["lettering_stats"] = lettering_stats
        manifest["lettering_render_receipt"] = {
            "kind": "comic_lettering_render_receipt",
            "tail_targets": lettering_stats.get("tail_receipts") or [],
            "resolved_tail_count": sum(bool(item.get("target_resolved")) for item in lettering_stats.get("tail_receipts") or []),
            "fallback_tail_count": sum(not bool(item.get("target_resolved")) for item in lettering_stats.get("tail_receipts") or []),
        }
        return

    combined, panel_ids = combine_pages(page_canvases, gap, background)
    rendered = []
    if max_height <= 0:
        fmt = choose_output_format(raster_formats, combined.width, combined.height)
        out_name = f"longstrip.{fmt}"
        out_path = out_dir / out_name
        save_canvas(combined, out_path, fmt, raster_dpi)
        rendered.append(
            {
                "path": str(out_path.relative_to(root)),
                "panel_ids": panel_ids,
                "size": {"width": combined.width, "height": combined.height},
                "format": fmt,
                "dpi": raster_dpi,
            }
        )
    else:
        y = 0
        idx = 1
        while y < combined.height:
            bottom = min(combined.height, y + max_height)
            crop = combined.crop((0, y, combined.width, bottom))
            fmt = choose_output_format(raster_formats, crop.width, crop.height)
            out_path = out_dir / f"part_{idx:03d}.{fmt}"
            save_canvas(crop, out_path, fmt, raster_dpi)
            rendered.append(
                {
                    "path": str(out_path.relative_to(root)),
                    "panel_ids": panel_ids,
                    "size": {"width": crop.width, "height": crop.height},
                    "y_range": [y, bottom],
                    "format": fmt,
                    "dpi": raster_dpi,
                }
            )
            y = bottom
            idx += 1
    manifest["rendered"] = rendered
    manifest["lettering_rendered"] = lettering_stats["drawn_items"] > 0
    manifest["text_language"] = language_mode
    manifest["bilingual_lettering"] = bool(
        language_mode in ("中上英下", "英上中下")
        and any(item.get("text_en") for item in (lettering or {}).get("items", []))
    )
    manifest["lettering_stats"] = lettering_stats
    manifest["lettering_render_receipt"] = {
        "kind": "comic_lettering_render_receipt",
        "tail_targets": lettering_stats.get("tail_receipts") or [],
        "resolved_tail_count": sum(bool(item.get("target_resolved")) for item in lettering_stats.get("tail_receipts") or []),
        "fallback_tail_count": sum(not bool(item.get("target_resolved")) for item in lettering_stats.get("tail_receipts") or []),
    }


def slot_records(layout: dict) -> dict[tuple[str, str], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for idx, segment in enumerate(layout.get("segments", []), 1):
        segment_id = str(segment.get("segment_id") or f"S{idx:03d}")
        for panel in segment.get("panels", []):
            pid = str(panel.get("panel_id") or "")
            if not pid:
                continue
            for slot in panel.get("bubble_slots", []):
                sid = str(slot.get("slot_id") or "")
                if sid:
                    records[(pid, sid)] = {"segment_id": segment_id, "slot": slot}
    return records


def build_page_map(manifest: dict, root: Path) -> dict[str, Any]:
    from PIL import Image

    pages: dict[str, Any] = {}
    for page in manifest.get("pages") or []:
        segment_id = str(page.get("segment_id") or "")
        page_path = page.get("path")
        if segment_id and page_path:
            try:
                pages[segment_id] = Image.open(root / page_path).convert("RGB")
            except (OSError, ValueError):
                continue
    return pages


def save_lettering_qc_sheet(
    manifest: dict,
    root: Path,
    layout: dict,
    lettering: dict | None,
    out_path: Path,
    *,
    thumb_w: int = 360,
    thumb_h: int = 170,
    cols: int = 4,
) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    items = (lettering or {}).get("items") or []
    if not items:
        return {"path": "", "items": 0, "missing_slots": []}
    pages = build_page_map(manifest, root)
    slots = slot_records(layout)
    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    label_font = load_font(18, manifest.get("font", ""))
    missing_slots: list[str] = []
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    for idx, item in enumerate(items):
        row, col = divmod(idx, cols)
        x0, y0 = col * thumb_w, row * thumb_h
        text = str(item.get("text_zh") or item.get("text") or item.get("text_en") or "")
        label = f"{item.get('item_id')} {item.get('panel_id')} {item.get('type')} {text}"
        draw.rectangle((x0, y0, x0 + thumb_w - 1, y0 + 23), fill=(25, 25, 25))
        draw.text((x0 + 6, y0 + 3), label[:36], font=label_font, fill=(255, 255, 255))

        pid = str(item.get("panel_id") or "")
        sid = str(item.get("slot_id") or "")
        record = slots.get((pid, sid))
        if not record:
            missing_slots.append(f"{pid}:{sid}")
            continue
        page = pages.get(record["segment_id"])
        if page is None:
            missing_slots.append(f"{pid}:{sid}")
            continue
        slot = record["slot"]
        pad = 60
        left = max(0, int(slot.get("x", 0) or 0) - pad)
        top = max(0, int(slot.get("y", 0) or 0) - pad)
        right = min(page.width, int((slot.get("x", 0) or 0) + (slot.get("w", 0) or 0)) + pad)
        bottom = min(page.height, int((slot.get("y", 0) or 0) + (slot.get("h", 0) or 0)) + pad)
        if right <= left or bottom <= top:
            missing_slots.append(f"{pid}:{sid}")
            continue
        crop = page.crop((left, top, right, bottom))
        crop.thumbnail((thumb_w, thumb_h - 28), resampling)
        sheet.paste(crop, (x0 + (thumb_w - crop.width) // 2, y0 + 24))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)
    return {"path": str(out_path.relative_to(root)), "items": len(items), "missing_slots": missing_slots}


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画长图导出 manifest/渲染")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--layout", default=None)
    parser.add_argument("--panel-dir", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--page-dir", default=None)
    parser.add_argument("--lettering", default=None)
    parser.add_argument("--no-lettering", action="store_true")
    parser.add_argument("--font", default=None)
    parser.add_argument("--formats", default=None, help="导出格式，如 webp、png、webp+png 或 pdf；默认读 _设置.md 的 导出格式")
    parser.add_argument("--pdf-out", default=None, help="PDF 输出路径；默认 排版/<话>/print/<话>.pdf")
    parser.add_argument("--platform-asset", action="append", default=[], metavar="NAME=PATH", help="登记真实平台缩略图，如 series_square=cover.png；可重复")
    parser.add_argument("--max-height", default=None, help="最大分段高度；0/不分段/单张 表示导出一张 longstrip.webp")
    parser.add_argument("--gap", type=int, default=24)
    parser.add_argument("--background", default="#ffffff")
    parser.add_argument("--render", action="store_true", help="用 Pillow 实际渲染长图")
    parser.add_argument("--write-progress", action="store_true", help="导出成功后回写 _进度.md 的 嵌字合成")
    parser.add_argument("--qc-slots", action="store_true", help="渲染后输出嵌字槽位 QC 接触表")
    parser.add_argument("--qc-out", default=None, help="嵌字槽位 QC 接触表输出路径")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    layout_path = Path(args.layout).expanduser().resolve() if args.layout else root / "排版" / args.chapter / "layout.json"
    panel_dir = Path(args.panel_dir).expanduser().resolve() if args.panel_dir else root / "出图" / args.chapter / "panels"
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else root / "排版" / args.chapter / "长图"
    page_dir = Path(args.page_dir).expanduser().resolve() if args.page_dir else root / "排版" / args.chapter / "pages"
    pdf_path = Path(args.pdf_out).expanduser().resolve() if args.pdf_out else root / "排版" / args.chapter / "print" / f"{args.chapter}.pdf"
    lettering_path = None if args.no_lettering else (Path(args.lettering).expanduser().resolve() if args.lettering else root / "排版" / args.chapter / "lettering.json")
    font_path = resolve_font_path(args.font)
    chapter_dir = root / "排版" / args.chapter
    manifest_path = chapter_dir / "export_manifest.json"
    try:
        recovered = recover_interrupted_promotion(root, chapter_dir)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"[err] 无法安全恢复上次渲染提升事务：{exc}")
        return 2
    if recovered:
        print("[ok] recovered interrupted render promotion")

    if not layout_path.is_file():
        print(f"[err] layout 不存在：{layout_path}")
        return 2
    if lettering_path is not None and not lettering_path.is_file():
        print(f"[err] lettering 不存在：{lettering_path}；如只需无字内部预览，请显式传 --no-lettering")
        return 2
    if lettering_path is not None:
        contract_report = lettering_contract.analyze(root, args.chapter, lettering_path)
        blockers = [
            item
            for item in contract_report.get("findings") or []
            if item.get("severity") == "block"
        ]
        if blockers:
            print("[err] lettering 版本合同未通过，拒绝用旧文字生成新 manifest/渲染物：")
            for item in blockers[:20]:
                print(f"  - {item.get('code')}: {item.get('reason')}")
            print("[hint] 重跑 build_lettering.py，处理 editorial_override/翻译表后再导出。")
            return 2
    panel_dir.mkdir(parents=True, exist_ok=True)
    layout = load_json(layout_path)
    lettering = load_json(lettering_path) if lettering_path and lettering_path.is_file() else None
    max_height = parse_max_height(args.max_height, parse_max_height(read_setting(root, "单话分段高度", "0")))
    export_formats = parse_export_formats(args.formats or read_setting(root, "导出格式", "webp"))
    manifest = build_manifest(
        root,
        args.chapter,
        layout_path,
        panel_dir,
        out_dir,
        page_dir,
        max_height,
        lettering_path,
        font_path,
        export_formats,
    )
    if not export_formats:
        manifest["format_error"] = "导出格式没有可执行适配：请使用 webp/png/jpg/pdf 或补自定义 renderer；未静默回退。"
    text_language = normalize_text_language(read_setting(root, "文字语言", (lettering or {}).get("language_mode", "中文") if lettering else "中文"))
    target_platform = read_setting(root, "目标平台", "通用")
    usage = read_setting(root, "合规用途", "自用草稿")
    platform_profile = profile_for_platform(target_platform)
    raster_dpi = float(platform_profile.required_dpi) if platform_profile.required_dpi else None
    manifest["text_language"] = text_language
    manifest["target_platform"] = target_platform
    manifest["platform_profile"] = platform_profile.to_manifest()
    renderer_preflight = text_renderer_preflight(root, lettering, text_language, font_path, usage)
    manifest["publication_text_required"] = renderer_preflight["publication_required"]
    platform_asset_args = list(args.platform_asset)
    previous_manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    previous_assets = previous_manifest.get("platform_assets") if isinstance(previous_manifest.get("platform_assets"), dict) else {}
    explicit_names = {raw.split("=", 1)[0].strip() for raw in platform_asset_args if "=" in raw}
    for asset_name, record in previous_assets.items():
        if asset_name not in explicit_names and isinstance(record, dict) and record.get("path"):
            platform_asset_args.append(f"{asset_name}={record['path']}")
    manifest["platform_assets"], manifest["platform_assets_missing"] = collect_platform_assets(
        root, platform_asset_args, platform_profile
    )
    unsupported_text = unsupported_lettering_items(lettering, text_language)
    manifest["text_layout_qc"] = {
        "renderer_preflight": renderer_preflight,
        "unsupported_items": unsupported_text,
        "verdict": renderer_preflight["verdict"],
    }
    render_digest = render_input_digest(manifest, layout_path, gap=args.gap, background=args.background)
    manifest["render_digest"] = render_digest
    staging = begin_render_staging(chapter_dir, render_digest) if args.render else None
    render_out_dir = staging / "longstrip" if staging is not None else out_dir
    render_page_dir = staging / "pages" if staging is not None else page_dir
    render_pdf_path = staging / "print" / pdf_path.name if staging is not None else pdf_path

    if args.render and renderer_preflight["blockers"]:
        manifest["render_error"] = "当前文字缺少专业 renderer 或完整 glyph coverage 的真实收据；未按 Pillow 静默降级。"
        print(f"[warn] {manifest['render_error']}")
    elif args.render and export_formats:
        try:
            render_longstrip(
                manifest,
                root,
                render_out_dir,
                render_page_dir,
                max_height,
                args.gap,
                args.background,
                layout,
                lettering,
                text_language,
                export_formats,
                args.chapter,
                render_pdf_path,
                raster_dpi,
            )
        except (RuntimeError, OSError, ValueError) as err:
            manifest["render_error"] = str(err)
            print(f"[warn] {err}")

    actual_text_receipts = ((manifest.get("lettering_stats") or {}).get("text_renderer_receipts") or [])
    if renderer_preflight["publication_required"] and renderer_preflight["item_count"]:
        publication_render_ok = bool(actual_text_receipts) and all(
            item.get("status") == "rendered" and item.get("publication_claim_allowed") is True
            for item in actual_text_receipts
        )
        if not publication_render_ok:
            manifest["text_layout_qc"]["verdict"] = "block"
            manifest["text_layout_qc"]["publication_render_error"] = "发布态缺少覆盖当前文字像素的 rendered receipt"
    manifest["text_layout_qc"]["actual_render_receipts"] = actual_text_receipts
    artifact_errors = stamp_and_validate_rendered_artifacts(manifest, root) if args.render else []
    manifest["render_bundle_validation"] = {
        "kind": "comic_render_bundle_validation",
        "decoded_artifact_count": len(manifest.get("pages") or []) + len(manifest.get("rendered") or []) + len(manifest.get("documents") or []),
        "errors": artifact_errors,
        "verdict": "block" if artifact_errors else "pass",
    }

    produced_formats = {
        str(item.get("format") or "").lower()
        for item in (manifest.get("rendered") or []) + (manifest.get("documents") or [])
        if isinstance(item, dict)
    }
    raster_requested = any(fmt in {"webp", "png", "jpg"} for fmt in export_formats)
    raster_produced = bool(produced_formats & {"webp", "png", "jpg"})
    missing_formats = []
    if raster_requested and not raster_produced:
        missing_formats.append("raster_image")
    if "pdf" in export_formats and "pdf" not in produced_formats:
        missing_formats.append("pdf")
    manifest["format_fulfillment"] = {
        "requested": export_formats,
        "produced": sorted(produced_formats),
        "missing": missing_formats,
        "raster_formats_are_priority_fallbacks": True,
        "verdict": "pass" if export_formats and not missing_formats else "block",
    }
    if "pdf" in export_formats and "pdf" not in produced_formats:
        manifest["pdf_export_error"] = manifest.get("render_error") or "PDF 已请求但未生成；需要 --render 与 Pillow。"

    manifest["platform_findings"] = validate_manifest(root, manifest, platform_profile, usage)

    qc_target: Path | None = None
    if args.qc_slots and args.render and manifest.get("pages") and staging is not None:
        qc_target = (
            Path(args.qc_out).expanduser().resolve()
            if args.qc_out
            else root / "生产数据" / "qa_previews" / f"{args.chapter}_lettering_slots.jpg"
        )
        stage_qc = staging / "qc" / qc_target.name
        manifest["lettering_slot_qc"] = save_lettering_qc_sheet(manifest, root, layout, lettering, stage_qc)
        print(f"[ok] lettering slot QC staged {stage_qc}")

    promoted = False
    preserve_previous = False
    if args.render and staging is not None:
        render_ready = (
            not manifest.get("render_error")
            and not manifest.get("missing_panels")
            and manifest["format_fulfillment"]["verdict"] == "pass"
            and manifest["render_bundle_validation"]["verdict"] == "pass"
            and manifest["text_layout_qc"]["verdict"] == "pass"
        )
        previous_healthy = bool(previous_manifest.get("rendered") or previous_manifest.get("documents")) and not previous_manifest.get("missing_panels") and not previous_manifest.get("render_error") and (previous_manifest.get("format_fulfillment") or {}).get("verdict", "pass") == "pass"
        mappings = [
            (staging / "pages", page_dir),
            (staging / "longstrip", out_dir),
            (staging / "print" / pdf_path.name, pdf_path),
        ]
        if qc_target is not None:
            mappings.append((staging / "qc" / qc_target.name, qc_target))
        staged_attempt_manifest = json.loads(json.dumps(manifest, ensure_ascii=False))
        staged_attempt_manifest["render_transaction"] = {
            "kind": "comic_render_attempt",
            "render_digest": render_digest,
            "attempt_staging": str(staging.relative_to(root)),
            "activated": False,
        }
        manifest = remap_staged_manifest(manifest, root, mappings)
        manifest["render_transaction"] = {
            "kind": "comic_render_transaction",
            "render_digest": render_digest,
            "bundle": str((chapter_dir / ".render_bundles" / render_digest).relative_to(root)),
            "active_pointer": str((chapter_dir / "active_render_bundle.json").relative_to(root)),
            "promotion_policy": "validated_bundle_then_atomic_pointer",
        }
        if render_ready:
            try:
                bundle = finalize_render_bundle(
                    root,
                    chapter_dir,
                    staging,
                    render_digest,
                    manifest,
                    page_dir=page_dir,
                    out_dir=out_dir,
                    pdf_path=pdf_path,
                    manifest_path=manifest_path,
                    qc_target=qc_target,
                    activate=True,
                )
                promoted = True
                print(f"[ok] active render bundle {bundle}")
            except (OSError, RuntimeError, ValueError) as exc:
                print(f"[err] render bundle promotion failed and was rolled back: {exc}")
                return 2
        elif previous_healthy:
            preserve_previous = True
            staged_attempt_manifest["preserved_active_bundle"] = True
            (staging / "export_manifest.json").write_text(json.dumps(staged_attempt_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"[warn] render attempt blocked; preserved previous canonical outputs: {staging}")
        else:
            # First incomplete attempt remains an explicit staging receipt.  It
            # does not create an active pointer or pretend to be an immutable
            # accepted bundle, but the canonical manifest remains discoverable.
            (staging / "export_manifest.json").write_text(json.dumps(staged_attempt_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            _atomic_write_json(manifest_path, staged_attempt_manifest)
            print(f"[warn] incomplete render attempt recorded without activation: {staging}")
    else:
        _atomic_write_json(manifest_path, manifest)
        promoted = True
    if promoted:
        print(f"[ok] {manifest_path}")
    if manifest["missing_panels"]:
        print("[warn] 缺少面板图：" + ", ".join(manifest["missing_panels"]))
    if manifest["rendered"] or manifest.get("documents"):
        print(f"[ok] rendered {len(manifest['rendered'])} image(s), {len(manifest.get('documents') or [])} document(s)")
    if args.write_progress and promoted:
        deliverables_ready = bool(manifest["rendered"] or manifest.get("documents")) and manifest["format_fulfillment"]["verdict"] == "pass"
        if not manifest["missing_panels"] and deliverables_ready and manifest.get("lettering"):
            value = "✅"
        elif not manifest["missing_panels"]:
            value = "⏳manifest"
        else:
            value = ""
        if value and update_stage(root, args.chapter, "嵌字合成", value, evidence=str(manifest_path.relative_to(root)), actor="comic-compose/export_longstrip.py"):
            print(f"[ok] progress 嵌字合成={value}")
        if update_checklist(root, {
            f"{args.chapter} 页面图": bool(manifest.get("pages")),
            f"{args.chapter} 长图": bool(manifest.get("rendered")),
            f"{args.chapter} export_manifest.json": manifest_path.is_file(),
        }):
            print("[ok] progress export checklist updated")
    return 2 if preserve_previous else 0


if __name__ == "__main__":
    raise SystemExit(main())
