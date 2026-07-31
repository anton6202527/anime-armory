#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_character_arc_audit — 弧线推进机检（Weiland 内构跨章对账）。

Run: cd skills/novel/novel-craft/scripts && python3 -m pytest test_character_arc_audit.py
"""
import json
import os

import character_arc_audit as caa


def _card(chapter, pov="沈砚", **fields):
    base = {"id": f"SC{chapter:03d}-01", "chapter": chapter, "scene_no": 1, "pov": pov}
    base.update(fields)
    return base


# ── want_need_collapsed ──────────────────────────────────────────────────────

def test_want_need_identical_flagged():
    scenes = [_card(1, want="报仇", need="报仇")]
    alerts = caa.want_need_collapsed(scenes)
    assert len(alerts) == 1 and alerts[0]["type"] == "WANT-NEED-COLLAPSED"


def test_want_need_distinct_ok():
    scenes = [_card(1, want="报仇", need="学会放下仇恨")]
    assert caa.want_need_collapsed(scenes) == []


def test_want_need_empty_not_flagged():
    assert caa.want_need_collapsed([_card(1, want="", need="")]) == []


# ── misbelief_no_cost_runs ───────────────────────────────────────────────────

def test_misbelief_without_cost_run_flagged():
    scenes = [_card(c, misbelief="只有力量能保护人") for c in range(1, 8)]
    alerts = caa.misbelief_no_cost_runs(scenes, run_len=6)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "MISBELIEF-NO-COST-RUN"
    assert alerts[0]["entity"] == "沈砚"


def test_misbelief_with_cost_breaks_run():
    scenes = [_card(c, misbelief="只有力量能保护人",
                    choice_cost="为救人暴露身份" if c == 4 else "")
              for c in range(1, 8)]
    assert caa.misbelief_no_cost_runs(scenes, run_len=6) == []


def test_nonconsecutive_chapters_break_run():
    # 章号断档（1-3、7-9）→ 各段都不足 run_len，不报
    scenes = [_card(c, misbelief="谎言") for c in (1, 2, 3, 7, 8, 9)]
    assert caa.misbelief_no_cost_runs(scenes, run_len=6) == []


def test_runs_grouped_by_pov():
    # 两个 POV 各自 3 章无代价 → 各自不够 6 章，不报
    scenes = ([_card(c, pov="沈砚", misbelief="A") for c in range(1, 4)]
              + [_card(c, pov="裴决", misbelief="B") for c in range(1, 4)])
    assert caa.misbelief_no_cost_runs(scenes, run_len=6) == []


# ── engine_decay ─────────────────────────────────────────────────────────────

def test_engine_decay_flagged_when_tail_collapses():
    filled = dict(want="w", need="n", misbelief="m", wound="wd",
                  fear="f", tactic="t", moral_boundary="mb", choice_cost="cc")
    scenes = [_card(c, **filled) for c in range(1, 5)] + [_card(c) for c in range(5, 13)]
    alerts = caa.engine_decay(scenes)
    assert len(alerts) == 1 and alerts[0]["type"] == "ARC-ENGINE-DECAY"


def test_engine_decay_not_flagged_when_consistent():
    filled = dict(want="w", need="n", misbelief="m")
    scenes = [_card(c, **filled) for c in range(1, 13)]
    assert caa.engine_decay(scenes) == []


def test_engine_decay_needs_min_chapters():
    scenes = [_card(1, want="w")] + [_card(2), _card(3)]
    assert caa.engine_decay(scenes) == []


# ── analyze 契约 ─────────────────────────────────────────────────────────────

def _write_cards(root, scenes):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_scene_cards", "scenes": scenes}, f, ensure_ascii=False)


def test_analyze_skips_without_cards(tmp_path):
    res = caa.analyze(str(tmp_path))
    assert res["ran"] is False


def test_analyze_skips_when_engine_never_used(tmp_path):
    # 场景卡存在但人物引擎字段全空 → 优雅跳过（不臆造"弧线停摆"）
    _write_cards(str(tmp_path), [_card(1), _card(2)])
    res = caa.analyze(str(tmp_path))
    assert res["ran"] is False and "从未启用" in res["skipped"]


def test_analyze_contract_blocking_zero(tmp_path):
    scenes = [_card(c, misbelief="谎言") for c in range(1, 8)]
    _write_cards(str(tmp_path), scenes)
    res = caa.analyze(str(tmp_path))
    assert res["ran"] is True
    assert res["blocking"] == 0
    assert res["total"] == len(res["alerts"]) >= 1
    assert all(a["severity"] in ("建议级", "info") for a in res["alerts"])
