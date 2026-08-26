#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vlm_adjudicate 回写校验与出队的封闭测试。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import vlm_adjudicate
import vlm_judge


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "作品"
    (root / "生产数据").mkdir(parents=True)
    panel_dir = root / "出图" / "第1话" / "panels"
    panel_dir.mkdir(parents=True)
    (panel_dir / "P001.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
    ref_dir = root / "出图" / "共享" / "图片"
    ref_dir.mkdir(parents=True)
    (ref_dir / "CHAR_A__front.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 100)
    return root


def make_tasks(root: Path) -> dict:
    panel_path = root / "出图" / "第1话" / "panels" / "P001.png"
    ref_rel = "出图/共享/图片/CHAR_A__front.png"
    task = {
        "task_id": "P001__CHAR_A__character",
        "axis": "character_identity",
        "panel": {
            "panel_id": "P001",
            "path": "出图/第1话/panels/P001.png",
            "sha256": vlm_judge.file_sha256(panel_path),
        },
        "subject": "CHAR_A",
        "references": [ref_rel],
        "references_sha256": {ref_rel: vlm_judge.file_sha256(root / ref_rel)},
        "question": "同一角色吗",
        "required_score_keys": list(vlm_judge.AXIS_SCORE_KEYS["character_identity"]),
        "required_evidence": {"region_required": True},
    }
    task["task_sha256"] = vlm_judge.task_sha256(task)
    payload = {"schema_version": 2, "kind": "comic_vlm_judge_tasks", "chapter": "第1话", "tasks": [task]}
    vlm_judge.tasks_path(root, "第1话").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return task


def good_record(task: dict) -> dict:
    return {
        "task_id": task["task_id"],
        "panel_sha256": task["panel"]["sha256"],
        "task_sha256": task["task_sha256"],
        "references_sha256": task["references_sha256"],
        "evaluator": {"model": "claude-fable-5", "version": "2026-07-20", "reviewed_at": "2026-07-20T00:00:00"},
        "scores": {"face": 5, "outfit": 4, "build": 5, "form_expression_state": 5},
        "verdict": "pass",
        "notes": "脸型发型一致",
        "evidence": [{"path": task["panel"]["path"], "sha256": task["panel"]["sha256"], "region": {"bbox": [0, 0, 1, 1]}}],
    }


def test_submit_accepts_valid_and_counts_coverage(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)
    task = make_tasks(root)
    submission = tmp_path / "sub.json"
    submission.write_text(json.dumps({"verdicts": [good_record(task)]}), encoding="utf-8")
    assert vlm_adjudicate.cmd_submit(root, "第1话", submission) == 0
    status = vlm_judge.judge_status(root, "第1话")
    assert status["verdict_count"] == 1 == status["task_count"]
    assert vlm_adjudicate.pending_tasks(root, "第1话") == []


def test_submit_rejects_stale_panel_sha(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)
    task = make_tasks(root)
    record = good_record(task)
    record["panel_sha256"] = "0" * 64  # 模拟该格已重抽
    submission = tmp_path / "sub.json"
    submission.write_text(json.dumps({"verdicts": [record]}), encoding="utf-8")
    assert vlm_adjudicate.cmd_submit(root, "第1话", submission) == 2
    assert vlm_judge.judge_status(root, "第1话")["verdict_count"] == 0, "整批拒绝，不得半写"


def test_submit_rejects_out_of_range_scores_and_missing_evaluator(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    task = make_tasks(root)
    record = good_record(task)
    record["scores"] = {"face": 9}
    record["evaluator"] = {"model": "", "version": ""}
    submission = tmp_path / "sub.json"
    submission.write_text(json.dumps({"verdicts": [record]}), encoding="utf-8")
    assert vlm_adjudicate.cmd_submit(root, "第1话", submission) == 2


def test_queue_lists_pending_with_abs_paths(tmp_path: Path, capsys) -> None:
    root = make_project(tmp_path)
    make_tasks(root)
    assert vlm_adjudicate.cmd_queue(root, "第1话", 0, 0, "") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pending_total"] == 1
    task = payload["tasks"][0]
    assert Path(task["panel"]["abs_path"]).is_file()
    assert all(Path(p).is_file() for p in task["references_abs"])
