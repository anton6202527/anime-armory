from __future__ import annotations

import json
from pathlib import Path

import detector_value_report as d


def test_high_quality_detector_needs_accepted_repair_yield_for_blocking(tmp_path: Path) -> None:
    rows = []
    rows.extend({"detector": "timeline", "dimension": "timeline", "label": "true_positive", "repair_status": "fixed", "craft_profile": "commercial", "genre": "fantasy"} for _ in range(9))
    rows.append({"detector": "timeline", "dimension": "timeline", "label": "false_negative", "repair_status": "failed", "craft_profile": "commercial", "genre": "fantasy"})
    rows.extend({"detector": "timeline", "dimension": "timeline", "label": "true_negative", "craft_profile": "commercial", "genre": "fantasy"} for _ in range(9))
    rows.append({"detector": "timeline", "dimension": "timeline", "label": "false_positive", "craft_profile": "commercial", "genre": "fantasy"})
    path = tmp_path / "生产数据/review_calibration.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = d.build_report(tmp_path)
    row = report["rows"][0]
    assert row["precision"] == 0.9
    assert row["recall"] == 0.9
    assert row["repair_yield"] == 0.9
    assert row["recommendation"] == "auto_block_eligible"


def test_noisy_detector_is_only_a_retire_candidate() -> None:
    result = d.summarize({"tp": 0, "fp": 12, "fn": 10, "tn": 8, "repair_attempts": 8, "repair_accepted": 0})
    assert result["recommendation"] == "retire_candidate_advisory_only"
    assert result["auto_block_eligible"] is False
