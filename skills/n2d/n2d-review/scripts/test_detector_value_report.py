from __future__ import annotations

import json
from pathlib import Path

import detector_value_report as value


def test_classification_understands_production_review_labels() -> None:
    assert value.classification({"label": "true_positive"}) == (True, True)
    assert value.classification({"label": "false_positive"}) == (True, False)
    assert value.classification({"label": "missed_by_machine"}) == (False, True)
    assert value.classification({"prediction": "block", "ground_truth": "clean"}) == (True, False)


def test_value_report_promotes_only_high_precision_recall_positive_utility(tmp_path: Path) -> None:
    rows = []
    rows.extend({"detector": "face", "dimension": "脸(G1)", "label": "true_positive"} for _ in range(18))
    rows.extend({"detector": "face", "dimension": "脸(G1)", "label": "false_negative"} for _ in range(2))
    rows.extend({"detector": "face", "dimension": "脸(G1)", "label": "true_negative"} for _ in range(19))
    rows.append({"detector": "face", "dimension": "脸(G1)", "label": "false_positive"})
    path = tmp_path / "生产数据" / "consistency_calibration.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    report = value.build_report(tmp_path)
    row = report["rows"][0]
    assert row["precision"] >= 0.9
    assert row["recall"] >= 0.8
    assert row["auto_block_eligible"] is True
    assert row["recommendation"] == "auto_block_eligible"


def test_noisy_detector_becomes_retire_candidate_not_auto_deleted() -> None:
    result = value.summarize_counts({"tp": 0, "fp": 12, "fn": 10, "tn": 8})
    assert result["recommendation"] == "retire_candidate"
    assert result["auto_block_eligible"] is False
