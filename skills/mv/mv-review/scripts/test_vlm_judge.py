#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV VLM 并排裁决合同单测（参照同仓漫画线 2026-07-17 机检空转整改）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import vlm_judge


def make_project(root: Path) -> None:
    (root / "分镜").mkdir(parents=True)
    (root / "出图" / "段落" / "图片").mkdir(parents=True)
    (root / "设定" / "参考").mkdir(parents=True)
    (root / "出图" / "段落" / "图片" / "Clip_001.png").write_bytes(b"img-001")
    (root / "出图" / "段落" / "图片" / "Clip_001_end.png").write_bytes(b"img-001-end")
    (root / "出图" / "段落" / "图片" / "Clip_002.png").write_bytes(b"img-002")
    (root / "设定" / "参考" / "lead_front.png").write_bytes(b"ref-front")
    clips = [
        {
            "clip_id": "Clip_001",
            "image_path": "出图/段落/图片/Clip_001.png",
            "end_frame_path": "出图/段落/图片/Clip_001_end.png",
            "need_end_frame": True,
            "reference_inputs": [{"path": "设定/参考/lead_front.png", "use": "lead_identity"}],
        },
        {
            "clip_id": "Clip_002",
            "image_path": "出图/段落/图片/Clip_002.png",
            "need_end_frame": False,
            "reference_inputs": [{"path": "设定/参考/lead_front.png", "use": "lead_identity"}],
        },
        {
            "clip_id": "Clip_003",
            "image_path": "出图/段落/图片/Clip_003.png",  # 未出图：不该生成任务
            "reference_inputs": [{"path": "设定/参考/lead_front.png", "use": "lead_identity"}],
        },
    ]
    (root / "分镜" / "clip_plan.json").write_text(
        json.dumps({"kind": "mv_clip_plan", "clips": clips}, ensure_ascii=False), encoding="utf-8")


def valid_verdict_for(task: dict) -> dict:
    return {
        "task_id": task["task_id"],
        "image_sha256": task["image"]["sha256"],
        "task_sha256": task["task_sha256"],
        "references_sha256": task["references_sha256"],
        "evaluator": {"model": "claude-fable-5", "version": "2026-07-17"},
        "scores": {"face": 5},
        "verdict": "pass",
        "notes": "ok",
    }


def test_build_tasks_covers_identity_and_seam_only_for_generated_images(tmp_path: Path) -> None:
    make_project(tmp_path)
    vlm_judge.write_tasks(str(tmp_path))
    payload = json.loads(Path(vlm_judge.tasks_path(str(tmp_path))).read_text(encoding="utf-8"))
    ids = {t["task_id"] for t in payload["tasks"]}
    assert ids == {"Clip_001__lead_identity", "Clip_002__lead_identity", "Clip_001__Clip_002__seam"}
    assert payload["inputs_sha256"]["分镜/clip_plan.json"]
    for task in payload["tasks"]:
        assert task["image"]["sha256"] and task["task_sha256"] and task["references_sha256"]


def test_verdict_contract_rejects_stale_and_unaccountable_records(tmp_path: Path) -> None:
    make_project(tmp_path)
    vlm_judge.write_tasks(str(tmp_path))
    tasks = json.loads(Path(vlm_judge.tasks_path(str(tmp_path))).read_text(encoding="utf-8"))["tasks"]
    good = valid_verdict_for(tasks[0])
    no_evaluator = dict(valid_verdict_for(tasks[1]))
    no_evaluator.pop("evaluator")
    Path(vlm_judge.verdicts_path(str(tmp_path))).write_text(
        json.dumps({"verdicts": [good, no_evaluator]}, ensure_ascii=False), encoding="utf-8")
    valid = vlm_judge.load_verdicts(str(tmp_path))
    assert set(valid) == {tasks[0]["task_id"]}

    # clip 重抽（图片内容变化）后旧裁决自动作废。
    (tmp_path / "出图" / "段落" / "图片" / "Clip_001.png").write_bytes(b"img-001-regen")
    vlm_judge.write_tasks(str(tmp_path))
    assert vlm_judge.load_verdicts(str(tmp_path)) == {}


def test_suspect_and_status(tmp_path: Path) -> None:
    make_project(tmp_path)
    vlm_judge.write_tasks(str(tmp_path))
    tasks = json.loads(Path(vlm_judge.tasks_path(str(tmp_path))).read_text(encoding="utf-8"))["tasks"]
    low = valid_verdict_for(tasks[0])
    low["scores"] = {"face": 2}
    Path(vlm_judge.verdicts_path(str(tmp_path))).write_text(
        json.dumps({"verdicts": [low]}, ensure_ascii=False), encoding="utf-8")
    suspects = vlm_judge.suspect_verdicts(str(tmp_path))
    assert len(suspects) == 1 and suspects[0]["low_scores"] == ["face=2"]
    status = vlm_judge.judge_status(str(tmp_path))
    assert status["task_count"] == 3 and status["verdict_count"] == 1
