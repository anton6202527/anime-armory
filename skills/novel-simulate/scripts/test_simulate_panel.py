#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for simulate_panel.py — deterministic reader-panel signals.

Run from this directory:
    cd skills/novel-simulate/scripts && python3 -m pytest test_simulate_panel.py
"""
import os
import json
import tempfile

import simulate_panel


def _make_project(chapters):
    """chapters: dict {filename: text}. Returns temp project dir path."""
    root = tempfile.mkdtemp()
    cdir = os.path.join(root, "章节")
    os.makedirs(cdir)
    for name, text in chapters.items():
        with open(os.path.join(cdir, name), "w", encoding="utf-8") as f:
            f.write(text)
    return root


def test_density_basic():
    # 4 CJK chars, keyword "打脸" appears once -> 1 hit / 4 chars * 1000 = 250.0
    d = simulate_panel._density("打脸时刻", ["打脸"])
    assert d == 250.0


def test_density_empty_text_no_crash():
    # _cjk_len 0 -> falls back to 1, no ZeroDivisionError
    assert simulate_panel._density("", ["打脸"]) == 0.0


def test_density_increases_with_more_hits():
    low = simulate_panel._density("逆袭啊啊啊啊啊啊啊啊", ["逆袭"])
    high = simulate_panel._density("逆袭逆袭逆袭逆袭", ["逆袭"])
    assert high > low


def test_lexical_diversity_bounds():
    # All 4-grams identical -> low diversity; varied text -> higher
    repetitive = simulate_panel._lexical_diversity("一二三四" * 10)
    varied = simulate_panel._lexical_diversity(
        "春风又绿江南岸明月何时照我还故人西辞黄鹤楼烟花三月下扬州")
    assert 0.0 <= repetitive <= 1.0
    assert 0.0 <= varied <= 1.0
    assert varied > repetitive


def test_lexical_diversity_no_cjk():
    assert simulate_panel._lexical_diversity("abc def") == 0.0


def test_hook_strength_bounds():
    # No markers -> 0.0
    assert simulate_panel._hook_strength("平淡无奇的句子结束了") == 0.0
    # Many markers in tail -> capped at 1.0
    strong = simulate_panel._hook_strength("正文" + "？但却突然竟然居然不料没想到此时" * 3)
    assert 0.0 <= strong <= 1.0
    assert strong == 1.0


def test_hook_strength_monotonic():
    weak = simulate_panel._hook_strength("结尾很平静地落下了")
    strong = simulate_panel._hook_strength("结尾处突然？竟然不料")
    assert strong > weak


def test_analyze_retention_prior_in_range():
    root = _make_project({
        "第1章.md": "他平静地走过街道，看着远方的天空，心里想着往事。" * 5,
        "第2章.md": "夜色降临，万物归于安宁，没有任何波澜。" * 5,
        "第3章.md": "时间慢慢流逝，一切都很安静。" * 5,
    })
    sig = simulate_panel.analyze(root, "opening", 1, ["rookie", "logic", "emote", "critic"])
    assert sig is not None
    assert 0.0 <= sig["retention_prior"] <= 1.0


def test_analyze_retention_prior_rises_with_shuang_and_hooks():
    bland = _make_project({
        "第1章.md": "他平静地走在路上，看着天空，心里想着往事的种种。" * 6,
        "第2章.md": "夜色降临，万物安宁，没有任何波澜起伏地过去了。" * 6,
        "第3章.md": "时间慢慢流逝，日子一天天过着，安静祥和。" * 6,
    })
    punchy = _make_project({
        "第1章.md": ("他逆袭打脸碾压突破反杀升级翻盘吊打震惊崛起无敌暴击斩杀，"
                     "局势骤然逆转！") * 6 + "突然？竟然不料没想到此时就在猛地",
        "第2章.md": ("再次逆袭打脸碾压突破反杀升级，所有人都被吊打震惊！") * 6
                    + "但却突然竟然居然不料",
        "第3章.md": ("又一轮逆袭打脸碾压突破反杀，无敌暴击斩杀崛起翻盘！") * 6
                    + "原来下一刻骤然猛地此时",
    })
    bland_sig = simulate_panel.analyze(bland, "opening", 1, list(simulate_panel.PERSONAS))
    punchy_sig = simulate_panel.analyze(punchy, "opening", 1, list(simulate_panel.PERSONAS))
    assert punchy_sig["retention_prior"] > bland_sig["retention_prior"]


def test_analyze_returns_none_when_no_chapters():
    root = tempfile.mkdtemp()  # no 章节 dir
    assert simulate_panel.analyze(root, "opening", 1, ["rookie"]) is None


def test_analyze_chapter_scope():
    root = _make_project({
        "第1章.md": "第一章内容逆袭打脸。",
        "第2章.md": "第二章内容碾压突破。",
    })
    sig = simulate_panel.analyze(root, "chapter", 2, ["rookie"])
    assert sig["chapters_read"] == [2]
    assert sig["scope"] == "chapter"


def test_write_report_emits_signals_json():
    root = _make_project({
        "第1章.md": "他逆袭打脸碾压突破反杀。" * 5 + "突然？竟然不料",
        "第2章.md": "再次反杀升级翻盘吊打。" * 5,
        "第3章.md": "崛起无敌暴击斩杀。" * 5,
    })
    personas = list(simulate_panel.PERSONAS)
    sig = simulate_panel.analyze(root, "opening", 1, personas)
    md_path, sig_path = simulate_panel.write_report(root, sig, personas)

    assert os.path.basename(sig_path) == "reader_panel_signals.json"
    assert os.path.exists(sig_path)
    assert os.path.exists(md_path)

    with open(sig_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "cliche_density_per_kchar" in data
    assert "retention_prior" in data
    assert data["analysis_mode"] == "signal_only"
    assert data["signal_only"] is True
    assert data["qualitative_completed"] is False
    assert data["personas_completed"] == []
    assert 0.0 <= data["retention_prior"] <= 1.0
    assert "date" in data
    # personas signals carried through
    for pid in personas:
        assert pid in data["personas"]
        assert "keyword_density_per_kchar" in data["personas"][pid]
