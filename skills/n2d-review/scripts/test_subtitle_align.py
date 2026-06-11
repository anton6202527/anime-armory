#!/usr/bin/env python3
"""subtitle_align 纯函数单测。从脚本自身目录跑：
    cd skills/n2d-review/scripts && python -m pytest test_subtitle_align.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subtitle_align as sa  # noqa: E402


def test_contains_cjk():
    assert sa.contains_cjk("你好 world")
    assert not sa.contains_cjk("hello world")
    assert not sa.contains_cjk("")


def test_char_len_strips_whitespace():
    assert sa.zh_char_len("你好，世界") == 5
    assert sa.zh_char_len("你 好\n世界") == 4
    assert sa.en_char_len("  hello   world  ") == len("hello world")


def test_count_sentences():
    assert sa.count_sentences("") == 0
    assert sa.count_sentences("你好世界") == 1          # 无终止符 → 残句记 1
    assert sa.count_sentences("你好。世界。") == 2
    assert sa.count_sentences("你好。世界") == 2         # 末尾残句
    assert sa.count_sentences("Wait... really?") == 2   # 连续 ... 算一句边界
    assert sa.count_sentences("Go!") == 1


def test_reading_cps():
    assert sa.reading_cps(18, 2.0) == 9.0
    assert sa.reading_cps(10, 0) is None
    assert sa.reading_cps(0, 2.0) is None


def test_ratio_band_needs_samples():
    assert sa.ratio_band([1.0, 2.0]) is None            # < RATIO_MIN_SAMPLES
    band = sa.ratio_band([1.0, 1.0, 1.0, 1.0, 1.0])
    assert band is not None
    lo, mid, hi = band
    assert mid == 1.0 and lo < 1.0 < hi


def test_pair_verdict_untranslated_is_block():
    rows = sa.pair_verdict("你笑什么", "你笑什么", 3.0, None)
    assert any(r["verdict"] == "block" and r["dim"] == "漏译" for r in rows)


def test_pair_verdict_missing_translation_block_short_circuits():
    rows = sa.pair_verdict("你好", "", 3.0, None)
    assert len(rows) == 1 and rows[0]["verdict"] == "block"


def test_pair_verdict_sentence_granularity_mismatch():
    rows = sa.pair_verdict("我来了。你走吧。", "I'm here.", 4.0, None)
    assert any(r["dim"] == "断句" and r["verdict"] == "warn" for r in rows)


def test_pair_verdict_clean_pair_no_findings():
    rows = sa.pair_verdict("我喜欢你", "I like you", 3.0, None)
    assert rows == []


def test_pair_verdict_reading_speed_too_fast():
    # 20 中文字 / 1 秒 = 20 cps >> 9
    rows = sa.pair_verdict("一二三四五六七八九十一二三四五六七八九十", "x", 1.0, None)
    assert any(r["dim"] == "阅读速度" and r["verdict"] == "warn" for r in rows)


def test_pair_verdict_length_ratio_outlier():
    band = (0.8, 1.5, 3.0)
    # zh 4 字, en 40 字符 → ratio 10 >> hi 3.0
    rows = sa.pair_verdict("短短短短", "x" * 40, 8.0, band)
    assert any(r["dim"] == "长度比" and r["verdict"] == "warn" for r in rows)
