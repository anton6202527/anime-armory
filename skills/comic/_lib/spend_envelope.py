#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comic-local paid-submit authorization envelope and append-only ledger.

Runners may verify and consume an envelope, but never issue one.  A reservation
is taken atomically immediately before a paid submit.  Polling and downloads do
not call this module and therefore do not consume another call/attempt.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import decimal
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Iterator

try:  # POSIX in production; the fallback still gives process-local safety.
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]


ENVELOPE_KIND = "comic_stage_spend_envelope"
LEDGER_KIND = "comic_stage_spend_ledger"
VERSION = 1
STAGE = "image"
OPERATION = "panel_image_generation"
_LOCAL_LOCK = threading.RLock()
_FORBIDDEN_APPROVER = re.compile(
    r"(?:^|[\s._-])(agent|assistant|auto|automatic|automation|bot|codex|claude|"
    r"delegate|delegated|machine|model|runner|system|test|unknown)(?:$|[\s._-])",
    re.IGNORECASE,
)
_DECIMAL_CONTEXT = decimal.Context(prec=28)


class SpendAuthorizationError(RuntimeError):
    """A machine-consumable fail-closed authorization stop."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": "comic_spend_authorization_stop",
            "version": VERSION,
            "status": "needs_human_budget_authorization",
            "code": self.code,
            "message": self.message,
            "human_gate": True,
            "retryable_after_authorization": True,
            "details": self.details,
        }


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_utc(value: dt.datetime | None = None) -> str:
    current = value or now_utc()
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    return current.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(raw: str, *, field: str) -> dt.datetime:
    text = str(raw or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise SpendAuthorizationError("invalid_time", f"{field} must be ISO-8601 with timezone", field=field) from exc
    if parsed.tzinfo is None:
        raise SpendAuthorizationError("invalid_time", f"{field} must include timezone", field=field)
    return parsed.astimezone(dt.timezone.utc)


def money(raw: Any, *, field: str, allow_zero: bool = False) -> decimal.Decimal:
    if isinstance(raw, bool) or raw is None:
        raise SpendAuthorizationError("unknown_cost", f"{field} is missing", field=field)
    try:
        value = _DECIMAL_CONTEXT.create_decimal(str(raw).strip())
    except (decimal.InvalidOperation, ValueError) as exc:
        raise SpendAuthorizationError("unknown_cost", f"{field} is not a finite decimal", field=field) from exc
    if not value.is_finite() or (value < 0 if allow_zero else value <= 0):
        raise SpendAuthorizationError("unknown_cost", f"{field} must be {'non-negative' if allow_zero else 'positive'}", field=field)
    return value


def money_text(value: decimal.Decimal | Any) -> str:
    number = value if isinstance(value, decimal.Decimal) else money(value, field="cost", allow_zero=True)
    normalized = number.normalize()
    return format(normalized, "f") if normalized != 0 else "0"


def project_binding(root: Path) -> dict[str, str]:
    resolved = root.expanduser().resolve()
    return {
        "project_name": resolved.name,
        "project_path_sha256": hashlib.sha256(str(resolved).encode("utf-8")).hexdigest(),
    }


def panel_jobs_input_material(data: dict[str, Any], chapter: str) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        panel_id = str(job.get("panel_id") or "").strip()
        execution_sha = str(job.get("execution_input_sha256") or "").strip()
        if not panel_id or not re.fullmatch(r"[0-9a-f]{64}", execution_sha, re.IGNORECASE):
            raise SpendAuthorizationError(
                "unknown_input",
                "every paid panel must have panel_id and execution_input_sha256 before authorization",
                panel_id=panel_id,
            )
        rows.append(
            {
                "panel_id": panel_id,
                "execution_input_sha256": execution_sha.lower(),
                "source_contract_sha256": str(job.get("source_contract_sha256") or ""),
                "submit_prompt_sha256": str(job.get("submit_prompt_sha256") or ""),
            }
        )
    if not rows:
        raise SpendAuthorizationError("unknown_input", "panel_jobs has no executable paid panels")
    return {
        "kind": "comic_panel_execution_input",
        "version": 1,
        "chapter": chapter,
        "panels": rows,
    }


def panel_jobs_input_sha256(data: dict[str, Any], chapter: str) -> str:
    return sha256_json(panel_jobs_input_material(data, chapter))


def default_envelope_path(root: Path, chapter: str) -> Path:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", chapter).strip("_") or "chapter"
    return root / "生产数据" / "spend_envelopes" / f"image_{safe}.json"


def ledger_path(root: Path) -> Path:
    return root / "生产数据" / "spend_ledger.json"


def requested_scope(chapter: str, panel_ids: list[str] | set[str], *, force: bool) -> dict[str, Any]:
    panels = sorted({str(panel).strip() for panel in panel_ids if str(panel).strip()})
    if not panels:
        raise SpendAuthorizationError("empty_scope", "paid submit scope has no panels")
    return {
        "operation": OPERATION,
        "chapter": chapter,
        "panel_ids": panels,
        "force": bool(force),
    }


def _authorization_material(envelope: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in envelope.items() if key != "authorization_sha256"}


def _validate_human_evidence(approver: str, reference: str, quote: str) -> None:
    name = approver.strip()
    if len(name) < 2 or _FORBIDDEN_APPROVER.search(name):
        raise SpendAuthorizationError(
            "human_approver_required",
            "approver must identify a real human, not an agent/runner/delegated policy",
            approver=name,
        )
    if len(reference.strip()) < 4:
        raise SpendAuthorizationError("approval_reference_required", "approval_reference must locate the human approval evidence")
    if len(quote.strip()) < 4:
        raise SpendAuthorizationError("source_quote_required", "source_quote must quote the human's budget approval")


def issue_envelope(
    root: Path,
    *,
    chapter: str,
    data: dict[str, Any],
    model: str,
    channel: str,
    scope: dict[str, Any],
    expires_at: str,
    max_calls: int,
    max_attempts: int,
    currency: str,
    max_total: Any,
    max_cost_per_call: Any,
    approver: str,
    approval_reference: str,
    source_quote: str,
    issued_at: str | None = None,
) -> dict[str, Any]:
    """Build an envelope from explicit human evidence; runners never call this."""
    _validate_human_evidence(approver, approval_reference, source_quote)
    if not str(model).strip() or not str(channel).strip():
        raise SpendAuthorizationError("backend_binding_required", "model and channel are required")
    if int(max_calls) <= 0 or int(max_attempts) <= 0:
        raise SpendAuthorizationError("invalid_limit", "max_calls and max_attempts must be positive")
    total = money(max_total, field="cost.max_total")
    per_call = money(max_cost_per_call, field="cost.max_cost_per_call")
    if per_call > total:
        raise SpendAuthorizationError("invalid_cost_limit", "max_cost_per_call cannot exceed max_total")
    curr = str(currency or "").strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9_-]{1,11}", curr):
        raise SpendAuthorizationError("unknown_cost", "cost.currency must be an explicit currency/unit")
    issued = parse_time(issued_at or iso_utc(), field="issued_at")
    expiry = parse_time(expires_at, field="expires_at")
    if expiry <= issued:
        raise SpendAuthorizationError("expired_envelope", "expires_at must be after issued_at")
    requested = requested_scope(chapter, scope.get("panel_ids") or [], force=bool(scope.get("force")))
    if requested != scope:
        raise SpendAuthorizationError("invalid_scope", "scope must use the canonical operation/chapter/panel_ids/force shape")
    known_panels = {row["panel_id"] for row in panel_jobs_input_material(data, chapter)["panels"]}
    unknown_panels = sorted(set(requested["panel_ids"]) - known_panels)
    if unknown_panels:
        raise SpendAuthorizationError(
            "invalid_scope", "approved scope contains panels absent from the bound input", panel_ids=unknown_panels
        )
    envelope: dict[str, Any] = {
        "kind": ENVELOPE_KIND,
        "version": VERSION,
        "envelope_id": f"comic-image-{uuid.uuid4().hex}",
        "issued_at": iso_utc(issued),
        "expires_at": iso_utc(expiry),
        "project": project_binding(root),
        "stage": STAGE,
        "input_sha256": panel_jobs_input_sha256(data, chapter),
        "model": str(model).strip(),
        "channel": str(channel).strip(),
        "scope": requested,
        "limits": {"max_calls": int(max_calls), "max_attempts": int(max_attempts)},
        "cost": {
            "currency": curr,
            "max_total": money_text(total),
            "max_cost_per_call": money_text(per_call),
        },
        "approval": {
            "approver": approver.strip(),
            "approval_reference": approval_reference.strip(),
            "source_quote": source_quote.strip(),
        },
    }
    envelope["authorization_sha256"] = sha256_json(_authorization_material(envelope))
    return envelope


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def save_envelope(path: Path, envelope: dict[str, Any]) -> None:
    if envelope.get("authorization_sha256") != sha256_json(_authorization_material(envelope)):
        raise SpendAuthorizationError("tampered_envelope", "authorization digest does not match envelope")
    atomic_write_json(path, envelope)


def load_envelope(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpendAuthorizationError("missing_envelope", "paid submit requires a human-issued spend envelope", path=str(path)) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise SpendAuthorizationError("invalid_envelope", "spend envelope is unreadable", path=str(path)) from exc
    if not isinstance(payload, dict):
        raise SpendAuthorizationError("invalid_envelope", "spend envelope must be a JSON object", path=str(path))
    return payload


def _validate_envelope(
    envelope: dict[str, Any],
    root: Path,
    *,
    stage: str,
    input_sha256: str,
    model: str,
    channel: str,
    scope: dict[str, Any],
    at: dt.datetime | None = None,
) -> tuple[decimal.Decimal, decimal.Decimal, str]:
    if envelope.get("kind") != ENVELOPE_KIND or envelope.get("version") != VERSION:
        raise SpendAuthorizationError("invalid_envelope", "unsupported spend envelope kind/version")
    digest = str(envelope.get("authorization_sha256") or "")
    if not digest or digest != sha256_json(_authorization_material(envelope)):
        raise SpendAuthorizationError("tampered_envelope", "spend envelope authorization digest mismatch")
    approval = envelope.get("approval") if isinstance(envelope.get("approval"), dict) else {}
    _validate_human_evidence(
        str(approval.get("approver") or ""),
        str(approval.get("approval_reference") or ""),
        str(approval.get("source_quote") or ""),
    )
    expiry = parse_time(str(envelope.get("expires_at") or ""), field="expires_at")
    if (at or now_utc()).astimezone(dt.timezone.utc) >= expiry:
        raise SpendAuthorizationError("expired_envelope", "spend envelope has expired", expires_at=iso_utc(expiry))
    expected = {
        "project": project_binding(root),
        "stage": stage,
        "input_sha256": input_sha256,
        "model": model,
        "channel": channel,
    }
    mismatches = {
        key: {"approved": envelope.get(key), "requested": value}
        for key, value in expected.items()
        if envelope.get(key) != value
    }
    if mismatches:
        raise SpendAuthorizationError("binding_mismatch", "project/stage/input/model/channel changed", mismatches=mismatches)
    approved_scope = envelope.get("scope") if isinstance(envelope.get("scope"), dict) else {}
    scope_ok = (
        approved_scope.get("operation") == scope.get("operation") == OPERATION
        and approved_scope.get("chapter") == scope.get("chapter")
        and set(scope.get("panel_ids") or []).issubset(set(approved_scope.get("panel_ids") or []))
        and (not bool(scope.get("force")) or bool(approved_scope.get("force")))
    )
    if not scope_ok:
        raise SpendAuthorizationError("scope_expanded", "requested paid scope exceeds the human-approved scope", approved=approved_scope, requested=scope)
    limits = envelope.get("limits") if isinstance(envelope.get("limits"), dict) else {}
    try:
        max_calls = int(limits.get("max_calls"))
        max_attempts = int(limits.get("max_attempts"))
    except (TypeError, ValueError) as exc:
        raise SpendAuthorizationError("invalid_limit", "max_calls/max_attempts are missing") from exc
    if max_calls <= 0 or max_attempts <= 0:
        raise SpendAuthorizationError("invalid_limit", "max_calls/max_attempts must be positive")
    cost = envelope.get("cost") if isinstance(envelope.get("cost"), dict) else {}
    total = money(cost.get("max_total"), field="cost.max_total")
    per_call = money(cost.get("max_cost_per_call"), field="cost.max_cost_per_call")
    currency = str(cost.get("currency") or "").strip().upper()
    if not currency or per_call > total:
        raise SpendAuthorizationError("unknown_cost", "cost currency/limits are incomplete or inconsistent")
    return total, per_call, currency


def _empty_ledger() -> dict[str, Any]:
    return {"kind": LEDGER_KIND, "version": VERSION, "updated_at": iso_utc(), "envelopes": {}}


def _load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_ledger()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpendAuthorizationError("ledger_unreadable", "spend ledger is unreadable; refusing paid submit", path=str(path)) from exc
    if payload.get("kind") != LEDGER_KIND or payload.get("version") != VERSION or not isinstance(payload.get("envelopes"), dict):
        raise SpendAuthorizationError("ledger_invalid", "spend ledger schema is invalid; refusing paid submit", path=str(path))
    return payload


@contextlib.contextmanager
def _locked_ledger(root: Path, *, write: bool) -> Iterator[tuple[Path, dict[str, Any]]]:
    path = ledger_path(root)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCAL_LOCK:
        with lock_path.open("a+", encoding="utf-8") as lock:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                ledger = _load_ledger(path)
                try:
                    yield path, ledger
                finally:
                    # Callers only mutate after a complete record is assembled.
                    # Persist fail-closed violation/unknown-settlement states even
                    # when they deliberately raise SpendAuthorizationError.
                    if write:
                        ledger["updated_at"] = iso_utc()
                        atomic_write_json(path, ledger)
            finally:
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _entry(ledger: dict[str, Any], envelope: dict[str, Any], *, create: bool) -> dict[str, Any]:
    envelope_id = str(envelope.get("envelope_id") or "")
    if not envelope_id:
        raise SpendAuthorizationError("invalid_envelope", "envelope_id is missing")
    entries = ledger["envelopes"]
    if envelope_id not in entries:
        if not create:
            return {"authorization_sha256": envelope.get("authorization_sha256"), "reservations": {}, "violations": []}
        entries[envelope_id] = {
            "authorization_sha256": envelope.get("authorization_sha256"),
            "reservations": {},
            "violations": [],
            "blocked": False,
        }
    entry = entries[envelope_id]
    if entry.get("authorization_sha256") != envelope.get("authorization_sha256"):
        raise SpendAuthorizationError("ledger_binding_mismatch", "ledger envelope digest differs from current authorization")
    if not isinstance(entry.get("reservations"), dict):
        raise SpendAuthorizationError("ledger_invalid", "ledger reservations are invalid")
    return entry


def _totals(entry: dict[str, Any]) -> tuple[int, int, decimal.Decimal]:
    reservations = list(entry.get("reservations", {}).values())
    calls = len(reservations)
    attempts = len({str(row.get("attempt_id") or "") for row in reservations})
    committed = decimal.Decimal("0")
    for row in reservations:
        if row.get("status") in {"settled", "violation"}:
            committed += money(row.get("actual_cost"), field="ledger.actual_cost", allow_zero=True)
        else:
            committed += money(row.get("reserved_cost"), field="ledger.reserved_cost", allow_zero=True)
    return calls, attempts, committed


def inspect_authorization(
    envelope_path: Path,
    root: Path,
    *,
    stage: str,
    input_sha256: str,
    model: str,
    channel: str,
    scope: dict[str, Any],
    next_attempt_id: str | None = None,
) -> dict[str, Any]:
    envelope = load_envelope(envelope_path)
    total, per_call, currency = _validate_envelope(
        envelope, root, stage=stage, input_sha256=input_sha256, model=model, channel=channel, scope=scope
    )
    with _locked_ledger(root, write=False) as (_path, ledger):
        entry = _entry(ledger, envelope, create=False)
        if entry.get("blocked") or entry.get("violations"):
            raise SpendAuthorizationError("ledger_blocked", "a prior cost violation blocks further paid submits")
        in_flight = sorted(
            key
            for key, row in entry.get("reservations", {}).items()
            if row.get("status") == "reserved"
        )
        if in_flight:
            raise SpendAuthorizationError(
                "submission_state_unknown",
                "an earlier paid submit is still in-flight/ambiguous; reconcile its provider receipt before continuing",
                consumption_ids=in_flight,
            )
        calls, attempts, committed = _totals(entry)
        attempt_ids = {
            str(row.get("attempt_id") or "") for row in entry.get("reservations", {}).values()
        }
    limits = envelope["limits"]
    attempt_authorized = (
        not next_attempt_id
        or next_attempt_id in attempt_ids
        or attempts < int(limits["max_attempts"])
    )
    return {
        # attempt limits are keyed by phase retry-round.  Without a requested
        # next attempt_id, inspect cannot know whether the next call reuses an
        # existing round (allowed) or opens a new one (possibly blocked).
        "status": "authorized" if (
            calls < int(limits["max_calls"])
            and committed + per_call <= total
            and attempt_authorized
        ) else "exhausted",
        "envelope_id": envelope["envelope_id"],
        "authorization_sha256": envelope["authorization_sha256"],
        "currency": currency,
        "max_cost_per_call": money_text(per_call),
        "used_calls": calls,
        "remaining_calls": max(0, int(limits["max_calls"]) - calls),
        "used_attempts": attempts,
        "remaining_attempts": max(0, int(limits["max_attempts"]) - attempts),
        "attempt_limit_checked_at_reserve": True,
        "next_attempt_id": next_attempt_id or "",
        "next_attempt_authorized": attempt_authorized if next_attempt_id else None,
        "committed_cost": money_text(committed),
        "remaining_cost": money_text(max(decimal.Decimal("0"), total - committed)),
    }


def reserve_submission(
    envelope_path: Path,
    root: Path,
    *,
    stage: str,
    input_sha256: str,
    model: str,
    channel: str,
    scope: dict[str, Any],
    consumption_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    """Atomically consume one call/attempt immediately before a paid submit."""
    if not consumption_id.strip() or not attempt_id.strip():
        raise SpendAuthorizationError("invalid_consumption_id", "consumption_id and attempt_id are required")
    envelope = load_envelope(envelope_path)
    total, per_call, currency = _validate_envelope(
        envelope, root, stage=stage, input_sha256=input_sha256, model=model, channel=channel, scope=scope
    )
    request_sha = sha256_json(
        {
            "authorization_sha256": envelope["authorization_sha256"],
            "stage": stage,
            "input_sha256": input_sha256,
            "model": model,
            "channel": channel,
            "scope": scope,
            "attempt_id": attempt_id,
        }
    )
    with _locked_ledger(root, write=True) as (_path, ledger):
        entry = _entry(ledger, envelope, create=True)
        existing = entry["reservations"].get(consumption_id)
        if existing is not None:
            if existing.get("request_sha256") != request_sha:
                raise SpendAuthorizationError("idempotency_conflict", "consumption_id was already used for a different request")
            # A reservation is written immediately before the provider call.  A
            # crash can therefore leave an ambiguous paid submit behind.  The
            # provider APIs used by comic do not accept this ID as a real
            # idempotency key, so returning a no-op here and submitting again
            # would be a double-spend bug.  Settlement is idempotent; submit is
            # deliberately not resumable without a provider receipt.
            raise SpendAuthorizationError(
                "submission_state_unknown" if existing.get("status") == "reserved" else "already_consumed",
                "consumption_id is already reserved/consumed; do not submit it again",
                consumption_id=consumption_id,
                status=existing.get("status"),
            )
        if entry.get("blocked") or entry.get("violations"):
            raise SpendAuthorizationError("ledger_blocked", "a prior cost violation blocks further paid submits")
        calls, attempts, committed = _totals(entry)
        limits = envelope["limits"]
        if calls >= int(limits["max_calls"]):
            raise SpendAuthorizationError("max_calls_exhausted", "approved paid-call limit is exhausted", used_calls=calls)
        existing_attempt_ids = {
            str(row.get("attempt_id") or "") for row in entry.get("reservations", {}).values()
        }
        if attempt_id not in existing_attempt_ids and attempts >= int(limits["max_attempts"]):
            raise SpendAuthorizationError("max_attempts_exhausted", "approved paid-attempt limit is exhausted", used_attempts=attempts)
        if committed + per_call > total:
            raise SpendAuthorizationError(
                "cost_ceiling_exhausted",
                "remaining approved cost cannot cover the worst-case next call",
                currency=currency,
                committed_cost=money_text(committed),
                max_total=money_text(total),
                next_reservation=money_text(per_call),
            )
        record = {
            "consumption_id": consumption_id,
            "attempt_id": attempt_id,
            "request_sha256": request_sha,
            "status": "reserved",
            "reserved_at": iso_utc(),
            "reserved_cost": money_text(per_call),
            "currency": currency,
            "scope": scope,
        }
        entry["reservations"][consumption_id] = record
        return dict(record, idempotent=False)


def settle_submission(
    envelope_path: Path,
    root: Path,
    *,
    consumption_id: str,
    actual_cost: Any | None,
) -> dict[str, Any]:
    """Atomically settle actual cost; unknown or over-limit actuals block the ledger."""
    envelope = load_envelope(envelope_path)
    # Verify immutable evidence/cost schema even though request bindings were checked at reserve time.
    digest = str(envelope.get("authorization_sha256") or "")
    if not digest or digest != sha256_json(_authorization_material(envelope)):
        raise SpendAuthorizationError("tampered_envelope", "spend envelope changed after reservation")
    cost = envelope.get("cost") if isinstance(envelope.get("cost"), dict) else {}
    total = money(cost.get("max_total"), field="cost.max_total")
    per_call = money(cost.get("max_cost_per_call"), field="cost.max_cost_per_call")
    with _locked_ledger(root, write=True) as (_path, ledger):
        entry = _entry(ledger, envelope, create=False)
        record = entry.get("reservations", {}).get(consumption_id)
        if record is None:
            raise SpendAuthorizationError("unknown_consumption", "cannot settle an unreserved paid submit")
        if record.get("status") in {"settled", "violation"}:
            actual = money(actual_cost, field="actual_cost", allow_zero=True)
            recorded = money(record.get("actual_cost"), field="ledger.actual_cost", allow_zero=True)
            if recorded != actual:
                raise SpendAuthorizationError("idempotency_conflict", "settlement actual_cost differs from prior settlement")
            return dict(record, idempotent=True)
        try:
            actual = money(actual_cost, field="actual_cost", allow_zero=True)
        except SpendAuthorizationError as exc:
            record.update(
                {
                    "status": "settlement_unknown",
                    "settlement_error": exc.code,
                    "settlement_failed_at": iso_utc(),
                }
            )
            entry["blocked"] = True
            raise SpendAuthorizationError(
                "settlement_unknown",
                "actual cost is unknown; the worst-case reservation remains and further submits are blocked",
                consumption_id=consumption_id,
            ) from exc
        _calls, _attempts, before = _totals(entry)
        reserved = money(record.get("reserved_cost"), field="ledger.reserved_cost", allow_zero=True)
        after = before - reserved + actual
        record.update({"settled_at": iso_utc(), "actual_cost": money_text(actual)})
        if actual > per_call or after > total:
            record["status"] = "violation"
            entry["blocked"] = True
            violation = {
                "code": "actual_cost_exceeded_authorization",
                "consumption_id": consumption_id,
                "actual_cost": money_text(actual),
                "max_cost_per_call": money_text(per_call),
                "committed_after": money_text(after),
                "max_total": money_text(total),
                "recorded_at": iso_utc(),
            }
            entry.setdefault("violations", []).append(violation)
            raise SpendAuthorizationError(
                "actual_cost_exceeded_authorization",
                "actual cost exceeded the reserved/approved ceiling; ledger is blocked",
                violation=violation,
            )
        record["status"] = "settled"
        record["released_cost"] = money_text(max(decimal.Decimal("0"), reserved - actual))
        record["additional_cost"] = money_text(max(decimal.Decimal("0"), actual - reserved))
        record.pop("settlement_error", None)
        record.pop("settlement_failed_at", None)
        unresolved = any(
            row.get("status") == "settlement_unknown"
            for key, row in entry.get("reservations", {}).items()
            if key != consumption_id
        )
        entry["blocked"] = bool(entry.get("violations")) or unresolved
        return dict(record, idempotent=False)


def structured_stop(exc: SpendAuthorizationError, *, envelope_path: Path | None = None) -> str:
    payload = exc.as_dict()
    if envelope_path is not None:
        payload["envelope_path"] = str(envelope_path)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _load_jobs(root: Path, chapter: str) -> dict[str, Any]:
    path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpendAuthorizationError("unknown_input", "panel_jobs.json is missing", path=str(path)) from exc


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue/inspect comic paid-stage spend envelopes")
    sub = parser.add_subparsers(dest="command", required=True)
    issue = sub.add_parser("issue", help="human-only: create an immutable paid-stage authorization envelope")
    issue.add_argument("project_root")
    issue.add_argument("--chapter", default="第1话")
    issue.add_argument("--panels", default="all", help="comma-separated panel IDs or all")
    issue.add_argument("--force", action="store_true", help="also authorize paid replacement of accepted panels")
    issue.add_argument("--model", default="", help="exact model; defaults to panel_jobs.model")
    issue.add_argument("--channel", default="", help="exact channel; defaults to panel_jobs.channel")
    issue.add_argument("--expires-at", required=True, help="ISO-8601 timestamp with timezone")
    issue.add_argument("--max-calls", type=int, required=True)
    issue.add_argument("--max-attempts", type=int, required=True)
    issue.add_argument("--currency", required=True)
    issue.add_argument("--max-total", required=True)
    issue.add_argument("--max-cost-per-call", required=True)
    issue.add_argument("--approver", required=True, help="real human name")
    issue.add_argument("--approval-reference", required=True, help="message/ticket/document locator")
    issue.add_argument("--source-quote", required=True, help="verbatim human authorization quote")
    issue.add_argument("--output", default="")
    inspect = sub.add_parser("inspect", help="verify current binding and show remaining budget without consuming")
    inspect.add_argument("project_root")
    inspect.add_argument("--chapter", default="第1话")
    inspect.add_argument("--panels", default="all")
    inspect.add_argument("--force", action="store_true")
    inspect.add_argument("--model", default="")
    inspect.add_argument("--channel", default="")
    inspect.add_argument("--envelope", default="")
    inspect.add_argument("--attempt-id", default="", help="optional next phase retry-round ID to evaluate")
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    try:
        data = _load_jobs(root, args.chapter)
        all_panels = [str(job.get("panel_id") or "") for job in data.get("jobs") or [] if isinstance(job, dict)]
        panels = all_panels if args.panels == "all" else [part.strip() for part in args.panels.split(",") if part.strip()]
        model = args.model.strip() or str(data.get("model") or "").strip()
        channel = args.channel.strip() or str(data.get("channel") or "").strip()
        scope = requested_scope(args.chapter, panels, force=args.force)
        path = Path(getattr(args, "output", "") or getattr(args, "envelope", "") or default_envelope_path(root, args.chapter))
        if args.command == "issue":
            envelope = issue_envelope(
                root,
                chapter=args.chapter,
                data=data,
                model=model,
                channel=channel,
                scope=scope,
                expires_at=args.expires_at,
                max_calls=args.max_calls,
                max_attempts=args.max_attempts,
                currency=args.currency,
                max_total=args.max_total,
                max_cost_per_call=args.max_cost_per_call,
                approver=args.approver,
                approval_reference=args.approval_reference,
                source_quote=args.source_quote,
            )
            save_envelope(path, envelope)
            print(json.dumps({"status": "issued", "path": str(path), "envelope": envelope}, ensure_ascii=False, sort_keys=True))
        else:
            status = inspect_authorization(
                path,
                root,
                stage=STAGE,
                input_sha256=panel_jobs_input_sha256(data, args.chapter),
                model=model,
                channel=channel,
                scope=scope,
                next_attempt_id=args.attempt_id.strip() or None,
            )
            print(json.dumps(status, ensure_ascii=False, sort_keys=True))
        return 0
    except SpendAuthorizationError as exc:
        path = locals().get("path")
        print(structured_stop(exc, envelope_path=path if isinstance(path, Path) else None), file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(cli())
