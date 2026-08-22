#!/usr/bin/env python3
"""Hash-bound, bounded and atomically consumed phase spend envelopes for n2d.

Version-1 production authorizations remain task/attempt receipts.  This module implements the
optional version-2 phase envelope: one accountable human approval may cover several exact paid
calls/retries, but only while project, stage, execution input, concrete model/channel, expiry and
all call/attempt/cost limits still match.  The usage ledger is project-local and VCS-free.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Dict, Iterator, Mapping, Optional, Sequence
import uuid

try:  # POSIX is the supported production platform; fallback keeps tests/packaging portable.
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


LINE = "n2d"
KIND = "n2d_phase_spend_envelope"
VERSION = 2
ATTEMPT_ID_SEMANTICS = "phase_retry_round"
LEDGER_KIND = "n2d_phase_spend_usage_ledger"
LEDGER_VERSION = 1
LEDGER_REL = Path("生产数据") / "spend_envelope_usage.json"
DEFAULT_DIR_REL = Path("生产数据") / "spend_envelopes"
REJECTED_IDENTITIES = {"", "unknown", "system", "agent", "auto", "any", "test"}
REJECTED_IDENTITY_PREFIXES = ("agent:", "auto:", "delegate:", "system:")


class SpendEnvelopeError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _without_digest(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "authorization_digest"}


def authorization_digest(payload: Mapping[str, Any]) -> str:
    return canonical_digest(_without_digest(payload))


def normalize_sha256(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("sha256:"):
        text = text[7:]
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise SpendEnvelopeError("input_sha256 must be a full SHA-256 digest")
    return "sha256:" + text


def project_id(root: str | Path) -> str:
    resolved = str(Path(root).expanduser().resolve())
    return "sha256:" + hashlib.sha256(resolved.encode("utf-8")).hexdigest()


def _invalid_approver(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in REJECTED_IDENTITIES or text.startswith(REJECTED_IDENTITY_PREFIXES)


def _approval_evidence(reference: Any, source_quote: Any) -> tuple[str, str]:
    """Require auditable evidence instead of trusting an approver label alone."""
    ref = str(reference or "").strip()
    quote = str(source_quote or "").strip()
    lowered_ref = ref.lower()
    lowered_quote = quote.lower()
    if not ref or lowered_ref in REJECTED_IDENTITIES or lowered_ref.startswith(
        REJECTED_IDENTITY_PREFIXES
    ):
        raise SpendEnvelopeError(
            "approval_reference is required and must point to the human approval record"
        )
    if not quote or lowered_quote in REJECTED_IDENTITIES or lowered_quote.startswith(
        REJECTED_IDENTITY_PREFIXES
    ):
        raise SpendEnvelopeError(
            "source_quote is required and must quote the human approval decision"
        )
    return ref, quote


def default_envelope_path(root: str | Path, stage: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(stage)).strip("._")
    return Path(root).expanduser().resolve() / DEFAULT_DIR_REL / f"{safe or 'stage'}.json"


def _parse_aware(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise SpendEnvelopeError(f"{field} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SpendEnvelopeError(f"{field} must be a positive integer") from exc
    if parsed <= 0 or str(value).strip() not in {str(parsed), f"+{parsed}"}:
        raise SpendEnvelopeError(f"{field} must be a positive integer")
    return parsed


def _money(amount: Any, currency: Any, *, field: str) -> tuple[float, str]:
    try:
        parsed = float(amount)
    except (TypeError, ValueError) as exc:
        raise SpendEnvelopeError(f"{field}.amount must be finite and non-negative") from exc
    unit = str(currency or "").strip()
    if not math.isfinite(parsed) or parsed < 0 or not unit:
        raise SpendEnvelopeError(f"{field} must contain finite non-negative amount and currency")
    return parsed, unit


def make_envelope(
    root: str | Path,
    *,
    stage: str,
    model: str,
    channel: str,
    input_sha256: str,
    max_calls: int,
    max_attempts: int,
    cost_ceiling: float,
    currency: str,
    approver: str,
    approval_reference: str,
    source_quote: str,
    expires_at: Optional[str] = None,
    ttl_hours: float = 24.0,
    envelope_id: Optional[str] = None,
    scope: Optional[Mapping[str, Any]] = None,
    issued_at: Optional[str] = None,
) -> Dict[str, Any]:
    stage_text = str(stage or "").strip()
    model_text = str(model or "").strip()
    channel_text = str(channel or "").strip()
    approver_text = str(approver or "").strip()
    approval_ref, quote = _approval_evidence(approval_reference, source_quote)
    if not stage_text:
        raise SpendEnvelopeError("stage is required")
    if model_text.lower() in REJECTED_IDENTITIES:
        raise SpendEnvelopeError("model must be a concrete accountable model/version, not any/auto")
    if channel_text.lower() in REJECTED_IDENTITIES:
        raise SpendEnvelopeError("channel must be a concrete access path, not any/auto")
    if _invalid_approver(approver_text):
        raise SpendEnvelopeError("approver must identify a real accountable human")
    calls = _positive_int(max_calls, "max_calls")
    attempts = _positive_int(max_attempts, "max_attempts")
    amount, unit = _money(cost_ceiling, currency, field="cost_ceiling")
    issued = _parse_aware(issued_at or now_iso())
    if issued is None:
        raise SpendEnvelopeError("issued_at must be timezone-aware ISO-8601")
    expiry = _parse_aware(expires_at) if expires_at else issued + timedelta(hours=float(ttl_hours))
    if expiry is None or expiry <= issued:
        raise SpendEnvelopeError("expires_at must be timezone-aware and after issued_at")
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "envelope_id": str(envelope_id or f"{LINE}-{stage_text}-{uuid.uuid4().hex[:16]}").strip(),
        "line": LINE,
        "project_id": project_id(root),
        "stage": stage_text,
        "scope": dict(scope or {}),
        "model": model_text,
        "channel": channel_text,
        "input_sha256": normalize_sha256(input_sha256),
        "issued_at": issued.replace(microsecond=0).isoformat(),
        "expires_at": expiry.replace(microsecond=0).isoformat(),
        "decision": "approved",
        "attempt_id_semantics": ATTEMPT_ID_SEMANTICS,
        "approver": approver_text,
        "approval_reference": approval_ref,
        "source_quote": quote,
        "limits": {
            "max_calls": calls,
            "max_attempts": attempts,
            "cost_ceiling": {"amount": amount, "currency": unit},
        },
        # Compatibility with the existing queue settlement receipt shape.
        "ceiling": {"amount": amount, "currency": unit},
    }
    if not payload["envelope_id"]:
        raise SpendEnvelopeError("envelope_id is required")
    payload["authorization_digest"] = authorization_digest(payload)
    return payload


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def write_envelope(path: str | Path, payload: Mapping[str, Any]) -> Path:
    target = Path(path).expanduser().resolve()
    _write_json_atomic(target, payload)
    return target


def load_envelope(path: str | Path) -> Dict[str, Any]:
    target = Path(path).expanduser().resolve()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpendEnvelopeError(f"spend envelope missing or invalid: {target}") from exc
    if not isinstance(payload, dict):
        raise SpendEnvelopeError("spend envelope must be a JSON object")
    return payload


def _empty_ledger(root: str | Path) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "kind": LEDGER_KIND,
        "version": LEDGER_VERSION,
        "line": LINE,
        "project_id": project_id(root),
        "envelopes": {},
        "updated_at": now_iso(),
    }
    payload["ledger_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "ledger_digest"}
    )
    return payload


def _load_ledger(root: str | Path) -> Dict[str, Any]:
    path = Path(root).expanduser().resolve() / LEDGER_REL
    if not path.exists():
        return _empty_ledger(root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpendEnvelopeError("spend usage ledger is unreadable/corrupt") from exc
    if not isinstance(payload, dict):
        raise SpendEnvelopeError("spend usage ledger must be an object")
    if payload.get("kind") != LEDGER_KIND or payload.get("version") != LEDGER_VERSION:
        raise SpendEnvelopeError("spend usage ledger kind/version mismatch")
    if payload.get("project_id") != project_id(root):
        raise SpendEnvelopeError("spend usage ledger project mismatch")
    declared = str(payload.get("ledger_digest") or "")
    calculated = canonical_digest(
        {key: value for key, value in payload.items() if key != "ledger_digest"}
    )
    if declared != calculated:
        raise SpendEnvelopeError("spend usage ledger digest mismatch")
    if not isinstance(payload.get("envelopes"), dict):
        raise SpendEnvelopeError("spend usage ledger envelopes must be an object")
    return payload


@contextmanager
def _ledger_lock(root: str | Path, *, timeout: float = 10.0) -> Iterator[None]:
    ledger_path = Path(root).expanduser().resolve() / LEDGER_REL
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger_path.with_suffix(ledger_path.suffix + ".lock")
    if fcntl is not None:
        with lock_path.open("a+") as handle:
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise SpendEnvelopeError("timed out waiting for spend ledger lock")
                    time.sleep(0.02)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return
    deadline = time.monotonic() + timeout  # pragma: no cover - portable fallback
    while True:  # pragma: no cover
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SpendEnvelopeError("timed out waiting for spend ledger lock")
            time.sleep(0.02)
    try:  # pragma: no cover
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _request_record(
    *,
    consumption_id: str,
    attempt_id: str,
    calls: int,
    cost: float,
    currency: str,
    stage: str,
    model: str,
    channel: str,
    input_sha256: str,
    scope: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    call_count = _positive_int(calls, "calls")
    amount, unit = _money(cost, currency, field="cost")
    cid = str(consumption_id or "").strip()
    aid = str(attempt_id or "").strip()
    if not cid or not aid:
        raise SpendEnvelopeError("consumption_id and attempt_id are required")
    return {
        "consumption_id": cid,
        "attempt_id": aid,
        "calls": call_count,
        "cost": {"amount": amount, "currency": unit},
        "stage": str(stage or "").strip(),
        "model": str(model or "").strip(),
        "channel": str(channel or "").strip(),
        "input_sha256": normalize_sha256(input_sha256),
        "scope": dict(scope or {}),
    }


def _envelope_issues(
    root: str | Path,
    envelope: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    records: Sequence[Mapping[str, Any]],
) -> list[str]:
    issues: list[str] = []
    if envelope.get("kind") != KIND or envelope.get("version") != VERSION:
        issues.append("spend envelope kind/version mismatch")
    if envelope.get("line") != LINE:
        issues.append("spend envelope line mismatch")
    if envelope.get("project_id") != project_id(root):
        issues.append("spend envelope project mismatch")
    declared = str(envelope.get("authorization_digest") or "")
    if declared != authorization_digest(envelope):
        issues.append("spend envelope authorization_digest mismatch")
    if str(envelope.get("decision") or "").lower() != "approved":
        issues.append("spend envelope decision must be approved")
    if envelope.get("attempt_id_semantics") != ATTEMPT_ID_SEMANTICS:
        issues.append("spend envelope attempt_id_semantics mismatch")
    if _invalid_approver(envelope.get("approver")):
        issues.append("spend envelope approver must identify a real accountable human")
    if not str(envelope.get("approval_reference") or "").strip():
        issues.append("spend envelope approval_reference missing")
    if not str(envelope.get("source_quote") or "").strip():
        issues.append("spend envelope source_quote missing")
    issued = _parse_aware(envelope.get("issued_at"))
    expiry = _parse_aware(envelope.get("expires_at"))
    now = datetime.now(timezone.utc)
    if issued is None or expiry is None or expiry <= issued:
        issues.append("spend envelope timestamps invalid")
    elif issued > now + timedelta(minutes=5):
        issues.append("spend envelope issued_at is in the future")
    elif expiry <= now:
        issues.append("spend envelope expired")
    for key in ("stage", "model", "channel", "input_sha256", "scope"):
        if envelope.get(key) != request.get(key):
            issues.append(f"spend envelope {key} mismatch")
    limits = envelope.get("limits") if isinstance(envelope.get("limits"), Mapping) else {}
    try:
        max_calls = _positive_int(limits.get("max_calls"), "max_calls")
        max_attempts = _positive_int(limits.get("max_attempts"), "max_attempts")
        ceiling = limits.get("cost_ceiling") if isinstance(limits.get("cost_ceiling"), Mapping) else {}
        ceiling_amount, ceiling_currency = _money(
            ceiling.get("amount"), ceiling.get("currency"), field="cost_ceiling"
        )
    except SpendEnvelopeError as exc:
        issues.append(str(exc))
        return issues
    requested_cost = request.get("cost") if isinstance(request.get("cost"), Mapping) else {}
    request_amount, request_currency = _money(
        requested_cost.get("amount"), requested_cost.get("currency"), field="cost"
    )
    if request_currency != ceiling_currency:
        issues.append("spend envelope cost currency mismatch")
    existing = next(
        (row for row in records if str(row.get("consumption_id") or "") == request.get("consumption_id")),
        None,
    )
    comparable = {key: value for key, value in request.items() if key != "consumed_at"}
    if existing is not None:
        prior = {
            key: value
            for key, value in existing.items()
            if key not in {"consumed_at", "state", "completion"}
        }
        if prior != comparable:
            issues.append("consumption_id already exists with different bindings")
        state = str(existing.get("state") or "in_flight")
        if state == "completed":
            issues.append(
                "consumption_id already completed; provider replay blocked (recover from existing outputs/receipt)"
            )
        else:
            issues.append(
                "consumption_id has uncertain in_flight provider state; provider replay blocked"
            )
        return issues
    if any(str(row.get("state") or "in_flight") != "completed" for row in records):
        issues.append(
            "prior spend consumption has uncertain in_flight provider state; recovery/finalization required"
        )
    used_calls = sum(int(row.get("calls") or 0) for row in records)
    used_cost = sum(float((row.get("cost") or {}).get("amount") or 0.0) for row in records)
    used_attempts = {str(row.get("attempt_id") or "") for row in records}
    if str(request.get("attempt_id") or "") not in used_attempts and len(used_attempts) + 1 > max_attempts:
        issues.append("spend envelope max_attempts exceeded")
    if used_calls + int(request.get("calls") or 0) > max_calls:
        issues.append("spend envelope max_calls exceeded")
    if request_currency == ceiling_currency and used_cost + request_amount > ceiling_amount + 1e-9:
        issues.append("spend envelope cost_ceiling exceeded")
    return issues


def verify(
    root: str | Path,
    envelope: Mapping[str, Any],
    *,
    stage: str,
    model: str,
    channel: str,
    input_sha256: str,
    scope: Optional[Mapping[str, Any]],
    consumption_id: str,
    attempt_id: str,
    calls: int,
    cost: float,
    currency: str,
) -> Dict[str, Any]:
    request = _request_record(
        consumption_id=consumption_id,
        attempt_id=attempt_id,
        calls=calls,
        cost=cost,
        currency=currency,
        stage=stage,
        model=model,
        channel=channel,
        input_sha256=input_sha256,
        scope=scope,
    )
    ledger = _load_ledger(root)
    entry = (ledger.get("envelopes") or {}).get(str(envelope.get("envelope_id") or ""), {})
    records = entry.get("consumptions") if isinstance(entry, Mapping) else []
    if not isinstance(records, list):
        records = []
    issues = _envelope_issues(root, envelope, request, records=records)
    if isinstance(entry, Mapping) and entry and entry.get("authorization_digest") != envelope.get(
        "authorization_digest"
    ):
        issues.append("envelope_id reused with a different authorization digest")
    existing = any(
        isinstance(row, Mapping) and row.get("consumption_id") == request["consumption_id"]
        for row in records
    )
    return {
        "status": "pass" if not issues else "blocked",
        # A duplicate identifier is accounting-idempotent (it never adds a row) but is never
        # executable-idempotent: without a provider idempotency guarantee, replay is blocked.
        "idempotent": existing,
        "replay_blocked": existing,
        "envelope_id": str(envelope.get("envelope_id") or ""),
        "authorization_digest": str(envelope.get("authorization_digest") or ""),
        "request": request,
        "usage": {
            "attempts": len({str(row.get("attempt_id") or "") for row in records}),
            "calls": sum(int(row.get("calls") or 0) for row in records if isinstance(row, Mapping)),
            "cost": sum(float((row.get("cost") or {}).get("amount") or 0.0) for row in records if isinstance(row, Mapping)),
        },
        "issues": issues,
    }


def consume(
    root: str | Path,
    envelope: Mapping[str, Any],
    **request_kwargs: Any,
) -> Dict[str, Any]:
    request = _request_record(**request_kwargs)
    root_path = Path(root).expanduser().resolve()
    with _ledger_lock(root_path):
        ledger = _load_ledger(root_path)
        envelope_id = str(envelope.get("envelope_id") or "").strip()
        if not envelope_id:
            raise SpendEnvelopeError("spend envelope envelope_id missing")
        entries = ledger.setdefault("envelopes", {})
        entry = entries.get(envelope_id)
        if entry is None:
            entry = {
                "authorization_digest": str(envelope.get("authorization_digest") or ""),
                "consumptions": [],
            }
            entries[envelope_id] = entry
        if not isinstance(entry, dict) or not isinstance(entry.get("consumptions"), list):
            raise SpendEnvelopeError("spend usage ledger envelope entry invalid")
        if entry.get("authorization_digest") != envelope.get("authorization_digest"):
            raise SpendEnvelopeError("envelope_id reused with a different authorization digest")
        records = entry["consumptions"]
        issues = _envelope_issues(root_path, envelope, request, records=records)
        if issues:
            raise SpendEnvelopeError("; ".join(issues))
        # `_envelope_issues` rejects an existing id (same binding included) and any earlier
        # unresolved reservation, so reaching here always creates exactly one new in-flight row.
        request = {**request, "state": "in_flight", "consumed_at": now_iso()}
        records.append(request)
        entry["updated_at"] = request["consumed_at"]
        ledger["updated_at"] = request["consumed_at"]
        ledger["ledger_digest"] = canonical_digest(
            {key: value for key, value in ledger.items() if key != "ledger_digest"}
        )
        _write_json_atomic(root_path / LEDGER_REL, ledger)
        return {
            "status": "pass",
            "idempotent": False,
            "replay_blocked": False,
            "envelope_id": envelope_id,
            "authorization_digest": str(envelope.get("authorization_digest") or ""),
            "consumption": dict(request),
            "usage": {
                "attempts": len({str(row.get("attempt_id") or "") for row in records}),
                "calls": sum(int(row.get("calls") or 0) for row in records),
                "cost": sum(float((row.get("cost") or {}).get("amount") or 0.0) for row in records),
            },
        }


def finalize(
    root: str | Path,
    envelope: Mapping[str, Any],
    *,
    consumption_id: str,
    evidence: Mapping[str, Any],
) -> Dict[str, Any]:
    """Atomically close an in-flight reservation after provider completion is proved.

    This does not grant another call.  It only removes the uncertainty lock so a *different*,
    separately bounded task/attempt may later consume remaining envelope capacity.  A crashed
    submit must first be recovered/query-resumed and supply durable completion evidence; callers
    cannot turn a repeated consumption id into a second provider submit.
    """
    cid = str(consumption_id or "").strip()
    proof = dict(evidence or {})
    if not cid:
        raise SpendEnvelopeError("consumption_id is required for finalization")
    if not proof:
        raise SpendEnvelopeError("provider completion evidence is required for finalization")
    kind = str(proof.get("kind") or "")
    if kind == "n2d_provider_completion_evidence":
        receipts = proof.get("paid_execution_receipts")
        outputs = proof.get("producer_output_bindings")
        valid_receipts = (
            isinstance(receipts, Mapping)
            and receipts.get("status") == "pass"
            and isinstance(receipts.get("records"), list)
            and bool(receipts.get("records"))
        )
        valid_outputs = (
            isinstance(outputs, list)
            and bool(outputs)
            and all(
                isinstance(row, Mapping)
                and row.get("exists") is True
                and str(row.get("sha256") or "")
                and not row.get("issue")
                for row in outputs
            )
        )
        if not valid_receipts or not valid_outputs:
            raise SpendEnvelopeError(
                "runner completion evidence requires passing paid receipts and verified outputs"
            )
    elif kind == "n2d_provider_recovery_evidence":
        submit_id = str(proof.get("provider_submit_id") or "").strip()
        reference = str(proof.get("query_receipt_reference") or "").strip()
        status = str(proof.get("provider_status") or "").strip().lower()
        try:
            normalize_sha256(proof.get("query_response_sha256"))
        except SpendEnvelopeError as exc:
            raise SpendEnvelopeError(
                "provider recovery evidence requires query_response_sha256"
            ) from exc
        if not submit_id or not reference or status not in {"success", "succeeded", "completed"}:
            raise SpendEnvelopeError(
                "provider recovery evidence requires submit id, terminal status and query receipt reference"
            )
    else:
        raise SpendEnvelopeError(
            "provider completion evidence kind must be runner completion or provider recovery"
        )
    root_path = Path(root).expanduser().resolve()
    with _ledger_lock(root_path):
        ledger = _load_ledger(root_path)
        envelope_id = str(envelope.get("envelope_id") or "").strip()
        entry = (ledger.get("envelopes") or {}).get(envelope_id)
        if (
            not isinstance(entry, dict)
            or entry.get("authorization_digest") != envelope.get("authorization_digest")
            or envelope.get("project_id") != project_id(root_path)
            or envelope.get("authorization_digest") != authorization_digest(envelope)
        ):
            raise SpendEnvelopeError("finalization envelope reservation missing or mismatched")
        rows = entry.get("consumptions")
        if not isinstance(rows, list):
            raise SpendEnvelopeError("spend usage ledger envelope entry invalid")
        row = next((item for item in rows if item.get("consumption_id") == cid), None)
        if not isinstance(row, dict):
            raise SpendEnvelopeError("finalization consumption reservation not found")
        completion_core = {
            "outcome": "provider_execution_completed",
            "evidence": proof,
            "evidence_digest": canonical_digest(proof),
        }
        previous = row.get("completion") if isinstance(row.get("completion"), Mapping) else None
        if previous is not None:
            if {key: previous.get(key) for key in completion_core} != completion_core:
                raise SpendEnvelopeError("consumption already finalized with different evidence")
            idempotent = True
        else:
            completion = {**completion_core, "completed_at": now_iso()}
            row["state"] = "completed"
            row["completion"] = completion
            idempotent = False
            entry["updated_at"] = completion["completed_at"]
            ledger["updated_at"] = completion["completed_at"]
            ledger["ledger_digest"] = canonical_digest(
                {key: value for key, value in ledger.items() if key != "ledger_digest"}
            )
            _write_json_atomic(root_path / LEDGER_REL, ledger)
        return {
            "status": "pass",
            "idempotent": idempotent,
            "envelope_id": envelope_id,
            "authorization_digest": str(envelope.get("authorization_digest") or ""),
            "consumption_id": cid,
            "completion": dict(row.get("completion") or completion_core),
        }


def _scope(value: str) -> Dict[str, Any]:
    try:
        payload = json.loads(value or "{}")
    except json.JSONDecodeError as exc:
        raise SpendEnvelopeError("--scope-json must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise SpendEnvelopeError("--scope-json must be a JSON object")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    issue = sub.add_parser("issue", help="write a human-approved v2 phase envelope")
    issue.add_argument("root")
    issue.add_argument("--stage", required=True)
    issue.add_argument("--model", required=True)
    issue.add_argument("--channel", required=True)
    issue.add_argument("--input-sha256", required=True)
    issue.add_argument("--scope-json", default="{}")
    issue.add_argument("--max-calls", type=int, required=True)
    issue.add_argument("--max-attempts", type=int, required=True)
    issue.add_argument("--cost-ceiling", type=float, required=True)
    issue.add_argument("--currency", required=True)
    issue.add_argument("--approver", required=True)
    issue.add_argument("--approval-reference", required=True,
                       help="external/UI approval receipt id, ticket, or immutable source reference")
    issue.add_argument(
        "--source-quote",
        required=True,
        help="verbatim human decision excerpt retained as approval evidence",
    )
    issue.add_argument("--expires-at")
    issue.add_argument("--ttl-hours", type=float, default=24.0)
    issue.add_argument("--envelope-id")
    issue.add_argument("--out")
    for name in ("verify", "consume"):
        cmd = sub.add_parser(name)
        cmd.add_argument("root")
        cmd.add_argument("--envelope", required=True)
        cmd.add_argument("--stage", required=True)
        cmd.add_argument("--model", required=True)
        cmd.add_argument("--channel", required=True)
        cmd.add_argument("--input-sha256", required=True)
        cmd.add_argument("--scope-json", default="{}")
        cmd.add_argument("--consumption-id", required=True)
        cmd.add_argument("--attempt-id", required=True)
        cmd.add_argument("--calls", type=int, required=True)
        cmd.add_argument("--cost", type=float, required=True)
        cmd.add_argument("--currency", required=True)
    finalize_cmd = sub.add_parser(
        "finalize",
        help="close an in-flight reservation using durable provider completion evidence",
    )
    finalize_cmd.add_argument("root")
    finalize_cmd.add_argument("--envelope", required=True)
    finalize_cmd.add_argument("--consumption-id", required=True)
    finalize_cmd.add_argument("--evidence-json", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.cmd == "issue":
            envelope = make_envelope(
                args.root,
                stage=args.stage,
                model=args.model,
                channel=args.channel,
                input_sha256=args.input_sha256,
                scope=_scope(args.scope_json),
                max_calls=args.max_calls,
                max_attempts=args.max_attempts,
                cost_ceiling=args.cost_ceiling,
                currency=args.currency,
                approver=args.approver,
                approval_reference=args.approval_reference,
                source_quote=args.source_quote,
                expires_at=args.expires_at,
                ttl_hours=args.ttl_hours,
                envelope_id=args.envelope_id,
            )
            path = write_envelope(
                args.out or default_envelope_path(args.root, args.stage), envelope
            )
            result = {"status": "issued", "path": str(path), "envelope": envelope}
        elif args.cmd in {"verify", "consume"}:
            envelope = load_envelope(args.envelope)
            kwargs = {
                "stage": args.stage,
                "model": args.model,
                "channel": args.channel,
                "input_sha256": args.input_sha256,
                "scope": _scope(args.scope_json),
                "consumption_id": args.consumption_id,
                "attempt_id": args.attempt_id,
                "calls": args.calls,
                "cost": args.cost,
                "currency": args.currency,
            }
            result = verify(args.root, envelope, **kwargs) if args.cmd == "verify" else consume(
                args.root, envelope, **kwargs
            )
        else:
            envelope = load_envelope(args.envelope)
            result = finalize(
                args.root,
                envelope,
                consumption_id=args.consumption_id,
                evidence=_scope(args.evidence_json),
            )
    except SpendEnvelopeError as exc:
        print(json.dumps({"status": "blocked", "issues": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"pass", "issued"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
