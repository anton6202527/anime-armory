#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_timeline_check.py — timeline_check 单测

cd skills/novel-wiki/scripts && python3 -m pytest test_timeline_check.py
"""
import timeline_check as tc


# ---- season_rank ----

def test_season_rank_basic():
    assert tc.season_rank("春") == 0
    assert tc.season_rank("夏") == 1
    assert tc.season_rank("秋") == 2
    assert tc.season_rank("冬") == 3
    assert tc.season_rank("腊") is None
    assert tc.season_rank("") is None


# ---- parse_time_markers ----

def test_parse_abs_year():
    mks = tc.parse_time_markers("第三年春，他登基；庆元七年又改元。")
    years = [m for m in mks if m["kind"] == "abs_year"]
    vals = {m["value"] for m in years}
    assert 3 in vals and 7 in vals
    assert all(m["comparable"] for m in years)


def test_parse_relative_not_comparable():
    mks = tc.parse_time_markers("三天后他回城，次日又出发，数月后才归。")
    rel = [m for m in mks if m["kind"] == "rel_fwd"]
    assert rel, "应抽到相对跳转标记"
    assert all(m["comparable"] is False for m in rel)
    # "三天后" 不应被当成绝对纪年 三年
    assert not any(m["kind"] == "abs_year" and m["value"] == 3 for m in mks)


def test_parse_season_marker():
    mks = tc.parse_time_markers("寒冬已至，万物萧瑟。")
    seasons = [m for m in mks if m["kind"] == "season"]
    assert any(m["value"] == 3 for m in seasons)
    assert all(m["comparable"] for m in seasons)


def test_markers_sorted_by_pos():
    mks = tc.parse_time_markers("第五年……第二年")
    assert mks == sorted(mks, key=lambda m: m["pos"])


# ---- timeline_conflict ----

def test_conflict_year_decreasing():
    prev = {"kind": "abs_year", "value": 7, "comparable": True}
    cur = {"kind": "abs_year", "value": 3, "comparable": True}
    ok, reason = tc.timeline_conflict(prev, cur)
    assert ok is True and reason


def test_no_conflict_year_increasing():
    prev = {"kind": "abs_year", "value": 3, "comparable": True}
    cur = {"kind": "abs_year", "value": 7, "comparable": True}
    ok, _ = tc.timeline_conflict(prev, cur)
    assert ok is False


def test_conflict_season_backward():
    prev = {"kind": "season", "value": 3, "comparable": True}  # 冬
    cur = {"kind": "season", "value": 0, "comparable": True}   # 春
    ok, reason = tc.timeline_conflict(prev, cur)
    assert ok is True and reason


def test_ambiguous_relative_no_conflict():
    # 相对跳转不可比较 → 永不判倒流
    prev = {"kind": "rel_fwd", "value": None, "comparable": False}
    cur = {"kind": "abs_year", "value": 1, "comparable": True}
    assert tc.timeline_conflict(prev, cur)[0] is False
    cur2 = {"kind": "rel_fwd", "value": None, "comparable": False}
    assert tc.timeline_conflict(cur, cur2)[0] is False


def test_cross_kind_no_conflict():
    prev = {"kind": "abs_year", "value": 5, "comparable": True}
    cur = {"kind": "season", "value": 0, "comparable": True}
    assert tc.timeline_conflict(prev, cur)[0] is False


# ---- analyze: backward across chapters + flashback exemption ----

def _mk_project(tmp_path, chapters):
    proj = tmp_path / "书"
    (proj / "章节").mkdir(parents=True)
    for i, body in enumerate(chapters, start=1):
        (proj / "章节" / f"第{i:02d}章.md").write_text(body, encoding="utf-8")
    return str(proj)


def test_analyze_backward_alert(tmp_path):
    proj = _mk_project(tmp_path, [
        "庆元七年，新政推行天下。",
        "庆元三年，他还只是个稚子。",   # 倒流，且无闪回
    ])
    alerts = tc.analyze(proj)["alerts"]
    back = [a for a in alerts if a["type"] == "timeline_backward"]
    assert len(back) == 1
    assert back[0]["severity"] == "建议级"
    assert back[0]["chapter"] == 2


def test_analyze_backward_exempt_by_flashback(tmp_path):
    proj = _mk_project(tmp_path, [
        "庆元七年，新政推行天下。",
        "他回忆起庆元三年那段稚子岁月。",  # 倒流但邻近有闪回语境 → 豁免
    ])
    alerts = tc.analyze(proj)["alerts"]
    assert not [a for a in alerts if a["type"] == "timeline_backward"]


def test_analyze_forward_no_alert(tmp_path):
    proj = _mk_project(tmp_path, [
        "庆元三年，他初入朝堂。",
        "庆元七年，他已位极人臣。",   # 递增，正常
    ])
    alerts = tc.analyze(proj)["alerts"]
    assert not [a for a in alerts if a["type"] == "timeline_backward"]


def test_analyze_relative_only_no_alert(tmp_path):
    # 全是相对跳转 → 不可比较 → 不报倒流（宁缺毋滥）
    proj = _mk_project(tmp_path, [
        "三天后他回城。",
        "次日又匆匆离去。",
    ])
    alerts = tc.analyze(proj)["alerts"]
    assert not [a for a in alerts if a["type"] == "timeline_backward"]


# ---- ledger out-of-order (阻断级) ----

def test_ledger_out_of_order_blocking():
    ledger = {"events": [
        {"name": "登基", "chapter": 5, "order": 1},
        {"name": "驾崩", "chapter": 2, "order": 2},  # order 更大却在更早的章 → 乱序
    ]}
    chapter_of_event = {"登基": 5, "驾崩": 2}
    alerts = tc.check_ledger_order(ledger, chapter_of_event)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "timeline_event_disorder"
    assert alerts[0]["severity"] == "阻断级"


def test_ledger_in_order_no_alert():
    ledger = {"events": [
        {"name": "登基", "chapter": 2, "order": 1},
        {"name": "驾崩", "chapter": 5, "order": 2},
    ]}
    chapter_of_event = {"登基": 2, "驾崩": 5}
    assert tc.check_ledger_order(ledger, chapter_of_event) == []


def test_analyze_runs_ledger_when_present(tmp_path):
    proj = _mk_project(tmp_path, ["平淡的一章，无时间标记。"])
    ledger = {"events": [
        {"name": "A", "chapter": 9, "order": 1},
        {"name": "B", "chapter": 3, "order": 2},
    ]}
    alerts = tc.analyze(proj, ledger=ledger)["alerts"]
    assert any(a["type"] == "timeline_event_disorder" and a["severity"] == "阻断级"
               for a in alerts)


def test_analyze_graceful_without_ledger(tmp_path):
    proj = _mk_project(tmp_path, ["平淡的一章，无时间标记。"])
    # 无台账 + 无可比较标记 → 干净跳过
    assert tc.analyze(proj, ledger=None)["alerts"] == []
