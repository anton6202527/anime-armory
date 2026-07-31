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
    """CCIP 活着且只有角色轴任务时，0 裁决只 warn 不 block（角色轴有 CCIP 兜底）。"""
    write_tasks_file(tmp_path, "第1话", 3)
    (tmp_path / "_设置.md").write_text("- 角色一致性硬闸: 开启\n", encoding="utf-8")
    findings: list = []
    gate.check_machine_audit_liveness(tmp_path, "第1话", {"capabilities": {"ccip": True}}, findings, [])
    unadjudicated = [item for item in findings if item["code"] == "vlm_judge_unadjudicated"]
    assert unadjudicated and unadjudicated[0]["severity"] == "warn"


def write_axis_tasks_file(root: Path, chapter: str, axis_counts: dict[str, int]) -> None:
    """按轴构造任务包：judge_status 会据 axis 字段聚合 by_axis。"""
    path = root / "生产数据" / f"comic_vlm_judge_tasks_{chapter}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tasks = []
    i = 0
    for axis, count in axis_counts.items():
        for _ in range(count):
            tasks.append({"task_id": f"T{i}", "axis": axis, "panel": {"sha256": "x"},
                          "task_sha256": f"ts{i}", "references_sha256": {}})
            i += 1
    path.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False), encoding="utf-8")


def test_hard_gate_live_ccip_blind_background_axis_blocks(tmp_path: Path) -> None:
    """聊斋实证回归：硬闸开启 + CCIP 已装，但 background/location 轴 0 裁决 —— CCIP 覆盖不到场景，
    这些轴完全空转，「背景该是虎妖画成别的生物」类漂移必须 block，不准因 CCIP 活着降 warn。"""
    write_axis_tasks_file(tmp_path, "第1话", {"character_identity": 32, "background_continuity": 14, "location_identity": 5})
    (tmp_path / "_设置.md").write_text("- 角色一致性硬闸: 开启\n", encoding="utf-8")
    findings: list = []
    gate.check_machine_audit_liveness(tmp_path, "第1话", {"capabilities": {"pillow": True, "ccip": True}}, findings, [])
    unadjudicated = [item for item in findings if item["code"] == "vlm_judge_unadjudicated"]
    assert unadjudicated and unadjudicated[0]["severity"] == "block"
    assert "background_continuity" in unadjudicated[0]["reason"] or "location_identity" in unadjudicated[0]["reason"]


def test_hard_gate_partial_coverage_but_prop_axis_blind_blocks(tmp_path: Path) -> None:
    """角色轴全裁决、但道具轴一条没裁决：整体覆盖过半看着没事，实则道具轴空转，硬闸下 block。"""
    write_axis_tasks_file(tmp_path, "第1话", {"character_identity": 2, "prop_identity": 3})
    (tmp_path / "_设置.md").write_text("- 角色一致性硬闸: 开启\n", encoding="utf-8")
    verdicts = {"verdicts": [
        {"task_id": "T0", "panel_sha256": "x", "task_sha256": "ts0", "references_sha256": {},
         "verdict": "pass", "evaluator": {"model": "m", "version": "v"}},
        {"task_id": "T1", "panel_sha256": "x", "task_sha256": "ts1", "references_sha256": {},
         "verdict": "pass", "evaluator": {"model": "m", "version": "v"}},
    ]}
    (tmp_path / "生产数据" / "comic_vlm_judge_verdicts_第1话.json").write_text(json.dumps(verdicts), encoding="utf-8")
    findings: list = []
    gate.check_machine_audit_liveness(tmp_path, "第1话", {"capabilities": {"pillow": True, "ccip": True}}, findings, [])
    blind = [item for item in findings if item["code"] == "vlm_judge_axis_blind"]
    assert blind and blind[0]["severity"] == "block"
    assert "prop_identity" in blind[0]["reason"]


def test_soft_gate_blind_axis_stays_warn(tmp_path: Path) -> None:
    """硬闸关闭时不升 block：advisory 语义，0 裁决仍是 warn。"""
    write_axis_tasks_file(tmp_path, "第1话", {"background_continuity": 5})
    findings: list = []
    gate.check_machine_audit_liveness(tmp_path, "第1话", {"capabilities": {"pillow": True, "ccip": True}}, findings, [])
    unadjudicated = [item for item in findings if item["code"] == "vlm_judge_unadjudicated"]
    assert unadjudicated and unadjudicated[0]["severity"] == "warn"
