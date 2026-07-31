#!/usr/bin/env python3
"""lipsync_consistency 纯数学核心 + 编排测试（无 SyncNet/ffmpeg 依赖）。

跑：cd skills/n2d/n2d-review/scripts && python -m pytest test_lipsync_consistency.py
"""
from __future__ import annotations

import json

import lipsync_consistency as lc


# ---------- offset_ms ----------

def test_offset_ms_frames_to_ms():
    assert lc.offset_ms(0, 25) == 0.0
    assert round(lc.offset_ms(5, 25), 1) == 200.0   # 5 帧 @25fps = 200ms
    assert round(lc.offset_ms(-2, 25), 1) == 80.0   # 取绝对值


def test_offset_ms_bad_fps_falls_back():
    # fps<=0 退回默认 25，不除零
    assert round(lc.offset_ms(5, 0), 1) == 200.0
    assert round(lc.offset_ms(5, -10), 1) == 200.0


# ---------- sync_band ----------

def test_band_low_confidence_inconclusive():
    # 置信低于地板 → inconclusive（哪怕偏移很大也不罚分）
    assert lc.sync_band(offset_frames=10, confidence=1.0) == "inconclusive"


def test_band_ok_small_offset():
    assert lc.sync_band(offset_frames=1, confidence=5.0) == "ok"   # 40ms < warn 80ms


def test_band_warn_mid_offset():
    assert lc.sync_band(offset_frames=3, confidence=5.0) == "warn"  # 120ms ≥ 80ms


def test_band_block_large_offset():
    assert lc.sync_band(offset_frames=6, confidence=5.0) == "block"  # 240ms ≥ 200ms


def test_band_thresholds_tweakable():
    # 把 block_ms 抬高后同输入从 block 降到 warn
    assert lc.sync_band(6, 5.0, block_ms=300.0) == "warn"


# ---------- advisory_verdict（审计封顶） ----------

def test_advisory_caps_block_to_warn():
    assert lc.advisory_verdict("block") == "warn"       # 噪声检测器绝不硬阻断 gate
    assert lc.advisory_verdict("warn") == "warn"
    assert lc.advisory_verdict("ok") == "ok"
    assert lc.advisory_verdict("inconclusive") == "ok"  # 不入 findings


# ---------- is_speaking_clip ----------

def test_is_speaking_clip():
    assert lc.is_speaking_clip("mouth_visible=yes 正面说话") is True
    # 尽力而为的宽松 prefilter：无任何说话标记 → False（漏判说话镜的代价低，
    # 误判非说话镜会被 SyncNet 低置信 → inconclusive 兜回，不罚分）
    assert lc.is_speaking_clip("远景 风景空镜 鸟鸣声 落日余晖") is False


# ---------- _band_rows ----------

def test_band_rows_drops_ok_keeps_warn_block_inconclusive():
    clips = [
        {"clip": "Clip_01", "offset_frames": 0, "confidence": 5.0},   # ok → drop
        {"clip": "Clip_02", "offset_frames": 3, "confidence": 5.0},   # warn
        {"clip": "Clip_03", "offset_frames": 8, "confidence": 5.0},   # block(measured) → verdict warn
        {"clip": "Clip_04", "offset_frames": 9, "confidence": 0.5},   # inconclusive → verdict ok, kept
    ]
    rows = lc._band_rows(clips, fps=25, warn_ms=80, block_ms=200, conf_floor=2.0)
    by_clip = {r["clip"]: r for r in rows}
    assert "Clip_01" not in by_clip
    assert by_clip["Clip_02"]["severity_measured"] == "warn"
    assert by_clip["Clip_02"]["verdict"] == "warn"
    assert by_clip["Clip_03"]["severity_measured"] == "block"
    assert by_clip["Clip_03"]["verdict"] == "warn"   # 封顶
    assert by_clip["Clip_04"]["severity_measured"] == "inconclusive"
    assert by_clip["Clip_04"]["verdict"] == "ok"


# ---------- offset_remediation（G2·cheap-fix-first 路由） ----------

def test_offset_remediation_only_for_real_offset():
    # 没测到真偏移（ok/inconclusive）→ 不乱给修法
    assert lc.offset_remediation("ok") is None
    assert lc.offset_remediation("inconclusive") is None
    # warn/block → cheap-fix-first 阶梯，路由到 video（lipsync_pass 所在 stage）
    for m in ("warn", "block"):
        rem = lc.offset_remediation(m)
        assert rem["return_to_stage"] == "video"
        assert "lipsync_pass" in rem["rerun_scope"]
        assert rem["remediation"][0]["action"] == "lipsync_pass"
        assert rem["remediation"][0]["cost"] == "cheap"
        assert rem["remediation"][1]["action"] == "regenerate_clip"
        assert rem["remediation"][1]["cost"] == "expensive"


def test_band_rows_attach_remediation_to_offsets():
    clips = [
        {"clip": "Clip_02", "offset_frames": 3, "confidence": 5.0},   # warn → has remediation
        {"clip": "Clip_04", "offset_frames": 9, "confidence": 0.5},   # inconclusive → no remediation
    ]
    rows = {r["clip"]: r for r in lc._band_rows(clips, 25, 80, 200, 2.0)}
    assert rows["Clip_02"]["return_to_stage"] == "video"
    assert rows["Clip_02"]["remediation"][0]["action"] == "lipsync_pass"
    assert "lipsync_pass" in rows["Clip_02"]["message"]
    assert "remediation" not in rows["Clip_04"]      # 低置信不乱给修法
    assert "return_to_stage" not in rows["Clip_04"]


# ---------- analyze 降级 + 外部报告消费 ----------

def test_analyze_degrades_without_backend(tmp_path):
    (tmp_path / "生产数据").mkdir()
    res = lc.analyze(str(tmp_path), "第1集")
    # 本测试环境一般无 SyncNet/外部报告 → 不可用，但绝不臆造分
    assert res["available"] is False
    assert res["precision"] == "none"
    assert res["notes"]


def test_analyze_consumes_external_offsets(tmp_path):
    si = tmp_path / "生产数据" / "score_inputs"
    si.mkdir(parents=True)
    (si / "第1集_syncnet_raw.json").write_text(json.dumps({
        "fps": 25,
        "clips": [
            {"clip": "Clip_01", "offset_frames": 1, "confidence": 5.0},  # ok
            {"clip": "Clip_02", "offset_frames": 7, "confidence": 5.0},  # measured block
        ],
    }), encoding="utf-8")
    res = lc.analyze(str(tmp_path), "第1集")
    assert res["available"] is True
    assert res["mode"] == "external_syncnet"
    assert res["precision"] == "full"
    clips = {r["clip"]: r for r in res["shots"]}
    assert "Clip_01" not in clips           # 同步良好不入清单
    assert clips["Clip_02"]["severity_measured"] == "block"
    assert clips["Clip_02"]["verdict"] == "warn"


# ---------- to_score_report ----------

def test_to_score_report_counts_measured_severity():
    res = {
        "available": True, "mode": "external_syncnet", "precision": "full",
        "shots": [
            {"clip": "Clip_02", "severity_measured": "warn", "verdict": "warn", "message": "x"},
            {"clip": "Clip_03", "severity_measured": "block", "verdict": "warn", "message": "y"},
        ],
    }
    rep = lc.to_score_report(res)
    assert rep["blocks"] == 1   # 机器分看真实严重档
    assert rep["warnings"] == 1
    assert rep["metrics"]["checked_clips"] == 2


def test_to_score_report_skip_when_unavailable():
    res = {"available": False, "mode": None, "precision": "none", "shots": [], "notes": ["缺 SyncNet"]}
    rep = lc.to_score_report(res)
    assert rep["blocks"] == 0 and rep["warnings"] == 0
    assert rep["evidence"] == ["缺 SyncNet"]


def test_write_score_report_roundtrips(tmp_path):
    res = {"available": True, "mode": "external_syncnet", "precision": "full", "shots": []}
    path = lc.write_score_report(str(tmp_path), "第1集", res)
    data = json.load(open(path, encoding="utf-8"))
    assert data["infos"] == 1   # 可用且无问题 → 通过证据


# ── 过同步上界 advisory（'higher Sync-C = better' 陷阱）──────────────────────────
def test_oversync_band_pure():
    assert lc.oversync_band(9.5) == "over_sync"          # 高于 GT 带 → 过同步
    assert lc.oversync_band(9.0) == "over_sync"          # 含等于上界
    assert lc.oversync_band(7.5) == "ok"                 # 真人 GT 带内 → 正常
    assert lc.oversync_band(1.0) == "ok"                 # 低置信不算过同步
    assert lc.oversync_band(12.0, ceiling=13.0) == "ok"  # 上界可调
    assert lc.oversync_band("x") == "ok"                 # 脏输入不炸


def test_band_rows_flags_oversync_even_when_offset_fine():
    # offset≈0（同步好）但置信爆表 11 → 旧逻辑判 ok 漏掉；现升 advisory warn 并标 oversync
    rows = lc._band_rows([{"clip": "Clip_03", "offset_frames": 0, "confidence": 11.0}],
                         fps=25.0, warn_ms=80.0, block_ms=200.0, conf_floor=2.0)
    assert len(rows) == 1
    r = rows[0]
    assert r["verdict"] == "warn" and r["oversync"] is True
    assert r["severity_measured"] == "ok"   # 偏移轴仍 ok（过同步与 offset 正交，不污染机器分严重档）
    assert "过同步" in r["message"]


def test_band_rows_no_oversync_when_inconclusive():
    # 低置信(inconclusive) 时置信不可信 → 不谈过同步（即便数值高也不报）
    rows = lc._band_rows([{"clip": "Clip_04", "offset_frames": 0, "confidence": 1.0}],
                         fps=25.0, warn_ms=80.0, block_ms=200.0, conf_floor=2.0)
    assert len(rows) == 1
    assert rows[0]["severity_measured"] == "inconclusive" and rows[0]["verdict"] == "ok"
    assert "oversync" not in rows[0]   # 低置信不标过同步


def test_to_score_report_counts_oversync():
    res = {"available": True, "mode": "external_syncnet", "precision": "full", "shots": [
        {"clip": "Clip_03", "severity_measured": "ok", "verdict": "warn", "oversync": True, "message": "x"},
    ]}
    rep = lc.to_score_report(res)
    assert rep["metrics"]["oversync"] == 1
    assert rep["blocks"] == 0 and rep["warnings"] == 0   # 过同步是 advisory，不进机器分严重档
