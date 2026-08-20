import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_plan as ep
from _test_readiness_fixture import write_formal_readiness
from feedback_ingest import build, main, two_proportion_score_test, wilson


def _local_plan(**updates):
    plan = {
        "design_mode": "local_binomial", "hypothesis": "hook 提升 CTR",
        "primary_kpi": "CTR", "conversion_event": "purchase", "attribution_window": "7d_click",
        "metric_definition": {"numerator": "clicks", "denominator": "impressions"},
        "baseline_rate": 0.05, "minimum_detectable_effect": 0.05, "alpha": 0.05, "power": 0.8,
        "multiple_comparison_method": "none",
        "stopping_rule": {"type": "fixed_sample", "minimum_sample_per_arm": "computed",
                          "no_early_stopping": True},
        "platform": "TikTok", "placement": "auction_in_feed", "audience": "prospecting",
        "randomization_unit": "impression", "analysis_unit": "impression", "independent_bernoulli": True,
        "decision_rule": "multiplicity-adjusted pooled two-proportion score test",
        "start_date": "2026-07-01", "end_date": "2026-07-31", "min_impressions": 100,
        "held_constant": {"budget": "50/50", "bidding": "same", "landing_page": "same",
                          "placement": "auction_in_feed"},
        "variants": [
            {"variant_id": "A", "hook_id": "H1", "message_id": "M1", "cta_id": "C1", "allocation": 0.5,
             "asset_path": "A.mp4", "asset_sha256": "a" * 64},
            {"variant_id": "B", "hook_id": "H2", "message_id": "M1", "cta_id": "C1", "allocation": 0.5,
             "asset_path": "B.mp4", "asset_sha256": "b" * 64},
        ],
    }
    plan.update(updates)
    return plan


def _bind_assets(plan, root):
    plan = copy.deepcopy(plan)
    for variant in plan["variants"]:
        path = root / "variants" / f"{variant['variant_id']}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((f"asset-{variant['variant_id']}" * 20).encode())
        variant["asset_path"] = str(path.relative_to(root))
        variant["asset_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    platform = plan.get("platform_experiment") if isinstance(plan.get("platform_experiment"), dict) else None
    if platform:
        receipt = platform["config_receipt"]
        evidence = root / "投放反馈" / "config-export.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text("platform config\n", encoding="utf-8")
        receipt["evidence_path"] = str(evidence.relative_to(root))
        receipt["evidence_sha256"] = hashlib.sha256(evidence.read_bytes()).hexdigest()
        receipt["asset_bindings"] = {v["variant_id"]: v["asset_sha256"] for v in plan["variants"]}
    return plan


def _write_readiness(root):
    write_formal_readiness(root, "CTR")


def _validation(root, plan=None):
    plan = _bind_assets(plan or _local_plan(), root)
    _write_readiness(root)
    payload = ep.build(plan, root)
    assert payload["summary"]["approved"] is True
    feedback = root / "投放反馈"
    feedback.mkdir(parents=True, exist_ok=True)
    (feedback / "experiment_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    (feedback / "experiment_plan_validation.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def _rows(a_clicks=500, b_clicks=100, impressions=5000):
    common = {"platform": "TikTok", "placement": "auction_in_feed", "audience": "prospecting"}
    return [
        {"variant_id": "A", "impressions": impressions, "clicks": a_clicks, "conversions": min(50, a_clicks),
         "spend": 100, "revenue": 300, **common},
        {"variant_id": "B", "impressions": impressions, "clicks": b_clicks, "conversions": min(10, b_clicks),
         "spend": 100, "revenue": 80, **common},
    ]


def test_wilson_and_local_qualified_winner_requires_power_plan(tmp_path):
    report = build([
        *_rows()
    ], min_impressions=10_000, measurement={"primary_kpi": "CTR"},
       experiment_validation=_validation(tmp_path), root=tmp_path)
    assert report["verdict"] == "local_qualified_winner"
    assert report["winner"] == "A"
    assert report["variants"][0]["sample_qualified"] is False  # diagnostic screen, not power
    assert report["local_inference"]["stopping_satisfied"] is True
    assert report["local_inference"]["effective_stopping_sample_per_arm"] != report["min_impressions"]
    assert wilson(0, 0) == [0.0, 0.0]


def test_small_sample_is_directional_only(tmp_path):
    rows = _rows(a_clicks=10, b_clicks=2, impressions=20)
    report = build(rows, min_impressions=10, measurement={"primary_kpi": "CTR"},
                   experiment_validation=_validation(tmp_path), root=tmp_path)
    assert report["verdict"] == "directional_only"
    assert report["winner"] is None
    assert report["analysis_status"] == "interim"
    assert report["local_inference"]["stopping_satisfied"] is False
    assert any(f["code"] == "stopping_rule_not_satisfied" for f in report["findings"])


def test_cross_platform_variants_are_not_declared_winner(tmp_path):
    report = build([
        {"variant_id": "A", "platform": "抖音", "audience": "new", "impressions": 5000, "clicks": 800},
        {"variant_id": "B", "platform": "小红书", "audience": "new", "impressions": 5000, "clicks": 100},
    ], min_impressions=1000, experiment_validation=_validation(tmp_path), root=tmp_path)
    assert report["winner"] is None
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "non_comparable_strata" for f in report["findings"])


def test_missing_registered_arm_stays_interim(tmp_path):
    report = build([
        _rows(a_clicks=500, impressions=5000)[0],
    ], measurement={"primary_kpi": "CTR"},
       experiment_validation=_validation(tmp_path), root=tmp_path)
    assert report["winner"] is None
    assert report["analysis_status"] == "interim"
    assert report["local_inference"]["sample_condition"] is False
    assert any(f["code"] == "registered_variant_missing_data" for f in report["findings"])


def test_components_and_fatigue_are_landed():
    report = build([
        {"variant_id": "A", "hook_id": "H1", "message_id": "M1", "cta_id": "C1", "date": "2026-07-01",
         "impressions": 2000, "clicks": 200, "spend": 100, "revenue": 400, "frequency": 1.0},
        {"variant_id": "A", "hook_id": "H1", "message_id": "M1", "cta_id": "C1", "date": "2026-07-08",
         "impressions": 2000, "clicks": 100, "spend": 100, "revenue": 200, "frequency": 2.0},
    ], min_impressions=1000, experiment_validation={})
    assert report["components"]["hook_id"][0]["id"] == "H1"
    assert any(f["code"] == "creative_fatigue" for f in report["findings"])


def test_roas_aggregate_never_claims_significance_without_variance():
    report = build([
        {"variant_id": "A", "impressions": 5000, "clicks": 500, "spend": 100, "revenue": 500},
        {"variant_id": "B", "impressions": 5000, "clicks": 400, "spend": 100, "revenue": 200},
    ], min_impressions=1000, measurement={"primary_kpi": "ROAS"}, experiment_validation={})
    assert report["winner"] is None
    assert any(f["code"] == "aggregate_metric_no_interval" for f in report["findings"])


def test_unregistered_experiment_never_announces_winner():
    report = build([
        {"variant_id": "A", "impressions": 5000, "clicks": 500},
        {"variant_id": "B", "impressions": 5000, "clicks": 100},
    ], min_impressions=1000, experiment_validation={})
    assert report["winner"] is None
    assert report["verdict"] == "directional_only"
    assert report["summary"]["block"] >= 1
    assert any(f["code"] == "experiment_not_preregistered" for f in report["findings"])


def test_data_must_match_registered_variants_and_strata(tmp_path):
    validation = _validation(tmp_path)
    report = build([
        {"variant_id": "A", "platform": "TikTok", "audience": "prospecting", "impressions": 5000, "clicks": 500},
        {"variant_id": "C", "platform": "Meta", "audience": "prospecting", "impressions": 5000, "clicks": 100},
    ], min_impressions=1000, measurement={"primary_kpi": "CTR"},
       experiment_validation=validation, root=tmp_path)
    assert report["winner"] is None
    assert any(f["code"] == "unregistered_variant" for f in report["findings"])
    assert any(f["code"] == "platform_drift" for f in report["findings"])


def test_hook_rate_floor_flags_failing_hook_only_with_data():
    report = build([
        {"variant_id": "A", "hook_id": "H1", "impressions": 5000, "clicks": 200, "video_3s": 800},
        {"variant_id": "B", "hook_id": "H2", "impressions": 5000, "clicks": 150, "video_3s": 2500},
    ], min_impressions=1000, experiment_validation={})
    hits = [f for f in report["findings"] if f["code"] == "hook_rate_low"]
    assert [f["variant_id"] for f in hits] == ["A"]  # A=16% < 25%；B=50% 达标
    assert hits[0]["severity"] == "warn"

    # video_3s 全 0 = 数据源没带该字段，不判（不臆造 hook 失败）
    report2 = build([
        {"variant_id": "A", "impressions": 5000, "clicks": 200},
    ], min_impressions=1000, experiment_validation={})
    assert not [f for f in report2["findings"] if f["code"] == "hook_rate_low"]

    # 样本不合格（曝光不足）不判
    report3 = build([
        {"variant_id": "A", "impressions": 200, "clicks": 20, "video_3s": 10},
    ], min_impressions=1000, experiment_validation={})
    assert not [f for f in report3["findings"] if f["code"] == "hook_rate_low"]


def test_fixed_horizon_requires_data_through_preregistered_end_date(tmp_path):
    plan = _local_plan(stopping_rule={"type": "fixed_horizon", "minimum_sample_per_arm": "computed",
                                      "no_early_stopping": True,
                                      "require_observed_through_end_date": True})
    validation = _validation(tmp_path, plan)
    before_end = [{**row, "date": "2026-07-20"} for row in _rows()]
    report = build(before_end, measurement={"primary_kpi": "CTR"}, experiment_validation=validation, root=tmp_path)
    assert report["verdict"] == "directional_only"
    assert report["local_inference"]["calendar_condition"] is False
    through_end = [{**row, "date": "2026-07-31"} for row in _rows()]
    report = build(through_end, measurement={"primary_kpi": "CTR"}, experiment_validation=validation, root=tmp_path)
    assert report["verdict"] == "local_qualified_winner"


def _platform_validation(root):
    plan = _local_plan(design_mode="platform_native")
    for key in ("metric_definition", "baseline_rate", "minimum_detectable_effect", "alpha", "power",
                "multiple_comparison_method", "stopping_rule"):
        plan.pop(key)
    plan["platform_experiment"] = {
        "experiment_id": "exp-42",
        "config_receipt": {
            "experiment_id": "exp-42", "status": "configured",
            "evidence_path": "投放反馈/config-export.json", "evidence_sha256": "c" * 64,
            "asset_bindings": {"A": "a" * 64, "B": "b" * 64},
        },
    }
    plan = _bind_assets(plan, root)
    _write_readiness(root)
    validation = ep.build(plan, root)
    assert validation["summary"]["approved"] is True
    feedback = root / "投放反馈"
    feedback.mkdir(parents=True, exist_ok=True)
    (feedback / "experiment_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    (feedback / "experiment_plan_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False), encoding="utf-8")
    return validation


def test_platform_native_result_receipt_takes_precedence(tmp_path):
    evidence = tmp_path / "platform-result.json"
    evidence.write_text("platform says B won\n", encoding="utf-8")
    validation = _platform_validation(tmp_path)
    bindings = {v["variant_id"]: v["asset_sha256"] for v in validation["plan"]["variants"]}
    receipt = {
        "experiment_id": "exp-42", "status": "completed", "primary_kpi": "CTR",
        "conclusion": "winner", "winner_variant_id": "B",
        "asset_bindings": bindings,
        "evidence_path": evidence.name,
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }
    receipt_path = tmp_path / "投放反馈" / "platform_experiment_result.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    validation["platform_result_receipt"] = receipt
    validation["platform_result_source"] = {
        "path": str(receipt_path.relative_to(tmp_path)),
        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    }
    # Local aggregate strongly favours A; the verified native receipt remains authoritative.
    report = build(_rows(), measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["verdict"] == "platform_qualified_winner"
    assert report["winner"] == "B"
    assert report["platform_inference"]["verified"] is True
    assert report["analysis_status"] == "complete"


def test_platform_receipt_with_stale_asset_binding_fails_closed(tmp_path):
    evidence = tmp_path / "platform-result.json"
    evidence.write_text("result\n", encoding="utf-8")
    validation = _platform_validation(tmp_path)
    bindings = {v["variant_id"]: v["asset_sha256"] for v in validation["plan"]["variants"]}
    stale_bindings = dict(bindings)
    stale_bindings["B"] = "d" * 64
    receipt = {
        "experiment_id": "exp-42", "status": "completed", "primary_kpi": "CTR",
        "conclusion": "winner", "winner_variant_id": "B",
        "asset_bindings": stale_bindings,
        "evidence_path": evidence.name,
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }
    receipt_path = tmp_path / "投放反馈" / "platform_experiment_result.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    validation["platform_result_receipt"] = receipt
    validation["platform_result_source"] = {
        "path": str(receipt_path.relative_to(tmp_path)),
        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    }
    report = build(_rows(), measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["verdict"] == "directional_only"
    assert report["winner"] is None
    assert any(f["code"] == "platform_result_asset_binding_mismatch" for f in report["findings"])


def test_legacy_approved_shape_without_design_mode_is_diagnostic_only():
    legacy = {"summary": {"approved": True}, "plan": {
        "primary_kpi": "CTR", "platform": "TikTok", "placement": "auction_in_feed",
        "audience": "prospecting", "variants": [{"variant_id": "A"}, {"variant_id": "B"}],
    }}
    report = build(_rows(), measurement={"primary_kpi": "CTR"}, experiment_validation=legacy)
    assert report["verdict"] == "directional_only"
    assert report["winner"] is None
    assert any(f["code"] == "experiment_design_mode_invalid" for f in report["findings"])


def test_strict_binomial_counts_fail_closed(tmp_path):
    validation = _validation(tmp_path)
    invalid_values = ["not-a-number", float("nan"), float("inf"), -1, 1.5]
    for value in invalid_values:
        rows = _rows()
        rows[1]["clicks"] = value
        report = build(rows, measurement={"primary_kpi": "CTR"},
                       experiment_validation=validation, root=tmp_path)
        assert report["winner"] is None
        assert report["analysis_status"] == "invalid"
        assert any(f["code"] == "binomial_count_invalid" for f in report["findings"])

    hierarchy = _rows()
    hierarchy[1]["clicks"] = hierarchy[1]["impressions"] + 1
    report = build(hierarchy, measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "binomial_hierarchy_invalid" for f in report["findings"])


def test_feedback_rechecks_current_variant_asset_sha(tmp_path):
    validation = _validation(tmp_path)
    asset = tmp_path / validation["plan"]["variants"][1]["asset_path"]
    asset.write_bytes(b"mutated-after-registration")
    report = build(_rows(), measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["winner"] is None
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "variant_asset_binding_stale" for f in report["findings"])


def test_feedback_rechecks_campaign_readiness_and_current_brief(tmp_path):
    validation = _validation(tmp_path)
    brief = tmp_path / "需求" / "brief.json"
    brief.write_text(json.dumps({"campaign_mode": "formal", "changed": True}), encoding="utf-8")
    report = build(_rows(), measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["winner"] is None
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "campaign_readiness_stale" for f in report["findings"])


def test_feedback_detects_within_variant_strata_drift(tmp_path):
    validation = _validation(tmp_path)
    rows = [
        {**_rows()[0], "platform": "Meta", "impressions": 2500, "clicks": 250},
        {**_rows()[0], "platform": "TikTok", "impressions": 2500, "clicks": 250},
        _rows()[1],
    ]
    report = build(rows, measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["winner"] is None
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "within_variant_platform_drift" for f in report["findings"])


def test_platform_config_and_result_evidence_are_rechecked(tmp_path):
    validation = _platform_validation(tmp_path)
    bindings = {v["variant_id"]: v["asset_sha256"] for v in validation["plan"]["variants"]}
    evidence = tmp_path / "投放反馈" / "result-export.json"
    evidence.write_text("winner B\n", encoding="utf-8")
    receipt = {
        "experiment_id": "exp-42", "status": "completed", "primary_kpi": "CTR",
        "conclusion": "winner", "winner_variant_id": "B", "asset_bindings": bindings,
        "evidence_path": str(evidence.relative_to(tmp_path)),
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }
    receipt_path = tmp_path / "投放反馈" / "platform_experiment_result.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    validation["platform_result_receipt"] = receipt
    validation["platform_result_source"] = {
        "path": str(receipt_path.relative_to(tmp_path)),
        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    }

    config_path = tmp_path / validation["plan"]["platform_experiment"]["config_receipt"]["evidence_path"]
    config_path.write_text("changed config\n", encoding="utf-8")
    report = build(_rows(), measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["analysis_status"] == "invalid"
    assert report["winner"] is None
    assert any(f["code"] == "platform_config_evidence_binding_stale" for f in report["findings"])

    # Restore config and mutate the exported result evidence instead.
    config_path.write_text("platform config\n", encoding="utf-8")
    evidence.write_text("changed result\n", encoding="utf-8")
    report = build(_rows(), measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "platform_result_evidence_stale" for f in report["findings"])

    receipt["evidence_path"] = "../outside.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    validation["platform_result_receipt"] = receipt
    validation["platform_result_source"]["sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    report = build(_rows(), measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "platform_result_evidence_stale" for f in report["findings"])


def test_score_test_is_decision_rule_and_wilson_is_display_only(tmp_path):
    validation = _validation(tmp_path)
    report = build(_rows(), measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["local_inference"]["decision_test"] == "pooled_two_proportion_score_test"
    assert report["local_inference"]["interval_role"] == "display_only_not_decision_rule"
    assert report["local_inference"]["all_required_pairwise_significant"] is True
    direct = two_proportion_score_test(500, 5000, 100, 5000)
    assert direct["p_value"] < 0.05


def test_multi_arm_bonferroni_score_family(tmp_path):
    plan = _local_plan()
    plan["multiple_comparison_method"] = "bonferroni"
    plan["variants"] = [
        {**plan["variants"][0], "allocation": 1 / 3},
        {**plan["variants"][1], "allocation": 1 / 3},
        {**plan["variants"][1], "variant_id": "C", "hook_id": "H3", "asset_path": "C.mp4",
         "asset_sha256": "c" * 64, "allocation": 1 / 3},
    ]
    validation = _validation(tmp_path, plan)
    common = {"platform": "TikTok", "placement": "auction_in_feed", "audience": "prospecting",
              "impressions": 5000}
    report = build([
        {"variant_id": "A", "clicks": 750, **common},
        {"variant_id": "B", "clicks": 250, **common},
        {"variant_id": "C", "clicks": 100, **common},
    ], measurement={"primary_kpi": "CTR"}, experiment_validation=validation, root=tmp_path)
    assert report["verdict"] == "local_qualified_winner"
    assert report["winner"] == "A"
    assert len(report["local_inference"]["pairwise_tests"]) == 3
    assert all(row["adjusted_p_value"] is not None for row in report["local_inference"]["pairwise_tests"])


def test_feedback_rejects_tampered_multi_arm_multiplicity(tmp_path):
    plan = _local_plan()
    plan["multiple_comparison_method"] = "bonferroni"
    plan["variants"] = [
        {**plan["variants"][0], "allocation": 1 / 3},
        {**plan["variants"][1], "allocation": 1 / 3},
        {**plan["variants"][1], "variant_id": "C", "hook_id": "H3", "asset_path": "C.mp4",
         "asset_sha256": "c" * 64, "allocation": 1 / 3},
    ]
    validation = _validation(tmp_path, plan)
    validation["power_analysis"]["comparison_count"] = 1
    validation["power_analysis"]["multiple_comparison_method"] = "none"
    common = {"platform": "TikTok", "placement": "auction_in_feed", "audience": "prospecting",
              "impressions": 5000}
    report = build([
        {"variant_id": "A", "clicks": 750, **common},
        {"variant_id": "B", "clicks": 250, **common},
        {"variant_id": "C", "clicks": 100, **common},
    ], measurement={"primary_kpi": "CTR"}, experiment_validation=validation, root=tmp_path)
    assert report["winner"] is None
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "experiment_validation_source_mismatch" for f in report["findings"])


def test_feedback_rejects_tampered_derived_power_target(tmp_path):
    validation = _validation(tmp_path)
    validation["power_analysis"]["required_sample_per_arm"] = 1
    validation["power_analysis"]["effective_stopping_sample_per_arm"] = 1
    validation["power_analysis"]["effective_stopping_sample_by_arm"] = {"A": 1, "B": 1}
    report = build(_rows(a_clicks=10, b_clicks=2, impressions=20),
                   measurement={"primary_kpi": "CTR"},
                   experiment_validation=validation, root=tmp_path)
    assert report["winner"] is None
    assert report["analysis_status"] == "invalid"
    assert any(f["code"] == "experiment_validation_source_mismatch" for f in report["findings"])
    assert report["local_inference"]["effective_stopping_sample_per_arm"] > 1


def test_cvr_uses_clicks_as_power_denominator_and_analysis_unit(tmp_path):
    plan = _local_plan(
        primary_kpi="CVR",
        metric_definition={"numerator": "conversions", "denominator": "clicks"},
        randomization_unit="click", analysis_unit="click", independent_bernoulli=True,
    )
    validation = _validation(tmp_path, plan)
    common = {"platform": "TikTok", "placement": "auction_in_feed", "audience": "prospecting",
              "impressions": 10_000, "clicks": 5000}
    report = build([
        {"variant_id": "A", "conversions": 500, **common},
        {"variant_id": "B", "conversions": 100, **common},
    ], measurement={"primary_kpi": "CVR"}, experiment_validation=validation, root=tmp_path)
    assert report["verdict"] == "local_qualified_winner"
    assert all(row["inference_denominator"] == 5000 for row in report["variants"])


def test_interim_analysis_does_not_mark_progress(tmp_path, monkeypatch):
    validation = _validation(tmp_path)
    feedback_dir = tmp_path / "投放反馈"
    feedback_dir.mkdir(exist_ok=True)
    (feedback_dir / "experiment_plan.json").write_text(
        json.dumps(validation["plan"], ensure_ascii=False), encoding="utf-8")
    (feedback_dir / "experiment_plan_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False), encoding="utf-8")
    source = tmp_path / "early.csv"
    source.write_text(
        "variant_id,platform,placement,audience,impressions,clicks\n"
        "A,TikTok,auction_in_feed,prospecting,20,10\n"
        "B,TikTok,auction_in_feed,prospecting,20,2\n",
        encoding="utf-8",
    )
    calls = []
    monkeypatch.setattr("feedback_ingest.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs)))
    assert main([str(tmp_path), "--input", str(source), "--mark-progress"]) == 0
    report = json.loads((feedback_dir / "feedback_report.json").read_text(encoding="utf-8"))
    assert report["analysis_status"] == "interim"
    assert calls == []


def test_ingest_parses_the_canonical_raw_copy_not_pre_copy_bytes(tmp_path, monkeypatch):
    validation = _validation(tmp_path)
    feedback_dir = tmp_path / "投放反馈"
    (feedback_dir / "experiment_plan.json").write_text(
        json.dumps(validation["plan"], ensure_ascii=False), encoding="utf-8")
    (feedback_dir / "experiment_plan_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False), encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-incoming.csv"
    outside.write_text(
        "variant_id,platform,placement,audience,impressions,clicks\n"
        "A,TikTok,auction_in_feed,prospecting,20,10\n"
        "B,TikTok,auction_in_feed,prospecting,20,2\n",
        encoding="utf-8",
    )

    def replace_during_copy(_source, destination):
        Path(destination).write_text(
            "variant_id,platform,placement,audience,impressions,clicks\n"
            "A,TikTok,auction_in_feed,prospecting,5000,500\n"
            "B,TikTok,auction_in_feed,prospecting,5000,100\n",
            encoding="utf-8",
        )

    monkeypatch.setattr("feedback_ingest.shutil.copy2", replace_during_copy)
    assert main([str(tmp_path), "--input", str(outside)]) == 0
    report = json.loads((feedback_dir / "feedback_report.json").read_text(encoding="utf-8"))
    canonical = feedback_dir / "raw" / outside.name
    assert report["analysis_status"] == "complete"
    assert report["variants"][0]["impressions"] == 5000
    assert report["source_data"]["sha256"] == hashlib.sha256(canonical.read_bytes()).hexdigest()


def test_ingest_refuses_canonical_raw_symlink_escape(tmp_path):
    validation = _validation(tmp_path)
    feedback_dir = tmp_path / "投放反馈"
    (feedback_dir / "experiment_plan.json").write_text(
        json.dumps(validation["plan"], ensure_ascii=False), encoding="utf-8")
    (feedback_dir / "experiment_plan_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False), encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-outside.csv"
    outside.write_text(
        "variant_id,platform,placement,audience,impressions,clicks\n"
        "A,TikTok,auction_in_feed,prospecting,5000,500\n"
        "B,TikTok,auction_in_feed,prospecting,5000,100\n",
        encoding="utf-8",
    )
    raw_dir = feedback_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / outside.name).symlink_to(outside)

    assert main([str(tmp_path), "--input", str(outside)]) == 1
    assert not (feedback_dir / "feedback_report.json").exists()
