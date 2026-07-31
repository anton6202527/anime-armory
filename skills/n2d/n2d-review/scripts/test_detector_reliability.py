from __future__ import annotations

import detector_reliability as dr


def test_vlm_block_is_capped_at_warn_until_human_confirmation() -> None:
    governed = dr.govern_verdict("block", detector_kind="vlm")
    assert governed["verdict"] == "warn"
    assert governed["human_confirmation_required"] is True

    confirmed = dr.govern_verdict("block", detector_kind="vlm", human_confirmed=True)
    assert confirmed["verdict"] == "block"


def test_numeric_detector_needs_production_calibration_to_auto_block() -> None:
    exploratory = dr.govern_verdict("block", detector_kind="numeric", calibration={
        "evidence_status": "calibrated", "auto_block_eligible": False,
    })
    production = dr.govern_verdict("block", detector_kind="numeric", calibration={
        "evidence_status": "production_calibrated", "auto_block_eligible": True,
    })
    assert exploratory["verdict"] == "warn"
    assert production["verdict"] == "block"


def test_deterministic_contract_keeps_load_bearing_block() -> None:
    governed = dr.govern_verdict("block", detector_kind="contract")
    assert governed["verdict"] == "block"
    assert governed["auto_block_eligible"] is True

