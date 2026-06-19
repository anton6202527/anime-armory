#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for power_system.py — run from skills/novel-wiki/scripts/.

    cd skills/novel-wiki/scripts && python3 -m pytest test_power_system.py
"""
import json
import os

import power_system as ps


# ── detect_genre ──

def test_detect_genre_system_flow():
    text = "他绑定了系统，面板显示属性栏，宿主等级升级，签到领积分，技能点兑换"
    r = ps.detect_genre(text)
    assert r["genre"] == "系统流"
    assert r["hits"] >= ps.GENRE_MIN_HITS


def test_detect_genre_below_threshold():
    assert ps.detect_genre("今天去公司上班喝咖啡")["genre"] is None


def test_genre_needs_power_check():
    assert ps.genre_needs_power_check("系统流") is True
    assert ps.genre_needs_power_check("修仙") is True
    assert ps.genre_needs_power_check("言情") is False


# ── tier_rank ──

def test_tier_rank_realm_with_subtier():
    seq = ["练气", "筑基", "结丹"]
    sub = ["初期", "中期", "后期", "大圆满"]
    assert ps.tier_rank("练气初期", seq, sub) == 0
    assert ps.tier_rank("练气大圆满", seq, sub) == 3
    assert ps.tier_rank("筑基初期", seq, sub) == 4
    assert ps.tier_rank("结丹中期", seq, sub) == 9
    assert ps.tier_rank("化神", seq, sub) is None   # 不在序列


# ── validate_progression ──

def test_progression_ok():
    prog = [
        {"chapter": 1, "character": "主角", "tier": "练气初期", "level": 1, "战力": 10},
        {"chapter": 5, "character": "主角", "tier": "练气后期", "level": 5, "战力": 45},
        {"chapter": 9, "character": "主角", "tier": "筑基初期", "level": 9, "战力": 120},
    ]
    tiers = {"sequence": ["练气", "筑基", "结丹"], "subtiers": ["初期", "中期", "后期", "大圆满"]}
    assert ps.validate_progression(prog, tiers) == []


def test_progression_tier_regress_blocks():
    prog = [
        {"chapter": 5, "character": "主角", "tier": "筑基初期"},
        {"chapter": 8, "character": "主角", "tier": "练气后期"},  # 退档
    ]
    tiers = {"sequence": ["练气", "筑基"], "subtiers": ["初期", "中期", "后期", "大圆满"]}
    alerts = ps.validate_progression(prog, tiers)
    assert any(a["type"] == "power_tier_regress" and a["severity"] == "阻断级" for a in alerts)


def test_progression_regress_exempt_by_reason():
    prog = [
        {"chapter": 5, "character": "主角", "tier": "筑基初期", "战力": 100},
        {"chapter": 8, "character": "主角", "tier": "练气后期", "战力": 20, "regress_reason": "渡劫失败被废修散功"},
    ]
    tiers = {"sequence": ["练气", "筑基"], "subtiers": ["初期", "中期", "后期", "大圆满"]}
    assert ps.validate_progression(prog, tiers) == []


def test_progression_level_and_combat_regress():
    prog = [
        {"chapter": 1, "character": "主角", "level": 10, "战力": 100},
        {"chapter": 3, "character": "主角", "level": 7, "战力": 60},
    ]
    alerts = ps.validate_progression(prog, {})
    types = {a["type"] for a in alerts}
    assert "power_level_regress" in types
    assert "power_combat_regress" in types


def test_progression_unknown_tier_blocks():
    prog = [{"chapter": 2, "character": "主角", "tier": "斗皇"}]
    tiers = {"sequence": ["练气", "筑基"], "subtiers": ["初期"]}
    alerts = ps.validate_progression(prog, tiers)
    assert any(a["type"] == "power_unknown_tier" and a["severity"] == "阻断级" for a in alerts)


def test_progression_advisory_demotes():
    prog = [{"chapter": 1, "character": "主角", "level": 5}, {"chapter": 2, "character": "主角", "level": 3}]
    alerts = ps.validate_progression(prog, {}, demote_severity="建议级")
    assert all(a["severity"] == "建议级" for a in alerts if a["type"] == "power_level_regress")


# ── validate_panel_schema ──

def test_panel_too_many_attrs():
    schema = {"attrs": ["力量", "敏捷", "体质", "精神", "幸运", "魅力", "悟性", "因果"]}  # 8 个
    alerts = ps.validate_panel_schema(schema)
    assert any(a["type"] == "power_panel_too_many_attrs" for a in alerts)


def test_panel_ok_and_dup():
    assert ps.validate_panel_schema({"attrs": ["力量", "敏捷", "体质"]}) == []
    dup = ps.validate_panel_schema({"attrs": ["力量", "力量"]})
    assert any(a["type"] == "power_panel_dup_attr" for a in dup)


# ── check_pacing ──

def test_pacing_leap_too_fast_unjustified():
    prog = [
        {"chapter": 1, "character": "主角", "tier": "练气初期"},
        {"chapter": 2, "character": "主角", "tier": "金丹初期"},  # 1 章跳 4 个大境界
    ]
    tiers = {"sequence": ["练气", "筑基", "结丹", "金丹", "元婴"], "subtiers": ["初期", "中期", "后期", "大圆满"]}
    alerts = ps.check_pacing(prog, tiers, {"max_tier_jump_per_chapter": 1}, {2: "他一夜之间突飞猛进"})
    assert any(a["type"] == "power_leap_too_fast" for a in alerts)


def test_pacing_leap_justified_by_text():
    prog = [
        {"chapter": 1, "character": "主角", "tier": "练气初期"},
        {"chapter": 2, "character": "主角", "tier": "金丹初期"},
    ]
    tiers = {"sequence": ["练气", "筑基", "结丹", "金丹"], "subtiers": ["初期", "中期", "后期", "大圆满"]}
    # 正文有"丹药/机缘/代价"→ 不报
    alerts = ps.check_pacing(prog, tiers, {"max_tier_jump_per_chapter": 1},
                             {2: "他服下九转金丹，承受巨大反噬，一举突破"})
    assert not any(a["type"] == "power_leap_too_fast" for a in alerts)


# ── check_scene_presence ──

def test_scene_presence_flags_long_gap():
    chapters = [(i, "他在街上走着，与朋友闲聊吃饭") for i in range(1, 13)]
    alerts = ps.check_scene_presence(chapters, window=10)
    assert any(a["type"] == "power_motif_absent" for a in alerts)


def test_scene_presence_ok_with_panels():
    chapters = [(i, "系统面板亮起，恭喜宿主升级") for i in range(1, 13)]
    assert ps.check_scene_presence(chapters, window=10) == []


# ── run（端到端·临时目录）──

def test_run_skips_without_registry(tmp_path):
    res = ps.run(str(tmp_path))
    assert res["ran"] is False


def test_run_blocks_on_regress(tmp_path):
    setdir = tmp_path / "设定"
    setdir.mkdir()
    reg = {
        "kind": ps.POWER_SYSTEM_REGISTRY_KIND, "version": 1, "system_type": "修仙",
        "tiers": {"sequence": ["练气", "筑基"], "subtiers": ["初期", "中期", "后期", "大圆满"]},
        "panel_schema": {},
        "pacing": {"max_tier_jump_per_chapter": 1},
        "progression": [
            {"chapter": 5, "character": "主角", "tier": "筑基初期"},
            {"chapter": 8, "character": "主角", "tier": "练气后期"},
        ],
    }
    (setdir / "power_system_registry.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    res = ps.run(str(tmp_path))
    assert res["ran"] is True
    assert res["blocking"] >= 1
    assert any(a["type"] == "power_tier_regress" for a in res["alerts"])


def test_run_advisory_only_no_block(tmp_path):
    setdir = tmp_path / "设定"
    setdir.mkdir()
    reg = {
        "kind": ps.POWER_SYSTEM_REGISTRY_KIND, "version": 1, "system_type": "修仙",
        "tiers": {"sequence": ["练气", "筑基"], "subtiers": ["初期", "中期", "后期", "大圆满"]},
        "progression": [
            {"chapter": 5, "character": "主角", "tier": "筑基初期"},
            {"chapter": 8, "character": "主角", "tier": "练气后期"},
        ],
    }
    (setdir / "power_system_registry.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    res = ps.run(str(tmp_path), advisory_only=True)
    assert res["ran"] is True
    assert res["blocking"] == 0
