#!/usr/bin/env python3
"""reverb_profile 纯函数单测。

跑法（从脚本自身目录，无中心 runner）：
  cd skills/n2d-voice && python -m pytest test_reverb_profile.py
"""
from __future__ import annotations

import reverb_profile as rp


# ---------- normalize_acoustic_table ----------

def test_normalize_basic():
    assert rp.normalize_acoustic_table({"冷宫大殿": "hall", "密道": "cave"}) == {
        "冷宫大殿": "hall", "密道": "cave"}


def test_normalize_none_and_empty():
    assert rp.normalize_acoustic_table(None) == {}
    assert rp.normalize_acoustic_table({}) == {}


def test_normalize_drops_empty_key_or_value():
    raw = {"": "hall", "御花园": "", "  ": "cave", "寝殿": "room"}
    assert rp.normalize_acoustic_table(raw) == {"寝殿": "room"}


def test_normalize_strips_whitespace():
    assert rp.normalize_acoustic_table({"  大殿 ": "  hall "}) == {"大殿": "hall"}


def test_normalize_keeps_unknown_preset_key():
    # 未知预设键不在 normalize 静默吞掉（留给 reverb_filter 当 dry），便于巡检发现错配
    assert rp.normalize_acoustic_table({"地牢": "dungeon"}) == {"地牢": "dungeon"}


# ---------- preset_for_scene ----------

def test_preset_longest_substring_wins():
    # "冷宫大殿" 应先于 "大殿" 命中（更具体的场景压过泛类）
    table = {"大殿": "hall", "冷宫大殿": "cave"}
    assert rp.preset_for_scene("镜头1 冷宫大殿 侧逆光", table) == "cave"


def test_preset_plain_substring_match():
    table = {"密道": "cave"}
    assert rp.preset_for_scene("EP02 暗夜密道追逐", table) == "cave"


def test_preset_default_when_no_match():
    table = {"大殿": "hall"}
    assert rp.preset_for_scene("御花园小径", table) == "dry"


def test_preset_default_when_table_empty():
    assert rp.preset_for_scene("冷宫大殿", {}) == "dry"


def test_preset_default_when_scene_empty():
    assert rp.preset_for_scene("", {"大殿": "hall"}) == "dry"
    assert rp.preset_for_scene(None, {"大殿": "hall"}) == "dry"


def test_preset_custom_default():
    assert rp.preset_for_scene("无名地", {"大殿": "hall"}, default="room") == "room"


# ---------- reverb_filter ----------

def test_reverb_filter_dry_is_empty():
    assert rp.reverb_filter("dry") == ""


def test_reverb_filter_unknown_is_empty():
    assert rp.reverb_filter("dungeon") == ""
    assert rp.reverb_filter("") == ""
    assert rp.reverb_filter(None) == ""


def test_reverb_filter_has_trailing_comma_when_wet():
    # 非空片段必须以尾逗号收口，才能前插进 render_voice 的 fx 链
    for key in ("room", "hall", "cave", "outdoor"):
        frag = rp.reverb_filter(key)
        assert frag.endswith(","), f"{key} 片段须以尾逗号收口: {frag!r}"
        assert frag.startswith("aecho="), f"{key} 须用 aecho（裁剪版 ffmpeg 无 afir/areverb）: {frag!r}"


def test_reverb_filter_known_values():
    assert rp.reverb_filter("hall") == "aecho=0.8:0.85:60:0.4,"
    assert rp.reverb_filter("cave") == "aecho=0.8:0.9:120|180:0.5|0.3,"


# ---------- line_reverb ----------

def test_line_reverb_end_to_end_wet():
    table = {"冷宫大殿": "hall"}
    assert rp.line_reverb("镜头3 冷宫大殿", table) == "aecho=0.8:0.85:60:0.4,"


def test_line_reverb_dry_when_no_match_or_no_table():
    assert rp.line_reverb("御花园", {"大殿": "hall"}) == ""   # 无命中 → dry → ""
    assert rp.line_reverb("冷宫大殿", {}) == ""                # 空表 → dry → ""
    assert rp.line_reverb("", {"大殿": "hall"}) == ""          # 空场景 → dry → ""


def test_line_reverb_prefix_safe_concat():
    # 模拟 render_voice 的拼接：reverb 前缀 + 系统音FX + loudnorm，分隔不破
    table = {"密道": "cave"}
    sysfx = "aecho=0.6:0.5:24:0.35,"
    fx = rp.line_reverb("暗夜密道", table) + sysfx
    assert fx == "aecho=0.8:0.9:120|180:0.5|0.3,aecho=0.6:0.5:24:0.35,"
    chain = fx + "loudnorm=I=-16:TP=-1.5:LRA=11"
    assert ",," not in chain and not chain.startswith(",")
