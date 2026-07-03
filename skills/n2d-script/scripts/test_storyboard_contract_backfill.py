#!/usr/bin/env python3
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import storyboard_contract_backfill as bf  # noqa: E402


def test_backfill_policy_template_and_presence_chain():
    data = {
        "clips": [
            {
                "id": "C1",
                "template": "system_panel",
                "template_contract": {"template_id": "system_panel", "beats": ["弹出"], "blocking": "面板", "camera_rule": "留白", "continuity_must": ["统一"], "negative": ["不要烤字"]},
                "character_ids": ["CHAR_A"],
                "object_ids": ["VFX_系统面板"],
                "screen_text_lines": [{"text": "到账"}],
                "continuity": {"start_state": "A 起", "end_state": "A 看面板", "need_endframe": True, "transition": "cut", "expression_span": "高"},
            },
            {
                "id": "C2",
                "template": "dialogue_shot_reverse",
                "template_contract": {"template_id": "dialogue_shot_reverse", "beats": ["问答"], "blocking": "A/B 反打", "camera_rule": "守轴", "continuity_must": ["不越轴"], "negative": ["不新增人"]},
                "character_ids": ["CHAR_A", "CHAR_B"],
                "continuity": {"start_state": "B 入画", "end_state": "A 回答", "need_endframe": True, "transition": "cut", "eyeline": "A 看 B"},
            },
            {
                "id": "C3",
                "template": "intimate_interaction",
                "template_contract": {"template_id": "intimate_interaction", "beats": ["合眼"], "blocking": "手部", "camera_rule": "特写", "continuity_must": ["不暧昧"], "negative": ["不拥抱"]},
                "character_ids": ["CHAR_A", "CHAR_DEAD"],
                "continuity": {"start_state": "遗体特写", "end_state": "合眼", "need_endframe": True, "transition": "cut"},
            },
        ]
    }

    changes = bf.backfill(data)

    assert data["policy"]["tailframe_default"] is True
    assert data["clips"][0]["continuity"]["expression_span"] == "大"
    assert data["clips"][1]["continuity"]["start_state"] == "A 看面板"
    assert "入画" in data["clips"][0]["continuity"]["entry_exit"]
    assert "offscreen_presence" in data["clips"][0]["entity_schedule"]
    assert data["clips"][0]["template_contract"]["text_layer"] == "compose_overlay_only"
    assert data["clips"][1]["template_contract"]["axis"]
    assert data["clips"][2]["template_contract"]["distance_boundary"]
    assert changes["template_contract"] >= 3


def test_write_json_atomic_roundtrip(tmp_path):
    path = tmp_path / "storyboard.json"
    payload = {"clips": []}
    bf.write_json_atomic(path, payload)
    assert json.loads(path.read_text(encoding="utf-8")) == payload
