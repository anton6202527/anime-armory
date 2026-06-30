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
