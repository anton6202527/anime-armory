#!/usr/bin/env python3
"""Validate a preregistered ad creative experiment before spend."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path


VARIABLES = ("hook_id", "message_id", "cta_id")
REQUIRED = ("hypothesis", "primary_kpi", "conversion_event", "attribution_window", "platform", "audience",
            "placement", "randomization_unit", "decision_rule", "start_date", "end_date", "min_impressions")


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


def build(plan, root=None):
    findings = []
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
        if not asset_path or not re_full_sha256(digest):
            findings.append({"severity": "block", "code": "variant_asset_binding_missing", "variant_id": vid,
                             "msg": "每个变体须在花钱前写 asset_path + 64 位 asset_sha256，防止计划与实际素材错位"})
        elif root is not None:
            path = Path(asset_path)
            if not path.is_absolute():
                path = Path(root) / path
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
    return {
        "schema_version": 1, "kind": "ad_experiment_plan_validation",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": plan_sha256(plan),
        "plan": plan, "changed_dimension": next(iter(changed_dimensions), None),
        "methodology": {
            "design": "preregistered single-variable randomized creative experiment",
            "platform_guidance": "Google Ads video experiments recommend comparable arms and a declared success metric; platform-native assignment/significance remains authoritative",
            "source": "https://support.google.com/google-ads/answer/10682377",
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
