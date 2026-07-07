#!/usr/bin/env python3
"""Tests for storyboard contract validator."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import validate_storyboard_contract as VC  # noqa: E402


def _long_fight(continuity):
    return {
        "id": "EP01_CLIP01",
        "duration": 10.0,
        "template": "fight_exchange",
        "template_contract": {"template_id": "fight_exchange", "beats": ["起手", "命中", "收势"]},
        "continuity": continuity,
    }


def test_long_fight_with_only_midframe_requires_anchors():
    rows = []
    VC.check_anchor_contract(
        rows,
        _long_fight({
            "start_state": "s",
            "end_state": "e",
            "transition": "硬切",
            "need_endframe": True,
            "midframe": {
                "midframe_png": "出图/第1集/图片/镜头01_mid.png",
                "split_at_sec": 5.0,
                "reason": "default",
            },
        }),
        "storyboard Clip_01",
        enforce_midframe=True,
    )

    assert any(row["dimension"] == "重动作多中帧" and row["severity"] == "block" for row in rows)


def test_long_fight_with_anchors_passes_action_anchor_rule():
    rows = []
    VC.check_anchor_contract(
        rows,
        _long_fight({
            "start_state": "s",
            "end_state": "e",
            "transition": "硬切",
            "need_endframe": True,
            "anchors": [
                {"anchor_png": "出图/第1集/图片/镜头01_a1.png", "at_sec": 3.0, "reason": "起手后"},
                {"anchor_png": "出图/第1集/图片/镜头01_a2.png", "at_sec": 6.5, "reason": "命中收势"},
            ],
        }),
        "storyboard Clip_01",
        enforce_midframe=True,
    )

    assert not any(row["dimension"] == "重动作多中帧" for row in rows)


def test_long_dialogue_with_literal_hand_or_name_does_not_require_anchors():
    rows = []
    VC.check_anchor_contract(
        rows,
        {
            "id": "EP01_CLIP03",
            "duration": 11.0,
            "template": "dialogue_shot_reverse",
            "template_contract": {
                "template_id": "dialogue_shot_reverse",
                "beats": ["张老大手掌拍肩下命令", "江剑背影收拾行囊", "贺平生低头应是"],
            },
            "continuity": {
                "start_state": "s",
                "end_state": "e",
                "transition": "硬切",
                "need_endframe": True,
            },
        },
        "storyboard Clip_03",
        enforce_midframe=False,
    )

    assert not any(row["dimension"] == "重动作多中帧" for row in rows)


def test_transmigration_genre_words_do_not_require_realm_portal_template():
    rows = []
    VC.check_template_contract(
        rows,
        {
            "id": "EP01_CLIP01",
            "label": "死人堆惊醒",
            "scene": "荒野尸场，姜月初睁眼醒来。",
            "subtitle_lines": ["我穿越成犯人了？", "身下不是床，是尸堆。"],
        },
        "storyboard EP01_CLIP01",
    )

    assert not rows


def test_visual_realm_portal_words_still_require_template_contract():
    rows = []
    VC.check_template_contract(
        rows,
        {
            "id": "EP01_CLIP02",
            "scene": "现代青年被时空裂缝卷入异界山门。",
        },
        "storyboard EP01_CLIP02",
    )

    assert any("realm_portal" in row["message"] for row in rows)


def test_contract_fields_accept_documented_english_aliases():
    rows = []
    VC.check_contract_fields(
        rows,
        {
            "visual_contract": {
                "color_baseline": "cold gray",
                "scene_light_anchors": {"LOC": "moon left"},
                "axis_and_eyeline": {"LOC": "left-right"},
                "character_state_progression": ["clean to tired"],
                "shot_size_ladder": ["MS", "CU"],
            },
            "style_contract": {
                "style_name": "custom",
                "visual_tone": "semi-realistic 3D",
                "composition": "9:16 close emotion",
                "lighting": "cold moon with warm accent",
                "motion_boundaries": "slow push only",
                "negative": ["watermark"],
                "style_anchor": "出图/共享/图片/风格锚_custom.png",
            },
        },
        "storyboard.json",
    )

    assert not rows


def test_timeline_mismatch_blocks_manual_start_end_drift():
    rows = []
    VC.check_timeline(
        rows,
        [
            {"id": "Clip_01", "duration": 4.0, "start_sec": 0.0, "end_sec": 2.0},
            {"id": "Clip_02", "duration": 3.0, "start_sec": 2.0, "end_sec": 5.0},
        ],
        "storyboard.json",
    )

    assert any(row["dimension"] == "时间轴契约" and row["severity"] == "block" for row in rows)


def test_timeline_passes_when_start_end_follow_duration_sum():
    rows = []
    VC.check_timeline(
        rows,
        [
            {"id": "Clip_01", "duration": 4.0, "start_sec": 0.0, "end_sec": 4.0},
            {"id": "Clip_02", "duration": 3.0, "start_sec": 4.0, "end_sec": 7.0},
        ],
        "storyboard.json",
    )

    assert not rows


def test_inner_monologue_warns_when_multiple_visible_subjects_without_exception():
    rows = []
    VC.check_inner_focus_isolation(
        rows,
        {
            "id": "EP01_CLIP07",
            "description": "姜月初内心独白：这百妖谱到底是什么。",
            "dramatic_function": "内心戏，表现主角疑惧。",
            "character_ids": ["CHAR_01", "CHAR_02"],
            "entity_schedule": {"required_presence": ["CHAR_01", "CHAR_02"]},
        },
        "storyboard EP01_CLIP07",
    )

    assert any(row["dimension"] == "内心戏主体隔离" and row["severity"] == "warn" for row in rows)


def test_inner_monologue_context_reason_allows_visible_pressure_subject():
    rows = []
    VC.check_inner_focus_isolation(
        rows,
        {
            "id": "EP01_CLIP07",
            "description": "姜月初内心独白，虎妖在后景虚焦压迫。",
            "character_ids": ["CHAR_01", "CHAR_TIGER"],
            "entity_schedule": {"required_presence": ["CHAR_01", "CHAR_TIGER"]},
            "inner_focus_context_reason": "虎妖必须作为后景虚焦压迫符号。",
        },
        "storyboard EP01_CLIP07",
    )

    assert not rows
