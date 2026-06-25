from __future__ import annotations

import json
from pathlib import Path

import consistency_threshold_registry as reg


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_build_registry_merges_calibration_and_recommendations(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "consistency_threshold_calibration.json").write_text(
        json.dumps(
            {
                "kind": "n2d_consistency_threshold_calibration",
                "calibrations": [
                    {
                        "dimension": "脸(G1)",
                        "backend": "seedance",
                        "style": "国漫写实",
                        "status": "separable",
                        "recommended_floor": 0.72,
                        "pass_n": 4,
                        "fail_n": 2,
                        "recognizers": ["arcface", "sface"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (prod / "consistency_threshold_recommendations.json").write_text(
        json.dumps(
            {
                "kind": "n2d_consistency_threshold_recommendations",
                "recommendations": [
                    {
                        "dimension": "脸(G1)",
                        "direction": "loosen_threshold_or_add_exemption",
                        "counts": {"false_positive": 2},
                        "suggested_action": "侧脸误报豁免",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = reg.build_registry(str(tmp_path))

    row = next(r for r in payload["rows"] if r["dimension"] == "脸(G1)")
    assert row["threshold_floor"] == 0.72
    assert row["evidence_status"] == "calibrated"
    assert row["production_escalation"]["direction"] == "loosen_threshold_or_add_exemption"


def test_write_registry_outputs_machine_readable_file(tmp_path: Path) -> None:
    path = reg.write_registry(str(tmp_path))
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["kind"] == reg.KIND
    assert data["rows"]
