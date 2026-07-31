#!/usr/bin/env python3
"""voice_lexicon 纯函数单测。
cd skills/n2d/n2d-voice && python -m pytest test_voice_lexicon.py
"""
import voice_lexicon as vl


LEX = vl.normalize_lexicon({
    "重华": {"pinyin": "chóng huá", "spoken": "虫华", "note": "剑名"},
    "燕王": "烟王",                      # str 简写 = spoken
    "太虚": {"pinyin": "tài xū"},        # 只给拼音、无 spoken → 留待音素后端，不改字面
})


def test_normalize_str_and_dict():
    assert LEX["燕王"]["spoken"] == "烟王"
    assert LEX["燕王"]["pinyin"] == ""
    assert LEX["重华"]["spoken"] == "虫华"
    assert LEX["太虚"]["spoken"] == ""


def test_normalize_drops_empty_term():
    out = vl.normalize_lexicon({"  ": "x", "甲": "乙"})
    assert "甲" in out and len(out) == 1


def test_to_spoken_replaces_homophone():
    assert vl.to_spoken("重华出鞘，燕王退避", LEX) == "虫华出鞘，烟王退避"


def test_to_spoken_skips_pinyin_only():
    # 太虚无 spoken → 字面不变（等音素后端处理）
    assert vl.to_spoken("太虚之境", LEX) == "太虚之境"


def test_to_spoken_longest_first():
    lex = vl.normalize_lexicon({"重": "众", "重华": "虫华"})
    # 「重华」整体替换，不被「重」先吞
    assert vl.to_spoken("重华", lex) == "虫华"


def test_to_spoken_empty_inputs():
    assert vl.to_spoken("", LEX) == ""
    assert vl.to_spoken("无专名", {}) == "无专名"


def test_applied_terms():
    assert set(vl.applied_terms("重华与燕王", LEX)) == {"重华", "燕王"}
    assert vl.applied_terms("太虚", LEX) == []   # 无 spoken 不算纠音


def test_pinyin_hints():
    hints = dict(vl.pinyin_hints("重华太虚", LEX))
    assert hints["重华"] == "chóng huá"
    assert hints["太虚"] == "tài xū"
    assert "燕王" not in hints            # 无 pinyin
