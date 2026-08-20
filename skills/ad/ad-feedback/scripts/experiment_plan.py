#!/usr/bin/env python3
"""Validate a preregistered ad creative experiment before spend."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from statistics import NormalDist
from datetime import date, datetime, timezone
from pathlib import Path


VARIABLES = ("hook_id", "message_id", "cta_id")
REQUIRED = ("hypothesis", "primary_kpi", "conversion_event", "attribution_window", "platform", "audience",
            "placement", "randomization_unit", "decision_rule", "start_date", "end_date", "min_impressions")
DESIGN_MODES = {"local_binomial", "platform_native"}
MULTIPLICITY_METHODS = {"none", "bonferroni"}
METRIC_COUNTS = {
    "CTR": ("clicks", "impressions"),
    "CVR": ("conversions", "clicks"),
}
DENOMINATOR_UNITS = {"impressions": "impression", "clicks": "click"}
READINESS_CORE_FIELDS = (
    "schema_version", "kind", "brief_sha256", "mode", "declared_mode",
    "policy", "checks", "scope_summary", "summary", "findings",
)


def plan_sha256(plan):
    raw = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _project_file(path_value, root=None):
    """Resolve a durable project-local relative path, rejecting traversal."""
    raw = str(path_value or "").strip()
    path = Path(raw)
    if not raw or path.is_absolute() or ".." in path.parts:
        return None
    if root is None:
        return path
    base = Path(root).resolve()
    resolved = (base / path).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        return None
    return resolved


def _rate(value, field, findings, *, lower=0.0, upper=1.0, inclusive_lower=False):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = math.nan
    lower_ok = parsed >= lower if inclusive_lower else parsed > lower
    if not math.isfinite(parsed) or not lower_ok or parsed >= upper:
        findings.append({"severity": "block", "code": f"{field}_invalid", "field": field,
                         "msg": f"{field} 必须是 {lower}{'≤' if inclusive_lower else '<'}x<{upper} 的数值"})
        return None
    return parsed


def _bindings(value):
    """Normalize {variant: sha} or [{variant_id, asset_sha256}] receipts."""
    if isinstance(value, dict):
        return {str(key): str(digest or "").lower() for key, digest in value.items()}
    out = {}
    for row in value or []:
        if isinstance(row, dict) and row.get("variant_id"):
            out[str(row["variant_id"])] = str(row.get("asset_sha256") or "").lower()
    return out


def _receipt_file_check(receipt, root, findings, prefix):
    path_value = str(receipt.get("evidence_path") or receipt.get("evidence_file") or "").strip()
    digest = str(receipt.get("evidence_sha256") or "").strip().lower()
    path = _project_file(path_value, root)
    if path is None:
        findings.append({"severity": "block", "code": f"{prefix}_evidence_path_invalid",
                         "msg": f"{prefix} evidence_path 必须是作品根内相对路径，禁止绝对路径或 ../"})
        return
    if not re_full_sha256(digest):
        findings.append({"severity": "block", "code": f"{prefix}_evidence_binding_missing",
                         "msg": f"{prefix} 必须绑定 evidence_path + 64 位 evidence_sha256"})
        return
    if root is not None:
        if file_sha256(path) != digest:
            findings.append({"severity": "block", "code": f"{prefix}_evidence_binding_stale",
                             "msg": f"{prefix} 证据文件不存在或 SHA 已变化"})


def _campaign_readiness_check(root, findings):
    """Require a current formal launch-readiness receipt before preregistration."""
    if root is None:
        findings.append({"severity": "block", "code": "campaign_readiness_root_missing",
                         "msg": "正式实验预注册必须提供作品根并消费当前 campaign_readiness.json"})
        return None
    base = Path(root).resolve()
    brief_path = base / "需求" / "brief.json"
    readiness_path = base / "生产数据" / "campaign_readiness.json"
    if not brief_path.is_file():
        findings.append({"severity": "block", "code": "campaign_readiness_brief_missing",
                         "msg": "正式实验预注册缺当前 需求/brief.json"})
        return None
    if not readiness_path.is_file():
        findings.append({"severity": "block", "code": "campaign_readiness_missing",
                         "msg": "正式实验预注册前须生成 生产数据/campaign_readiness.json"})
        return None
    try:
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        if not isinstance(readiness, dict):
            raise ValueError("not_object")
    except (OSError, ValueError, json.JSONDecodeError):
        findings.append({"severity": "block", "code": "campaign_readiness_unreadable",
                         "msg": "campaign_readiness.json 缺失或不是有效 JSON 对象"})
        return None
    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    if readiness.get("kind") != "ad_campaign_readiness":
        findings.append({"severity": "block", "code": "campaign_readiness_kind_invalid",
                         "msg": "campaign_readiness.json kind 必须为 ad_campaign_readiness"})
    if str(readiness.get("mode") or "").lower() != "formal":
        findings.append({"severity": "block", "code": "campaign_readiness_not_formal",
                         "msg": "sample/unknown readiness 不能批准正式付费实验"})
    if summary.get("release_ready") is not True or summary.get("block") != 0:
        findings.append({"severity": "block", "code": "campaign_not_release_ready",
                         "msg": "campaign_readiness 必须 formal、release_ready=true 且 block=0"})
    brief_digest = file_sha256(brief_path)
    if readiness.get("brief_sha256") != brief_digest:
        findings.append({"severity": "block", "code": "campaign_readiness_stale",
                         "msg": "campaign_readiness.brief_sha256 与当前 brief 不一致；须重跑 readiness"})
    semantic_current = False
    try:
        craft_scripts = Path(__file__).resolve().parents[2] / "ad-craft" / "scripts"
        if str(craft_scripts) not in sys.path:
            sys.path.insert(0, str(craft_scripts))
        import campaign_readiness as campaign_readiness_module
        fresh = campaign_readiness_module.evaluate(base, "auto")
        stored_core = {key: readiness.get(key) for key in READINESS_CORE_FIELDS}
        fresh_core = {key: fresh.get(key) for key in READINESS_CORE_FIELDS}
        semantic_current = stored_core == fresh_core
        if not semantic_current:
            findings.append({
                "severity": "block", "code": "campaign_readiness_semantic_stale",
                "msg": "campaign_readiness 与当前落地页、准入、埋点、归因、路由及隐私证据重算结果不一致",
            })
    except Exception as exc:
        findings.append({
            "severity": "block", "code": "campaign_readiness_rebuild_failed",
            "msg": f"无法重算 campaign readiness：{exc}",
        })
    return {
        "path": "生产数据/campaign_readiness.json",
        "sha256": file_sha256(readiness_path),
        "brief_sha256": brief_digest,
        "mode": readiness.get("mode"),
        "release_ready": summary.get("release_ready") is True and semantic_current,
    }


def _power_analysis(plan, variants, findings):
    """Conservative fixed-sample calculation for a two-sided difference in proportions.

    Multi-arm experiments use a Bonferroni familywise correction. The same
    per-comparison alpha is consumed by feedback_ingest's pooled two-proportion
    score test, keeping design and inference aligned without a SciPy dependency.
    """
    primary_kpi = str(plan.get("primary_kpi") or "").upper()
    metric = plan.get("metric_definition") if isinstance(plan.get("metric_definition"), dict) else {}
    numerator = str(metric.get("numerator") or "").strip()
    denominator = str(metric.get("denominator") or "").strip()
    expected_counts = METRIC_COUNTS.get(primary_kpi)
    if expected_counts is None:
        findings.append({"severity": "block", "code": "local_kpi_not_binomial",
                         "msg": "local_binomial 仅支持有明确计数口径的 CTR/CVR；CPA/ROAS 请用平台原生实验或事件级方法"})
    elif (numerator, denominator) != expected_counts:
        findings.append({"severity": "block", "code": "metric_definition_invalid",
                         "msg": f"{primary_kpi} 必须明确 numerator={expected_counts[0]}、denominator={expected_counts[1]}"})
    expected_unit = DENOMINATOR_UNITS.get(denominator)
    analysis_unit = str(plan.get("analysis_unit") or "").strip().lower()
    randomization_unit = str(plan.get("randomization_unit") or "").strip().lower()
    if not expected_unit or analysis_unit != expected_unit or randomization_unit != expected_unit:
        findings.append({"severity": "block", "code": "analysis_randomization_unit_mismatch",
                         "msg": ("local_binomial 要求 randomization_unit 与 analysis_unit 都等于 denominator 的独立事件单元；"
                                 f"当前 denominator={denominator or '?'}，期望 {expected_unit or '?'}。用户/桶随机化请走 platform_native")})
    if plan.get("independent_bernoulli") is not True:
        findings.append({"severity": "block", "code": "independent_bernoulli_not_attested",
                         "msg": "local_binomial 必须显式 independent_bernoulli=true；重复曝光、用户分桶或聚类数据请走 platform_native"})

    baseline = _rate(plan.get("baseline_rate"), "baseline_rate", findings)
    mde = _rate(plan.get("minimum_detectable_effect"), "minimum_detectable_effect", findings)
    alpha = _rate(plan.get("alpha"), "alpha", findings)
    power = _rate(plan.get("power"), "power", findings, lower=0.5)
    if baseline is not None and mde is not None and baseline + mde >= 1:
        findings.append({"severity": "block", "code": "mde_out_of_range",
                         "msg": "baseline_rate + minimum_detectable_effect 必须小于 1；MDE 是绝对百分点差"})

    # Winner selection compares the best observed arm with every other arm. Plan
    # conservatively for the complete pairwise family rather than pretending all
    # arms are only compared with an implicit control.
    comparisons = max(1, len(variants) * (len(variants) - 1) // 2)
    method = str(plan.get("multiple_comparison_method") or "").strip().lower()
    if method not in MULTIPLICITY_METHODS:
        findings.append({"severity": "block", "code": "multiple_comparison_method_invalid",
                         "msg": "multiple_comparison_method 必须为 none/bonferroni；Holm 未实现，不得声明"})
    elif comparisons > 1 and method == "none":
        findings.append({"severity": "block", "code": "multiplicity_uncontrolled",
                         "msg": "超过两个实验臂时须用 bonferroni 控制多重比较"})
    adjusted_alpha = alpha / comparisons if alpha is not None and method == "bonferroni" else alpha

    allocations = []
    try:
        allocations = [float(v.get("allocation") or 0) for v in variants]
    except (TypeError, ValueError):
        pass
    if allocations and max(allocations) - min(allocations) > 0.001:
        findings.append({"severity": "block", "code": "local_allocation_unbalanced",
                         "msg": "当前本地功效计算要求各臂等分流；不等分请使用经验证的外部功效计算并走 platform_native"})

    required = None
    if all(value is not None for value in (baseline, mde, adjusted_alpha, power)) and baseline + mde < 1:
        p1, p2 = baseline, baseline + mde
        p_bar = (p1 + p2) / 2
        z_alpha = NormalDist().inv_cdf(1 - adjusted_alpha / 2)
        z_power = NormalDist().inv_cdf(power)
        numerator_n = (
            z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
            + z_power * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        ) ** 2
        required = int(math.ceil(numerator_n / (mde ** 2)))

    stopping = plan.get("stopping_rule") if isinstance(plan.get("stopping_rule"), dict) else {}
    stop_type = str(stopping.get("type") or "").strip().lower()
    if stop_type not in {"fixed_sample", "fixed_horizon"}:
        findings.append({"severity": "block", "code": "stopping_rule_invalid",
                         "msg": "stopping_rule.type 必须为 fixed_sample 或 fixed_horizon"})
    if stopping.get("no_early_stopping") is not True:
        findings.append({"severity": "block", "code": "early_stopping_not_prohibited",
                         "msg": "stopping_rule.no_early_stopping 必须显式为 true，禁止看数提前停"})
    declared_target = stopping.get("minimum_sample_per_arm")
    if declared_target not in (None, "", "computed"):
        try:
            declared_target = int(declared_target)
            if declared_target <= 0:
                raise ValueError
            if required is not None and declared_target < required:
                findings.append({"severity": "block", "code": "stopping_sample_below_power",
                                 "msg": f"stopping_rule.minimum_sample_per_arm={declared_target} 小于功效计算所需 {required}"})
        except (TypeError, ValueError):
            findings.append({"severity": "block", "code": "stopping_sample_invalid",
                             "msg": "minimum_sample_per_arm 必须为正整数、computed 或省略"})
            declared_target = None
    else:
        declared_target = None
    if stop_type == "fixed_horizon" and stopping.get("require_observed_through_end_date") is not True:
        findings.append({"severity": "block", "code": "horizon_evidence_not_required",
                         "msg": "fixed_horizon 必须设置 require_observed_through_end_date=true，确保数据覆盖预注册终点"})

    effective_target = max(required or 0, declared_target or 0) or None
    return {
        "method": "two_sided_two_proportion_normal_approximation",
        "inference_test": "pooled_two_proportion_score_test",
        "metric_definition": {"numerator": numerator, "denominator": denominator},
        "analysis_unit": analysis_unit or None,
        "randomization_unit": randomization_unit or None,
        "independent_bernoulli": plan.get("independent_bernoulli") is True,
        "baseline_rate": baseline,
        "minimum_detectable_effect_absolute": mde,
        "alpha_familywise": alpha,
        "power": power,
        "multiple_comparison_method": method or None,
        "comparison_count": comparisons,
        "planning_alpha_per_comparison": adjusted_alpha,
        "required_sample_per_arm": required,
        "required_sample_by_arm": {str(row.get("variant_id") or ""): required for row in variants},
        "effective_stopping_sample_per_arm": effective_target,
        "effective_stopping_sample_by_arm": {
            str(row.get("variant_id") or ""): effective_target for row in variants
        },
        "stopping_rule": stopping,
        "note": "min_impressions 仅用于运营诊断筛选，不参与功效计算",
    }


def _platform_configuration(plan, variants, root, findings):
    platform = plan.get("platform_experiment") if isinstance(plan.get("platform_experiment"), dict) else {}
    experiment_id = str(platform.get("experiment_id") or "").strip()
    if not experiment_id:
        findings.append({"severity": "block", "code": "platform_experiment_id_missing",
                         "msg": "platform_native 必须预注册 platform_experiment.experiment_id"})
    receipt = platform.get("config_receipt") if isinstance(platform.get("config_receipt"), dict) else {}
    if str(receipt.get("status") or "").lower() not in {"configured", "active", "completed"}:
        findings.append({"severity": "block", "code": "platform_config_status_invalid",
                         "msg": "平台配置 receipt.status 必须为 configured/active/completed"})
    _receipt_file_check(receipt, root, findings, "platform_config")
    expected = {str(v.get("variant_id") or ""): str(v.get("asset_sha256") or "").lower() for v in variants}
    actual = _bindings(receipt.get("asset_bindings"))
    if actual != expected:
        findings.append({"severity": "block", "code": "platform_config_asset_binding_mismatch",
                         "msg": "平台配置 receipt 必须逐变体绑定当前 asset_sha256"})
    receipt_experiment_id = str(receipt.get("experiment_id") or "").strip()
    if not receipt_experiment_id:
        findings.append({"severity": "block", "code": "platform_config_experiment_id_missing",
                         "msg": "config receipt 自身必须显式携带 experiment_id"})
    elif experiment_id and receipt_experiment_id != experiment_id:
        findings.append({"severity": "block", "code": "platform_config_experiment_id_mismatch",
                         "msg": "config receipt 的 experiment_id 与计划不一致"})
    return {
        "experiment_id": experiment_id or None,
        "config_receipt": receipt,
        "asset_bindings": actual,
        "platform_is_inference_authority": True,
    }


def build(plan, root=None):
    findings = []
    campaign_readiness = _campaign_readiness_check(root, findings)
    for key in REQUIRED:
        if plan.get(key) in (None, "", []):
            findings.append({"severity": "block", "code": "plan_field_missing", "field": key,
                             "msg": f"实验预注册缺 {key}"})
    variants = [v for v in plan.get("variants") or [] if isinstance(v, dict)]
    if len(variants) < 2:
        findings.append({"severity": "block", "code": "variants_insufficient", "msg": "实验至少需要 2 个变体"})
    ids = [str(v.get("variant_id") or "") for v in variants]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        findings.append({"severity": "block", "code": "variant_id_invalid", "msg": "variant_id 必须非空且唯一"})
    asset_hashes = []
    for variant in variants:
        vid = variant.get("variant_id") or "?"
        asset_path = str(variant.get("asset_path") or "").strip()
        digest = str(variant.get("asset_sha256") or "").strip().lower()
        path = _project_file(asset_path, root)
        if path is None:
            findings.append({"severity": "block", "code": "variant_asset_path_invalid", "variant_id": vid,
                             "msg": "asset_path 必须是作品根内相对路径，禁止绝对路径或 ../"})
        if not re_full_sha256(digest):
            findings.append({"severity": "block", "code": "variant_asset_binding_missing", "variant_id": vid,
                             "msg": "每个变体须在花钱前写 asset_path + 64 位 asset_sha256，防止计划与实际素材错位"})
        elif root is not None and path is not None:
            if file_sha256(path) != digest:
                findings.append({"severity": "block", "code": "variant_asset_binding_stale", "variant_id": vid,
                                 "msg": f"变体 {vid} 的文件不存在或 SHA 已变化"})
        if digest:
            asset_hashes.append(digest)
    if len(asset_hashes) >= 2 and len(set(asset_hashes)) != len(asset_hashes):
        findings.append({"severity": "block", "code": "variant_assets_identical",
                         "msg": "不同 variant_id 绑定了相同媒体 SHA；无法证明实际投放素材不同"})
    changed_dimensions = set()
    if variants:
        base = variants[0]
        for variant in variants[1:]:
            diffs = [key for key in VARIABLES if variant.get(key) != base.get(key)]
            if len(diffs) != 1:
                findings.append({"severity": "block", "code": "not_single_variable",
                                 "variant_id": variant.get("variant_id"),
                                 "msg": f"相对基准同时改变 {diffs or '0'} 个创意变量；无法归因"})
            else:
                changed_dimensions.add(diffs[0])
    if len(changed_dimensions) > 1:
        findings.append({"severity": "block", "code": "mixed_experiment_dimensions",
                         "msg": "同一实验组混测多个变量维度；拆成顺序实验"})
    try:
        allocations = [float(v.get("allocation") or 0) for v in variants]
        if any(not math.isfinite(value) for value in allocations):
            raise ValueError
    except (TypeError, ValueError):
        allocations = []
        findings.append({"severity": "block", "code": "allocation_not_numeric",
                         "msg": "各变体 allocation 必须是数值"})
    if variants and (len(allocations) != len(variants) or abs(sum(allocations) - 1.0) > 0.001
                     or any(v <= 0 for v in allocations)):
        findings.append({"severity": "block", "code": "allocation_invalid",
                         "msg": "各变体 allocation 必须为正且合计 1.0"})
    if len(variants) > 4:
        findings.append({"severity": "warn", "code": "too_many_arms",
                         "msg": "同轮超过 4 个变体会稀释样本；优先拆成顺序实验"})
    constants = plan.get("held_constant") if isinstance(plan.get("held_constant"), dict) else {}
    for key in ("budget", "bidding", "landing_page", "placement"):
        if not constants.get(key):
            findings.append({"severity": "block", "code": "constant_missing", "field": key,
                             "msg": f"未声明保持不变的 {key}"})
    if constants.get("placement") and str(constants.get("placement")) != str(plan.get("placement")):
        findings.append({"severity": "block", "code": "placement_constant_mismatch",
                         "msg": "held_constant.placement 必须等于计划的具体 placement"})
    try:
        start, end = date.fromisoformat(str(plan.get("start_date"))), date.fromisoformat(str(plan.get("end_date")))
        if end <= start:
            findings.append({"severity": "block", "code": "date_range_invalid", "msg": "end_date 必须晚于 start_date"})
    except ValueError:
        if plan.get("start_date") or plan.get("end_date"):
            findings.append({"severity": "block", "code": "date_invalid", "msg": "实验日期须为 YYYY-MM-DD"})
    try:
        if int(plan.get("min_impressions") or 0) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        findings.append({"severity": "block", "code": "min_impressions_invalid",
                         "msg": "min_impressions 必须为正整数；它是样本快筛线，不等于统计功效计算"})
    design_mode = str(plan.get("design_mode") or "").strip().lower()
    power_analysis = None
    platform_configuration = None
    if design_mode not in DESIGN_MODES:
        findings.append({"severity": "block", "code": "design_mode_missing_or_invalid",
                         "msg": "须显式声明 design_mode=local_binomial 或 platform_native；旧计划仅可诊断"})
    elif design_mode == "local_binomial":
        power_analysis = _power_analysis(plan, variants, findings)
    else:
        platform_configuration = _platform_configuration(plan, variants, root, findings)
    return {
        "schema_version": 3, "kind": "ad_experiment_plan_validation",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": plan_sha256(plan),
        "plan": plan, "design_mode": design_mode or None,
        "changed_dimension": next(iter(changed_dimensions), None),
        "power_analysis": power_analysis,
        "platform_configuration": platform_configuration,
        "campaign_readiness": campaign_readiness,
        "methodology": {
            "design": "preregistered randomized creative experiment",
            "local_boundary": "local_binomial requires an independent Bernoulli analysis unit identical to the randomization/denominator unit, an a-priori baseline/MDE/alpha/power calculation, Bonferroni where needed, and a fixed stopping rule; min_impressions is diagnostic only",
            "platform_guidance": "platform_native conclusions are authoritative only when experiment/config/result receipts and current asset hashes agree",
            "source": "https://support.google.com/google-ads/answer/10436762",
        },
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings),
                    "approved": not any(f["severity"] == "block" for f in findings)},
        "findings": findings,
    }


def re_full_sha256(value):
    return len(str(value or "")) == 64 and all(ch in "0123456789abcdef" for ch in str(value or "").lower())


def main(argv=None):
    ap = argparse.ArgumentParser(description="validate preregistered ad experiment plan")
    ap.add_argument("project_root")
    ap.add_argument("--input", required=True)
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    plan = json.loads(Path(ns.input).read_text(encoding="utf-8"))
    canonical = root / "投放反馈" / "experiment_plan.json"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = build(plan, root)
    out = root / "投放反馈" / "experiment_plan_validation.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# experiment plan approved={payload['summary']['approved']} block={payload['summary']['block']}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
