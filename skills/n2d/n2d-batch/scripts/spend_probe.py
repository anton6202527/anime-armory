#!/usr/bin/env python3
"""Read-only probe for current n2d v2 phase-envelope capacity.

The probe rebuilds the same task/producer execution binding used by ``runner.py`` and calls
``verify`` only.  It never claims a queue task, consumes a ledger row, executes a provider, or
issues/expands authorization.  The batch runner remains the sole consumption boundary.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Dict, Optional, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def _load_runner() -> ModuleType:
    path = SCRIPT_DIR / "runner.py"
    spec = importlib.util.spec_from_file_location("n2d_batch_runner_for_spend_probe", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load n2d batch runner: {path}")
    module = importlib.util.module_from_spec(spec)
    # Register before execution so any runtime type/introspection machinery sees the same
    # module object.  The unique name also avoids collisions in mixed-line pytest runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _plan_projection(task: Dict[str, Any]) -> Dict[str, Any]:
    """Immutable planning fields used to reject a stale active queue row."""
    return {
        key: task.get(key)
        for key in (
            "idempotency_key", "episode", "stage_key", "command", "reason", "estimated_cost",
            "rerun_scope", "affected_artifacts", "affected_shots", "finding_fingerprints",
        )
    }


def _plan_digest(task: Dict[str, Any]) -> str:
    raw = json.dumps(
        _plan_projection(task), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _task_for(runtime: ModuleType, root: str, episode: str, stage: str) -> Dict[str, Any]:
    normalize = runtime.queue_mod.normalize_episode
    wanted_episode = normalize(episode)
    planned = runtime.queue_mod.route_tasks(
        root,
        episodes={wanted_episode},
        stage_filters={stage},
        cost_estimates=runtime.queue_mod.load_cost_estimates(root),
        max_retries=1,
    )
    if not planned:
        raise RuntimeError(f"no current batch task for {wanted_episode}/{stage}")
    current = deepcopy(planned[0])
    candidates = []
    try:
        ledger = runtime.queue_mod.load_queue(root)
        candidates = [
            task
            for task in (ledger.get("tasks") or [])
            if isinstance(task, dict)
            and normalize(str(task.get("episode") or "")) == wanted_episode
            and str(task.get("stage_key") or "") == stage
            and str(task.get("status") or "") in runtime.queue_mod.ACTIVE_STATUSES
        ]
    except (FileNotFoundError, ValueError, OSError):
        candidates = []
    if candidates:
        rank = {"running": 0, "retry_queued": 1, "queued": 2, "qa_blocked": 3}
        candidates.sort(
            key=lambda task: (
                rank.get(str(task.get("status") or ""), 9),
                int(task.get("priority") or 10**9),
                str(task.get("id") or ""),
            )
        )
        exact = next(
            (
                candidate
                for candidate in candidates
                if _plan_projection(candidate) == _plan_projection(current)
            ),
            None,
        )
        if exact is not None:
            task = deepcopy(exact)
            task["_probe_current_plan_digest"] = _plan_digest(current)
            return task
    current["_probe_current_plan_digest"] = _plan_digest(current)
    return current


def probe(
    root: str,
    episode: str,
    stage: str,
    *,
    config_path: Optional[str] = None,
    runtime: Optional[ModuleType] = None,
) -> Dict[str, Any]:
    runtime = runtime or _load_runner()
    root = str(Path(root).expanduser().resolve())
    try:
        task = _task_for(runtime, root, episode, stage)
        config = runtime.load_config(root, config_path)
        runtime._bind_execution_context(task, config)
        command = runtime.resolve_command(root, task, config, None)
        task["resolved_command"] = command
        runtime.bind_production_execution_context(root, task, config, command)
        producer_issue = str(task.get("_runner_producer_contract_issue") or "").strip()
        if producer_issue:
            raise RuntimeError(f"current producer contract unavailable: {producer_issue}")
        authorization = runtime._authorization_from_config(task, config, root)
        if not isinstance(authorization, dict) or authorization.get("version") != 2:
            return {
                "status": "not_authorized",
                "read_only": True,
                "consumed": False,
                "episode": runtime.queue_mod.normalize_episode(episode),
                "stage": stage,
                "task_id": str(task.get("id") or ""),
                "current_plan_digest": str(task.get("_probe_current_plan_digest") or ""),
                "issue": "no v2 phase spend envelope resolved for current task/stage",
            }
        request = runtime._phase_consumption_kwargs(task)
        verification = runtime.spend_envelope_mod.verify(root, authorization, **request)
        status = "authorized" if verification.get("status") == "pass" else "blocked"
        return {
            "status": status,
            "read_only": True,
            "consumed": False,
            "episode": runtime.queue_mod.normalize_episode(episode),
            "stage": stage,
            "task_id": str(task.get("id") or ""),
            "current_plan_digest": str(task.get("_probe_current_plan_digest") or ""),
            "attempt_id": str(request.get("attempt_id") or ""),
            "model": str(request.get("model") or ""),
            "channel": str(request.get("channel") or ""),
            "input_sha256": str(request.get("input_sha256") or ""),
            "envelope_id": str(authorization.get("envelope_id") or ""),
            "authorization_digest": str(authorization.get("authorization_digest") or ""),
            "verification": verification,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "read_only": True,
            "consumed": False,
            "episode": str(episode),
            "stage": str(stage),
            "issue": f"{type(exc).__name__}: {exc}",
        }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root")
    parser.add_argument("episode")
    parser.add_argument("stage")
    parser.add_argument("--config")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = probe(args.root, args.episode, args.stage, config_path=args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") == "authorized" else 2


if __name__ == "__main__":
    raise SystemExit(main())
