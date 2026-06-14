# -*- coding: utf-8 -*-
"""Tests for foreshadow_ledger.py — 伏笔台账确定性部分（超期判定 + 回收率）。

Run from this directory:
    cd skills/novel-wiki/scripts && python3 -m pytest test_foreshadow_ledger.py
"""
import os
import json

import foreshadow_ledger as fl


# ── plant / payoff / drop 状态机 + JSON 完整性 ─────────────────────────────────
def test_plant_assigns_id_and_pending():
    data = {"kind": fl.KIND, "seeds": []}
    seed = fl.plant(data, "沈念捡到半块断剑", planted_chapter=5, expected_payoff_chapter=50)
    assert seed["id"] == "SEED_001"
    assert seed["status"] == "pending"
    assert seed["planted_chapter"] == 5
    assert seed["expected_payoff_chapter"] == 50
    assert seed["actual_payoff_chapter"] is None


def test_plant_auto_id_avoids_collision():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "a", 1, 10, seed_id="SEED_001")
    fl.plant(data, "b", 2, 12)  # auto -> should not collide
    ids = [s["id"] for s in data["seeds"]]
    assert ids == ["SEED_001", "SEED_002"]


def test_plant_rejects_duplicate_id():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "a", 1, 10, seed_id="SEED_001")
    try:
        fl.plant(data, "b", 2, 12, seed_id="SEED_001")
        assert False, "expected duplicate id to raise"
    except ValueError:
        pass


def test_plant_rejects_bad_importance():
    data = {"kind": fl.KIND, "seeds": []}
    try:
        fl.plant(data, "a", 1, 10, importance="超级重要")
        assert False
    except ValueError:
        pass


def test_payoff_sets_resolved_with_chapter_and_evidence():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "断剑", 5, 50, seed_id="SEED_001")
    seed = fl.payoff(data, "SEED_001", actual_payoff_chapter=48, evidence="断剑认主")
    assert seed["status"] == "resolved"
    assert seed["actual_payoff_chapter"] == 48
    assert seed["evidence"] == "断剑认主"


def test_payoff_partial():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "断剑", 5, 50, seed_id="SEED_001")
    seed = fl.payoff(data, "SEED_001", partial=True)
    assert seed["status"] == "partially_resolved"


def test_payoff_unknown_id_raises():
    data = {"kind": fl.KIND, "seeds": []}
    try:
        fl.payoff(data, "SEED_999")
        assert False
    except KeyError:
        pass


def test_drop_marks_dropped():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "废线索", 3, 20, seed_id="SEED_001")
    seed = fl.drop(data, "SEED_001", reason="作者弃用")
    assert seed["status"] == "dropped"
    assert seed["evidence"] == "作者弃用"


# ── 超期判定（确定性核心） ──────────────────────────────────────────────────────
def test_overdue_true_past_expected_plus_grace():
    seed = {"status": "pending", "expected_payoff_chapter": 50}
    # grace 默认 5 -> 章 56 才算超期，55 不算
    assert fl.is_overdue(seed, through_chapter=56, grace=5) is True
    assert fl.is_overdue(seed, through_chapter=55, grace=5) is False


def test_overdue_false_when_resolved():
    seed = {"status": "resolved", "expected_payoff_chapter": 10}
    assert fl.is_overdue(seed, through_chapter=100) is False


def test_overdue_false_without_expected_chapter():
    # 没有预期回收章 -> 脚本不臆测，绝不机检超期
    seed = {"status": "pending", "expected_payoff_chapter": None}
    assert fl.is_overdue(seed, through_chapter=999) is False


def test_partially_resolved_can_be_overdue():
    seed = {"status": "partially_resolved", "expected_payoff_chapter": 20}
    assert fl.is_overdue(seed, through_chapter=30, grace=5) is True


# ── 回收率（确定性核心） ────────────────────────────────────────────────────────
def test_payoff_rate_basic():
    seeds = [
        {"status": "resolved"},
        {"status": "resolved"},
        {"status": "pending"},
        {"status": "pending"},
    ]
    r = fl.payoff_rate(seeds)
    assert r["rate"] == 0.5  # 2 resolved / 4 effective
    assert r["effective_total"] == 4
    assert r["resolved"] == 2


def test_payoff_rate_dropped_excluded_from_denominator():
    seeds = [
        {"status": "resolved"},
        {"status": "pending"},
        {"status": "dropped"},  # 不进分母
    ]
    r = fl.payoff_rate(seeds)
    assert r["rate"] == 0.5  # 1 / 2 effective, dropped excluded
    assert r["dropped"] == 1
    assert r["effective_total"] == 2


def test_payoff_rate_partial_counts_half():
    seeds = [{"status": "resolved"}, {"status": "partially_resolved"}]
    r = fl.payoff_rate(seeds)
    assert r["rate"] == 0.75  # (1 + 0.5) / 2


def test_payoff_rate_none_when_no_effective():
    assert fl.payoff_rate([])["rate"] is None
    assert fl.payoff_rate([{"status": "dropped"}])["rate"] is None  # 全作废 -> 不谎报 0/0


# ── scan 聚合 + 严重度分级 ─────────────────────────────────────────────────────
def test_scan_flags_high_importance_overdue_as_blocking():
    data = {"kind": fl.KIND, "seeds": [
        {"id": "SEED_001", "description": "关键身世", "status": "pending",
         "planted_chapter": 5, "expected_payoff_chapter": 30, "importance": "critical"},
        {"id": "SEED_002", "description": "小道具", "status": "pending",
         "planted_chapter": 6, "expected_payoff_chapter": 30, "importance": "low"},
    ]}
    report = fl.scan(data, through_chapter=40, grace=5)
    assert report["overdue_count"] == 2
    assert report["blocking"] == 1  # only critical is 阻断级
    sev = {o["id"]: o["severity"] for o in report["overdue"]}
    assert sev["SEED_001"] == "阻断级"
    assert sev["SEED_002"] == "建议级"


def test_scan_no_overdue_within_window():
    data = {"kind": fl.KIND, "seeds": [
        {"id": "SEED_001", "description": "x", "status": "pending",
         "planted_chapter": 5, "expected_payoff_chapter": 50, "importance": "high"},
    ]}
    report = fl.scan(data, through_chapter=52, grace=5)
    assert report["overdue_count"] == 0


# ── round-trip 落盘 ───────────────────────────────────────────────────────────
def test_load_save_roundtrip(tmp_path):
    proj = tmp_path / "书"
    (proj / "设定").mkdir(parents=True)
    data = fl.load_ledger(str(proj))
    fl.plant(data, "断剑", 5, 50)
    fl.save_ledger(str(proj), data)
    path = os.path.join(str(proj), "设定", "foreshadowing_ledger.json")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        reloaded = json.load(f)
    assert reloaded["kind"] == fl.KIND
    assert reloaded["seeds"][0]["id"] == "SEED_001"
