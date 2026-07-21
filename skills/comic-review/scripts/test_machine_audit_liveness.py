#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-07-17 机检空转回归：VLM 0 裁决与 CCIP 降级必须出 warn finding，不准静默 pass。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import gate


def write_tasks_file(root: Path, chapter: str, count: int) -> None:
    path = root / "生产数据" / f"comic_vlm_judge_tasks_{chapter}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "tasks": [
                    {"task_id": f"T{i}", "panel": {"sha256": "x"}, "task_sha256": f"ts{i}", "references_sha256": {}}
                    for i in range(count)
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def codes(findings):
    return {item["code"] for item in findings}


def test_unadjudicated_vlm_tasks_and_missing_ccip_warn(tmp_path: Path) -> None:
    write_tasks_file(tmp_path, "第1话", 3)
    findings: list = []
    notes: list = []
    gate.check_machine_audit_liveness(tmp_path, "第1话", {"capabilities": {"pillow": True, "ccip": False}}, findings, notes)
    got = codes(findings)
    assert "vlm_judge_unadjudicated" in got
    assert "identity_similarity_engine_degraded" in got
    assert all(item["severity"] == "warn" for item in findings)


def test_full_vlm_coverage_with_ccip_is_quiet(tmp_path: Path) -> None:
    write_tasks_file(tmp_path, "第1话", 2)
    verdicts = {
        "verdicts": [
            {
                "task_id": f"T{i}",
                "panel_sha256": "x",
                "task_sha256": f"ts{i}",
                "references_sha256": {},
                "verdict": "pass",
                "evaluator": {"model": "claude-fable-5", "version": "2026-07-17"},
            }
            for i in range(2)
        ]
    }
    (tmp_path / "生产数据" / "comic_vlm_judge_verdicts_第1话.json").write_text(json.dumps(verdicts), encoding="utf-8")
    findings: list = []
    notes: list = []
    gate.check_machine_audit_liveness(tmp_path, "第1话", {"capabilities": {"pillow": True, "ccip": True}}, findings, notes)
    assert findings == []
    assert any("vlm judge coverage: 2/2" in note for note in notes)


def test_full_vlm_coverage_downgrades_missing_ccip_to_info(tmp_path: Path) -> None:
    write_tasks_file(tmp_path, "第1话", 2)
    verdicts = {
        "verdicts": [
            {
                "task_id": f"T{i}", "panel_sha256": "x", "task_sha256": f"ts{i}",
                "references_sha256": {}, "verdict": "pass",
                "evaluator": {"model": "multimodal-reviewer", "version": "2026-07-18"},
            }
            for i in range(2)
        ]
    }
    (tmp_path / "生产数据" / "comic_vlm_judge_verdicts_第1话.json").write_text(
        json.dumps(verdicts), encoding="utf-8"
    )
    findings: list = []
    notes: list = []
    gate.check_machine_audit_liveness(
        tmp_path, "第1话", {"capabilities": {"pillow": True, "ccip": False}}, findings, notes
    )
    assert len(findings) == 1
    assert findings[0]["code"] == "identity_similarity_engine_degraded"
    assert findings[0]["severity"] == "info"


def test_hard_gate_with_no_ccip_and_zero_verdicts_blocks(tmp_path: Path) -> None:
    """硬闸开启 + CCIP 不可用 + 0 裁决 = 身份轴完全无机检，必须 block。"""
    write_tasks_file(tmp_path, "第1话", 3)
    (tmp_path / "_设置.md").write_text("- 角色一致性硬闸: 开启\n", encoding="utf-8")
    findings: list = []
    gate.check_machine_audit_liveness(tmp_path, "第1话", {"capabilities": {"ccip": False}}, findings, [])
    unadjudicated = [item for item in findings if item["code"] == "vlm_judge_unadjudicated"]
    assert unadjudicated and unadjudicated[0]["severity"] == "block"


def test_hard_gate_with_live_ccip_keeps_warn(tmp_path: Path) -> None:
    """CCIP 活着时身份轴有机检，0 裁决只 warn 不 block。"""
    write_tasks_file(tmp_path, "第1话", 3)
    (tmp_path / "_设置.md").write_text("- 角色一致性硬闸: 开启\n", encoding="utf-8")
    findings: list = []
    gate.check_machine_audit_liveness(tmp_path, "第1话", {"capabilities": {"ccip": True}}, findings, [])
    unadjudicated = [item for item in findings if item["code"] == "vlm_judge_unadjudicated"]
    assert unadjudicated and unadjudicated[0]["severity"] == "warn"
