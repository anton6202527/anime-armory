#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_lettering


def test_build_lettering_prefers_target_text_for_english_mode() -> None:
    panel_script = {
        "chapter": "第1话",
        "panels": [
            {
                "panel_id": "P001",
                "meaning_zh": "他说那座老屋仍在河边。",
                "dialogue": [
                    {
                        "speaker": "A",
                        "text": "La vieille maison etait pres de la riviere.",
                        "text_target": "The old house still stood by the river.",
                        "source_text": "La vieille maison etait pres de la riviere.",
                    }
                ],
            }
        ],
    }
    layout = {
        "segments": [
            {
                "panels": [
                    {
                        "panel_id": "P001",
                        "bubble_slots": [{"slot_id": "B001D1", "type": "dialogue"}],
                    }
                ]
            }
        ]
    }

    lettering = build_lettering.build_lettering(panel_script, layout, {}, "英文")

    item = lettering["items"][0]
    assert item["text"] == "The old house still stood by the river."
    assert item["text_en"] == "The old house still stood by the river."
    assert item["text_source"] == "La vieille maison etait pres de la riviere."
    assert item["text_zh"] == "他说那座老屋仍在河边。"
    assert item["lang"] == "en"
    assert item["dir"] == "ltr"
    assert item["source_lang"] == "und"


def test_build_lettering_uses_narration_target_for_chinese_mode() -> None:
    panel_script = {
        "chapter": "第1话",
        "panels": [
            {
                "panel_id": "P001",
                "source_excerpt": "太祖曰。",
                "narration": "太祖曰。",
                "narration_target": "太祖开口了。",
            }
        ],
    }
    layout = {
        "segments": [
            {
                "panels": [
                    {
                        "panel_id": "P001",
                        "bubble_slots": [{"slot_id": "B001N", "type": "narration"}],
                    }
                ]
            }
        ]
    }

    lettering = build_lettering.build_lettering(panel_script, layout, {}, "中文")

    item = lettering["items"][0]
    assert item["text"] == "太祖开口了。"
    assert item["text_zh"] == "太祖开口了。"
    assert item["text_source"] == "太祖曰。"
    assert item["lang"] == "zh-Hans"
    assert item["line_break"] == "cjk"
