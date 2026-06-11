#!/usr/bin/env python3
"""mouth_detect 纯函数单测。从脚本自身目录跑：
    cd skills/n2d-model-router/scripts && python -m pytest test_mouth_detect.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mouth_detect as md  # noqa: E402


def test_parse_prompt_mouth_visible():
    assert md.parse_prompt_mouth_visible("原生音画策略：mouth_visible=yes，risk=low") is True
    assert md.parse_prompt_mouth_visible("mouth_visible = no") is False
    assert md.parse_prompt_mouth_visible("mouth_visible：是") is True
    assert md.parse_prompt_mouth_visible("mouth_visible: 否") is False
    assert md.parse_prompt_mouth_visible("没有这个字段") is None


def test_reconcile_no_image_uses_text():
    r = md.reconcile(text_says=True, image_says=None, prompt_says=None)
    assert r["suggested"] is True and r["suggested_source"] == "text" and r["verdict"] == "ok"


def test_reconcile_image_overrides_text():
    r = md.reconcile(text_says=False, image_says=True, prompt_says=None)
    assert r["suggested"] is True and r["suggested_source"] == "image"
    assert r["verdict"] == "warn"  # 图≠文本启发式 → 提示以图为准


def test_reconcile_image_vs_prompt_conflict_warns():
    r = md.reconcile(text_says=True, image_says=False, prompt_says=True)
    assert r["verdict"] == "warn"
    assert "按图改" in r["message"]
    assert r["suggested"] is False  # 以图为准


def test_reconcile_text_vs_prompt_conflict_when_no_image():
    r = md.reconcile(text_says=True, image_says=None, prompt_says=False)
    assert r["verdict"] == "warn"
    assert r["suggested"] is True  # 无图退回文本端建议


def test_reconcile_all_agree_ok():
    r = md.reconcile(text_says=True, image_says=True, prompt_says=True)
    assert r["verdict"] == "ok" and r["message"] == ""


def test_yn_helper():
    assert md._yn(True) == "yes"
    assert md._yn(False) == "no"
    assert md._yn(None) == "unknown"


def test_detect_mouth_returns_none_without_lib():
    # 系统无 insightface（PEP 668）→ 优雅 None，绝不臆造
    assert md.detect_mouth_in_image("/nonexistent.png") is None
