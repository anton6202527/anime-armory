#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for motif_detector.py — run from skills/n2d-script/scripts/.

    cd skills/n2d-script/scripts && python -m pytest test_motif_detector.py
"""
import json
import os

import motif_detector as md


# ── detect_genre（纯函数）──

def test_detect_genre_system_flow():
    text = "他穿越后绑定了系统，面板上属性栏显示宿主等级，每日签到领奖励，叮——升级了"
    r = md.detect_genre(text)
    assert r["genre"] == "系统流"
    assert r["hits"] >= md.GENRE_MIN_HITS
    assert r["confidence"] > 0


def test_detect_genre_below_threshold_returns_none():
    # 只命中一个题材关键词，达不到 min_hits
    r = md.detect_genre("今天天气不错，他去公司上班")
    assert r["genre"] is None
    assert r["confidence"] == 0.0


def test_detect_genre_by_genre_sorted_desc():
    text = "穿越重生回到古代，醒来发现身处异世界，前世今生"
    r = md.detect_genre(text)
    assert r["genre"] == "穿越"
    # by_genre 按命中数降序
    hits = [g["hits"] for g in r["by_genre"]]
    assert hits == sorted(hits, reverse=True)


# ── classify_motif / detect_motif_clips ──

def _clip(label="", desc="", cid=None):
    c = {"label": label, "shots": [{"desc": desc}]}
    if cid:
        c["id"] = cid
    return c


def test_classify_motif_system_panel():
    hit = md.classify_motif(_clip(label="系统面板浮现", desc="蓝色光幕显示等级与属性值"))
    assert hit is not None
    assert hit["motif_type"] == "system_panel"
    assert "命中" in hit["rule"]


def test_classify_motif_no_hit():
    assert md.classify_motif(_clip(label="两人在街头对话", desc="过肩反打")) is None


def test_detect_motif_clips_assigns_ids_and_growth():
    clips = [
        _clip(label="日常开场", desc="走在路上"),
        _clip(label="系统面板出现", desc="光幕显示属性面板等级", cid="EP01_CLIP02"),
        _clip(label="主角升级", desc="经验满，等级提升，突破"),
    ]
    found = md.detect_motif_clips(clips, "第1集")
    assert len(found) == 2
    # 第二个 clip 用自带 id；第三个回退合成 id
    ids = {m["clip_id"] for m in found}
    assert "EP01_CLIP02" in ids
    assert any(i.endswith("CLIP03") for i in ids)
    # 面板家族统一归 MOTIF_系统面板，套 system_panel 模板
    for m in found:
        assert m["motif_id"] == md.SYSTEM_PANEL_MOTIF_ID
        assert m["template"] == md.SYSTEM_PANEL_TEMPLATE_ID
    # 成长档按出现序递增（占位）
    levels = [m["growth_suggestion"]["level"] for m in found]
    assert levels == [1, 2]


# ── motif_template_id / motif_id_for ──

def test_panel_family_maps_to_system_panel():
    assert md.motif_template_id("level_up") == md.SYSTEM_PANEL_TEMPLATE_ID
    assert md.motif_id_for("signin") == md.SYSTEM_PANEL_MOTIF_ID


def test_non_panel_motif_has_no_template():
    assert md.motif_template_id("loot") == ""
    assert md.motif_id_for("loot") == md.MOTIF_ID_PREFIX + "loot"


# ── validate_progression_monotonic（纯函数）──

def test_progression_monotonic_ok():
    prog = [
        {"at_clip": "C1", "level": 1, "panel_tier": "v1_素纹"},
        {"at_clip": "C2", "level": 5, "panel_tier": "v2_流光"},
        {"at_clip": "C3", "level": 12, "panel_tier": "v3_符纹"},
    ]
    r = md.validate_progression_monotonic(prog)
    assert r["ok"] is True
    assert r["violations"] == []


def test_progression_regression_blocks():
    prog = [
        {"at_clip": "C1", "level": 5, "panel_tier": "v2"},
        {"at_clip": "C2", "level": 3, "panel_tier": "v1"},  # 等级退档 + 面板退档
    ]
    r = md.validate_progression_monotonic(prog)
    assert r["ok"] is False
    fields = {v["field"] for v in r["violations"]}
    assert "level" in fields
    assert "panel_tier" in fields


def test_progression_skips_unparseable_values():
    prog = [{"at_clip": "C1", "level": None}, {"at_clip": "C2", "level": 2}]
    r = md.validate_progression_monotonic(prog)
    assert r["ok"] is True


def test_clip_text_ignores_continuity_bridge_state():
    clip = {
        "id": "EP01_CLIP09",
        "label": "小禾信任沈念",
        "continuity": {
            "start_state": "系统空光幕收起，沈念看向小禾",
            "end_state": "小禾靠近沈念半步",
        },
        "shots": [{"desc": "小禾颤抖却选择留下。"}],
    }

    assert md.classify_motif(clip) is None


# ── write-back（端到端·临时目录）──

def test_inject_and_upsert_registry(tmp_path):
    root = tmp_path
    ep = "第1集"
    sb_dir = root / "脚本" / ep
    sb_dir.mkdir(parents=True)
    storyboard = {"clips": [
        {"id": "EP01_CLIP01", "label": "开场"},
        {"id": "EP01_CLIP02", "label": "系统面板出现", "shots": [{"desc": "光幕显示等级属性面板"}]},
    ]}
    (sb_dir / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")

    plan = md.plan_episode(str(root), ep)
    assert plan["summary"]["panel_clips"] == 1

    n = md.inject_storyboard(str(root), ep, plan["motif_clips"])
    assert n == 1
    sb = json.loads((sb_dir / "storyboard.json").read_text(encoding="utf-8"))
    clip2 = sb["clips"][1]
    assert clip2["template"] == md.SYSTEM_PANEL_TEMPLATE_ID
    assert clip2["template_contract"]["template_id"] == md.SYSTEM_PANEL_TEMPLATE_ID
    assert clip2["template_contract"]["beats"]
    assert clip2["template_contract"]["negative"]
    assert clip2["template_contract"]["motif_id"] == md.SYSTEM_PANEL_MOTIF_ID
    assert clip2["template_contract"]["text_layer"] == "overlay"

    reg_info = md.upsert_motif_registry(str(root), plan["motif_clips"])
    assert reg_info["created"] == 1
    assert reg_info["appended"] == 1
    reg = json.loads((root / "出图" / "共享" / "motif_registry.json").read_text(encoding="utf-8"))
    assert reg["kind"] == md.MOTIF_REGISTRY_KIND
    entry = reg["motifs"][0]
    assert entry["motif_id"] == md.SYSTEM_PANEL_MOTIF_ID
    assert entry["growth_state_machine"]["bound_vfx"] == md.SYSTEM_PANEL_VFX_ID
    assert entry["growth_state_machine"]["progression"][0]["at_clip"] == "EP01_CLIP02"


def test_upsert_registry_idempotent(tmp_path):
    root = tmp_path
    ep = "第1集"
    sb_dir = root / "脚本" / ep
    sb_dir.mkdir(parents=True)
    storyboard = {"clips": [
        {"id": "EP01_CLIP02", "label": "系统面板", "shots": [{"desc": "光幕等级属性面板"}]},
    ]}
    (sb_dir / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    plan = md.plan_episode(str(root), ep)
    md.upsert_motif_registry(str(root), plan["motif_clips"])
    second = md.upsert_motif_registry(str(root), plan["motif_clips"])
    # 重跑不重复追加同一 at_clip
    assert second["appended"] == 0
    reg = json.loads((root / "出图" / "共享" / "motif_registry.json").read_text(encoding="utf-8"))
    assert len(reg["motifs"][0]["growth_state_machine"]["progression"]) == 1
