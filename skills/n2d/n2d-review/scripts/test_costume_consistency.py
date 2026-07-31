#!/usr/bin/env python3
"""Tests for costume_consistency.py — pure functions only (no torch/CLIP needed)."""
from __future__ import annotations

import pytest
import costume_consistency as cc


class TestCalibrateFloor:
    def test_empty_returns_fallback(self):
        assert cc.calibrate_floor([]) == cc.DEFAULT_FALLBACK

    def test_single_score_returns_fallback(self):
        assert cc.calibrate_floor([0.85]) == cc.DEFAULT_FALLBACK

    def test_two_scores_returns_min(self):
        result = cc.calibrate_floor([0.90, 0.80])
        assert result == 0.80

    def test_many_scores_returns_min(self):
        result = cc.calibrate_floor([0.95, 0.92, 0.88, 0.91, 0.85])
        assert result == 0.85

    def test_custom_fallback(self):
        assert cc.calibrate_floor([], fallback=0.70) == 0.70


class TestBand:
    def test_below_floor_block(self):
        assert cc.band(0.70, floor=0.80) == "block"

    def test_at_floor_warn(self):
        assert cc.band(0.80, floor=0.80) == "warn"

    def test_within_margin_warn(self):
        assert cc.band(0.85, floor=0.80, margin=0.10) == "warn"

    def test_above_margin_ok(self):
        assert cc.band(0.91, floor=0.80, margin=0.10) == "ok"

    def test_far_above_ok(self):
        assert cc.band(0.98, floor=0.80) == "ok"


class TestProbeClip:
    def test_returns_bool(self):
        result = cc._probe_clip()
        assert isinstance(result, bool)


class TestAnalyzeNoDeps:
    def test_analyze_without_clip_returns_unavailable(self):
        # This test works regardless of whether CLIP is installed;
        # the analyze function checks _probe_clip() first.
        import os
        # Use a temp root that has no identity_registry — should fail fast
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = cc.analyze(tmp, "第1集")
            # Either unavailable (no CLIP) or available with 0 shots (no images)
            assert isinstance(result, dict)
            assert "available" in result
            assert "shots" in result
