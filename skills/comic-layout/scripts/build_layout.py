#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 生成条漫/页漫 MVP layout.json。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEAVY_FUNCTIONS = {
    "opening_hook",
    "opening_pressure",
    "action_peak",
    "turning_point",
    "cliffhanger",
    "chapter_hook",
    "reveal",
    "public_humiliation",
    "physical_burden",
    "mystery_glint",
    "water_source_reveal",
}
MEDIUM_FUNCTIONS = {
    "compressed_backstory",
    "labor_montage",
    "task_assignment",
    "rules_and_threat",
}
COMPACT_FUNCTIONS = {
    "reaction",
    "transition",
    "setup",
    "identity_question",
    "mockery_setup",
    "leave_hall",
    "empty_room",
    "water_task_scale",
    "proactive_choice",
    "night_fifth_trip",
    "approach_basin",
}

HEAVY_TOKENS = ("opening", "hook", "cliffhanger", "reveal", "peak", "turning", "humiliation", "burden", "glint", "source")
MEDIUM_TOKENS = ("montage", "assignment", "threat", "scale", "backstory")
COMPACT_TOKENS = ("reaction", "transition", "setup", "question", "leave", "empty", "approach")


def load_json(path: Path) -> dict:
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
    return int(match.group(1)) if match else default


def parse_max_segment_height(value: str, default: int = 0) -> int:
    raw = str(value or "").strip()
    if not raw:
        return default
    lowered = raw.lower()
    if raw == "0" or any(token in lowered for token in ("不分段", "不限", "单张", "single", "none", "no-split", "unlimited")):
        return 0
    match = re.search(r"\d+", raw)
    return int(match.group(0)) if match else default


def panel_height(panel: dict) -> int:
    fn = str(panel.get("story_function", "")).strip()
    dialogue_count = len(panel.get("dialogue") or [])
    has_narration = bool(str(panel.get("narration", "")).strip())
    has_sfx = bool(panel.get("sfx") or [])
    lowered = fn.lower()
    notes = str(panel.get("art_notes") or "")
    description = str(panel.get("description") or "")
    wants_big = any(token in notes or token in description for token in ("大格", "重点", "钩子", "压迫", "奇观"))
    if fn in HEAVY_FUNCTIONS or any(token in lowered for token in HEAVY_TOKENS) or wants_big:
        base = 960
    elif fn in MEDIUM_FUNCTIONS or any(token in lowered for token in MEDIUM_TOKENS):
        base = 840
    elif fn in COMPACT_FUNCTIONS:
        base = 620
    elif any(token in lowered for token in COMPACT_TOKENS):
        base = 680
    else:
        base = 760
    if dialogue_count >= 2:
        base += 120
    if has_narration:
        base += 80
    if has_sfx:
        base += 80
    return min(max(base, 560), 1240)


def bubble_slots(panel: dict, rect: dict, index: int) -> list[dict]:
    slots = []
    x = rect["x"]
    y = rect["y"]
    w = rect["w"]
    h = rect["h"]
    cursor_y = y + 44
    if str(panel.get("narration", "")).strip():
        slots.append(
            {
                "slot_id": f"B{index:03d}N",
                "type": "narration",
                "x": x + 48,
                "y": cursor_y,
                "w": min(560, w - 96),
                "h": 118,
            }
        )
        cursor_y += 138
    for dialogue_index, _dialogue in enumerate(panel.get("dialogue") or [], 1):
        slot_w = 430
        slot_h = 136
        side_right = dialogue_index % 2 == 1
        slot_x = x + w - slot_w - 56 if side_right else x + 56
        slots.append(
            {
                "slot_id": f"B{index:03d}D{dialogue_index}",
                "type": "dialogue",
                "x": slot_x,
                "y": cursor_y,
                "w": slot_w,
                "h": slot_h,
            }
        )
        cursor_y += slot_h + 18
    if panel.get("sfx"):
        slots.append(
            {
                "slot_id": f"B{index:03d}S",
                "type": "sfx",
                "x": x + max(80, w // 2 - 180),
                "y": y + max(120, h // 2 - 80),
                "w": 360,
                "h": 150,
            }
        )
    return slots


def build_layout(root: Path, chapter: str, max_segment_height: int, gutter: int) -> dict:
    panel_path = root / "脚本" / chapter / "panel_script.json"
    panel_script = load_json(panel_path)
    width = parse_width(read_setting(root, "页面尺寸", "1440xauto"))
    comic_format = read_setting(root, "漫画形态", "条漫")
    reading_direction = read_setting(root, "阅读方向", "从上到下")
    margin = 72
    panel_w = width - margin * 2

    segments = []
    current = {"segment_id": "S001", "width": width, "height": 0, "panels": []}
    y = gutter
    segment_index = 1

    for index, panel in enumerate(panel_script.get("panels", []), 1):
        h = panel_height(panel)
        if max_segment_height > 0 and current["panels"] and y + h + gutter > max_segment_height:
            current["height"] = y
            segments.append(current)
            segment_index += 1
            current = {"segment_id": f"S{segment_index:03d}", "width": width, "height": 0, "panels": []}
            y = gutter
        rect = {
            "panel_id": panel["panel_id"],
            "x": margin,
            "y": y,
            "w": panel_w,
            "h": h,
        }
        rect["bubble_slots"] = bubble_slots(panel, rect, index)
        current["panels"].append(rect)
        y += h + gutter

    current["height"] = y if current["panels"] else 0
    if current["panels"]:
        segments.append(current)

    return {
        "schema_version": 1,
        "kind": "comic_layout",
        "chapter": chapter,
        "format": comic_format,
        "reading_direction": reading_direction,
        "canvas": {"width": width, "height": "auto"},
        "segments": segments,
    }


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


def write_notes(root: Path, chapter: str, layout: dict) -> None:
    total_panels = sum(len(seg.get("panels", [])) for seg in layout.get("segments", []))
    lines = [
        f"# 排版说明 — {chapter}",
        "",
        f"- 形态：{layout.get('format')}",
        f"- 阅读方向：{layout.get('reading_direction')}",
        f"- 分段数：{len(layout.get('segments', []))}",
        f"- 面板数：{total_panels}",
        "- 气泡坐标为 MVP 占位，正式嵌字前需人工检查是否挡脸、手、刀、妖物关键动作。",
        "- 出图阶段应生成无字画面，只预留低细节留白；不要把正文台词、文字框或空白气泡烘焙进图片。",
    ]
    path = root / "排版" / chapter / "layout_notes.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="从 panel_script.json 生成 comic layout.json")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--max-segment-height", type=int, default=None)
    parser.add_argument("--gutter", type=int, default=28)
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    max_height = args.max_segment_height if args.max_segment_height is not None else parse_max_segment_height(read_setting(root, "单话分段高度", "0"))
    layout = build_layout(root, args.chapter, max_height, args.gutter)
    out_path = root / "排版" / args.chapter / "layout.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_notes(root, args.chapter, layout)
    if not args.no_progress:
        update_progress(root, args.chapter, "页面排版", "✅")
    print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
