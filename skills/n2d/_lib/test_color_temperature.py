#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""色温数值化体检单元测试。

cd skills/n2d/_lib && python -m pytest test_color_temperature.py
"""
from n2d_logic import parse_kelvin_values, kelvin_warmth, color_temperature_findings


def test_parse_kelvin_basic():
    assert parse_kelvin_values("3000K 暖宫灯") == [3000]
    assert parse_kelvin_values("5600K 冷月主光，3200K 暖轮廓光") == [5600, 3200]


def test_parse_kelvin_ignores_resolution_and_strength():
    assert parse_kelvin_values("4K 画质 0.5x 推近") == []  # 4K=1位不匹配


def test_kelvin_warmth_bands():
    assert kelvin_warmth(3000) == "warm"
    assert kelvin_warmth(5600) == "cool"
    assert kelvin_warmth(4800) == "neutral"


def test_consistent_no_findings():
    assert color_temperature_findings("3000K 暖宫灯主光") == []
    assert color_temperature_findings("5600K 冷月主光") == []


def test_contradiction_warm_kelvin_cool_word():
    codes = [f["code"] for f in color_temperature_findings("3000K 冷调主光")]
    assert "kelvin_warmcool_contradiction" in codes


def test_contradiction_cool_kelvin_warm_word():
    codes = [f["code"] for f in color_temperature_findings("6500K 暖色主光")]
    assert "kelvin_warmcool_contradiction" in codes


def test_mixed_lighting_not_flagged():
    # 主光冷 + 轮廓暖 是合法混合布光，两个色温值 → 不判矛盾
    assert color_temperature_findings("5600K 冷月主光，3200K 暖色轮廓光") == []


def test_implausible_kelvin():
    codes = [f["code"] for f in color_temperature_findings("300000K 主光")]
    assert "kelvin_implausible" in codes
