#!/usr/bin/env python3
"""Tests for shared n2d platform profiles."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import n2d_platform_profiles as p  # noqa: E402


def test_video_backend_aliases_and_limits():
    assert p.normalize_video_backend("即梦") == "dreamina"
    assert p.normalize_video_backend("Seedance") == "seedance"
    assert p.normalize_video_backend("可灵") == "kling"
    assert p.video_backend_max_seconds("seedance") == 15
    assert p.video_backend_max_seconds("veo") == 8
    assert p.video_backend_max_seconds("unknown", default=7) == 7


def test_native_av_backends_come_from_profiles():
    assert {"seedance", "veo", "sora"} <= set(p.NATIVE_AV_BACKENDS)
    assert "dreamina" not in p.NATIVE_AV_BACKENDS
