"""SIGNATURE_EFFECT_LEXICON 活引用与 normalize_signature_effect 归一测试。"""
from __future__ import annotations

import n2d_const as C
from n2d_logic import normalize_signature_effect


def test_lexicon_loaded_from_manifest() -> None:
    assert len(C.SIGNATURE_EFFECT_LEXICON) == 48
    # 每条都带回链运镜与身份风险级。
    for name, spec in C.SIGNATURE_EFFECT_LEXICON.items():
        assert spec["id"], name
        assert spec["camera_move"], name
        assert spec["identity_risk"] in {"low", "medium", "high"}, name


def test_high_identity_risk_set_matches_manifest() -> None:
    # 换装/换脸/近脸升格/对打/名场面/化鸟/上帝视角落地 都属高身份风险。
    assert "普拉达换装" in C.HIGH_IDENTITY_RISK_EFFECTS
    assert "面部换拍" in C.HIGH_IDENTITY_RISK_EFFECTS
    assert "升格KO" in C.HIGH_IDENTITY_RISK_EFFECTS
    # 第二批高身份风险：液态金属/破碎虚空/气场爆发/凤凰浴火/化妆品涂抹。
    assert "液态金属" in C.HIGH_IDENTITY_RISK_EFFECTS
    assert "化妆品涂抹" in C.HIGH_IDENTITY_RISK_EFFECTS
    # 低风险特效不应误列。
    assert "产品扫光" not in C.HIGH_IDENTITY_RISK_EFFECTS
    assert "city drive" not in C.HIGH_IDENTITY_RISK_EFFECTS
    assert "御剑飞行" not in C.HIGH_IDENTITY_RISK_EFFECTS


def test_normalize_recognizes_new_wuxia_and_scifi_batch() -> None:
    for name in ("御剑飞行", "剑气斩", "巨龙盘旋", "纳米装甲合体", "超空间跳跃", "千军万马"):
        result = normalize_signature_effect(f"本镜{name}")
        assert any(e["zh"] == name for e in result["effects"]), name


def test_normalize_recognizes_every_effect_by_name() -> None:
    for name in C.SIGNATURE_EFFECT_LEXICON:
        result = normalize_signature_effect(f"本镜采用{name}处理")
        assert result["recognized"], name
        assert any(e["zh"] == name for e in result["effects"]), name


def test_normalize_flags_high_identity_risk() -> None:
    result = normalize_signature_effect("模特走秀 普拉达换装 连续切换")
    assert result["has_high_identity_risk"] is True
    primary = result["effects"][0]
    assert primary["negatives"], "high-risk effect must carry negatives"


def test_normalize_no_false_positive_on_plain_text() -> None:
    result = normalize_signature_effect("两人在茶馆对话，固定机位，轻微推镜")
    assert result["recognized"] is False
    assert result["effects"] == []


def test_normalize_recognizes_alias() -> None:
    result = normalize_signature_effect("用换脸转场把甲切成乙")
    assert any(e["id"] == "face_morph" for e in result["effects"])
