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


def test_fight_exchange_contract_backfills_required_fields():
    data = {
        "clips": [
            {
                "id": "C_FIGHT",
                "label": "横刀反打",
                "template": "fight_exchange",
                "template_contract": {
                    "axis": "姜月初由画面左下向右上斩出，狼妖从深景扑来。",
                    "beats": ["起手拔刀", "刀爪撞点", "狼妖后撤"],
                },
                "character_ids": ["CHAR_姜月初", "GROUP_狼妖"],
                "object_ids": ["PROP_横刀"],
                "entity_schedule": {"required_presence": ["CHAR_姜月初", "GROUP_狼妖"]},
                "continuity": {
                    "start_state": "横刀未完全出鞘，狼妖扑近。",
                    "end_state": "刀爪撞开，狼妖被逼退。",
                    "eyeline": "姜月初锁狼妖首领，狼妖看刀锋。",
                    "shot_size": "MS 起手 → CU 撞点 → WS 后撤",
                    "need_endframe": True,
                    "transition": "impact_cut",
                    "entry_exit": "狼妖从深景入画，尾帧向画面右侧退开。",
                },
                "shots": [
                    {"desc": "姜月初横刀出鞘。", "camera": "低机位侧前方跟刀。"},
                    {"desc": "刀爪撞出火星。", "camera": "撞点特写后快速拉开。"},
                ],
            }
        ]
    }

    bf.backfill(data)

    contract = data["clips"][0]["template_contract"]
    assert contract["template_id"] == "fight_exchange"
    for field in bf.spectacle_required_fields("fight_exchange"):
        assert contract.get(field), field
