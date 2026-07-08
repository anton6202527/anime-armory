#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

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
