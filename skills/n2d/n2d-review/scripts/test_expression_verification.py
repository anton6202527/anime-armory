#!/usr/bin/env python3
"""Tests for expression_verification.py — pure functions only (no insightface needed)."""
from __future__ import annotations

import pytest
import expression_verification as ev


class TestMouthOpennessRatio:
    def test_closed_mouth(self):
        lm = [(0.0, 0.0)] * 106
        # Landmarks[52] serves as both top and left anchor
        lm[ev.MOUTH_TOP_IDX] = (50.0, 45.0)     # top-left anchor
        lm[ev.MOUTH_BOTTOM_IDX] = (50.0, 47.0)   # bottom of mouth
        lm[ev.MOUTH_LEFT_IDX] = (50.0, 45.0)     # same as top (shared anchor)
        lm[ev.MOUTH_RIGHT_IDX] = (58.0, 45.0)    # right of mouth
        ratio = ev.mouth_openness_ratio(lm)
        # v = |47-45| = 2, h = |58-50| = 8, ratio = 2/8 = 0.25
        assert ratio == pytest.approx(0.25)

    def test_open_mouth(self):
        lm = [(0.0, 0.0)] * 106
        lm[ev.MOUTH_TOP_IDX] = (50.0, 40.0)
        lm[ev.MOUTH_BOTTOM_IDX] = (50.0, 55.0)
        lm[ev.MOUTH_LEFT_IDX] = (50.0, 40.0)
        lm[ev.MOUTH_RIGHT_IDX] = (58.0, 47.0)
        ratio = ev.mouth_openness_ratio(lm)
        # v = |55-40| = 15, h = |58-50| = 8, ratio = 15/8 = 1.875
        assert ratio == pytest.approx(1.875)

    def test_zero_horizontal(self):
        lm = [(0.0, 0.0)] * 106
        lm[ev.MOUTH_TOP_IDX] = (50.0, 40.0)
        lm[ev.MOUTH_BOTTOM_IDX] = (50.0, 55.0)
        lm[ev.MOUTH_LEFT_IDX] = (50.0, 46.0)
        lm[ev.MOUTH_RIGHT_IDX] = (50.0, 46.0)
        assert ev.mouth_openness_ratio(lm) == 0.0


class TestEyeOpennessRatio:
    def test_basic(self):
        lm = [(0.0, 0.0)] * 106
        lm[ev.EYE_TOP_IDX] = (40.0, 25.0)
        lm[ev.EYE_BOTTOM_IDX] = (40.0, 30.0)
        assert ev.eye_openness_ratio(lm) == 5.0


class TestExpressionChangeVerdict:
    def test_no_change_warns(self):
        assert ev.expression_change_verdict(0.5, 0.5, 10.0, 10.0) == "warn"

    def test_small_change_warns(self):
        assert ev.expression_change_verdict(0.5, 0.6, 10.0, 10.1, mouth_threshold=0.30, eye_threshold=0.15) == "warn"

    def test_large_mouth_change_ok(self):
        assert ev.expression_change_verdict(0.2, 0.8, 10.0, 10.0) == "ok"

    def test_large_eye_change_ok(self):
        assert ev.expression_change_verdict(0.5, 0.5, 10.0, 15.0) == "ok"

    def test_both_large_change_ok(self):
        assert ev.expression_change_verdict(0.2, 0.8, 10.0, 15.0) == "ok"


class TestProbeInsightface:
    def test_returns_bool(self):
        assert isinstance(ev._probe_insightface(), bool)
