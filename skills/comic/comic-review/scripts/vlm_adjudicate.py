#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VLM 三轴判定的执行编排：出队待裁决任务、校验并回写裁决。

vlm_judge.py 只产任务包；历史上没有任何执行编排，导致"137 条任务 0 条裁决"
的机检空转。本脚本补上闭环的两半：

1. ``queue``  —— 输出未裁决任务（绝对路径、分批），供多模态 agent 逐条看图打分。
2. ``submit`` —— 接收 agent 产出的裁决 JSON，逐条校验 SHA 绑定与 schema 后
   合并写回 verdicts 文件；非法记录整批拒绝并逐条说明原因，绝不半写。

裁决协议（每条记录）见任务包 ``verdict_schema``；本脚本强制：
- task_id 存在于当前任务包；
- panel_sha256 / task_sha256 / references_sha256 与当前任务包完全一致
  （重抽过的格必须先重建任务包再裁决）；
- evaluator.model / evaluator.version 非空；
- scores 数值均在 1-5；verdict ∈ {pass, suspect}。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import vlm_judge


def pending_tasks(root: Path, chapter: str) -> list[dict[str, Any]]:
    tasks_payload = vlm_judge.load_json(vlm_judge.tasks_path(root, chapter), {})
    tasks = tasks_payload.get("tasks") or [] if isinstance(tasks_payload, dict) else []
    done = vlm_judge.load_verdicts(root, chapter)
    return [
        task
        for task in tasks
        if isinstance(task, dict) and str(task.get("task_id")) not in done
    ]


def cmd_queue(root: Path, chapter: str, batch_size: int, batch_index: int, axis: str) -> int:
    pending = pending_tasks(root, chapter)
    if axis:
        pending = [task for task in pending if str(task.get("axis")) == axis]
    total = len(pending)
    if batch_size > 0:
        start = batch_index * batch_size
        pending = pending[start : start + batch_size]
    resolved = []
    for task in pending:
        item = dict(task)
        panel = dict(item.get("panel") or {})
        panel["abs_path"] = str(vlm_judge.resolve_path(root, str(panel.get("path") or "")))
        item["panel"] = panel
        item["references_abs"] = [
            str(vlm_judge.resolve_path(root, str(ref))) for ref in item.get("references") or []
        ]
        resolved.append(item)
    print(
        json.dumps(
            {
                "chapter": chapter,
                "pending_total": total,
                "batch_size": batch_size,
                "batch_index": batch_index,
                "batch_count": len(resolved),
                "verdict_file": vlm_judge.rel(root, vlm_judge.verdicts_path(root, chapter)),
                "submit_hint": (
                    "把裁决记录写成 {\"verdicts\": [...]} 的 JSON 文件后运行 "
                    "vlm_adjudicate.py <root> --chapter <章> submit <file> 合并回写"
                ),
                "tasks": resolved,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def validate_record(record: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(record.get("panel_sha256") or "") != contract["panel_sha256"]:
        errors.append("panel_sha256 与当前任务包不一致（该格可能已重抽，先重建任务包）")
    if str(record.get("task_sha256") or "") != contract["task_sha256"]:
        errors.append("task_sha256 与当前任务包不一致")
    refs = record.get("references_sha256")
    if not isinstance(refs, dict) or refs != contract["references_sha256"]:
        errors.append("references_sha256 缺失或与当前任务包不一致")
    evaluator = record.get("evaluator") if isinstance(record.get("evaluator"), dict) else {}
    if not str(evaluator.get("model") or "").strip() or not str(evaluator.get("version") or "").strip():
        errors.append("evaluator.model / evaluator.version 必填")
    reviewed_at = str(evaluator.get("reviewed_at") or "").strip()
    try:
        datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError:
        errors.append("evaluator.reviewed_at 必须是 ISO-8601")
    scores = record.get("scores")
    if not isinstance(scores, dict) or not scores:
        errors.append("scores 必须是非空对象")
    else:
        required_keys = set(contract.get("required_score_keys") or [])
        if set(scores) != required_keys:
            errors.append("scores 必须精确覆盖本轴 required_score_keys=" + ",".join(sorted(required_keys)))
        for key, value in scores.items():
            if not isinstance(value, (int, float)) or not 1 <= float(value) <= 5:
                errors.append(f"scores.{key} 必须是 1-5 数值")
    if str(record.get("verdict") or "").lower() not in {"pass", "suspect"}:
        errors.append("verdict 必须是 pass 或 suspect")
    if not str(record.get("notes") or "").strip():
        errors.append("notes 必填，必须说明可见证据")
    evidence = record.get("evidence") if isinstance(record.get("evidence"), list) else []
    if not evidence:
        errors.append("evidence 必须至少绑定一个当前 panel/reference path+SHA")
    allowed = contract.get("allowed_evidence") if isinstance(contract.get("allowed_evidence"), dict) else {}
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"evidence[{index}] 必须是对象")
            continue
        path = str(item.get("path") or "")
        sha = str(item.get("sha256") or "")
        if not path or allowed.get(path) != sha:
            errors.append(f"evidence[{index}] path/SHA 不属于当前任务")
    if contract.get("region_required") and not any(
        isinstance(item, dict) and item.get("region") not in (None, "", {}, []) for item in evidence
    ):
        errors.append("该主体任务要求 bbox/mask/occlusion region 证据")
    return errors


def cmd_submit(root: Path, chapter: str, submission_path: Path) -> int:
    try:
        submission = json.loads(submission_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[err] 无法读取裁决文件 {submission_path}: {exc}", file=sys.stderr)
        return 2
    records = submission.get("verdicts") if isinstance(submission, dict) else None
    if not isinstance(records, list) or not records:
        print("[err] 裁决文件必须是 {\"verdicts\": [...]} 且非空", file=sys.stderr)
        return 2

    tasks_payload = vlm_judge.load_json(vlm_judge.tasks_path(root, chapter), {})
    contracts = {
        str(task.get("task_id")): {
            "panel_sha256": str((task.get("panel") or {}).get("sha256") or ""),
            "task_sha256": str(task.get("task_sha256") or ""),
            "references_sha256": task.get("references_sha256")
            if isinstance(task.get("references_sha256"), dict)
            else {},
            "required_score_keys": list(task.get("required_score_keys") or []),
            "allowed_evidence": {
                str((task.get("panel") or {}).get("path") or ""): str((task.get("panel") or {}).get("sha256") or ""),
                **(
                    task.get("references_sha256")
                    if isinstance(task.get("references_sha256"), dict)
                    else {}
                ),
            },
            "region_required": bool((task.get("required_evidence") or {}).get("region_required")),
        }
        for task in (tasks_payload.get("tasks") or [])
        if isinstance(task, dict)
    }

    failures: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            failures.append(f"#{index}: 不是对象")
            continue
        task_id = str(record.get("task_id") or "")
        contract = contracts.get(task_id)
        if not contract:
            failures.append(f"#{index} {task_id or '<缺 task_id>'}: 不在当前任务包")
            continue
        for error in validate_record(record, contract):
            failures.append(f"#{index} {task_id}: {error}")
    if failures:
        for line in failures:
            print(f"[err] {line}", file=sys.stderr)
        print(f"[err] {len(failures)} 条问题，整批拒绝（不做半写合并）", file=sys.stderr)
        return 2

    verdicts_file = vlm_judge.verdicts_path(root, chapter)
    existing = vlm_judge.load_json(verdicts_file, {})
    existing_records = existing.get("verdicts") if isinstance(existing, dict) else None
    merged: dict[str, dict[str, Any]] = {}
    for record in existing_records or []:
        if isinstance(record, dict) and record.get("task_id"):
            merged[str(record["task_id"])] = record
    for record in records:
        merged[str(record["task_id"])] = record

    payload = {
        "schema_version": 2,
        "kind": "comic_vlm_judge_verdicts",
        "chapter": chapter,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "verdicts": list(merged.values()),
    }
    verdicts_file.parent.mkdir(parents=True, exist_ok=True)
    verdicts_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = vlm_judge.judge_status(root, chapter)
    print(
        f"[ok] 合并 {len(records)} 条裁决 → {vlm_judge.rel(root, verdicts_file)}；"
        f"当前覆盖 {status['verdict_count']}/{status['task_count']}"
    )
    return 0


def cmd_status(root: Path, chapter: str) -> int:
    status = vlm_judge.judge_status(root, chapter)
    tasks_payload = vlm_judge.load_json(vlm_judge.tasks_path(root, chapter), {})
    done = vlm_judge.load_verdicts(root, chapter)
    by_axis: dict[str, dict[str, int]] = {}
    for task in tasks_payload.get("tasks") or [] if isinstance(tasks_payload, dict) else []:
        if not isinstance(task, dict):
            continue
        axis = str(task.get("axis") or "unknown")
        bucket = by_axis.setdefault(axis, {"tasks": 0, "verdicts": 0})
        bucket["tasks"] += 1
        if str(task.get("task_id")) in done:
            bucket["verdicts"] += 1
    status["by_axis"] = by_axis
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="VLM 三轴判定执行编排（出队/回写/状态）")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    sub = parser.add_subparsers(dest="command", required=True)
    queue_parser = sub.add_parser("queue", help="输出未裁决任务（绝对路径），供多模态 agent 看图打分")
    queue_parser.add_argument("--batch-size", type=int, default=0, help="每批任务数；0 表示全部")
    queue_parser.add_argument("--batch-index", type=int, default=0)
    queue_parser.add_argument("--axis", default="", choices=("", *vlm_judge.AXES))
    submit_parser = sub.add_parser("submit", help="校验并合并回写裁决 JSON 文件")
    submit_parser.add_argument("submission", help="{\"verdicts\": [...]} 格式的裁决文件路径")
    sub.add_parser("status", help="总体与分轴覆盖度")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    if args.command == "queue":
        return cmd_queue(root, args.chapter, args.batch_size, args.batch_index, args.axis)
    if args.command == "submit":
        return cmd_submit(root, args.chapter, Path(args.submission).expanduser().resolve())
    return cmd_status(root, args.chapter)


if __name__ == "__main__":
    raise SystemExit(main())
