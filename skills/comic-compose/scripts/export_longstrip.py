#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成漫画导出 manifest，并可选用 Pillow 渲染长图分段。"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
FONT_CANDIDATES = (
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ordered_panel_ids(layout: dict) -> list[str]:
    ids: list[str] = []
    for seg in layout.get("segments", []):
        panels = sorted(seg.get("panels", []), key=lambda p: (p.get("y", 0), p.get("x", 0)))
        for panel in panels:
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


def wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    text = str(text).strip()
    if not text:
        return []
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


def fit_lines(draw, text: str, font_path: str, target_size: int, max_width: int, max_height: int) -> tuple[object, list[str], int]:
    size = max(16, int(target_size))
    while size >= 18:
        font = load_font(size, font_path)
        lines = wrap_text(draw, text, font, max_width)
        _, line_h = text_size(draw, "国", font)
        line_h = max(line_h, size)
        total_h = len(lines) * line_h + max(0, len(lines) - 1) * 6
        if lines and total_h <= max_height and all(text_size(draw, line, font)[0] <= max_width for line in lines):
            return font, lines, line_h
        size -= 2
    font = load_font(18, font_path)
    return font, wrap_text(draw, text, font, max_width), 20


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


def draw_text_block(image, draw, rect: tuple[int, int, int, int], text: str, item_type: str, style: dict, font_path: str) -> None:
    x, y, w, h = rect
    pad = max(14, int(min(w, h) * 0.12))
    size = int(style.get("size") or (72 if item_type == "sfx" else 44))
    if item_type == "sfx":
        font, lines, line_h = fit_lines(draw, text, font_path, size, max(40, w), max(30, h))
        total_h = len(lines) * line_h + max(0, len(lines) - 1) * 4
        yy = y + max(0, (h - total_h) // 2)
        for line in lines:
            tw, _ = text_size(draw, line, font)
            draw.text((x + max(0, (w - tw) // 2), yy), line, font=font, fill=(245, 239, 220), stroke_width=4, stroke_fill=(25, 20, 18))
            yy += line_h + 4
        return

    radius = 18 if item_type == "dialogue" else 8
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=(252, 248, 238), outline=(22, 22, 22), width=3)
    font, lines, line_h = fit_lines(draw, text, font_path, size, max(40, w - pad * 2), max(30, h - pad * 2))
    total_h = len(lines) * line_h + max(0, len(lines) - 1) * 5
    yy = y + max(pad // 2, (h - total_h) // 2)
    for line in lines:
        tw, _ = text_size(draw, line, font)
        draw.text((x + max(pad, (w - tw) // 2), yy), line, font=font, fill=(20, 20, 20))
        yy += line_h + 5


def apply_lettering(image, panel_id: str, slot_info: dict[str, Any], items: list[dict], font_path: str):
    if not items:
        return image
    from PIL import ImageDraw

    panel = slot_info.get("panel") or {"w": image.width, "h": image.height}
    slots = slot_info.get("slots") or {}
    draw = ImageDraw.Draw(image)
    groups: dict[str, list[dict]] = {}
    for item in items:
        sid = item.get("slot_id") or item.get("item_id")
        groups.setdefault(str(sid), []).append(item)
    fallback_y = 32
    for sid, group in groups.items():
        first = group[0]
        item_type = first.get("type", "dialogue")
        style = first.get("style") or {}
        if item_type == "sfx":
            text = "  ".join(str(item.get("text", "")).strip() for item in group if str(item.get("text", "")).strip())
        else:
            text = "\n".join(str(item.get("text", "")).strip() for item in group if str(item.get("text", "")).strip())
        if not text:
            continue
        slot = slots.get(sid)
        if slot:
            rect = slot_rect(panel, slot, image)
        else:
            rect = (32, fallback_y, min(560, image.width - 64), 140)
            fallback_y += 160
        draw_text_block(image, draw, rect, text, item_type, style, font_path)
    return image


def build_manifest(root: Path, chapter: str, layout_path: Path, panel_dir: Path, out_dir: Path, max_height: int, lettering_path: Path | None, font_path: str) -> dict:
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
        "lettering": str(lettering_path.relative_to(root)) if lettering_path and lettering_path.is_file() else "",
        "font": font_path,
        "font_status": "system_font_draft" if font_path else "pillow_default_fallback",
        "max_segment_height": max_height,
        "panels": panels,
        "missing_panels": missing,
        "rendered": [],
    }


def render_longstrip(manifest: dict, root: Path, out_dir: Path, max_height: int, gap: int, background: str, layout: dict, lettering: dict | None) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow 未安装；已可生成 manifest，如需渲染长图请先安装 Pillow。") from exc

    slots = panel_slot_map(layout)
    lettering_items = lettering_by_panel(lettering or {})
    font_path = manifest.get("font", "")
    images = []
    for item in manifest["panels"]:
        path = root / item["path"]
        image = Image.open(path).convert("RGB")
        image = apply_lettering(image, item["panel_id"], slots.get(item["panel_id"], {}), lettering_items.get(item["panel_id"], []), font_path)
        images.append((item["panel_id"], image))
        item["size"] = {"width": image.width, "height": image.height}

    if not images:
        return

    width = max(image.width for _, image in images)
    parts: list[list[tuple[str, Image.Image]]] = []
    current: list[tuple[str, Image.Image]] = []
    current_h = 0
    for pid, image in images:
        add_h = image.height + (gap if current else 0)
        if current and current_h + add_h > max_height:
            parts.append(current)
            current = []
            current_h = 0
            add_h = image.height
        current.append((pid, image))
        current_h += add_h
    if current:
        parts.append(current)

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for idx, part in enumerate(parts, 1):
        height = sum(img.height for _, img in part) + gap * max(0, len(part) - 1)
        canvas = Image.new("RGB", (width, height), background)
        y = 0
        panel_ids = []
        for pid, image in part:
            x = math.floor((width - image.width) / 2)
            canvas.paste(image, (x, y))
            y += image.height + gap
            panel_ids.append(pid)
        out_path = out_dir / f"part_{idx:03d}.webp"
        canvas.save(out_path, quality=92)
        rendered.append({"path": str(out_path.relative_to(root)), "panel_ids": panel_ids, "size": {"width": width, "height": height}})
    manifest["rendered"] = rendered
    manifest["lettering_rendered"] = bool(lettering_items)


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画长图导出 manifest/渲染")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--layout", default=None)
    parser.add_argument("--panel-dir", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--lettering", default=None)
    parser.add_argument("--no-lettering", action="store_true")
    parser.add_argument("--font", default=None)
    parser.add_argument("--max-height", type=int, default=12000)
    parser.add_argument("--gap", type=int, default=24)
    parser.add_argument("--background", default="#ffffff")
    parser.add_argument("--render", action="store_true", help="用 Pillow 实际渲染长图分段")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    layout_path = Path(args.layout).expanduser().resolve() if args.layout else root / "排版" / args.chapter / "layout.json"
    panel_dir = Path(args.panel_dir).expanduser().resolve() if args.panel_dir else root / "出图" / args.chapter / "panels"
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else root / "排版" / args.chapter / "长图"
    lettering_path = None if args.no_lettering else (Path(args.lettering).expanduser().resolve() if args.lettering else root / "排版" / args.chapter / "lettering.json")
    font_path = resolve_font_path(args.font)
    manifest_path = root / "排版" / args.chapter / "export_manifest.json"

    if not layout_path.is_file():
        print(f"[err] layout 不存在：{layout_path}")
        return 2
    panel_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    layout = load_json(layout_path)
    lettering = load_json(lettering_path) if lettering_path and lettering_path.is_file() else None
    manifest = build_manifest(root, args.chapter, layout_path, panel_dir, out_dir, args.max_height, lettering_path, font_path)

    if args.render:
        try:
            render_longstrip(manifest, root, out_dir, args.max_height, args.gap, args.background, layout, lettering)
        except RuntimeError as err:
            manifest["render_error"] = str(err)
            print(f"[warn] {err}")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {manifest_path}")
    if manifest["missing_panels"]:
        print("[warn] 缺少面板图：" + ", ".join(manifest["missing_panels"]))
    if manifest["rendered"]:
        print(f"[ok] rendered {len(manifest['rendered'])} part(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
