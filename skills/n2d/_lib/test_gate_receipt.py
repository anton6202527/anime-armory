#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for gate_receipt — the ✅-must-have-fresh-evidence linchpin.

Run from this directory:
    cd skills/n2d/_lib && python3 -m pytest test_gate_receipt.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gate_receipt as gr
from skill_snapshot import artifact_fingerprint


def _write_image(root, ep="第1集", png_rel="出图/第1集/图片/01.png", png_bytes=b"PNG-A"):
    """Lay down one PNG and a gate-findings receipt fingerprinting it."""
    png_abs = os.path.join(root, png_rel)
    os.makedirs(os.path.dirname(png_abs), exist_ok=True)
    with open(png_abs, "wb") as fh:
        fh.write(png_bytes)
    return png_rel


def _write_receipt(root, stage="image", ep="第1集", blocks=0, files=None, with_fp=True):
    files = files or ["出图/第1集/图片/01.png"]
    pdir = os.path.join(root, gr.PRODUCTION_DIRNAME)
    os.makedirs(pdir, exist_ok=True)
    payload = {
        "kind": "n2d_consistency_findings",
        "gate_stage": stage,
        "summary": {"severity": {"block": blocks, "warn": 0, "info": 0}},
        "findings": [],
    }
    if with_fp:
        payload["inputs_fingerprint"] = artifact_fingerprint(root, files)
    path = gr.gate_findings_path(root, ep, stage)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    return path


def test_non_gated_column_passes(tmp_path):
    v = gr.check_advance(str(tmp_path), "第1集", "配音", "✅")
    assert v.ok and not v.enforced and v.code == "not_gated"


def test_non_done_value_passes(tmp_path):
    # partial 出图 count should not require a receipt
    v = gr.check_advance(str(tmp_path), "第1集", "出图", "3/8")
    assert v.ok and v.code == "not_complete"


def test_missing_receipt_blocks(tmp_path):
    v = gr.check_advance(str(tmp_path), "第1集", "出图", "✅")
    assert not v.ok and v.enforced and v.code == "no_receipt"


def test_failed_gate_blocks(tmp_path):
    root = str(tmp_path)
    _write_image(root)
    _write_receipt(root, blocks=2)
    v = gr.check_advance(root, "第1集", "出图", "✅")
    assert not v.ok and v.code == "gate_failed"


def test_fresh_passing_receipt_allows(tmp_path):
    root = str(tmp_path)
    _write_image(root)
    _write_receipt(root, blocks=0)
    v = gr.check_advance(root, "第1集", "出图", "✅")
    assert v.ok and v.enforced and v.code == "verified"


def test_stale_receipt_blocks(tmp_path):
    root = str(tmp_path)
    _write_image(root, png_bytes=b"PNG-A")
    _write_receipt(root, blocks=0)
    # Re-render the PNG after the gate ran → receipt is now stale.
    _write_image(root, png_bytes=b"PNG-B-REDRAWN")
    v = gr.check_advance(root, "第1集", "出图", "✅")
    assert not v.ok and v.code == "stale"


def test_fingerprintless_receipt_blocks(tmp_path):
    root = str(tmp_path)
    _write_image(root)
    _write_receipt(root, blocks=0, with_fp=False)
    v = gr.check_advance(root, "第1集", "出图", "✅")
    assert not v.ok and v.code == "unverifiable"


def test_x_of_y_complete_requires_receipt(tmp_path):
    # 8/8 counts as done → must be backed by evidence
    root = str(tmp_path)
    v = gr.check_advance(root, "第1集", "出图", "8/8")
    assert not v.ok and v.code == "no_receipt"


def test_compose_and_review_are_enforced(tmp_path):
    assert gr.ENFORCED_COLUMN_GATE_STAGE["成片"] == "compose"
    assert gr.ENFORCED_COLUMN_GATE_STAGE["验收"] == "review"
    v = gr.check_advance(str(tmp_path), "第1集", "成片", "✅")
    assert not v.ok and v.stage == "compose"


def test_review_completion_uses_only_canonical_acceptance(monkeypatch, tmp_path):
    monkeypatch.setattr(
        gr.acceptance_contract,
        "check_acceptance",
        lambda root, ep: {"status": "fail", "issues": ["canonical acceptance receipt missing"]},
    )
    rejected = gr.check_advance(str(tmp_path), "第1集", "验收", "✅")
    assert not rejected.ok and rejected.code == "canonical_acceptance_invalid"

    monkeypatch.setattr(
        gr.acceptance_contract,
        "check_acceptance",
        lambda root, ep: {"status": "pass", "receipt_id": "receipt-1", "issues": []},
    )
    accepted = gr.check_advance(str(tmp_path), "第1集", "验收", "✅")
    assert accepted.ok and accepted.code == "canonical_acceptance_verified"


def test_unresolved_waiver_clears_after_fresh_receipt(tmp_path):
    root = str(tmp_path)
    v = gr.check_advance(root, "第1集", "出图", "✅")
    gr.record_waiver(root, "第1集", "出图", v)
    assert len(gr.unresolved_waivers(root)) == 1
    # Lay down a fresh passing receipt → the same (episode, stage) debt is销账.
    _write_image(root)
    _write_receipt(root, blocks=0)
    assert gr.unresolved_waivers(root) == []


def test_unresolved_waiver_dedups_per_episode_stage(tmp_path):
    root = str(tmp_path)
    v = gr.check_advance(root, "第1集", "出图", "✅")
    gr.record_waiver(root, "第1集", "出图", v)
    gr.record_waiver(root, "第1集", "出图", v)  # same (ep, stage) twice
    assert len(gr.unresolved_waivers(root)) == 1  # collapses to one debt


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))


# ── H3: reconcile_progress（交付侧对账，抓绕过 do_set 的带外 ✅）──
def test_reconcile_flags_unbacked_progress_check(tmp_path):
    root = str(tmp_path)
    # 进度表：出图标 ✅ 但没有任何 gate 凭据（模拟手写/带外 ✅）
    os.makedirs(root, exist_ok=True)
    prog = (
        "| 集 | 出图prompt | 出图 | 视频 | 成片 | 验收 |\n"
        "|---|---|---|---|---|---|\n"
        "| 第1集 | ✅ | ✅ | ⬜ | ⬜ | ⬜ |\n"
    )
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as fh:
        fh.write(prog)
    viol = gr.reconcile_progress(root, "第1集")
    cols = {v["column"] for v in viol}
    assert "出图" in cols                      # ✅ 无凭据 → violation
    assert all(v["gate_stage"] for v in viol)  # 带 gate_stage
    # 出图prompt 非受闸列、视频/成片非 done → 不报
    assert "出图prompt" not in cols and "视频" not in cols


def test_reconcile_passes_when_receipt_fresh(tmp_path):
    root = str(tmp_path)
    _write_image(root)    # 落 PNG
    _write_receipt(root)  # 落新鲜+绿 image 凭据（指纹覆盖该 PNG）
    prog = (
        "| 集 | 出图 | 视频 | 成片 | 验收 |\n"
        "|---|---|---|---|---|\n"
        "| 第1集 | ✅ | ⬜ | ⬜ | ⬜ |\n"
    )
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as fh:
        fh.write(prog)
    viol = gr.reconcile_progress(root, "第1集")
    assert not any(v["column"] == "出图" for v in viol)  # 有新鲜凭据 → 不报


def test_reconcile_no_progress_file_is_empty(tmp_path):
    assert gr.reconcile_progress(str(tmp_path), "第1集") == []
