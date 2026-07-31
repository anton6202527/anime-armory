#!/usr/bin/env python3
"""Tests for fidelity-gate KPI integration in score.py."""
from __future__ import annotations

import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "n2d-score", "scripts"))
import score


class TestBuildConsistencyKPI:
    def test_absent_fidelity_gate_returns_insufficient_data(self):
        consistency = {
            "sections": {
                "脸(G1)": {
                    "fidelity_gate": "absent",
                    "encoder": "arcface",
                    "characters": {
                        "沈念": {"ep_mean_score": 0.92},
                        "柳娘子": {"ep_mean_score": 0.88},
                    },
                }
            }
        }
        kpi = score.build_consistency_kpi(consistency, None)
        assert kpi["verdict"] == "insufficient_data"
        assert "warnings" in kpi
        assert len(kpi["warnings"]) > 0
        assert "vlm_verify" in kpi["warnings"][0] or "fidelity-gate" in kpi["warnings"][0]

    def test_none_fidelity_gate_returns_insufficient_data(self):
        consistency = {
            "sections": {
                "脸(G1)": {
                    "fidelity_gate": None,
                    "encoder": "arcface",
                    "characters": {
                        "沈念": {"ep_mean_score": 0.92},
                    },
                }
            }
        }
        kpi = score.build_consistency_kpi(consistency, None)
        assert kpi["verdict"] == "insufficient_data"

    def test_active_fidelity_gate_above_line(self):
        consistency = {
            "sections": {
                "脸(G1)": {
                    "fidelity_gate": "active",
                    "encoder": "arcface",
                    "characters": {
                        "沈念": {"ep_mean_score": 0.92},
                    },
                }
            }
        }
        kpi = score.build_consistency_kpi(consistency, None)
        assert kpi["verdict"] == "above"
        assert "warnings" not in kpi

    def test_active_fidelity_gate_below_line(self):
        consistency = {
            "sections": {
                "脸(G1)": {
                    "fidelity_gate": "active",
                    "encoder": "arcface",
                    "characters": {
                        "沈念": {"ep_mean_score": 0.72},
                    },
                }
            }
        }
        kpi = score.build_consistency_kpi(consistency, None)
        assert kpi["verdict"] == "below"

    def test_no_intra_scores_none_verdict(self):
        consistency = {
            "sections": {
                "脸(G1)": {
                    "fidelity_gate": "absent",
                    "encoder": "arcface",
                    "characters": {},
                }
            }
        }
        kpi = score.build_consistency_kpi(consistency, None)
        assert kpi["intra_episode"] is None
        assert kpi["verdict"] is None  # no scores to evaluate, don't fabricate
