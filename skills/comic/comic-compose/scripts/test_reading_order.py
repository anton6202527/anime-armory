#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import export_longstrip as ex


def _rtl_layout():
    # 页漫 RTL row: reader-first panel is on the RIGHT (larger x). A (y,x) sort
    # would emit P002 (x=0) before P001 (x=800) — backwards. reading_order fixes it.
    return {
        "reading_direction": "从右到左",
        "segments": [{
            "segment_id": "S001",
            "reading_order": ["P001", "P002"],
            "panels": [
                {"panel_id": "P001", "x": 800, "y": 0, "w": 700, "h": 1000},
                {"panel_id": "P002", "x": 0, "y": 0, "w": 700, "h": 1000},
            ],
        }],
    }


def test_reading_order_honored_over_coordinate_sort():
    assert ex.ordered_panel_ids(_rtl_layout()) == ["P001", "P002"]
    ordered = [p["panel_id"] for p in ex.segment_panels_in_reading_order(_rtl_layout()["segments"][0])]
    assert ordered == ["P001", "P002"]


def test_falls_back_to_authored_panels_order_without_reading_order():
    seg = {"panels": [{"panel_id": "P001", "x": 800}, {"panel_id": "P002", "x": 0}]}
    # no reading_order → authored array order (NOT re-sorted by x)
    assert [p["panel_id"] for p in ex.segment_panels_in_reading_order(seg)] == ["P001", "P002"]
