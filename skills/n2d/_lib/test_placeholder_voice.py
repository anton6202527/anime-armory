"""Placeholder voice-row detection (single source of truth) tests.

Run from this directory:
  python3 -m pytest test_placeholder_voice.py

Locks the cross-stage placeholder predicate so render_voice (progress column),
finalize_storyboard and validate_timings stay in agreement: macOS `say` is a
placeholder-grade backend even when it produces audible audio, so any say: voice_key
counts as placeholder regardless of the marker separator.
"""
from __future__ import annotations

import n2d_route as route


def test_explicit_placeholder_flag():
    assert route.manifest_is_placeholder([{"idx": 0, "占位": True}]) is True


def test_say_canonical_underscore_marker():
    # What render_voice/voice_manifest actually emits today.
    rows = [{"idx": 0, "voice_key": "say:Tingting_placeholder"}]
    assert route.manifest_is_placeholder(rows) is True


def test_say_legacy_hash_marker():
    # Old projects may carry the legacy `#placeholder` separator.
    rows = [{"idx": 0, "voice_key": "say:Tingting#placeholder"}]
    assert route.manifest_is_placeholder(rows) is True


def test_say_prefix_without_suffix_still_placeholder():
    rows = [{"idx": 0, "voice_key": "say:Tingting"}]
    assert route.manifest_is_placeholder(rows) is True


def test_say_via_voice_id_field():
    rows = [{"idx": 0, "voice_key": "SHEN", "voice_id": "say:Tingting"}]
    assert route.manifest_is_placeholder(rows) is True


def test_real_voicemap_key_is_not_placeholder():
    rows = [
        {"idx": 0, "voice_key": "SHEN", "voice_id": "CosyVoice:SHEN:沈念.wav"},
        {"idx": 1, "voice_key": "LIU", "voice_id": "MiniMax:female-1"},
    ]
    assert route.manifest_is_placeholder(rows) is False
    assert route.placeholder_rows(rows) == []
    assert route.placeholder_indices(rows) == []


def test_mixed_manifest_reports_only_placeholder_indices():
    rows = [
        {"idx": 0, "voice_key": "SHEN", "voice_id": "CosyVoice:SHEN:沈念.wav"},
        {"idx": 1, "voice_key": "say:Tingting_placeholder"},
        {"idx": 2, "占位": True},
    ]
    assert route.manifest_is_placeholder(rows) is True
    assert route.placeholder_indices(rows) == [1, 2]


def test_non_list_manifest_is_safe():
    assert route.manifest_is_placeholder(None) is False
    assert route.placeholder_rows("nope") == []
