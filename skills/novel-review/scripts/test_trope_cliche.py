#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import trope_cliche as tc


def test_detect_system_binding_unacknowledged():
    hits = tc.detect("主角一觉醒来，脑海中响起：叮，系统绑定成功，宿主请开始你的表演。", "")
    names = [h["trope"] for h in hits]
    assert "系统绑定开局" in names
    h = next(x for x in hits if x["trope"] == "系统绑定开局")
    assert h["severity"] == "建议级" and h["acknowledged"] is False


def test_acknowledged_when_differentiation_names_it():
    premise = "叮，系统绑定宿主。"
    diff = "差异化决策：本作故意颠覆‘系统绑定开局’——系统是敌人植入的枷锁，每次使用都替反派积累筹码。"
    hits = tc.detect(premise, diff)
    h = next(x for x in hits if x["trope"] == "系统绑定开局")
    assert h["acknowledged"] is True


def test_combo_transmigration_plus_annulment():
    hits = tc.detect("穿越到异世，开局便被未婚夫当众退婚。", "")
    assert any(h["trope"] == "穿越/重生+退婚流" for h in hits)


def test_no_false_positive_on_plain_words():
    # 单独一个「系统」不触发（需 AND 组合），避免噪声
    hits = tc.detect("这个国家的行政系统非常庞大，官员众多。", "")
    assert hits == []


def test_analyze_skips_when_no_premise(tmp_path):
    res = tc.analyze(str(tmp_path))
    assert res["ran"] is False
