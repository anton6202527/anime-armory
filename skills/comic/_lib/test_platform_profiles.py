#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from datetime import date

import platform_profiles


def test_tapas_profile_has_verified_width_and_size() -> None:
    profile = platform_profiles.profile_for_platform("Tapas")
    assert profile.verified is True
    assert profile.page_width_px == 940
    assert profile.max_file_bytes == 10 * 1024 * 1024


def test_webtoon_profile_warns_unverified() -> None:
    profile = platform_profiles.profile_for_platform("WEBTOON")
    findings = platform_profiles.validate_manifest(
        root=Path("."),
        manifest={"pages": [], "rendered": []},
        profile=profile,
        usage="发布候选",
    )
    assert findings[0]["severity"] == "block"
    assert findings[0]["code"] == "platform_profile_unverified"


def test_kuaikan_panel_floor_is_scoped_to_submission_profile() -> None:
    profile = platform_profiles.profile_for_platform("快看漫画投稿")
    findings = platform_profiles.validate_manifest(
        root=Path("."),
        manifest={"panels": [{"panel_id": f"P{i:03d}"} for i in range(1, 5)]},
        profile=profile,
        usage="发布候选",
    )
    assert "platform_panel_minimum_not_met" in {item["code"] for item in findings}
    generic = platform_profiles.validate_manifest(
        root=Path("."),
        manifest={"panels": [{"panel_id": "P001"}]},
        profile=platform_profiles.profile_for_platform("通用"),
        usage="发布候选",
    )
    assert "platform_panel_minimum_not_met" not in {item["code"] for item in generic}


def test_manga_plus_page_recommendation_is_warn_not_block() -> None:
    profile = platform_profiles.profile_for_platform("MANGA Plus Creators")
    findings = platform_profiles.validate_manifest(
        root=Path("."),
        manifest={"pages": [{"path": f"p{i}.png"} for i in range(4)]},
        profile=profile,
        usage="发布候选",
    )
    row = next(item for item in findings if item["code"] == "platform_page_count_below_recommendation")
    assert row["severity"] == "warn"


def test_profile_freshness_is_computable() -> None:
    profile = platform_profiles.profile_for_platform("Tapas")
    assert platform_profiles.profile_age_days(profile, today=date(2026, 7, 15)) == 1
