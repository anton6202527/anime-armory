#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Durable, boundary-aware producer loop for the novel pipeline.

The producer repeatedly consumes ``supervisor.decide_next_action``.  It may run
reversible deterministic repository commands and project-local specialist
adapters, but it never fabricates prose itself or cross final acceptance,
rights/compliance, budget, unsupported assignment, or circuit-breaker bounds.
Every real attempt is fed back to the supervisor circuit ledger.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import supervisor  # noqa: E402


KIND = "novel_producer_run"
REGISTRY_KIND = "novel_specialist_execution_adapter_registry"
REGISTRY_REL = Path("生产数据") / "novel_specialist_execution_adapters.json"
HARD_ACTIONS = {
    "final_acceptance",
    "complete_human_semantic_job",
    "circuit_breaker_tripped",
    "repair_semantic_job_assignment",
    "human_review_or_creation",
    "resolve_revision_conflicts",
}
SAFE_ROLES = {"workflow_orchestrator", "deterministic_runner", "local_tool"}
SPECIALIST_ROLES = set(supervisor.SEMANTIC_AGENT_ROLES)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def output_path(root: str | Path) -> Path:
    return Path(root) / "生产数据" / "producer" / "producer_run.json"


def request_path(root: str | Path, role: str, cycle: int) -> Path:
    safe_role = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in role) or "specialist"
    return Path(root) / "生产数据" / "producer" / "requests" / f"{cycle:03d}_{safe_role}.json"


def _available(argv: Sequence[str]) -> bool:
    if not argv:
        return False
    binary = Path(argv[0]).expanduser()
    if binary.is_absolute() or "/" in argv[0]:
        return binary.is_file() and os.access(binary, os.X_OK)
    return shutil.which(argv[0]) is not None


def run_argv(argv: Sequence[str], *, timeout: int = 1800) -> dict[str, Any]:
    if not _available(argv):
        return {"status": "failed", "returncode": 127, "error": f"command unavailable: {argv[0] if argv else ''}"}
    try:
        proc = subprocess.run(
            list(argv), cwd=str(REPO_ROOT), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {"status": "failed", "returncode": 124, "error": f"timeout: {exc}"}
    return {
        "status": "complete" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
    }


def parse_declared_command(command: str) -> list[str]:
    raw = str(command or "").strip()
    if not raw or "<" in raw or ">" in raw or "|" in raw or ";" in raw or "&&" in raw or "||" in raw:
        return []
    try:
        return shlex.split(raw)
    except ValueError:
        return []


def load_adapter(root: str | Path, role: str) -> dict[str, Any] | None:
    registry = _load_json(Path(root) / REGISTRY_REL)
    if registry.get("kind") not in {None, "", REGISTRY_KIND}:
        return None
    adapters = registry.get("adapters") if isinstance(registry.get("adapters"), Mapping) else {}
    raw = adapters.get(role) if isinstance(adapters, Mapping) else None
    if not isinstance(raw, Mapping):
        return None
    command = raw.get("command")
    tokens = [str(token) for token in command] if isinstance(command, list) else parse_declared_command(str(command or ""))
    if not tokens:
        return None
    return {
        "adapter_id": str(raw.get("adapter_id") or f"{role}_adapter_v1"),
        "command": tokens,
        "timeout_seconds": int(raw.get("timeout_seconds") or 1800),
    }


def make_specialist_request(root: str, action: Mapping[str, Any], cycle: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "novel_specialist_execution_request",
        "created_at": now_iso(),
        "project_root": root,
        "cycle": cycle,
        "stage": action.get("next_stage"),
        "role": action.get("agent_role"),
        "action": action.get("action"),
        "reason": action.get("reason"),
        "handoff": action.get("handoff"),
        "context": action.get("context") or [],
        "recommended_commands": action.get("recommended_commands") or [],
        "completion_contract": (
            "complete the declared semantic artifact and its verification/writeback; "
            "never approve rights, spend, publication, or final acceptance"
        ),
    }


def make_registry_specialist_executor(root: str) -> Callable[[Mapping[str, Any], int], dict[str, Any]]:
    def execute(action: Mapping[str, Any], cycle: int) -> dict[str, Any]:
        role = str(action.get("agent_role") or "")
        adapter = load_adapter(root, role)
        if adapter is None:
            return {"status": "adapter_required", "error": f"no specialist adapter registered for {role}"}
        req = make_specialist_request(root, action, cycle)
        path = request_path(root, role, cycle)
        _atomic_json(path, req)
        argv = [token.replace("{request}", str(path)) for token in adapter["command"]]
        if not any("{request}" in token for token in adapter["command"]):
            argv.extend(["--request", str(path)])
        result = run_argv(argv, timeout=adapter["timeout_seconds"])
        result.update({"adapter_id": adapter["adapter_id"], "request": str(path)})
        return result
    return execute


def _identity(action: Mapping[str, Any]) -> str:
    jobs = ((action.get("signals") or {}).get("open_semantic_jobs") or []) if isinstance(action.get("signals"), Mapping) else []
    first_job = jobs[0].get("path") if jobs and isinstance(jobs[0], Mapping) else ""
    return "::".join((
        str(action.get("status") or ""), str(action.get("action") or ""),
        str(action.get("next_stage") or ""), str(first_job or ""),
    ))


def run_loop(
    root: str,
    *,
    max_cycles: int = 60,
    max_stagnant_cycles: int = 2,
    planner: Callable[..., dict[str, Any]] = supervisor.decide_next_action,
    command_executor: Callable[[Sequence[str]], dict[str, Any]] = run_argv,
    specialist_executor: Callable[[Mapping[str, Any], int], dict[str, Any]] | None = None,
    recorder: Callable[..., dict[str, Any]] = supervisor.record_execution_event,
    execute: bool = True,
) -> dict[str, Any]:
    root = str(Path(root).resolve())
    events: list[dict[str, Any]] = []
    previous = ""
    stagnant = 0
    status, stop_reason = "stopped", "max_cycles"
    final_action: dict[str, Any] = {}

    for cycle in range(1, max(1, max_cycles) + 1):
        final_action = planner(root, write_pipeline_plan=False)
        identity = _identity(final_action)
        stagnant = stagnant + 1 if identity == previous else 0
        previous = identity
        action_name = str(final_action.get("action") or "")
        stage = str(final_action.get("next_stage") or action_name or "unknown")
        event: dict[str, Any] = {"cycle": cycle, "at": now_iso(), "identity": identity, "stage": stage}

        if final_action.get("status") == "complete":
            event["execution"] = "terminal"
            events.append(event)
            status, stop_reason = "complete", "accepted"
            break
        if action_name in HARD_ACTIONS or final_action.get("status") == "needs_human":
            event["execution"] = "hard_boundary"
            events.append(event)
            stop_reason = action_name or "needs_human"
            break
        if final_action.get("status") == "blocked":
            event["execution"] = "blocked"
            events.append(event)
            stop_reason = action_name or "blocked"
            break
        if not execute:
            event["execution"] = "plan_only"
            events.append(event)
            stop_reason = "plan_only"
            break
        if stagnant >= max_stagnant_cycles:
            event["execution"] = "non_convergent"
            events.append(event)
            stop_reason = "non_convergent"
            break

        role = str(final_action.get("agent_role") or "workflow_orchestrator")
        if role in SPECIALIST_ROLES:
            if specialist_executor is None:
                event["execution"] = "specialist_adapter_required"
                events.append(event)
                stop_reason = "specialist_adapter_required"
                break
            recorder(root, stage_key=stage, result="started", reason=action_name)
            result = specialist_executor(final_action, cycle)
            ok = result.get("status") == "complete"
            recorder(root, stage_key=stage, result="succeeded" if ok else "failed", reason=str(result.get("error") or action_name))
            event.update({"execution": "specialist_adapter", "result": result})
            events.append(event)
            if not ok:
                stop_reason = str(result.get("status") or "specialist_failed")
                break
            continue

        if role not in SAFE_ROLES and final_action.get("status") != "self_healing":
            event["execution"] = "unsupported_role"
            events.append(event)
            stop_reason = "unsupported_role"
            break
        commands = [parse_declared_command(command) for command in final_action.get("recommended_commands") or []]
        if not commands or any(not argv for argv in commands):
            event["execution"] = "safe_command_required"
            events.append(event)
            stop_reason = "safe_command_required"
            break
        recorder(root, stage_key=stage, result="started", reason=action_name)
        results = [command_executor(argv) for argv in commands]
        ok = all(result.get("status") == "complete" for result in results)
        reason = next((str(result.get("error") or result.get("stderr") or "") for result in results if result.get("status") != "complete"), action_name)
        recorder(root, stage_key=stage, result="succeeded" if ok else "failed", reason=reason)
        event.update({"execution": "deterministic_commands", "results": results})
        events.append(event)
        if not ok:
            stop_reason = "execution_failed"
            break

    payload = {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": now_iso(),
        "project_root": root,
        "status": status,
        "stop_reason": stop_reason,
        "cycles": len(events),
        "events": events,
        "final_action": final_action,
        "state_scope": "execution_receipt_only",
        "business_state_source": "_进度.md",
        "completion_authority": "导出/completion_verdict.json",
    }
    _atomic_json(output_path(root), payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project_root")
    ap.add_argument("--max-cycles", type=int, default=60)
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = str(Path(ns.project_root).expanduser().resolve())
    if not Path(root).is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    result = run_loop(
        root, max_cycles=ns.max_cycles, execute=not ns.plan_only,
        specialist_executor=make_registry_specialist_executor(root),
    )
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={result['status']} stop_reason={result['stop_reason']} cycles={result['cycles']}")
        print(output_path(root))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
