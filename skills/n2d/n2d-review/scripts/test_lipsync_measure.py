#!/usr/bin/env python3
"""lipsync_measure 纯函数 + 环境降级测试（无 SyncNet 依赖）。

跑：cd skills/n2d/n2d-review/scripts && python -m pytest test_lipsync_measure.py
"""
from __future__ import annotations

import lipsync_measure as lm


# ---------- clip_at（累计时长定位） ----------

def test_clip_at_maps_seconds_to_clip():
    durs = [("Clip01", 4.0), ("Clip02", 6.0), ("Clip03", 5.0)]
    assert lm.clip_at(durs, 0.0) == "Clip01"
    assert lm.clip_at(durs, 3.9) == "Clip01"
    assert lm.clip_at(durs, 4.0) == "Clip02"   # 边界归下一镜
    assert lm.clip_at(durs, 9.9) == "Clip02"
    assert lm.clip_at(durs, 10.0) == "Clip03"


def test_clip_at_skips_zero_duration_and_clamps_tail():
    durs = [("Clip01", 0.0), ("Clip02", 5.0)]
    assert lm.clip_at(durs, 1.0) == "Clip02"   # 0 时长镜跳过
    assert lm.clip_at(durs, 999.0) == "Clip02"  # 越界归末镜


def test_clip_at_empty_is_none():
    assert lm.clip_at([], 3.0) is None


# ---------- fold_best_by_clip（同 Clip 取最高置信） ----------

def test_fold_best_keeps_highest_confidence():
    rows = [
        {"clip": "Clip01", "confidence": 2.0, "offset_frames": 1, "at_sec": 0.0},
        {"clip": "Clip01", "confidence": 7.5, "offset_frames": 5, "at_sec": 1.0},  # 更高置信
        {"clip": "Clip02", "confidence": 3.0, "offset_frames": 0, "at_sec": 6.0},
    ]
    out = lm.fold_best_by_clip(rows)
    by = {r["clip"]: r for r in out}
    assert by["Clip01"]["confidence"] == 7.5
    assert by["Clip01"]["offset_frames"] == 5
    assert len(out) == 2
    # 按 at_sec 排序
    assert [r["clip"] for r in out] == ["Clip01", "Clip02"]


# ---------- 环境缺失优雅降级（不抛、给提示） ----------

def test_measure_missing_env_degrades(tmp_path):
    res = lm.measure(str(tmp_path), "第1集", home=str(tmp_path / "no_syncnet_here"))
    assert res["ok"] is False
    assert any("SyncNet" in n for n in res["notes"])
