from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("calibration.py")
spec = importlib.util.spec_from_file_location("calibration", SCRIPT)
calibration = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(calibration)


def _write_cases(root: Path) -> None:
    pdir = root / "生产数据"
    pdir.mkdir()
    (pdir / "review_calibration_cases.json").write_text(
        json.dumps({
            "kind": "n2d_review_calibration_cases",
            "cases": [
                {"case_id": "A", "dimension": "character_consistency", "gold_label": "block"},
                {"case_id": "B", "dimension": "scene_continuity", "gold_label": "pass"},
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_votes(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["case_id", "reviewer", "label"])
        writer.writeheader()
        writer.writerows(rows)


def test_calibration_passes_when_reviewers_match_gold(tmp_path: Path) -> None:
    _write_cases(tmp_path)
    votes = tmp_path / "votes.csv"
    _write_votes(votes, [
        {"case_id": "A", "reviewer": "r1", "label": "block"},
        {"case_id": "B", "reviewer": "r1", "label": "pass"},
        {"case_id": "A", "reviewer": "r2", "label": "block"},
        {"case_id": "B", "reviewer": "r2", "label": "pass"},
    ])

    payload = calibration.score_votes(str(tmp_path), votes)
    calibration.write_report(str(tmp_path), payload)

    assert payload["status"] == "pass"
    assert all(row["accuracy"] == 1.0 for row in payload["reviewers"])
    assert (tmp_path / "生产数据" / "review_calibration.json").is_file()


def test_calibration_flags_disagreement(tmp_path: Path) -> None:
    _write_cases(tmp_path)
    votes = tmp_path / "votes.csv"
    _write_votes(votes, [
        {"case_id": "A", "reviewer": "r1", "label": "block"},
        {"case_id": "A", "reviewer": "r2", "label": "pass"},
    ])

    payload = calibration.score_votes(str(tmp_path), votes)

    assert payload["status"] == "needs_calibration"
    assert payload["disagreements"][0]["case_id"] == "A"
