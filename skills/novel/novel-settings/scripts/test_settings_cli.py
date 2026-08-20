#!/usr/bin/env python3
"""Regression coverage for the novel craft-profile choice point."""
from __future__ import annotations

import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
NOVEL_LIB = os.path.abspath(os.path.join(HERE, "..", "..", "_lib"))
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)

import craft_profile  # noqa: E402
import settings  # noqa: E402


def test_craft_profile_aliases_normalize_to_canonical_values():
    expected = {
        "商业连载": "commercial_serial",
        "类型小说": "genre_novel",
        "文学小说": "literary",
        "实验小说": "experimental",
    }
    for raw, canonical in expected.items():
        assert settings.normalize_setting_value("创作工艺档", raw) == canonical
        check = settings.validate_setting("创作工艺档", raw, family="novel")
        assert check["level"] == "ok"
        assert check["value"] == canonical


def test_missing_profile_has_safe_legacy_default_and_ignores_platform():
    assert craft_profile.resolve_craft_profile({}) == "genre_novel"
    assert craft_profile.resolve_craft_profile({"目标平台": "晋江"}) == "genre_novel"
    assert craft_profile.resolve_craft_profile({"目标平台": "番茄"}) == "genre_novel"


def test_new_project_settings_record_default_profile(tmp_path):
    root = str(tmp_path)
    settings.write_settings(root, {"目标平台": "跨平台"})

    parsed = settings.load_settings(root)

    assert parsed["创作工艺档"] == "genre_novel"


def test_private_global_profile_prefills_new_project(tmp_path):
    root = str(tmp_path)
    with open(os.path.join(root, "创作偏好-默认.md"), "w", encoding="utf-8") as f:
        f.write("# 默认\n- 创作工艺档：文学小说\n")

    settings.write_settings(root, {"目标平台": "跨平台"})

    assert settings.load_settings(root)["创作工艺档"] == "literary"


def test_setting_patch_persists_canonical_profile(tmp_path):
    root = str(tmp_path)
    settings.write_settings(root, {"目标平台": "跨平台"})

    old, new = settings.set_project_setting(root, "创作工艺档", "实验小说")

    assert old == "genre_novel"
    assert new == "experimental"
    assert settings.load_settings(root)["创作工艺档"] == "experimental"


def test_forced_custom_profile_is_preserved_for_visible_adapter_failure(tmp_path):
    root = str(tmp_path)
    settings.write_settings(root, {"目标平台": "跨平台"})

    _, new = settings.set_project_setting(
        root,
        "创作工艺档",
        "hybrid_lyric",
        validate=False,
    )

    assert new == "hybrid_lyric"
    assert settings.load_settings(root)["创作工艺档"] == "hybrid_lyric"
    assert craft_profile.resolve_craft_profile({"创作工艺档": new}) == "hybrid_lyric"
    assert craft_profile.is_supported_craft_profile(new) is False
