#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_layout


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
