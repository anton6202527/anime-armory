import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feedback_ingest import build, wilson


def test_wilson_and_qualified_winner():
    report = build([
        {"variant_id": "A", "impressions": 5000, "clicks": 500, "conversions": 50, "spend": 100, "revenue": 300},
        {"variant_id": "B", "impressions": 5000, "clicks": 100, "conversions": 10, "spend": 100, "revenue": 80},
    ], min_impressions=1000)
    assert report["verdict"] == "qualified_winner"
    assert report["winner"] == "A"
    assert wilson(0, 0) == [0.0, 0.0]


def test_small_sample_is_directional_only():
    report = build([{"variant_id": "A", "impressions": 20, "clicks": 10}], min_impressions=1000)
    assert report["verdict"] == "insufficient_data"


def test_cross_platform_variants_are_not_declared_winner():
    report = build([
        {"variant_id": "A", "platform": "抖音", "audience": "new", "impressions": 5000, "clicks": 800},
        {"variant_id": "B", "platform": "小红书", "audience": "new", "impressions": 5000, "clicks": 100},
    ], min_impressions=1000)
    assert report["winner"] is None
    assert any(f["code"] == "non_comparable_strata" for f in report["findings"])


def test_components_and_fatigue_are_landed():
    report = build([
        {"variant_id": "A", "hook_id": "H1", "message_id": "M1", "cta_id": "C1", "date": "2026-07-01",
         "impressions": 2000, "clicks": 200, "spend": 100, "revenue": 400, "frequency": 1.0},
        {"variant_id": "A", "hook_id": "H1", "message_id": "M1", "cta_id": "C1", "date": "2026-07-08",
         "impressions": 2000, "clicks": 100, "spend": 100, "revenue": 200, "frequency": 2.0},
    ], min_impressions=1000)
    assert report["components"]["hook_id"][0]["id"] == "H1"
    assert any(f["code"] == "creative_fatigue" for f in report["findings"])


def test_roas_aggregate_never_claims_significance_without_variance():
    report = build([
        {"variant_id": "A", "impressions": 5000, "clicks": 500, "spend": 100, "revenue": 500},
        {"variant_id": "B", "impressions": 5000, "clicks": 400, "spend": 100, "revenue": 200},
    ], min_impressions=1000, measurement={"primary_kpi": "ROAS"})
    assert report["winner"] is None
    assert any(f["code"] == "aggregate_metric_no_interval" for f in report["findings"])


def test_unregistered_experiment_never_announces_winner():
    report = build([
        {"variant_id": "A", "impressions": 5000, "clicks": 500},
        {"variant_id": "B", "impressions": 5000, "clicks": 100},
    ], min_impressions=1000, experiment_validation={})
    assert report["winner"] is None
    assert report["verdict"] == "directional_only"
    assert report["summary"]["block"] == 1
    assert any(f["code"] == "experiment_not_preregistered" for f in report["findings"])


def test_data_must_match_registered_variants_and_strata():
    validation = {"summary": {"approved": True}, "plan": {
        "primary_kpi": "CTR", "platform": "TikTok", "audience": "prospecting",
        "variants": [{"variant_id": "A"}, {"variant_id": "B"}],
    }}
    report = build([
        {"variant_id": "A", "platform": "TikTok", "audience": "prospecting", "impressions": 5000, "clicks": 500},
        {"variant_id": "C", "platform": "Meta", "audience": "prospecting", "impressions": 5000, "clicks": 100},
    ], min_impressions=1000, measurement={"primary_kpi": "CTR"}, experiment_validation=validation)
    assert report["winner"] is None
    assert any(f["code"] == "unregistered_variant" for f in report["findings"])
    assert any(f["code"] == "platform_drift" for f in report["findings"])
