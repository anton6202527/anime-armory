#!/usr/bin/env python3
"""Tests for cross-detector correlation upgrade (gate.correlate_findings)."""
from __future__ import annotations

import pytest
import gate


class TestCorrelateFindings:
    def test_no_upgrade_when_no_warns(self):
        findings = [
            {"sev": gate.BLOCK, "dim": "脸(G1)", "msg": "face drift", "affected_shots": ["01.png"]},
        ]
        result = gate.correlate_findings(findings)
        assert result == []

    def test_no_upgrade_when_warns_on_different_clips(self):
        findings = [
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "a", "risk_score": 0.8, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "服装配色(N1)", "msg": "b", "risk_score": 0.8, "affected_shots": ["02.png"]},
            {"sev": gate.WARN, "dim": "场景(O2)", "msg": "c", "risk_score": 0.8, "affected_shots": ["03.png"]},
        ]
        result = gate.correlate_findings(findings)
        assert result == []

    def test_no_upgrade_when_less_than_3_dims(self):
        findings = [
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "a", "risk_score": 0.8, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "b", "risk_score": 0.8, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "c", "risk_score": 0.8, "affected_shots": ["01.png"]},
        ]
        result = gate.correlate_findings(findings)
        assert result == []

    def test_no_upgrade_when_low_risk_warns(self):
        findings = [
            {"sev": gate.WARN, "dim": "风格(S1)", "msg": "a", "risk_score": 0.3, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "色调", "msg": "b", "risk_score": 0.3, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "prompt", "msg": "c", "risk_score": 0.2, "affected_shots": ["01.png"]},
        ]
        result = gate.correlate_findings(findings)
        assert result == []

    def test_upgrade_triggered_with_3_high_warns_3_dims(self):
        findings = [
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "face drift", "risk_score": 0.8, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "服装配色(N1)", "msg": "outfit change", "risk_score": 0.8, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "场景(O2)", "msg": "scene shift", "risk_score": 0.8, "affected_shots": ["01.png"]},
        ]
        result = gate.correlate_findings(findings)
        assert len(result) == 1
        assert result[0]["sev"] == gate.BLOCK
        assert "多维度同时漂移" in str(result[0]["msg"])
        assert result[0]["risk_score"] == 0.9  # correlation upgrades are high-confidence

    def test_no_upgrade_when_same_evidence_family(self):
        findings = [
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "a", "risk_score": 0.8, "affected_shots": ["01.png"], "evidence_family": "pixel_hash"},
            {"sev": gate.WARN, "dim": "服装配色(N1)", "msg": "b", "risk_score": 0.8, "affected_shots": ["01.png"], "evidence_family": "pixel_hash"},
            {"sev": gate.WARN, "dim": "场景(O2)", "msg": "c", "risk_score": 0.8, "affected_shots": ["01.png"], "evidence_family": "pixel_hash"},
        ]
        result = gate.correlate_findings(findings)
        assert result == []

    def test_upgrade_uses_affected_artifacts(self):
        findings = [
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "a", "risk_score": 0.8, "affected_artifacts": ["出图/第1集/图片/01.png"]},
            {"sev": gate.WARN, "dim": "服装配色(N1)", "msg": "b", "risk_score": 0.8, "affected_artifacts": ["出图/第1集/图片/01.png"]},
            {"sev": gate.WARN, "dim": "场景(O2)", "msg": "c", "risk_score": 0.8, "affected_artifacts": ["出图/第1集/图片/01.png"]},
        ]
        result = gate.correlate_findings(findings)
        assert len(result) >= 1

    def test_upgrade_skips_non_warn_severity(self):
        findings = [
            {"sev": gate.BLOCK, "dim": "脸(G1)", "msg": "a", "risk_score": 0.9, "affected_shots": ["01.png"]},
            {"sev": gate.BLOCK, "dim": "服装配色(N1)", "msg": "b", "risk_score": 0.9, "affected_shots": ["01.png"]},
            {"sev": gate.BLOCK, "dim": "场景(O2)", "msg": "c", "risk_score": 0.9, "affected_shots": ["01.png"]},
        ]
        result = gate.correlate_findings(findings)
        assert result == []  # correlation only upgrades WARN → BLOCK, not BLOCK

    def test_upgrade_exact_risk_boundary(self):
        findings = [
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "a", "risk_score": 0.7, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "服装配色(N1)", "msg": "b", "risk_score": 0.7, "affected_shots": ["01.png"]},
            {"sev": gate.WARN, "dim": "场景(O2)", "msg": "c", "risk_score": 0.7, "affected_shots": ["01.png"]},
        ]
        result = gate.correlate_findings(findings)
        assert len(result) == 1  # 0.7 is the boundary, >= 0.7 triggers
