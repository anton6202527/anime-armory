#!/usr/bin/env python3
"""Evidence-tier governance for n2d machine QC verdicts.

Creative VLM judgements are useful triage but are not deterministic proof.
Numeric detectors may auto-block only after a production-sized labelled golden
set demonstrates adequate separation. Deterministic contract/pixel checks keep
their existing load-bearing authority.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping


KIND = "n2d_detector_reliability_policy"
VERSION = 1
VLM_KINDS = {"vlm", "vision_language_model", "semantic_vlm"}
NUMERIC_KINDS = {"numeric", "embedding", "classifier", "distance_metric"}
DETERMINISTIC_KINDS = {"deterministic", "contract", "pixel_exact", "schema"}


def govern_verdict(
    raw_verdict: str,
    *,
    detector_kind: str,
    calibration: Mapping[str, Any] | None = None,
    human_confirmed: bool = False,
    load_bearing: bool = False,
) -> Dict[str, Any]:
    raw = str(raw_verdict or "warn").strip().lower()
    kind = str(detector_kind or "unknown").strip().lower()
    cal = dict(calibration or {})
    governed = raw
    auto_block = False
    reason = "raw verdict retained"

    if human_confirmed:
        auto_block = raw == "block"
        reason = "human-confirmed finding"
    elif kind in VLM_KINDS:
        if raw == "block":
            governed = "warn"
        reason = "VLM semantic judgement is advisory; block requires human or deterministic corroboration"
    elif kind in NUMERIC_KINDS:
        eligible = bool(cal.get("auto_block_eligible")) and str(cal.get("evidence_status") or cal.get("status") or "") in {
            "production_calibrated", "calibrated", "separable", "overlap",
        }
        if raw == "block" and not eligible and not load_bearing:
            governed = "warn"
            reason = "numeric detector lacks production-sized labelled calibration"
        else:
            auto_block = raw == "block"
            reason = "calibrated numeric detector" if eligible else "explicit load-bearing policy"
    elif kind in DETERMINISTIC_KINDS or load_bearing:
        auto_block = raw == "block"
        reason = "deterministic/load-bearing contract check"
    elif raw == "block":
        governed = "warn"
        reason = "unknown detector evidence tier cannot auto-block"

    return {
        "kind": KIND,
        "version": VERSION,
        "detector_kind": kind,
        "raw_verdict": raw,
        "verdict": governed,
        "auto_block_eligible": auto_block,
        "human_confirmation_required": raw == "block" and governed != "block",
        "reason": reason,
    }


def registry_enforcement(row: Mapping[str, Any]) -> Dict[str, Any]:
    detector_kind = str(row.get("detector_kind") or "numeric")
    calibration = {
        "status": row.get("calibration_status"),
        "evidence_status": row.get("evidence_status"),
        "auto_block_eligible": row.get("auto_block_eligible"),
    }
    governed = govern_verdict("block", detector_kind=detector_kind, calibration=calibration)
    return {
        "detector_kind": detector_kind,
        "auto_block_eligible": governed["verdict"] == "block",
        "unconfirmed_block_action": "block" if governed["verdict"] == "block" else "warn_and_human_review",
        "reason": governed["reason"],
    }


__all__ = ["KIND", "VERSION", "govern_verdict", "registry_enforcement"]

