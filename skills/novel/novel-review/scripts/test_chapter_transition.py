# -*- coding: utf-8 -*-
"""test_chapter_transition — 章首承接机检。

Run: cd skills/novel/novel-review/scripts && python3 -m pytest test_chapter_transition.py
"""
import os

import chapter_transition as ct

ROSTER = {"沈砚", "裴决", "周衡"}


# ── 纯函数 ──────────────────────────────────────────────────────────────────

def test_marker_exempts_everything():
    v, _ = ct.judge_boundary("沈砚握紧了刀。", "与此同时，千里之外的周衡正在喝茶。", ROSTER)
    assert v == "ok"   # 换线标记=有意转场，即便人物零交集也豁免


def test_abrupt_when_no_marker_and_disjoint_characters():
    v, detail = ct.judge_boundary("沈砚握紧了刀，刀光袭来。", "周衡放下茶盏，看着窗外。", ROSTER)
    assert v == "abrupt"
    assert "沈砚" in detail and "周衡" in detail


def test_ok_when_characters_overlap():
    v, _ = ct.judge_boundary("沈砚握紧了刀。", "沈砚的刀最终没有落下。", ROSTER)
    assert v == "ok"


def test_orphan_when_no_known_character():
    v, _ = ct.judge_boundary("沈砚握紧了刀。", "细雨落在青石板上，远处更声隐约。", ROSTER)
    assert v == "orphan"


def test_time_marker_exempts():
    v, _ = ct.judge_boundary("沈砚握紧了刀。", "翌日清晨，周衡登门。", ROSTER)
    assert v == "ok"


# ── analyze() 集成 ──────────────────────────────────────────────────────────

def _project(tmp_path, chapters, card="## 沈砚\n## 周衡\n"):
    os.makedirs(os.path.join(str(tmp_path), "设定"), exist_ok=True)
    with open(os.path.join(str(tmp_path), "设定", "角色卡.md"), "w", encoding="utf-8") as f:
        f.write(card)
    d = os.path.join(str(tmp_path), "章节")
    os.makedirs(d, exist_ok=True)
    for i, t in enumerate(chapters, 1):
        with open(os.path.join(d, f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(t)


def test_analyze_flags_abrupt_and_is_advisory(tmp_path):
    _project(tmp_path, [
        "沈砚一路追查，夜里握紧了刀。",
        "周衡放下茶盏，慢条斯理地看着窗外。",     # 无标记、人物零交集 → abrupt
    ])
    res = ct.analyze(str(tmp_path))
    assert res["ran"] is True and res["blocking"] == 0
    assert any(a["type"] == "abrupt_chapter_transition" for a in res["alerts"])


def test_analyze_skips_without_roster(tmp_path):
    _project(tmp_path, ["甲走了。", "乙来了。"], card="（空）\n")
    res = ct.analyze(str(tmp_path))
    assert res["ran"] is False and "名册" in res["skipped"]


def test_analyze_marker_clean(tmp_path):
    _project(tmp_path, [
        "沈砚一路追查，夜里握紧了刀。",
        "与此同时，周衡放下了茶盏。",
    ])
    res = ct.analyze(str(tmp_path))
    assert res["ran"] is True and res["alerts"] == []
