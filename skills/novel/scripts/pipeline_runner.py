#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic workflow runner for the novel pipeline.

The runner does not write prose, call model backends, or spend quota.  It reads
the executable pipeline registry, checks project artifacts, and explains the
next safe step for an optional thin agent/orchestrator.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any


_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "_lib"))
_CRAFT = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-craft", "scripts"))
for _path in (_LIB, _CRAFT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from novel_pipeline import (  # noqa: E402
    PIPELINE_PLAN_KIND,
    artifact_graph,
    dry_run_plan,
    handoff_contract,
    registry_payload,
)
try:
    from provenance import append_event  # noqa: E402
except Exception:  # pragma: no cover - runner should still work without provenance helper
    append_event = None

RUN_KIND = "novel_pipeline_run"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Novel Pipeline Dry Run",
        "",
        f"- 作品：{plan.get('title')}",
        f"- kind：{plan.get('project_kind')}",
        f"- next_stage：{plan.get('next_stage') or 'done'}",
        "",
        "| status | stage | owner | gate | cost | semantic | parallel | missing inputs |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for stage in plan.get("stages") or []:
        missing = ", ".join(stage.get("missing_inputs") or [])
        lines.append(
            f"| {stage['status']} | {stage['key']} / {stage['label']} | {stage['owner']} | "
            f"{stage.get('gate') or ''} | {stage.get('cost_level') or ''} | "
            f"{'yes' if stage.get('semantic_required') else 'no'} | "
            f"{'yes' if stage.get('can_parallel') else 'no'} | {missing} |"
        )
    if plan.get("open_semantic_jobs"):
        lines.extend(["", "## Open Semantic Jobs", ""])
        for job in plan["open_semantic_jobs"]:
            lines.append(f"- {job}")
    if plan.get("market_evidence_jobs"):
        lines.extend(["", "## Market Evidence Jobs", "", f"- {plan['market_evidence_jobs']}"])
    summary = plan.get("artifact_graph_summary") or {}
    if summary:
        lines.extend(["", "## Artifact Graph", ""])
        lines.append(f"- artifacts={summary.get('artifact_count', 0)} stale={summary.get('stale_count', 0)}")
        for item in summary.get("stale_artifacts") or []:
            lines.append(f"- stale {item.get('pattern')}: {', '.join(item.get('files') or [])}")
    lines.extend(["", "## Agent Layer", ""])
    for role, spec in (plan.get("agent_layer") or {}).items():
        lines.append(
            f"- {role}: {spec.get('purpose')} "
            f"(may_call_models={'yes' if spec.get('may_call_models') else 'no'})"
        )
    return "\n".join(lines) + "\n"


def write_plan(root: str, plan: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "novel_pipeline_plan.json")
    md_path = os.path.join(out_dir, "novel_pipeline_plan.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(plan))
    if append_event:
        append_event(
            root,
            event_type="pipeline_plan_written",
            tool="novel/scripts/pipeline_runner.py",
            outputs=[json_path, md_path],
            metadata={"kind": PIPELINE_PLAN_KIND, "next_stage": plan.get("next_stage")},
        )
    return json_path, md_path


def run_dir(root: str) -> str:
    return os.path.join(root, "生产数据", "pipeline_runs")


def run_path(root: str, run_id: str) -> str:
    return os.path.join(run_dir(root), f"{run_id}.json")


def latest_run_id(root: str) -> str:
    paths = sorted(
        os.path.join(run_dir(root), name)
        for name in os.listdir(run_dir(root)) if name.endswith(".json")
    ) if os.path.isdir(run_dir(root)) else []
    if not paths:
        raise FileNotFoundError("no pipeline run found; use --start-run first")
    return os.path.splitext(os.path.basename(paths[-1]))[0]


def _workflow_status(evaluated_status: str) -> str:
    if evaluated_status == "done":
        return "completed"
    if evaluated_status == "ready":
        return "pending"
    return "blocked"


def _overall_status(stages: list[dict[str, Any]]) -> str:
    statuses = [stage.get("status") for stage in stages]
    if statuses and all(status in {"completed", "skipped"} for status in statuses):
        return "completed"
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "running" for status in statuses):
        return "running"
    if any(status == "pending" for status in statuses):
        return "open"
    return "blocked"


def create_run(root: str, *, run_id: str | None = None, actor: str = "") -> dict[str, Any]:
    root = os.path.abspath(root)
    plan = dry_run_plan(root)
    run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    stages = []
    for stage in plan.get("stages") or []:
        stages.append({
            "key": stage["key"],
            "label": stage["label"],
            "agent_role": stage.get("agent_role"),
            "status": _workflow_status(stage.get("status") or "blocked"),
            "evaluated_status": stage.get("status"),
            "attempts": 0,
            "claimed_by": "",
            "blocked_reason": "; ".join(stage.get("missing_inputs") or []),
            "started_at": "",
            "completed_at": "",
            "updated_at": now(),
        })
    run = {
        "schema_version": 1,
        "kind": RUN_KIND,
        "run_id": run_id,
        "status": _overall_status(stages),
        "created_at": now(),
        "updated_at": now(),
        "created_by": actor,
        "project_root": root,
        "plan_path": "",
        "stages": stages,
        "next_stage": next((stage["key"] for stage in stages if stage["status"] == "pending"), None),
    }
    os.makedirs(run_dir(root), exist_ok=True)
    write_json(run_path(root, run_id), run)
    if append_event:
        append_event(
            root,
            event_type="pipeline_run_started",
            tool="novel/scripts/pipeline_runner.py",
            outputs=[run_path(root, run_id)],
            metadata={"run_id": run_id, "actor": actor, "next_stage": run.get("next_stage")},
        )
    return run


def load_run(root: str, run_id: str) -> dict[str, Any]:
    run = load_json(run_path(os.path.abspath(root), run_id))
    if not isinstance(run, dict) or run.get("kind") != RUN_KIND:
        raise ValueError(f"not a pipeline run: {run_id}")
    return run


def update_run_stage(
    root: str,
    run_id: str,
    stage_key: str,
    action: str,
    *,
    actor: str = "",
    reason: str = "",
) -> dict[str, Any]:
    root = os.path.abspath(root)
    run = load_run(root, run_id)
    stage = next((item for item in run.get("stages") or [] if item.get("key") == stage_key), None)
    if not stage:
        raise KeyError(f"unknown run stage: {stage_key}")
    event_type = f"pipeline_stage_{action}"
    if action == "claimed":
        if stage.get("status") not in {"pending", "blocked", "failed"}:
            raise ValueError(f"stage {stage_key} cannot be claimed from {stage.get('status')}")
        stage["status"] = "running"
        stage["claimed_by"] = actor
        stage["attempts"] = int(stage.get("attempts") or 0) + 1
        stage["started_at"] = stage.get("started_at") or now()
        stage["blocked_reason"] = ""
    elif action == "completed":
        stage["status"] = "completed"
        stage["completed_at"] = now()
        stage["blocked_reason"] = ""
        # 防 run 文件单方面宣称完成：用 artifact 视图复核该阶段，disk 不支持就记 completion_warning
        # （可见、不静默；不硬拒，避免误伤产物非 glob 可检的阶段）。
        try:
            plan = dry_run_plan(root)
            disk = next((s for s in plan.get("stages") or [] if s.get("key") == stage_key), None)
            disk_status = disk.get("status") if disk else None
            if disk_status and disk_status != "done":
                stage["completion_warning"] = (
                    f"run 标记 completed，但 artifact 视图判 {stage_key}={disk_status}（产物未达完成）；请核对 _进度.md / 产物。")
            else:
                stage.pop("completion_warning", None)
        except Exception:
            pass
    elif action == "failed":
        stage["status"] = "failed"
        stage["blocked_reason"] = reason or "failed"
    elif action == "blocked":
        stage["status"] = "blocked"
        stage["blocked_reason"] = reason or "blocked"
    elif action == "skipped":
        stage["status"] = "skipped"
        stage["blocked_reason"] = reason
    else:
        raise ValueError(f"unsupported action: {action}")
    stage["updated_at"] = now()
    run["updated_at"] = now()
    run["status"] = _overall_status(run.get("stages") or [])
    run["next_stage"] = next((item["key"] for item in run.get("stages") or [] if item.get("status") == "pending"), None)
    write_json(run_path(root, run_id), run)
    if append_event:
        outputs = [run_path(root, run_id)]
        append_event(
            root,
            event_type=event_type,
            tool="novel/scripts/pipeline_runner.py",
            outputs=outputs,
            metadata={
                "run_id": run_id,
                "stage_key": stage_key,
                "actor": actor,
                "reason": reason,
                "status": stage["status"],
            },
        )
    return run


def render_run_markdown(run: dict[str, Any]) -> str:
    lines = [
        "# Novel Pipeline Run",
        "",
        f"- run_id：{run.get('run_id')}",
        f"- status：{run.get('status')}",
        f"- next_stage：{run.get('next_stage') or 'none'}",
        "",
        "| status | stage | role | attempts | claimed_by | blocked_reason |",
        "|---|---|---|---:|---|---|",
    ]
    for stage in run.get("stages") or []:
        lines.append(
            f"| {stage.get('status')} | {stage.get('key')} / {stage.get('label')} | "
            f"{stage.get('agent_role') or ''} | {stage.get('attempts') or 0} | "
            f"{stage.get('claimed_by') or ''} | {stage.get('blocked_reason') or ''} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="novel deterministic pipeline runner")
    parser.add_argument("project_root", nargs="?", help="作品根；--registry-only 时可省略")
    parser.add_argument("--registry-only", action="store_true", help="只打印 pipeline registry")
    parser.add_argument("--artifact-graph", action="store_true", help="打印 artifact graph 与 stale 检测")
    parser.add_argument("--handoff", metavar="STAGE", help="打印指定阶段的 specialist handoff contract")
    parser.add_argument("--json", action="store_true", help="打印 JSON")
    parser.add_argument("--write-plan", action="store_true", help="写 生产数据/novel_pipeline_plan.{json,md}")
    parser.add_argument("--start-run", action="store_true", help="创建可恢复 pipeline run 状态文件")
    parser.add_argument("--run-id", help="要读取或更新的 run id；省略时 --show-run 使用最新 run")
    parser.add_argument("--show-run", action="store_true", help="展示 pipeline run 状态")
    parser.add_argument("--claim-stage", metavar="STAGE", help="把阶段置为 running，并记录 claimed_by/attempt")
    parser.add_argument("--complete-stage", metavar="STAGE", help="把阶段置为 completed")
    parser.add_argument("--fail-stage", metavar="STAGE", help="把阶段置为 failed")
    parser.add_argument("--block-stage", metavar="STAGE", help="把阶段置为 blocked")
    parser.add_argument("--skip-stage", metavar="STAGE", help="把阶段置为 skipped")
    parser.add_argument("--agent", default="", help="stage claim/update actor")
    parser.add_argument("--reason", default="", help="fail/block/skip reason")
    args = parser.parse_args(argv)

    if args.registry_only:
        payload = registry_payload()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not args.project_root:
        parser.error("project_root is required unless --registry-only is used")
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    if args.artifact_graph:
        payload = artifact_graph(root)
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if payload.get("stale_artifacts") else 0
    if args.handoff:
        try:
            payload = handoff_contract(root, args.handoff)
        except KeyError as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.start_run:
        run = create_run(root, actor=args.agent)
        print(json.dumps(run, ensure_ascii=False, indent=2) if args.json else render_run_markdown(run))
        return 0
    if args.show_run:
        try:
            run = load_run(root, args.run_id or latest_run_id(root))
        except (OSError, ValueError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(json.dumps(run, ensure_ascii=False, indent=2) if args.json else render_run_markdown(run))
        return 0
    stage_actions = [
        ("claimed", args.claim_stage),
        ("completed", args.complete_stage),
        ("failed", args.fail_stage),
        ("blocked", args.block_stage),
        ("skipped", args.skip_stage),
    ]
    selected = [(action, stage) for action, stage in stage_actions if stage]
    if selected:
        if len(selected) != 1:
            print("[err] stage update flags are mutually exclusive", file=sys.stderr)
            return 2
        if not args.run_id:
            print("[err] stage update requires --run-id", file=sys.stderr)
            return 2
        action, stage_key = selected[0]
        try:
            run = update_run_stage(root, args.run_id, stage_key, action, actor=args.agent, reason=args.reason)
        except (OSError, ValueError, KeyError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(json.dumps(run, ensure_ascii=False, indent=2) if args.json else render_run_markdown(run))
        return 0
    plan = dry_run_plan(root)
    if args.write_plan:
        json_path, md_path = write_plan(root, plan)
        print(f"[ok] pipeline plan JSON → {json_path}")
        print(f"[ok] pipeline plan MD   → {md_path}")
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(plan))
    if any(stage["status"] == "blocked" for stage in plan["stages"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
