#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only production dashboard for a novel project."""
from __future__ import annotations

import argparse
import glob
import html
import importlib.util
import json
import os
import sys
from datetime import datetime
from typing import Any


HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.abspath(os.path.join(HERE, "..", ".."))
NOVEL_LIB = os.path.join(SKILLS, "novel", "_lib")
NOVEL_BATCH = os.path.join(SKILLS, "novel-batch", "scripts")
NOVEL_SUPERVISOR = os.path.join(SKILLS, "novel-supervisor", "scripts")
NOVEL_CRAFT = os.path.join(SKILLS, "novel-craft", "scripts")
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)

from novel_pipeline import artifact_graph, dry_run_plan  # noqa: E402
try:
    from report_snapshot import validate_snapshot  # noqa: E402
except Exception:  # pragma: no cover - 兜底：缺模块时不做新鲜度核验（诚实置 None）
    validate_snapshot = None


def _circuit_failure_threshold() -> int:
    """单一真值：从 novel-supervisor 取熔断阈值，别在 dashboard 硬编 3 造成漂移。

    跨 skill 取常量用 importlib（与下方 batch queue.py 同模式）；取不到则回落 3（与 supervisor 默认一致）。"""
    try:
        sup = os.path.join(NOVEL_SUPERVISOR, "supervisor.py")
        spec = importlib.util.spec_from_file_location("novel_supervisor_mod", sup)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return int(mod.CIRCUIT_FAILURE_THRESHOLD)
    except Exception:
        return 3


CIRCUIT_FAILURE_THRESHOLD = _circuit_failure_threshold()

def _load_batch_queue_module():
    queue_path = os.path.join(NOVEL_BATCH, "queue.py")
    if not os.path.exists(queue_path):
        return None
    spec = importlib.util.spec_from_file_location("novel_batch_queue", queue_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_author_workflow_module():
    path = os.path.join(NOVEL_CRAFT, "author_workflow.py")
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location("novel_author_workflow", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    batch_queue = _load_batch_queue_module()
except Exception:  # pragma: no cover - dashboard degrades if queue is unavailable
    batch_queue = None
try:
    author_workflow_mod = _load_author_workflow_module()
except Exception:  # pragma: no cover - dashboard degrades if workflow is unavailable
    author_workflow_mod = None


DASHBOARD_KIND = "novel_dashboard"


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def open_semantic_jobs(root: str) -> list[dict[str, Any]]:
    jobs = []
    for path in sorted(glob.glob(os.path.join(root, "语义任务", "*.json"))):
        payload = load_json(path, {}) or {}
        status = str(payload.get("status") or payload.get("state") or "open")
        if status in {"completed", "approved", "rejected"}:
            continue
        jobs.append({
            "path": rel(root, path),
            "status": status,
            "assigned_role": payload.get("assigned_role") or payload.get("role") or "",
            "schema_ref": payload.get("schema_ref") or "",
        })
    return jobs


def revision_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "修订", "revision_plan.json")
    plan = load_json(path, {}) or {}
    tasks = plan.get("tasks") if isinstance(plan, dict) else []
    if not isinstance(tasks, list):
        tasks = []
    by_priority: dict[str, int] = {}
    conflicts = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        priority = str(task.get("priority") or "P?")
        by_priority[priority] = by_priority.get(priority, 0) + 1
        if task.get("conflict"):
            conflicts += 1
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "task_count": len(tasks),
        "by_priority": by_priority,
        "conflicts": conflicts,
    }


def _snapshot_freshness(root: str, payload: Any) -> dict[str, Any]:
    """报告 source_snapshot vs **当前正文** 的实时核验（王敦外传实证的自盲修复）：
    dashboard 生成早于改稿时，provenance 图的 stale 检测看不到"报告的源正文已变"——
    报告文件本身没变、不算 stale，但它评的已经不是现在这本书。每次 build 都重新对
    快照 hash，而不是信任生成时点的图。缺快照/缺依赖 → fresh=None（诚实未知，不装新鲜）。"""
    if validate_snapshot is None or not isinstance(payload, dict) or not payload:
        return {"fresh": None, "msg": "未核验（缺报告或核验依赖）"}
    ok, msg = validate_snapshot(root, payload.get("source_snapshot"))
    return {"fresh": bool(ok), "msg": msg}


def review_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "审稿", "review_report.json")
    payload = load_json(path, {}) or {}
    findings = payload.get("findings") if isinstance(payload, dict) else []
    if not isinstance(findings, list):
        findings = []
    blocking = [item for item in findings if isinstance(item, dict) and item.get("blocking")]
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "finding_count": len(findings),
        "blocking_count": len(blocking),
        "blocking_ids": [item.get("id") or item.get("dimension") or item.get("problem") for item in blocking[:20]],
        "snapshot": _snapshot_freshness(root, payload) if os.path.exists(path) else {"fresh": None, "msg": "无报告"},
    }


def score_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "评分", "score_report.json")
    payload = load_json(path, {}) or {}
    market_jobs = os.path.join(root, "评分", "market_evidence_jobs.json")
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "total_score": payload.get("total_score") if isinstance(payload, dict) else None,
        "verdict": payload.get("verdict") if isinstance(payload, dict) else "",
        "production_decision": (payload.get("production_decision") or {}).get("decision") if isinstance(payload, dict) else "",
        "market_evidence_jobs": rel(root, market_jobs) if os.path.exists(market_jobs) else "",
        "snapshot": _snapshot_freshness(root, payload) if os.path.exists(path) else {"fresh": None, "msg": "无报告"},
    }


def batch_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "生产数据", "novel_batch_queue.json")
    if batch_queue is None:
        return {
            "path": rel(root, path),
            "exists": os.path.exists(path),
            "summary": {},
            "dead_letter_count": 0,
            "run_artifacts": {"count": 0, "by_status": {}, "latest": []},
        }
    queue = batch_queue.NovelBatchQueue(root)
    if not os.path.exists(path):
        return {
            "path": rel(root, path),
            "exists": False,
            "summary": {},
            "dead_letter_count": 0,
            "run_artifacts": queue.run_artifact_summary(),
        }
    q = queue.status()
    dead = [task for task in q.get("tasks", []) if task.get("status") == "dead_letter"]
    return {
        "path": rel(root, path),
        "exists": True,
        "summary": q.get("summary") or {},
        "dead_letter_count": len(dead),
        "run_artifacts": queue.run_artifact_summary(),
    }


def release_summary(root: str) -> dict[str, Any]:
    manifest = os.path.join(root, "导出", "release_manifest.json")
    exported = sorted(glob.glob(os.path.join(root, "导出", "*")))
    payload = load_json(manifest, {}) or {}
    readiness = payload.get("release_readiness") if isinstance(payload, dict) else {}
    return {
        "release_manifest": rel(root, manifest),
        "release_manifest_exists": os.path.exists(manifest),
        "release_ready": bool(payload.get("release_ready")) if isinstance(payload, dict) else False,
        "blocker_count": (readiness or {}).get("blocker_count", 0) if isinstance(readiness, dict) else 0,
        "exported_files": [rel(root, path) for path in exported if os.path.isfile(path)],
    }


def author_workflow_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "生产数据", "author_workflow.json")
    payload = load_json(path, {}) or {}
    source = "file" if isinstance(payload, dict) and payload else ""
    if (not payload or not isinstance(payload, dict)) and author_workflow_mod is not None:
        try:
            payload = author_workflow_mod.build_workflow(root)
            source = "computed"
        except Exception as exc:  # pragma: no cover - dashboard must degrade
            return {"path": rel(root, path), "exists": os.path.exists(path), "error": str(exc)}
    steps = payload.get("steps") if isinstance(payload, dict) else []
    steps = steps if isinstance(steps, list) else []
    active = next((step for step in steps if isinstance(step, dict) and step.get("key") == payload.get("current_step")), None)
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "source": source,
        "current_step": payload.get("current_step") if isinstance(payload, dict) else "",
        "next_action": payload.get("next_action") if isinstance(payload, dict) else "",
        "step_count": len(steps),
        "done_count": sum(1 for step in steps if isinstance(step, dict) and step.get("status") == "done"),
        "warning_count": sum(1 for step in steps if isinstance(step, dict) and step.get("status") == "warning"),
        "pending_count": sum(1 for step in steps if isinstance(step, dict) and step.get("status") == "pending"),
        "active_label": active.get("label") if isinstance(active, dict) else "",
        "active_blockers": active.get("blockers") if isinstance(active, dict) else [],
        "active_warnings": active.get("warnings") if isinstance(active, dict) else [],
    }


def review_board_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "审稿", "review_board.json")
    payload = load_json(path, {}) or {}
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "decision": payload.get("decision") if isinstance(payload, dict) else "",
        "approval_required": bool(payload.get("approval_required")) if isinstance(payload, dict) else False,
        "generated_at": payload.get("generated_at") if isinstance(payload, dict) else "",
    }


def prompt_cache_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "生产数据", "prompt_cache_metrics.json")
    payload = load_json(path, {}) or {}
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "item_count": payload.get("item_count", 0) if isinstance(payload, dict) else 0,
        "cache_control_coverage": payload.get("cache_control_coverage", 0.0) if isinstance(payload, dict) else 0.0,
        "static_context_ratio": payload.get("static_context_ratio", 0.0) if isinstance(payload, dict) else 0.0,
        "cache_readiness_ratio": payload.get("cache_readiness_ratio", payload.get("static_context_ratio", 0.0)) if isinstance(payload, dict) else 0.0,
        "actual_cache_hit_ratio": payload.get("actual_cache_hit_ratio", 0.0) if isinstance(payload, dict) else 0.0,
        "actual_usage_records": ((payload.get("actual_usage") or {}).get("record_count", 0) if isinstance(payload, dict) else 0),
        "estimated_static_tokens": payload.get("estimated_static_tokens", 0) if isinstance(payload, dict) else 0,
    }


def vector_eval_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "生产数据", "vector_store_eval.json")
    payload = load_json(path, {}) or {}
    metrics = payload.get("metrics") if isinstance(payload, dict) else {}
    thresholds = payload.get("thresholds") if isinstance(payload, dict) else {}
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "passed": bool(payload.get("passed")) if isinstance(payload, dict) else False,
        "recall_at_k": (metrics or {}).get("recall_at_k", 0.0) if isinstance(metrics, dict) else 0.0,
        "mrr": (metrics or {}).get("mrr", 0.0) if isinstance(metrics, dict) else 0.0,
        "case_count": (metrics or {}).get("case_count", 0) if isinstance(metrics, dict) else 0,
        "failure_count": (metrics or {}).get("failure_count", 0) if isinstance(metrics, dict) else 0,
        "top_k": (thresholds or {}).get("top_k", 0) if isinstance(thresholds, dict) else 0,
    }


def supervisor_summary(root: str) -> dict[str, Any]:
    path = os.path.join(root, "生产数据", "supervisor_ledger.json")
    payload = load_json(path, {}) or {}
    rolling = payload.get("rolling_entries") if isinstance(payload, dict) else {}
    rolling = rolling if isinstance(rolling, dict) else {}
    tripped = []
    for key, entry in rolling.items():
        if not isinstance(entry, dict):
            continue
        failures = int(entry.get("failure_count") or 0)
        if failures >= CIRCUIT_FAILURE_THRESHOLD:  # 单一真值·与 supervisor 同源（不再硬编 3）
            tripped.append({
                "key": key,
                "stage": entry.get("stage") or "",
                "finding_hash": entry.get("finding_hash") or "",
                "failure_count": failures,
                "cooldown_until": entry.get("cooldown_until") or "",
            })
    return {
        "path": rel(root, path),
        "exists": os.path.exists(path),
        "rolling_entry_count": len(rolling),
        "rolling_tripped_count": len(tripped),
        "rolling_tripped": tripped[:10],
    }


def history_path(root: str) -> str:
    return os.path.join(root, "生产数据", "novel_dashboard_history.jsonl")


def history_record(dashboard: dict[str, Any]) -> dict[str, Any]:
    batch = dashboard.get("batch") or {}
    run_artifacts = batch.get("run_artifacts") or {}
    prompt_cache = dashboard.get("prompt_cache") or {}
    vector_eval = dashboard.get("vector_eval") or {}
    supervisor = dashboard.get("supervisor") or {}
    return {
        "generated_at": dashboard.get("generated_at"),
        "next_stage": dashboard.get("next_stage"),
        "batch_avg_elapsed_ms": run_artifacts.get("avg_elapsed_ms", 0),
        "batch_failed_runs": (run_artifacts.get("by_status") or {}).get("failed", 0),
        "batch_dead_letter": batch.get("dead_letter_count", 0),
        "prompt_cache_readiness": prompt_cache.get("cache_readiness_ratio", prompt_cache.get("static_context_ratio", 0.0)),
        "actual_cache_hit_ratio": prompt_cache.get("actual_cache_hit_ratio", 0.0),
        "retrieval_recall_at_k": vector_eval.get("recall_at_k", 0.0),
        "retrieval_mrr": vector_eval.get("mrr", 0.0),
        "supervisor_rolling_tripped": supervisor.get("rolling_tripped_count", 0),
    }


def load_history(root: str, limit: int = 50) -> list[dict[str, Any]]:
    path = history_path(root)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                out.append(payload)
    return out[-limit:]


def trend_summary(root: str) -> dict[str, Any]:
    history = load_history(root, limit=50)
    latest = history[-1] if history else {}
    previous = history[-2] if len(history) >= 2 else {}
    deltas = {}
    for key in (
        "batch_avg_elapsed_ms",
        "batch_failed_runs",
        "batch_dead_letter",
        "prompt_cache_readiness",
        "actual_cache_hit_ratio",
        "retrieval_recall_at_k",
        "retrieval_mrr",
        "supervisor_rolling_tripped",
    ):
        if key in latest and key in previous:
            try:
                deltas[key] = latest[key] - previous[key]
            except TypeError:
                pass
    return {
        "path": rel(root, history_path(root)),
        "record_count": len(history),
        "latest": latest,
        "previous": previous,
        "deltas": deltas,
    }


def build_dashboard(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    plan = dry_run_plan(root)
    graph = artifact_graph(root)
    stages = plan.get("stages") or []
    stage_counts: dict[str, int] = {}
    for stage in stages:
        status = str(stage.get("status") or "unknown")
        stage_counts[status] = stage_counts.get(status, 0) + 1
    stale = graph.get("stale_artifacts") or []
    batch = batch_summary(root)
    prompt_cache = prompt_cache_summary(root)
    vector_eval = vector_eval_summary(root)
    supervisor = supervisor_summary(root)
    author_flow = author_workflow_summary(root)
    run_artifacts = batch.get("run_artifacts") or {}
    return {
        "schema_version": 1,
        "kind": DASHBOARD_KIND,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": root,
        "title": plan.get("title"),
        "next_stage": plan.get("next_stage"),
        "author_workflow": author_flow,
        "stage_counts": stage_counts,
        "blocked_stages": [
            {
                "key": stage.get("key"),
                "label": stage.get("label"),
                "missing_inputs": stage.get("missing_inputs") or [],
                "gate_blockers": stage.get("gate_blockers") or [],
            }
            for stage in stages if stage.get("status") == "blocked"
        ],
        "stale_artifacts": stale,
        "open_semantic_jobs": open_semantic_jobs(root),
        "revision": revision_summary(root),
        "review": review_summary(root),
        "score": score_summary(root),
        "batch": batch,
        "release": release_summary(root),
        "review_board": review_board_summary(root),
        "prompt_cache": prompt_cache,
        "vector_eval": vector_eval,
        "supervisor": supervisor,
        "ops_slo": {
            "batch_avg_elapsed_ms": run_artifacts.get("avg_elapsed_ms", 0),
            "batch_failed_runs": (run_artifacts.get("by_status") or {}).get("failed", 0),
            "batch_truncated_logs": run_artifacts.get("truncated_log_count", 0),
            "batch_dead_letter": batch.get("dead_letter_count", 0),
            "prompt_cache_readiness": prompt_cache.get("cache_readiness_ratio", prompt_cache.get("static_context_ratio", 0.0)),
            "actual_cache_hit_ratio": prompt_cache.get("actual_cache_hit_ratio", 0.0),
            "retrieval_recall_at_k": vector_eval.get("recall_at_k", 0.0),
            "retrieval_mrr": vector_eval.get("mrr", 0.0),
            "supervisor_rolling_tripped": supervisor.get("rolling_tripped_count", 0),
        },
        "trends": trend_summary(root),
    }


def render_markdown(dashboard: dict[str, Any]) -> str:
    lines = [
        "# Novel Dashboard",
        "",
        f"- 作品：{dashboard.get('title')}",
        f"- 生成：{dashboard.get('generated_at')}",
        f"- next_stage：{dashboard.get('next_stage') or 'done'}",
        f"- stage_counts：{dashboard.get('stage_counts')}",
        "",
        "## Blocked Stages",
        "",
    ]
    blocked = dashboard.get("blocked_stages") or []
    if blocked:
        for stage in blocked:
            lines.append(
                f"- {stage.get('key')} / {stage.get('label')}："
                f"missing={stage.get('missing_inputs')} gate={stage.get('gate_blockers') or []}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Signals", ""])
    review = dashboard.get("review") or {}
    score = dashboard.get("score") or {}
    revision = dashboard.get("revision") or {}
    batch = dashboard.get("batch") or {}
    release = dashboard.get("release") or {}
    board = dashboard.get("review_board") or {}
    cache = dashboard.get("prompt_cache") or {}
    vector_eval = dashboard.get("vector_eval") or {}
    supervisor = dashboard.get("supervisor") or {}
    author_flow = dashboard.get("author_workflow") or {}
    ops_slo = dashboard.get("ops_slo") or {}
    trends = dashboard.get("trends") or {}
    lines.append(f"- review blockers：{review.get('blocking_count', 0)} / findings={review.get('finding_count', 0)}")
    # 报告新鲜度（实时核验·非生成时点快照）：False = 正文在报告之后改过，review/score 结论已过期
    for label, summ in (("review", review), ("score", score)):
        snap = summ.get("snapshot") or {}
        if snap.get("fresh") is False:
            lines.append(f"- ⚠️ {label} 报告已过期：{snap.get('msg')}")
    lines.append(
        f"- author workflow：{author_flow.get('current_step') or 'unknown'} "
        f"done={author_flow.get('done_count', 0)}/{author_flow.get('step_count', 0)} source={author_flow.get('source') or '-'}"
    )
    if author_flow.get("active_blockers"):
        lines.append(f"- author blockers：{author_flow.get('active_blockers')}")
    if author_flow.get("next_action"):
        lines.append(f"- author next_action：`{author_flow.get('next_action')}`")
    lines.append(f"- score：{score.get('total_score')} verdict={score.get('verdict') or ''} decision={score.get('production_decision') or ''}")
    lines.append(f"- revision tasks：{revision.get('task_count', 0)} by_priority={revision.get('by_priority') or {}} conflicts={revision.get('conflicts', 0)}")
    lines.append(f"- semantic jobs：{len(dashboard.get('open_semantic_jobs') or [])}")
    lines.append(f"- stale artifacts：{len(dashboard.get('stale_artifacts') or [])}")
    lines.append(f"- batch：{(batch.get('summary') or {}).get('by_status') or {}} dead_letter={batch.get('dead_letter_count', 0)}")
    lines.append(
        f"- batch runs：{(batch.get('run_artifacts') or {}).get('count', 0)} "
        f"by_status={(batch.get('run_artifacts') or {}).get('by_status') or {}}"
    )
    lines.append(
        f"- release manifest：{'yes' if release.get('release_manifest_exists') else 'no'} "
        f"ready={release.get('release_ready')} blockers={release.get('blocker_count', 0)}"
    )
    lines.append(
        f"- review board：{'yes' if board.get('exists') else 'no'} "
        f"decision={board.get('decision') or ''} approval_required={board.get('approval_required')}"
    )
    lines.append(
        f"- prompt cache：{'yes' if cache.get('exists') else 'no'} "
        f"coverage={cache.get('cache_control_coverage', 0):.2f} readiness={cache.get('cache_readiness_ratio', cache.get('static_context_ratio', 0)):.2f} actual_hit={cache.get('actual_cache_hit_ratio', 0):.2f}"
    )
    lines.append(
        f"- vector eval：{'yes' if vector_eval.get('exists') else 'no'} "
        f"passed={vector_eval.get('passed')} recall={vector_eval.get('recall_at_k', 0):.2f} mrr={vector_eval.get('mrr', 0):.2f}"
    )
    lines.append(
        f"- supervisor：rolling_entries={supervisor.get('rolling_entry_count', 0)} "
        f"tripped={supervisor.get('rolling_tripped_count', 0)}"
    )
    lines.extend(["", "## Ops SLO", ""])
    lines.append(
        f"- batch_avg_elapsed_ms={ops_slo.get('batch_avg_elapsed_ms', 0)} "
        f"failed_runs={ops_slo.get('batch_failed_runs', 0)} truncated_logs={ops_slo.get('batch_truncated_logs', 0)}"
    )
    lines.append(
        f"- cache_readiness={ops_slo.get('prompt_cache_readiness', 0):.2f} "
        f"actual_cache_hit={ops_slo.get('actual_cache_hit_ratio', 0):.2f} "
        f"retrieval_recall={ops_slo.get('retrieval_recall_at_k', 0):.2f}"
    )
    if trends.get("record_count"):
        lines.extend(["", "## Trends", "", f"- history_records：{trends.get('record_count')} deltas={trends.get('deltas') or {}}"])
    if score.get("market_evidence_jobs"):
        lines.extend(["", "## Market Evidence", "", f"- {score.get('market_evidence_jobs')}"])
    return "\n".join(lines) + "\n"


def render_html(dashboard: dict[str, Any], markdown: str) -> str:
    payload = html.escape(json.dumps(dashboard, ensure_ascii=False, indent=2))
    body = html.escape(markdown)
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<title>Novel Dashboard</title>"
        "<style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:24px;line-height:1.45}"
        "pre{background:#f6f8fa;padding:16px;border-radius:6px;overflow:auto}"
        ".grid{display:grid;grid-template-columns:minmax(280px,1fr) minmax(280px,1fr);gap:20px}"
        "@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>"
        "<h1>Novel Dashboard</h1><div class='grid'><section><h2>Summary</h2>"
        f"<pre>{body}</pre></section><section><h2>JSON</h2><pre>{payload}</pre></section></div>"
    )


def write_outputs(root: str, dashboard: dict[str, Any], *, html_out: bool = False) -> tuple[str, str, str | None]:
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "novel_dashboard.json")
    md_path = os.path.join(out_dir, "novel_dashboard.md")
    markdown = render_markdown(dashboard)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    html_path = None
    if html_out:
        html_path = os.path.join(out_dir, "novel_dashboard.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(render_html(dashboard, markdown))
    append_history(root, dashboard)
    return json_path, md_path, html_path


def append_history(root: str, dashboard: dict[str, Any], *, keep: int = 200) -> str:
    path = history_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    history = load_history(root, limit=keep - 1)
    history.append(history_record(dashboard))
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        for item in history[-keep:]:
            f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="novel read-only production dashboard")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true", help="write dashboard JSON/Markdown")
    parser.add_argument("--html", action="store_true", help="also write static HTML with --write")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    dashboard = build_dashboard(root)
    if args.write:
        json_path, md_path, html_path = write_outputs(root, dashboard, html_out=args.html)
        if not args.json:
            print(f"[ok] dashboard JSON → {json_path}")
            print(f"[ok] dashboard MD   → {md_path}")
            if html_path:
                print(f"[ok] dashboard HTML → {html_path}")
    if args.json or not args.write:
        print(json.dumps(dashboard, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
