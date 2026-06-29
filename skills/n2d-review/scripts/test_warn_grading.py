#!/usr/bin/env python3
"""Tests for WARN risk_score grading (gate.py display/priority layer).

Covers:
  - _warn_tier boundary behaviour
  - _warn_icon returns correct emoji per tier
  - add() propagates risk_score into finding dict
  - add() auto-derives risk_score from dim for WARN findings
  - add() does NOT set risk_score for BLOCK/INFO findings
  - _sort_key puts BLOCK before WARN before INFO; WARNs sorted by risk_score desc
  - _default_risk_score returns sensible values for known and unknown dims
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest
from typing import Optional

# Import gate module symbols (test runs from skills/n2d-review/scripts/)
import gate


class TestWarnTier:
    def test_none_is_moderate(self):
        assert gate._warn_tier(None) == "warn_mod"

    def test_high_boundary(self):
        assert gate._warn_tier(0.7) == "warn_hi"
        assert gate._warn_tier(0.85) == "warn_hi"
        assert gate._warn_tier(0.999) == "warn_hi"

    def test_moderate_range(self):
        assert gate._warn_tier(0.4) == "warn_mod"
        assert gate._warn_tier(0.55) == "warn_mod"
        assert gate._warn_tier(0.699) == "warn_mod"

    def test_minor_range(self):
        assert gate._warn_tier(0.0) == "warn_minor"
        assert gate._warn_tier(0.2) == "warn_minor"
        assert gate._warn_tier(0.399) == "warn_minor"


class TestWarnIcon:
    def test_tiers(self):
        assert "❗" in gate._warn_icon("warn_hi") or "exclamation" in gate._warn_icon("warn_hi").lower()
        assert "warn" in gate._warn_icon("warn_mod").lower() or "⚠" in gate._warn_icon("warn_mod")
        assert "info" in gate._warn_icon("warn_minor").lower() or "ℹ" in gate._warn_icon("warn_minor")

    def test_unknown_tier_falls_back(self):
        assert gate._warn_icon("nonexistent") == "⚠️"


class TestDefaultRiskScore:
    def test_face_dims_high(self):
        assert gate._default_risk_score("脸(G1)") >= 0.7
        assert gate._default_risk_score("face consistency") >= 0.7
        assert gate._default_risk_score("角色一致性") >= 0.7

    def test_contract_dims_moderate_high(self):
        assert gate._default_risk_score("契约继承") >= 0.6
        assert gate._default_risk_score("跨集音色") >= 0.6
        assert gate._default_risk_score("跨集声纹") >= 0.6

    def test_scene_outfit_moderate(self):
        assert 0.4 <= gate._default_risk_score("场景(O2)") <= 0.6
        assert 0.4 <= gate._default_risk_score("服装配色") <= 0.6

    def test_style_low(self):
        assert gate._default_risk_score("风格一致性") < 0.4
        assert gate._default_risk_score("色调") < 0.4

    def test_unrecognised_moderate(self):
        assert gate._default_risk_score("未知维度XYZ") == 0.5


class TestAddRiskScore:
    def setup_method(self):
        gate.findings.clear()

    def test_warn_auto_derives_risk_score(self):
        gate.add(gate.WARN, "脸(G1)", "test.png", "face drift")
        f = gate.findings[-1]
        assert f["sev"] == gate.WARN
        assert "risk_score" in f
        assert f["risk_score"] is not None
        assert f["risk_score"] >= 0.7  # face dims are high

    def test_warn_explicit_risk_score_overrides(self):
        gate.add(gate.WARN, "脸(G1)", "test.png", "face drift", risk_score=0.42)
        f = gate.findings[-1]
        assert f["risk_score"] == 0.42

    def test_block_has_no_risk_score(self):
        gate.add(gate.BLOCK, "脸(G1)", "test.png", "face drift")
        f = gate.findings[-1]
        assert "risk_score" not in f

    def test_info_has_no_risk_score(self):
        gate.add(gate.INFO, "prompt", "test.md", "advisory note")
        f = gate.findings[-1]
        assert "risk_score" not in f

    def test_warn_advisory_dim_gets_low_risk(self):
        gate.add(gate.WARN, "prompt", "test.md", "checklist missing")
        f = gate.findings[-1]
        assert f["risk_score"] <= 0.3


class TestSortKey:
    def test_block_before_warn(self):
        b = {"sev": gate.BLOCK}
        w = {"sev": gate.WARN, "risk_score": 0.9}
        assert gate._finding_sort_key(b) < gate._finding_sort_key(w)

    def test_warn_before_info(self):
        w = {"sev": gate.WARN, "risk_score": 0.9}
        i = {"sev": gate.INFO}
        assert gate._finding_sort_key(w) < gate._finding_sort_key(i)

    def test_high_risk_before_low_risk(self):
        w_hi = {"sev": gate.WARN, "risk_score": 0.9}
        w_lo = {"sev": gate.WARN, "risk_score": 0.2}
        # Higher risk_score sorts earlier (negated in key)
        assert gate._finding_sort_key(w_hi) < gate._finding_sort_key(w_lo)

    def test_ungraded_warn_middle(self):
        w_hi = {"sev": gate.WARN, "risk_score": 0.9}
        w_no = {"sev": gate.WARN}  # no risk_score
        w_lo = {"sev": gate.WARN, "risk_score": 0.2}
        keys = sorted([w_hi, w_no, w_lo], key=gate._finding_sort_key)
        # w_hi first, w_no second (0.5 default), w_lo last
        assert keys[0] is w_hi
        assert keys[1] is w_no
        assert keys[2] is w_lo


class TestDimRiskScore:
    """Verify per-dimension risk_score defaults in consistency_audit."""
    def setup_method(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "consistency_audit.py")
        spec = importlib.util.spec_from_file_location("_n2d_review_consistency_audit_for_test", path)
        ca = importlib.util.module_from_spec(spec)
        sys.modules["_n2d_review_consistency_audit_for_test"] = ca
        spec.loader.exec_module(ca)
        self.ca = ca

    def test_known_face_dim(self):
        assert self.ca._dim_risk_score("脸(G1)") >= 0.8

    def test_known_style_dim(self):
        assert self.ca._dim_risk_score("风格(S1)") < 0.4

    def test_substring_match(self):
        assert self.ca._dim_risk_score("脸(G1) something extra") >= 0.8

    def test_unknown_dim_fallback(self):
        assert self.ca._dim_risk_score("全新维度") == 0.5
