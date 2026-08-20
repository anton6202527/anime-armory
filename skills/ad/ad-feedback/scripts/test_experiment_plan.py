import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_plan as ep  # noqa: E402
from _test_readiness_fixture import write_formal_readiness  # noqa: E402


def _ready_root(root):
    write_formal_readiness(root, "CTR")


def _plan(root=None):
    plan = {
        "design_mode": "local_binomial",
        "hypothesis": "更直接的产品钩子提升 CTR",
        "primary_kpi": "CTR", "conversion_event": "purchase", "attribution_window": "7d_click",
        "metric_definition": {"numerator": "clicks", "denominator": "impressions"},
        "baseline_rate": 0.05, "minimum_detectable_effect": 0.02, "alpha": 0.05, "power": 0.8,
        "multiple_comparison_method": "none",
        "stopping_rule": {"type": "fixed_sample", "minimum_sample_per_arm": "computed",
                          "no_early_stopping": True},
        "platform": "TikTok", "placement": "auction_in_feed", "audience": "prospecting-cn", "start_date": "2026-07-12",
        "end_date": "2026-08-23", "min_impressions": 5000,
        "randomization_unit": "impression", "analysis_unit": "impression", "independent_bernoulli": True,
        "decision_rule": "预注册两比例 score test；否则只作方向性读取",
        "held_constant": {"budget": "50/50", "bidding": "same", "landing_page": "same", "placement": "auction_in_feed"},
        "variants": [
            {"variant_id": "A", "hook_id": "H1", "message_id": "M1", "cta_id": "C1", "allocation": 0.5,
             "asset_path": "variants/A.mp4", "asset_sha256": "a" * 64},
            {"variant_id": "B", "hook_id": "H2", "message_id": "M1", "cta_id": "C1", "allocation": 0.5,
             "asset_path": "variants/B.mp4", "asset_sha256": "b" * 64},
        ],
    }
    if root is not None:
        _ready_root(root)
        for variant in plan["variants"]:
            path = root / "variants" / f"{variant['variant_id']}.mp4"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("asset-" + variant["variant_id"]).encode())
            variant["asset_path"] = str(path.relative_to(root))
            variant["asset_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return plan


def test_single_variable_plan_passes(tmp_path):
    payload = ep.build(_plan(tmp_path), tmp_path)
    assert payload["summary"]["approved"] is True
    assert payload["changed_dimension"] == "hook_id"
    assert payload["power_analysis"]["required_sample_per_arm"] > 0
    assert payload["power_analysis"]["note"].startswith("min_impressions")


def test_handwritten_release_ready_receipt_cannot_bypass_readiness_audit(tmp_path):
    plan = _plan(tmp_path)
    brief = tmp_path / "需求" / "brief.json"
    readiness = tmp_path / "生产数据" / "campaign_readiness.json"
    readiness.write_text(json.dumps({
        "kind": "ad_campaign_readiness", "mode": "formal",
        "brief_sha256": hashlib.sha256(brief.read_bytes()).hexdigest(),
        "summary": {"block": 0, "release_ready": True},
    }), encoding="utf-8")
    payload = ep.build(plan, tmp_path)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "campaign_readiness_semantic_stale" for f in payload["findings"])


def test_multi_variable_plan_blocks(tmp_path):
    plan = _plan(tmp_path)
    plan["variants"][1]["message_id"] = "M2"
    payload = ep.build(plan, tmp_path)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "not_single_variable" for f in payload["findings"])


def test_invalid_allocation_is_reported_not_crashed(tmp_path):
    plan = _plan(tmp_path)
    plan["variants"][1]["allocation"] = "not-a-number"
    payload = ep.build(plan, tmp_path)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "allocation_not_numeric" for f in payload["findings"])


def test_variant_media_hash_must_bind_actual_file(tmp_path):
    plan = _plan(tmp_path)
    (tmp_path / plan["variants"][0]["asset_path"]).write_bytes(b"changed")
    payload = ep.build(plan, tmp_path)
    assert any(f["code"] == "variant_asset_binding_stale" for f in payload["findings"])


def test_legacy_plan_without_power_preregistration_fails_closed(tmp_path):
    plan = _plan(tmp_path)
    for key in ("design_mode", "metric_definition", "baseline_rate", "minimum_detectable_effect",
                "alpha", "power", "multiple_comparison_method", "stopping_rule"):
        plan.pop(key)
    payload = ep.build(plan, tmp_path)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "design_mode_missing_or_invalid" for f in payload["findings"])


def test_min_impressions_does_not_replace_power_or_stopping_rule(tmp_path):
    plan = _plan(tmp_path)
    plan.pop("baseline_rate")
    plan.pop("stopping_rule")
    payload = ep.build(plan, tmp_path)
    codes = {f["code"] for f in payload["findings"]}
    assert "baseline_rate_invalid" in codes
    assert "stopping_rule_invalid" in codes
    assert payload["summary"]["approved"] is False


def test_multiple_arms_require_multiplicity_control(tmp_path):
    plan = _plan(tmp_path)
    plan["variants"] = [
        {**plan["variants"][0], "allocation": 1 / 3},
        {**plan["variants"][1], "allocation": 1 / 3},
        {**plan["variants"][1], "variant_id": "C", "hook_id": "H3", "asset_sha256": "c" * 64,
         "asset_path": "variants/C.mp4", "allocation": 1 / 3},
    ]
    c_path = tmp_path / "variants" / "C.mp4"
    c_path.write_bytes(b"asset-C")
    plan["variants"][2]["asset_sha256"] = hashlib.sha256(c_path.read_bytes()).hexdigest()
    payload = ep.build(plan, tmp_path)
    assert any(f["code"] == "multiplicity_uncontrolled" for f in payload["findings"])
    plan["multiple_comparison_method"] = "holm"
    payload = ep.build(plan, tmp_path)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "multiple_comparison_method_invalid" for f in payload["findings"])
    plan["multiple_comparison_method"] = "bonferroni"
    payload = ep.build(plan, tmp_path)
    assert payload["summary"]["approved"] is True
    assert abs(payload["power_analysis"]["planning_alpha_per_comparison"] - (0.05 / 3)) < 1e-12


def test_platform_native_requires_sha_bound_configuration_receipt(tmp_path):
    plan = _plan(tmp_path)
    plan["design_mode"] = "platform_native"
    for key in ("metric_definition", "baseline_rate", "minimum_detectable_effect", "alpha", "power",
                "multiple_comparison_method", "stopping_rule"):
        plan.pop(key)
    evidence = tmp_path / "投放反馈" / "evidence" / "config.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("config", encoding="utf-8")
    bindings = {row["variant_id"]: row["asset_sha256"] for row in plan["variants"]}
    plan["platform_experiment"] = {
        "experiment_id": "exp-123",
        "config_receipt": {
            "experiment_id": "exp-123", "status": "configured",
            "evidence_path": str(evidence.relative_to(tmp_path)),
            "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
            "asset_bindings": bindings,
        },
    }
    payload = ep.build(plan, tmp_path)
    assert payload["summary"]["approved"] is True
    assert payload["platform_configuration"]["experiment_id"] == "exp-123"
    plan["platform_experiment"]["config_receipt"]["asset_bindings"]["B"] = "e" * 64
    payload = ep.build(plan, tmp_path)
    assert any(f["code"] == "platform_config_asset_binding_mismatch" for f in payload["findings"])


def test_local_rejects_cluster_randomization_and_missing_independence_attestation(tmp_path):
    plan = _plan(tmp_path)
    plan["randomization_unit"] = "platform_user_bucket"
    plan["independent_bernoulli"] = False
    payload = ep.build(plan, tmp_path)
    codes = {f["code"] for f in payload["findings"]}
    assert "analysis_randomization_unit_mismatch" in codes
    assert "independent_bernoulli_not_attested" in codes


def test_paths_must_be_project_relative_and_config_receipt_id_explicit(tmp_path):
    plan = _plan(tmp_path)
    plan["variants"][0]["asset_path"] = "../outside.mp4"
    assert any(f["code"] == "variant_asset_path_invalid" for f in ep.build(plan, tmp_path)["findings"])

    platform = _plan(tmp_path)
    platform["design_mode"] = "platform_native"
    for key in ("metric_definition", "baseline_rate", "minimum_detectable_effect", "alpha", "power",
                "multiple_comparison_method", "stopping_rule"):
        platform.pop(key)
    platform["platform_experiment"] = {
        "experiment_id": "exp-1",
        "config_receipt": {"status": "configured", "evidence_path": "proof.json",
                           "evidence_sha256": "c" * 64,
                           "asset_bindings": {"A": "a" * 64, "B": "b" * 64}},
    }
    assert any(f["code"] == "platform_config_experiment_id_missing" for f in ep.build(platform, tmp_path)["findings"])


def test_nan_allocation_is_rejected(tmp_path):
    plan = _plan(tmp_path)
    plan["variants"][1]["allocation"] = float("nan")
    payload = ep.build(plan, tmp_path)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "allocation_not_numeric" for f in payload["findings"])


def test_formal_preregistration_requires_current_campaign_readiness(tmp_path):
    plan = _plan(tmp_path)
    readiness_path = tmp_path / "生产数据" / "campaign_readiness.json"
    readiness_path.unlink()
    payload = ep.build(plan, tmp_path)
    assert any(f["code"] == "campaign_readiness_missing" for f in payload["findings"])

    _ready_root(tmp_path)
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["mode"] = "sample"
    readiness["summary"]["release_ready"] = False
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
    payload = ep.build(plan, tmp_path)
    codes = {f["code"] for f in payload["findings"]}
    assert "campaign_readiness_not_formal" in codes
    assert "campaign_not_release_ready" in codes

    _ready_root(tmp_path)
    (tmp_path / "需求" / "brief.json").write_text(json.dumps({"campaign_mode": "formal", "changed": True}),
                                                    encoding="utf-8")
    payload = ep.build(plan, tmp_path)
    assert any(f["code"] == "campaign_readiness_stale" for f in payload["findings"])


def test_build_without_project_root_cannot_formally_approve():
    payload = ep.build(_plan())
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "campaign_readiness_root_missing" for f in payload["findings"])
