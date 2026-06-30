#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_antagonist_scaling.py — 反派/威胁战力 scaling 检测器单测（纯函数 + analyze 优雅跳过）。

cd skills/novel-wiki/scripts && python3 -m pytest test_antagonist_scaling.py
"""
import json
import os

import antagonist_scaling as A


# ── threat_gap ────────────────────────────────────────────────────────────────

def test_threat_gap_hero_leads():
    # 主角序 5，最强反派序 2 → 领先 3。
    assert A.threat_gap(5, [2, 1, 0]) == 3


def test_threat_gap_uses_strongest_antag():
    # 取 max(在场反派)，不是 min/平均。
    assert A.threat_gap(6, [1, 5, 2]) == 1


def test_threat_gap_ignores_none_entries():
    assert A.threat_gap(4, [None, 1, None]) == 3


def test_threat_gap_none_when_no_antag():
    assert A.threat_gap(5, []) is None
    assert A.threat_gap(5, [None]) is None
    assert A.threat_gap(None, [1]) is None


# ── scaling_band：主角领先 3 tier (> max_lead=2) = warn ───────────────────────

def test_scaling_band_warn_when_hero_far_ahead():
    gap = A.threat_gap(5, [2, 1])          # = 3
    assert A.scaling_band(gap, max_lead=2) == "warn"


def test_scaling_band_ok_at_boundary():
    assert A.scaling_band(2, max_lead=2) == "ok"     # 等于上限不报
    assert A.scaling_band(1, max_lead=2) == "ok"
    assert A.scaling_band(0, max_lead=2) == "ok"
    assert A.scaling_band(-1, max_lead=2) == "ok"    # 反派反超主角，不在此报


def test_scaling_band_none_is_ok():
    assert A.scaling_band(None) == "ok"


# ── antag_spike_band：2-tier 跳 ok，4-tier 跳 warn ───────────────────────────

def test_antag_spike_band_two_tier_ok():
    assert A.antag_spike_band(1, 3, max_jump=2) == "ok"     # 跳 2 = 上限，ok


def test_antag_spike_band_four_tier_warn():
    assert A.antag_spike_band(1, 5, max_jump=2) == "warn"   # 跳 4 > 2 = warn


def test_antag_spike_band_downgrade_not_flagged():
    # 下降不在此报（单调退档由 power_system 管）。
    assert A.antag_spike_band(5, 1, max_jump=2) == "ok"


def test_antag_spike_band_none_is_ok():
    assert A.antag_spike_band(None, 5) == "ok"
    assert A.antag_spike_band(3, None) == "ok"


# ── role 归类 ─────────────────────────────────────────────────────────────────

def test_role_classification():
    assert A.is_protagonist("protagonist")
    assert A.is_protagonist("主角")
    assert A.is_antagonist("antagonist")
    assert A.is_antagonist("反派")
    assert not A.is_antagonist("protagonist")
    assert not A.is_protagonist("反派")


# ── analyze：优雅跳过 ─────────────────────────────────────────────────────────

def test_analyze_skips_when_no_registry(tmp_path):
    res = A.analyze(str(tmp_path))
    assert res["ran"] is False
    assert "power_system_registry" in res["skipped"]


def _write_registry(tmp_path, progression, *, roster=None):
    setting = tmp_path / "设定"
    setting.mkdir(parents=True, exist_ok=True)
    reg = {
        "kind": "novel_power_system_registry",
        "tiers": {"sequence": ["练气", "筑基", "结丹", "元婴", "化神", "炼虚", "合体"]},
        "progression": progression,
    }
    if roster is not None:
        reg["roster"] = roster
    (setting / "power_system_registry.json").write_text(
        json.dumps(reg, ensure_ascii=False), encoding="utf-8")


def test_analyze_skips_when_no_antagonist_tagged(tmp_path):
    # 只有主角被标，没反派 → 优雅跳过（无法推断威胁）。
    _write_registry(tmp_path, [
        {"chapter": 1, "character": "主角", "tier": "练气", "role": "主角"},
        {"chapter": 5, "character": "主角", "tier": "筑基", "role": "主角"},
    ])
    res = A.analyze(str(tmp_path))
    assert res["ran"] is True
    assert res["total"] == 0
    assert "反派" in res["note"]


def test_analyze_flags_threat_underscaled(tmp_path):
    # 主角化神(序4) vs 在场反派练气(序0) → 领先 4 > 2 = 威胁缺位。
    _write_registry(tmp_path, [
        {"chapter": 3, "character": "主角", "tier": "化神", "role": "主角"},
        {"chapter": 3, "character": "杂鱼反派", "tier": "练气", "role": "反派"},
    ])
    res = A.analyze(str(tmp_path))
    assert res["ran"] is True
    types = [a["type"] for a in res["alerts"]]
    assert "threat_underscaled" in types
    assert all(a["severity"] == "建议级" for a in res["alerts"])
    assert res["blocking"] == 0


def test_analyze_flags_antagonist_power_spike(tmp_path):
    # 反派自己 练气(0)→元婴(3)，跳 3 > 2，无代价 → 突兀膨胀。主角同章不碾压（避免叠 threat 报）。
    _write_registry(tmp_path, [
        {"chapter": 1, "character": "宿敌", "tier": "练气", "role": "反派"},
        {"chapter": 2, "character": "宿敌", "tier": "元婴", "role": "反派"},
        {"chapter": 1, "character": "主角", "tier": "练气", "role": "主角"},
        {"chapter": 2, "character": "主角", "tier": "结丹", "role": "主角"},
    ])
    res = A.analyze(str(tmp_path))
    spikes = [a for a in res["alerts"] if a["type"] == "antagonist_power_spike"]
    assert spikes and spikes[0]["entity"] == "宿敌"
    assert spikes[0]["severity"] == "建议级"


def test_analyze_spike_exempt_with_reason(tmp_path):
    # 同样大跳，但快照写了 spike_reason 命中代价词 → 不报暴涨。
    _write_registry(tmp_path, [
        {"chapter": 1, "character": "宿敌", "tier": "练气", "role": "反派"},
        {"chapter": 2, "character": "宿敌", "tier": "元婴", "role": "反派",
         "spike_reason": "献祭全族修为禁术夺舍，代价是寿元尽失"},
        {"chapter": 1, "character": "主角", "tier": "练气", "role": "主角"},
        {"chapter": 2, "character": "主角", "tier": "结丹", "role": "主角"},
    ])
    res = A.analyze(str(tmp_path))
    spikes = [a for a in res["alerts"] if a["type"] == "antagonist_power_spike"]
    assert not spikes


def test_analyze_role_from_roster(tmp_path):
    # role 也可从 registry.roster 推断（快照不带 role）。
    _write_registry(tmp_path, [
        {"chapter": 3, "character": "林凡", "tier": "化神"},
        {"chapter": 3, "character": "黑袍人", "tier": "练气"},
    ], roster=[
        {"character": "林凡", "role": "protagonist"},
        {"character": "黑袍人", "role": "antagonist"},
    ])
    res = A.analyze(str(tmp_path))
    assert "threat_underscaled" in [a["type"] for a in res["alerts"]]


def test_analyze_no_warn_when_well_matched(tmp_path):
    # 反派紧跟主角（领先 ≤ 2，无暴涨）→ 0 报。
    _write_registry(tmp_path, [
        {"chapter": 1, "character": "主角", "tier": "练气", "role": "主角"},
        {"chapter": 1, "character": "宿敌", "tier": "练气", "role": "反派"},
        {"chapter": 5, "character": "主角", "tier": "结丹", "role": "主角"},
        {"chapter": 5, "character": "宿敌", "tier": "筑基", "role": "反派"},
    ])
    res = A.analyze(str(tmp_path))
    assert res["total"] == 0


def test_main_exits_zero_advisory(tmp_path, capsys):
    # advisory：哪怕有报，main 也退 0（不硬挡 post_write）。
    _write_registry(tmp_path, [
        {"chapter": 3, "character": "主角", "tier": "化神", "role": "主角"},
        {"chapter": 3, "character": "杂鱼", "tier": "练气", "role": "反派"},
    ])
    rc = A.main([str(tmp_path)])
    assert rc == 0
    assert os.path.isfile(os.path.join(str(tmp_path), "审稿", "antagonist_findings.json"))
