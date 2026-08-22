from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import threading

import pytest

MODULE_PATH = Path(__file__).with_name("spend_envelope.py")
SPEC = importlib.util.spec_from_file_location("ad_spend_envelope_tests", MODULE_PATH)
assert SPEC and SPEC.loader
envelope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(envelope)


INPUT = "sha256:" + "1" * 64


def auth(root: Path, **updates):
    values = {
        "stage": "video", "model": "Seedance 2.0 Fast",
        "channel": "Dreamina/即梦官方 CLI/API", "input_sha256": INPUT,
        "scope": {"jobs": ["shot-01", "shot-02"]}, "max_calls": 2,
        "max_attempts": 2, "cost_ceiling": 8, "currency": "credit",
        "approver": "client-producer@example.invalid", "envelope_id": "ad-video-phase",
        "approval_reference": "approval-ui:ad-video-phase",
        "source_quote": "我确认按该阶段预算包执行广告素材生成。",
    }
    values.update(updates)
    return envelope.make_envelope(root, **values)


def request(**updates):
    values = {
        "stage": "video", "model": "Seedance 2.0 Fast",
        "channel": "Dreamina/即梦官方 CLI/API", "input_sha256": INPUT,
        "scope": {"jobs": ["shot-01", "shot-02"]},
        "consumption_id": "shot-01:1", "attempt_id": "1",
        "calls": 1, "cost": 3, "currency": "credit",
    }
    values.update(updates)
    return values


def test_phase_usage_is_persistent_and_duplicate_submit_is_blocked(tmp_path: Path) -> None:
    approved = auth(tmp_path)
    assert envelope.consume(tmp_path, approved, **request())["idempotent"] is False
    with pytest.raises(envelope.SpendEnvelopeError, match="provider replay blocked"):
        envelope.consume(tmp_path, approved, **request())
    settled = envelope.settle(
        tmp_path, approved, consumption_id="shot-01:1", actual_cost=2, currency="credit"
    )
    assert settled["status"] == "pass"
    assert settled["usage"]["cost"] == 2.0
    assert envelope.settle(
        tmp_path, approved, consumption_id="shot-01:1", actual_cost=2, currency="credit"
    )["idempotent"] is True


def test_crash_window_never_turns_same_consumption_into_free_provider_replay(
    tmp_path: Path,
) -> None:
    approved = auth(tmp_path)
    envelope.consume(tmp_path, approved, **request())
    with pytest.raises(envelope.SpendEnvelopeError, match="provider replay blocked"):
        envelope.consume(tmp_path, approved, **request())
    with pytest.raises(envelope.SpendEnvelopeError, match="awaiting actual-cost settlement"):
        envelope.consume(
            tmp_path,
            approved,
            **request(consumption_id="shot-02:1", cost=2),
        )
    ledger = json.loads((tmp_path / envelope.LEDGER_REL).read_text(encoding="utf-8"))
    assert len(ledger["envelopes"]["ad-video-phase"]["consumptions"]) == 1


def test_expired_after_submit_still_settles_but_cannot_consume_again(
    tmp_path: Path, monkeypatch
) -> None:
    issued = datetime.now(timezone.utc) - timedelta(minutes=10)
    approved = auth(
        tmp_path,
        issued_at=issued.isoformat(),
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
    )
    envelope.consume(tmp_path, approved, **request())

    class FutureDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime.now(timezone.utc) + timedelta(hours=2)
            return value if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr(envelope, "datetime", FutureDateTime)

    settled = envelope.settle(
        tmp_path, approved, consumption_id="shot-01:1", actual_cost=2, currency="credit"
    )
    assert settled["status"] == "pass"
    with pytest.raises(envelope.SpendEnvelopeError, match="spend envelope expired"):
        envelope.consume(
            tmp_path,
            approved,
            **request(consumption_id="shot-02:1", attempt_id="2", cost=1),
        )


def test_hash_model_channel_and_expiry_are_exact(tmp_path: Path) -> None:
    approved = auth(tmp_path)
    for field, value in (("input_sha256", "2" * 64), ("model", "Veo 3.1"), ("channel", "Other API")):
        result = envelope.verify(tmp_path, approved, **request(**{field: value}))
        assert result["status"] == "blocked"
        assert any(field in issue for issue in result["issues"])
    expired = auth(
        tmp_path, envelope_id="expired",
        issued_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )
    assert "spend envelope expired" in envelope.verify(tmp_path, expired, **request())["issues"]


def test_attempt_call_and_cost_limits_fail_closed(tmp_path: Path) -> None:
    approved = auth(tmp_path, max_calls=2, max_attempts=2, cost_ceiling=5)
    envelope.consume(tmp_path, approved, **request(cost=3))
    envelope.settle(
        tmp_path, approved, consumption_id="shot-01:1", actual_cost=3, currency="credit"
    )
    with pytest.raises(envelope.SpendEnvelopeError, match="cost_ceiling exceeded"):
        envelope.consume(
            tmp_path, approved,
            **request(consumption_id="shot-02:1", attempt_id="2", cost=3),
        )


def test_attempt_limit_counts_unique_attempt_id(tmp_path: Path) -> None:
    approved = auth(tmp_path, max_calls=3, max_attempts=1, cost_ceiling=3)
    envelope.consume(tmp_path, approved, **request(calls=1, cost=1))
    envelope.settle(
        tmp_path, approved, consumption_id="shot-01:1", actual_cost=1, currency="credit"
    )
    second = envelope.consume(
        tmp_path, approved,
        **request(consumption_id="shot-02:1", attempt_id="1", calls=1, cost=1),
    )
    assert second["usage"]["attempts"] == 1
    envelope.settle(
        tmp_path, approved, consumption_id="shot-02:1", actual_cost=1, currency="credit"
    )
    with pytest.raises(envelope.SpendEnvelopeError, match="max_attempts exceeded"):
        envelope.consume(
            tmp_path, approved,
            **request(consumption_id="shot-01:2", attempt_id="2", calls=1, cost=1),
        )


@pytest.mark.parametrize("approver", ["agent:producer", "delegate:client", "auto:approval"])
def test_nonhuman_approver_prefix_is_rejected(tmp_path: Path, approver: str) -> None:
    with pytest.raises(envelope.SpendEnvelopeError, match="accountable human"):
        auth(tmp_path, approver=approver)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("approval_reference", "", "approval_reference"),
        ("source_quote", "", "source_quote"),
        ("approval_reference", "agent:invented", "approval_reference"),
        ("source_quote", "auto:approved", "source_quote"),
    ],
)
def test_human_approval_evidence_is_mandatory(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    with pytest.raises(envelope.SpendEnvelopeError, match=message):
        auth(tmp_path, **{field: value})


def test_approval_quote_tampering_breaks_authorization_digest(tmp_path: Path) -> None:
    approved = auth(tmp_path)
    approved["source_quote"] = "伪造的新决定"
    result = envelope.verify(tmp_path, approved, **request())
    assert result["status"] == "blocked"
    assert "spend envelope authorization_digest mismatch" in result["issues"]


def test_actual_cost_delta_is_recorded_and_over_ceiling_blocks_future(tmp_path: Path) -> None:
    approved = auth(tmp_path, max_calls=2, max_attempts=1, cost_ceiling=3)
    envelope.consume(tmp_path, approved, **request(cost=2))
    settled = envelope.settle(
        tmp_path, approved, consumption_id="shot-01:1", actual_cost=4, currency="credit"
    )
    assert settled["status"] == "blocked"
    assert settled["settlement"]["delta"] == 2.0
    assert settled["usage"]["cost"] == 4.0
    with pytest.raises(envelope.SpendEnvelopeError, match="cost_ceiling exceeded"):
        envelope.consume(
            tmp_path,
            approved,
            **request(consumption_id="shot-02:1", attempt_id="1", cost=0),
        )


def test_concurrent_consumption_cannot_exceed_one_call(tmp_path: Path) -> None:
    approved = auth(tmp_path, max_calls=1, max_attempts=1, cost_ceiling=1)

    def one(index: int):
        return envelope.consume(
            tmp_path, approved,
            **request(consumption_id=f"shot-{index}:1", calls=1, cost=1),
        )

    states = []
    barrier = threading.Barrier(2)

    def worker(index: int) -> None:
        try:
            barrier.wait()
            states.append(one(index)["status"])
        except envelope.SpendEnvelopeError:
            states.append("blocked")
    threads = [threading.Thread(target=worker, args=(index,)) for index in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(states) == ["blocked", "pass"]


def test_tampered_ledger_is_not_treated_as_empty(tmp_path: Path) -> None:
    approved = auth(tmp_path)
    envelope.consume(tmp_path, approved, **request())
    path = tmp_path / envelope.LEDGER_REL
    data = json.loads(path.read_text(encoding="utf-8"))
    data["envelopes"] = {}
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(envelope.SpendEnvelopeError, match="digest mismatch"):
        envelope.verify(tmp_path, approved, **request())
