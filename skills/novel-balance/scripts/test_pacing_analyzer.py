#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_pacing_analyzer.py — 从脚本自身目录运行：
    cd skills/novel-balance/scripts && python -m pytest test_pacing_analyzer.py
"""
import json
import os
import tempfile

import pacing_analyzer as pa


def _mk_project(chapters):
    """chapters: dict{int: text} → 临时作品根。"""
    root = tempfile.mkdtemp()
    cdir = os.path.join(root, "章节")
    os.makedirs(cdir)
    for n, text in chapters.items():
        with open(os.path.join(cdir, f"第{n:02d}章_x.md"), "w", encoding="utf-8") as f:
            f.write(text)
    return root


def test_scale_endpoints_and_middle():
    assert pa._scale(0, 0, 12) == 1
    assert pa._scale(12, 0, 12) == 10
    assert pa._scale(-5, 0, 12) == 1      # below lo clamps
    assert pa._scale(99, 0, 12) == 10     # above hi clamps
    mid = pa._scale(6, 0, 12)
    assert 5 <= mid <= 6                  # halfway → ~5.5 rounded


def test_density_per_kchar():
    # 9 个汉字里 "杀" 出现 2 次 → 2/9*1000
    assert pa._density("杀杀人对峙刀光剑影", ["杀"]) == round(2 / 9 * 1000, 2)


def test_parse_range():
    assert pa.parse_range("3-8") == (3, 8)
    assert pa.parse_range("12") == (12, 12)
    assert pa.parse_range(None) is None


def test_range_filters_chapters():
    root = _mk_project({1: "平淡的一天" * 50, 5: "战斗" * 50, 9: "日常" * 50})
    rows = pa.analyze(root, (5, 9))
    nums = sorted(r["chapter"] for r in rows)
    assert nums == [5, 9]


def test_high_conflict_chapter_scores_higher_than_calm():
    calm = "她安静地坐在窗边喝着一杯温茶看着庭院里的花慢慢开放心里一片宁静" * 20
    fight = "突然他猛地拔剑一刀斩杀冲来的敌人鲜血四溅怒吼着反杀破开重围" * 20
    root = _mk_project({1: calm, 2: fight})
    rows = {r["chapter"]: r for r in pa.analyze(root, None)}
    assert rows[2]["conflict_score"] > rows[1]["conflict_score"]


def test_consecutive_watering_flagged():
    calm = "他平静地走着想着一些琐碎的小事没有任何波澜日子就这样过去了" * 30
    rows = [{"chapter": i, "conflict_score": 2, "info_score": 1, "payoff_score": 1}
            for i in range(1, 7)]
    pa.flag_rows(rows)
    # 第5、6章应进入连续注水段判定
    assert any("注水段" in r["verdict"] for r in rows[4:])


def test_writes_both_artifacts():
    root = _mk_project({1: "战斗厮杀" * 40, 2: "日常对话" * 40})
    rows = pa.flag_rows(pa.analyze(root, None))
    md_path, sig_path = pa.write_report(root, rows)
    assert os.path.exists(md_path) and os.path.exists(sig_path)
    data = json.load(open(sig_path, encoding="utf-8"))
    assert data["kind"] == "novel_pacing_signals"
    assert len(data["chapters"]) == 2
    assert "冲突强度" in open(md_path, encoding="utf-8").read()
