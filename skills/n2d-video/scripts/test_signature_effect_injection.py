"""prompt_pack 特效镜头主动接入测试：命中即暴露核心 prompt，高风险自动拼身份锁负向词。"""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("prompt_pack.py")
spec = importlib.util.spec_from_file_location("prompt_pack_sig", SCRIPT)
prompt_pack = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(prompt_pack)


def test_high_risk_effect_injects_identity_lock_negatives() -> None:
    line, extra_negatives, high_risk = prompt_pack.signature_effect_directive(
        {"signature_effect": "普拉达换装"}, "模特走秀，服装连续切换"
    )
    assert high_risk is True
    assert "特效镜头" in line and "普拉达换装" in line
    # 该特效自带 negatives + 身份锁词都应并入。
    assert any("identity" in n or "face" in n for n in extra_negatives)
    assert set(prompt_pack.IDENTITY_LOCK_NEGATIVE_TERMS).issubset(set(extra_negatives))


def test_medium_risk_effect_surfaces_prompt_without_extra_negatives() -> None:
    line, extra_negatives, high_risk = prompt_pack.signature_effect_directive(
        {}, "本镜用子弹时间定格腾空瞬间"
    )
    assert high_risk is False
    assert "子弹时间" in line
    assert extra_negatives == []


def test_no_effect_leaves_output_unchanged() -> None:
    line, extra_negatives, high_risk = prompt_pack.signature_effect_directive(
        {}, "两人对话，固定机位"
    )
    assert line == ""
    assert extra_negatives == []
    assert high_risk is False


def test_probe_reads_camera_and_desc_text() -> None:
    # 探针来自运镜/描述文本，而非仅显式字段。
    line, _, _ = prompt_pack.signature_effect_directive({}, "镜头：产品扫光，硬光条斜扫瓶身")
    assert "产品扫光" in line
