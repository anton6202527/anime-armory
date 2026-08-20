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


def _write_settings(root, profile=None, platform=None):
    lines = ["# 设置"]
    if profile:
        lines.append(f"- 创作工艺档：{profile}")
    if platform:
        lines.append(f"- 目标平台：{platform}")
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


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


def test_literary_profile_accepts_registered_nontraditional_function(tmp_path):
    root = str(tmp_path)
    _write_settings(root, profile="literary")
    _write_cards(root, [_full_card(turn="", value_shift="", perceptual_shift="她第一次把沉默听成拒绝")])

    result = scene_cards.check(root)

    assert result["craft_profile"] == "literary"
    assert result["blocking"] == 0
    ids = {item["id"] for item in result["findings"]}
    assert "SCENE-CARD-MISSING-FIELDS" not in ids
    assert "SCENE-CARD-NARRATIVE-FUNCTION-MISSING" not in ids


def test_literary_profile_missing_all_functions_is_heuristic_warning(tmp_path):
    root = str(tmp_path)
    _write_settings(root, profile="文学小说")  # 中文别名经适配层归一
    _write_cards(root, [_full_card(turn="", value_shift="")])

    result = scene_cards.check(root)

    finding = next(
        item for item in result["findings"]
        if item["id"] == "SCENE-CARD-NARRATIVE-FUNCTION-MISSING"
    )
    assert result["craft_profile"] == "literary"
    assert result["blocking"] == 0
    assert finding["severity"] == "warning"
    assert finding["confidence"] == "heuristic"


def test_literary_allows_viewpoint_and_advises_missing_conventional_dynamics(tmp_path):
    root = str(tmp_path)
    _write_settings(root, profile="literary")
    _write_cards(root, [{
        "id": "SC001-01",
        "chapter": 1,
        "scene_no": 1,
        "viewpoint": "村中众人的合唱式视角",
        "motif_return": "每个人都记得不同颜色的河水",
    }])

    result = scene_cards.check(root)

    assert result["blocking"] == 0
    finding = next(
        item for item in result["findings"]
        if item["id"] == "SCENE-CARD-LITERARY-DYNAMICS-OMITTED"
    )
    assert finding["confidence"] == "heuristic"
    assert "desire" in finding["reason"] and "conflict" in finding["reason"]


def test_experimental_does_not_block_missing_conventional_scene_fields(tmp_path):
    root = str(tmp_path)
    _write_settings(root, profile="experimental")
    _write_cards(root, [{
        "id": "SC001-01",
        "chapter": 1,
        "scene_no": 1,
        "deliberate_stasis": "三页只记录灯影移动，让等待本身成为形式",
    }])

    result = scene_cards.check(root)

    assert result["blocking"] == 0
    ids = {item["id"] for item in result["findings"]}
    assert "SCENE-CARD-MISSING-FIELDS" not in ids
    assert "SCENE-CARD-NARRATIVE-FUNCTION-MISSING" not in ids


def test_literary_requires_only_attributable_pov_or_viewpoint(tmp_path):
    root = str(tmp_path)
    _write_settings(root, profile="literary")
    _write_cards(root, [{
        "id": "SC001-01",
        "chapter": 1,
        "scene_no": 1,
        "motif_return": "河水再次变色",
    }])

    result = scene_cards.check(root)

    finding = next(item for item in result["findings"] if item["id"] == "SCENE-CARD-MISSING-FIELDS")
    assert result["blocking"] == 1
    assert "pov|viewpoint" in finding["reason"]


def test_commercial_and_legacy_profiles_keep_turn_value_contract(tmp_path):
    for profile in ("commercial_serial", None):
        root = tmp_path / (profile or "legacy")
        root.mkdir()
        _write_settings(str(root), profile=profile, platform="晋江")
        _write_cards(
            str(root),
            [_full_card(turn="", value_shift="", revelation="旧信上的落款属于母亲")],
        )

        result = scene_cards.check(str(root))

        assert result["blocking"] == 1
        finding = next(item for item in result["findings"] if item["id"] == "SCENE-CARD-MISSING-FIELDS")
        assert "turn" in finding["reason"] and "value_shift" in finding["reason"]
        if profile is None:
            # 目标平台不替代独立工艺选择点；旧项目安全保持 genre_novel。
            assert result["craft_profile"] == "genre_novel"


def test_scaffold_includes_flexible_narrative_function_fields(tmp_path):
    root = str(tmp_path)
    scene_cards.scaffold(root, chapters=[1])
    with open(os.path.join(root, "设定", "scene_cards.json"), encoding="utf-8") as f:
        card = json.load(f)["scenes"][0]
    for field in (
        "viewpoint",
        "revelation",
        "relation_drift",
        "perceptual_shift",
        "motif_return",
        "deliberate_stasis",
    ):
        assert field in card


def test_unsupported_custom_profile_blocks_instead_of_silent_fallback(tmp_path):
    root = str(tmp_path)
    _write_settings(root, profile="hybrid_lyric")
    _write_cards(root, [_full_card()])

    result = scene_cards.check(root)

    assert result["craft_profile"] == "hybrid_lyric"
    assert any(
        item["id"] == "SCENE-CARD-CRAFT-PROFILE-UNSUPPORTED"
        for item in result["findings"]
    )
    assert result["blocking"] >= 1
