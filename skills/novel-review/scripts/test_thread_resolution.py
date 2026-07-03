#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_thread_resolution.py — thread_resolution 纯函数单测

cd skills/novel-review/scripts && python3 -m pytest test_thread_resolution.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thread_resolution import (
    overdue_threads,
    unresolved_at_finale,
    analyze,
    _opened_chapter,
    _thread_id,
)


# ---------- overdue_threads ----------

def test_overdue_thread_open_40_chapters_warns():
    threads = [{"id": "复仇线", "opened_chapter": 5}]
    alerts = overdue_threads(threads, current_chapter=45, max_open_span=30)
    assert len(alerts) == 1
    a = alerts[0]
    assert a["type"] == "subplot_stale"
    assert a["severity"] == "建议级"
    assert a["span"] == 40
    assert a["opened_chapter"] == 5
    assert a["auto"] is True
    assert a["entity"] == "复仇线"


def test_overdue_thread_open_10_chapters_ok():
    threads = [{"id": "短支线", "opened_chapter": 35}]
    assert overdue_threads(threads, current_chapter=45, max_open_span=30) == []


def test_overdue_exactly_at_span_not_reported():
    # span == max_open_span 不报（严格 >）
    threads = [{"id": "线", "opened_chapter": 10}]
    assert overdue_threads(threads, current_chapter=40, max_open_span=30) == []


def test_overdue_missing_opened_chapter_skipped():
    threads = [{"id": "无章号线", "description": "某条没记开启章的支线"}]
    assert overdue_threads(threads, current_chapter=100, max_open_span=30) == []


def test_overdue_real_ledger_shape_uses_chapter_field():
    # reconcile_ledger 真实形状：{"chapter": N, "thread": "..."}
    threads = [{"chapter": 2, "thread": "失踪的妹妹"}]
    alerts = overdue_threads(threads, current_chapter=50, max_open_span=30)
    assert len(alerts) == 1
    assert alerts[0]["opened_chapter"] == 2
    assert alerts[0]["entity"] == "失踪的妹妹"


def test_overdue_none_current_chapter_returns_empty():
    threads = [{"id": "线", "opened_chapter": 5}]
    assert overdue_threads(threads, current_chapter=None) == []


def test_overdue_empty_input():
    assert overdue_threads([], current_chapter=50) == []
    assert overdue_threads(None, current_chapter=50) == []


# ---------- unresolved_at_finale ----------

def test_unresolved_at_finale_blocks():
    threads = [{"id": "复仇线", "opened_chapter": 5},
               {"chapter": 12, "thread": "身世之谜"}]
    alerts = unresolved_at_finale(threads, is_finale=True)
    assert len(alerts) == 2
    for a in alerts:
        assert a["type"] == "subplot_unresolved_at_finale"
        assert a["severity"] == "阻断级"
        assert a["auto"] is True
    assert alerts[0]["opened_chapter"] == 5


def test_not_finale_returns_empty():
    threads = [{"id": "复仇线", "opened_chapter": 5}]
    assert unresolved_at_finale(threads, is_finale=False) == []


def test_finale_no_open_threads_empty():
    assert unresolved_at_finale([], is_finale=True) == []


def test_finale_missing_opened_chapter_still_blocks():
    threads = [{"id": "无章号线"}]
    alerts = unresolved_at_finale(threads, is_finale=True)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "阻断级"
    assert "opened_chapter" not in alerts[0]  # 缺字段时不臆造


# ---------- helpers ----------

def test_opened_chapter_field_tolerance():
    assert _opened_chapter({"opened_chapter": 7}) == 7
    assert _opened_chapter({"chapter": 3}) == 3
    assert _opened_chapter({"opened_at": "9"}) == 9
    assert _opened_chapter({"description": "x"}) is None
    assert _opened_chapter("not a dict") is None


def test_thread_id_tolerance():
    assert _thread_id({"id": "A"}) == "A"
    assert _thread_id({"thread": "B"}) == "B"
    assert _thread_id({"description": "C"}) == "C"
    assert _thread_id({}) == "thread"
    assert _thread_id("plain") == "plain"


# ---------- analyze (graceful skip) ----------

def test_analyze_missing_ledger_graceful(tmp_path):
    res = analyze(str(tmp_path))
    assert res["alerts"] == []
    assert res["open"] == 0
    assert "note" in res


def test_analyze_with_ledger(tmp_path):
    import json
    review_dir = tmp_path / "审稿"
    review_dir.mkdir()
    ledger = {
        "open_threads": [{"chapter": 2, "thread": "失踪的妹妹"}],
        "resolved_threads": [{"chapter": 8, "thread": "初遇反派"}],
    }
    (review_dir / "state_ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False), encoding="utf-8")

    # 普通模式：span 触发建议级
    res = analyze(str(tmp_path), current_chapter=50, finale=False, max_open_span=30)
    assert res["open"] == 1
    assert res["resolved"] == 1
    assert any(a["type"] == "subplot_stale" for a in res["alerts"])
    assert all(a["severity"] != "阻断级" for a in res["alerts"])

    # finale 模式：仍挂支线升阻断级
    res2 = analyze(str(tmp_path), current_chapter=50, finale=True, max_open_span=30)
    assert any(a["type"] == "subplot_unresolved_at_finale"
               and a["severity"] == "阻断级" for a in res2["alerts"])


def test_analyze_empty_open_threads(tmp_path):
    import json
    review_dir = tmp_path / "审稿"
    review_dir.mkdir()
    (review_dir / "state_ledger.json").write_text(
        json.dumps({"open_threads": [], "resolved_threads": [{"chapter": 1, "thread": "x"}]},
                   ensure_ascii=False), encoding="utf-8")
    res = analyze(str(tmp_path), finale=True)
    assert res["alerts"] == []
    assert res["resolved"] == 1
    assert "note" in res


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
