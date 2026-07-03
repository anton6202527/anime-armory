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


class TestConsolidateByShot:
    """逐镜仲裁/归并层（correlate 的去重对偶·report 层不改 verdict）。"""

    def test_dedup_by_evidence_family_no_double_count(self):
        # 同一镜 3 条 finding 但只 2 个独立证据族（pixel_hash 双发=同根因）→ merged_family_count=2，raw=3。
        findings = [
            {"sev": gate.WARN, "dim": "脸(G1)", "msg": "a", "affected_shots": ["07.png"], "evidence_family": "pixel_hash"},
            {"sev": gate.WARN, "dim": "表情(EXP)", "msg": "b", "affected_shots": ["07.png"], "evidence_family": "pixel_hash"},
            {"sev": gate.BLOCK, "dim": "口型(LIP)", "msg": "c", "affected_shots": ["07.png"], "evidence_family": "lipsync_av"},
        ]
        res = gate.consolidate_findings_by_shot(findings)
        assert len(res) == 1
        row = res[0]
        assert row["shot"] == "07.png"
        assert row["raw_finding_count"] == 3
        assert row["merged_family_count"] == 2            # pixel_hash 去重→2 族
        assert set(row["independent_evidence_families"]) == {"pixel_hash", "lipsync_av"}
        assert row["verdict"] == gate.BLOCK               # 最坏维度为准
        assert len(row["dims"]) == 3

    def test_unknown_family_not_counted_independent(self):
        findings = [
            {"sev": gate.WARN, "dim": "x", "msg": "a", "affected_shots": ["01.png"], "evidence_family": "unknown"},
            {"sev": gate.WARN, "dim": "y", "msg": "b", "affected_shots": ["01.png"], "evidence_family": "unknown"},
        ]
        res = gate.consolidate_findings_by_shot(findings)
        assert res[0]["independent_evidence_families"] == []
        assert res[0]["merged_family_count"] == 1

    def test_sorted_worst_first(self):
        findings = [
            {"sev": gate.INFO, "dim": "a", "msg": "m", "affected_shots": ["02.png"], "evidence_family": "f1"},
            {"sev": gate.BLOCK, "dim": "b", "msg": "m", "affected_shots": ["09.png"], "evidence_family": "f2"},
        ]
        res = gate.consolidate_findings_by_shot(findings)
        assert [r["shot"] for r in res] == ["09.png", "02.png"]   # block 镜排前

    def test_findings_without_shots_ignored(self):
        findings = [{"sev": gate.BLOCK, "dim": "契约", "msg": "no shot"}]
        assert gate.consolidate_findings_by_shot(findings) == []
