#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path
import json

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_layout


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_dialogue_slot_height_uses_text_target_length() -> None:
    short_panel = {
        "panel_id": "P001",
        "story_function": "reaction",
        "dialogue": [{"text": "短句"}],
    }
    long_panel = {
        "panel_id": "P002",
        "story_function": "reaction",
        "dialogue": [
            {
                "text": "短句",
                "text_target": "This translated line is deliberately much longer than the source and should need more than two bubble lines.",
            }
        ],
    }

    short_slot = build_layout.bubble_slots(short_panel, {"x": 0, "y": 0, "w": 1440, "h": 700}, 1)[0]
    long_slot = build_layout.bubble_slots(long_panel, {"x": 0, "y": 0, "w": 1440, "h": 900}, 2)[0]

    assert long_slot["h"] > short_slot["h"]
    assert build_layout.panel_height(long_panel) > build_layout.panel_height(short_panel)


def test_build_layout_inherits_name_board_manuscript_and_panel_metadata(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：页漫\n- 阅读方向：从右到左\n- 页面尺寸：1440xauto\n- 原稿规格：B5商漫\n", encoding="utf-8")
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {
            "panels": [
                {
                    "panel_id": "P001",
                    "story_function": "opening_hook",
                    "description": "主角推门。",
                    "dialogue": [{"text": "来了。"}],
                }
            ]
        },
    )
    write_json(
        root / "排版" / chapter / "name_board.json",
        {
            "manuscript": {
                "spec": "B5商漫",
                "trim_box": {"x": 0, "y": 0, "w": 1440, "h": 2036},
                "safe_area": {"x": 96, "y": 96, "w": 1248, "h": 1844},
                "bleed": 48,
                "inner_frame": {"x": 144, "y": 144, "w": 1152, "h": 1748},
            },
            "pages": [
                {
                    "page_id": "PAGE_001",
                    "page_side": "right",
                    "spread_id": "SPREAD_001",
                    "page_turn_hook": "P001 opening_hook",
                    "panels": [
                        {
                            "panel_id": "P001",
                            "layout_weight": "heavy",
                            "panel_shape": "wide",
                            "border_style": "standard",
                            "bubble_first": "right_top",
                            "effects_hint": "focus lines",
                        }
                    ],
                }
            ],
        },
    )

    layout = build_layout.build_layout(root, chapter, 0, 28)
    panel = layout["segments"][0]["panels"][0]

    assert layout["manuscript"]["spec"] == "B5商漫"
    assert layout["name_board"] == "排版/第1话/name_board.json"
    assert panel["layout_weight"] == "heavy"
    assert panel["page_side"] == "right"
    assert panel["bubble_first"] == "right_top"
    assert panel["bubble_slots"][0]["x"] > 700
