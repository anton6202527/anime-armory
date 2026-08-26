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
import contextlib
import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence
import uuid

try:
    import fcntl
except ImportError:  # pragma: no cover - n2d desktop/runtime is POSIX
    fcntl = None  # type: ignore[assignment]

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import supervisor  # noqa: E402


KIND = "n2d_producer_run"
VERSION = 2
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


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:  # pragma: no cover - unsupported filesystems
        pass


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value or "全集")) or "全集"


def output_path(root: str | Path, episode: str) -> Path:
    return Path(root) / "生产数据" / "producer" / f"producer_run_{_safe_slug(episode)}.json"


def journal_path(root: str | Path, episode: str) -> Path:
    return Path(root) / "生产数据" / "producer" / f"producer_events_{_safe_slug(episode)}.jsonl"


def work_unit_wal_path(root: str | Path, episode: str) -> Path:
    return Path(root) / "生产数据" / "producer" / f"work_units_{_safe_slug(episode)}.jsonl"


def work_unit_path(root: str | Path, episode: str, digest: str) -> Path:
    return (
        Path(root) / "生产数据" / "producer" / "work_units"
        / _safe_slug(episode) / f"{digest}.json"
    )


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    """Append and fsync one recovery checkpoint before the loop advances."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_dir(path.parent)


def _record_event(
    events: list[Dict[str, Any]], path: Path, run_id: str, event: Mapping[str, Any]
) -> None:
    row = {"run_id": run_id, **dict(event)}
    events.append(row)
    _append_jsonl(path, row)


@contextlib.contextmanager
def producer_lease(root: str | Path, episode: str):
    """Hold one exclusive project/episode lease for the complete producer run."""
    directory = Path(root) / "生产数据" / "producer"
    directory.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(episode)
    lock_path = directory / f"producer_{slug}.lock"
    handle = lock_path.open("a+")
    token = uuid.uuid4().hex
    acquired = False
    release_status = "released"
    lease = directory / f"producer_lease_{slug}.json"
    try:
        if fcntl is None:
            raise RuntimeError("producer_lease_unsupported")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("producer_busy") from exc
        acquired = True
        _atomic_json(lease, {
            "kind": "n2d_producer_lease",
            "version": 1,
            "project_root": str(Path(root).resolve()),
            "episode": episode,
            "lease_token": token,
            "pid": os.getpid(),
            "status": "held",
            "acquired_at": now_iso(),
        })
        try:
            yield token
        except BaseException:
            release_status = "aborted"
            raise
    finally:
        if acquired:
            try:
                _atomic_json(lease, {
                    "kind": "n2d_producer_lease",
                    "version": 1,
                    "project_root": str(Path(root).resolve()),
                    "episode": episode,
                    "lease_token": token,
                    "pid": os.getpid(),
                    "status": release_status,
                    "released_at": now_iso(),
                })
            except OSError:
                pass
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


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


def _frontier_material(plan: Mapping[str, Any]) -> Dict[str, Any]:
    """Stable evidence used only for crash reconciliation, never as completion."""
    action = plan.get("next_action") if isinstance(plan.get("next_action"), Mapping) else {}
    frontier = action.get("frontier") if isinstance(action.get("frontier"), Mapping) else {}
    card = action.get("action_card") if isinstance(action.get("action_card"), Mapping) else {}
    dispatch = plan.get("dispatch") if isinstance(plan.get("dispatch"), Mapping) else {}
    context = card.get("context_pack") if isinstance(card.get("context_pack"), Mapping) else {}
    envelope = (
        card.get("phase_spend_envelope")
        if isinstance(card.get("phase_spend_envelope"), Mapping) else {}
    )
    guardrails = (
        dispatch.get("runtime_guardrails")
        if isinstance(dispatch.get("runtime_guardrails"), Mapping) else {}
    )
    return {
        "episode": str(frontier.get("ep") or plan.get("episode") or ""),
        "stage_key": str(frontier.get("stage_key") or dispatch.get("stage_key") or ""),
        "frontier_state": str(frontier.get("state") or ""),
        "stop_reason": str(action.get("stop_reason") or ""),
        "input_fingerprint": str(context.get("input_fingerprint") or ""),
        "constraints_fingerprint": str(guardrails.get("constraints_fingerprint") or ""),
        "task_id": str(envelope.get("task_id") or ""),
        "plan_digest": str(envelope.get("current_plan_digest") or ""),
        "envelope_id": str(envelope.get("envelope_id") or ""),
        "authorization_digest": str(envelope.get("authorization_digest") or ""),
    }


def frontier_digest(plan: Mapping[str, Any]) -> str:
    return _digest(_frontier_material(plan))


def _work_unit_material(
    plan: Mapping[str, Any],
    episode: str,
    *,
    operation_kind: str,
    argv: Sequence[str],
    operation_index: int = 0,
) -> Dict[str, Any]:
    """Immutable logical side-effect identity; excludes cycle/time/run id."""
    action = plan.get("next_action") if isinstance(plan.get("next_action"), Mapping) else {}
    frontier = action.get("frontier") if isinstance(action.get("frontier"), Mapping) else {}
    card = action.get("action_card") if isinstance(action.get("action_card"), Mapping) else {}
    dispatch = plan.get("dispatch") if isinstance(plan.get("dispatch"), Mapping) else {}
    specialist = dispatch.get("specialist") if isinstance(dispatch.get("specialist"), Mapping) else {}
    context = card.get("context_pack") if isinstance(card.get("context_pack"), Mapping) else {}
    envelope = (
        card.get("phase_spend_envelope")
        if isinstance(card.get("phase_spend_envelope"), Mapping) else {}
    )
    guardrails = (
        dispatch.get("runtime_guardrails")
        if isinstance(dispatch.get("runtime_guardrails"), Mapping) else {}
    )
    return {
        "kind": "n2d_producer_work_unit",
        "version": 1,
        "episode": str(frontier.get("ep") or plan.get("episode") or episode),
        "stage_key": str(frontier.get("stage_key") or dispatch.get("stage_key") or ""),
        "stop_reason": str(action.get("stop_reason") or ""),
        "operation_kind": operation_kind,
        "operation_index": int(operation_index),
        "argv": [str(token) for token in argv],
        "specialist": {
            key: specialist.get(key)
            for key in ("name", "skill", "version") if specialist.get(key) is not None
        },
        "input_fingerprint": str(context.get("input_fingerprint") or ""),
        "constraints_fingerprint": str(guardrails.get("constraints_fingerprint") or ""),
        "authorization": {
            key: envelope.get(key)
            for key in (
                "envelope_id", "authorization_digest", "task_id", "current_plan_digest",
                "attempt_id", "model", "channel", "input_sha256",
            ) if envelope.get(key) is not None
        },
    }


def work_unit_digest(
    plan: Mapping[str, Any],
    episode: str,
    *,
    operation_kind: str,
    argv: Sequence[str],
    operation_index: int = 0,
) -> str:
    return _digest(_work_unit_material(
        plan, episode, operation_kind=operation_kind, argv=argv,
        operation_index=operation_index,
    ))


def _prepare_work_unit(
    root: Path,
    episode: str,
    plan: Mapping[str, Any],
    *,
    lease_token: str,
    precondition_digest: str,
    operation_kind: str,
    argv: Sequence[str],
    operation_index: int = 0,
) -> Dict[str, Any]:
    material = _work_unit_material(
        plan, episode, operation_kind=operation_kind, argv=argv,
        operation_index=operation_index,
    )
    digest = _digest(material)
    path = work_unit_path(root, episode, digest)
    prior = _load_json(path)
    prior_status = str(prior.get("status") or "")
    if prior:
        if prior.get("work_unit_digest") != digest or prior.get("material") != material:
            raise RuntimeError("immutable_work_unit_conflict")
        status_map = {
            "committed": "already_committed",
            "effect_observed_after_crash": "already_reconciled",
            "failed": "already_failed",
            "started": "ambiguous_prior_work_unit",
            "prepared": "ambiguous_prior_work_unit",
        }
        if prior_status in status_map:
            return {"status": status_map[prior_status], "path": str(path), "claim": prior}
        if prior_status != "abandoned_before_start":
            return {"status": "already_terminal", "path": str(path), "claim": prior}
    attempt = int(prior.get("attempt") or 0) + 1
    claim = {
        "kind": "n2d_producer_work_unit_claim",
        "version": 1,
        "status": "prepared",
        "work_unit_digest": digest,
        "material": material,
        "episode": episode,
        "attempt": attempt,
        "lease_token": lease_token,
        "pid": os.getpid(),
        "precondition_digest": precondition_digest,
        "prepared_at": now_iso(),
    }
    _atomic_json(path, claim)
    _append_jsonl(work_unit_wal_path(root, episode), {
        "event": "work_unit_prepared",
        "at": now_iso(),
        "episode": episode,
        "work_unit_digest": digest,
        "attempt": attempt,
        "lease_token": lease_token,
        "precondition_digest": precondition_digest,
    })
    return {"status": "prepared", "path": str(path), "claim": claim}


def _start_work_unit(root: Path, episode: str, prepared: Mapping[str, Any]) -> Dict[str, Any]:
    path = Path(str(prepared["path"]))
    claim = _load_json(path)
    token = str((prepared.get("claim") or {}).get("lease_token") or "")
    if claim.get("status") != "prepared" or claim.get("lease_token") != token:
        raise RuntimeError("work_unit_prepare_token_mismatch")
    claim.update({"status": "started", "started_at": now_iso()})
    _atomic_json(path, claim)
    _append_jsonl(work_unit_wal_path(root, episode), {
        "event": "work_unit_started",
        "at": now_iso(),
        "episode": episode,
        "work_unit_digest": claim["work_unit_digest"],
        "attempt": claim["attempt"],
        "lease_token": token,
        "precondition_digest": claim["precondition_digest"],
    })
    return claim


def _commit_work_unit(
    root: Path,
    episode: str,
    prepared: Mapping[str, Any],
    result: Mapping[str, Any],
) -> Dict[str, Any]:
    path = Path(str(prepared["path"]))
    claim = _load_json(path)
    token = str((prepared.get("claim") or {}).get("lease_token") or "")
    if claim.get("status") != "started" or claim.get("lease_token") != token:
        raise RuntimeError("work_unit_start_token_mismatch")
    terminal = "committed" if result.get("status") == "complete" else "failed"
    claim.update({
        "status": terminal,
        "committed_at": now_iso(),
        "result_status": str(result.get("status") or "failed"),
        "result_digest": _digest(result),
    })
    _atomic_json(path, claim)
    _append_jsonl(work_unit_wal_path(root, episode), {
        "event": "work_unit_committed",
        "at": now_iso(),
        "episode": episode,
        "work_unit_digest": claim["work_unit_digest"],
        "attempt": claim["attempt"],
        "lease_token": token,
        "terminal_status": terminal,
        "result_status": claim["result_status"],
        "result_digest": claim["result_digest"],
    })
    return claim


def reconcile_pending_work_units(
    root: str | Path,
    episode: str,
    current_frontier_digest: str,
) -> list[Dict[str, Any]]:
    """Recover unstarted work; fail closed on unchanged started work."""
    directory = Path(root) / "生产数据" / "producer" / "work_units" / _safe_slug(episode)
    if not directory.is_dir():
        return []
    outcomes: list[Dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        claim = _load_json(path)
        status = str(claim.get("status") or "")
        if status not in {"prepared", "started"}:
            continue
        if status == "prepared":
            resolved = "abandoned_before_start"
            claim.update({
                "status": resolved,
                "reconciled_at": now_iso(),
                "reconcile_reason": "prepared intent had no started WAL; safe to reclaim",
            })
        elif str(claim.get("precondition_digest") or "") != current_frontier_digest:
            resolved = "effect_observed_after_crash"
            claim.update({
                "status": resolved,
                "reconciled_at": now_iso(),
                "observed_frontier_digest": current_frontier_digest,
                "reconcile_reason": "frontier advanced after started WAL; replay forbidden",
            })
        else:
            resolved = "ambiguous_started_work_unit"
        if resolved != "ambiguous_started_work_unit":
            _atomic_json(path, claim)
        outcome = {
            "status": resolved,
            "work_unit_digest": str(claim.get("work_unit_digest") or path.stem),
            "path": str(path),
            "precondition_digest": str(claim.get("precondition_digest") or ""),
            "observed_frontier_digest": current_frontier_digest,
        }
        _append_jsonl(work_unit_wal_path(root, episode), {
            "event": "work_unit_reconciled",
            "at": now_iso(),
            "episode": episode,
            **outcome,
        })
        outcomes.append(outcome)
    return outcomes


def _run_durable_work_unit(
    root: Path,
    episode: str,
    plan: Mapping[str, Any],
    *,
    lease_token: str,
    precondition_digest: str,
    operation_kind: str,
    argv: Sequence[str],
    executor: Callable[[], Dict[str, Any]],
    operation_index: int = 0,
    fault_injector: Optional[Callable[[str, Mapping[str, Any]], None]] = None,
) -> Dict[str, Any]:
    prepared = _prepare_work_unit(
        root, episode, plan, lease_token=lease_token,
        precondition_digest=precondition_digest, operation_kind=operation_kind,
        argv=argv, operation_index=operation_index,
    )
    if prepared["status"] in {"already_committed", "already_reconciled"}:
        return {
            "status": "complete",
            "deduplicated": True,
            "work_unit_status": prepared["status"],
            "work_unit_digest": (prepared.get("claim") or {}).get("work_unit_digest"),
        }
    if prepared["status"] != "prepared":
        return {
            "status": "failed",
            "error": prepared["status"],
            "work_unit_digest": (prepared.get("claim") or {}).get("work_unit_digest"),
        }
    if fault_injector is not None:
        fault_injector("after_prepared", prepared)
    started = _start_work_unit(root, episode, prepared)
    if fault_injector is not None:
        fault_injector("after_started", started)
    result = executor()
    if fault_injector is not None:
        fault_injector("after_effect", {"claim": started, "result": result})
    committed = _commit_work_unit(root, episode, prepared, result)
    if fault_injector is not None:
        fault_injector("after_committed", committed)
    return {
        **dict(result),
        "deduplicated": False,
        "work_unit_status": committed["status"],
        "work_unit_digest": committed["work_unit_digest"],
    }


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
    fault_injector: Optional[Callable[[str, Mapping[str, Any]], None]] = None,
) -> Dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    root = str(root_path)
    episode_key = episode or "全集"
    events: list[Dict[str, Any]] = []
    run_id = f"{now_iso()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"
    event_journal = journal_path(root_path, episode_key)
    previous_identity = ""
    stagnant = 0
    final_plan: Dict[str, Any] = {}
    status = "stopped"
    stop_reason = "max_cycles"

    def payload() -> Dict[str, Any]:
        used_cycles = len({int(row.get("cycle") or 0) for row in events if int(row.get("cycle") or 0) > 0})
        return {
            "kind": KIND,
            "version": VERSION,
            "root": root,
            "episode": episode,
            "generated_at": now_iso(),
            "status": status,
            "stop_reason": stop_reason,
            "run_id": run_id,
            "cycles": used_cycles,
            "iteration_budget": {
                "max_cycles": max(1, int(max_cycles)),
                "used_cycles": used_cycles,
                "remaining_cycles": max(0, max(1, int(max_cycles)) - used_cycles),
            },
            "append_only_journal": str(event_journal),
            "work_unit_wal": str(work_unit_wal_path(root_path, episode_key)),
            "events": events,
            "final_plan": final_plan,
            "authority": "derived execution receipt; canonical completion remains run.py done + release verdict",
        }

    lease_context = producer_lease(root_path, episode_key)
    try:
        lease_token = lease_context.__enter__()
    except RuntimeError as exc:
        if str(exc) != "producer_busy":
            raise
        stop_reason = "producer_busy"
        return payload()

    try:
        # Planning is read-only here.  Every declared side effect below crosses
        # prepared -> started -> committed WAL instead of hiding inside --auto.
        initial_plan = planner(root, episode or None, auto=False, track_rounds=False)
        current_digest = frontier_digest(initial_plan)
        recoveries = reconcile_pending_work_units(root_path, episode_key, current_digest)
        for recovery in recoveries:
            _record_event(events, event_journal, run_id, {
                "cycle": 0,
                "at": now_iso(),
                "action": "work_unit_reconciliation",
                **recovery,
            })
        if any(row.get("status") == "ambiguous_started_work_unit" for row in recoveries):
            final_plan = initial_plan
            stop_reason = "ambiguous_started_work_unit"
            result_payload = payload()
            _atomic_json(output_path(root_path, episode_key), result_payload)
            return result_payload

        cached_plan: Optional[Dict[str, Any]] = initial_plan
        for cycle in range(1, max(1, max_cycles) + 1):
            final_plan = cached_plan or planner(root, episode or None, auto=False, track_rounds=False)
            cached_plan = None
            action = final_plan.get("next_action") if isinstance(final_plan.get("next_action"), Mapping) else {}
            dispatch = final_plan.get("dispatch") if isinstance(final_plan.get("dispatch"), Mapping) else {}
            reason = str(action.get("stop_reason") or final_plan.get("summary", {}).get("stop_reason") or "")
            identity = _frontier_identity(final_plan)
            precondition_digest = frontier_digest(final_plan)
            stagnant = stagnant + 1 if identity == previous_identity else 0
            previous_identity = identity
            event: Dict[str, Any] = {
                "cycle": cycle,
                "at": now_iso(),
                "identity": identity,
                "frontier_digest": precondition_digest,
                "stop_reason": reason,
                "stage_key": str(dispatch.get("stage_key") or ""),
            }

            if reason == "done":
                event["action"] = "terminal"
                _record_event(events, event_journal, run_id, event)
                status, stop_reason = "complete", "done"
                break
            if reason in HARD_BOUNDARIES:
                event["action"] = "hard_boundary"
                _record_event(events, event_journal, run_id, event)
                stop_reason = reason
                break
            if not execute:
                event["action"] = "plan_only"
                _record_event(events, event_journal, run_id, event)
                stop_reason = reason or "plan_only"
                break
            if stagnant >= max_stagnant_cycles:
                event["action"] = "non_convergent"
                _record_event(events, event_journal, run_id, event)
                stop_reason = "non_convergent"
                break

            card = action.get("action_card") if isinstance(action.get("action_card"), Mapping) else {}
            recipe = card.get("repair_recipe") if isinstance(card.get("repair_recipe"), Mapping) else {}
            repair_commands = [str(value) for value in recipe.get("safe_auto_commands") or [] if str(value).strip()]
            if repair_commands and not recipe.get("auto_attempted"):
                results = []
                for index, command in enumerate(repair_commands):
                    argv = shlex.split(command)
                    result = _run_durable_work_unit(
                        root_path, episode_key, final_plan,
                        lease_token=lease_token,
                        precondition_digest=precondition_digest,
                        operation_kind="auto_repair",
                        operation_index=index,
                        argv=argv,
                        executor=lambda argv=argv: command_executor(argv),
                        fault_injector=fault_injector,
                    )
                    results.append(result)
                    if result.get("status") != "complete":
                        break
                event.update({"action": "auto_repair", "results": results})
                _record_event(events, event_journal, run_id, event)
                if any(result.get("status") != "complete" for result in results):
                    stop_reason = "auto_repair_failed"
                    break
                continue

            if dispatch.get("should_call_specialist"):
                if reason == "needs_agent_gen":
                    if specialist_executor is None:
                        event["action"] = "specialist_adapter_required"
                        _record_event(events, event_journal, run_id, event)
                        stop_reason = "specialist_adapter_required"
                        break
                    specialist = dispatch.get("specialist") if isinstance(dispatch.get("specialist"), Mapping) else {}
                    specialist_argv = ["specialist_adapter", str(specialist.get("name") or "unknown")]
                    result = _run_durable_work_unit(
                        root_path, episode_key, final_plan,
                        lease_token=lease_token,
                        precondition_digest=precondition_digest,
                        operation_kind="specialist_adapter",
                        argv=specialist_argv,
                        executor=lambda: specialist_executor(final_plan, cycle),
                        fault_injector=fault_injector,
                    )
                    event.update({"action": "specialist", "result": result})
                elif dispatch.get("authorized_batch_execution") or dispatch.get("safe_local_execution") or reason == "needs_stage_execution":
                    argv = _declared_command(card)
                    if not argv:
                        event["action"] = "declared_command_missing"
                        _record_event(events, event_journal, run_id, event)
                        stop_reason = "declared_command_missing"
                        break
                    result = _run_durable_work_unit(
                        root_path, episode_key, final_plan,
                        lease_token=lease_token,
                        precondition_digest=precondition_digest,
                        operation_kind="stage_execution",
                        argv=argv,
                        executor=lambda: command_executor(argv),
                        fault_injector=fault_injector,
                    )
                    event.update({"action": "stage_execution", "result": result})
                else:
                    result = {"status": "failed", "error": "dispatch not executable under current authorization"}
                    event.update({"action": "dispatch_not_executable", "result": result})
                _record_event(events, event_journal, run_id, event)
                if result.get("status") != "complete":
                    stop_reason = "execution_failed"
                    break
                continue

            event["action"] = "repair_or_adapter_required" if reason.startswith("blocked_by_") or reason == "prework_failed" else "idle"
            _record_event(events, event_journal, run_id, event)
            stop_reason = reason or "idle"
            break

        result_payload = payload()
        _atomic_json(output_path(root_path, episode_key), result_payload)
        return result_payload
    finally:
        lease_context.__exit__(*sys.exc_info())


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
