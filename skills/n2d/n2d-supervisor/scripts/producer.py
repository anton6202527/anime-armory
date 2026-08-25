#!/usr/bin/env python3
"""Durable n2d producer loop.

Owns repeated ``run.py next`` evaluation until the canonical workflow is done
or reaches a real authorization/compliance/publish/acceptance boundary.  It
does not invent status, approve spend, or call a provider directly: paid work
still crosses the existing n2d-batch authorization-consumption boundary.

Creative stages are executed through an optional project-local, vendor-neutral
specialist wrapper registry.  An interactive host agent may instead consume
the same request and keep the loop alive itself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import supervisor  # noqa: E402


KIND = "n2d_producer_run"
VERSION = 1
REGISTRY_KIND = "n2d_specialist_execution_adapter_registry"
REGISTRY_REL = Path("生产数据") / "specialist_execution_adapters.json"
HARD_BOUNDARIES = {
    "needs_payment_confirm",
    "needs_choice",
    "needs_compliance",
    "needs_acceptance_signoff",
    "capability_evidence_required",
    "env_missing",
    "unknown_stage",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value or "全集")) or "全集"


def output_path(root: str | Path, episode: str) -> Path:
    return Path(root) / "生产数据" / "producer" / f"producer_run_{_safe_slug(episode)}.json"


def request_path(root: str | Path, episode: str, stage: str, cycle: int) -> Path:
    return (
        Path(root) / "生产数据" / "producer" / "requests"
        / f"{_safe_slug(episode)}_{_safe_slug(stage)}_{cycle:03d}.json"
    )


def load_specialist_adapter(root: str | Path, specialist_name: str) -> Optional[Dict[str, Any]]:
    registry = _load_json(Path(root) / REGISTRY_REL)
    if registry.get("kind") not in {None, "", REGISTRY_KIND}:
        return None
    adapters = registry.get("adapters") if isinstance(registry.get("adapters"), Mapping) else {}
    raw = adapters.get(specialist_name) if isinstance(adapters, Mapping) else None
    if not isinstance(raw, Mapping):
        return None
    command = raw.get("command")
    tokens = [str(value) for value in command] if isinstance(command, list) else shlex.split(str(command or ""))
    if not tokens:
        return None
    return {
        "adapter_id": str(raw.get("adapter_id") or f"{specialist_name}_wrapper_v1"),
        "specialist": specialist_name,
        "command": tokens,
        "timeout_seconds": int(raw.get("timeout_seconds") or 900),
    }


def build_specialist_request(root: str, plan: Mapping[str, Any], cycle: int) -> Dict[str, Any]:
    next_action = plan.get("next_action") if isinstance(plan.get("next_action"), Mapping) else {}
    dispatch = plan.get("dispatch") if isinstance(plan.get("dispatch"), Mapping) else {}
    frontier = next_action.get("frontier") if isinstance(next_action.get("frontier"), Mapping) else {}
    specialist = dispatch.get("specialist") if isinstance(dispatch.get("specialist"), Mapping) else {}
    return {
        "kind": "n2d_specialist_execution_request",
        "version": 1,
        "root": root,
        "episode": str(frontier.get("ep") or plan.get("episode") or ""),
        "stage_key": str(frontier.get("stage_key") or dispatch.get("stage_key") or ""),
        "cycle": cycle,
        "specialist": specialist,
        "next_action": next_action,
        "constraints": (dispatch.get("runtime_guardrails") or {}).get("carried_constraints") or {},
        "constraints_fingerprint": (dispatch.get("runtime_guardrails") or {}).get("constraints_fingerprint") or "",
        "completion_contract": (
            "produce the declared stage artifacts, run the stage verification/writeback contract, "
            "and return JSON status=complete; never approve spend, compliance, publish, or final acceptance"
        ),
    }


def _command_available(argv: Sequence[str]) -> bool:
    if not argv:
        return False
    binary = Path(argv[0]).expanduser()
    if binary.is_absolute() or "/" in argv[0]:
        return binary.is_file() and os.access(binary, os.X_OK)
    from shutil import which
    return which(argv[0]) is not None


def run_argv(argv: Sequence[str], *, timeout: int = 1800) -> Dict[str, Any]:
    if not _command_available(argv):
        return {"status": "failed", "returncode": 127, "error": f"command unavailable: {argv[0] if argv else ''}"}
    try:
        proc = subprocess.run(list(argv), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return {"status": "failed", "returncode": 124, "error": f"timeout: {exc}"}
    return {
        "status": "complete" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
    }


def _declared_command(card: Mapping[str, Any]) -> list[str]:
    raw = str(card.get("exact_command") or card.get("command") or "").strip()
    if not raw or "<" in raw or ">" in raw:
        return []
    try:
        return shlex.split(raw)
    except ValueError:
        return []


def _frontier_identity(plan: Mapping[str, Any]) -> str:
    action = plan.get("next_action") if isinstance(plan.get("next_action"), Mapping) else {}
    frontier = action.get("frontier") if isinstance(action.get("frontier"), Mapping) else {}
    graph = ((action.get("action_card") or {}).get("context_pack") or {}) if isinstance(action.get("action_card"), Mapping) else {}
    return "::".join((
        str(frontier.get("ep") or ""),
        str(frontier.get("stage_key") or ""),
        str(action.get("stop_reason") or ""),
        str(graph.get("input_fingerprint") or ""),
    ))


def run_loop(
    root: str,
    episode: str = "",
    *,
    max_cycles: int = 40,
    max_stagnant_cycles: int = 2,
    planner: Callable[..., Dict[str, Any]] = supervisor.build_plan,
    command_executor: Callable[..., Dict[str, Any]] = run_argv,
    specialist_executor: Optional[Callable[[Mapping[str, Any], int], Dict[str, Any]]] = None,
    execute: bool = True,
) -> Dict[str, Any]:
    events: list[Dict[str, Any]] = []
    previous_identity = ""
    stagnant = 0
    final_plan: Dict[str, Any] = {}
    status = "stopped"
    stop_reason = "max_cycles"

    for cycle in range(1, max(1, max_cycles) + 1):
        final_plan = planner(root, episode or None, auto=True, track_rounds=False)
        action = final_plan.get("next_action") if isinstance(final_plan.get("next_action"), Mapping) else {}
        dispatch = final_plan.get("dispatch") if isinstance(final_plan.get("dispatch"), Mapping) else {}
        reason = str(action.get("stop_reason") or final_plan.get("summary", {}).get("stop_reason") or "")
        identity = _frontier_identity(final_plan)
        stagnant = stagnant + 1 if identity == previous_identity else 0
        previous_identity = identity
        event: Dict[str, Any] = {
            "cycle": cycle,
            "at": now_iso(),
            "identity": identity,
            "stop_reason": reason,
            "stage_key": str(dispatch.get("stage_key") or ""),
        }

        if reason == "done":
            event["action"] = "terminal"
            events.append(event)
            status, stop_reason = "complete", "done"
            break
        if reason in HARD_BOUNDARIES:
            event["action"] = "hard_boundary"
            events.append(event)
            stop_reason = reason
            break
        if not execute:
            event["action"] = "plan_only"
            events.append(event)
            stop_reason = reason or "plan_only"
            break
        if stagnant >= max_stagnant_cycles:
            event["action"] = "non_convergent"
            events.append(event)
            stop_reason = "non_convergent"
            break

        card = action.get("action_card") if isinstance(action.get("action_card"), Mapping) else {}
        recipe = card.get("repair_recipe") if isinstance(card.get("repair_recipe"), Mapping) else {}
        repair_commands = [str(value) for value in recipe.get("safe_auto_commands") or [] if str(value).strip()]
        if repair_commands and not recipe.get("auto_attempted"):
            results = [command_executor(shlex.split(command)) for command in repair_commands]
            event.update({"action": "auto_repair", "results": results})
            events.append(event)
            if any(result.get("status") != "complete" for result in results):
                stop_reason = "auto_repair_failed"
                break
            continue

        if dispatch.get("should_call_specialist"):
            if reason == "needs_agent_gen":
                if specialist_executor is None:
                    event["action"] = "specialist_adapter_required"
                    events.append(event)
                    stop_reason = "specialist_adapter_required"
                    break
                result = specialist_executor(final_plan, cycle)
                event.update({"action": "specialist", "result": result})
            elif dispatch.get("authorized_batch_execution") or dispatch.get("safe_local_execution") or reason == "needs_stage_execution":
                argv = _declared_command(card)
                if not argv:
                    event["action"] = "declared_command_missing"
                    events.append(event)
                    stop_reason = "declared_command_missing"
                    break
                result = command_executor(argv)
                event.update({"action": "stage_execution", "result": result})
            else:
                result = {"status": "failed", "error": "dispatch not executable under current authorization"}
                event.update({"action": "dispatch_not_executable", "result": result})
            events.append(event)
            if result.get("status") != "complete":
                stop_reason = "execution_failed"
                break
            continue

        event["action"] = "repair_or_adapter_required" if reason.startswith("blocked_by_") or reason == "prework_failed" else "idle"
        events.append(event)
        stop_reason = reason or "idle"
        break

    payload = {
        "kind": KIND,
        "version": VERSION,
        "root": root,
        "episode": episode,
        "generated_at": now_iso(),
        "status": status,
        "stop_reason": stop_reason,
        "cycles": len(events),
        "events": events,
        "final_plan": final_plan,
        "authority": "derived execution receipt; canonical completion remains run.py done + release verdict",
    }
    _atomic_json(output_path(root, episode or "全集"), payload)
    return payload


def make_registry_specialist_executor(root: str) -> Callable[[Mapping[str, Any], int], Dict[str, Any]]:
    def execute(plan: Mapping[str, Any], cycle: int) -> Dict[str, Any]:
        dispatch = plan.get("dispatch") if isinstance(plan.get("dispatch"), Mapping) else {}
        specialist = dispatch.get("specialist") if isinstance(dispatch.get("specialist"), Mapping) else {}
        name = str(specialist.get("name") or "")
        adapter = load_specialist_adapter(root, name)
        if adapter is None:
            return {"status": "failed", "error": f"no specialist adapter registered for {name}"}
        action = plan.get("next_action") if isinstance(plan.get("next_action"), Mapping) else {}
        frontier = action.get("frontier") if isinstance(action.get("frontier"), Mapping) else {}
        request = build_specialist_request(root, plan, cycle)
        path = request_path(root, str(frontier.get("ep") or "全集"), str(frontier.get("stage_key") or "unknown"), cycle)
        _atomic_json(path, request)
        argv = [token.replace("{request}", str(path)) for token in adapter["command"]]
        if not any("{request}" in token for token in adapter["command"]):
            argv.extend(["--request", str(path)])
        result = run_argv(argv, timeout=adapter["timeout_seconds"])
        result.update({"adapter_id": adapter["adapter_id"], "request": str(path)})
        return result
    return execute


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode", nargs="?", default="")
    ap.add_argument("--max-cycles", type=int, default=40)
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = str(Path(ns.root).expanduser().resolve())
    result = run_loop(
        root,
        ns.episode,
        max_cycles=ns.max_cycles,
        specialist_executor=make_registry_specialist_executor(root),
        execute=not ns.plan_only,
    )
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={result['status']} stop_reason={result['stop_reason']} cycles={result['cycles']}")
        print(output_path(root, ns.episode or "全集"))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
