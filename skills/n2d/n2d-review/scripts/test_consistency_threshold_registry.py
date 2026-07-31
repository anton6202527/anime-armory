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
    assert row["enforcement"]["auto_block_eligible"] is False


def test_write_registry_outputs_machine_readable_file(tmp_path: Path) -> None:
    path = reg.write_registry(str(tmp_path))
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["kind"] == reg.KIND
    assert data["rows"]
    assert len(data["rows"]) >= 12
    assert {"state_pixel_presence", "seam_continuity", "lip_sync", "audio_sync"} <= {row["dimension"] for row in data["rows"]}


# ── P4：后端 floor 单调性/连贯校验（掣肘四：缺单调校验，放松无人察觉）──

def test_coherence_flags_unbacked_backend_loosening():
    import consistency_threshold_registry as r
    rows = [
        {"dimension": "character_consistency", "stage": "image", "backend": "any",
         "threshold_floor": 0.60, "evidence_status": "default_policy_only"},
        {"dimension": "character_consistency", "stage": "image", "backend": "seedance",
         "threshold_floor": 0.40, "evidence_status": "recommendation_only"},
    ]
    issues = r.coherence_issues(rows)
    assert any(i["backend"] == "seedance" and i["severity"] == "block" for i in issues)


def test_coherence_allows_calibrated_loosening_as_warn():
    import consistency_threshold_registry as r
    rows = [
        {"dimension": "outfit_consistency", "stage": "image", "backend": "any",
         "threshold_floor": 0.60, "evidence_status": "default_policy_only"},
        {"dimension": "outfit_consistency", "stage": "image", "backend": "kling",
         "threshold_floor": 0.50, "evidence_status": "calibrated"},
    ]
    issues = r.coherence_issues(rows)
    assert any(i["backend"] == "kling" and i["severity"] == "warn" for i in issues)


def test_coherence_clean_when_backend_tighter_or_equal():
    import consistency_threshold_registry as r
    rows = [
        {"dimension": "style_consistency", "stage": "image", "backend": "any",
         "threshold_floor": 0.50, "evidence_status": "default_policy_only"},
        {"dimension": "style_consistency", "stage": "image", "backend": "veo",
         "threshold_floor": 0.55, "evidence_status": "recommendation_only"},
    ]
    assert r.coherence_issues(rows) == []
