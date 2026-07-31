from __future__ import annotations

import json
from pathlib import Path

import calibrate_thresholds


def test_lower_is_match_threshold_separates_gold_labels(tmp_path: Path) -> None:
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps({"metrics": {"ccip_difference": {
        "direction": "lower_is_match",
        "samples": [
            {"value": 0.10, "label": "same"},
            {"value": 0.14, "label": "same"},
            {"value": 0.28, "label": "different"},
            {"value": 0.35, "label": "different"},
        ],
    }}}), encoding="utf-8")
    registry = calibrate_thresholds.build_registry(gold, min_positive=2, min_negative=2)
    row = registry["metrics"]["ccip_difference"]
    assert row["status"] == "validated"
    assert 0.14 <= row["threshold"] < 0.28
    assert row["enforcement"] == "warn_only"


def test_small_gold_set_stays_draft() -> None:
    row = calibrate_thresholds.calibrate_metric({
        "direction": "higher_is_match",
        "samples": [{"value": 0.9, "label": "same"}, {"value": 0.2, "label": "different"}],
    })
    assert row["status"] == "draft"
