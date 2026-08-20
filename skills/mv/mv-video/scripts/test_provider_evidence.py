#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import base64

import provider_evidence
import pytest


OUTPUT_SHA = hashlib.sha256(b"selected video bytes").hexdigest()
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.fixture(autouse=True)
def _code_owned_test_adapter(monkeypatch):
    """Exercise the adapter machinery without pretending this is a provider format."""
    monkeypatch.setitem(provider_evidence.TRUSTED_API_ADAPTERS, "fixture.operation.v1", {
        "provider_ids": {"google.gemini_api"},
        "models": {"Veo 3.1", "Gemini Omni Flash Preview"},
        "job_id_pointer": "/name",
        "submitted_at_pointer": "/metadata/createTime",
        "submitted_at_format": "iso8601",
        "model_pointer": "/metadata/model",
        "model_values": {
            "Veo 3.1": "Veo 3.1",
            "Gemini Omni Flash Preview": "Gemini Omni Flash Preview",
        },
        "status_pointer": "/done",
        "status_kind": "done_boolean",
    })


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _api_receipt(tmp_path, *, document=None, evidence_overrides=None, receipt_overrides=None):
    submitted_at = "2026-08-20T12:00:00+08:00"
    document = document or {
        "name": "operations/provider-job-42",
        "metadata": {"createTime": submitted_at, "model": "Veo 3.1"},
        "done": True,
    }
    path = _write(tmp_path / "出视频/provider_evidence/api.json", document)
    evidence = {
        "schema_version": 2,
        "kind": "provider_api_response_json",
        "execution_transport": "api",
        "adapter_id": "fixture.operation.v1",
        "route_sha256": "",
        "path": path.relative_to(tmp_path).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "selected_asset": {
            "sha256": OUTPUT_SHA,
            "bound_by": "download operator",
            "notes": "downloaded this completed operation output without transcoding",
        },
    }
    evidence.update(evidence_overrides or {})
    receipt = {
        "provider_job_id": "operations/provider-job-42",
        "submitted_at": submitted_at,
        "model": "Veo 3.1",
        "provider_status": "succeeded",
        "compiled_request_controls_sha256": "a" * 64,
        "submitted_refs": [],
        "provider_evidence": evidence,
    }
    receipt.update(receipt_overrides or {})
    route = {
        "channel_kind": "api",
        "provider_id": "google.gemini_api",
        "model": "Veo 3.1",
    }
    return route, receipt, path


def _ui_receipt(tmp_path):
    path = tmp_path / "出视频/provider_evidence/ui.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG_BYTES)
    evidence = {
        "schema_version": 2,
        "kind": "provider_ui_capture",
        "execution_transport": "web",
        "adapter_id": "named_ui_observation.v1",
        "route_sha256": "",
        "path": path.relative_to(tmp_path).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "ui_observation": {
            "reviewer": "web operator",
            "notes": "read the completed task row and output preview in the provider UI",
            "observed_at": "2026-08-20T12:00:00+08:00",
            "submitted_at": "2026-08-20T12:00:00+08:00",
            "provider_id": "bytedance.dreamina",
            "provider_job_id": "web-job-42",
            "model": "Seedance 2.0",
            "status": "completed",
            "capture_method": "browser_screenshot",
            "source_url": "https://dreamina.capcut.com/ai-tool/video/generate",
        },
        "selected_asset": {
            "sha256": OUTPUT_SHA,
            "bound_by": "web operator",
            "notes": "downloaded the preview represented by this completed task row",
        },
    }
    receipt = {
        "provider_job_id": "web-job-42",
        "submitted_at": "2026-08-20T12:00:00+08:00",
        "model": "Seedance 2.0",
        "provider_status": "succeeded",
        "provider_evidence": evidence,
    }
    route = {"channel_kind": "web", "provider_id": "bytedance.dreamina"}
    return route, receipt, path


def test_api_adapter_extracts_job_time_model_status_and_selected_asset(tmp_path):
    route, receipt, _path = _api_receipt(tmp_path)
    normalized, errors = provider_evidence.validate_provider_evidence(
        str(tmp_path), route, receipt, OUTPUT_SHA
    )
    assert errors == []
    assert normalized["verified_fields"] == {
        "adapter_id": "fixture.operation.v1",
        "evidence_class": "machine_response_plus_named_output_binding",
        "provider_id": "google.gemini_api",
        "provider_job_id": "operations/provider-job-42",
        "submitted_at_utc": "2026-08-20T04:00:00.000Z",
        "model": "Veo 3.1",
        "status": "succeeded",
        "selected_asset_sha256": OUTPUT_SHA,
    }


def test_arbitrary_json_and_caller_selected_pointer_cannot_mint_evidence(tmp_path):
    route, receipt, path = _api_receipt(
        tmp_path,
        document={"claim": {"job": "operations/provider-job-42", "at": "2026-08-20T12:00:00+08:00"}},
        evidence_overrides={
            "bindings": {
                "provider_job_id": {"json_pointer": "/claim/job"},
                "submitted_at": {"json_pointer": "/claim/at"},
            },
        },
    )
    receipt["provider_evidence"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_freeform_bindings_forbidden" in errors


def test_duplicate_json_keys_are_rejected_before_adapter_extraction(tmp_path):
    route, receipt, path = _api_receipt(tmp_path)
    path.write_text(
        '{"name":"operations/provider-job-42","name":"forged",'
        '"metadata":{"createTime":"2026-08-20T12:00:00+08:00","model":"Veo 3.1"},"done":true}',
        encoding="utf-8",
    )
    receipt["provider_evidence"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_json_duplicate_key" in errors


def test_nonstandard_json_constants_are_rejected(tmp_path):
    route, receipt, path = _api_receipt(tmp_path)
    path.write_text(
        '{"name":"operations/provider-job-42","metadata":'
        '{"createTime":"2026-08-20T12:00:00+08:00","model":"Veo 3.1"},'
        '"done":true,"score":NaN}', encoding="utf-8",
    )
    receipt["provider_evidence"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_json_nonstandard_constant" in errors


def test_adapter_is_bound_to_provider_and_model(tmp_path):
    route, receipt, _path = _api_receipt(tmp_path)
    route["provider_id"] = "attacker.example"
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_trusted_adapter_unavailable" in errors


def test_current_api_route_fails_closed_without_a_shipped_adapter(tmp_path, monkeypatch):
    route, receipt, _path = _api_receipt(tmp_path)
    monkeypatch.delitem(
        provider_evidence.TRUSTED_API_ADAPTERS, "fixture.operation.v1", raising=False
    )
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_trusted_adapter_unavailable" in errors

    route, receipt, _path = _api_receipt(
        tmp_path, receipt_overrides={"model": "Veo 9.9"}
    )
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_trusted_adapter_unavailable" in errors


def test_model_status_and_output_hash_drift_fail_closed(tmp_path):
    route, receipt, _path = _api_receipt(tmp_path, receipt_overrides={"model": "Gemini Omni Flash Preview"})
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_model_mismatch" in errors

    route, receipt, _path = _api_receipt(tmp_path, receipt_overrides={"provider_status": "running"})
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_status_mismatch" in errors

    route, receipt, _path = _api_receipt(tmp_path)
    _normalized, errors = provider_evidence.validate_provider_evidence(
        str(tmp_path), route, receipt, "f" * 64
    )
    assert "provider_evidence_selected_asset_sha256_mismatch" in errors


def test_provider_response_request_material_cannot_remain_unbound(tmp_path):
    route, receipt, _path = _api_receipt(tmp_path, document={
        "name": "operations/provider-job-42",
        "metadata": {
            "createTime": "2026-08-20T12:00:00+08:00", "model": "Veo 3.1",
        },
        "done": True,
        "request": {"prompt": "different controls"},
    })
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_response_contains_unbound_request_material" in errors


def test_ui_is_named_human_observation_over_real_capture_not_json_claim(tmp_path):
    route, receipt, _path = _ui_receipt(tmp_path)
    normalized, errors = provider_evidence.validate_provider_evidence(
        str(tmp_path), route, receipt, OUTPUT_SHA
    )
    assert errors == []
    assert normalized["verified_fields"]["evidence_class"] == "named_human_observation"

    receipt["provider_evidence"]["ui_observation"]["reviewer"] = ""
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_ui_reviewer_missing" in errors


def test_schema_v2_rejects_unknown_fields_and_impossible_observation_order(tmp_path):
    route, receipt, _path = _ui_receipt(tmp_path)
    receipt["provider_evidence"]["self_asserted_machine_verified"] = True
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_unknown_field" in errors

    route, receipt, _path = _ui_receipt(tmp_path)
    receipt["provider_evidence"]["ui_observation"]["observed_at"] = (
        "2026-08-20T11:59:59+08:00"
    )
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_ui_observed_before_submission" in errors


def test_ui_json_export_and_untrusted_origin_are_rejected(tmp_path):
    route, receipt, path = _ui_receipt(tmp_path)
    json_path = path.with_suffix(".json")
    json_path.write_text('{"job":"self asserted"}', encoding="utf-8")
    receipt["provider_evidence"].update({
        "path": json_path.relative_to(tmp_path).as_posix(),
        "sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
    })
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_capture_type_invalid" in errors

    route, receipt, _path = _ui_receipt(tmp_path)
    receipt["provider_evidence"]["ui_observation"]["source_url"] = "https://evil.example/task"
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_ui_origin_untrusted" in errors


def test_local_runner_receipt_binds_controls_refs_and_output(tmp_path):
    submitted_refs = [{"role": "start_frame", "path": "出图/a.png", "sha256": "b" * 64,
                       "confirmed_submitted": True}]
    controls_sha = "a" * 64
    document = {
        "kind": "mv_video_local_runner_receipt",
        "schema_version": 1,
        "provider_id": "local.open_source",
        "runner": {
            "name": "local-video-cli", "version": "1.2.3", "operator": "local operator",
            "command_sha256": "c" * 64,
        },
        "execution": {
            "job_id": "local-job-1", "submitted_at": "2026-08-20T12:00:00+08:00",
            "model": "Wan 2.2", "status": "completed", "exit_code": 0,
            "request_controls_sha256": controls_sha,
            "submitted_refs_sha256": provider_evidence._stable_hash(submitted_refs),
            "output_asset_sha256": OUTPUT_SHA,
        },
    }
    path = _write(tmp_path / "出视频/provider_evidence/local.json", document)
    receipt = {
        "provider_job_id": "local-job-1", "submitted_at": "2026-08-20T12:00:00+08:00",
        "model": "Wan 2.2", "provider_status": "succeeded",
        "compiled_request_controls_sha256": controls_sha, "submitted_refs": submitted_refs,
        "provider_evidence": {
            "schema_version": 2, "kind": "local_runner_receipt_json",
            "execution_transport": "local", "adapter_id": "mv_video.local_runner_receipt.v1",
            "route_sha256": "", "path": path.relative_to(tmp_path).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "selected_asset": {"sha256": OUTPUT_SHA},
        },
    }
    route = {"channel_kind": "local", "provider_id": "local.open_source"}
    normalized, errors = provider_evidence.validate_provider_evidence(
        str(tmp_path), route, receipt, OUTPUT_SHA
    )
    assert errors == []
    assert normalized["verified_fields"]["evidence_class"] == "structured_local_runner_receipt"

    receipt["submitted_refs"].append({"role": "end_frame"})
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_submitted_refs_mismatch" in errors


def test_api_or_web_route_requires_explicit_transport(tmp_path):
    route, receipt, _path = _ui_receipt(tmp_path)
    route["channel_kind"] = "api_or_web"
    receipt["provider_evidence"]["execution_transport"] = ""
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_execution_transport_missing" in errors

    route, receipt, _path = _ui_receipt(tmp_path)
    receipt["provider_evidence"]["execution_transport"] = "api"
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_execution_transport_mismatch" in errors


def test_evidence_cannot_point_to_receipt_tree(tmp_path):
    route, receipt, source = _api_receipt(tmp_path)
    target = tmp_path / "出视频/receipts/self.submit.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    receipt["provider_evidence"].update({
        "path": target.relative_to(tmp_path).as_posix(),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    })
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_path_not_in_evidence_tree" in errors


def test_evidence_must_live_in_catalogued_provider_evidence_tree(tmp_path):
    route, receipt, source = _api_receipt(tmp_path)
    target = tmp_path / "misc/provider.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    receipt["provider_evidence"].update({
        "path": target.relative_to(tmp_path).as_posix(),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    })
    _normalized, errors = provider_evidence.validate_provider_evidence(str(tmp_path), route, receipt)
    assert "provider_evidence_path_not_in_evidence_tree" in errors


def test_manual_route_keeps_named_attestation_path_outside_provider_evidence():
    assert provider_evidence.route_requires_evidence({"channel_kind": "manual"}) is False
