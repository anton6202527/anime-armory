"""calibrate_thresholds 金标 floor 反推单测（FCB 多识别器投票）。
cd skills/n2d-review/scripts && python -m pytest test_calibrate_thresholds.py
"""
import json
import os

import calibrate_thresholds as ct


def test_agg_score_median_of_recognizers():
    assert ct._agg_score({"scores": {"arcface": 0.8, "facenet": 0.7, "sface": 0.9}}) == 0.8
    assert ct._agg_score({"similarity": 0.66}) == 0.66
    assert ct._agg_score({}) is None


def test_derive_floor_separable_midpoint():
    res = ct.derive_floor([0.8, 0.85, 0.9], [0.4, 0.5])
    assert res["status"] == "separable"
    assert res["recommended_floor"] == round((0.5 + 0.8) / 2, 3)
    assert res["margin"] == round(0.8 - 0.5, 3)
    assert res["confusion"] == {"tp": 3, "fn": 0, "fp": 0, "tn": 2}
    assert res["calibration_tier"] == "exploratory"
    assert res["auto_block_eligible"] is False


def test_derive_floor_insufficient_samples():
    assert ct.derive_floor([0.9], [0.3])["status"] == "insufficient_samples"


def test_derive_floor_overlap_uses_youden():
    res = ct.derive_floor([0.6, 0.7, 0.8, 0.9], [0.5, 0.65, 0.72])
    assert res["status"] == "overlap"
    assert res["separable"] is False
    assert 0.0 <= res["recommended_floor"] <= 1.0
    assert "balanced_accuracy" in res and "sensitivity_ci95" in res


def test_derive_floor_only_enables_auto_block_with_production_sized_golden_set():
    res = ct.derive_floor([0.8 + i / 1000 for i in range(20)], [0.2 + i / 1000 for i in range(20)])
    assert res["calibration_tier"] == "production"
    assert res["auto_block_eligible"] is True


def test_build_calibration_groups_by_backend_style(tmp_path):
    rows = [
        {"dimension": "脸(G1)", "backend": "seedance", "style": "default", "label": "pass", "scores": {"arcface": 0.82, "sface": 0.80}},
        {"dimension": "脸(G1)", "backend": "seedance", "style": "default", "label": "pass", "scores": {"arcface": 0.88, "sface": 0.86}},
        {"dimension": "脸(G1)", "backend": "seedance", "style": "default", "label": "pass", "scores": {"arcface": 0.84, "sface": 0.83}},
        {"dimension": "脸(G1)", "backend": "seedance", "style": "default", "label": "fail", "scores": {"arcface": 0.45, "sface": 0.50}},
        {"dimension": "脸(G1)", "backend": "seedance", "style": "default", "label": "fail", "scores": {"arcface": 0.55, "sface": 0.52}},
    ]
    path = tmp_path / "生产数据" / "consistency_golden_set.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    payload = ct.build_calibration(str(tmp_path))
    assert payload["kind"] == "n2d_consistency_threshold_calibration"
    assert len(payload["calibrations"]) == 1
    cal = payload["calibrations"][0]
    assert cal["dimension"] == "脸(G1)" and cal["backend"] == "seedance"
    assert cal["status"] == "separable" and 0.5 < cal["recommended_floor"] < 0.8
    assert set(cal["recognizers"]) == {"arcface", "sface"}

    out = ct.write_calibration(str(tmp_path))
    assert os.path.basename(out) == "consistency_threshold_calibration.json"
    assert json.loads(open(out, encoding="utf-8").read())["calibrations"][0]["dimension"] == "脸(G1)"
