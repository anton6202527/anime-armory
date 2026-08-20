from __future__ import annotations

import json

import pytest

import paid_execution_contract as contract


def _install(monkeypatch, tmp_path, *, input_fp: str = "input-a", submit: str = "submit-a") -> dict:
    payload = contract.build_expectation(
        stage="image",
        task_id="task-1",
        episode="第1集",
        attempt=1,
        authorization_digest="sha256:" + "a" * 64,
        records=[{
            "shot": "Clip_01",
            "target": "出图/第1集/图片/Clip01_first.png",
            "input_fingerprint": input_fp,
            "submit_request_sha256": submit,
        }],
    )
    for key, value in contract.environment_for_expectation(payload).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("N2D_TASK_ID", "task-1")
    monkeypatch.setenv("N2D_ROOT", str(tmp_path))
    return payload


def test_manual_invocation_has_no_batch_expectation(monkeypatch) -> None:
    monkeypatch.delenv(contract.EXPECTATION_ENV, raising=False)
    for name in ("N2D_TASK_ID", "N2D_IDEMPOTENCY_KEY", "N2D_STAGE"):
        monkeypatch.delenv(name, raising=False)
    assert contract.enforce_expected_paid_request(
        stage="image", identity="Clip_01", target="x", input_fingerprint="a",
        submit_request_sha256="b",
    )["enforced"] is False


def test_batch_marker_without_expectation_fails_before_spend(monkeypatch) -> None:
    monkeypatch.delenv(contract.EXPECTATION_ENV, raising=False)
    monkeypatch.setenv("N2D_TASK_ID", "batch-task-1")
    with pytest.raises(contract.PaidExecutionContractError, match="expectation is missing"):
        contract.enforce_expected_paid_request(
            stage="image", identity="Clip_01", target="x", input_fingerprint="a",
            submit_request_sha256="b",
        )


def test_exact_authorized_request_passes(monkeypatch, tmp_path) -> None:
    payload = _install(monkeypatch, tmp_path)
    result = contract.enforce_expected_paid_request(
        stage="image",
        identity="Clip_01",
        target="出图/第1集/图片/Clip01_first.png",
        input_fingerprint="input-a",
        submit_request_sha256="submit-a",
    )
    assert result["enforced"] is True
    assert result["expectation_digest"] == payload["digest"]
    receipts = contract.verify_expected_receipts(tmp_path, payload)
    assert receipts["status"] == "pass"
    assert len(receipts["records"]) == 1


@pytest.mark.parametrize("field", ["input", "submit", "digest"])
def test_changed_or_tampered_request_fails_closed(monkeypatch, tmp_path, field: str) -> None:
    _install(monkeypatch, tmp_path)
    kwargs = {"input_fingerprint": "input-a", "submit_request_sha256": "submit-a"}
    if field == "input":
        kwargs["input_fingerprint"] = "input-b"
    elif field == "submit":
        kwargs["submit_request_sha256"] = "submit-b"
    else:
        monkeypatch.setenv(contract.EXPECTATION_DIGEST_ENV, "sha256:" + "b" * 64)
    with pytest.raises(contract.PaidExecutionContractError):
        contract.enforce_expected_paid_request(
            stage="image",
            identity="Clip_01",
            target="出图/第1集/图片/Clip01_first.png",
            **kwargs,
        )


def test_missing_or_tampered_boundary_receipt_fails_completion(monkeypatch, tmp_path) -> None:
    payload = _install(monkeypatch, tmp_path)
    assert contract.verify_expected_receipts(tmp_path, payload)["status"] == "fail"
    result = contract.enforce_expected_paid_request(
        stage="image",
        identity="Clip_01",
        target="出图/第1集/图片/Clip01_first.png",
        input_fingerprint="input-a",
        submit_request_sha256="submit-a",
    )
    path = tmp_path / result["boundary_receipt"]["path"]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["record"]["input_fingerprint"] = "tampered"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert contract.verify_expected_receipts(tmp_path, payload)["status"] == "fail"
