from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

import pytest


LIB_DIR = Path(__file__).resolve().parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

import spend_envelope as spend  # noqa: E402


def jobs(*panels: str) -> dict:
    return {
        "model": "Model A",
        "channel": "Official CLI",
        "jobs": [
            {
                "panel_id": panel,
                "execution_input_sha256": (f"{index:x}" * 64)[:64],
                "source_contract_sha256": "a" * 64,
                "submit_prompt_sha256": "b" * 64,
            }
            for index, panel in enumerate(panels, start=1)
        ],
    }


def issued(
    root: Path,
    data: dict,
    *,
    panels: tuple[str, ...] = ("P001", "P002"),
    max_calls: int = 4,
    max_attempts: int = 2,
    max_total: str = "40",
    per_call: str = "10",
) -> tuple[Path, dict]:
    scope = spend.requested_scope("第1话", list(panels), force=False)
    envelope = spend.issue_envelope(
        root,
        chapter="第1话",
        data=data,
        model="Model A",
        channel="Official CLI",
        scope=scope,
        expires_at="2099-01-01T00:00:00Z",
        max_calls=max_calls,
        max_attempts=max_attempts,
        currency="CNY",
        max_total=max_total,
        max_cost_per_call=per_call,
        approver="Wesley Chen",
        approval_reference="chat://budget/42",
        source_quote="我批准本话在以上范围和总额内连续出图。",
    )
    path = spend.default_envelope_path(root, "第1话")
    spend.save_envelope(path, envelope)
    return path, envelope


def binding(root: Path, data: dict, panels: list[str] | None = None) -> dict:
    return {
        "stage": spend.STAGE,
        "input_sha256": spend.panel_jobs_input_sha256(data, "第1话"),
        "model": "Model A",
        "channel": "Official CLI",
        "scope": spend.requested_scope("第1话", panels or ["P001"], force=False),
    }


def reserve(path: Path, root: Path, data: dict, call: str, attempt: str = "round-1") -> dict:
    return spend.reserve_submission(
        path, root, consumption_id=call, attempt_id=attempt, **binding(root, data)
    )


def test_issue_requires_real_human_and_evidence(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    with pytest.raises(spend.SpendAuthorizationError, match="real human"):
        spend.issue_envelope(
            tmp_path,
            chapter="第1话",
            data=data,
            model="Model A",
            channel="Official CLI",
            scope=spend.requested_scope("第1话", ["P001"], force=False),
            expires_at="2099-01-01T00:00:00Z",
            max_calls=1,
            max_attempts=1,
            currency="CNY",
            max_total="10",
            max_cost_per_call="10",
            approver="comic runner agent",
            approval_reference="auto",
            source_quote="自动批准",
        )


def test_binding_is_exact_but_approved_panel_subset_can_continue(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    path, _ = issued(tmp_path, data)
    status = spend.inspect_authorization(path, tmp_path, **binding(tmp_path, data, ["P002"]))
    assert status["status"] == "authorized"

    changed = jobs("P001", "P002")
    changed["jobs"][0]["execution_input_sha256"] = "f" * 64
    with pytest.raises(spend.SpendAuthorizationError) as exc:
        spend.inspect_authorization(path, tmp_path, **binding(tmp_path, changed))
    assert exc.value.code == "binding_mismatch"

    expanded = binding(tmp_path, data, ["P001", "P003"])
    with pytest.raises(spend.SpendAuthorizationError) as exc:
        spend.inspect_authorization(path, tmp_path, **expanded)
    assert exc.value.code == "scope_expanded"


def test_same_retry_round_allows_multiple_calls_but_second_unique_round_blocks(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    path, _ = issued(tmp_path, data, max_attempts=1)
    reserve(path, tmp_path, data, "call-1", "phase-round-1")
    reserve(path, tmp_path, data, "call-2", "phase-round-1")
    spend.settle_submission(path, tmp_path, consumption_id="call-1", actual_cost="5")
    spend.settle_submission(path, tmp_path, consumption_id="call-2", actual_cost="5")
    same = spend.inspect_authorization(
        path, tmp_path, next_attempt_id="phase-round-1", **binding(tmp_path, data)
    )
    new = spend.inspect_authorization(
        path, tmp_path, next_attempt_id="phase-round-2", **binding(tmp_path, data)
    )
    assert same["status"] == "authorized"
    assert new["status"] == "exhausted"
    with pytest.raises(spend.SpendAuthorizationError) as exc:
        reserve(path, tmp_path, data, "call-3", "phase-round-2")
    assert exc.value.code == "max_attempts_exhausted"


def test_crash_window_same_consumption_id_never_resubmits(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    path, _ = issued(tmp_path, data)
    reserve(path, tmp_path, data, "ambiguous-call")
    with pytest.raises(spend.SpendAuthorizationError) as exc:
        reserve(path, tmp_path, data, "ambiguous-call")
    assert exc.value.code == "submission_state_unknown"
    with pytest.raises(spend.SpendAuthorizationError) as inspect_exc:
        spend.inspect_authorization(path, tmp_path, **binding(tmp_path, data))
    assert inspect_exc.value.code == "submission_state_unknown"
    ledger = json.loads(spend.ledger_path(tmp_path).read_text(encoding="utf-8"))
    entry = next(iter(ledger["envelopes"].values()))
    assert list(entry["reservations"]) == ["ambiguous-call"]


def test_unknown_cost_never_consumes_or_creates_ledger(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    path, envelope = issued(tmp_path, data)
    envelope["cost"].pop("max_cost_per_call")
    envelope["authorization_sha256"] = spend.sha256_json(spend._authorization_material(envelope))
    spend.save_envelope(path, envelope)
    with pytest.raises(spend.SpendAuthorizationError) as exc:
        reserve(path, tmp_path, data, "never-submitted")
    assert exc.value.code == "unknown_cost"
    assert not spend.ledger_path(tmp_path).exists()


def test_unknown_actual_persists_block_then_valid_settlement_unblocks(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    path, _ = issued(tmp_path, data)
    reserve(path, tmp_path, data, "call-1")
    with pytest.raises(spend.SpendAuthorizationError) as exc:
        spend.settle_submission(path, tmp_path, consumption_id="call-1", actual_cost=None)
    assert exc.value.code == "settlement_unknown"

    reopened = json.loads(spend.ledger_path(tmp_path).read_text(encoding="utf-8"))
    entry = next(iter(reopened["envelopes"].values()))
    assert entry["blocked"] is True
    assert entry["reservations"]["call-1"]["status"] == "settlement_unknown"
    with pytest.raises(spend.SpendAuthorizationError) as blocked:
        reserve(path, tmp_path, data, "call-2")
    assert blocked.value.code == "ledger_blocked"

    settled = spend.settle_submission(path, tmp_path, consumption_id="call-1", actual_cost="8")
    assert settled["status"] == "settled"
    assert reserve(path, tmp_path, data, "call-2")["status"] == "reserved"


def test_actual_over_cap_persists_and_new_process_remains_blocked(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    path, _ = issued(tmp_path, data)
    reserve(path, tmp_path, data, "call-1")
    with pytest.raises(spend.SpendAuthorizationError) as exc:
        spend.settle_submission(path, tmp_path, consumption_id="call-1", actual_cost="11")
    assert exc.value.code == "actual_cost_exceeded_authorization"
    reopened = json.loads(spend.ledger_path(tmp_path).read_text(encoding="utf-8"))
    entry = next(iter(reopened["envelopes"].values()))
    assert entry["blocked"] is True
    assert entry["reservations"]["call-1"]["status"] == "violation"

    script = """
import pathlib, sys
sys.path.insert(0, sys.argv[1])
import spend_envelope as s
root=pathlib.Path(sys.argv[2]); path=pathlib.Path(sys.argv[3]); data=__import__('json').loads(sys.argv[4])
try:
 s.reserve_submission(path,root,stage=s.STAGE,input_sha256=s.panel_jobs_input_sha256(data,'第1话'),model='Model A',channel='Official CLI',scope=s.requested_scope('第1话',['P001'],force=False),consumption_id='call-new-process',attempt_id='round-1')
except s.SpendAuthorizationError as e:
 print(e.code); raise SystemExit(0)
raise SystemExit(9)
"""
    proc = subprocess.run(
        [sys.executable, "-c", script, str(LIB_DIR), str(tmp_path), str(path), json.dumps(data)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "ledger_blocked"


def test_concurrent_reservations_never_exceed_call_or_cost_ceiling(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    path, _ = issued(tmp_path, data, max_calls=3, max_attempts=1, max_total="30")

    def one(index: int) -> str:
        try:
            reserve(path, tmp_path, data, f"call-{index}", "same-round")
            return "ok"
        except spend.SpendAuthorizationError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(one, range(12)))
    assert results.count("ok") == 3
    ledger = json.loads(spend.ledger_path(tmp_path).read_text(encoding="utf-8"))
    entry = next(iter(ledger["envelopes"].values()))
    assert len(entry["reservations"]) == 3


def test_settlement_is_idempotent_and_releases_unused_reservation(tmp_path: Path) -> None:
    data = jobs("P001", "P002")
    path, _ = issued(tmp_path, data)
    reserve(path, tmp_path, data, "call-1")
    first = spend.settle_submission(path, tmp_path, consumption_id="call-1", actual_cost="6")
    second = spend.settle_submission(path, tmp_path, consumption_id="call-1", actual_cost="6")
    assert first["released_cost"] == "4"
    assert second["idempotent"] is True
