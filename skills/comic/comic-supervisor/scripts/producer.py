#!/usr/bin/env python3
"""Durable, boundary-aware Comic producer loop."""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence
import uuid

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import supervisor  # noqa: E402


REGISTRY_REL = Path("生产数据") / "comic_specialist_execution_adapters.json"
REGISTRY_KIND = "comic_specialist_execution_adapter_registry"
SPECIALIST_ROLES = {"story_editor", "comic_writer", "visual_qc_agent", "quality_editor"}
HARD_ACTIONS = {"final_acceptance", "rights_or_release_boundary", "budget_authorization", "irreversible_publish"}
LEGACY_WORK_UNIT_DIGEST = "legacy-unversioned"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _fsync_dir(path: Path) -> None:
    """Persist directory entries after replace/create when the OS supports it."""
    try:
        directory_fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:  # pragma: no cover - unsupported on some filesystems/OSes
        pass


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)
    _fsync_dir(path.parent.parent)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_sha(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_wal(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical(dict(payload)) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_dir(path.parent)
    _fsync_dir(path.parent.parent)


def _control_dir(root: Path, chapter: str) -> Path:
    return root / "生产数据" / "producer" / chapter


def _frontier_snapshot(root: Path, chapter: str) -> dict[str, Any]:
    paths = [
        root / "_设置.md", root / "_进度.md",
        root / "脚本" / chapter / "chapter_contract.json",
        root / "脚本" / chapter / "panel_script.json",
        root / "排版" / chapter / "name.json",
        root / "排版" / chapter / "layout.json",
        root / "排版" / chapter / "finishing_plan.json",
        root / "出图" / chapter / "prompt" / "panel_jobs.json",
        root / "排版" / chapter / "export_manifest.json",
        root / "生产数据" / "gate_receipts" / f"review_{chapter}.json",
        root / "生产数据" / f"release_contract_{chapter}.json",
        root / "生产数据" / f"completion_verdict_{chapter}.json",
    ]
    records = [
        {"path": str(path.relative_to(root)), "sha256": _file_sha(path)}
        for path in paths if path.is_file()
    ]
    return {"records": records, "sha256": _digest(records)}


def _stable_action(action: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "status", "action", "next_stage", "panel_id", "reason", "issues",
        "recommended_commands", "completion_command", "agent_role", "hard_boundary",
    )
    return {key: action.get(key) for key in keys if key in action}


def _validated_work_unit_digest(
    action: Mapping[str, Any],
    *,
    allow_legacy_migration: bool = False,
) -> str:
    digest = str(action.get("work_unit_input_digest") or "").strip().lower()
    if len(digest) == 64 and all(char in "0123456789abcdef" for char in digest):
        return digest
    if allow_legacy_migration:
        return LEGACY_WORK_UNIT_DIGEST
    raise ValueError(
        "invalid_action_contract: mutating action requires a 64-hex work_unit_input_digest"
    )


def _logical_action_material(
    chapter: str,
    action: Mapping[str, Any],
    *,
    allow_legacy_migration: bool = False,
) -> dict[str, Any]:
    """Return the immutable identity of an intended side effect.

    The observed project frontier is deliberately excluded.  It is a
    precondition recorded on the claim, not an idempotency key.  Otherwise a
    process that dies after changing `_进度.md` but before finishing the claim
    would obtain a brand-new card on restart and replay the same command.
    """
    identity_keys = (
        "action", "next_stage", "panel_id", "recommended_commands",
        "completion_command", "agent_role",
    )
    intent = {key: action.get(key) for key in identity_keys if key in action}
    intent["work_unit_input_digest"] = _validated_work_unit_digest(
        action, allow_legacy_migration=allow_legacy_migration
    )
    return {
        "schema_version": 2,
        "kind": "comic_producer_action_card",
        "chapter": chapter,
        "action_intent": intent,
    }


def _install_legacy_claim_tombstone(
    root: Path,
    chapter: str,
    legacy_claim_path: Path,
    claim: Mapping[str, Any],
) -> None:
    """Map frontier-bound v1 cards to the stable v2 idempotency key."""
    directory = _control_dir(root, chapter)
    old_card = _load(directory / "action_cards" / f"{legacy_claim_path.stem}.json")
    action = old_card.get("action") if isinstance(old_card.get("action"), Mapping) else None
    if action is None:
        return
    material = _logical_action_material(chapter, action, allow_legacy_migration=True)
    stable_key = _digest(material)
    if stable_key == legacy_claim_path.stem:
        return
    card = {**material, "action_card_sha256": stable_key}
    card_path = directory / "action_cards" / f"{stable_key}.json"
    if card_path.is_file() and _load(card_path) != card:
        raise RuntimeError("immutable_action_card_conflict")
    if not card_path.is_file():
        _atomic(card_path, card)
    tombstone_path = directory / "claims" / f"{stable_key}.json"
    if not tombstone_path.exists():
        _atomic(tombstone_path, {
            "schema_version": 2,
            "kind": "comic_producer_action_claim",
            "status": "reconciled_legacy_claim",
            "chapter": chapter,
            "action_card_sha256": stable_key,
            "logical_idempotency_key": stable_key,
            "legacy_claim_path": str(legacy_claim_path),
            "legacy_claim_token": claim.get("claim_token"),
            "reconciled_at": now_iso(),
            "reconcile_reason": "legacy frontier-bound claim already observed; replay forbidden",
        })


@contextlib.contextmanager
def producer_lease(root: Path, chapter: str):
    """Exclusive chapter lease held by the OS for the whole producer run."""
    directory = _control_dir(root, chapter)
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / "producer.lock"
    handle = lock_path.open("a+")
    token = uuid.uuid4().hex
    try:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("producer_busy") from exc
        lease_path = directory / "lease.json"
        _atomic(lease_path, {
            "schema_version": 1, "kind": "comic_producer_lease", "chapter": chapter,
            "claim_token": token, "pid": os.getpid(), "acquired_at": now_iso(), "status": "held",
        })
        yield token
        _atomic(lease_path, {
            "schema_version": 1, "kind": "comic_producer_lease", "chapter": chapter,
            "claim_token": token, "pid": os.getpid(), "released_at": now_iso(), "status": "released",
        })
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def claim_action(
    root: Path,
    chapter: str,
    action: Mapping[str, Any],
    *,
    lease_token: str,
    frontier: Mapping[str, Any],
) -> dict[str, Any]:
    material = _logical_action_material(chapter, action)
    action_sha = _digest(material)
    material["action_card_sha256"] = action_sha
    directory = _control_dir(root, chapter)
    card_path = directory / "action_cards" / f"{action_sha}.json"
    if card_path.is_file():
        existing = _load(card_path)
        if existing != material:
            raise RuntimeError("immutable_action_card_conflict")
    else:
        _atomic(card_path, material)
    claim_path = directory / "claims" / f"{action_sha}.json"
    existing_claim = _load(claim_path)
    if existing_claim:
        status = str(existing_claim.get("status") or "")
        if status in {"claimed", "executing"}:
            if str(existing_claim.get("precondition_digest") or "") == str(frontier.get("sha256") or ""):
                return {
                    "status": "ambiguous_prior_claim", "action_card_sha256": action_sha,
                    "claim": existing_claim, "card_path": str(card_path), "claim_path": str(claim_path),
                }
            existing_claim.update({
                "status": "reconciled_frontier_advanced", "reconciled_at": now_iso(),
                "observed_frontier_digest": frontier.get("sha256"),
            })
            _atomic(claim_path, existing_claim)
            return {
                "status": "frontier_advanced", "action_card_sha256": action_sha,
                "claim": existing_claim, "card_path": str(card_path), "claim_path": str(claim_path),
            }
        return {
            "status": "already_claimed", "action_card_sha256": action_sha,
            "claim": existing_claim, "card_path": str(card_path), "claim_path": str(claim_path),
        }
    claim_token = uuid.uuid4().hex
    claim = {
        "schema_version": 2, "kind": "comic_producer_action_claim", "status": "claimed",
        "chapter": chapter, "action_card_sha256": action_sha,
        "logical_idempotency_key": action_sha,
        "work_unit_input_digest": str(material["action_intent"]["work_unit_input_digest"]),
        "observed_action_digest": _digest(_stable_action(action)),
        "claim_token": claim_token, "lease_token": lease_token,
        "precondition_digest": frontier.get("sha256"), "claimed_at": now_iso(), "pid": os.getpid(),
        "command_records": [],
    }
    _atomic(claim_path, claim)
    return {
        "status": "claimed", "action_card_sha256": action_sha, "claim": claim,
        "card_path": str(card_path), "claim_path": str(claim_path),
    }


def _claim_wal(root: Path, chapter: str) -> Path:
    return _control_dir(root, chapter) / "commands.jsonl"


def begin_claim_command(
    root: Path,
    chapter: str,
    claimed: Mapping[str, Any],
    *,
    index: int,
    argv: Sequence[str],
    operation_kind: str = "command",
) -> dict[str, Any]:
    """Persist a command intent before any external side effect is invoked."""
    claim_path = Path(str(claimed["claim_path"]))
    claim = _load(claim_path)
    token = str((claimed.get("claim") or {}).get("claim_token") or "")
    if claim.get("status") not in {"claimed", "executing"} or claim.get("claim_token") != token:
        raise RuntimeError("claim_token_mismatch")
    command_key = _digest({
        "logical_idempotency_key": claim.get("logical_idempotency_key") or claim.get("action_card_sha256"),
        "index": int(index),
        "argv": list(argv),
        "operation_kind": operation_kind,
    })
    records = claim.get("command_records") if isinstance(claim.get("command_records"), list) else []
    previous = next((row for row in records if isinstance(row, Mapping) and row.get("command_key") == command_key), None)
    if previous:
        return dict(previous)
    record = {
        "command_key": command_key,
        "index": int(index),
        "operation_kind": operation_kind,
        "argv": list(argv),
        "status": "started",
        "started_at": now_iso(),
        "precondition_digest": _frontier_snapshot(root, chapter)["sha256"],
    }
    claim["status"] = "executing"
    claim["command_records"] = [*records, record]
    claim["active_command_key"] = command_key
    _atomic(claim_path, claim)
    _append_wal(_claim_wal(root, chapter), {
        "event": "command_started", "chapter": chapter,
        "action_card_sha256": claim.get("action_card_sha256"),
        "claim_token": token, **record,
    })
    return record


def commit_claim_command(
    root: Path,
    chapter: str,
    claimed: Mapping[str, Any],
    *,
    command_key: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Commit a returned command result and its observed postcondition."""
    claim_path = Path(str(claimed["claim_path"]))
    claim = _load(claim_path)
    token = str((claimed.get("claim") or {}).get("claim_token") or "")
    if claim.get("status") != "executing" or claim.get("claim_token") != token:
        raise RuntimeError("claim_token_mismatch")
    records = claim.get("command_records") if isinstance(claim.get("command_records"), list) else []
    found: dict[str, Any] | None = None
    for row in records:
        if isinstance(row, dict) and row.get("command_key") == command_key:
            found = row
            break
    if found is None or found.get("status") != "started":
        raise RuntimeError("command_intent_missing")
    found.update({
        "status": "committed" if result.get("status") == "complete" else "failed",
        "committed_at": now_iso(),
        "result_digest": _digest(result),
        "result_status": str(result.get("status") or "failed"),
        "postcondition_digest": _frontier_snapshot(root, chapter)["sha256"],
    })
    claim.pop("active_command_key", None)
    _atomic(claim_path, claim)
    _append_wal(_claim_wal(root, chapter), {
        "event": "command_committed", "chapter": chapter,
        "action_card_sha256": claim.get("action_card_sha256"),
        "claim_token": token, **found,
    })
    return dict(found)


def reconcile_pending_claims(root: Path, chapter: str) -> list[dict[str, Any]]:
    """Scan *all* unfinished claims before planning any new action.

    A changed frontier after a durable command intent is positive evidence that
    the side effect may already have happened, so the claim is reconciled and
    never replayed.  An unchanged frontier remains ambiguous and stops the
    producer fail-closed.
    """
    claims_dir = _control_dir(root, chapter) / "claims"
    if not claims_dir.is_dir():
        return []
    frontier = _frontier_snapshot(root, chapter)
    outcomes: list[dict[str, Any]] = []
    for path in sorted(claims_dir.glob("*.json")):
        claim = _load(path)
        if claim.get("status") not in {"claimed", "executing"}:
            continue
        records = [row for row in claim.get("command_records") or [] if isinstance(row, Mapping)]
        terminal_records = bool(records) and all(row.get("status") in {"committed", "failed"} for row in records)
        if terminal_records:
            succeeded = all(row.get("status") == "committed" and row.get("result_status") == "complete" for row in records)
            claim.update({
                "status": "completed" if succeeded else "failed",
                "reconciled_at": now_iso(),
                "reconcile_reason": "all command-level WAL records were terminal",
                "postcondition_digest": frontier["sha256"],
            })
            result = "command_wal_committed"
        elif str(claim.get("precondition_digest") or "") != str(frontier["sha256"]):
            for row in claim.get("command_records") or []:
                if isinstance(row, dict) and row.get("status") == "started":
                    row.update({
                        "status": "effect_observed_after_crash",
                        "reconciled_at": now_iso(),
                        "observed_frontier_digest": frontier["sha256"],
                    })
            claim.update({
                "status": "reconciled_frontier_advanced",
                "reconciled_at": now_iso(),
                "observed_frontier_digest": frontier["sha256"],
                "reconcile_reason": "frontier changed after durable claim/command intent; replay forbidden",
            })
            result = "frontier_advanced_no_replay"
        else:
            result = "ambiguous_prior_claim"
        if result != "ambiguous_prior_claim":
            _atomic(path, claim)
            _install_legacy_claim_tombstone(root, chapter, path, claim)
        outcomes.append({
            "claim_path": str(path),
            "action_card_sha256": claim.get("action_card_sha256") or path.stem,
            "claim_token": claim.get("claim_token"),
            "status": result,
            "precondition_digest": claim.get("precondition_digest"),
            "observed_frontier_digest": frontier["sha256"],
        })
    return outcomes


def finish_claim(root: Path, chapter: str, claimed: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    claim_path = Path(str(claimed["claim_path"]))
    claim = _load(claim_path)
    token = str((claimed.get("claim") or {}).get("claim_token") or "")
    if claim.get("status") not in {"claimed", "executing"} or claim.get("claim_token") != token:
        raise RuntimeError("claim_token_mismatch")
    postcondition = _frontier_snapshot(root, chapter)
    claim.update({
        "status": "completed" if result.get("status") == "complete" else "failed",
        "finished_at": now_iso(), "result_digest": _digest(result),
        "postcondition_digest": postcondition["sha256"],
    })
    _atomic(claim_path, claim)
    return claim


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


def _identity(action: Mapping[str, Any], frontier_digest: str) -> str:
    blocker_digest = _digest({
        "reason": action.get("reason") or "",
        "issues": action.get("issues") or [],
    })
    return "::".join(
        [str(action.get(key) or "") for key in ("status", "action", "next_stage", "panel_id")]
        + [str(action.get("work_unit_input_digest") or ""), frontier_digest, blocker_digest]
    )


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
    out = root_path / "生产数据" / "producer" / chapter / "producer_run.json"
    journal = out.with_name("events.jsonl")
    events: list[dict[str, Any]] = []
    previous, stagnant = "", 0
    status, stop_reason, final_action = "stopped", "max_cycles", {}
    run_id = f"{now_iso()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"

    def payload() -> dict[str, Any]:
        return {
            "schema_version": 2, "kind": "comic_producer_run", "updated_at": now_iso(),
            "project_root": str(root_path), "chapter": chapter, "status": status,
            "stop_reason": stop_reason, "cycles": len({row.get('cycle') for row in events}),
            "run_id": run_id, "events": events, "final_action": final_action,
            "wal_path": str(journal.relative_to(root_path)),
            "authority": "execution receipt only; canonical completion remains completion_verdict",
        }

    def record(row: Mapping[str, Any]) -> None:
        event = {"run_id": run_id, **dict(row)}
        events.append(event)
        _append_wal(journal, event)
        _atomic(out, payload())

    try:
        lease_context = producer_lease(root_path, chapter)
        lease_token = lease_context.__enter__()
    except RuntimeError as exc:
        if str(exc) != "producer_busy":
            raise
        stop_reason = "producer_busy"
        return payload()
    try:
        pending = reconcile_pending_claims(root_path, chapter)
        for recovery in pending:
            record({
                "cycle": 0,
                "at": now_iso(),
                "phase": "claim_recovery",
                "execution": recovery["status"],
                **recovery,
            })
        if any(row.get("status") == "ambiguous_prior_claim" for row in pending):
            stop_reason = "ambiguous_prior_claim"
            _atomic(out, payload())
            return payload()
        for cycle in range(1, max(1, max_cycles) + 1):
            frontier = _frontier_snapshot(root_path, chapter)
            final_action = planner(root_path, chapter)
            identity = _identity(final_action, str(frontier["sha256"]))
            stagnant = stagnant + 1 if identity == previous else 0
            previous = identity
            base: dict[str, Any] = {
                "cycle": cycle, "at": now_iso(), "identity": identity,
                "action": final_action.get("action"),
                "frontier_digest": frontier["sha256"],
            }
            if final_action.get("status") == "complete":
                status, stop_reason = "complete", "accepted"
                record({**base, "phase": "terminal", "execution": "terminal"})
                break
            if final_action.get("action") in HARD_ACTIONS or (
                final_action.get("hard_boundary")
                and final_action.get("status") in {"needs_human", "blocked"}
            ):
                stop_reason = str(final_action.get("action") or "hard_boundary")
                record({**base, "phase": "stopped", "execution": "hard_boundary"})
                break
            if not execute:
                stop_reason = "plan_only"
                record({**base, "phase": "planned", "execution": "plan_only"})
                break
            if stagnant >= max_stagnant_cycles:
                stop_reason = "non_convergent"
                record({**base, "phase": "stopped", "execution": "circuit_breaker"})
                break

            try:
                claimed = claim_action(
                    root_path, chapter, final_action, lease_token=lease_token, frontier=frontier
                )
            except ValueError as exc:
                if not str(exc).startswith("invalid_action_contract:"):
                    raise
                stop_reason = "invalid_action_contract"
                record({
                    **base, "phase": "stopped", "execution": "invalid_action_contract",
                    "reason": str(exc),
                })
                break
            record({
                **base, "phase": "claimed", "execution": "claim",
                "action_card_sha256": claimed["action_card_sha256"],
                "claim_status": claimed["status"],
                "claim_token": (claimed.get("claim") or {}).get("claim_token"),
                "precondition_digest": frontier["sha256"],
            })
            if claimed["status"] == "frontier_advanced":
                continue
            if claimed["status"] != "claimed":
                stop_reason = (
                    "ambiguous_prior_claim" if claimed["status"] == "ambiguous_prior_claim"
                    else "claimed_action_without_progress"
                )
                record({**base, "phase": "stopped", "execution": stop_reason})
                break

            role = str(final_action.get("agent_role") or "")
            if role in SPECIALIST_ROLES:
                operation = begin_claim_command(
                    root_path, chapter, claimed, index=0,
                    argv=["specialist_adapter", role], operation_kind="specialist_adapter",
                )
                result = specialist(root_path, chapter, final_action, cycle)
                commit_claim_command(
                    root_path, chapter, claimed,
                    command_key=str(operation["command_key"]), result=result,
                )
                claim_receipt = finish_claim(root_path, chapter, claimed, result)
                record({
                    **base, "phase": "finished", "execution": "specialist_adapter",
                    "result": result, "postcondition_digest": claim_receipt.get("postcondition_digest"),
                    "action_card_sha256": claimed["action_card_sha256"],
                })
                if result.get("status") != "complete":
                    stop_reason = str(result.get("status") or "specialist_failed")
                    break
                continue
            commands = [parse_command(item) for item in final_action.get("recommended_commands") or []]
            if not commands or any(not command for command in commands):
                result = {"status": "failed", "error": "safe command required"}
                finish_claim(root_path, chapter, claimed, result)
                stop_reason = "safe_command_required"
                record({**base, "phase": "finished", "execution": "safe_command_required"})
                break
            results = []
            for index, command in enumerate(commands):
                command_intent = begin_claim_command(
                    root_path, chapter, claimed, index=index, argv=command,
                )
                record({
                    **base, "phase": "command_started", "execution": "deterministic",
                    "action_card_sha256": claimed["action_card_sha256"],
                    "command_key": command_intent["command_key"], "command_index": index,
                })
                command_result = command_executor(command)
                command_commit = commit_claim_command(
                    root_path, chapter, claimed,
                    command_key=str(command_intent["command_key"]), result=command_result,
                )
                results.append(command_result)
                record({
                    **base, "phase": "command_committed", "execution": "deterministic",
                    "action_card_sha256": claimed["action_card_sha256"],
                    "command_key": command_commit["command_key"], "command_index": index,
                    "result_digest": command_commit["result_digest"],
                    "postcondition_digest": command_commit["postcondition_digest"],
                })
                if command_result.get("status") != "complete":
                    break
            combined = {
                "status": "complete" if all(row.get("status") == "complete" for row in results) else "failed",
                "results": results,
            }
            claim_receipt = finish_claim(root_path, chapter, claimed, combined)
            record({
                **base, "phase": "finished", "execution": "deterministic", "results": results,
                "postcondition_digest": claim_receipt.get("postcondition_digest"),
                "action_card_sha256": claimed["action_card_sha256"],
            })
            if combined["status"] != "complete":
                stop_reason = "command_failed"
                break
        _atomic(out, payload())
        return payload()
    finally:
        lease_context.__exit__(None, None, None)


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
