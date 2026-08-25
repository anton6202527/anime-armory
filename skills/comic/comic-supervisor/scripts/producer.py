#!/usr/bin/env python3
"""Durable, boundary-aware Comic producer loop."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import supervisor  # noqa: E402


REGISTRY_REL = Path("生产数据") / "comic_specialist_execution_adapters.json"
REGISTRY_KIND = "comic_specialist_execution_adapter_registry"
SPECIALIST_ROLES = {"story_editor", "comic_writer", "visual_qc_agent", "quality_editor"}
HARD_ACTIONS = {"final_acceptance", "rights_or_release_boundary", "budget_authorization", "irreversible_publish"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def parse_command(command: Any) -> list[str]:
    if isinstance(command, list):
        tokens = [str(item) for item in command]
    else:
        raw = str(command or "").strip()
        if not raw or any(mark in raw for mark in ("|", ";", "&&", "||", "`", "$(", ">", "<")):
            return []
        try:
            tokens = shlex.split(raw)
        except ValueError:
            return []
    if not tokens or any("<" in token or ">" in token for token in tokens):
        return []
    return tokens


def run_argv(argv: Sequence[str], *, timeout: int = 1800) -> dict[str, Any]:
    if not argv:
        return {"status": "failed", "returncode": 127, "error": "empty command"}
    binary = Path(argv[0]).expanduser()
    if not ((binary.is_absolute() or "/" in argv[0]) and binary.is_file()) and not shutil.which(argv[0]):
        return {"status": "failed", "returncode": 127, "error": f"command unavailable: {argv[0]}"}
    try:
        proc = subprocess.run(list(argv), cwd=str(REPO), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return {"status": "failed", "returncode": 124, "error": f"timeout: {exc}"}
    return {
        "status": "complete" if proc.returncode == 0 else "failed", "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:], "stderr": (proc.stderr or "")[-4000:],
    }


def _adapter(root: Path, role: str) -> dict[str, Any] | None:
    registry = _load(root / REGISTRY_REL)
    if registry.get("kind") not in {None, "", REGISTRY_KIND}:
        return None
    raw = (registry.get("adapters") or {}).get(role) if isinstance(registry.get("adapters"), Mapping) else None
    if not isinstance(raw, Mapping):
        return None
    command = parse_command(raw.get("command"))
    if not command:
        return None
    return {"adapter_id": str(raw.get("adapter_id") or role), "command": command, "timeout": int(raw.get("timeout_seconds") or 1800)}


def _request(root: Path, chapter: str, action: Mapping[str, Any], cycle: int) -> Path:
    role = str(action.get("agent_role") or "specialist")
    path = root / "生产数据" / "producer" / chapter / "requests" / f"{cycle:03d}_{role}.json"
    packet = {
        "schema_version": 1, "kind": "comic_specialist_execution_request", "created_at": now_iso(),
        "project_root": str(root), "chapter": chapter, "cycle": cycle, "role": role,
        "action": action.get("action"), "reason": action.get("reason"),
        "issues": action.get("issues") or [], "visual_review_packet": action.get("visual_review_packet") or {},
        "recommended_commands": action.get("recommended_commands") or [],
        "completion_command": action.get("completion_command") or "",
        "completion_contract": "mutate only declared reversible artifacts, verify current SHA, never approve spend/rights/publication/final acceptance",
    }
    _atomic(path, packet)
    return path


def specialist_executor(root: Path, chapter: str, action: Mapping[str, Any], cycle: int) -> dict[str, Any]:
    role = str(action.get("agent_role") or "")
    adapter = _adapter(root, role)
    if adapter is None:
        return {"status": "adapter_required", "error": f"no project specialist adapter registered for {role}"}
    request = _request(root, chapter, action, cycle)
    command = [token.replace("{request}", str(request)) for token in adapter["command"]]
    if not any("{request}" in token for token in adapter["command"]):
        command += ["--request", str(request)]
    result = run_argv(command, timeout=adapter["timeout"])
    result.update({"adapter_id": adapter["adapter_id"], "request": str(request)})
    return result


def _identity(action: Mapping[str, Any]) -> str:
    return "::".join(str(action.get(key) or "") for key in ("status", "action", "next_stage", "panel_id"))


def run_loop(
    root: str | Path,
    chapter: str,
    *,
    max_cycles: int = 60,
    max_stagnant_cycles: int = 2,
    planner: Callable[[str | Path, str], dict[str, Any]] = supervisor.decide_next_action,
    command_executor: Callable[[Sequence[str]], dict[str, Any]] = run_argv,
    specialist: Callable[[Path, str, Mapping[str, Any], int], dict[str, Any]] = specialist_executor,
    execute: bool = True,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    events, previous, stagnant = [], "", 0
    status, stop_reason, final_action = "stopped", "max_cycles", {}
    for cycle in range(1, max(1, max_cycles) + 1):
        final_action = planner(root_path, chapter)
        identity = _identity(final_action)
        stagnant = stagnant + 1 if identity == previous else 0
        previous = identity
        event: dict[str, Any] = {"cycle": cycle, "at": now_iso(), "identity": identity, "action": final_action.get("action")}
        if final_action.get("status") == "complete":
            event["execution"] = "terminal"; events.append(event)
            status, stop_reason = "complete", "accepted"; break
        if final_action.get("action") in HARD_ACTIONS or final_action.get("hard_boundary") and final_action.get("status") in {"needs_human", "blocked"}:
            event["execution"] = "hard_boundary"; events.append(event)
            stop_reason = str(final_action.get("action") or "hard_boundary"); break
        if not execute:
            event["execution"] = "plan_only"; events.append(event); stop_reason = "plan_only"; break
        if stagnant >= max_stagnant_cycles:
            event["execution"] = "circuit_breaker"; events.append(event); stop_reason = "non_convergent"; break
        role = str(final_action.get("agent_role") or "")
        if role in SPECIALIST_ROLES:
            result = specialist(root_path, chapter, final_action, cycle)
            event.update({"execution": "specialist_adapter", "result": result}); events.append(event)
            if result.get("status") != "complete":
                stop_reason = str(result.get("status") or "specialist_failed"); break
            continue
        commands = [parse_command(item) for item in final_action.get("recommended_commands") or []]
        if not commands or any(not command for command in commands):
            event["execution"] = "safe_command_required"; events.append(event); stop_reason = "safe_command_required"; break
        results = [command_executor(command) for command in commands]
        event.update({"execution": "deterministic", "results": results}); events.append(event)
        if not all(row.get("status") == "complete" for row in results):
            stop_reason = "command_failed"; break
    payload = {
        "schema_version": 1, "kind": "comic_producer_run", "updated_at": now_iso(),
        "project_root": str(root_path), "chapter": chapter, "status": status,
        "stop_reason": stop_reason, "cycles": len(events), "events": events,
        "final_action": final_action,
    }
    out = root_path / "生产数据" / "producer" / chapter / "producer_run.json"
    _atomic(out, payload)
    journal = out.with_name("events.jsonl")
    journal.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in events), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--max-cycles", type=int, default=60)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_loop(args.project_root, args.chapter, max_cycles=args.max_cycles, execute=not args.plan_only)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"status={result['status']} stop_reason={result['stop_reason']} cycles={result['cycles']}")
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
