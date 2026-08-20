#!/usr/bin/env python3
from datetime import date
import pytest

import video_jobs


cap = video_jobs.video_capabilities


def inputs(*roles):
    return [
        {"role": role, "path": f"{role}.png", "sha256": str(index + 1) * 64, "use": role}
        for index, role in enumerate(roles)
    ]


def planned(*roles, duration=4, fps=24, resolution="720p"):
    return {
        "duration_seconds": duration, "fps": fps, "resolution": resolution,
        "mode": "frames2video" if "end_frame" in roles else "image2video",
        "quality_tier": "high", "input_roles": inputs(*roles), "end_frame_intent": "submit",
    }


def omni_account_adapter(capability=None):
    """Account-scoped observed values; intentionally not promoted to the graph."""
    if capability is None:
        capability = {
            "input_roles": {
                "start_frame": {"max_count": 1, "required_for_image2video": True},
                "end_frame": {"max_count": 0},
                "reference_image": {"max_count": 0},
                "reference_video": {"max_count": 0},
                "reference_audio": {"max_count": 0},
                "keyframe": {"max_count": 0},
            },
            "allowed_input_combinations": [["start_frame"]],
            "duration_seconds": {"allowed": [2.0, 4.0]},
            "fps": [24],
            "resolutions": ["720p"],
            "native_audio": {
                "produces": True,
                "disableable": None,
                "disableability_status": "account_observed_not_confirmed",
            },
            "multi_shot": False,
            "legacy_compatibility": False,
            "provenance": {"source": "named account smoke test", "source_date_or_collected": "2026-08-20"},
        }
    return {
        "schema_version": 1,
        "kind": cap.ADAPTER_KIND,
        "model": "Gemini Omni Flash Preview",
        "channel": "Google Gemini API",
        "provider_id": "google.gemini_api",
        "access_status": "available",
        "adapter_kind": "api",
        "reviewer": "integration owner",
        "notes": "verified exact controls against this account and SDK revision",
        "capability": capability,
    }


def test_known_model_and_known_channel_do_not_imply_executable_pair():
    with pytest.raises(ValueError, match="non_executable_model_channel_pair"):
        cap.resolve_route("Veo 3.1", "Runway API")


def test_builtin_capability_graph_expires_and_requires_reverification(monkeypatch):
    assert cap.capability_graph_freshness_errors(date(2026, 8, 20)) == []
    assert cap.capability_graph_freshness_errors(date(2026, 11, 19))
    monkeypatch.setattr(cap, "capability_graph_freshness_errors", lambda today=None: ["capability_graph_stale"])
    with pytest.raises(ValueError, match="capability_graph_reverification_required"):
        cap.resolve_route("Veo 3.1", "Google Gemini API")


def test_omni_preview_is_candidate_only_and_google_route_requires_adapter():
    candidate = cap.MODEL_CANDIDATES["Gemini Omni Flash Preview"]
    assert candidate["provider_model_id"] == "gemini-omni-flash-preview"
    assert candidate["release_stage"] == "preview"
    assert candidate["route_status"] == "adapter_required"
    assert "Gemini Omni Flash Preview" not in cap.MODEL_CAPABILITIES
    assert cap.CHANNELS["Google Gemini API"]["models"]["Gemini Omni Flash Preview"] == "adapter_required"
    assert cap.CHANNELS["Google Gemini API"]["model_release_stages"]["Gemini Omni Flash Preview"] == "preview"
    assert {"duration_seconds", "fps", "resolutions"}.issubset(candidate["adapter_must_supply"])
    with pytest.raises(ValueError, match="missing_explicit_adapter_record"):
        cap.resolve_route("Gemini Omni Flash Preview", "Google Gemini API")


def test_omni_preview_requires_complete_capability_adapter_then_compiles():
    incomplete = omni_account_adapter({})
    with pytest.raises(ValueError, match="adapter_capability_"):
        cap.resolve_route("Gemini Omni Flash Preview", "Google Gemini API", incomplete)
    adapter = omni_account_adapter()
    route = cap.resolve_route("Gemini Omni Flash Preview", "Google Gemini API", adapter)
    assert route["release_stage"] == "preview"
    assert route["declared_route_status"] == "adapter_required"
    assert route["adapter_required"] is True
    assert route["adapter_record_sha256"] == cap.stable_hash(adapter)
    controls = cap.compile_request_controls(route, planned("start_frame", duration=4))
    assert controls["duration_seconds"] == 4
    assert controls["resolution"] == "720p"


def test_manual_route_requires_named_explicit_adapter():
    with pytest.raises(ValueError, match="missing_explicit_adapter_record"):
        cap.resolve_route("manual", "manual")
    adapter = {
        "schema_version": 1, "kind": cap.ADAPTER_KIND,
        "model": "manual", "channel": "manual", "provider_id": "studio.vendor",
        "access_status": "available", "adapter_kind": "manual",
        "reviewer": "producer", "notes": "verified vendor workflow",
        "capability": cap.MODEL_CAPABILITIES["Seedance 2.0"],
    }
    route = cap.resolve_route("manual", "manual", adapter)
    assert route["provider_id"] == "studio.vendor"
    assert route["adapter_record_sha256"] == cap.stable_hash(adapter)


def test_veo_always_on_audio_is_not_given_a_false_provider_control():
    route = cap.resolve_route("Veo 3.1", "Google Gemini API")
    controls = cap.compile_request_controls(
        route, planned("start_frame", "end_frame", duration=8, fps=30)
    )
    assert controls["fps"] == 24
    assert controls["audio"]["provider_can_disable"] is False
    assert controls["audio"]["provider_parameter_generate_audio"] is None
    assert controls["audio"]["discard_provider_audio_after_download"] is True


def test_veo_end_frame_compiles_eight_seconds_and_records_picture_lock_trim():
    route = cap.resolve_route("Veo 3.1", "Google Gemini API")
    controls = cap.compile_request_controls(route, planned("start_frame", "end_frame", duration=4))
    assert controls["duration_seconds"] == 8
    assert any(row["kind"] == "provider_duration_then_trim_to_picture_lock" for row in controls["adaptations"])


def test_unsupported_end_frame_is_not_compiled_as_submitted_evidence():
    route = cap.resolve_route("Runway Gen-4.5", "Runway API")
    controls = cap.compile_request_controls(
        route, planned("start_frame", "end_frame", duration=4)
    )
    assert [row["role"] for row in controls["input_roles"]] == ["start_frame"]
    assert any(row["kind"] == "unsupported_end_frame_not_submitted" for row in controls["adaptations"])


def test_new_versions_are_explicit_and_never_silent_upgrades():
    seedance_new = cap.resolve_route("Seedance 2.5", "即梦/Dreamina")
    seedance_old = cap.resolve_route("Seedance 2.0", "即梦/Dreamina")
    ray_new = cap.resolve_route("Luma Ray3.2", "Luma Dream Machine")
    ray_old = cap.resolve_route("Luma Ray3 / Ray3.14", "Luma Dream Machine")
    assert seedance_new["model"] == "Seedance 2.5"
    assert seedance_old["model"] == "Seedance 2.0"
    assert ray_new["model"] == "Luma Ray3.2"
    assert ray_old["model"] == "Luma Ray3 / Ray3.14"
    assert ray_old["access_status"] == "legacy"
