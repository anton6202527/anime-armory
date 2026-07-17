#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate VLM 裁决覆盖率告警单测（机检空转显式化·参照同仓漫画线 2026-07-17 整改）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import gate


def write_tasks(root: Path, tasks: list[dict]) -> None:
    out = root / "生产数据" / "vlm_judge" / "vlm_judge_tasks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"kind": "mv_vlm_judge_tasks", "tasks": tasks}, ensure_ascii=False), encoding="utf-8")


def make_root(tmp_path: Path) -> Path:
    (tmp_path / "分镜").mkdir(parents=True, exist_ok=True)
    (tmp_path / "分镜" / "clip_plan.json").write_text("{\"clips\": []}", encoding="utf-8")
    return tmp_path


def test_missing_task_pack_suggests_running_judge(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    warnings = gate._vlm_judge_warnings(str(root), "image")
    assert len(warnings) == 1 and "未生成 VLM 并排裁决任务包" in warnings[0]


def test_zero_adjudication_warns_idle(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_tasks(root, [{"task_id": "T1", "image": {"sha256": "a"}, "task_sha256": "s1"}])
    warnings = gate._vlm_judge_warnings(str(root), "image")
    assert any("空转" in w and "0 条有效裁决" in w for w in warnings)


def test_full_valid_coverage_is_quiet_and_suspect_surfaces(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_tasks(root, [{"task_id": "T1", "image": {"sha256": "a"}, "task_sha256": "s1"}])
    verdicts = root / "生产数据" / "vlm_judge" / "vlm_judge_verdicts.json"
    verdicts.write_text(json.dumps({"verdicts": [{
        "task_id": "T1", "image_sha256": "a", "task_sha256": "s1",
        "evaluator": {"model": "claude-fable-5", "version": "2026-07-17"},
        "scores": {"face": 5}, "verdict": "pass",
    }]}, ensure_ascii=False), encoding="utf-8")
    assert gate._vlm_judge_warnings(str(root), "image") == []

    verdicts.write_text(json.dumps({"verdicts": [{
        "task_id": "T1", "image_sha256": "a", "task_sha256": "s1",
        "evaluator": {"model": "claude-fable-5", "version": "2026-07-17"},
        "scores": {"face": 2}, "verdict": "suspect", "notes": "换脸",
    }]}, ensure_ascii=False), encoding="utf-8")
    warnings = gate._vlm_judge_warnings(str(root), "image")
    assert any("存疑 T1" in w for w in warnings)


def test_stale_verdict_counts_as_unadjudicated(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_tasks(root, [{"task_id": "T1", "image": {"sha256": "new"}, "task_sha256": "s2"}])
    verdicts = root / "生产数据" / "vlm_judge" / "vlm_judge_verdicts.json"
    verdicts.write_text(json.dumps({"verdicts": [{
        "task_id": "T1", "image_sha256": "old", "task_sha256": "s1",
        "evaluator": {"model": "claude-fable-5", "version": "2026-07-17"},
        "verdict": "pass",
    }]}, ensure_ascii=False), encoding="utf-8")
    warnings = gate._vlm_judge_warnings(str(root), "image")
    assert any("空转" in w for w in warnings)
