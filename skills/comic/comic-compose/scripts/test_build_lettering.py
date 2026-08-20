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


def test_build_lettering_carries_drawn_sfx_plan() -> None:
    panel_script = {
        "chapter": "第1话",
        "panels": [
            {
                "panel_id": "P001",
                "sfx": ["砰"],
            }
        ],
    }
    layout = {
        "segments": [
            {
                "panels": [
                    {
                        "panel_id": "P001",
                        "bubble_slots": [{"slot_id": "B001S", "type": "sfx"}],
                    }
                ]
            }
        ]
    }
    finishing_map = {
        "P001": {
            "lettering_sfx_plan": {
                "mode": "drawn_sfx",
                "integration": "along impact zone",
                "shape": "jagged impact",
            }
        }
    }

    lettering = build_lettering.build_lettering(panel_script, layout, {}, "中文", finishing_map)

    item = lettering["items"][0]
    assert item["type"] == "sfx"
    assert item["style"]["drawn_lettering_mode"] == "drawn_sfx"
    assert item["style"]["integration"] == "along impact zone"
    assert item["style"]["shape"] == "jagged impact"


def test_build_lettering_extracts_structured_sfx_and_distinct_slots() -> None:
    panel_script = {
        "chapter": "第1话",
        "panels": [
            {
                "panel_id": "P001",
                "sfx": [
                    {"text": "轰！", "text_target": "轰！", "source": "猛虎落地"},
                    {"text": "沙——", "text_target": "沙——", "source": "草叶摩擦"},
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
                        "bubble_slots": [
                            {"slot_id": "B001S1", "type": "sfx"},
                            {"slot_id": "B001S2", "type": "sfx"},
                        ],
                    }
                ]
            }
        ]
    }

    lettering = build_lettering.build_lettering(panel_script, layout, {}, "中文")

    assert [item["text"] for item in lettering["items"]] == ["轰！", "沙——"]
    assert [item["slot_id"] for item in lettering["items"]] == ["B001S1", "B001S2"]
    assert [item["sound_source"] for item in lettering["items"]] == ["猛虎落地", "草叶摩擦"]
    assert all("{'text'" not in item["text"] for item in lettering["items"])


def test_translation_todo_created_and_cleared(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    (root / "排版" / "第1话").mkdir(parents=True)
    lettering = {
        "language_mode": "中上英下",
        "items": [
            {
                "item_id": "L001",
                "content_ref": "panel:P001.dialogue:1",
                "panel_id": "P001",
                "type": "dialogue",
                "source_text": "你是谁？",
                "source_text_sha256": "current-sha",
                "text": "你是谁？",
                "text_zh": "你是谁？",
            },
            {
                "item_id": "L002",
                "content_ref": "panel:P001.dialogue:2",
                "panel_id": "P001",
                "type": "dialogue",
                "text": "报上名来。",
                "text_zh": "报上名来。",
                "text_en": "State your name.",
            },
        ],
    }

    todo = build_lettering.write_translation_todo(root, "第1话", lettering)

    assert todo is not None and todo.is_file()
    import json

    payload = json.loads(todo.read_text(encoding="utf-8"))
    assert payload["pending_count"] == 1
    assert payload["schema_version"] == 2
    assert payload["pending"][0]["content_ref"] == "panel:P001.dialogue:1"
    assert payload["pending"][0]["source_text_sha256"] == "current-sha"
    assert payload["pending"][0]["text_zh"] == "你是谁？"
    assert '"source_text_sha256"' in payload["instructions"]

    # 补齐译文后重跑 → todo 清除
    lettering["items"][0]["text_en"] = "Who are you?"
    assert build_lettering.write_translation_todo(root, "第1话", lettering) is None
    assert not todo.is_file()


def test_lettering_style_baseline_persists_and_flags_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    (root / "排版").mkdir(parents=True)
    ch1 = {
        "items": [
            {"type": "dialogue", "style": {"font": "project_default", "size": 44, "direction": "horizontal", "bubble": "round"}},
        ]
    }
    build_lettering.check_lettering_style_baseline(root, "第1话", ch1)
    assert (root / "排版" / "lettering_style_baseline.json").is_file()
    assert ch1["style_consistency"]["mismatches"] == []

    ch2 = {
        "items": [
            {"type": "dialogue", "style": {"font": "other_font", "size": 52, "direction": "horizontal", "bubble": "round"}},
        ]
    }
    build_lettering.check_lettering_style_baseline(root, "第2话", ch2)
    mismatches = ch2["style_consistency"]["mismatches"]
    assert mismatches and "不一致" in mismatches[0]


def _layout_two_dialogue_slots():
    # panel has 3 script dialogues but D2 has empty target → layout emits slots
    # only for D1 and D3, with content_ref binding them to the right lines.
    return {
        "reading_direction": "从上到下",
        "segments": [{
            "segment_id": "S001",
            "reading_order": ["P001"],
            "panels": [{
                "panel_id": "P001",
                "bubble_slots": [
                    {"slot_id": "P001-b1", "type": "dialogue", "content_ref": "panel:P001.dialogue:1", "speaker": "甲"},
                    {"slot_id": "P001-b3", "type": "dialogue", "content_ref": "panel:P001.dialogue:3", "speaker": "乙"},
                ],
            }],
        }],
    }


def test_content_ref_binding_survives_empty_middle_dialogue():
    panel_script = {
        "chapter": "第1话",
        "panels": [{
            "panel_id": "P001",
            "dialogue": [
                {"speaker": "甲", "text_target": "第一句"},
                {"speaker": "旁", "text_target": ""},            # empty → no slot, no balloon
                {"speaker": "乙", "text_target": "第三句"},
            ],
        }],
    }
    result = build_lettering.build_lettering(panel_script, _layout_two_dialogue_slots(), {}, "中文")
    dialogue = [it for it in result["items"] if it["type"] == "dialogue"]
    # empty-target middle line produces no balloon; the two real lines bind to the
    # slot that matches their content_ref (NOT positionally shifted)
    assert len(dialogue) == 2
    first = next(it for it in dialogue if it["content_ref"] == "panel:P001.dialogue:1")
    third = next(it for it in dialogue if it["content_ref"] == "panel:P001.dialogue:3")
    assert first["slot_id"] == "P001-b1" and first["speaker"] == "甲"
    assert third["slot_id"] == "P001-b3" and third["speaker"] == "乙"
    # slot speaker carried for review cross-check
    assert third["slot_speaker"] == "乙"


def test_content_ref_binding_leaves_unslotted_real_line_visible():
    panel_script = {
        "chapter": "第1话",
        "panels": [{
            "panel_id": "P001",
            "dialogue": [
                {"speaker": "甲", "text_target": "第一句"},
                {"speaker": "乙", "text_target": "第二句"},  # no slot for dialogue:2
                {"speaker": "丙", "text_target": "第三句"},
            ],
        }],
    }
    result = build_lettering.build_lettering(panel_script, _layout_two_dialogue_slots(), {}, "中文")
    dialogue = [it for it in result["items"] if it["type"] == "dialogue"]
    unslotted = [it for it in dialogue if it["content_ref"] == "panel:P001.dialogue:2"]
    assert unslotted and unslotted[0]["slot_id"] == ""  # kept so review can flag it
