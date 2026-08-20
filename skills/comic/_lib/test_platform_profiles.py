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
    assert profile.thumbnail_assets["episode"]["width"] == 300
    assert profile.field_provenance["thumbnail_assets.episode"]["source_url"] == platform_profiles.TAPAS_SOURCE
    assert profile.field_provenance["thumbnail_assets.episode.formats"]["source_url"] == platform_profiles.TAPAS_SOURCE
    assert profile.field_provenance["thumbnail_assets.episode.max_file_bytes"]["source_url"] == platform_profiles.TAPAS_SOURCE
    assert profile.format_specific_constraints["gif"]["max_image_height_px"] == 1000


def test_webtoon_profile_has_field_level_thumbnail_specs_and_missing_assets_are_explicit() -> None:
    profile = platform_profiles.profile_for_platform("WEBTOON")
    assert profile.verified is True
    assert profile.thumbnail_assets["series_square"] == {
        "width": 1080, "height": 1080, "formats": ["jpg", "png"], "max_file_bytes": 500 * 1024,
        "constraint_level": "required",
    }
    assert profile.thumbnail_assets["series_vertical"]["height"] == 1920
    assert profile.thumbnail_assets["episode"]["width"] == 202
    assert "thumbnail_assets.episode" in profile.field_provenance
    findings = platform_profiles.validate_manifest(
        root=Path("."),
        manifest={"pages": [], "rendered": []},
        profile=profile,
        usage="发布候选",
    )
    assert findings[0]["severity"] == "block"
    assert findings[0]["code"] == "platform_thumbnail_asset_missing"


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


def test_kuaikan_dpi_and_rgb_notes_are_executable(tmp_path: Path) -> None:
    from PIL import Image

    path = tmp_path / "page.png"
    Image.new("RGB", (1280, 10)).save(path)
    profile = platform_profiles.profile_for_platform("快看漫画投稿")
    findings = platform_profiles.validate_manifest(
        root=tmp_path,
        manifest={"pages": [{"path": "page.png", "format": "png", "size": {"width": 1280, "height": 10}}]},
        profile=profile,
        usage="发布候选",
    )
    codes = {item["code"] for item in findings}
    assert "platform_dpi_mismatch" in codes
    assert "platform_color_mode_mismatch" not in codes


def test_tapas_gif_height_exception_is_machine_checked(tmp_path: Path) -> None:
    from PIL import Image

    path = tmp_path / "episode.gif"
    Image.new("RGB", (940, 1001)).save(path, format="GIF")
    findings = platform_profiles.validate_manifest(
        root=tmp_path,
        manifest={"rendered": [{"path": "episode.gif", "format": "gif", "size": {"width": 940, "height": 1001}}]},
        profile=platform_profiles.profile_for_platform("Tapas"),
        usage="发布候选",
    )
    assert "platform_format_height_exceeded" in {item["code"] for item in findings}


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
    exactly_eight = platform_profiles.validate_manifest(
        root=Path("."),
        manifest={"pages": [{"path": f"p{i}.png"} for i in range(8)]},
        profile=profile,
        usage="发布候选",
    )
    assert "platform_page_count_below_recommendation" in {item["code"] for item in exactly_eight}
    nine = platform_profiles.validate_manifest(
        root=Path("."),
        manifest={"pages": [{"path": f"p{i}.png"} for i in range(9)]},
        profile=profile,
        usage="发布候选",
    )
    assert "platform_page_count_below_recommendation" not in {item["code"] for item in nine}


def test_profile_freshness_is_computable() -> None:
    profile = platform_profiles.profile_for_platform("Tapas")
    assert platform_profiles.profile_age_days(profile, today=date(2026, 8, 21)) == 1
    assert platform_profiles.field_age_days(profile, "page_width_px", today=date(2026, 8, 21)) == 1


def test_webtoon_episode_thumbnail_dimensions_are_recommended_not_block(tmp_path: Path) -> None:
    from PIL import Image

    square = tmp_path / "square.png"
    vertical = tmp_path / "vertical.png"
    episode_path = tmp_path / "episode.png"
    Image.new("RGB", (1080, 1080)).save(square)
    Image.new("RGB", (1080, 1920)).save(vertical)
    Image.new("RGB", (203, 142)).save(episode_path)
    profile = platform_profiles.profile_for_platform("WEBTOON")
    findings = platform_profiles.validate_manifest(
        root=tmp_path,
        manifest={"platform_assets": {
            "series_square": {"path": "square.png", "format": "png", "size": {"width": 1080, "height": 1080}},
            "series_vertical": {"path": "vertical.png", "format": "png", "size": {"width": 1080, "height": 1920}},
            "episode": {"path": "episode.png", "format": "png", "size": {"width": 203, "height": 142}},
        }},
        profile=profile,
        usage="发布候选",
    )
    episode = [item for item in findings if item["code"] == "platform_thumbnail_dimensions_mismatch" and "episode" in item["reason"]]
    assert episode and episode[0]["severity"] == "warn"
