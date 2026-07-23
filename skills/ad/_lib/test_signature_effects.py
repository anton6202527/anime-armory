"""signature_effects 检测模块测试（本线自包含，无跨线依赖）。"""
from __future__ import annotations

import signature_effects as S


def test_lexicon_loaded_from_this_line_manifest() -> None:
    assert len(S.SIGNATURE_EFFECT_LEXICON) == 48
    for name, spec in S.SIGNATURE_EFFECT_LEXICON.items():
        assert spec["id"], name
        assert spec["camera_move"], name
        assert spec["identity_risk"] in {"low", "medium", "high"}, name


def test_high_identity_risk_set() -> None:
    assert len(S.HIGH_IDENTITY_RISK_EFFECTS) == 12
    assert "普拉达换装" in S.HIGH_IDENTITY_RISK_EFFECTS
    assert "液态金属" in S.HIGH_IDENTITY_RISK_EFFECTS
    assert "产品扫光" not in S.HIGH_IDENTITY_RISK_EFFECTS


def test_directive_high_risk_injects_identity_lock() -> None:
    line, negatives, high_risk = S.signature_effect_directive("普拉达换装 走秀连续切换")
    assert high_risk is True
    assert "普拉达换装" in line
    assert set(S.IDENTITY_LOCK_NEGATIVE_TERMS).issubset(set(negatives))


def test_directive_medium_risk_surfaces_prompt_no_extra_negatives() -> None:
    line, negatives, high_risk = S.signature_effect_directive("本镜子弹时间定格")
    assert high_risk is False
    assert "子弹时间" in line
    assert negatives == []


def test_directive_no_hit_is_noop() -> None:
    line, negatives, high_risk = S.signature_effect_directive("两人对话，固定机位")
    assert line == ""
    assert negatives == []
    assert high_risk is False


def test_normalize_recognizes_by_alias() -> None:
    result = S.normalize_signature_effect("用换脸转场把甲切成乙")
    assert any(e["id"] == "face_morph" for e in result["effects"])
