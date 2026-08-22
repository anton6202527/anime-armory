from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import threading

import pytest

MODULE_PATH = Path(__file__).with_name("spend_envelope.py")
SPEC = importlib.util.spec_from_file_location("n2d_spend_envelope_tests", MODULE_PATH)
assert SPEC and SPEC.loader
envelope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(envelope)


INPUT_A = "sha256:" + "a" * 64


def _make(root: Path, **updates):
    args = {
        "stage": "image",
        "model": "GPT Image 2",
        "channel": "Codex CLI",
        "input_sha256": INPUT_A,
        "scope": {"episode": "第1集", "shots": ["Clip_01"]},
        "max_calls": 4,
        "max_attempts": 2,
        "cost_ceiling": 12,
        "currency": "CNY",
        "approver": "producer@example.invalid",
        "approval_reference": "approval-ui:phase-image-1",
        "source_quote": "我确认按此阶段预算和输入执行付费生成。",
        "envelope_id": "phase-image-1",
    }
    args.update(updates)
    return envelope.make_envelope(root, **args)


def _request(**updates):
    args = {
        "stage": "image",
        "model": "GPT Image 2",
        "channel": "Codex CLI",
        "input_sha256": INPUT_A,
        "scope": {"episode": "第1集", "shots": ["Clip_01"]},
        "consumption_id": "task-1:1",
        "attempt_id": "1",
        "calls": 2,
        "cost": 5,
        "currency": "CNY",
    }
    args.update(updates)
    return args


def _recovery_proof(label: str):
    return {
        "kind": "n2d_provider_recovery_evidence",
        "provider_submit_id": label,
        "provider_status": "success",
        "query_receipt_reference": f"provider-query:{label}",
        "query_response_sha256": "sha256:" + "c" * 64,
    }


def test_consume_is_persistent_atomic_and_replay_safe(tmp_path: Path) -> None:
    auth = _make(tmp_path)
    first = envelope.consume(tmp_path, auth, **_request())
    assert first["idempotent"] is False
    with pytest.raises(envelope.SpendEnvelopeError, match="provider replay blocked"):
        envelope.consume(tmp_path, auth, **_request())
    ledger = json.loads((tmp_path / envelope.LEDGER_REL).read_text(encoding="utf-8"))
    assert len(ledger["envelopes"]["phase-image-1"]["consumptions"]) == 1
    assert ledger["envelopes"]["phase-image-1"]["consumptions"][0]["state"] == "in_flight"


def test_finalize_is_idempotent_and_unlocks_a_different_bounded_call(tmp_path: Path) -> None:
    auth = _make(tmp_path)
    envelope.consume(tmp_path, auth, **_request(calls=1, cost=2))
    proof = _recovery_proof("receipt-1")
    first = envelope.finalize(tmp_path, auth, consumption_id="task-1:1", evidence=proof)
    again = envelope.finalize(tmp_path, auth, consumption_id="task-1:1", evidence=proof)
    assert first["idempotent"] is False and again["idempotent"] is True
    second = envelope.consume(
        tmp_path,
        auth,
        **_request(consumption_id="task-1:1:call-2", attempt_id="1", calls=1, cost=2),
    )
    assert second["usage"] == {"attempts": 1, "calls": 2, "cost": 4.0}


def test_crash_window_blocks_same_and_new_attempt_until_provider_recovery(tmp_path: Path) -> None:
    auth = _make(tmp_path)
    envelope.consume(tmp_path, auth, **_request(calls=1, cost=2))
    with pytest.raises(envelope.SpendEnvelopeError, match="provider replay blocked"):
        envelope.consume(tmp_path, auth, **_request(calls=1, cost=2))
    with pytest.raises(envelope.SpendEnvelopeError, match="recovery/finalization required"):
        envelope.consume(
            tmp_path,
            auth,
            **_request(consumption_id="task-1:2", attempt_id="2", calls=1, cost=2),
        )
    ledger = json.loads((tmp_path / envelope.LEDGER_REL).read_text(encoding="utf-8"))
    assert len(ledger["envelopes"]["phase-image-1"]["consumptions"]) == 1


def test_changed_binding_and_expiry_fail_closed(tmp_path: Path) -> None:
    auth = _make(tmp_path)
    changed = envelope.verify(tmp_path, auth, **_request(input_sha256="b" * 64))
    assert changed["status"] == "blocked"
    assert any("input_sha256 mismatch" in issue for issue in changed["issues"])
    expired = _make(
        tmp_path,
        envelope_id="expired",
        issued_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )
    result = envelope.verify(tmp_path, expired, **_request())
    assert result["status"] == "blocked"
    assert "spend envelope expired" in result["issues"]


def test_limits_apply_across_unique_attempts(tmp_path: Path) -> None:
    auth = _make(tmp_path, max_calls=3, max_attempts=2, cost_ceiling=7)
    envelope.consume(tmp_path, auth, **_request(calls=1, cost=3))
    envelope.finalize(tmp_path, auth, consumption_id="task-1:1", evidence=_recovery_proof("r1"))
    with pytest.raises(envelope.SpendEnvelopeError, match="max_calls exceeded"):
        envelope.consume(
            tmp_path,
            auth,
            **_request(consumption_id="task-1:2", attempt_id="2", calls=3, cost=3),
        )
    with pytest.raises(envelope.SpendEnvelopeError, match="cost_ceiling exceeded"):
        envelope.consume(
            tmp_path,
            auth,
            **_request(consumption_id="task-1:2", attempt_id="2", calls=1, cost=5),
        )


def test_max_attempts_counts_unique_attempt_ids_not_consumption_rows(tmp_path: Path) -> None:
    approved = _make(tmp_path, max_calls=3, max_attempts=1, cost_ceiling=3)
    envelope.consume(tmp_path, approved, **_request(calls=1, cost=1))
    envelope.finalize(tmp_path, approved, consumption_id="task-1:1", evidence=_recovery_proof("r1"))
    second = envelope.consume(
        tmp_path,
        approved,
        **_request(consumption_id="task-1:1:call-2", attempt_id="1", calls=1, cost=1),
    )
    assert second["usage"]["attempts"] == 1
    envelope.finalize(
        tmp_path,
        approved,
        consumption_id="task-1:1:call-2",
        evidence=_recovery_proof("r2"),
    )
    with pytest.raises(envelope.SpendEnvelopeError, match="max_attempts exceeded"):
        envelope.consume(
            tmp_path,
            approved,
            **_request(consumption_id="task-1:2", attempt_id="2", calls=1, cost=1),
        )


@pytest.mark.parametrize("approver", ["agent:producer", "delegate:owner", "auto:approval"])
def test_automated_or_delegated_approver_identity_is_rejected(tmp_path: Path, approver: str) -> None:
    with pytest.raises(envelope.SpendEnvelopeError, match="accountable human"):
        _make(tmp_path, approver=approver)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("approval_reference", "", "approval_reference"),
        ("source_quote", "", "source_quote"),
        ("approval_reference", "delegate:invented", "approval_reference"),
        ("source_quote", "agent:approved", "source_quote"),
    ],
)
def test_human_approval_evidence_is_required(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    with pytest.raises(envelope.SpendEnvelopeError, match=message):
        _make(tmp_path, **{field: value})


def test_source_quote_is_bound_into_authorization_digest(tmp_path: Path) -> None:
    approved = _make(tmp_path)
    approved["source_quote"] = "另一段未经授权的文字"
    result = envelope.verify(tmp_path, approved, **_request())
    assert result["status"] == "blocked"
    assert "spend envelope authorization_digest mismatch" in result["issues"]


def test_same_consumption_id_cannot_change_attempt_payload(tmp_path: Path) -> None:
    auth = _make(tmp_path)
    envelope.consume(tmp_path, auth, **_request())
    with pytest.raises(envelope.SpendEnvelopeError, match="different bindings"):
        envelope.consume(tmp_path, auth, **_request(cost=4))


def test_concurrent_consumers_cannot_oversubscribe(tmp_path: Path) -> None:
    auth = _make(tmp_path, max_calls=1, max_attempts=1, cost_ceiling=1)

    def run(index: int):
        return envelope.consume(
            tmp_path,
            auth,
            **_request(
                consumption_id=f"task-{index}:1", attempt_id="1", calls=1, cost=1,
            ),
        )

    outcomes = []
    barrier = threading.Barrier(2)

    def worker(index: int) -> None:
        try:
            barrier.wait()
            outcomes.append(run(index)["status"])
        except envelope.SpendEnvelopeError:
            outcomes.append("blocked")
    threads = [threading.Thread(target=worker, args=(index,)) for index in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["blocked", "pass"]


def test_corrupt_ledger_never_resets_usage(tmp_path: Path) -> None:
    auth = _make(tmp_path)
    envelope.consume(tmp_path, auth, **_request())
    path = tmp_path / envelope.LEDGER_REL
    data = json.loads(path.read_text(encoding="utf-8"))
    data["envelopes"] = {}
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(envelope.SpendEnvelopeError, match="digest mismatch"):
        envelope.verify(tmp_path, auth, **_request())
