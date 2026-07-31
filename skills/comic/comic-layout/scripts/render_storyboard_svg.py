#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 layout.json + panel_script.json 渲成可审查的 SVG 分格草图。"""
from __future__ import annotations

import argparse
import html
import json
import textwrap
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def panel_map(panel_script: dict) -> dict[str, dict]:
    return {panel.get("panel_id"): panel for panel in panel_script.get("panels", []) if panel.get("panel_id")}


def wrap(value: str, width: int = 28, max_lines: int = 4) -> list[str]:
    value = " ".join(str(value or "").split())
    if not value:
        return []
    lines = textwrap.wrap(value, width=width, break_long_words=False, replace_whitespace=False)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("，。；,. ") + "..."
    return lines


def text_block(x: int, y: int, lines: list[str], size: int = 26, color: str = "#202124") -> str:
    escaped = [html.escape(line) for line in lines if line]
    if not escaped:
        return ""
    tspans = []
    for idx, line in enumerate(escaped):
        dy = 0 if idx == 0 else int(size * 1.35)
        tspans.append(f'<tspan x="{x}" dy="{dy}">{line}</tspan>')
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-family="PingFang SC, Heiti SC, sans-serif">{"".join(tspans)}</text>'


def build_svg(layout: dict, panels: dict[str, dict]) -> str:
    width = int(layout.get("canvas", {}).get("width", 1440))
    segment_gap = 80
    y_offsets = []
    cursor = 0
    for segment in layout.get("segments", []):
        y_offsets.append(cursor)
        cursor += int(segment.get("height", 0)) + segment_gap
    height = max(cursor - segment_gap, 1000)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3f0e8"/>',
    ]
    for seg_index, segment in enumerate(layout.get("segments", [])):
        offset_y = y_offsets[seg_index]
        seg_height = int(segment.get("height", 0))
        parts.append(f'<rect x="0" y="{offset_y}" width="{width}" height="{seg_height}" fill="#fbfaf7" stroke="#d4c8b4" stroke-width="2"/>')
        parts.append(text_block(36, offset_y + 44, [segment.get("segment_id", f"S{seg_index + 1:03d}")], 28, "#7a5a20"))
        for panel_index, rect in enumerate(segment.get("panels", []), 1):
            pid = rect.get("panel_id", "")
            panel = panels.get(pid, {})
            x = int(rect.get("x", 0))
            y = int(rect.get("y", 0)) + offset_y
            w = int(rect.get("w", 0))
            h = int(rect.get("h", 0))
            fill = "#eee7dc" if panel_index % 2 else "#e5e0d8"
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="#1f1f1f" stroke-width="4"/>')
            title = f"{pid}  {panel.get('story_function', '')}"
            parts.append(text_block(x + 28, y + 48, [title], 30, "#111111"))
            desc = panel.get("description", "")
            parts.append(text_block(x + 28, y + 98, wrap(desc, 34, 4), 26, "#333333"))
            dialogue_lines = []
            if panel.get("narration"):
                dialogue_lines.append("旁白：" + str(panel.get("narration")))
            for dialogue in panel.get("dialogue") or []:
                dialogue_lines.append(f"{dialogue.get('speaker', '')}：{dialogue.get('text', '')}")
            if panel.get("sfx"):
                dialogue_lines.append("SFX：" + " / ".join(map(str, panel.get("sfx", []))))
            parts.append(text_block(x + 28, y + h - 160, wrap(" | ".join(dialogue_lines), 34, 4), 24, "#5b2b20"))
            for slot in rect.get("bubble_slots", []):
                sx = int(slot.get("x", 0))
                sy = int(slot.get("y", 0)) + offset_y
                sw = int(slot.get("w", 0))
                sh = int(slot.get("h", 0))
                color = "#3d72b4" if slot.get("type") != "sfx" else "#b4433d"
                parts.append(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="28" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="10 8"/>')
                parts.append(text_block(sx + 16, sy + 34, [slot.get("slot_id", ""), slot.get("type", "")], 20, color))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染漫画 SVG 分格草图")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    layout = load_json(root / "排版" / args.chapter / "layout.json")
    panel_script = load_json(root / "脚本" / args.chapter / "panel_script.json")
    out_path = Path(args.out).expanduser().resolve() if args.out else root / "排版" / args.chapter / "pages" / "storyboard.svg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_svg(layout, panel_map(panel_script)), encoding="utf-8")
    print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
