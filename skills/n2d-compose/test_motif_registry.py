#!/usr/bin/env python3
"""motif_registry 纯函数单测——确定性复用规划的回归护栏。
跑法：cd skills/n2d-compose && python -m pytest test_motif_registry.py
"""
from __future__ import annotations

import motif_registry as M


# ---------- normalize_motifs ----------

def test_normalize_str_value_as_file():
    out = M.normalize_motifs({"沈念": "素材/motif/shen.wav"})
    assert out["沈念"]["file"] == "素材/motif/shen.wav"
    assert out["沈念"]["cue"] == M.DEFAULT_CUE
    assert out["沈念"]["gain"] == M.DEFAULT_GAIN


def test_normalize_dict_value_full():
    out = M.normalize_motifs(
        {"东宫": {"file": "x.wav", "cue": "faction", "gain": 0.4, "faction": True}})
    assert out["东宫"] == {"file": "x.wav", "cue": "faction", "gain": 0.4}


def test_normalize_drops_empty_key_and_empty_file():
    out = M.normalize_motifs({"": "a.wav", "无音频": {"file": "", "gain": 0.5},
                              "好": {"file": "b.wav"}})
    assert "" not in out and "无音频" not in out
    assert out["好"]["file"] == "b.wav"


def test_normalize_bad_gain_falls_back_default():
    out = M.normalize_motifs({"沈念": {"file": "a.wav", "gain": "loud"}})
    assert out["沈念"]["gain"] == M.DEFAULT_GAIN


def test_normalize_none_and_nondict_value():
    out = M.normalize_motifs({"x": None, "y": 123, "z": "z.wav"})
    assert set(out) == {"z"}


# ---------- plan_cues ----------

def _line(role, start, end=None):
    d = {"角色": role, "start": start}
    if end is not None:
        d["end"] = end
    return d


def test_plan_empty_registry_returns_empty():
    man = [_line("沈念", 0.0), _line("沈念", 20.0)]
    assert M.plan_cues(man, {}) == []


def test_plan_empty_manifest_returns_empty():
    assert M.plan_cues([], {"沈念": {"file": "a.wav", "cue": "focus", "gain": 0.5}}) == []


def test_plan_single_focus_cue():
    motifs = {"沈念": {"file": "shen.wav", "cue": "focus", "gain": 0.5}}
    man = [_line("沈念", 3.0, 6.0)]
    cues = M.plan_cues(man, motifs)
    assert len(cues) == 1
    assert cues[0]["key"] == "沈念"
    assert cues[0]["file"] == "shen.wav"
    assert cues[0]["at"] == 3.0
    assert cues[0]["gain"] == 0.5


def test_plan_retrigger_suppressed_within_min_gap():
    motifs = {"沈念": {"file": "shen.wav", "cue": "focus", "gain": 0.5}}
    # 三句沈念：0s、5s（距上次 5 < 8 → 压）、20s（距上次 20 > 8 → 触发）
    man = [_line("沈念", 0.0), _line("沈念", 5.0), _line("沈念", 20.0)]
    cues = M.plan_cues(man, motifs, min_gap=8.0)
    ats = [c["at"] for c in cues]
    assert ats == [0.0, 20.0]


def test_plan_min_gap_boundary_exactly_at_gap_triggers():
    # 恰好 == min_gap 不算「不足」，应触发（用 < 判定）
    motifs = {"沈念": {"file": "a.wav", "cue": "focus", "gain": 0.5}}
    man = [_line("沈念", 0.0), _line("沈念", 8.0)]
    cues = M.plan_cues(man, motifs, min_gap=8.0)
    assert [c["at"] for c in cues] == [0.0, 8.0]


def test_plan_multiple_characters_independent_gap():
    motifs = {"沈念": {"file": "shen.wav", "cue": "focus", "gain": 0.5},
              "东宫": {"file": "dg.wav", "cue": "faction", "gain": 0.4}}
    man = [_line("沈念", 0.0), _line("东宫", 2.0), _line("沈念", 3.0),
           _line("东宫", 12.0)]
    cues = M.plan_cues(man, motifs, min_gap=8.0)
    # 沈念@0 触发，沈念@3 被压（<8）；东宫@2 触发，东宫@12 触发（>8）。各角色独立计 gap。
    got = [(c["key"], c["at"]) for c in cues]
    assert got == [("沈念", 0.0), ("东宫", 2.0), ("东宫", 12.0)]


def test_plan_sorted_by_time_even_if_manifest_unordered():
    motifs = {"沈念": {"file": "a.wav", "cue": "focus", "gain": 0.5}}
    man = [_line("沈念", 30.0), _line("沈念", 0.0)]
    cues = M.plan_cues(man, motifs, min_gap=8.0)
    assert [c["at"] for c in cues] == [0.0, 30.0]


def test_plan_substring_role_match_and_longest_first():
    # '沈念旁白' 应命中登记的 '沈念'；同时有更具体的 key 时长 key 优先
    motifs = {"沈念": {"file": "shen.wav", "cue": "focus", "gain": 0.5}}
    man = [_line("沈念旁白", 1.0)]
    cues = M.plan_cues(man, motifs)
    assert len(cues) == 1 and cues[0]["key"] == "沈念"


def test_plan_role_field_role_key_alias():
    motifs = {"沈念": {"file": "a.wav", "cue": "focus", "gain": 0.5}}
    man = [{"role": "沈念", "start": 4.0}]
    cues = M.plan_cues(man, motifs)
    assert len(cues) == 1 and cues[0]["at"] == 4.0


def test_plan_skips_lines_missing_start_or_role():
    motifs = {"沈念": {"file": "a.wav", "cue": "focus", "gain": 0.5}}
    man = [{"角色": "沈念"}, {"start": 5.0}, _line("沈念", 9.0)]
    cues = M.plan_cues(man, motifs)
    assert [c["at"] for c in cues] == [9.0]


def test_plan_unregistered_character_no_cue():
    motifs = {"沈念": {"file": "a.wav", "cue": "focus", "gain": 0.5}}
    man = [_line("柳娘子", 0.0), _line("小禾", 5.0)]
    assert M.plan_cues(man, motifs) == []


# ---------- cue_filter_plan ----------

def test_cue_filter_plan_adelay_and_gain():
    cues = [{"key": "沈念", "file": "shen.wav", "at": 3.25, "gain": 0.5, "cue": "focus"}]
    plan = M.cue_filter_plan(cues)
    assert plan == [{"file": "shen.wav", "adelay_ms": 3250, "gain": 0.5, "key": "沈念"}]


def test_cue_filter_plan_empty():
    assert M.cue_filter_plan([]) == []


def test_cue_filter_plan_negative_at_clamped_to_zero():
    plan = M.cue_filter_plan([{"file": "a.wav", "at": -2.0, "gain": 0.4, "key": "x"}])
    assert plan[0]["adelay_ms"] == 0


def test_cue_filter_plan_missing_gain_defaults():
    plan = M.cue_filter_plan([{"file": "a.wav", "at": 1.0, "key": "x"}])
    assert plan[0]["gain"] == M.DEFAULT_GAIN


def test_end_to_end_plan_then_filter():
    motifs = {"沈念": {"file": "shen.wav", "cue": "focus", "gain": 0.5}}
    man = [_line("沈念", 1.0), _line("沈念", 2.0), _line("沈念", 30.0)]
    plan = M.cue_filter_plan(M.plan_cues(man, motifs, min_gap=8.0))
    assert [(p["adelay_ms"], p["key"]) for p in plan] == [(1000, "沈念"), (30000, "沈念")]


# ---- 成片动机铺设 argv 构造（T5·compose 接入，纯函数）----

def test_build_overlay_args_empty_plan_is_none():
    assert M.build_overlay_args("in.mp4", "out.mp4", []) is None


def test_build_overlay_args_structure():
    plan = [{"file": "a.wav", "adelay_ms": 3000, "gain": 0.5, "key": "沈念"},
            {"file": "b.wav", "adelay_ms": 12000, "gain": 0.4, "key": "东宫"}]
    args = M.build_overlay_args("in.mp4", "out.mp4", plan, ffmpeg="ffmpeg")
    # 基础视频直 copy，音频 amix=1+2=3 路，两段动机各自 adelay+volume
    assert "-c:v" in args and args[args.index("-c:v") + 1] == "copy"
    fc = args[args.index("-filter_complex") + 1]
    assert "adelay=3000|3000,volume=0.5[m1]" in fc
    assert "adelay=12000|12000,volume=0.4[m2]" in fc
    assert "amix=inputs=3:normalize=0:duration=first[a]" in fc
    # 每段动机一个 -i 输入 + 成片本身
    assert args.count("-i") == 3
    assert args[-1] == "out.mp4"
