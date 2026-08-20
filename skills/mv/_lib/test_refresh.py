#!/usr/bin/env python3
from datetime import date

import refresh


def test_current_video_snapshot_separates_current_and_legacy_versions():
    snapshot = refresh.build_snapshot(
        "video_models", date(2026, 8, 20).isoformat(),
        verification_mode="official_content_review",
        verification_note="official source review",
    )
    rows = {row["name"]: row for row in snapshot["items"]}
    assert rows["Seedance 2.5"]["capabilities"]
    assert rows["Gemini Omni Flash Preview"]["route_status"] == "adapter_required"
    assert rows["Gemini Omni Flash Preview"]["preview"] is True
    assert rows["Luma Ray3.2"]["capabilities"]
    assert rows["Seedance 2.0"]["legacy"] is True
    assert rows["Luma Ray3 / Ray3.14"]["legacy"] is True
    assert snapshot["verification_mode"] == "official_content_review"


def test_pending_api_is_not_promoted_and_forbidden_image_channel_does_not_return():
    channels = {row["name"]: row for row in refresh.CURRENT_SNAPSHOTS["video_channels"]}
    assert channels["火山方舟/Volcengine API"]["models"]["Seedance 2.5"] == "api_pending"
    assert channels["Google Gemini API"]["models"]["Gemini Omni Flash Preview"] == "adapter_required"
    seedream = next(
        row for row in refresh.CURRENT_SNAPSHOTS["image_backends"]
        if row["name"] == "Seedream 5.0 Lite"
    )
    assert "即梦/Dreamina" not in seedream["channels"]
