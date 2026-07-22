#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成漫画导出 manifest，并可选用 Pillow 渲染条漫长图。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from platform_profiles import profile_for_platform, validate_manifest
from text_metadata import normalize_text_language, unsupported_lettering_items


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
    return formats or ["webp"]


def choose_output_format(formats: list[str], width: int, height: int) -> str:
    for fmt in formats:
        if fmt == "webp" and max(width, height) <= WEBP_MAX_DIMENSION:
            return fmt
        if fmt in {"png", "jpg"}:
            return fmt
    return "png"


def save_canvas(image: Any, path: Path, fmt: str) -> None:
    if fmt == "webp":
        image.save(path, quality=92)
    elif fmt == "jpg":
        image.save(path, quality=92)
    else:
        image.save(path)


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


def draw_irregular_bubble(draw, rect: tuple[int, int, int, int], item_type: str, seed: str) -> tuple[int, int, int, int]:
    x, y, w, h = rect
    fill = (252, 248, 238) if item_type == "dialogue" else (244, 238, 220)
    tail = item_type == "dialogue"
    points, tail_h = irregular_points(x, y, w, h, seed, tail)
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=(20, 20, 20), width=3, joint="curve")
    return x, y, w, max(24, h - tail_h)


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
) -> None:
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
        return

    body_x, body_y, body_w, body_h = draw_irregular_bubble(draw, rect, item_type, seed)
    text_x = body_x + pad
    text_y = body_y + pad
    text_w = max(40, body_w - pad * 2)
    text_h = max(30, body_h - pad * 2)
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


def apply_lettering(image, panel_id: str, slot_info: dict[str, Any], items: list[dict], font_path: str, text_language: str):
    from PIL import ImageDraw

    panel = slot_info.get("panel") or {"w": image.width, "h": image.height}
    slots = slot_info.get("slots") or {}
    draw = ImageDraw.Draw(image)
    groups: dict[str, list[dict]] = {}
    for item in items:
        sid = item.get("slot_id") or item.get("item_id")
        groups.setdefault(str(sid), []).append(item)
    fallback_y = 32
    stats = {"drawn_items": 0, "skipped_empty_items": [], "empty_slots_removed": []}
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
        draw_text_block(image, draw, rect, primary_text, secondary_text, item_type, style, font_path, f"{panel_id}:{sid}")
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
            panels.append({"panel_id": pid, "path": str(img.relative_to(root))})
        else:
            missing.append(pid)
    return {
        "schema_version": 1,
        "kind": "comic_export_manifest",
        "chapter": chapter,
        "layout": str(layout_path.relative_to(root)),
        "panel_dir": str(panel_dir.relative_to(root)),
        "out_dir": str(out_dir.relative_to(root)),
        "page_dir": str(page_dir.relative_to(root)),
        "lettering": str(lettering_path.relative_to(root)) if lettering_path and lettering_path.is_file() else "",
        "font": font_path,
        "font_status": "system_font_draft" if font_path else "pillow_default_fallback",
        "export_formats": export_formats,
        "max_segment_height": max_height,
        "split_mode": "height" if max_height > 0 else "single",
        "panels": panels,
        "missing_panels": missing,
        "pages": [],
        "rendered": [],
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


def merge_lettering_stats(total: dict[str, Any], stats: dict[str, Any]) -> None:
    total["drawn_items"] += stats["drawn_items"]
    total["skipped_empty_items"].extend(stats["skipped_empty_items"])
    total["empty_slots_removed"].extend(stats["empty_slots_removed"])


def render_layout_pages(
    manifest: dict,
    root: Path,
    page_dir: Path,
    background: str,
    layout: dict,
    lettering: dict | None,
    text_language: str,
    export_formats: list[str],
) -> tuple[list[tuple[dict[str, Any], Any]], dict[str, Any]]:
    from PIL import Image

    panel_items = {item["panel_id"]: item for item in manifest["panels"]}
    lettering_items = lettering_by_panel(lettering or {})
    font_path = manifest.get("font", "")
    language_mode = normalize_text_language(text_language)
    rendered_pages: list[tuple[dict[str, Any], Any]] = []
    lettering_stats = {"drawn_items": 0, "skipped_empty_items": [], "empty_slots_removed": []}

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
            )
            merge_lettering_stats(lettering_stats, stats)
            item["size"] = {"width": image.width, "height": image.height}
            canvas.paste(image, (int(panel.get("x") or 0), int(panel.get("y") or 0)))
            page_panel_ids.append(pid)

        fmt = choose_output_format(export_formats, canvas.width, canvas.height)
        page_path = page_dir / f"page_{idx:03d}.{fmt}"
        save_canvas(canvas, page_path, fmt)
        meta = {
            "path": str(page_path.relative_to(root)),
            "segment_id": segment.get("segment_id", f"S{idx:03d}"),
            "panel_ids": page_panel_ids,
            "size": {"width": canvas.width, "height": canvas.height},
            "format": fmt,
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
) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow 未安装；已可生成 manifest，如需渲染长图请先安装 Pillow。") from exc

    language_mode = normalize_text_language(text_language)
    cleanup_outputs(out_dir, page_dir)
    page_canvases, lettering_stats = render_layout_pages(
        manifest, root, page_dir, background, layout, lettering, language_mode, export_formats
    )
    manifest["pages"] = [meta for meta, _canvas in page_canvases]
    if not page_canvases:
        return

    combined, panel_ids = combine_pages(page_canvases, gap, background)
    rendered = []
    if max_height <= 0:
        fmt = choose_output_format(export_formats, combined.width, combined.height)
        out_name = f"longstrip.{fmt}"
        out_path = out_dir / out_name
        save_canvas(combined, out_path, fmt)
        rendered.append(
            {
                "path": str(out_path.relative_to(root)),
                "panel_ids": panel_ids,
                "size": {"width": combined.width, "height": combined.height},
                "format": fmt,
            }
        )
    else:
        y = 0
        idx = 1
        while y < combined.height:
            bottom = min(combined.height, y + max_height)
            crop = combined.crop((0, y, combined.width, bottom))
            fmt = choose_output_format(export_formats, crop.width, crop.height)
            out_path = out_dir / f"part_{idx:03d}.{fmt}"
            save_canvas(crop, out_path, fmt)
            rendered.append(
                {
                    "path": str(out_path.relative_to(root)),
                    "panel_ids": panel_ids,
                    "size": {"width": crop.width, "height": crop.height},
                    "y_range": [y, bottom],
                    "format": fmt,
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


def update_progress(root: Path, chapter: str, stage: str, value: str) -> bool:
    path = root / "_进度.md"
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    headers: list[str] = []
    updated = False
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
                updated = True
        out.append(line)
    if updated:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return updated


def update_export_checklist(root: Path, chapter: str, *, pages_ready: bool, longstrip_ready: bool, manifest_ready: bool) -> bool:
    path = root / "_进度.md"
    if not path.is_file():
        return False
    targets = {
        f"{chapter} 页面图": pages_ready,
        f"{chapter} 长图": longstrip_ready,
        f"{chapter} export_manifest.json": manifest_ready,
    }
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = False
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        match = re.match(r"^-\s+\[[ xX]\]\s+(.+?)\s*$", stripped)
        if match and match.group(1) in targets:
            label = match.group(1)
            seen.add(label)
            desired = f"- [{'x' if targets[label] else ' '}] {label}"
            indent = line[: len(line) - len(line.lstrip())]
            new_line = indent + desired
            if new_line != line:
                line = new_line
                changed = True
        out.append(line)
    missing = [label for label in targets if label not in seen]
    if missing:
        insert_at = None
        in_export_section = False
        last_export_item = None
        for idx, line in enumerate(out):
            stripped = line.strip()
            if stripped == "## 导出":
                in_export_section = True
                insert_at = idx + 1
                continue
            if in_export_section and stripped.startswith("## "):
                break
            if in_export_section and stripped.startswith("- ["):
                last_export_item = idx
        if last_export_item is not None:
            insert_at = last_export_item + 1
        if insert_at is None:
            out.extend(["", "## 导出"])
            insert_at = len(out)
        additions = [f"- [{'x' if targets[label] else ' '}] {label}" for label in missing]
        out[insert_at:insert_at] = additions
        changed = True
    if changed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


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
    parser.add_argument("--formats", default=None, help="导出格式，如 webp、png 或 webp+png；默认读 _设置.md 的 导出格式")
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
    lettering_path = None if args.no_lettering else (Path(args.lettering).expanduser().resolve() if args.lettering else root / "排版" / args.chapter / "lettering.json")
    font_path = resolve_font_path(args.font)
    manifest_path = root / "排版" / args.chapter / "export_manifest.json"

    if not layout_path.is_file():
        print(f"[err] layout 不存在：{layout_path}")
        return 2
    panel_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    page_dir.mkdir(parents=True, exist_ok=True)
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
    text_language = normalize_text_language(read_setting(root, "文字语言", (lettering or {}).get("language_mode", "中文") if lettering else "中文"))
    target_platform = read_setting(root, "目标平台", "通用")
    usage = read_setting(root, "合规用途", "自用草稿")
    platform_profile = profile_for_platform(target_platform)
    manifest["text_language"] = text_language
    manifest["target_platform"] = target_platform
    manifest["platform_profile"] = platform_profile.to_manifest()
    unsupported_text = unsupported_lettering_items(lettering, text_language)
    manifest["text_layout_qc"] = {
        "renderer": "pillow_draft",
        "unsupported_items": unsupported_text,
        "verdict": "block" if unsupported_text else "pass",
    }

    if args.render and unsupported_text:
        manifest["render_error"] = "当前 Pillow 草稿嵌字不支持 RTL 或需词典分词的目标文字；请改用人工/专业排版 renderer。"
        print(f"[warn] {manifest['render_error']}")
    elif args.render:
        try:
            render_longstrip(
                manifest,
                root,
                out_dir,
                page_dir,
                max_height,
                args.gap,
                args.background,
                layout,
                lettering,
                text_language,
                export_formats,
            )
        except RuntimeError as err:
            manifest["render_error"] = str(err)
            print(f"[warn] {err}")

    manifest["platform_findings"] = validate_manifest(root, manifest, platform_profile, usage)

    if args.qc_slots and args.render and manifest.get("pages"):
        qc_path = (
            Path(args.qc_out).expanduser().resolve()
            if args.qc_out
            else root / "生产数据" / "qa_previews" / f"{args.chapter}_lettering_slots.jpg"
        )
        manifest["lettering_slot_qc"] = save_lettering_qc_sheet(manifest, root, layout, lettering, qc_path)
        print(f"[ok] lettering slot QC {qc_path}")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {manifest_path}")
    if manifest["missing_panels"]:
        print("[warn] 缺少面板图：" + ", ".join(manifest["missing_panels"]))
    if manifest["rendered"]:
        print(f"[ok] rendered {len(manifest['rendered'])} file(s)")
    if args.write_progress:
        if not manifest["missing_panels"] and manifest["rendered"] and manifest.get("lettering"):
            value = "✅"
        elif not manifest["missing_panels"]:
            value = "⏳manifest"
        else:
            value = ""
        if value and update_progress(root, args.chapter, "嵌字合成", value):
            print(f"[ok] progress 嵌字合成={value}")
        if update_export_checklist(
            root,
            args.chapter,
            pages_ready=bool(manifest.get("pages")),
            longstrip_ready=bool(manifest.get("rendered")),
            manifest_ready=manifest_path.is_file(),
        ):
            print("[ok] progress export checklist updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
