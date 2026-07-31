#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic supervisor layer for the novel pipeline.

The supervisor does not write prose, call models, or bypass human-choice gates.
It reads the executable pipeline plan plus QA/revision/batch signals and returns
the next safe orchestration action for a thin agent or human operator.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any


HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.abspath(os.path.join(HERE, "..", ".."))
NOVEL_LIB = os.path.join(SKILLS, "_lib")
NOVEL_SCRIPTS = os.path.join(SKILLS, "scripts")
NOVEL_CRAFT = os.path.join(SKILLS, "novel-craft", "scripts")
NOVEL_BATCH = os.path.join(SKILLS, "novel-batch", "scripts", "queue.py")
for path in (NOVEL_LIB, NOVEL_SCRIPTS, NOVEL_CRAFT):
    if path not in sys.path:
        sys.path.insert(0, path)

from novel_pipeline import dry_run_plan, handoff_contract  # noqa: E402

try:
    from pipeline_runner import create_run, latest_run_id, load_run, write_plan  # noqa: E402
except Exception:  # pragma: no cover - supervisor can still plan without run state
    create_run = latest_run_id = load_run = write_plan = None

try:
    from provenance import append_event  # noqa: E402
except Exception:  # pragma: no cover - provenance is additive
    append_event = None

try:
    from project_io import load_project_settings  # noqa: E402
except Exception:  # pragma: no cover - settings 缺失时 critic 触发面静默关闭
    load_project_settings = None


SUPERVISOR_KIND = "novel_supervisor_next_action"
SUPERVISOR_LEDGER_KIND = "novel_supervisor_circuit_ledger"
HUMAN_STAGES = {"blueprint", "setting", "demo"}
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_MINUTES = 60


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def _load_batch_queue_module():
    if not os.path.exists(NOVEL_BATCH):
        return None
    spec = importlib.util.spec_from_file_location("novel_batch_queue_supervisor", NOVEL_BATCH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_semantic_jobs(root: str) -> list[str]:
    jobs_dir = os.path.join(root, "语义任务")
    if not os.path.isdir(jobs_dir):
        return []
    out = []
    for name in sorted(os.listdir(jobs_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(jobs_dir, name)
        payload = load_json(path, {}) or {}
        status = str(payload.get("status") or payload.get("state") or "open")
        if status not in {"completed", "approved", "rejected"}:
            out.append(rel(root, path))
    return out


def review_blockers(root: str) -> list[dict[str, Any]]:
    report = load_json(os.path.join(root, "审稿", "review_report.json"), {}) or {}
    findings = report.get("findings") if isinstance(report, dict) else []
    if not isinstance(findings, list):
        return []
    return [item for item in findings if isinstance(item, dict) and item.get("blocking")]


def revision_plan_status(root: str) -> dict[str, Any]:
    path = os.path.join(root, "修订", "revision_plan.json")
    plan = load_json(path, {}) or {}
    tasks = plan.get("tasks") if isinstance(plan, dict) else []
    if not isinstance(tasks, list):
        tasks = []
    p0 = [task for task in tasks if isinstance(task, dict) and task.get("priority") == "P0"]
    conflicts = [task for task in tasks if isinstance(task, dict) and task.get("conflict")]
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "task_count": len(tasks),
        "p0_count": len(p0),
        "conflict_count": len(conflicts),
    }


def batch_status(root: str) -> dict[str, Any]:
    module = _load_batch_queue_module()
    queue_path = os.path.join(root, "生产数据", "novel_batch_queue.json")
    if module is None or not os.path.exists(queue_path):
        return {"exists": os.path.exists(queue_path), "summary": {}, "dead_letter_count": 0}
    payload = module.NovelBatchQueue(root).status()
    dead = [task for task in payload.get("tasks", []) if task.get("status") == "dead_letter"]
    return {
        "exists": True,
        "summary": payload.get("summary") or {},
        "dead_letter_count": len(dead),
    }


def stage_by_key(plan: dict[str, Any], key: str | None) -> dict[str, Any]:
    for stage in plan.get("stages") or []:
        if stage.get("key") == key:
            return stage
    return {}


def ledger_path(root: str) -> str:
    return os.path.join(root, "生产数据", "supervisor_ledger.json")


def circuit_key(stage_key: str | None, *, run_id: str = "", finding_hash: str = "") -> str:
    return "|".join([
        str(run_id or "adhoc"),
        str(stage_key or "none"),
        str(finding_hash or "no_finding_hash"),
    ])


def rolling_key(stage_key: str | None, *, finding_hash: str = "") -> str:
    return "|".join([
        "rolling",
        str(stage_key or "none"),
        str(finding_hash or "no_finding_hash"),
    ])


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def is_tripped(entry: dict[str, Any]) -> bool:
    failures = int(entry.get("failure_count") or 0)
    if failures < CIRCUIT_FAILURE_THRESHOLD:
        return False
    cooldown_until = parse_dt(entry.get("cooldown_until") or "")
    if cooldown_until is None:
        return True
    return datetime.now() < cooldown_until


def load_circuit_ledger(root: str) -> dict[str, Any]:
    payload = load_json(ledger_path(root), {}) or {}
    if payload.get("kind") == SUPERVISOR_LEDGER_KIND:
        payload.setdefault("entries", {})
        payload.setdefault("rolling_entries", {})
        return payload
    # Legacy schema was {"last_stage": "...", "retry_count": N}. Keep the
    # information visible but do not let old read-side increments trip the new
    # execution-side breaker.
    return {
        "schema_version": 1,
        "kind": SUPERVISOR_LEDGER_KIND,
        "created_from_legacy": bool(payload),
        "legacy": payload,
        "entries": {},
        "rolling_entries": {},
    }


def write_circuit_ledger(root: str, payload: dict[str, Any]) -> str:
    path = ledger_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return path


def circuit_status(root: str, stage_key: str | None, *, run_id: str = "", finding_hash: str = "") -> dict[str, Any]:
    ledger = load_circuit_ledger(root)
    key = circuit_key(stage_key, run_id=run_id, finding_hash=finding_hash)
    entry = (ledger.get("entries") or {}).get(key) or {}
    failures = int(entry.get("failure_count") or 0)
    return {
        "key": key,
        "run_id": run_id or "adhoc",
        "stage": stage_key,
        "finding_hash": finding_hash or "",
        "failure_count": failures,
        "tripped": is_tripped(entry),
        "last_event": entry.get("last_event") or "",
        "last_reason": entry.get("last_reason") or "",
        "last_updated_at": entry.get("last_updated_at") or "",
        "cooldown_until": entry.get("cooldown_until") or "",
    }


def aggregate_circuit_status(root: str, stage_key: str | None, *, active_run_id: str = "") -> dict[str, Any]:
    """Read breaker state for all execution records relevant to a stage.

    Exact breaker keys remain scoped by stage/run/finding so one bad finding does
    not erase other work. The scheduler, however, must stop if any active or
    prior record for the same next stage has tripped; otherwise failures written
    with real run_id/finding_hash values are invisible to read-side decisions.
    """
    ledger = load_circuit_ledger(root)
    entries = ledger.get("entries") or {}
    matching: list[dict[str, Any]] = []
    for key, entry in entries.items():
        if not isinstance(entry, dict) or entry.get("stage") != stage_key:
            continue
        if active_run_id and entry.get("run_id") not in {active_run_id, "adhoc", ""}:
            continue
        failures = int(entry.get("failure_count") or 0)
        matching.append({
            "key": key,
            "run_id": entry.get("run_id") or "adhoc",
            "stage": entry.get("stage") or stage_key,
            "finding_hash": entry.get("finding_hash") or "",
            "failure_count": failures,
            "tripped": is_tripped(entry),
            "last_event": entry.get("last_event") or "",
            "last_reason": entry.get("last_reason") or "",
            "last_updated_at": entry.get("last_updated_at") or "",
            "cooldown_until": entry.get("cooldown_until") or "",
            "scope": "run",
        })
    rolling_matching: list[dict[str, Any]] = []
    for key, entry in (ledger.get("rolling_entries") or {}).items():
        if not isinstance(entry, dict) or entry.get("stage") != stage_key:
            continue
        failures = int(entry.get("failure_count") or 0)
        rolling_matching.append({
            "key": key,
            "run_id": "rolling",
            "stage": entry.get("stage") or stage_key,
            "finding_hash": entry.get("finding_hash") or "",
            "failure_count": failures,
            "tripped": is_tripped(entry),
            "last_event": entry.get("last_event") or "",
            "last_reason": entry.get("last_reason") or "",
            "last_updated_at": entry.get("last_updated_at") or "",
            "cooldown_until": entry.get("cooldown_until") or "",
            "scope": "rolling",
            "run_ids": entry.get("run_ids") or [],
        })
    matching.extend(rolling_matching)
    matching.sort(key=lambda item: (
        -int(item.get("failure_count") or 0),
        1 if item.get("scope") == "rolling" else 0,
        str(item.get("last_updated_at") or ""),
        item["key"],
    ))
    tripped = [item for item in matching if item.get("tripped")]
    max_failures = max((int(item.get("failure_count") or 0) for item in matching), default=0)
    # 诚实可见化（B1）：熔断器只在执行方**逐次回报**结果时才有数据可判。没有任何执行回报 →
    # 它无从判断成败、永远 tripped=False（inert）。把这层"是否接到遥测"显式暴露，避免读者误以为
    # 一个静默空账的熔断器在保护流程（claims-vs-reality）。armed=有遥测才算真正在保护。
    telemetry_present = len(matching) > 0
    return {
        "key": f"aggregate|{stage_key or 'none'}",
        "run_id": active_run_id or "any",
        "stage": stage_key,
        "finding_hash": "",
        "failure_count": max_failures,
        "tripped": bool(tripped),
        "telemetry_present": telemetry_present,
        "armed": telemetry_present,
        "note": ("" if telemetry_present else
                 "未接执行遥测：熔断器处于 inert（无从判断成败、永不触发）——执行方须在每次 started/"
                 "failed/succeeded 后调用 `supervisor.py record-execution` 才会真正生效。"),
        "last_event": (matching[0].get("last_event") if matching else ""),
        "last_reason": (matching[0].get("last_reason") if matching else ""),
        "last_updated_at": (matching[0].get("last_updated_at") if matching else ""),
        "matching_entry_count": len(matching),
        "rolling_entry_count": len(rolling_matching),
        "tripped_entries": tripped[:10],
        "matching_entries": matching[:20],
    }


def record_execution_event(
    root: str,
    *,
    stage_key: str,
    result: str,
    run_id: str = "",
    finding_hash: str = "",
    reason: str = "",
) -> dict[str, Any]:
    """Record a real execution result.

    Read-only inspection must never mutate the circuit breaker. Only actual
    failed execution attempts increment failure_count; success clears it.
    """
    root = os.path.abspath(root)
    if result not in {"started", "failed", "succeeded"}:
        raise ValueError(f"unsupported execution result: {result}")
    ledger = load_circuit_ledger(root)
    entries = ledger.setdefault("entries", {})
    rolling_entries = ledger.setdefault("rolling_entries", {})
    key = circuit_key(stage_key, run_id=run_id, finding_hash=finding_hash)
    entry = entries.setdefault(key, {
        "run_id": run_id or "adhoc",
        "stage": stage_key,
        "finding_hash": finding_hash or "",
        "failure_count": 0,
    })
    roll_key = rolling_key(stage_key, finding_hash=finding_hash)
    rolling = rolling_entries.setdefault(roll_key, {
        "stage": stage_key,
        "finding_hash": finding_hash or "",
        "failure_count": 0,
        "run_ids": [],
    })
    timestamp = datetime.now()
    if result == "failed":
        entry["failure_count"] = int(entry.get("failure_count") or 0) + 1
        rolling["failure_count"] = int(rolling.get("failure_count") or 0) + 1
        run_ids = list(rolling.get("run_ids") or [])
        current_run = run_id or "adhoc"
        if current_run not in run_ids:
            run_ids.append(current_run)
        rolling["run_ids"] = run_ids[-20:]
        if int(entry.get("failure_count") or 0) >= CIRCUIT_FAILURE_THRESHOLD:
            entry["cooldown_until"] = (timestamp + timedelta(minutes=CIRCUIT_COOLDOWN_MINUTES)).isoformat(timespec="seconds")
        if int(rolling.get("failure_count") or 0) >= CIRCUIT_FAILURE_THRESHOLD:
            rolling["cooldown_until"] = (timestamp + timedelta(minutes=CIRCUIT_COOLDOWN_MINUTES)).isoformat(timespec="seconds")
    elif result == "succeeded":
        entry["failure_count"] = 0
        entry.pop("cooldown_until", None)
        rolling["failure_count"] = 0
        rolling.pop("cooldown_until", None)
    entry["last_event"] = result
    entry["last_reason"] = reason
    entry["last_updated_at"] = timestamp.isoformat(timespec="seconds")
    rolling["last_event"] = result
    rolling["last_reason"] = reason
    rolling["last_updated_at"] = timestamp.isoformat(timespec="seconds")
    ledger["schema_version"] = 1
    ledger["kind"] = SUPERVISOR_LEDGER_KIND
    ledger["updated_at"] = entry["last_updated_at"]
    path = write_circuit_ledger(root, ledger)
    if append_event:
        append_event(
            root,
            event_type="supervisor_execution_recorded",
            tool="novel-supervisor/scripts/supervisor.py",
            outputs=[path],
            metadata={
                "stage": stage_key,
                "run_id": run_id or "adhoc",
                "finding_hash": finding_hash or "",
                "result": result,
                "failure_count": entry["failure_count"],
            },
        )
    return circuit_status(root, stage_key, run_id=run_id, finding_hash=finding_hash)


def command_for_stage(root: str, stage: dict[str, Any]) -> list[str]:
    key = stage.get("key")
    if key == "author_workflow":
        return [f'python3 skills/novel/novel-craft/scripts/author_workflow.py "{root}" --write']
    if key == "author_intent":
        return [f'python3 skills/novel/novel-craft/scripts/author_intent.py scaffold "{root}"']
    if key == "evidence_prep":
        return [
            f'python3 skills/novel/novel-research/scripts/research_pack.py jobs "{root}"',
            f'python3 skills/novel/novel-research/scripts/research_pack.py scene-usage "{root}"',
            f'python3 skills/novel/novel-observe/scripts/observe.py scaffold "{root}"',
            f'python3 skills/novel/novel-aesthetic/scripts/aesthetic_bank.py scaffold "{root}"',
        ]
    if key == "manuscript_map":
        return [f'python3 skills/novel/novel-craft/scripts/manuscript_map.py "{root}" --write']
    if key == "demo_readiness":
        return [f'python3 skills/novel/novel-craft/scripts/demo_readiness.py "{root}" --write']
    if key == "reader_validation":
        return [f'python3 skills/novel/novel-feedback/scripts/reader_test_plan.py "{root}" --scope opening:1-3']
    if key == "edit":
        return [f'python3 skills/novel/novel-edit/scripts/edit_plan.py "{root}"']
    if key == "ai_compliance":
        return [
            f'python3 skills/novel/novel-craft/scripts/ai_usage.py "{root}"',
            f'python3 skills/novel/novel-craft/scripts/compliance_profile.py "{root}" --write',
        ]
    if key == "metadata_pack":
        return [f'python3 skills/novel/novel-craft/scripts/metadata_pack.py "{root}" --write']
    if key == "revision":
        return [f'python3 skills/novel/novel-craft/scripts/revision_planner.py "{root}"']
    if key == "score":
        return [
            f'python3 skills/novel/novel-score/scripts/collect_market_baseline.py "{root}/评分" --target-platform "<目标平台>" --allow-fetch-errors',
            f'python3 skills/novel/novel-score/scripts/score.py "{root}" --scope opening',
        ]
    if key == "review":
        return [
            f'python3 skills/novel/novel-review/scripts/consistency_audit.py "{root}"',
            f'python3 skills/novel/novel-review/scripts/build_review_report.py "{root}"',
        ]
    if key == "export":
        return [
            f'python3 skills/novel/novel-craft/scripts/export.py "{root}"',
        ]
    if key == "release_manifest":
        return [f'python3 skills/novel/novel-craft/scripts/release_manifest.py "{root}"']
    if key == "screen_ready":
        return [f'python3 skills/novel/novel-craft/scripts/screen_adaptation_ready.py "{root}"']
    if key == "draft":
        return [
            f'python3 skills/novel/novel-craft/scripts/draft_queue.py "{root}" init',
            f'python3 skills/novel/novel-craft/scripts/draft_packets.py "{root}" --next',
        ]
    if key == "post_write":
        return [f'python3 skills/novel/scripts/post_write.py "{root}" --chapter 第NN章 --conclusion "{root}/审稿/state_verify_第NN章.json"']
    if key == "outline":
        return [f'python3 skills/novel/novel-craft/scripts/scene_cards.py "{root}"']
    return []


def critic_loop_signal(root: str) -> dict[str, Any]:
    """critic_loop 选择点的**触发面**（references/critic-loop.md 的 spec 此前只是纸面：
    `_设置.md` 开了 critic_loop 也没有任何机器提示，spec 永远不会在正确时机被想起）。
    本函数只做发现与提示——不执行任何 LLM 评委（supervisor 铁律：确定性编排，不挂评委），
    去偏协议的确定性执行层在 novel/_lib/judge_protocol.py。"""
    if load_project_settings is None:
        return {"enabled": False, "reason": "settings loader unavailable"}
    try:
        settings = load_project_settings(root) or {}
    except Exception:
        return {"enabled": False, "reason": "settings unreadable"}
    raw = str(settings.get("critic_loop") or settings.get("Critic迭代") or "").strip().lower()
    enabled = raw in {"on", "true", "1", "开", "开启", "yes", "enabled"}
    return {"enabled": enabled,
            "spec": "skills/novel/novel-supervisor/references/critic-loop.md",
            "note": ("已开启：高权重章（黄金三章/弧段高潮/关键反转）过确定性闸后，"
                     "按 spec 跑 checklist-grounded critic（评委结论必须过 judge_protocol 去偏）"
                     if enabled else "未开启（默认关·成本闸控）")}


def decide_next_action(root: str, *, write_pipeline_plan: bool = False) -> dict[str, Any]:
    root = os.path.abspath(root)
    plan = dry_run_plan(root)
    if write_pipeline_plan and write_plan:
        write_plan(root, plan)
    semantic_jobs = open_semantic_jobs(root)
    blockers = review_blockers(root)
    revision = revision_plan_status(root)
    batch = batch_status(root)
    next_stage = plan.get("next_stage")
    stage = stage_by_key(plan, next_stage)
    active_run_id = ""
    if latest_run_id is not None:
        try:
            active_run_id = latest_run_id(root) or ""
        except Exception:
            active_run_id = ""
    breaker = aggregate_circuit_status(root, next_stage, active_run_id=active_run_id)
    
    action: dict[str, Any] = {
        "schema_version": 1,
        "kind": SUPERVISOR_KIND,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": root,
        "status": "ready",
        "next_stage": next_stage,
        "stage": stage,
        "signals": {
            "open_semantic_jobs": semantic_jobs,
            "review_blockers": len(blockers),
            "revision": revision,
            "batch": batch,
            "retry_count": breaker["failure_count"],
            "circuit_breaker": breaker,
            "critic_loop": critic_loop_signal(root),
        },
        "recommended_commands": [],
        "handoff": None,
    }

    if breaker["tripped"]:
        action.update({
            "status": "needs_human",
            "action": "circuit_breaker_tripped",
            "reason": f"Self-healing loop exceeded max execution failures ({CIRCUIT_FAILURE_THRESHOLD}) at stage {next_stage}. Human intervention required.",
            "recommended_commands": []
        })
        return action

    if batch.get("dead_letter_count"):
        action.update({
            "status": "blocked",
            "action": "inspect_dead_letter",
            "reason": "batch queue contains dead-letter tasks",
            "recommended_commands": [f'python3 skills/novel/novel-batch/scripts/queue.py dead-letter "{root}" --json'],
        })
        return action

    if blockers and not revision.get("exists"):
        action.update({
            "status": "self_healing",
            "action": "build_revision_plan",
            "reason": "review_report has blocking findings but revision_plan is missing",
            "recommended_commands": [f'python3 skills/novel/novel-craft/scripts/revision_planner.py "{root}"'],
        })
        return action

    if revision.get("conflict_count"):
        action.update({
            "status": "needs_human",
            "action": "resolve_revision_conflicts",
            "reason": "revision_plan contains cross-source conflicts",
            "recommended_commands": [f'sed -n "1,220p" "{root}/修订/修订计划.md"'],
        })
        return action

    if semantic_jobs:
        action.update({
            "status": "dispatch",
            "action": "claim_or_complete_semantic_job",
            "agent_role": "specialist_reviewer",
            "reason": "open semantic jobs exist",
            "context": semantic_jobs[:10],
            "recommended_commands": [
                f'python3 skills/novel/novel-craft/scripts/semantic_job.py show "{root}/{semantic_jobs[0]}"'
            ],
        })
        return action

    if not next_stage:
        action.update({
            "status": "complete",
            "action": "none",
            "reason": "pipeline dry-run reports all stages done",
            "recommended_commands": [f'python3 skills/novel/novel-dashboard/scripts/dashboard.py "{root}" --write --html'],
        })
        return action

    if next_stage in HUMAN_STAGES or "human" in str(stage.get("gate") or ""):
        action.update({
            "status": "needs_human",
            "action": "human_review_or_creation",
            "agent_role": "human",
            "reason": f"stage {next_stage} is a human-choice/semantic approval boundary",
            "recommended_commands": [f'python3 skills/novel/scripts/pipeline_runner.py "{root}" --handoff {next_stage}'],
        })
        return action

    role = stage.get("agent_role") or "workflow_orchestrator"
    action.update({
        "status": "dispatch",
        "action": f"execute_{next_stage}",
        "agent_role": role,
        "reason": f"next pipeline stage is {next_stage}",
        "recommended_commands": command_for_stage(root, stage),
        "handoff": handoff_contract(root, next_stage) if next_stage else None,
    })
    return action


def write_action(root: str, action: dict[str, Any]) -> str:
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "supervisor_next_action.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(action, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if append_event:
        append_event(
            root,
            event_type="supervisor_action_written",
            tool="novel-supervisor/scripts/supervisor.py",
            outputs=[path],
            metadata={
                "next_stage": action.get("next_stage"),
                "status": action.get("status"),
                "action": action.get("action"),
            },
        )
    return path


def render_text(action: dict[str, Any]) -> str:
    lines = [
        f"[{str(action.get('status') or '').upper()}] {action.get('action') or 'none'}",
        f"next_stage: {action.get('next_stage') or 'none'}",
        f"reason: {action.get('reason') or ''}",
    ]
    if action.get("agent_role"):
        lines.append(f"agent_role: {action.get('agent_role')}")
    commands = action.get("recommended_commands") or []
    if commands:
        lines.append("commands:")
        for cmd in commands:
            lines.append(f"- {cmd}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="novel supervisor deterministic next action")
    parser.add_argument("command", choices=["run", "next", "start-run", "show-run", "record-execution"])
    parser.add_argument("project_root")
    parser.add_argument("--run-id")
    parser.add_argument("--agent", default="novel-supervisor")
    parser.add_argument("--stage")
    parser.add_argument("--result", choices=["started", "failed", "succeeded"], default="failed")
    parser.add_argument("--finding-hash", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--write", action="store_true", help="write 生产数据/supervisor_next_action.json")
    parser.add_argument("--write-plan", action="store_true", help="also write pipeline plan artifacts")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2

    if args.command == "start-run":
        if create_run is None:
            print("[err] pipeline_runner create_run unavailable", file=sys.stderr)
            return 1
        run = create_run(root, actor=args.agent)
        print(json.dumps(run, ensure_ascii=False, indent=2) if args.json else f"[ok] started {run['run_id']}")
        return 0

    if args.command == "show-run":
        if load_run is None or latest_run_id is None:
            print("[err] pipeline_runner run helpers unavailable", file=sys.stderr)
            return 1
        run_id = args.run_id or latest_run_id(root)
        run = load_run(root, run_id)
        print(json.dumps(run, ensure_ascii=False, indent=2))
        return 0

    if args.command == "record-execution":
        if not args.stage:
            print("[err] record-execution requires --stage", file=sys.stderr)
            return 2
        status = record_execution_event(
            root,
            stage_key=args.stage,
            result=args.result,
            run_id=args.run_id or "",
            finding_hash=args.finding_hash,
            reason=args.reason,
        )
        print(json.dumps(status, ensure_ascii=False, indent=2) if args.json else render_text({
            "status": "needs_human" if status.get("tripped") else "ready",
            "action": "circuit_breaker_tripped" if status.get("tripped") else "execution_recorded",
            "next_stage": args.stage,
            "reason": status.get("last_reason") or status.get("last_event") or "",
        }))
        return 1 if status.get("tripped") else 0

    action = decide_next_action(root, write_pipeline_plan=args.write_plan)
    if args.write:
        path = write_action(root, action)
        if not args.json:
            print(f"[ok] supervisor action → {path}")
    print(json.dumps(action, ensure_ascii=False, indent=2) if args.json else render_text(action))
    return 0 if action.get("status") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
