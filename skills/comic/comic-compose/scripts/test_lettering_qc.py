#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lettering_qc 几何检查的封闭测试。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import lettering_qc


def write_fixture(tmp_path: Path, slots: list[dict], items: list[dict] | None = None) -> Path:
    root = tmp_path / "作品"
    (root / "排版" / "第1话").mkdir(parents=True)
    layout = {
        "segments": [
            {
                "segment_id": "SCROLL_001",
                "width": 1440,
                "height": 4000,
                "panels": [
                    {"panel_id": "P001", "x": 72, "y": 28, "w": 1296, "h": 960, "bubble_slots": slots}
                ],
            }
        ]
    }
    if items is None:
        items = [
            {"item_id": f"L{i:03d}", "panel_id": "P001", "type": "dialogue",
             "slot_id": slot["slot_id"], "style": {"size": 44}}
            for i, slot in enumerate(slots, 1)
        ]
    (root / "排版" / "第1话" / "layout.json").write_text(json.dumps(layout, ensure_ascii=False), encoding="utf-8")
    (root / "排版" / "第1话" / "lettering.json").write_text(
        json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8")
    return root


def codes(report: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in report["findings"]:
        out[item["code"]] = out.get(item["code"], 0) + 1
    return out


def test_clean_layout_passes(tmp_path: Path) -> None:
    root = write_fixture(tmp_path, [
        {"slot_id": "B1", "type": "dialogue", "x": 120, "y": 76, "w": 430, "h": 88},
    ])
    report = lettering_qc.analyze(root, "第1话")
    assert report["findings"] == []
    assert report["summary"]["checked_slots"] == 1


def test_out_of_canvas_blocks(tmp_path: Path) -> None:
    root = write_fixture(tmp_path, [
        {"slot_id": "B1", "type": "dialogue", "x": 1200, "y": 76, "w": 400, "h": 88},
    ])
    report = lettering_qc.analyze(root, "第1话")
    got = codes(report)
    assert got.get("lettering_out_of_canvas") == 1
    assert report["summary"]["block"] == 1


def test_safe_area_and_outside_panel_warn(tmp_path: Path) -> None:
    root = write_fixture(tmp_path, [
        {"slot_id": "B1", "type": "dialogue", "x": 8, "y": 2000, "w": 300, "h": 88},
    ])
    report = lettering_qc.analyze(root, "第1话")
    got = codes(report)
    assert got.get("lettering_safe_area") == 1
    assert got.get("lettering_outside_panel") == 1  # y=2000 在格外（格高 960）


def test_bubble_density_warns(tmp_path: Path) -> None:
    slots = [
        {"slot_id": f"B{i}", "type": "dialogue", "x": 120, "y": 76 + i * 200, "w": 300, "h": 80}
        for i in range(4)
    ]
    root = write_fixture(tmp_path, slots)
    report = lettering_qc.analyze(root, "第1话")
    assert codes(report).get("lettering_bubble_density") == 1


def test_overlap_warns(tmp_path: Path) -> None:
    root = write_fixture(tmp_path, [
        {"slot_id": "B1", "type": "dialogue", "x": 120, "y": 76, "w": 430, "h": 88},
        {"slot_id": "B2", "type": "dialogue", "x": 300, "y": 100, "w": 430, "h": 88},
    ])
    report = lettering_qc.analyze(root, "第1话")
    assert codes(report).get("lettering_overlap") == 1


def test_small_font_warns(tmp_path: Path) -> None:
    slots = [{"slot_id": "B1", "type": "dialogue", "x": 120, "y": 76, "w": 430, "h": 88}]
    items = [{"item_id": "L001", "panel_id": "P001", "type": "dialogue", "slot_id": "B1", "style": {"size": 20}}]
    root = write_fixture(tmp_path, slots, items)
    report = lettering_qc.analyze(root, "第1话")
    assert codes(report).get("lettering_font_too_small") == 1


def test_unused_slots_are_ignored(tmp_path: Path) -> None:
    slots = [
        {"slot_id": "B1", "type": "dialogue", "x": 120, "y": 76, "w": 430, "h": 88},
        {"slot_id": "B_EMPTY", "type": "dialogue", "x": -50, "y": 76, "w": 430, "h": 88},
    ]
    items = [{"item_id": "L001", "panel_id": "P001", "type": "dialogue", "slot_id": "B1", "style": {"size": 44}}]
    root = write_fixture(tmp_path, slots, items)
    report = lettering_qc.analyze(root, "第1话")
    assert report["findings"] == [], "无文字条目的孤儿槽位不算嵌字问题"


def test_missing_inputs_graceful(tmp_path: Path) -> None:
    root = tmp_path / "空作品"
    root.mkdir()
    report = lettering_qc.analyze(root, "第1话")
    assert report["findings"] == []
    assert report["notes"]


def test_overflowing_text_is_flagged(tmp_path: Path) -> None:
    # a tall wall of CJK text in a short slot cannot fit at font 44
    slot = {"slot_id": "B1", "type": "dialogue", "x": 120, "y": 76, "w": 300, "h": 80}
    long_text = "这是一段非常非常长的台词" * 8
    items = [{"item_id": "L001", "panel_id": "P001", "type": "dialogue",
              "slot_id": "B1", "text": long_text, "text_zh": long_text, "style": {"size": 44}}]
    root = write_fixture(tmp_path, [slot], items)
    report = lettering_qc.analyze(root, "第1话")
    assert "lettering_text_overflow" in codes(report)


def test_short_text_fits_no_overflow(tmp_path: Path) -> None:
    slot = {"slot_id": "B1", "type": "dialogue", "x": 120, "y": 76, "w": 430, "h": 300}
    items = [{"item_id": "L001", "panel_id": "P001", "type": "dialogue",
              "slot_id": "B1", "text": "来了。", "text_zh": "来了。", "style": {"size": 44}}]
    root = write_fixture(tmp_path, [slot], items)
    report = lettering_qc.analyze(root, "第1话")
    assert "lettering_text_overflow" not in codes(report)
