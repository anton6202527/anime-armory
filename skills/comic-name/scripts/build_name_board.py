#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a traditional manga name-board from panel_script.json."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


HEAVY_TOKENS = ("hook", "cliff", "reveal", "peak", "turn", "breakthrough", "冲击", "揭示", "钩子", "高潮", "动作")
COMPACT_TOKENS = ("reaction", "transition", "setup", "反应", "过渡", "铺垫")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_setting(root: Path, key: str, default: str) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def parse_width(value: str, default: int = 1440) -> int:
    match = re.match(r"\s*(\d+)\s*x", value)
    if match:
        return int(match.group(1))
    if value.upper() == "A4":
        return 1440
    if value.upper() == "B5":
        return 1280
    return default


def compact_text(value: Any, *, max_len: int = 90) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    elif isinstance(value, list):
        text = "；".join(compact_text(item, max_len=max_len) for item in value)
    elif isinstance(value, dict):
        text = "；".join(f"{key}:{compact_text(item, max_len=max_len)}" for key, item in value.items())
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip("； ")
    return text[: max_len - 1].rstrip() + "…" if len(text) > max_len else text


def explicit_weight(panel: dict[str, Any]) -> str:
    for key in ("layout_weight", "visual_weight", "importance"):
        raw = str(panel.get(key) or "").strip().lower()
        if raw in {"heavy", "large", "big", "重点", "大格", "强", "高", "3"}:
            return "heavy"
        if raw in {"compact", "small", "小格", "轻", "低", "1"}:
            return "compact"
        if raw in {"medium", "normal", "标准", "中", "2"}:
            return "medium"
    fn = str(panel.get("story_function") or "").lower()
    if any(token in fn for token in HEAVY_TOKENS):
        return "heavy"
    if any(token in fn for token in COMPACT_TOKENS):
        return "compact"
    if panel.get("sfx"):
        return "heavy"
    return "medium"


def text_load(panel: dict[str, Any]) -> int:
    load = 0
    if compact_text(panel.get("narration")) or compact_text(panel.get("narration_target")):
        load += 1
    for dialogue in panel.get("dialogue") or []:
        if isinstance(dialogue, dict) and compact_text(dialogue.get("text_target") or dialogue.get("text")):
            load += 1
    return load


def manuscript_boxes(width: int, comic_format: str, spec: str) -> dict[str, Any]:
    if "页漫" in comic_format or "B5" in spec or "A4" in spec:
        height = int(width * 1.42)
        bleed = max(24, width // 32)
        safe = max(72, width // 15)
        inner = max(104, width // 11)
    else:
        height = 1800
        bleed = 0
        safe = max(72, width // 20)
        inner = safe
    return {
        "spec": spec,
        "trim_box": {"x": 0, "y": 0, "w": width, "h": height},
        "safe_area": {"x": safe, "y": safe, "w": width - safe * 2, "h": height - safe * 2},
        "bleed": bleed,
        "inner_frame": {"x": inner, "y": inner, "w": width - inner * 2, "h": height - inner * 2},
    }


def panels_per_page(comic_format: str) -> int:
    if "四格" in comic_format:
        return 4
    if "页漫" in comic_format:
        return 5
    return 6


def page_side(index: int, comic_format: str, reading_direction: str) -> str:
    if "条漫" in comic_format:
        return "scroll"
    if reading_direction == "从右到左":
        return "right" if index % 2 == 1 else "left"
    return "left" if index % 2 == 1 else "right"


def bubble_first(panel: dict[str, Any], reading_direction: str) -> str:
    if text_load(panel) == 0:
        return "none"
    if reading_direction == "从右到左":
        return "right_top"
    return "left_top" if reading_direction == "从左到右" else "top"


def panel_shape_for(weight: str, panel: dict[str, Any]) -> str:
    explicit = str(panel.get("panel_shape") or "").strip()
    if explicit:
        return explicit
    if weight == "heavy":
        return "wide"
    if weight == "compact":
        return "small"
    return "standard"


def effect_hint(panel: dict[str, Any], weight: str) -> str:
    explicit = compact_text(panel.get("effects_plan") or panel.get("effects_hint") or panel.get("sfx"))
    if explicit:
        return explicit
    fn = str(panel.get("story_function") or "").lower()
    if panel.get("sfx") or weight == "heavy" and any(token in fn for token in ("action", "peak", "动作")):
        return "speed/action lines around motion path; keep face and hands readable"
    if "reveal" in fn or "揭示" in fn:
        return "focus lines or black-field contrast toward reveal object"
    return "none"


def page_turn_hook(page_panels: list[dict[str, Any]]) -> str:
    if not page_panels:
        return ""
    candidates = []
    for panel in page_panels:
        fn = str(panel.get("story_function") or "").lower()
        if any(token in fn for token in HEAVY_TOKENS):
            candidates.append(panel)
    chosen = candidates[-1] if candidates else page_panels[-1]
    return f"{chosen.get('panel_id', '')} {compact_text(chosen.get('story_function'), max_len=36)}".strip()


def rough_rects(count: int, page: dict[str, Any], weights: list[str]) -> list[dict[str, int]]:
    safe = page["safe_area"]
    x = int(safe["x"])
    y = int(safe["y"])
    w = int(safe["w"])
    available_h = int(safe["h"])
    gap = max(18, w // 48)
    units = sum(3 if weight == "heavy" else 1 if weight == "compact" else 2 for weight in weights) or 1
    rects: list[dict[str, int]] = []
    cursor = y
    for idx, weight in enumerate(weights):
        unit = 3 if weight == "heavy" else 1 if weight == "compact" else 2
        remaining_gap = gap * max(0, count - 1)
        h = max(120, int((available_h - remaining_gap) * unit / units))
        if idx == count - 1:
            h = max(120, y + available_h - cursor)
        inset = 0 if weight == "heavy" else w // 12 if weight == "compact" else w // 24
        rects.append({"x": x + inset, "y": cursor, "w": w - inset * 2, "h": h})
        cursor += h + gap
    return rects


def finishing_preview(root: Path) -> dict[str, str]:
    style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    render_stage = read_setting(root, "出图稿层", "完成稿")
    tone_strategy = read_setting(root, "网点策略", "风格驱动")
    effects_strategy = read_setting(root, "效果线策略", "剧情驱动")
    if "黑白" in style or "网点" in style or "日漫" in style:
        tone_plan = f"{tone_strategy}: screentone hierarchy for skin, cloth, background depth, and mood blacks"
    else:
        tone_plan = f"{tone_strategy}: grayscale/value planning even when final art is color"
    return {
        "render_stage": render_stage,
        "ink_plan": "clear silhouettes, stable line weight, solid blacks assigned before tone/color",
        "tone_plan": tone_plan,
        "effects_plan": f"{effects_strategy}: action lines, focus lines, impact flashes, symbols, and omitted backgrounds only when they support reading",
    }


def build_name_board(root: Path, chapter: str) -> dict[str, Any]:
    panel_script = load_json(root / "脚本" / chapter / "panel_script.json")
    comic_format = read_setting(root, "漫画形态", str(panel_script.get("format") or "条漫"))
    reading_direction = read_setting(root, "阅读方向", "从上到下")
    width = parse_width(read_setting(root, "页面尺寸", "1440xauto"))
    spec = read_setting(root, "原稿规格", "数字条漫")
    manuscript = manuscript_boxes(width, comic_format, spec)
    page_capacity = panels_per_page(comic_format)
    panels = [panel for panel in panel_script.get("panels") or [] if isinstance(panel, dict) and panel.get("panel_id")]
    pages: list[dict[str, Any]] = []
    for page_index, start in enumerate(range(0, len(panels), page_capacity), 1):
        group = panels[start : start + page_capacity]
        page_id = f"SCROLL_{page_index:03d}" if "条漫" in comic_format else f"PAGE_{page_index:03d}"
        weights = [explicit_weight(panel) for panel in group]
        rects = rough_rects(len(group), manuscript, weights)
        page_panels = []
        gutter_notes = []
        for panel, weight, rect in zip(group, weights, rects):
            pid = str(panel.get("panel_id"))
            shape = panel_shape_for(weight, panel)
            gutter = compact_text(panel.get("gutter_intent") or ("long pause" if weight == "heavy" else "quick cut" if weight == "compact" else "standard beat"), max_len=48)
            gutter_notes.append(f"{pid}:{gutter}")
            page_panels.append(
                {
                    "panel_id": pid,
                    "thumbnail_rect": rect,
                    "layout_weight": weight,
                    "panel_shape": shape,
                    "border_style": str(panel.get("border_style") or "standard"),
                    "camera_hint": compact_text(panel.get("camera_role") or panel.get("art_notes") or panel.get("description")),
                    "text_load": text_load(panel),
                    "bubble_first": bubble_first(panel, reading_direction),
                    "effects_hint": effect_hint(panel, weight),
                }
            )
        pages.append(
            {
                "page_id": page_id,
                "page_side": page_side(page_index, comic_format, reading_direction),
                "spread_id": f"SPREAD_{(page_index + 1) // 2:03d}",
                "page_turn_hook": page_turn_hook(group),
                "eye_flow_path": [str(panel.get("panel_id")) for panel in group],
                "gutter_intent": "；".join(gutter_notes),
                "panels": page_panels,
            }
        )
    return {
        "schema_version": 1,
        "kind": "comic_name_board",
        "chapter": chapter,
        "format": comic_format,
        "reading_direction": reading_direction,
        "manuscript": manuscript,
        "pages": pages,
        "finishing_preview": finishing_preview(root),
    }


def write_svg(root: Path, chapter: str, board: dict[str, Any]) -> Path:
    page_w = 300
    page_h = 430
    gap = 28
    cols = 3
    pages = board.get("pages") or []
    rows = max(1, (len(pages) + cols - 1) // cols)
    width = cols * page_w + (cols + 1) * gap
    height = rows * page_h + (rows + 1) * gap
    src = board.get("manuscript") if isinstance(board.get("manuscript"), dict) else {}
    safe = src.get("safe_area") if isinstance(src.get("safe_area"), dict) else {"x": 0, "y": 0, "w": 1, "h": 1}
    safe_w = max(1, int(safe.get("w") or 1))
    safe_h = max(1, int(safe.get("h") or 1))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f2efe7"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif;font-size:11px;fill:#222}.pid{font-weight:700}.note{font-size:9px;fill:#555}</style>',
    ]
    for idx, page in enumerate(pages):
        row = idx // cols
        col = idx % cols
        ox = gap + col * (page_w + gap)
        oy = gap + row * (page_h + gap)
        parts.append(f'<rect x="{ox}" y="{oy}" width="{page_w}" height="{page_h}" fill="#fffdf7" stroke="#222" stroke-width="2"/>')
        parts.append(f'<text x="{ox + 10}" y="{oy + 18}">{html.escape(str(page.get("page_id") or ""))} {html.escape(str(page.get("page_side") or ""))}</text>')
        for panel in page.get("panels") or []:
            rect = panel.get("thumbnail_rect") if isinstance(panel.get("thumbnail_rect"), dict) else {}
            x = ox + 18 + int((int(rect.get("x") or 0) - int(safe.get("x") or 0)) / safe_w * (page_w - 36))
            y = oy + 34 + int((int(rect.get("y") or 0) - int(safe.get("y") or 0)) / safe_h * (page_h - 62))
            w = max(22, int(int(rect.get("w") or 1) / safe_w * (page_w - 36)))
            h = max(20, int(int(rect.get("h") or 1) / safe_h * (page_h - 62)))
            fill = "#f7f7f7" if panel.get("layout_weight") != "heavy" else "#ece8dc"
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#333" stroke-width="1.5"/>')
            parts.append(f'<text class="pid" x="{x + 5}" y="{y + 15}">{html.escape(str(panel.get("panel_id") or ""))}</text>')
            hint = html.escape(compact_text(panel.get("camera_hint"), max_len=32))
            if hint:
                parts.append(f'<text class="note" x="{x + 5}" y="{min(y + h - 7, y + 30)}">{hint}</text>')
        hook = html.escape(compact_text(page.get("page_turn_hook"), max_len=46))
        parts.append(f'<text class="note" x="{ox + 10}" y="{oy + page_h - 10}">hook: {hook}</text>')
    parts.append("</svg>")
    out = root / "排版" / chapter / "name" / "name_board.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out


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


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画缩略分镜/name_board.json")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    board = build_name_board(root, args.chapter)
    out_path = root / "排版" / args.chapter / "name_board.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    svg_path = write_svg(root, args.chapter, board)
    if not args.no_progress:
        update_progress(root, args.chapter, "缩略分镜", "✅")
    print(f"[ok] {out_path}")
    print(f"[ok] {svg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
