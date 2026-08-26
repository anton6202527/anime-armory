#!/usr/bin/env python3
from image_backend_adapter import intersect_with_execution, resolve_capabilities


def test_dreamina_official_cli_exposes_verified_ten_image_budget() -> None:
    caps = resolve_capabilities("Dreamina 5.0", "Dreamina/即梦官方 CLI")
    assert caps.adapter_id == "dreamina_image2image"
    assert caps.reference_image_limit == 10
    assert caps.single_character_reference_limit == 5
    assert caps.multi_character_reference_limit == 4
    assert caps.non_character_reference_limit == 2
    assert caps.style_reference_limit == 1


def test_persistent_subject_requires_verified_runner_parameter_and_evidence() -> None:
    planned = resolve_capabilities("Seedream Subject", "custom subject API")
    assert planned.persistent_subject is False, "model name alone is not execution evidence"
    incomplete = intersect_with_execution(planned, {
        "adapter_id": "subject_runner", "status": "executable",
        "features": {"image_inputs": True, "persistent_subject": True, "subject_id_parameter": "--subject-id"},
        "feature_evidence": {},
    })
    assert incomplete.persistent_subject is False
    effective = intersect_with_execution(planned, {
        "adapter_id": "subject_runner", "status": "executable",
        "features": {"image_inputs": True, "persistent_subject": True, "subject_id_parameter": "--subject-id"},
        "feature_evidence": {"verified_at": "2026-08-26", "source": "subject-runner --help"},
    })
    assert effective.persistent_subject is True
    assert "--subject-id" in effective.persistent_subject_evidence
