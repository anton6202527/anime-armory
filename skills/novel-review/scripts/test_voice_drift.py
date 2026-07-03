#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_voice_drift.py — voice_drift.py 纯函数单测

跑法：cd skills/novel-review/scripts && python3 -m pytest test_voice_drift.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_drift import (
    extract_dialogue,
    catchphrase_coverage,
    avg_sentence_len,
    voice_drift_band,
)


# ---------- extract_dialogue ----------

def test_extract_dialogue_attribution_hit_before():
    """名字+动词在引号前 → 归属命中。"""
    text = "沈砚冷笑道：「哼，本座说过别惹我。」她转身离去。"
    quotes = extract_dialogue(text, "沈砚")
    assert quotes == ["哼，本座说过别惹我。"]


def test_extract_dialogue_attribution_hit_after():
    """名字+动词在引号后 → 归属命中（另一种语序）。"""
    text = "「哼。」沈砚冷笑了一声。"
    quotes = extract_dialogue(text, "沈砚")
    assert quotes == ["哼。"]


def test_extract_dialogue_non_adjacent_quote_not_attributed():
    """远处一段没有名字+动词邻接的引号，不应被归到该角色（保守，宁缺毋滥）。"""
    text = "沈砚走进大殿，许久之后，远处某人说：「这里好安静。」"
    quotes = extract_dialogue(text, "沈砚")
    # "说"邻接引号，但窗口内并无"沈砚"——不归属。
    assert quotes == []


def test_extract_dialogue_other_speaker_not_grabbed():
    """同段里别人说的话不被算到 name 头上。"""
    text = "林越笑道：「你来啦。」沈砚没有回答。"
    assert extract_dialogue(text, "沈砚") == []
    assert extract_dialogue(text, "林越") == ["你来啦。"]


# ---------- catchphrase_coverage ----------

def test_catchphrase_coverage_counts():
    lines = ["哼，本座说过。", "哼。", "你算什么东西。"]
    cov = catchphrase_coverage(lines, ["哼", "本座", "嘤嘤嘤"])
    assert cov == {"哼": 2, "本座": 1, "嘤嘤嘤": 0}


def test_catchphrase_coverage_tolerant_scalar():
    """catchphrases 容错成标量。"""
    cov = catchphrase_coverage(["哼哼哼"], "哼")
    assert cov == {"哼": 3}


# ---------- avg_sentence_len ----------

def test_avg_sentence_len_basic():
    # "哼" (1) + "本座说过" (4) → (1+4)/2 = 2.5
    assert avg_sentence_len(["哼！本座说过？"]) == 2.5


def test_avg_sentence_len_empty():
    assert avg_sentence_len([]) == 0.0


def test_avg_sentence_len_no_terminator():
    # 无终止标点 → 整体一句
    assert avg_sentence_len(["你好啊"]) == 3.0


# ---------- voice_drift_band ----------

def test_band_dropped_catchphrase_flagged():
    """登记口头禅 0 次出现 + 说够了话 → catchphrase_dropped 建议级。"""
    profile = {"口头禅": ["哼"], "syntax_profile": {"avg_sentence_length": 8}}
    observed = {"name": "沈砚", "line_count": 5,
                "coverage": {"哼": 0}, "avg_len": 8.0}
    alerts = voice_drift_band(profile, observed)
    dropped = [a for a in alerts if a["type"] == "catchphrase_dropped"]
    assert len(dropped) == 1
    a = dropped[0]
    assert a["entity"] == "沈砚"
    assert a["severity"] == "建议级"
    assert a["phrase"] == "哼"
    assert a["auto"] is True


def test_band_present_catchphrase_ok():
    """口头禅有出现 + 句长贴合 → 无 alert。"""
    profile = {"口头禅": ["哼"], "syntax_profile": {"avg_sentence_length": 8}}
    observed = {"name": "沈砚", "line_count": 5,
                "coverage": {"哼": 3}, "avg_len": 8.0}
    assert voice_drift_band(profile, observed) == []


def test_band_too_few_lines_not_flagged():
    """说得太少（< MIN_LINES_FOR_BAND）不下'消失'判断。"""
    profile = {"口头禅": ["哼"]}
    observed = {"name": "沈砚", "line_count": 1, "coverage": {"哼": 0}, "avg_len": 0.0}
    assert voice_drift_band(profile, observed) == []


def test_band_sentence_len_deviation_flagged():
    """句均长大幅偏离登记 band → voice_drift 建议级。"""
    profile = {"syntax_profile": {"avg_sentence_length": 8}}
    observed = {"name": "沈砚", "line_count": 5, "coverage": {}, "avg_len": 30.0}
    alerts = voice_drift_band(profile, observed)
    drift = [a for a in alerts if a["type"] == "voice_drift"]
    assert len(drift) == 1
    assert drift[0]["severity"] == "建议级"


def test_band_textual_sentence_band_tolerant():
    """宽松形：句长用文字档'短' → 映射 8 字 band，观测 30 字判偏移。"""
    profile = {"句长": "短"}
    observed = {"name": "沈砚", "line_count": 5, "coverage": {}, "avg_len": 30.0}
    alerts = voice_drift_band(profile, observed)
    assert any(a["type"] == "voice_drift" for a in alerts)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
