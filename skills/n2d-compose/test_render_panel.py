#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for render_panel.py — run from skills/n2d-compose/.

    cd skills/n2d-compose && python -m pytest test_render_panel.py

只测纯函数（select_snapshot/compute_clip_windows/panel_text_lines/anchor_xy/plan_panels），
不触 PIL 渲染（render() 内惰性 import PIL）。
"""
import render_panel as rp


# ── compute_clip_windows ──

def test_compute_clip_windows_cumulative():
    clips = [{"duration": 3}, {"duration": 5}, {"duration": 2}]
    assert rp.compute_clip_windows(clips) == [(0.0, 3.0), (3.0, 8.0), (8.0, 10.0)]


def test_compute_clip_windows_missing_duration_zero_width():
    clips = [{"duration": 4}, {"label": "无时长"}, {"duration": 2}]
    w = rp.compute_clip_windows(clips)
    assert w[0] == (0.0, 4.0)
    assert w[1] == (4.0, 4.0)   # 0 宽
    assert w[2] == (4.0, 6.0)


# ── is_panel_clip / clip_motif_id ──

def test_is_panel_clip_by_template():
    assert rp.is_panel_clip({"template": "system_panel"}) is True
    assert rp.is_panel_clip({"template_contract": {"motif_id": "MOTIF_系统面板"}}) is True
    assert rp.is_panel_clip({"template": "fight_exchange"}) is False
    assert rp.is_panel_clip({}) is False


def test_clip_motif_id_default():
    assert rp.clip_motif_id({"template": "system_panel"}) == rp.SYSTEM_PANEL_MOTIF_ID
    assert rp.clip_motif_id({"template_contract": {"motif_id": "MOTIF_X"}}) == "MOTIF_X"


# ── select_snapshot ──

def _prog():
    return [
        {"at_clip": "C2", "level": 1, "panel_tier": "v1"},
        {"at_clip": "C5", "level": 5, "panel_tier": "v2"},
        {"at_clip": "C9", "level": 12, "panel_tier": "v3"},
    ]


def test_select_snapshot_exact():
    order = {"C2": 1, "C5": 4, "C9": 8}
    snap = rp.select_snapshot(_prog(), order, "C5")
    assert snap["level"] == 5


def test_select_snapshot_latest_before_current():
    # 当前 Clip C7 序在 C5 和 C9 之间 → 取最新 ≤ 的 C5
    order = {"C2": 1, "C5": 4, "C7": 6, "C9": 8}
    snap = rp.select_snapshot(_prog(), order, "C7")
    assert snap["level"] == 5


def test_select_snapshot_none_before_first():
    # 当前 Clip C1 序在第一条成长档之前 → 无候选
    order = {"C1": 0, "C2": 1, "C5": 4, "C9": 8}
    assert rp.select_snapshot(_prog(), order, "C1") is None


# ── panel_text_lines ──

def test_panel_text_lines_full():
    snap = {"title": "系统", "level": 5, "attrs": {"力量": 30, "敏捷": 22}}
    spec = {"fields": ["title", "level", "attrs"]}
    lines = rp.panel_text_lines(snap, spec)
    assert lines[0] == "系统"
    assert lines[1] == "Lv.5"
    assert "力量  30" in lines and "敏捷  22" in lines


def test_panel_text_lines_skips_missing():
    snap = {"level": 3}
    lines = rp.panel_text_lines(snap, {"fields": ["title", "level", "attrs"]})
    assert lines == ["Lv.3"]


# ── anchor_xy ──

def test_anchor_xy_known_and_fallback():
    assert rp.anchor_xy("panel_center", 1080, 1920) == (540, 960)
    assert rp.anchor_xy("panel_top", 1080, 1920) == (540, 640)
    # 未知锚点回退中心
    assert rp.anchor_xy("???", 1080, 1920) == (540, 960)


# ── plan_panels（端到端·纯函数） ──

def test_plan_panels_picks_growth_per_clip():
    clips = [
        {"id": "C1", "duration": 3, "label": "开场"},
        {"id": "C2", "duration": 4, "template": "system_panel",
         "template_contract": {"motif_id": "MOTIF_系统面板"}},
        {"id": "C5", "duration": 5, "template": "system_panel",
         "template_contract": {"motif_id": "MOTIF_系统面板"}},
    ]
    # 注：C5 在 clips 里序号=2，但成长档 at_clip 用真实 id
    registry = {"kind": "n2d_motif_registry", "motifs": [{
        "motif_id": "MOTIF_系统面板",
        "growth_state_machine": {"progression": [
            {"at_clip": "C2", "level": 1, "title": "系统", "attrs": {"力量": 10}},
            {"at_clip": "C5", "level": 5, "title": "系统", "attrs": {"力量": 30}},
        ]},
        "overlay_spec": {"anchor": "panel_center", "fields": ["title", "level", "attrs"], "color": [180, 230, 255]},
    }]}
    panels = rp.plan_panels(clips, registry, "第1集")
    assert len(panels) == 2
    # 第一个面板镜=C2→Lv.1；第二个=C5→Lv.5
    assert panels[0]["clip_id"] == "C2" and "Lv.1" in panels[0]["lines"]
    assert panels[1]["clip_id"] == "C5" and "Lv.5" in panels[1]["lines"]
    # 时间窗累计：C2=[3,7], C5=[7,12]
    assert panels[0]["window"] == (3.0, 7.0)
    assert panels[1]["window"] == (7.0, 12.0)


def test_plan_panels_empty_without_registry():
    clips = [{"id": "C2", "duration": 4, "template": "system_panel"}]
    assert rp.plan_panels(clips, None, "第1集") == []
