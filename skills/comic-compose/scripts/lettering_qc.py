#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""嵌字几何 QC（确定性）：气泡槽位坐标层面的可复算检查。

既有 QC 只覆盖「文字布局是否可渲染」（text_layout_qc）与「槽位是否缺失」
（lettering_slot_qc 预览图）；槽位越界、贴边、遮挡、密度、字号全靠人眼。
本脚本从 layout.json（槽位/格几何，layout 画布坐标系）+ lettering.json
（条目→槽位、字号）做纯几何检查，不做像素审美判断：

- lettering_out_of_canvas （block·确定性）：槽位 bbox 超出所属 segment 画布或坐标为负。
- lettering_outside_panel （warn）：槽位明显跑出所属格边界（允许 gutter 侵入容差）。
- lettering_safe_area     （warn）：槽位距画布左右边缘 < 安全边距（默认 40px@1440，按宽度等比）。
- lettering_overlap       （warn）：同格两个槽位 bbox 相交（对白互压/互遮）。
- lettering_bubble_density（warn）：单格对白+旁白槽位 > 3（条漫规范上限）。
- lettering_font_too_small（warn）：字号 < 最小可读字号（默认 28px@1440 宽，等比换算）。

lettering.json / layout.json 缺失时优雅返回空发现 + note，绝不假 block。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

KIND = "comic_lettering_qc"
SAFE_MARGIN_BASE = 40  # px @ 1440 宽
MIN_FONT_BASE = 28  # px @ 1440 宽
BASE_CANVAS_WIDTH = 1440
MAX_BUBBLES_PER_PANEL = 3
PANEL_OVERFLOW_TOLERANCE = 24  # 允许气泡略侵 gutter 的容差 px


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def finding(severity: str, code: str, panel_id: str, reason: str, suggested_fix: str) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "panel_id": panel_id,
        "artifact": "排版/<章>/lettering.json",
        "reason": reason,
        "suggested_fix": suggested_fix,
    }


def rect(slot: dict[str, Any]) -> tuple[float, float, float, float] | None:
    try:
        x = float(slot.get("x"))
        y = float(slot.get("y"))
        w = float(slot.get("w"))
        h = float(slot.get("h"))
    except (TypeError, ValueError):
        return None
    return x, y, w, h


def rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def analyze(root: Path, chapter: str) -> dict[str, Any]:
    layout = load_json(root / "排版" / chapter / "layout.json", {}) or {}
    lettering = load_json(root / "排版" / chapter / "lettering.json", {}) or {}
    notes: list[str] = []
    findings: list[dict[str, Any]] = []

    if not layout.get("segments"):
        notes.append("layout.json 缺失或无 segments；几何 QC 跳过（排版未完成）。")
    if not lettering.get("items"):
        notes.append("lettering.json 缺失或无 items；几何 QC 跳过（嵌字未完成）。")
    if notes:
        return {
            "kind": KIND,
            "schema_version": 1,
            "chapter": chapter,
            "summary": {"checked_slots": 0, "block": 0, "warn": 0},
            "findings": [],
            "notes": notes,
        }

    # 只检查真的承载文字条目的槽位；孤儿槽位不算嵌字问题。
    used_slot_ids = {
        str(item.get("slot_id"))
        for item in lettering.get("items") or []
        if isinstance(item, dict) and str(item.get("slot_id") or "").strip()
    }
    items_by_slot: dict[str, dict[str, Any]] = {
        str(item.get("slot_id")): item
        for item in lettering.get("items") or []
        if isinstance(item, dict) and str(item.get("slot_id") or "").strip()
    }

    checked = 0
    for segment in layout.get("segments") or []:
        if not isinstance(segment, dict):
            continue
        seg_w = float(segment.get("width") or 0)
        seg_h = float(segment.get("height") or 0)
        safe_margin = SAFE_MARGIN_BASE * (seg_w / BASE_CANVAS_WIDTH if seg_w else 1)
        min_font = MIN_FONT_BASE * (seg_w / BASE_CANVAS_WIDTH if seg_w else 1)
        for panel in segment.get("panels") or []:
            if not isinstance(panel, dict):
                continue
            pid = str(panel.get("panel_id") or "?")
            panel_rect = rect(panel)
            slots = [
                slot
                for slot in panel.get("bubble_slots") or []
                if isinstance(slot, dict) and str(slot.get("slot_id") or "") in used_slot_ids
            ]
            text_slots = [s for s in slots if str(s.get("type") or "dialogue") in {"dialogue", "narration"}]
            if len(text_slots) > MAX_BUBBLES_PER_PANEL:
                findings.append(finding(
                    "warn", "lettering_bubble_density", pid,
                    f"{pid} 有 {len(text_slots)} 个对白/旁白槽位，超过条漫单格上限 {MAX_BUBBLES_PER_PANEL}——一屏文字过密影响竖向阅读节奏。",
                    "回 comic-script 拆格或合并台词，或把次要信息移到相邻格。",
                ))
            slot_rects: list[tuple[str, tuple[float, float, float, float]]] = []
            for slot in slots:
                sid = str(slot.get("slot_id") or "?")
                r = rect(slot)
                if r is None:
                    continue
                checked += 1
                x, y, w, h = r
                if x < 0 or y < 0 or (seg_w and x + w > seg_w) or (seg_h and y + h > seg_h):
                    findings.append(finding(
                        "block", "lettering_out_of_canvas", pid,
                        f"{pid} 槽位 {sid} bbox({x:.0f},{y:.0f},{w:.0f},{h:.0f}) 超出 segment 画布 {seg_w:.0f}x{seg_h:.0f}——渲染必然裁字。",
                        "修 layout.json 槽位坐标后重跑 build_lettering.py 与 export_longstrip.py --render。",
                    ))
                    continue
                if seg_w and (x < safe_margin or x + w > seg_w - safe_margin):
                    findings.append(finding(
                        "warn", "lettering_safe_area", pid,
                        f"{pid} 槽位 {sid} 距画布左右边缘不足安全边距 {safe_margin:.0f}px，窄屏/圆角设备可能切字。",
                        "槽位内移或缩窄气泡宽度。",
                    ))
                if panel_rect is not None:
                    px, py, pw, ph = panel_rect
                    if (
                        x < px - PANEL_OVERFLOW_TOLERANCE
                        or y < py - PANEL_OVERFLOW_TOLERANCE
                        or x + w > px + pw + PANEL_OVERFLOW_TOLERANCE
                        or y + h > py + ph + PANEL_OVERFLOW_TOLERANCE
                    ):
                        findings.append(finding(
                            "warn", "lettering_outside_panel", pid,
                            f"{pid} 槽位 {sid} 超出所属格边界（容差 {PANEL_OVERFLOW_TOLERANCE}px）——气泡会压到相邻格或 gutter。",
                            "调整槽位坐标或放大格高，保持气泡归属清晰。",
                        ))
                item = items_by_slot.get(sid) or {}
                style = item.get("style") if isinstance(item.get("style"), dict) else {}
                size = style.get("size")
                if isinstance(size, (int, float)) and str(item.get("type")) in {"dialogue", "narration"} and size < min_font:
                    findings.append(finding(
                        "warn", "lettering_font_too_small", pid,
                        f"{pid} 槽位 {sid} 字号 {size} 低于最小可读字号 {min_font:.0f}px（@画布宽 {seg_w:.0f}）。",
                        "调大 lettering style.size 或减字数扩气泡。",
                    ))
                slot_rects.append((sid, r))
            for i in range(len(slot_rects)):
                for j in range(i + 1, len(slot_rects)):
                    if rects_overlap(slot_rects[i][1], slot_rects[j][1]):
                        findings.append(finding(
                            "warn", "lettering_overlap", pid,
                            f"{pid} 槽位 {slot_rects[i][0]} 与 {slot_rects[j][0]} bbox 相交——对白互压/遮挡。",
                            "错开槽位坐标或合并台词。",
                        ))

    return {
        "kind": KIND,
        "schema_version": 1,
        "chapter": chapter,
        "summary": {
            "checked_slots": checked,
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
        },
        "findings": findings,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画嵌字几何 QC（确定性坐标检查）")
    parser.add_argument("project_root")
    parser.add_argument("chapter", nargs="?", default="第1话")
    parser.add_argument("--chapter", dest="chapter_opt", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    chapter = args.chapter_opt or args.chapter
    report = analyze(root, chapter)
    if args.write:
        out = root / "生产数据" / f"{KIND}_{chapter}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
