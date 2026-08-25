from pathlib import Path
import json
from detector_value_report import build_report, summarize


def test_requires_repair_yield_before_auto_block():
    weak = summarize({"tp": 20, "fp": 0, "fn": 0, "tn": 20, "repairs": 10, "successful_repairs": 2})
    strong = summarize({"tp": 20, "fp": 0, "fn": 0, "tn": 20, "repairs": 10, "successful_repairs": 9})
    assert not weak["auto_block_eligible"]
    assert strong["auto_block_eligible"]


def test_stratifies_genre_and_craft(tmp_path: Path):
    source = tmp_path / "生产数据" / "review_calibration.jsonl"; source.parent.mkdir(parents=True)
    rows = [{"detector": "bubble", "genre": "romance", "craft_profile": "webtoon", "review_label": "true_positive", "repair_attempted": True, "repair_succeeded": True}]
    source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    report = build_report(tmp_path)
    assert report["rows"][0]["genre"] == "romance"
    assert report["rows"][0]["repair_yield"] == 1.0
