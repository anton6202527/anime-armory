#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H1 回归：gate_receipt 模块不可加载时，受闸列 ✅ 必须 fail-closed（不再静默放行）。

Run: cd skills/n2d && python3 -m pytest test_progress_receipt_failclosed.py
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import progress  # noqa: E402


def _break_gate_receipt(monkeypatch):
    # sys.modules[name]=None → `from gate_receipt import ...` 抛 ImportError（模拟模块不可加载）
    monkeypatch.setitem(sys.modules, "gate_receipt", None)


def test_gated_done_failclosed_when_module_missing(tmp_path, monkeypatch):
    _break_gate_receipt(monkeypatch)
    monkeypatch.delenv("N2D_PROGRESS_ALLOW_UNVERIFIED", raising=False)
    with pytest.raises(SystemExit) as ei:
        progress._verify_gate_receipt(str(tmp_path), "第1集", "出图", "✅")
    assert ei.value.code == 2  # 受闸列 done + 无凭据模块 + 无 override → 拒绝


def test_gated_done_override_writes_waiver(tmp_path, monkeypatch):
    _break_gate_receipt(monkeypatch)
    monkeypatch.setenv("N2D_PROGRESS_ALLOW_UNVERIFIED", "1")
    progress._verify_gate_receipt(str(tmp_path), "第1集", "成片", "✅")  # 不应 raise
    led = tmp_path / "生产数据" / "progress_unverified_waivers.jsonl"
    assert led.exists(), "override 路径必须留痕欠债"
    rec = json.loads(led.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert rec["column"] == "成片"
    assert rec["gate_stage"] == "compose"          # schema 兼容 unresolved_waivers 的 (episode,gate_stage) 键
    assert rec["code"] == "gate_receipt_unavailable"


def test_non_gated_column_passes_when_module_missing(tmp_path, monkeypatch):
    _break_gate_receipt(monkeypatch)
    monkeypatch.delenv("N2D_PROGRESS_ALLOW_UNVERIFIED", raising=False)
    # 非受闸列（纯文本 prompt 列）即使模块缺失也照常放行，不误伤
    progress._verify_gate_receipt(str(tmp_path), "第1集", "出图prompt", "✅")


def test_gated_non_done_passes_when_module_missing(tmp_path, monkeypatch):
    _break_gate_receipt(monkeypatch)
    monkeypatch.delenv("N2D_PROGRESS_ALLOW_UNVERIFIED", raising=False)
    # 受闸列但非完成态（rough/分数）不受凭据约束
    progress._verify_gate_receipt(str(tmp_path), "第1集", "出图", "⏳rough")


def test_failclose_constants_match_gate_receipt():
    # 反漂移：兜底常量必须与 gate_receipt 单一真值源一致
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_lib"))
    import gate_receipt as gr
    assert progress._GATED_COLUMN_STAGE_FALLBACK == gr.ENFORCED_COLUMN_GATE_STAGE
    assert progress._PROGRESS_ALLOW_ENV == gr.ALLOW_ENV
    assert progress._UNVERIFIED_WAIVER_LEDGER == gr.WAIVER_LEDGER
