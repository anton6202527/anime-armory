#!/usr/bin/env python3
"""Tests for the n2d_text_utils re-export shim over text_utils.

Importing through the shim exercises the backward-compatible re-export path.

Run from this directory:
    cd skills/common && python3 -m pytest test_n2d_text_utils.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Import via the shim so the re-export path is exercised.
from n2d_text_utils import (  # noqa: E402
    cjk_count,
    strip_quotes,
    clean_punctuation,
    is_placeholder,
)


# ── cjk_count ──
def test_cjk_count_mixed_cjk_ascii():
    # 4 CJK chars, ASCII/digits/punct don't count.
    assert cjk_count("你好世界 hello 123!") == 4


def test_cjk_count_empty():
    assert cjk_count("") == 0
    assert cjk_count(None) == 0


def test_cjk_count_pure_ascii():
    assert cjk_count("hello world") == 0


# ── strip_quotes ──
def test_strip_quotes_removes_paired_content():
    out = strip_quotes("他说「你好」然后走了")
    assert "你好" not in out
    assert "他说" in out and "然后走了" in out


def test_strip_quotes_curly_double():
    out = strip_quotes("旁白“引用内容”结束")
    assert "引用内容" not in out
    assert "旁白" in out and "结束" in out


# ── clean_punctuation ──
def test_clean_punctuation_dedups_commas():
    assert clean_punctuation("你好，，世界") == "你好，世界"


def test_clean_punctuation_drops_comma_after_terminal():
    # 。 followed by redundant comma → comma removed
    assert clean_punctuation("结束。，") == "结束。"


def test_clean_punctuation_empty():
    assert clean_punctuation("") == ""
    assert clean_punctuation(None) == ""


# ── is_placeholder ──
def test_is_placeholder_true_cases():
    assert is_placeholder("待精修台词")
    assert is_placeholder("这里是占位")
    assert is_placeholder("placeholder text")
    assert is_placeholder("TODO: fill")
    assert is_placeholder("（待补充")


def test_is_placeholder_false_cases():
    assert not is_placeholder("正式定稿的台词")
    assert not is_placeholder("")
    assert not is_placeholder(None)
