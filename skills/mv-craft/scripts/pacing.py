#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv 共享卡点/节奏/时长确定性引擎（pure functions，无 IO、无副作用）。

把"卡点节奏可机算"的那几个信号收成一处，给两个消费方共用：
  - mv-review/scripts/mv_check.py —— 事后质检（成片/产物体检）。
  - mv-score/scripts/score_pacing.py —— 事前闸门（出图/出视频花钱前的机检前奏）。

输入只认两个已解析好的 dict + 一个歌长：
  clip_plan  —— mv-plan/scripts/plan_clips.py 产的 clip_plan.json，取 clips[].duration / clip_id /
                section / start / end / beat_role。
  beatgrid   —— mv-beat/scripts/beat_detect.py 产的 beatgrid.json，取 downbeats / beats / duration / bpm。
  song_len   —— 歌长（秒），可为 None（缺成品歌时只算与歌长无关的指标）。

四个指标（全部确定性、可复跑）：
  1. clip 边界 ↔ downbeat 对齐率   clip_downbeat_alignment()
  2. 副歌 vs 主歌 clip 密度对比     chorus_verse_density()
  3. 规划总时长 vs 歌长             planned_duration_vs_song()
  4. 等长 clip CV（疑似不卡点）     equal_length_cv()

容差 / 阈值常量从 mv-craft/scripts/contract.py 取（单一真相源；本模块不另立一套）。
只用标准库。
"""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONTRACT_PATH = os.path.join(_HERE, "contract.py")


def _load_contract():
    spec = importlib.util.spec_from_file_location("mv_contract", _CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_contract = _load_contract()

# 节奏判据阈值（来自 contract，单一真相源；缺则用保守默认，绝不在本模块另立一套）
DUR_TOL = float(getattr(_contract, "PACING_DUR_TOL", 2.0))         # 时长一致允许差（秒，或按 10% 取大）
DUR_TOL_FRAC = float(getattr(_contract, "PACING_DUR_TOL_FRAC", 0.1))
EQUAL_CV = float(getattr(_contract, "PACING_EQUAL_CV", 0.05))      # 极差/均值 低于此 → 疑似等长不卡点
ALIGN_TOL = float(getattr(_contract, "PACING_ALIGN_TOL", 0.15))    # clip 边界落在 downbeat ± 此秒数内算"对齐"


def duration_tol(song_len, base_tol=None):
    """歌长相关时长容差：max(绝对容差, 比例容差)。song_len 缺失时退回绝对容差。"""
    base = DUR_TOL if base_tol is None else float(base_tol)
    if not song_len:
        return base
    return max(base, DUR_TOL_FRAC * float(song_len))


def _is_chorus(name):
    low = str(name or "").lower()
    return any(k in low for k in ("chorus", "副歌", "drop", "hook", "refrain"))


def _is_verse(name):
    low = str(name or "").lower()
    if _is_chorus(name):
        return False
    return any(k in low for k in ("verse", "主歌", "段", "stanza")) or low.startswith("verse")


def _durations(clips):
    out = []
    for c in clips or []:
        try:
            d = float(c.get("duration") or 0)
        except (TypeError, ValueError):
            continue
        if d > 0:
            out.append(d)
    return out


def _boundaries(clips):
    """clip 内部边界时间戳（不含整曲首尾 0 / 末尾），用于对齐 downbeat 检测。"""
    pts = []
    for c in clips or []:
        for key in ("start", "end"):
            v = c.get(key)
            if isinstance(v, (int, float)):
                pts.append(round(float(v), 3))
    # 去重排序
    pts = sorted(set(pts))
    # 丢掉整曲起点(≈0)与可能的终点（终点不算"切点"）
    if pts and pts[0] <= 0.01:
        pts = pts[1:]
    if pts:
        pts = pts[:-1]  # 末边界=曲尾，不计为内部切点
    return pts


def equal_length_cv(clip_plan, min_clips=4):
    """等长 clip 检测：返回 (cv, suspicious, n)。

    cv = 极差/均值（与 mv_check 旧实现一致：(max-min)/mean）；
    clip 数 < min_clips 时 suspicious=False（样本太少不判）。
    """
    durs = _durations((clip_plan or {}).get("clips"))
    n = len(durs)
    if n < min_clips:
        return None, False, n
    mean = sum(durs) / n
    if mean <= 0:
        return None, False, n
    cv = (max(durs) - min(durs)) / mean
    return round(cv, 4), bool(cv < EQUAL_CV), n


def planned_duration_vs_song(clip_plan, song_len):
    """规划总时长 vs 歌长：返回 (total, song_len, diff, mismatch)。

    song_len 缺失 → mismatch=None（无基准不判）。
    """
    durs = _durations((clip_plan or {}).get("clips"))
    total = round(sum(durs), 3)
    if not song_len:
        return total, None, None, None
    diff = round(total - float(song_len), 3)
    mismatch = abs(diff) > duration_tol(song_len)
    return total, round(float(song_len), 3), diff, bool(mismatch)


def clip_downbeat_alignment(clip_plan, beatgrid, tol=None):
    """clip 内部切点 ↔ downbeat 对齐率：返回 (aligned, total_boundaries, ratio)。

    每个内部 clip 边界，若存在某 downbeat 落在 ±tol 内 → 计为对齐。
    无内部边界或无 downbeat → ratio=None。
    """
    tol = ALIGN_TOL if tol is None else float(tol)
    bounds = _boundaries((clip_plan or {}).get("clips"))
    grid = (beatgrid or {}).get("downbeats") or (beatgrid or {}).get("beats") or []
    grid = sorted(float(t) for t in grid if isinstance(t, (int, float)))
    if not bounds or not grid:
        return 0, len(bounds), None
    aligned = 0
    for b in bounds:
        # 最近 downbeat 距离
        nearest = min(abs(b - g) for g in grid)
        if nearest <= tol:
            aligned += 1
    ratio = round(aligned / len(bounds), 4)
    return aligned, len(bounds), ratio


def chorus_verse_density(clip_plan, beatgrid=None):
    """副歌 vs 主歌 clip 密度（clip 数 / 秒）对比。

    返回 dict：
      chorus_density / verse_density —— clips-per-second（按各自段落实占时长）
      contrast —— chorus_density / verse_density（>1 = 副歌更密，符合"副歌快切"规律）
      chorus_clips / verse_clips / chorus_secs / verse_secs
      ok —— 副歌密度 ≥ 主歌密度（contrast ≥ 1）；任一缺样本则 None。
    MV 节奏铁律：副歌快切爆发、主歌长镜叙事 → 期望 contrast > 1。
    """
    clips = (clip_plan or {}).get("clips") or []
    c_clips = v_clips = 0
    c_secs = v_secs = 0.0
    for c in clips:
        sec = c.get("section")
        try:
            d = float(c.get("duration") or 0)
        except (TypeError, ValueError):
            d = 0.0
        if _is_chorus(sec):
            c_clips += 1
            c_secs += d
        elif _is_verse(sec):
            v_clips += 1
            v_secs += d
    c_density = round(c_clips / c_secs, 4) if c_secs > 0 else None
    v_density = round(v_clips / v_secs, 4) if v_secs > 0 else None
    contrast = round(c_density / v_density, 3) if (c_density and v_density) else None
    ok = (contrast is not None and contrast >= 1.0)
    return {
        "chorus_clips": c_clips,
        "verse_clips": v_clips,
        "chorus_secs": round(c_secs, 3),
        "verse_secs": round(v_secs, 3),
        "chorus_density": c_density,
        "verse_density": v_density,
        "contrast": contrast,
        "ok": ok if contrast is not None else None,
    }


def pacing_report(clip_plan, beatgrid, song_len):
    """一次性算齐四个指标，返回结构化 dict（消费方各取所需，自行翻译成 finding/score）。"""
    cv, cv_suspicious, n_clips = equal_length_cv(clip_plan)
    total, song, diff, dur_mismatch = planned_duration_vs_song(clip_plan, song_len)
    aligned, n_bounds, align_ratio = clip_downbeat_alignment(clip_plan, beatgrid)
    density = chorus_verse_density(clip_plan, beatgrid)
    return {
        "clip_count": n_clips,
        "equal_length": {"cv": cv, "suspicious": cv_suspicious, "threshold": EQUAL_CV},
        "duration": {
            "planned_total": total,
            "song_len": song,
            "diff": diff,
            "mismatch": dur_mismatch,
            "tol": round(duration_tol(song_len), 3) if song_len else DUR_TOL,
        },
        "downbeat_alignment": {
            "aligned": aligned,
            "boundaries": n_bounds,
            "ratio": align_ratio,
            "tol": ALIGN_TOL,
        },
        "chorus_verse_density": density,
    }
