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
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path


NUMERIC = ("impressions", "clicks", "conversions", "spend", "revenue", "video_3s", "video_6s", "completed_views")
# 业界信息流基准（2026 采集·会过期快照）：3s 观看率（hook rate）< 25% ≈ 前 3 秒失败，
# 无论后段多强都先修 hook。仅在数据真带 video_3s 时判（全 0 视为字段缺失，不臆造）。
HOOK_RATE_FLOOR = 0.25


def file_sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path):
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def number(value):
    try:
        return float(str(value or 0).replace(",", ""))
    except ValueError:
        return 0.0


def wilson(successes, total, z=1.96):
    if total <= 0:
        return [0.0, 0.0]
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [round(max(0, center - margin), 6), round(min(1, center + margin), 6)]


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


def build(input_rows, min_impressions=1000, measurement=None, experiment_validation=None):
    measurement = measurement or {}
    primary_kpi = str(measurement.get("primary_kpi") or "CTR").upper()
    agg = defaultdict(lambda: {k: 0.0 for k in NUMERIC})
    frequency_weighted = defaultdict(float)
    meta = {}
    rows_by_variant = defaultdict(list)
    for row in input_rows:
        vid = str(row.get("variant_id") or "").strip()
        if not vid:
            continue
        for key in NUMERIC:
            agg[vid][key] += number(row.get(key))
        frequency_weighted[vid] += number(row.get("frequency")) * number(row.get("impressions"))
        meta[vid] = {k: row.get(k) for k in ("hook_id", "message_id", "cta_id", "platform", "placement", "audience")}
        rows_by_variant[vid].append(row)
    variants = []
    for vid, vals in agg.items():
        imp, clicks, conv = vals["impressions"], vals["clicks"], vals["conversions"]
        variants.append({
            "variant_id": vid, **meta.get(vid, {}), **{k: round(v, 4) for k, v in vals.items()},
            **_metrics(vals),
            "frequency": round(frequency_weighted[vid] / imp, 4) if imp else 0,
            "sample_qualified": imp >= min_impressions,
        })
    metric_key = {"CTR": "ctr", "CVR": "cvr", "CPA": "cpa", "ROAS": "roas"}.get(primary_kpi, "ctr")
    def rank(row):
        value = row[metric_key]
        score = float("-inf") if value is None else (-value if metric_key == "cpa" else value)
        return row["sample_qualified"], value is not None, score
    variants.sort(key=rank, reverse=True)
    verdict = "insufficient_data"
    winner = None
    strata = {(v.get("platform") or "", v.get("placement") or "", v.get("audience") or "") for v in variants}
    comparable = len(strata) <= 1
    interval_key = "ctr_wilson95" if primary_kpi == "CTR" else ("cvr_wilson95" if primary_kpi == "CVR" else None)
    if variants and variants[0]["sample_qualified"] and comparable and interval_key:
        if len(variants) == 1 or not variants[1]["sample_qualified"] or variants[0][interval_key][0] > variants[1][interval_key][1]:
            verdict, winner = "qualified_winner", variants[0]["variant_id"]
        else:
            verdict = "directional_only"
    findings = []
    if not variants:
        findings.append({"severity": "block", "code": "no_valid_variants", "msg": "没有带 variant_id 的有效行"})
    elif verdict != "qualified_winner":
        findings.append({"severity": "warn", "code": "no_qualified_winner", "msg": "样本或区间不足，不宣布胜者"})
    if not comparable:
        findings.append({"severity": "warn", "code": "non_comparable_strata",
                         "msg": "变体跨平台、placement 或受众，不在同一可比层，禁止直接宣布胜者"})
    if primary_kpi not in {"CTR", "CVR"}:
        findings.append({"severity": "warn", "code": "aggregate_metric_no_interval",
                         "msg": f"primary_kpi={primary_kpi} 仅有聚合值、无方差/逐事件数据，不做显著性胜者判定"})
    plan_approved = None if experiment_validation is None else bool(
        ((experiment_validation or {}).get("summary") or {}).get("approved")
    )
    registered_plan = (experiment_validation or {}).get("plan") if isinstance(experiment_validation, dict) else {}
    registered_plan = registered_plan if isinstance(registered_plan, dict) else {}
    if plan_approved:
        plan_kpi = str(registered_plan.get("primary_kpi") or "").upper()
        if plan_kpi and plan_kpi != primary_kpi:
            winner = None
            verdict = "directional_only" if variants else "insufficient_data"
            findings.append({"severity": "block", "code": "primary_kpi_drift",
                             "msg": f"报告 KPI={primary_kpi} 与预注册 KPI={plan_kpi} 不一致"})
        expected_ids = {str(row.get("variant_id") or "") for row in registered_plan.get("variants") or []}
        actual_ids = {row["variant_id"] for row in variants}
        unexpected = sorted(actual_ids - expected_ids)
        missing_ids = sorted(expected_ids - actual_ids)
        if unexpected:
            winner = None
            verdict = "directional_only"
            findings.append({"severity": "block", "code": "unregistered_variant",
                             "msg": "数据含未预注册变体：" + "、".join(unexpected)})
        if missing_ids:
            findings.append({"severity": "warn", "code": "registered_variant_missing_data",
                             "msg": "预注册变体无数据：" + "、".join(missing_ids)})
        for field in ("platform", "placement", "audience"):
            expected = str(registered_plan.get(field) or "")
            observed = {str(v.get(field) or "") for v in variants if str(v.get(field) or "")}
            if expected and observed and observed != {expected}:
                winner = None
                verdict = "directional_only"
                findings.append({"severity": "block", "code": f"{field}_drift",
                                 "msg": f"数据 {field}={sorted(observed)} 与预注册 {expected} 不一致"})
            elif expected and not observed:
                findings.append({"severity": "warn", "code": f"{field}_unverified",
                                 "msg": f"原始数据未带 {field}，无法核验预注册不变量 {expected}"})
    if plan_approved is False:
        winner = None
        verdict = "directional_only" if variants else "insufficient_data"
        findings.append({"severity": "block", "code": "experiment_not_preregistered",
                         "msg": "缺已批准且绑定当前计划的实验预注册；本批数据只可诊断，不得宣布胜者"})
    findings.extend(_fatigue(rows_by_variant))
    for v in variants:
        if v["sample_qualified"] and v["video_3s"] > 0 and v["view_3s_rate"] < HOOK_RATE_FLOOR:
            findings.append({
                "severity": "warn", "code": "hook_rate_low", "variant_id": v["variant_id"],
                "msg": (f"变体 {v['variant_id']} 3s 观看率 {v['view_3s_rate']:.1%} < 基准地板 {HOOK_RATE_FLOOR:.0%}"
                        f"——前 3 秒（hook_id={v.get('hook_id') or '?'}）在流量里失败，后段再强也到不了；"
                        "优先单变量换 hook 复测，别急着改 message/CTA"),
            })
    components = {key: _component_rollup(input_rows, key, min_impressions)
                  for key in ("hook_id", "message_id", "cta_id")}
    return {"schema_version": 3, "kind": "ad_feedback_report", "verdict": verdict, "winner": winner,
            "primary_kpi": primary_kpi, "comparable_strata": comparable,
            "experiment_plan_approved": plan_approved,
            "min_impressions": min_impressions, "variants": variants,
            "methodology": {
                "local_intervals": "Wilson 95% interval for aggregate binomial CTR/CVR only",
                "boundary": "Not equivalent to platform-native randomized experiment inference; platform assignment and significance output take precedence",
                "aggregate_cpa_roas": "directional only without event-level variance/randomization data",
            },
            "components": components,
            "recommendations": ["先单变量刷新 hook/message/CTA，再在同平台同受众同预算条件复测"] if findings else [],
            "summary": {"block": sum(1 for f in findings if f["severity"] == "block"),
                        "warn": sum(1 for f in findings if f["severity"] == "warn")},
            "findings": findings}


def markdown(report):
    lines = ["# Ad Feedback", "", f"- verdict: {report['verdict']}", f"- winner: {report['winner'] or '—'}", "",
             "| variant | hook | message | CTA | impressions | CTR | CVR | CPA | ROAS | 3s rate | qualified |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for v in report["variants"]:
        lines.append(f"| {v['variant_id']} | {v.get('hook_id') or ''} | {v.get('message_id') or ''} | {v.get('cta_id') or ''} | {v['impressions']:.0f} | {v['ctr']:.2%} | {v['cvr']:.2%} | {v['cpa'] or '—'} | {v['roas'] or '—'} | {v['view_3s_rate']:.2%} | {v['sample_qualified']} |")
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
    report = build(rows(input_path), effective_min_impressions, measurement, validation)
    out = root / "投放反馈" / "feedback_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = root / "投放反馈" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    canonical_input = raw_dir / input_path.name
    if input_path != canonical_input.resolve():
        shutil.copy2(input_path, canonical_input)
    report["source_data"] = {
        "path": str(canonical_input.relative_to(root)),
        "sha256": file_sha256(canonical_input),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    if ns.mark_progress and not report["summary"]["block"]:
        progress = Path(__file__).resolve().parents[2] / "ad-craft" / "scripts" / "progress_set.py"
        subprocess.run([sys.executable, str(progress), "set-stage", str(root), "feedback", "--status", "✅", "--artifact", "投放反馈/feedback_report.json"], check=True)
    print(f"# ad feedback verdict={report['verdict']} variants={len(report['variants'])}")
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
