#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import shutil
import sys
import tempfile
from datetime import date, datetime, timezone
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist


NUMERIC = ("impressions", "clicks", "conversions", "spend", "revenue", "video_3s", "video_6s", "completed_views")
BINOMIAL_COUNTS = ("impressions", "clicks", "conversions")
CORE_STRATA = ("platform", "placement", "audience")
OPTIONAL_CONSTANTS = ("conversion_event", "attribution_window", "landing_page", "bidding", "budget")
# 业界信息流基准（2026 采集·会过期快照）：3s 观看率（hook rate）< 25% ≈ 前 3 秒失败，
# 无论后段多强都先修 hook。仅在数据真带 video_3s 时判（全 0 视为字段缺失，不臆造）。
HOOK_RATE_FLOOR = 0.25
BINOMIAL_METRICS = {
    "CTR": ("clicks", "impressions", "ctr"),
    "CVR": ("conversions", "clicks", "cvr"),
}
VALIDATION_CORE_FIELDS = (
    "schema_version", "kind", "plan_sha256", "plan", "design_mode",
    "changed_dimension", "power_analysis", "platform_configuration",
    "campaign_readiness", "methodology", "summary", "findings",
)


def file_sha256(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _full_sha256(value):
    value = str(value or "").lower()
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _bindings(value):
    if isinstance(value, dict):
        return {str(key): str(digest or "").lower() for key, digest in value.items()}
    out = {}
    for row in value or []:
        if isinstance(row, dict) and row.get("variant_id"):
            out[str(row["variant_id"])] = str(row.get("asset_sha256") or "").lower()
    return out


def _project_file(path_value, root=None):
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


def _load_json_object(path: Path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _validation_core(payload):
    payload = payload if isinstance(payload, dict) else {}
    return {key: payload.get(key) for key in VALIDATION_CORE_FIELDS}


def _revalidated_experiment(validation, root, findings):
    """Rebuild the preregistration validation instead of trusting a derivative.

    ``experiment_plan_validation.json`` contains calculated power and stopping
    fields that directly decide whether an analysis is terminal.  A matching
    plan hash alone cannot authenticate those calculated fields: they could be
    edited in place.  Formal feedback therefore compares the stored and supplied
    validation cores with a fresh deterministic build from the canonical plan.
    ``validated_at`` is deliberately excluded because it is informational time.
    """
    supplied = validation if isinstance(validation, dict) else {}
    if root is None:
        if bool(((supplied.get("summary") or {}).get("approved"))):
            findings.append({
                "severity": "block", "code": "experiment_validation_currentness_unavailable",
                "msg": "已批准实验验证必须提供作品根，才能重算功效、停止规则与证据绑定",
            })
        return supplied

    base = Path(root).resolve()
    plan_path = base / "投放反馈" / "experiment_plan.json"
    validation_path = base / "投放反馈" / "experiment_plan_validation.json"
    canonical = _load_json_object(plan_path)
    stored = _load_json_object(validation_path)
    if canonical is None:
        findings.append({"severity": "block", "code": "experiment_plan_source_missing",
                         "msg": "缺当前、有效的 投放反馈/experiment_plan.json，无法重算预注册"})
        return supplied
    if stored is None:
        findings.append({"severity": "block", "code": "experiment_validation_source_missing",
                         "msg": "缺当前、有效的 experiment_plan_validation.json，无法证明花钱前预注册"})
        return supplied

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import experiment_plan as experiment_plan_module
        fresh = experiment_plan_module.build(canonical, base)
    except Exception as exc:
        findings.append({"severity": "block", "code": "experiment_validation_rebuild_failed",
                         "msg": f"无法从当前计划重算实验验证：{exc}"})
        return supplied

    for row in fresh.get("findings") or []:
        if not isinstance(row, dict):
            continue
        copied = dict(row)
        copied.setdefault("source", "preregistration_rebuild")
        if not any(existing.get("code") == copied.get("code") and
                   existing.get("variant_id") == copied.get("variant_id")
                   for existing in findings):
            findings.append(copied)

    stored_core = _validation_core(stored)
    supplied_core = _validation_core(supplied)
    fresh_core = _validation_core(fresh)
    if stored_core != fresh_core:
        findings.append({
            "severity": "block", "code": "experiment_validation_semantic_stale",
            "msg": "实验验证的计划、功效、停止规则、平台配置或 readiness 与当前重算结果不一致",
        })
    if supplied_core != stored_core:
        findings.append({
            "severity": "block", "code": "experiment_validation_source_mismatch",
            "msg": "反馈分析消费的实验验证与当前磁盘验证产物不一致",
        })

    # Consume freshly calculated fields even when a mismatch was found, so a
    # tampered stopping target can never influence subsequent computations.
    rebuilt = dict(fresh)
    for key in ("platform_result_receipt", "platform_result_source"):
        if key in supplied:
            rebuilt[key] = supplied[key]
    return rebuilt


def _strict_count(value):
    if isinstance(value, bool) or value is None or str(value).strip() == "":
        raise ValueError("missing")
    try:
        parsed = float(str(value).replace(",", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError("not_numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError("not_finite")
    if parsed < 0 or not parsed.is_integer():
        raise ValueError("not_nonnegative_integer")
    return int(parsed)


def _current_plan_bindings(plan, root, findings, campaign_readiness=None):
    """Revalidate every current media/config file at feedback time."""
    finding_start = len(findings)
    if root is None:
        findings.append({"severity": "block", "code": "current_binding_check_unavailable",
                         "msg": "反馈推断必须提供作品根，才能重核当前素材与配置证据 SHA"})
        return {"verified": False, "assets": {}, "config_evidence": None}
    assets = {}
    for row in plan.get("variants") or []:
        if not isinstance(row, dict):
            continue
        variant_id = str(row.get("variant_id") or "")
        path_value = str(row.get("asset_path") or "")
        expected = str(row.get("asset_sha256") or "").lower()
        path = _project_file(path_value, root)
        actual = file_sha256(path) if path is not None else None
        assets[variant_id] = {"path": path_value, "expected_sha256": expected, "actual_sha256": actual,
                              "current": bool(_full_sha256(expected) and actual == expected)}
        if path is None:
            findings.append({"severity": "block", "code": "variant_asset_path_invalid", "variant_id": variant_id,
                             "msg": "asset_path 必须是作品根内相对路径，禁止绝对路径或 ../"})
        elif actual != expected:
            findings.append({"severity": "block", "code": "variant_asset_binding_stale", "variant_id": variant_id,
                             "msg": f"变体 {variant_id} 当前素材不存在或 SHA 已变化"})

    config_status = None
    if str(plan.get("design_mode") or "").lower() == "platform_native":
        platform = plan.get("platform_experiment") if isinstance(plan.get("platform_experiment"), dict) else {}
        experiment_id = str(platform.get("experiment_id") or "")
        receipt = platform.get("config_receipt") if isinstance(platform.get("config_receipt"), dict) else {}
        receipt_id = str(receipt.get("experiment_id") or "")
        if not receipt_id or receipt_id != experiment_id:
            findings.append({"severity": "block", "code": "platform_config_experiment_id_mismatch",
                             "msg": "config receipt 必须显式携带与计划一致的 experiment_id"})
        evidence_path = str(receipt.get("evidence_path") or receipt.get("evidence_file") or "")
        expected = str(receipt.get("evidence_sha256") or "").lower()
        path = _project_file(evidence_path, root)
        actual = file_sha256(path) if path is not None else None
        config_status = {"path": evidence_path, "expected_sha256": expected, "actual_sha256": actual,
                         "current": bool(_full_sha256(expected) and actual == expected)}
        if path is None:
            findings.append({"severity": "block", "code": "platform_config_evidence_path_invalid",
                             "msg": "config receipt evidence_path 必须是作品根内相对路径"})
        elif actual != expected:
            findings.append({"severity": "block", "code": "platform_config_evidence_stale",
                             "msg": "平台实验配置证据不存在或 SHA 已变化"})
        expected_bindings = {str(row.get("variant_id") or ""): str(row.get("asset_sha256") or "").lower()
                             for row in plan.get("variants") or [] if isinstance(row, dict)}
        if _bindings(receipt.get("asset_bindings")) != expected_bindings:
            findings.append({"severity": "block", "code": "platform_config_asset_binding_mismatch",
                             "msg": "config receipt 未逐变体绑定当前计划素材 SHA"})
    readiness_status = None
    readiness_receipt = campaign_readiness if isinstance(campaign_readiness, dict) else {}
    readiness_path_value = str(readiness_receipt.get("path") or "")
    readiness_path = _project_file(readiness_path_value, root)
    readiness_expected = str(readiness_receipt.get("sha256") or "").lower()
    readiness_actual = file_sha256(readiness_path) if readiness_path is not None else None
    brief_path = Path(root).resolve() / "需求" / "brief.json"
    brief_actual = file_sha256(brief_path)
    readiness_status = {
        "path": readiness_path_value, "expected_sha256": readiness_expected,
        "actual_sha256": readiness_actual, "brief_sha256": brief_actual,
        "current": bool(_full_sha256(readiness_expected) and readiness_actual == readiness_expected
                        and brief_actual == readiness_receipt.get("brief_sha256")
                        and readiness_receipt.get("mode") == "formal"
                        and readiness_receipt.get("release_ready") is True),
    }
    if not readiness_status["current"]:
        findings.append({"severity": "block", "code": "campaign_readiness_binding_stale",
                         "msg": "实验预注册绑定的 formal campaign readiness 或当前 brief 已变化"})
    return {"verified": not any(row["severity"] == "block" for row in findings[finding_start:]),
            "assets": assets, "config_evidence": config_status, "campaign_readiness": readiness_status}


def _observed_through(input_rows):
    values = []
    for row in input_rows:
        raw = str(row.get("observed_through") or row.get("date") or "").strip()
        try:
            values.append(date.fromisoformat(raw))
        except ValueError:
            continue
    return max(values).isoformat() if values else None


def _observed_through_by_variant(input_rows):
    grouped = defaultdict(list)
    for row in input_rows:
        variant_id = str(row.get("variant_id") or "").strip()
        raw = str(row.get("observed_through") or row.get("date") or "").strip()
        if not variant_id:
            continue
        try:
            grouped[variant_id].append(date.fromisoformat(raw))
        except ValueError:
            continue
    return {variant_id: max(values).isoformat() for variant_id, values in grouped.items() if values}


def _receipt_evidence_valid(receipt, root):
    path_value = str(receipt.get("evidence_path") or receipt.get("evidence_file") or "").strip()
    expected = str(receipt.get("evidence_sha256") or "").strip().lower()
    path = _project_file(path_value, root)
    if path is None or not _full_sha256(expected):
        return False, "missing"
    if root is None:
        return True, "structure_only"
    return file_sha256(path) == expected, str(path)


def _platform_result(validation, root, findings, variants, primary_kpi):
    plan = validation.get("plan") if isinstance(validation.get("plan"), dict) else {}
    config = validation.get("platform_configuration") if isinstance(validation.get("platform_configuration"), dict) else {}
    receipt = validation.get("platform_result_receipt")
    if not isinstance(receipt, dict):
        findings.append({"severity": "block", "code": "platform_result_receipt_missing",
                         "msg": "platform_native 缺 投放反馈/platform_experiment_result.json；本地聚合只能诊断"})
        return {"verified": False, "receipt": None}
    errors = []
    expected_experiment_id = str(config.get("experiment_id") or
                                 ((plan.get("platform_experiment") or {}).get("experiment_id") if isinstance(plan.get("platform_experiment"), dict) else "") or "")
    actual_experiment_id = str(receipt.get("experiment_id") or "")
    if not expected_experiment_id or actual_experiment_id != expected_experiment_id:
        errors.append(("platform_result_experiment_id_mismatch", "平台结果 experiment_id 与预注册配置不一致"))
    if str(receipt.get("status") or "").lower() != "completed":
        errors.append(("platform_result_not_completed", "平台结果 receipt.status 必须为 completed"))
    receipt_kpi = str(receipt.get("primary_kpi") or receipt.get("metric") or "").upper()
    if receipt_kpi != primary_kpi:
        errors.append(("platform_result_kpi_mismatch", "平台结果 KPI 与预注册 primary_kpi 不一致"))
    expected_bindings = {str(v.get("variant_id") or ""): str(v.get("asset_sha256") or "").lower()
                         for v in plan.get("variants") or [] if isinstance(v, dict)}
    actual_bindings = _bindings(receipt.get("asset_bindings"))
    if actual_bindings != expected_bindings:
        errors.append(("platform_result_asset_binding_mismatch", "平台结果必须逐变体绑定当前素材 SHA"))
    evidence_ok, evidence_detail = _receipt_evidence_valid(receipt, root)
    if not evidence_ok:
        errors.append(("platform_result_evidence_stale", "平台结果证据缺失、SHA 非法或文件已变化"))
    source = validation.get("platform_result_source") if isinstance(validation.get("platform_result_source"), dict) else {}
    source_path_value = str(source.get("path") or "")
    source_path = _project_file(source_path_value, root)
    source_expected = str(source.get("sha256") or "").lower()
    if root is None or source_path is None or not _full_sha256(source_expected) or file_sha256(source_path) != source_expected:
        errors.append(("platform_result_receipt_source_stale",
                       "platform_experiment_result.json 自身未以作品内 path+sha256 绑定或已变化"))
    conclusion = str(receipt.get("conclusion") or "").lower()
    if conclusion not in {"winner", "no_winner", "inconclusive"}:
        errors.append(("platform_result_conclusion_invalid", "conclusion 必须为 winner/no_winner/inconclusive"))
    winner = str(receipt.get("winner_variant_id") or "").strip() or None
    expected_ids = set(expected_bindings)
    if conclusion == "winner" and winner not in expected_ids:
        errors.append(("platform_result_winner_invalid", "winner_variant_id 不属于预注册变体"))
    if conclusion != "winner" and winner is not None:
        errors.append(("platform_result_winner_unexpected", "非 winner 结论不得携带 winner_variant_id"))
    for code, msg in errors:
        findings.append({"severity": "block", "code": code, "msg": msg})
    return {
        "verified": not errors,
        "experiment_id": expected_experiment_id or None,
        "conclusion": conclusion or None,
        "winner_variant_id": winner,
        "primary_kpi": receipt_kpi or None,
        "evidence": evidence_detail,
        "receipt_source": source,
        "asset_bindings": actual_bindings,
        "receipt": receipt,
    }


def rows(path: Path):
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def number(value):
    try:
        parsed = float(str(value or 0).replace(",", ""))
        return parsed if math.isfinite(parsed) else 0.0
    except (TypeError, ValueError):
        return 0.0


def wilson(successes, total, z=1.96):
    if total <= 0:
        return [0.0, 0.0]
    # Keep diagnostics renderable for malformed exports; build() separately
    # records the impossible count relationship as a blocking finding.
    successes = min(max(0.0, successes), total)
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [round(max(0, center - margin), 6), round(min(1, center + margin), 6)]


def two_proportion_score_test(success_a, total_a, success_b, total_b):
    """Two-sided pooled two-proportion score/z test."""
    if total_a <= 0 or total_b <= 0:
        return {"z": None, "p_value": None, "rate_difference": None}
    rate_a, rate_b = success_a / total_a, success_b / total_b
    pooled = (success_a + success_b) / (total_a + total_b)
    variance = pooled * (1 - pooled) * (1 / total_a + 1 / total_b)
    difference = rate_a - rate_b
    if variance <= 0:
        z_value = 0.0 if difference == 0 else (math.inf if difference > 0 else -math.inf)
        p_value = 1.0 if difference == 0 else 0.0
    else:
        z_value = difference / math.sqrt(variance)
        p_value = 2 * (1 - NormalDist().cdf(abs(z_value)))
    return {"z": z_value, "p_value": max(0.0, min(1.0, p_value)),
            "rate_difference": difference}


def _metrics(vals):
    imp, clicks, conv = vals["impressions"], vals["clicks"], vals["conversions"]
    spend, revenue = vals["spend"], vals["revenue"]
    return {
        "ctr": round(clicks / imp, 6) if imp else 0,
        "cvr": round(conv / clicks, 6) if clicks else 0,
        "cpa": round(spend / conv, 4) if conv else None,
        "roas": round(revenue / spend, 4) if spend else None,
        "view_3s_rate": round(vals["video_3s"] / imp, 6) if imp else 0,
        "completion_rate": round(vals["completed_views"] / imp, 6) if imp else 0,
        "ctr_wilson95": wilson(clicks, imp),
        "cvr_wilson95": wilson(conv, clicks),
    }


def _component_rollup(input_rows, key, min_impressions):
    grouped = defaultdict(lambda: {k: 0.0 for k in NUMERIC})
    for row in input_rows:
        cid = str(row.get(key) or "").strip()
        if not cid:
            continue
        for field in NUMERIC:
            grouped[cid][field] += number(row.get(field))
    return [{"id": cid, **{k: round(v, 4) for k, v in vals.items()}, **_metrics(vals),
             "sample_qualified": vals["impressions"] >= min_impressions}
            for cid, vals in sorted(grouped.items())]


def _fatigue(rows_by_variant):
    findings = []
    for vid, rows_ in rows_by_variant.items():
        dated = sorted((r for r in rows_ if str(r.get("date") or "").strip()), key=lambda r: str(r.get("date")))
        if len(dated) < 2:
            continue
        cut = max(1, len(dated) // 2)
        halves = (dated[:cut], dated[cut:])
        if not halves[1]:
            continue
        summary = []
        for half in halves:
            vals = {k: sum(number(r.get(k)) for r in half) for k in NUMERIC}
            imp = vals["impressions"]
            avg_frequency = (sum(number(r.get("frequency")) * number(r.get("impressions")) for r in half) / imp
                             if imp else 0)
            summary.append({**_metrics(vals), "frequency": avg_frequency})
        early, late = summary
        ctr_drop = early["ctr"] > 0 and late["ctr"] < early["ctr"] * 0.8
        roas_drop = early["roas"] not in (None, 0) and late["roas"] is not None and late["roas"] < early["roas"] * 0.8
        frequency_up = late["frequency"] >= early["frequency"] + 0.5
        if frequency_up and (ctr_drop or roas_drop):
            findings.append({
                "severity": "warn", "code": "creative_fatigue", "variant_id": vid,
                "msg": "后半段 frequency 上升且 CTR/ROAS 较前半段下降≥20%，建议刷新 hook/caption/开场",
                "early": early, "late": late,
            })
    return findings


def build(input_rows, min_impressions=1000, measurement=None, experiment_validation=None, root=None):
    """Build a diagnostic report and, only with current evidence, an experiment verdict.

    ``min_impressions`` remains a low-cost operations screen. It never substitutes
    for an a-priori power target and is deliberately excluded from local winner
    qualification.
    """
    input_rows = list(input_rows)
    measurement = measurement or {}
    findings = []
    validation = _revalidated_experiment(experiment_validation, root, findings)
    plan_approved = bool(((validation.get("summary") or {}).get("approved")))
    registered_plan = validation.get("plan") if isinstance(validation.get("plan"), dict) else {}
    design_mode = str(validation.get("design_mode") or registered_plan.get("design_mode") or "").lower() or None
    primary_kpi = str(measurement.get("primary_kpi") or registered_plan.get("primary_kpi") or "CTR").upper()
    agg = defaultdict(lambda: {k: 0.0 for k in NUMERIC})
    frequency_weighted = defaultdict(float)
    meta_values = defaultdict(lambda: {key: set() for key in CORE_STRATA + OPTIONAL_CONSTANTS})
    rows_by_variant = defaultdict(list)
    present_fields = defaultdict(set)
    required_count_fields = set(BINOMIAL_METRICS.get(primary_kpi, ())[:2]) if design_mode == "local_binomial" else set()
    for row_index, row in enumerate(input_rows, start=1):
        vid = str(row.get("variant_id") or "").strip()
        if not vid:
            continue
        parsed_counts = {}
        for key in BINOMIAL_COUNTS:
            raw_present = key in row and str(row.get(key) if row.get(key) is not None else "").strip() != ""
            if not raw_present:
                if key in required_count_fields:
                    findings.append({"severity": "block", "code": "metric_count_missing", "variant_id": vid,
                                     "row": row_index, "field": key,
                                     "msg": f"变体 {vid} 第 {row_index} 行缺预注册二项计数字段 {key}"})
                continue
            try:
                parsed_counts[key] = _strict_count(row.get(key))
                present_fields[vid].add(key)
            except ValueError as exc:
                findings.append({"severity": "block", "code": "binomial_count_invalid", "variant_id": vid,
                                 "row": row_index, "field": key, "detail": str(exc),
                                 "msg": f"变体 {vid} 第 {row_index} 行 {key} 必须是有限非负整数"})
        if {"clicks", "impressions"} <= set(parsed_counts) and parsed_counts["clicks"] > parsed_counts["impressions"]:
            findings.append({"severity": "block", "code": "binomial_hierarchy_invalid", "variant_id": vid,
                             "row": row_index, "msg": "逐行必须 clicks <= impressions"})
        if {"conversions", "clicks"} <= set(parsed_counts) and parsed_counts["conversions"] > parsed_counts["clicks"]:
            findings.append({"severity": "block", "code": "binomial_hierarchy_invalid", "variant_id": vid,
                             "row": row_index, "msg": "逐行必须 conversions <= clicks"})
        for key in NUMERIC:
            agg[vid][key] += parsed_counts.get(key, 0) if key in BINOMIAL_COUNTS else number(row.get(key))
            if key not in BINOMIAL_COUNTS and key in row and str(row.get(key) if row.get(key) is not None else "").strip() != "":
                present_fields[vid].add(key)
        frequency_weighted[vid] += number(row.get("frequency")) * number(row.get("impressions"))
        for field in CORE_STRATA + OPTIONAL_CONSTANTS:
            value = str(row.get(field) or "").strip()
            if value:
                meta_values[vid][field].add(value)
        rows_by_variant[vid].append(row)

    metric_counts = BINOMIAL_METRICS.get(primary_kpi)
    variants = []
    for vid, vals in agg.items():
        imp = vals["impressions"]
        stable_meta = {field: next(iter(values)) if len(values) == 1 else None
                       for field, values in meta_values[vid].items()}
        row = {
            "variant_id": vid, **stable_meta, **{k: round(v, 4) for k, v in vals.items()},
            **_metrics(vals),
            "frequency": round(frequency_weighted[vid] / imp, 4) if imp else 0,
            "sample_qualified": imp >= min_impressions,
            "strata_values": {field: sorted(values) for field, values in meta_values[vid].items()},
        }
        if metric_counts:
            numerator_field, denominator_field, _ = metric_counts
            row["inference_numerator"] = vals[numerator_field]
            row["inference_denominator"] = vals[denominator_field]
        variants.append(row)
        if vals["clicks"] > vals["impressions"] or vals["conversions"] > vals["clicks"]:
            findings.append({"severity": "block", "code": "binomial_counts_invalid", "variant_id": vid,
                             "msg": f"变体 {vid} 的 clicks>impressions 或 conversions>clicks，须修正原始导出"})

    metric_key = {"CTR": "ctr", "CVR": "cvr", "CPA": "cpa", "ROAS": "roas"}.get(primary_kpi, "ctr")

    def rank(row):
        value = row[metric_key]
        score = float("-inf") if value is None else (-value if metric_key == "cpa" else value)
        return value is not None, score

    variants.sort(key=rank, reverse=True)
    verdict = "directional_only" if variants else "insufficient_data"
    winner = None
    binding_currentness = _current_plan_bindings(
        registered_plan, root, findings, validation.get("campaign_readiness")
    ) if plan_approved else None
    strata = {(v.get("platform") or "", v.get("placement") or "", v.get("audience") or "") for v in variants}
    comparable = len(strata) <= 1 and all(
        len(meta_values[v["variant_id"]][field]) == 1 for v in variants for field in CORE_STRATA
    )
    inference_invalid = any(finding["severity"] == "block" for finding in findings)

    if not variants:
        findings.append({"severity": "block", "code": "no_valid_variants", "msg": "没有带 variant_id 的有效行"})
    if not comparable:
        inference_invalid = True
        findings.append({"severity": "block", "code": "non_comparable_strata",
                         "msg": "变体跨平台、placement 或受众，不在同一可比层，禁止本地宣布胜者"})
    if primary_kpi not in BINOMIAL_METRICS:
        findings.append({"severity": "warn", "code": "aggregate_metric_no_interval",
                         "msg": f"primary_kpi={primary_kpi} 仅有聚合值、无方差/逐事件数据，不做本地显著性胜者判定"})
    if not plan_approved:
        inference_invalid = True
        findings.append({"severity": "block", "code": "experiment_not_preregistered",
                         "msg": "缺已批准且绑定当前计划的实验预注册；旧计划或未注册数据只可诊断"})
    else:
        plan_kpi = str(registered_plan.get("primary_kpi") or "").upper()
        if plan_kpi and plan_kpi != primary_kpi:
            inference_invalid = True
            findings.append({"severity": "block", "code": "primary_kpi_drift",
                             "msg": f"报告 KPI={primary_kpi} 与预注册 KPI={plan_kpi} 不一致"})
        expected_ids = {str(row.get("variant_id") or "") for row in registered_plan.get("variants") or []}
        actual_ids = {row["variant_id"] for row in variants}
        unexpected = sorted(actual_ids - expected_ids)
        missing_ids = sorted(expected_ids - actual_ids)
        if unexpected:
            inference_invalid = True
            findings.append({"severity": "block", "code": "unregistered_variant",
                             "msg": "数据含未预注册变体：" + "、".join(unexpected)})
        if missing_ids:
            inference_invalid = True
            findings.append({"severity": "warn", "code": "registered_variant_missing_data",
                             "msg": "预注册变体无数据：" + "、".join(missing_ids)})
        constants = registered_plan.get("held_constant") if isinstance(registered_plan.get("held_constant"), dict) else {}
        expected_by_field = {field: str(registered_plan.get(field) or "") for field in CORE_STRATA}
        expected_by_field.update({
            "conversion_event": str(registered_plan.get("conversion_event") or ""),
            "attribution_window": str(registered_plan.get("attribution_window") or ""),
            "landing_page": str(constants.get("landing_page") or ""),
            "bidding": str(constants.get("bidding") or ""),
            "budget": str(constants.get("budget") or ""),
        })
        for variant in variants:
            vid = variant["variant_id"]
            for field in CORE_STRATA + OPTIONAL_CONSTANTS:
                observed = meta_values[vid][field]
                expected = expected_by_field.get(field, "")
                if len(observed) > 1:
                    inference_invalid = True
                    findings.append({"severity": "block", "code": f"within_variant_{field}_drift",
                                     "variant_id": vid,
                                     "msg": f"变体 {vid} 内 {field} 出现多个值：{sorted(observed)}"})
                elif observed and expected and observed != {expected}:
                    inference_invalid = True
                    findings.append({"severity": "block", "code": f"{field}_drift", "variant_id": vid,
                                     "msg": f"变体 {vid} 数据 {field}={sorted(observed)} 与预注册 {expected} 不一致"})
                elif not observed and field in CORE_STRATA:
                    inference_invalid = True
                    findings.append({"severity": "block", "code": f"{field}_unverified", "variant_id": vid,
                                     "msg": f"变体 {vid} 原始数据未带 {field}，无法核验预注册不变量"})
                elif not observed and field in OPTIONAL_CONSTANTS:
                    findings.append({"severity": "warn", "code": f"{field}_unverified", "variant_id": vid,
                                     "msg": f"变体 {vid} 原始数据未带 {field}，仅凭预注册声明保持不变"})

    local_inference = None
    platform_inference = None
    terminal_analysis_complete = False
    if plan_approved and design_mode == "local_binomial":
        analysis = validation.get("power_analysis") if isinstance(validation.get("power_analysis"), dict) else {}
        metric_definition = analysis.get("metric_definition") if isinstance(analysis.get("metric_definition"), dict) else {}
        expected_metric = BINOMIAL_METRICS.get(primary_kpi)
        expected_unit = {"impressions": "impression", "clicks": "click"}.get(str(metric_definition.get("denominator") or ""))
        if (not expected_unit or analysis.get("analysis_unit") != expected_unit
                or analysis.get("randomization_unit") != expected_unit
                or analysis.get("independent_bernoulli") is not True):
            inference_invalid = True
            findings.append({"severity": "block", "code": "analysis_randomization_unit_mismatch",
                             "msg": "本地推断的随机化单元、分析单元与 denominator 不一致，或未确认独立 Bernoulli"})
        target = analysis.get("effective_stopping_sample_per_arm") or analysis.get("required_sample_per_arm")
        try:
            target = int(target)
            if target <= 0:
                raise ValueError
        except (TypeError, ValueError):
            target = None
            inference_invalid = True
            findings.append({"severity": "block", "code": "power_target_missing",
                             "msg": "已批准计划缺有效的每臂功效样本量；不得用 min_impressions 顶替"})
        if expected_metric:
            numerator_field, denominator_field, _ = expected_metric
            if (metric_definition.get("numerator"), metric_definition.get("denominator")) != (numerator_field, denominator_field):
                inference_invalid = True
                findings.append({"severity": "block", "code": "metric_definition_drift",
                                 "msg": "反馈报告 numerator/denominator 与预注册计数口径不一致"})
            for variant in variants:
                vid = variant["variant_id"]
                if not {numerator_field, denominator_field} <= present_fields[vid]:
                    inference_invalid = True
                    findings.append({"severity": "block", "code": "metric_count_fields_missing", "variant_id": vid,
                                     "msg": f"变体 {vid} 缺 {numerator_field}/{denominator_field} 原始计数字段"})
                variant["power_sample_qualified"] = bool(target and variant["inference_denominator"] >= target)

        stopping = analysis.get("stopping_rule") if isinstance(analysis.get("stopping_rule"), dict) else {}
        stop_type = str(stopping.get("type") or "").lower()
        sample_condition = bool(
            variants and target and actual_ids == expected_ids
            and all(v.get("power_sample_qualified") for v in variants)
        )
        observed_through = _observed_through(input_rows)
        observed_through_by_variant = _observed_through_by_variant(input_rows)
        calendar_condition = True
        if stop_type == "fixed_horizon":
            try:
                end_date = date.fromisoformat(str(registered_plan.get("end_date")))
                registered_ids = {str(row.get("variant_id") or "") for row in registered_plan.get("variants") or []}
                calendar_condition = bool(registered_ids and all(
                    variant_id in observed_through_by_variant
                    and date.fromisoformat(observed_through_by_variant[variant_id]) >= end_date
                    for variant_id in registered_ids
                ))
            except ValueError:
                calendar_condition = False
        elif stop_type != "fixed_sample":
            calendar_condition = False
        stopping_satisfied = sample_condition and calendar_condition and stopping.get("no_early_stopping") is True
        if not stopping_satisfied:
            findings.append({"severity": "warn", "code": "stopping_rule_not_satisfied",
                             "msg": "尚未同时满足预注册功效样本量和停止条件；本地推断仅可作 directional_only",
                             "sample_condition": sample_condition, "calendar_condition": calendar_condition})

        adjusted_alpha = analysis.get("planning_alpha_per_comparison")
        try:
            adjusted_alpha = float(adjusted_alpha)
            if not math.isfinite(adjusted_alpha) or not 0 < adjusted_alpha < 1:
                raise ValueError
            z_value = NormalDist().inv_cdf(1 - adjusted_alpha / 2)
        except (TypeError, ValueError, ArithmeticError):
            z_value = None
            inference_invalid = True
            findings.append({"severity": "block", "code": "adjusted_alpha_missing",
                             "msg": "预注册缺多重比较调整后的 alpha，禁止本地胜者结论"})
        interval_name = None
        if expected_metric and z_value is not None:
            numerator_field, denominator_field, _ = expected_metric
            interval_name = f"{primary_kpi.lower()}_wilson_preregistered"
            for variant in variants:
                variant[interval_name] = wilson(variant[numerator_field], variant[denominator_field], z_value)
        method = str(analysis.get("multiple_comparison_method") or "")
        expected_comparison_count = max(1, len(expected_ids) * (len(expected_ids) - 1) // 2)
        try:
            comparison_count = int(analysis.get("comparison_count"))
            if comparison_count != expected_comparison_count:
                raise ValueError
        except (TypeError, ValueError):
            comparison_count = None
            inference_invalid = True
            findings.append({"severity": "block", "code": "comparison_count_invalid",
                             "msg": "预注册多重比较数量与变体全集不一致，禁止本地胜者结论"})
        method_valid = method in {"none", "bonferroni"} and not (
            expected_comparison_count > 1 and method != "bonferroni"
        )
        pairwise_tests = []
        if expected_metric and z_value is not None and comparison_count is not None and method_valid:
            numerator_field, denominator_field, _ = expected_metric
            for left_index, left in enumerate(variants):
                for right in variants[left_index + 1:]:
                    test = two_proportion_score_test(
                        left[numerator_field], left[denominator_field],
                        right[numerator_field], right[denominator_field],
                    )
                    p_value = test["p_value"]
                    adjusted_p = None if p_value is None else min(1.0, p_value * comparison_count) if method == "bonferroni" else p_value
                    pairwise_tests.append({
                        "left_variant_id": left["variant_id"], "right_variant_id": right["variant_id"],
                        **test, "adjusted_p_value": adjusted_p,
                        "significant_at_preregistered_alpha": bool(p_value is not None and p_value <= adjusted_alpha),
                    })
        else:
            inference_invalid = True
            findings.append({"severity": "block", "code": "local_inference_method_invalid",
                             "msg": "本地推断只允许 none/bonferroni 的 pooled two-proportion score test"})
        top_id = variants[0]["variant_id"] if variants else None
        top_tests = [row for row in pairwise_tests if row["left_variant_id"] == top_id]
        all_required_pairwise_significant = bool(
            len(top_tests) == max(0, len(expected_ids) - 1)
            and all(row["rate_difference"] is not None and row["rate_difference"] > 0
                    and row["significant_at_preregistered_alpha"] for row in top_tests)
        )
        if not inference_invalid and comparable and stopping_satisfied and all_required_pairwise_significant:
            verdict, winner = "local_qualified_winner", variants[0]["variant_id"]
        terminal_analysis_complete = stopping_satisfied and not inference_invalid
        local_inference = {
            "metric_definition": metric_definition,
            "required_sample_per_arm": analysis.get("required_sample_per_arm"),
            "effective_stopping_sample_per_arm": target,
            "min_impressions_is_power_target": False,
            "multiple_comparison_method": analysis.get("multiple_comparison_method"),
            "comparison_count": comparison_count,
            "familywise_alpha": analysis.get("alpha_familywise"),
            "planning_alpha_per_comparison": adjusted_alpha,
            "power": analysis.get("power"),
            "stopping_rule": stopping,
            "observed_through": observed_through,
            "observed_through_by_variant": observed_through_by_variant,
            "sample_condition": sample_condition,
            "calendar_condition": calendar_condition,
            "stopping_satisfied": stopping_satisfied,
            "decision_test": "pooled_two_proportion_score_test",
            "pairwise_tests": pairwise_tests,
            "all_required_pairwise_significant": all_required_pairwise_significant,
            "interval_field": interval_name,
            "interval_role": "display_only_not_decision_rule",
        }
    elif plan_approved and design_mode == "platform_native":
        platform_inference = _platform_result(validation, root, findings, variants, primary_kpi)
        if platform_inference["verified"] and not inference_invalid:
            terminal_analysis_complete = True
            conclusion = platform_inference["conclusion"]
            if conclusion == "winner":
                verdict, winner = "platform_qualified_winner", platform_inference["winner_variant_id"]
            elif conclusion == "no_winner":
                verdict = "platform_no_winner"
            else:
                verdict = "platform_inconclusive"
    elif plan_approved:
        findings.append({"severity": "block", "code": "experiment_design_mode_invalid",
                         "msg": "已批准计划缺可识别 design_mode；仅可诊断"})

    if variants and verdict in {"directional_only", "insufficient_data"}:
        findings.append({"severity": "warn", "code": "no_qualified_winner",
                         "msg": "计划、功效、停止条件或预注册 score-test 证据不足，不宣布胜者"})
    findings.extend(_fatigue(rows_by_variant))
    for variant in variants:
        if variant["sample_qualified"] and variant["video_3s"] > 0 and variant["view_3s_rate"] < HOOK_RATE_FLOOR:
            findings.append({
                "severity": "warn", "code": "hook_rate_low", "variant_id": variant["variant_id"],
                "msg": (f"变体 {variant['variant_id']} 3s 观看率 {variant['view_3s_rate']:.1%} < 基准地板 {HOOK_RATE_FLOOR:.0%}"
                        f"——前 3 秒（hook_id={variant.get('hook_id') or '?'}）在流量里失败，后段再强也到不了；"
                        "优先单变量换 hook 复测，别急着改 message/CTA"),
            })
    components = {key: _component_rollup(input_rows, key, min_impressions)
                  for key in ("hook_id", "message_id", "cta_id")}
    has_blocks = any(finding["severity"] == "block" for finding in findings)
    analysis_status = "invalid" if has_blocks else ("complete" if terminal_analysis_complete else "interim")
    return {
        "schema_version": 5, "kind": "ad_feedback_report", "verdict": verdict, "winner": winner,
        "analysis_status": analysis_status,
        "primary_kpi": primary_kpi, "comparable_strata": comparable,
        "experiment_plan_approved": plan_approved, "design_mode": design_mode,
        "min_impressions": min_impressions, "min_impressions_role": "diagnostic_only",
        "variants": variants, "local_inference": local_inference, "platform_inference": platform_inference,
        "binding_currentness": binding_currentness,
        "methodology": {
            "local_intervals": "Wilson interval is display-only; winner decisions use the preregistered pooled two-proportion score test",
            "local_winner_boundary": "Requires approved a-priori power plan, strict count semantics, matching independent analysis/randomization units, all-arm target attainment, stopping-rule completion, comparable strata, and multiplicity-adjusted score tests",
            "platform_boundary": "A current platform result receipt bound to experiment ID, KPI, evidence SHA, and every asset SHA takes precedence",
            "aggregate_cpa_roas": "directional only without event-level variance/randomization data",
        },
        "components": components,
        "recommendations": ["先单变量刷新 hook/message/CTA，再在同平台同受众同预算条件复测"] if findings else [],
        "summary": {"block": sum(1 for finding in findings if finding["severity"] == "block"),
                    "warn": sum(1 for finding in findings if finding["severity"] == "warn")},
        "findings": findings,
    }


def markdown(report):
    lines = ["# Ad Feedback", "", f"- verdict: {report['verdict']}", f"- winner: {report['winner'] or '—'}",
             f"- analysis_status: {report.get('analysis_status') or 'unknown'}",
             f"- design_mode: {report.get('design_mode') or 'unregistered'}",
             f"- min_impressions: {report.get('min_impressions')} (diagnostic only; not power)"]
    local = report.get("local_inference") if isinstance(report.get("local_inference"), dict) else None
    platform = report.get("platform_inference") if isinstance(report.get("platform_inference"), dict) else None
    if local:
        lines.extend([
            f"- powered target / arm: {local.get('effective_stopping_sample_per_arm') or '—'}",
            f"- stopping satisfied: {local.get('stopping_satisfied')}",
            f"- observed through: {local.get('observed_through') or 'not required / unavailable'}",
        ])
    if platform:
        lines.extend([
            f"- platform experiment: {platform.get('experiment_id') or '—'}",
            f"- platform receipt verified: {platform.get('verified')}",
        ])
    lines.extend(["",
             "| variant | hook | message | CTA | impressions | CTR | CVR | CPA | ROAS | 3s rate | diagnostic sample | powered sample |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|"])
    for v in report["variants"]:
        lines.append(f"| {v['variant_id']} | {v.get('hook_id') or ''} | {v.get('message_id') or ''} | {v.get('cta_id') or ''} | {v['impressions']:.0f} | {v['ctr']:.2%} | {v['cvr']:.2%} | {v['cpa'] or '—'} | {v['roas'] or '—'} | {v['view_3s_rate']:.2%} | {v['sample_qualified']} | {v.get('power_sample_qualified', '—')} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--input", required=True)
    ap.add_argument("--min-impressions", type=int, default=1000)
    ap.add_argument("--mark-progress", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    brief_path = root / "需求" / "brief.json"
    try:
        measurement = (json.loads(brief_path.read_text(encoding="utf-8")) or {}).get("measurement") or {}
    except Exception:
        measurement = {}
    validation_path = root / "投放反馈" / "experiment_plan_validation.json"
    try:
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        canonical = json.loads((root / "投放反馈" / "experiment_plan.json").read_text(encoding="utf-8"))
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from experiment_plan import plan_sha256  # local ad-line module
        if validation.get("plan_sha256") != plan_sha256(canonical):
            validation = {}
    except Exception:
        validation = {}
    result_receipt_path = root / "投放反馈" / "platform_experiment_result.json"
    if result_receipt_path.is_file() and validation:
        try:
            validation = dict(validation)
            validation["platform_result_receipt"] = json.loads(result_receipt_path.read_text(encoding="utf-8"))
            validation["platform_result_source"] = {
                "path": str(result_receipt_path.relative_to(root)),
                "sha256": file_sha256(result_receipt_path),
            }
        except Exception:
            # The report will fail closed with platform_result_receipt_missing/invalid.
            pass
    input_path = Path(ns.input).resolve()
    effective_min_impressions = ns.min_impressions
    if bool(((validation or {}).get("summary") or {}).get("approved")):
        plan_measurement = (validation.get("plan") or {}) if isinstance(validation.get("plan"), dict) else {}
        measurement = dict(measurement)
        if plan_measurement.get("primary_kpi"):
            measurement["primary_kpi"] = plan_measurement["primary_kpi"]
        if plan_measurement.get("conversion_event"):
            measurement["conversion_event"] = plan_measurement["conversion_event"]
        try:
            effective_min_impressions = int(plan_measurement.get("min_impressions"))
        except (TypeError, ValueError):
            pass
    raw_dir = root / "投放反馈" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    try:
        raw_dir.resolve().relative_to(root)
    except (OSError, RuntimeError, ValueError):
        print("[block] 投放反馈/raw 必须是作品根内真实目录，不能是越界 symlink", file=sys.stderr)
        return 1
    canonical_input = raw_dir / input_path.name
    if canonical_input.is_symlink():
        print("[block] canonical raw 目标不能是 symlink", file=sys.stderr)
        return 1
    if input_path != canonical_input.resolve():
        # Copy to a unique sibling and atomically replace the destination.  This
        # avoids following a pre-existing destination link/hardlink and ensures
        # the parser sees a complete canonical snapshot.
        with tempfile.NamedTemporaryFile(prefix=".feedback-", suffix=".tmp", dir=raw_dir,
                                         delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            shutil.copy2(input_path, temp_path)
            os.replace(temp_path, canonical_input)
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
    # Parse exactly the bytes that are subsequently SHA-bound.  Parsing an
    # external path first and copying it later creates a TOCTOU gap where the
    # report semantics and receipt could describe different source bytes.
    report = build(rows(canonical_input), effective_min_impressions, measurement, validation, root=root)
    out = root / "投放反馈" / "feedback_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    report["source_data"] = {
        "path": str(canonical_input.relative_to(root)),
        "sha256": file_sha256(canonical_input),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    registered = validation.get("plan") if isinstance(validation.get("plan"), dict) else {}
    variant_receipts = {}
    for row in registered.get("variants") or []:
        if not isinstance(row, dict) or not row.get("variant_id"):
            continue
        asset_path = str(row.get("asset_path") or "")
        resolved = _project_file(asset_path, root)
        variant_receipts[str(row["variant_id"])] = {
            "path": asset_path,
            "sha256": file_sha256(resolved) if resolved is not None else None,
        }
    platform_config = registered.get("platform_experiment") if isinstance(
        registered.get("platform_experiment"), dict) else {}
    config_receipt = platform_config.get("config_receipt") if isinstance(
        platform_config.get("config_receipt"), dict) else {}
    result_receipt = validation.get("platform_result_receipt") if isinstance(
        validation.get("platform_result_receipt"), dict) else {}
    report["analysis_receipts"] = {
        "experiment_plan": {
            "path": "投放反馈/experiment_plan.json",
            "sha256": file_sha256(root / "投放反馈" / "experiment_plan.json"),
        },
        "experiment_validation": {
            "path": "投放反馈/experiment_plan_validation.json",
            "sha256": file_sha256(validation_path),
        },
        "campaign_readiness": dict((validation or {}).get("campaign_readiness") or {}),
        "brief": {
            "path": "需求/brief.json",
            "sha256": file_sha256(root / "需求" / "brief.json"),
        },
        "raw_source": {
            "path": str(canonical_input.relative_to(root)),
            "sha256": file_sha256(canonical_input),
        },
        "variant_assets": variant_receipts,
        "platform_config_evidence": {
            "path": str(config_receipt.get("evidence_path") or config_receipt.get("evidence_file") or ""),
            "sha256": str(config_receipt.get("evidence_sha256") or "") or None,
        },
        "platform_result": dict((validation or {}).get("platform_result_source") or {}),
        "platform_result_evidence": {
            "path": str(result_receipt.get("evidence_path") or result_receipt.get("evidence_file") or ""),
            "sha256": str(result_receipt.get("evidence_sha256") or "") or None,
        },
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    if ns.mark_progress and not report["summary"]["block"] and report.get("analysis_status") == "complete":
        progress = Path(__file__).resolve().parents[2] / "ad-craft" / "scripts" / "progress_set.py"
        subprocess.run([sys.executable, str(progress), "set-stage", str(root), "feedback", "--status", "✅", "--artifact", "投放反馈/feedback_report.json"], check=True)
    print(f"# ad feedback verdict={report['verdict']} variants={len(report['variants'])}")
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
