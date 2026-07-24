#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scene_cards outcome/plotline 字段（try-fail 循环 + 情节线标签）测试。"""
import json
import os

import scene_cards


def _write_cards(root, scenes):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_scene_cards", "scenes": scenes}, f, ensure_ascii=False)


def _full_card(**over):
    card = {
        "id": "SC001-01", "chapter": 1, "scene_no": 1,
        "pov": "沈砚", "desire": "查案", "obstacle": "官府阻挠", "conflict": "对峙",
        "turn": "拿到名册", "value_shift": "从被动到主动",
    }
    card.update(over)
    return card


def test_outcome_invalid_value_flagged(tmp_path):
    root = str(tmp_path)
    _write_cards(root, [_full_card(outcome="大获全胜")])
    result = scene_cards.check(root)
    ids = [f["id"] for f in result["findings"]]
    assert "SCENE-CARD-OUTCOME-INVALID" in ids
    # 建议级不阻断
    assert result["blocking"] == 0


def test_outcome_enum_and_empty_pass(tmp_path):
    root = str(tmp_path)
    _write_cards(root, [
        _full_card(id="SC001-01", outcome="yes-but"),
        _full_card(id="SC001-02", scene_no=2, outcome=""),  # 留空=不判定，合法
    ])
    result = scene_cards.check(root)
    assert "SCENE-CARD-OUTCOME-INVALID" not in [f["id"] for f in result["findings"]]


def test_scaffold_includes_outcome_and_plotline(tmp_path):
    root = str(tmp_path)
    scene_cards.scaffold(root, chapters=[1])
    with open(os.path.join(root, "设定", "scene_cards.json"), encoding="utf-8") as f:
        data = json.load(f)
    card = data["scenes"][0]
    assert "outcome" in card and "plotline" in card
    # 可选字段清单同步（SCENE-CARD-WEAK-FIELDS 会提示补齐）
    assert "outcome" in scene_cards.OPTIONAL_FIELDS
    assert "plotline" in scene_cards.OPTIONAL_FIELDS


def test_turn_source_enum_validation(tmp_path):
    root = str(tmp_path)
    _write_cards(root, [
        _full_card(id="SC001-01", turn_source="巧合"),                  # 枚举内，合法
        _full_card(id="SC001-02", scene_no=2, turn_source="天降神兵"),  # 枚举外 → warning
        _full_card(id="SC001-03", scene_no=3, turn_source=""),          # 留空=不判定
    ])
    result = scene_cards.check(root)
    hits = [f for f in result["findings"] if f["id"] == "SCENE-CARD-TURN-SOURCE-INVALID"]
    assert len(hits) == 1 and hits[0]["scene_id"] == "SC001-02"
    assert result["blocking"] == 0


def test_scaffold_includes_turn_source(tmp_path):
    root = str(tmp_path)
    scene_cards.scaffold(root, chapters=[1])
    with open(os.path.join(root, "设定", "scene_cards.json"), encoding="utf-8") as f:
        data = json.load(f)
    assert "turn_source" in data["scenes"][0]
    assert "turn_source" in scene_cards.OPTIONAL_FIELDS
