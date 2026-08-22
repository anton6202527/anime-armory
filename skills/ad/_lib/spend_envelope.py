#!/usr/bin/env python3
"""广告线阶段预算信封：精确绑定、限额消费、并发安全且重放 fail-closed。

本模块只属于 ad 线。付费 runner 在每次真正提交前调用 ``consume``；查询/下载既有
submit_id 不消费。授权摘要是防误改证据，不冒充数字签名，``approver`` 必须是真实责任人。
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

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


LINE = "ad"
KIND = "ad_phase_spend_envelope"
VERSION = 2
ATTEMPT_ID_SEMANTICS = "phase_retry_round"
LEDGER_KIND = "ad_phase_spend_usage_ledger"
LEDGER_VERSION = 1
LEDGER_REL = Path("生产数据") / "spend_envelope_usage.json"
DEFAULT_DIR_REL = Path("生产数据") / "spend_envelopes"
INVALID_IDENTITY = {"", "unknown", "system", "agent", "auto", "any", "test"}
INVALID_IDENTITY_PREFIXES = ("agent:", "auto:", "delegate:", "system:")


class SpendEnvelopeError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def authorization_digest(payload: Mapping[str, Any]) -> str:
    return canonical_digest({k: v for k, v in payload.items() if k != "authorization_digest"})


def normalize_sha256(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("sha256:"):
        text = text[7:]
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise SpendEnvelopeError("input_sha256 must be a full SHA-256 digest")
    return "sha256:" + text


def project_id(root: str | Path) -> str:
    return "sha256:" + hashlib.sha256(
        str(Path(root).expanduser().resolve()).encode("utf-8")
    ).hexdigest()


def _invalid_approver(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in INVALID_IDENTITY or text.startswith(INVALID_IDENTITY_PREFIXES)


def _approval_evidence(reference: Any, source_quote: Any) -> tuple[str, str]:
    """Require an approval record reference plus the human decision excerpt."""
    reference = str(reference or "").strip()
    source_quote = str(source_quote or "").strip()
    lowered_ref = reference.lower()
    lowered_quote = source_quote.lower()
    if not reference or lowered_ref in INVALID_IDENTITY or lowered_ref.startswith(
        INVALID_IDENTITY_PREFIXES
    ):
        raise SpendEnvelopeError("approval_reference must point to the human approval record")
    if not source_quote or lowered_quote in INVALID_IDENTITY or lowered_quote.startswith(
        INVALID_IDENTITY_PREFIXES
    ):
        raise SpendEnvelopeError("source_quote must quote the human approval decision")
    return reference, source_quote


def default_envelope_path(root: str | Path, stage: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(stage)).strip("._")
    return Path(root).expanduser().resolve() / DEFAULT_DIR_REL / f"{safe or 'stage'}.json"


def _aware(value: Any) -> Optional[datetime]:
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
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise SpendEnvelopeError(f"{field} must be a positive integer") from exc
    if result <= 0 or str(value).strip() not in {str(result), f"+{result}"}:
        raise SpendEnvelopeError(f"{field} must be a positive integer")
    return result


def _amount(value: Any, currency: Any, field: str) -> tuple[float, str]:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SpendEnvelopeError(f"{field} must have a finite non-negative amount") from exc
    unit = str(currency or "").strip()
    if not math.isfinite(number) or number < 0 or not unit:
        raise SpendEnvelopeError(f"{field} must have amount and currency")
    return number, unit


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
    scope: Optional[Mapping[str, Any]] = None,
    expires_at: Optional[str] = None,
    ttl_hours: float = 24.0,
    envelope_id: Optional[str] = None,
    issued_at: Optional[str] = None,
) -> Dict[str, Any]:
    stage, model, channel, approver = map(
        lambda value: str(value or "").strip(), (stage, model, channel, approver)
    )
    approval_reference, source_quote = _approval_evidence(approval_reference, source_quote)
    if not stage:
        raise SpendEnvelopeError("stage is required")
    if model.lower() in INVALID_IDENTITY:
        raise SpendEnvelopeError("model must be a concrete model/version")
    if channel.lower() in INVALID_IDENTITY:
        raise SpendEnvelopeError("channel must be a concrete access path")
    if _invalid_approver(approver):
        raise SpendEnvelopeError("approver must identify a real accountable human")
    calls = _positive_int(max_calls, "max_calls")
    attempts = _positive_int(max_attempts, "max_attempts")
    ceiling, unit = _amount(cost_ceiling, currency, "cost_ceiling")
    issued = _aware(issued_at or now_iso())
    expiry = _aware(expires_at) if expires_at else (
        issued + timedelta(hours=float(ttl_hours)) if issued else None
    )
    if issued is None or expiry is None or expiry <= issued:
        raise SpendEnvelopeError("issued_at/expires_at must be timezone-aware and ordered")
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "envelope_id": str(envelope_id or f"ad-{stage}-{uuid.uuid4().hex[:16]}"),
        "line": LINE,
        "project_id": project_id(root),
        "stage": stage,
        "model": model,
        "channel": channel,
        "input_sha256": normalize_sha256(input_sha256),
        "scope": dict(scope or {}),
        "issued_at": issued.replace(microsecond=0).isoformat(),
        "expires_at": expiry.replace(microsecond=0).isoformat(),
        "decision": "approved",
        "attempt_id_semantics": ATTEMPT_ID_SEMANTICS,
        "approver": approver,
        "approval_reference": approval_reference,
        "source_quote": source_quote,
        "limits": {
            "max_calls": calls,
            "max_attempts": attempts,
            "cost_ceiling": {"amount": ceiling, "currency": unit},
        },
        "ceiling": {"amount": ceiling, "currency": unit},
    }
    payload["authorization_digest"] = authorization_digest(payload)
    return payload


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def write_envelope(path: str | Path, payload: Mapping[str, Any]) -> Path:
    target = Path(path).expanduser().resolve()
    _write(target, payload)
    return target


def load_envelope(path: str | Path) -> Dict[str, Any]:
    try:
        payload = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpendEnvelopeError("spend envelope missing or invalid") from exc
    if not isinstance(payload, dict):
        raise SpendEnvelopeError("spend envelope must be a JSON object")
    return payload


def _new_ledger(root: str | Path) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "kind": LEDGER_KIND, "version": LEDGER_VERSION, "line": LINE,
        "project_id": project_id(root), "envelopes": {}, "updated_at": now_iso(),
    }
    payload["ledger_digest"] = canonical_digest(payload)
    return payload


def _load_ledger(root: str | Path) -> Dict[str, Any]:
    path = Path(root).expanduser().resolve() / LEDGER_REL
    if not path.exists():
        return _new_ledger(root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpendEnvelopeError("spend usage ledger is unreadable/corrupt") from exc
    if not isinstance(payload, dict):
        raise SpendEnvelopeError("spend usage ledger must be a JSON object")
    expected = canonical_digest({k: v for k, v in payload.items() if k != "ledger_digest"})
    if (
        payload.get("kind") != LEDGER_KIND
        or payload.get("version") != LEDGER_VERSION
        or payload.get("project_id") != project_id(root)
        or payload.get("ledger_digest") != expected
        or not isinstance(payload.get("envelopes"), dict)
    ):
        raise SpendEnvelopeError("spend usage ledger identity/digest mismatch")
    return payload


@contextmanager
def _lock(root: str | Path, timeout: float = 10.0) -> Iterator[None]:
    path = Path(root).expanduser().resolve() / LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
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
    deadline = time.monotonic() + timeout  # pragma: no cover
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
        lock_path.unlink(missing_ok=True)


def _request(**values: Any) -> Dict[str, Any]:
    calls = _positive_int(values.get("calls"), "calls")
    cost, unit = _amount(values.get("cost"), values.get("currency"), "cost")
    consumption_id = str(values.get("consumption_id") or "").strip()
    attempt_id = str(values.get("attempt_id") or "").strip()
    if not consumption_id or not attempt_id:
        raise SpendEnvelopeError("consumption_id and attempt_id are required")
    return {
        "consumption_id": consumption_id,
        "attempt_id": attempt_id,
        "calls": calls,
        "cost": {"amount": cost, "currency": unit},
        "stage": str(values.get("stage") or "").strip(),
        "model": str(values.get("model") or "").strip(),
        "channel": str(values.get("channel") or "").strip(),
        "input_sha256": normalize_sha256(values.get("input_sha256")),
        "scope": dict(values.get("scope") or {}),
    }


def _base_request(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "consumption_id", "attempt_id", "calls", "cost", "stage", "model", "channel",
            "input_sha256", "scope",
        )
    }


def _effective_cost(row: Mapping[str, Any]) -> float:
    settlement = row.get("settlement") if isinstance(row.get("settlement"), Mapping) else {}
    actual = settlement.get("actual_cost") if isinstance(settlement.get("actual_cost"), Mapping) else {}
    source = actual if actual else (row.get("cost") if isinstance(row.get("cost"), Mapping) else {})
    return float(source.get("amount") or 0.0)


def _issues(root: str | Path, auth: Mapping[str, Any], req: Mapping[str, Any],
            rows: Sequence[Mapping[str, Any]]) -> list[str]:
    issues: list[str] = []
    if auth.get("kind") != KIND or auth.get("version") != VERSION or auth.get("line") != LINE:
        issues.append("spend envelope kind/version/line mismatch")
    if auth.get("project_id") != project_id(root):
        issues.append("spend envelope project mismatch")
    if auth.get("authorization_digest") != authorization_digest(auth):
        issues.append("spend envelope authorization_digest mismatch")
    if str(auth.get("decision") or "").lower() != "approved":
        issues.append("spend envelope decision must be approved")
    if auth.get("attempt_id_semantics") != ATTEMPT_ID_SEMANTICS:
        issues.append("spend envelope attempt_id_semantics mismatch")
    if _invalid_approver(auth.get("approver")):
        issues.append("spend envelope approver invalid")
    if not str(auth.get("approval_reference") or "").strip():
        issues.append("spend envelope approval_reference missing")
    if not str(auth.get("source_quote") or "").strip():
        issues.append("spend envelope source_quote missing")
    issued, expiry = _aware(auth.get("issued_at")), _aware(auth.get("expires_at"))
    now = datetime.now(timezone.utc)
    if issued is None or expiry is None or expiry <= issued:
        issues.append("spend envelope timestamps invalid")
    elif expiry <= now:
        issues.append("spend envelope expired")
    elif issued > now + timedelta(minutes=5):
        issues.append("spend envelope issued_at is in the future")
    for key in ("stage", "model", "channel", "input_sha256", "scope"):
        if auth.get(key) != req.get(key):
            issues.append(f"spend envelope {key} mismatch")
    limits = auth.get("limits") if isinstance(auth.get("limits"), Mapping) else {}
    try:
        max_calls = _positive_int(limits.get("max_calls"), "max_calls")
        max_attempts = _positive_int(limits.get("max_attempts"), "max_attempts")
        cap = limits.get("cost_ceiling") if isinstance(limits.get("cost_ceiling"), Mapping) else {}
        cap_amount, cap_unit = _amount(cap.get("amount"), cap.get("currency"), "cost_ceiling")
    except SpendEnvelopeError as exc:
        return issues + [str(exc)]
    existing = next((row for row in rows if row.get("consumption_id") == req["consumption_id"]), None)
    if existing is not None:
        if _base_request(existing) != dict(req):
            issues.append("consumption_id already exists with different bindings")
        if isinstance(existing.get("settlement"), Mapping):
            issues.append(
                "consumption_id already settled; provider replay blocked (query existing submit_id)"
            )
        else:
            issues.append(
                "consumption_id has uncertain in_flight provider state; provider replay blocked"
            )
        return issues
    if any(not isinstance(row.get("settlement"), Mapping) for row in rows):
        issues.append("prior spend consumption is awaiting actual-cost settlement")
    used_calls = sum(int(row.get("calls") or 0) for row in rows)
    used_cost = sum(_effective_cost(row) for row in rows)
    request_cost = float((req.get("cost") or {}).get("amount") or 0)
    request_unit = str((req.get("cost") or {}).get("currency") or "")
    used_attempts = {str(row.get("attempt_id") or "") for row in rows}
    if str(req.get("attempt_id") or "") not in used_attempts and len(used_attempts) + 1 > max_attempts:
        issues.append("spend envelope max_attempts exceeded")
    if used_calls + int(req.get("calls") or 0) > max_calls:
        issues.append("spend envelope max_calls exceeded")
    if request_unit != cap_unit:
        issues.append("spend envelope cost currency mismatch")
    elif used_cost + request_cost > cap_amount + 1e-9:
        issues.append("spend envelope cost_ceiling exceeded")
    return issues


def verify(root: str | Path, auth: Mapping[str, Any], **values: Any) -> Dict[str, Any]:
    req = _request(**values)
    ledger = _load_ledger(root)
    entry = (ledger.get("envelopes") or {}).get(str(auth.get("envelope_id") or ""), {})
    rows = entry.get("consumptions") if isinstance(entry, Mapping) else []
    if not isinstance(rows, list):
        rows = []
    issues = _issues(root, auth, req, rows)
    if isinstance(entry, Mapping) and entry and entry.get("authorization_digest") != auth.get(
        "authorization_digest"
    ):
        issues.append("envelope_id reused with a different authorization digest")
    return {
        "status": "pass" if not issues else "blocked",
        "idempotent": any(row.get("consumption_id") == req["consumption_id"] for row in rows),
        "replay_blocked": any(row.get("consumption_id") == req["consumption_id"] for row in rows),
        "issues": issues,
        "usage": {
            "attempts": len({str(row.get("attempt_id") or "") for row in rows}),
            "calls": sum(int(row.get("calls") or 0) for row in rows),
            "cost": sum(_effective_cost(row) for row in rows),
        },
    }


def consume(root: str | Path, auth: Mapping[str, Any], **values: Any) -> Dict[str, Any]:
    req = _request(**values)
    root = Path(root).expanduser().resolve()
    with _lock(root):
        ledger = _load_ledger(root)
        envelope_id = str(auth.get("envelope_id") or "").strip()
        if not envelope_id:
            raise SpendEnvelopeError("spend envelope envelope_id missing")
        entry = ledger["envelopes"].setdefault(envelope_id, {
            "authorization_digest": str(auth.get("authorization_digest") or ""),
            "consumptions": [],
        })
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("consumptions"), list)
            or entry.get("authorization_digest") != auth.get("authorization_digest")
        ):
            raise SpendEnvelopeError("envelope_id reused or ledger entry invalid")
        rows = entry["consumptions"]
        issues = _issues(root, auth, req, rows)
        if issues:
            raise SpendEnvelopeError("; ".join(issues))
        # Existing ids and any unresolved prior reservation were rejected above.  Accounting
        # idempotency therefore means "never add a duplicate row", not "submit twice for free".
        existing = {**req, "state": "in_flight", "consumed_at": now_iso()}
        rows.append(existing)
        ledger["updated_at"] = existing["consumed_at"]
        ledger["ledger_digest"] = canonical_digest(
            {k: v for k, v in ledger.items() if k != "ledger_digest"}
        )
        _write(root / LEDGER_REL, ledger)
        return {
            "status": "pass", "idempotent": False, "replay_blocked": False,
            "envelope_id": envelope_id,
            "authorization_digest": str(auth.get("authorization_digest") or ""),
            "consumption": dict(existing),
            "usage": {
                "attempts": len({str(row.get("attempt_id") or "") for row in rows}),
                "calls": sum(int(row.get("calls") or 0) for row in rows),
                "cost": sum(_effective_cost(row) for row in rows),
            },
        }


def _settlement_auth_issues(
    root: str | Path,
    auth: Mapping[str, Any],
    row: Mapping[str, Any],
) -> list[str]:
    """Validate the original reservation identity without applying current-time expiry.

    Expiry prohibits *new* provider calls.  It must never prevent accounting for actual cost
    returned after an already-authorized submit, otherwise the ledger can remain permanently
    optimistic/pending.
    """
    issues: list[str] = []
    if auth.get("kind") != KIND or auth.get("version") != VERSION or auth.get("line") != LINE:
        issues.append("settlement spend envelope kind/version/line mismatch")
    if auth.get("project_id") != project_id(root):
        issues.append("settlement spend envelope project mismatch")
    if auth.get("authorization_digest") != authorization_digest(auth):
        issues.append("settlement spend envelope authorization_digest mismatch")
    if str(auth.get("decision") or "").lower() != "approved":
        issues.append("settlement spend envelope decision mismatch")
    if auth.get("attempt_id_semantics") != ATTEMPT_ID_SEMANTICS:
        issues.append("settlement attempt_id_semantics mismatch")
    issued, expiry = _aware(auth.get("issued_at")), _aware(auth.get("expires_at"))
    if issued is None or expiry is None or expiry <= issued:
        issues.append("settlement spend envelope timestamps invalid")
    for key in ("stage", "model", "channel", "input_sha256", "scope"):
        if auth.get(key) != row.get(key):
            issues.append(f"settlement spend envelope {key} mismatch")
    return issues


def settle(
    root: str | Path,
    auth: Mapping[str, Any],
    *,
    consumption_id: str,
    actual_cost: float,
    currency: str,
) -> Dict[str, Any]:
    """Atomically replace a reservation with provider-reported actual cost.

    An over-ceiling actual is still recorded (never silently under-count it), and the blocked
    result plus effective ledger total prevents every later consumption from proceeding.
    """
    actual, unit = _amount(actual_cost, currency, "actual_cost")
    root_path = Path(root).expanduser().resolve()
    cid = str(consumption_id or "").strip()
    if not cid:
        raise SpendEnvelopeError("consumption_id is required for settlement")
    with _lock(root_path):
        ledger = _load_ledger(root_path)
        envelope_id = str(auth.get("envelope_id") or "").strip()
        entry = ledger["envelopes"].get(envelope_id)
        if (
            not isinstance(entry, dict)
            or entry.get("authorization_digest") != auth.get("authorization_digest")
            or not isinstance(entry.get("consumptions"), list)
        ):
            raise SpendEnvelopeError("settlement envelope reservation missing or mismatched")
        rows = entry["consumptions"]
        row = next((item for item in rows if item.get("consumption_id") == cid), None)
        if not isinstance(row, dict):
            raise SpendEnvelopeError("settlement consumption reservation not found")
        # Do not call `_issues`: it intentionally blocks expired envelopes and repeated consume,
        # while settlement must remain possible after expiry for this existing reservation.
        issues = _settlement_auth_issues(root_path, auth, row)
        if issues:
            raise SpendEnvelopeError("; ".join(issues))
        reserved = row.get("cost") if isinstance(row.get("cost"), Mapping) else {}
        reserved_amount, reserved_unit = _amount(
            reserved.get("amount"), reserved.get("currency"), "reserved_cost"
        )
        if unit != reserved_unit:
            raise SpendEnvelopeError("actual cost currency does not match reservation")
        previous = row.get("settlement") if isinstance(row.get("settlement"), Mapping) else None
        settlement = {
            "actual_cost": {"amount": actual, "currency": unit},
            "reserved_cost": {"amount": reserved_amount, "currency": reserved_unit},
            "delta": actual - reserved_amount,
        }
        if previous is not None:
            previous_core = {key: previous.get(key) for key in settlement}
            if previous_core != settlement:
                raise SpendEnvelopeError("consumption already settled with a different actual cost")
            idempotent = True
        else:
            settlement["settled_at"] = now_iso()
            row["settlement"] = settlement
            row["state"] = "settled"
            idempotent = False
            ledger["updated_at"] = settlement["settled_at"]
            ledger["ledger_digest"] = canonical_digest(
                {k: v for k, v in ledger.items() if k != "ledger_digest"}
            )
            _write(root_path / LEDGER_REL, ledger)
        limits = auth.get("limits") if isinstance(auth.get("limits"), Mapping) else {}
        cap = limits.get("cost_ceiling") if isinstance(limits.get("cost_ceiling"), Mapping) else {}
        cap_amount, cap_unit = _amount(cap.get("amount"), cap.get("currency"), "cost_ceiling")
        total = sum(_effective_cost(item) for item in rows)
        over_ceiling = unit != cap_unit or total > cap_amount + 1e-9
        return {
            "status": "blocked" if over_ceiling else "pass",
            "idempotent": idempotent,
            "envelope_id": envelope_id,
            "authorization_digest": str(auth.get("authorization_digest") or ""),
            "consumption_id": cid,
            "settlement": dict(row.get("settlement") or settlement),
            "usage": {"cost": total, "currency": cap_unit, "ceiling": cap_amount},
            "issues": ["provider actual cost exceeds spend envelope cost_ceiling"] if over_ceiling else [],
        }


def _scope(text: str) -> Dict[str, Any]:
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise SpendEnvelopeError("--scope-json must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise SpendEnvelopeError("--scope-json must be an object")
    return payload


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    issue = sub.add_parser("issue")
    issue.add_argument("root")
    for flag in (
        "stage", "model", "channel", "input-sha256", "currency", "approver",
        "approval-reference", "source-quote",
    ):
        issue.add_argument("--" + flag, required=True)
    issue.add_argument("--scope-json", default="{}")
    issue.add_argument("--max-calls", type=int, required=True)
    issue.add_argument("--max-attempts", type=int, required=True)
    issue.add_argument("--cost-ceiling", type=float, required=True)
    issue.add_argument("--expires-at")
    issue.add_argument("--ttl-hours", type=float, default=24)
    issue.add_argument("--envelope-id")
    issue.add_argument("--out")
    for name in ("verify", "consume"):
        cmd = sub.add_parser(name)
        cmd.add_argument("root")
        cmd.add_argument("--envelope", required=True)
        for flag in ("stage", "model", "channel", "input-sha256", "currency", "consumption-id", "attempt-id"):
            cmd.add_argument("--" + flag, required=True)
        cmd.add_argument("--scope-json", default="{}")
        cmd.add_argument("--calls", type=int, required=True)
        cmd.add_argument("--cost", type=float, required=True)
    settle_cmd = sub.add_parser("settle")
    settle_cmd.add_argument("root")
    settle_cmd.add_argument("--envelope", required=True)
    settle_cmd.add_argument("--consumption-id", required=True)
    settle_cmd.add_argument("--actual-cost", type=float, required=True)
    settle_cmd.add_argument("--currency", required=True)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.cmd == "issue":
            auth = make_envelope(
                args.root, stage=args.stage, model=args.model, channel=args.channel,
                input_sha256=args.input_sha256, scope=_scope(args.scope_json),
                max_calls=args.max_calls, max_attempts=args.max_attempts,
                cost_ceiling=args.cost_ceiling, currency=args.currency, approver=args.approver,
                approval_reference=args.approval_reference,
                source_quote=args.source_quote,
                expires_at=args.expires_at, ttl_hours=args.ttl_hours, envelope_id=args.envelope_id,
            )
            path = write_envelope(args.out or default_envelope_path(args.root, args.stage), auth)
            result = {"status": "issued", "path": str(path), "envelope": auth}
        elif args.cmd in {"verify", "consume"}:
            auth = load_envelope(args.envelope)
            kwargs = {
                "stage": args.stage, "model": args.model, "channel": args.channel,
                "input_sha256": args.input_sha256, "scope": _scope(args.scope_json),
                "consumption_id": args.consumption_id, "attempt_id": args.attempt_id,
                "calls": args.calls, "cost": args.cost, "currency": args.currency,
            }
            result = verify(args.root, auth, **kwargs) if args.cmd == "verify" else consume(
                args.root, auth, **kwargs
            )
        else:
            auth = load_envelope(args.envelope)
            result = settle(
                args.root,
                auth,
                consumption_id=args.consumption_id,
                actual_cost=args.actual_cost,
                currency=args.currency,
            )
    except SpendEnvelopeError as exc:
        result = {"status": "blocked", "issues": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"pass", "issued"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
