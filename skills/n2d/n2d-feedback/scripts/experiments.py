#!/usr/bin/env python3
"""Creative experiment registry for n2d feedback."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


KIND = "n2d_creative_experiments"
EXPERIMENTS_JSON = "creative_experiments.json"
AUDIT_JSON = "creative_experiment_audit.json"
AUDIT_MD = "creative_experiment_audit.md"


def production_dir(root: str) -> Path:
    return Path(root) / "生产数据"


def experiments_path(root: str) -> Path:
    return production_dir(root) / EXPERIMENTS_JSON


def load_experiments(root: str) -> Dict[str, Any]:
    path = experiments_path(root)
    if not path.is_file():
        return {"kind": KIND, "version": 2, "experiments": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != KIND:
        raise ValueError(f"{path} is not {KIND}")
    data.setdefault("experiments", [])
    data["version"] = max(2, int(data.get("version") or 1))
    return data


def save_experiments(root: str, data: Dict[str, Any]) -> Path:
    path = experiments_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def parse_variant(items: Sequence[str]) -> List[Dict[str, str]]:
    out = []
    for item in items:
        if "=" not in str(item):
            raise ValueError(f"--variant expects id=description: {item}")
        key, value = str(item).split("=", 1)
        out.append({"variant_id": key.strip(), "description": value.strip()})
    return out


def upsert_experiment(
    root: str,
    experiment_id: str,
    *,
    episode: str,
    hypothesis: str,
    variants: Sequence[Dict[str, str]],
    primary_metric: str,
    min_samples: int,
    owner: str = "",
    alpha: float = 0.05,
) -> Dict[str, Any]:
    data = load_experiments(root)
    exp = {
        "experiment_id": experiment_id,
        "episode": episode,
        "hypothesis": hypothesis,
        "variants": list(variants),
        "primary_metric": primary_metric,
        "min_samples": int(min_samples),
        "owner": owner,
        "status": "planned",
        "analysis_policy": {
            "design": "fixed_horizon",
            "alpha": float(alpha),
            "multiple_comparison_correction": "bonferroni_vs_control",
            "min_samples_scope": "per_variant",
            "control_variant": str((variants[0] if variants else {}).get("variant_id") or ""),
        },
    }
    rows = [item for item in data.get("experiments") or [] if isinstance(item, dict) and item.get("experiment_id") != experiment_id]
    rows.append(exp)
    data["experiments"] = sorted(rows, key=lambda item: str(item.get("experiment_id")))
    return data


def read_metrics(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if isinstance(data, dict):
            rows = data.get("rows") or data.get("records") or data.get("metrics")
            return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def _rate(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed > 1.0 and parsed <= 100.0:
        parsed /= 100.0
    return min(1.0, max(0.0, parsed)) if math.isfinite(parsed) else None


def wilson_interval(successes: float, total: float, z: float = 1.959963984540054) -> List[float]:
    if total <= 0:
        return [0.0, 1.0]
    p = min(1.0, max(0.0, successes / total))
    den = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / den
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [round(max(0.0, centre - margin), 6), round(min(1.0, centre + margin), 6)]


def two_proportion_pvalue(success_a: float, n_a: float, success_b: float, n_b: float) -> Optional[float]:
    if n_a <= 0 or n_b <= 0:
        return None
    p_a, p_b = success_a / n_a, success_b / n_b
    pooled = (success_a + success_b) / (n_a + n_b)
    variance = pooled * (1 - pooled) * (1 / n_a + 1 / n_b)
    if variance <= 0:
        return 1.0 if abs(p_a - p_b) < 1e-12 else 0.0
    z = (p_b - p_a) / math.sqrt(variance)
    return math.erfc(abs(z) / math.sqrt(2.0))


def _variant_summary(exp: Mapping[str, Any], matched: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    metric = str(exp.get("primary_metric") or "retention_3s")
    out: Dict[str, Dict[str, Any]] = {}
    for variant in exp.get("variants") or []:
        if not isinstance(variant, Mapping):
            continue
        variant_id = str(variant.get("variant_id") or "")
        rows = [row for row in matched if str(row.get("variant_id") or "") == variant_id]
        plays = 0.0
        successes = 0.0
        valid_rows = 0
        looks: set[int] = set()
        for row in rows:
            n = _number(row.get("plays") or row.get("views") or row.get("samples"), 0.0)
            rate = _rate(row.get(metric))
            explicit_successes = row.get("successes") or row.get(f"{metric}_successes")
            if n <= 0 or (rate is None and explicit_successes in (None, "")):
                continue
            x = _number(explicit_successes, -1.0)
            if x < 0:
                x = float(rate or 0.0) * n
            plays += n
            successes += min(n, max(0.0, x))
            valid_rows += 1
            try:
                if row.get("look_index") not in (None, ""):
                    looks.add(int(row.get("look_index")))
            except (TypeError, ValueError):
                pass
        rate_value = successes / plays if plays else None
        out[variant_id] = {
            "variant_id": variant_id,
            "plays": plays,
            "successes": round(successes, 6),
            "rate": round(rate_value, 6) if rate_value is not None else None,
            "ci95": wilson_interval(successes, plays) if plays else [0.0, 1.0],
            "metric_rows": valid_rows,
            "look_indices": sorted(looks),
        }
    return out


def _experiment_analysis(exp_id: str, exp: Mapping[str, Any], matched: Sequence[Mapping[str, Any]], alpha: float) -> Dict[str, Any]:
    variants = _variant_summary(exp, matched)
    ordered = [str(row.get("variant_id") or "") for row in exp.get("variants") or [] if isinstance(row, Mapping)]
    policy = exp.get("analysis_policy") if isinstance(exp.get("analysis_policy"), Mapping) else {}
    control = str(policy.get("control_variant") or (ordered[0] if ordered else ""))
    comparisons = []
    comparison_count = max(1, len(ordered) - 1)
    control_row = variants.get(control) or {"plays": 0.0, "successes": 0.0, "rate": None}
    for candidate in ordered:
        if candidate == control:
            continue
        row = variants.get(candidate) or {"plays": 0.0, "successes": 0.0, "rate": None}
        p = two_proportion_pvalue(
            float(control_row.get("successes") or 0), float(control_row.get("plays") or 0),
            float(row.get("successes") or 0), float(row.get("plays") or 0),
        )
        adjusted = min(1.0, p * comparison_count) if p is not None else None
        lift = (
            float(row["rate"]) - float(control_row["rate"])
            if row.get("rate") is not None and control_row.get("rate") is not None else None
        )
        comparisons.append({
            "control": control, "candidate": candidate,
            "absolute_lift": round(lift, 6) if lift is not None else None,
            "relative_lift": round(lift / float(control_row["rate"]), 6) if lift is not None and control_row.get("rate") else None,
            "p_value": round(p, 8) if p is not None else None,
            "adjusted_p_value": round(adjusted, 8) if adjusted is not None else None,
            "significant": adjusted is not None and adjusted < alpha,
            "correction": f"bonferroni_m={comparison_count}",
        })
    min_samples = int(exp.get("min_samples") or 0)
    powered = all(float((variants.get(v) or {}).get("plays") or 0) >= min_samples for v in ordered)
    warnings: List[Dict[str, Any]] = []
    total = sum(float((variants.get(v) or {}).get("plays") or 0) for v in ordered)
    shares = [float((variants.get(v) or {}).get("plays") or 0) / total for v in ordered] if total and ordered else []
    if shares and max(shares) - min(shares) > 0.15:
        warnings.append({"code": "allocation_imbalance", "shares": {v: round(float((variants.get(v) or {}).get("plays") or 0) / total, 4) for v in ordered}})
    look_indices = sorted({look for row in variants.values() for look in row.get("look_indices") or []})
    if len(look_indices) > 1 and str(policy.get("design") or "fixed_horizon") == "fixed_horizon":
        warnings.append({"code": "sequential_peeking_without_alpha_spending", "look_indices": look_indices})
    favorable = [row for row in comparisons if row.get("significant") and float(row.get("absolute_lift") or 0) > 0]
    harmful = [row for row in comparisons if row.get("significant") and float(row.get("absolute_lift") or 0) < 0]
    if not powered:
        decision, winner = "insufficient_samples", ""
    elif warnings:
        decision, winner = "analysis_design_review", ""
    elif favorable:
        best = max(favorable, key=lambda row: float(row.get("absolute_lift") or 0))
        decision, winner = "promote_variant", str(best.get("candidate") or "")
    elif harmful and len(harmful) == len(comparisons):
        decision, winner = "keep_control", control
    else:
        decision, winner = "no_significant_difference", ""
    return {
        "experiment_id": exp_id,
        "primary_metric": exp.get("primary_metric"),
        "alpha": alpha,
        "control_variant": control,
        "variant_metrics": variants,
        "comparisons": comparisons,
        "powered": powered,
        "analysis_warnings": warnings,
        "decision": decision,
        "winner": winner,
    }


def audit_metrics(root: str, metrics_path: Path, *, alpha: float = 0.05) -> Dict[str, Any]:
    data = load_experiments(root)
    experiments = {str(item.get("experiment_id")): item for item in data.get("experiments") or [] if isinstance(item, dict)}
    rows = read_metrics(metrics_path)
    ab_ids = sorted({str(row.get("ab_test_id") or "").strip() for row in rows if str(row.get("ab_test_id") or "").strip()})
    missing = [ab for ab in ab_ids if ab not in experiments]
    underpowered = []
    analyses = []
    analysis_warnings = []
    for exp_id, exp in experiments.items():
        variants = {str(v.get("variant_id")) for v in exp.get("variants") or [] if isinstance(v, dict)}
        matched = [row for row in rows if str(row.get("ab_test_id") or "") == exp_id]
        seen_variants = {str(row.get("variant_id") or "") for row in matched if str(row.get("variant_id") or "")}
        analysis = _experiment_analysis(exp_id, exp, matched, float((exp.get("analysis_policy") or {}).get("alpha") or alpha))
        analyses.append(analysis)
        if variants and not variants <= seen_variants:
            underpowered.append({"experiment_id": exp_id, "issue": "missing_variant_metrics", "missing": sorted(variants - seen_variants)})
        for variant_id, summary in (analysis.get("variant_metrics") or {}).items():
            plays = float(summary.get("plays") or 0)
            if plays < int(exp.get("min_samples") or 0):
                underpowered.append({"experiment_id": exp_id, "variant_id": variant_id, "issue": "below_min_samples_per_variant", "plays": plays, "min_samples": exp.get("min_samples")})
        analysis_warnings.extend({"experiment_id": exp_id, **row} for row in analysis.get("analysis_warnings") or [])
    payload = {
        "kind": "n2d_creative_experiment_audit",
        "version": 1,
        "root": root,
        "metrics_path": str(metrics_path),
        "experiments": sorted(experiments),
        "ab_test_ids_in_metrics": ab_ids,
        "missing_experiment_definitions": missing,
        "underpowered": underpowered,
        "analyses": analyses,
        "analysis_warnings": analysis_warnings,
        "statistical_contract": {
            "min_samples_scope": "per_variant",
            "interval": "Wilson 95%",
            "test": "two-sided pooled two-proportion z-test",
            "multiple_comparisons": "Bonferroni vs registered control",
            "default_alpha": alpha,
        },
        "status": "fail" if missing else ("observe" if underpowered or analysis_warnings else "pass"),
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d 投放实验审计",
        "",
        f"- 状态：{payload.get('status')}",
        f"- metrics A/B：{', '.join(payload.get('ab_test_ids_in_metrics') or []) or '—'}",
        "",
        "## 缺实验定义",
        "",
    ]
    lines.extend([f"- {item}" for item in payload.get("missing_experiment_definitions") or []] or ["- 无"])
    lines.extend(["", "## 样本/变体不足", ""])
    lines.extend([f"- {item}" for item in payload.get("underpowered") or []] or ["- 无"])
    lines.extend(["", "## 统计结论", ""])
    for analysis in payload.get("analyses") or []:
        lines.append(f"- {analysis.get('experiment_id')}: {analysis.get('decision')} winner={analysis.get('winner') or '—'}")
        for row in analysis.get("comparisons") or []:
            lines.append(f"  - {row.get('control')} vs {row.get('candidate')}: lift={row.get('absolute_lift')} adjusted_p={row.get('adjusted_p_value')} significant={row.get('significant')}")
    lines.extend(["", "## 设计告警", ""])
    lines.extend([f"- {item}" for item in payload.get("analysis_warnings") or []] or ["- 无"])
    lines.append("")
    return "\n".join(lines)


def write_audit(root: str, payload: Dict[str, Any]) -> None:
    pdir = production_dir(root)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / AUDIT_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (pdir / AUDIT_MD).write_text(render_markdown(payload), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d creative experiment registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("upsert")
    p.add_argument("root")
    p.add_argument("--id", required=True)
    p.add_argument("--episode", required=True)
    p.add_argument("--hypothesis", required=True)
    p.add_argument("--variant", action="append", required=True)
    p.add_argument("--primary-metric", default="retention_3s")
    p.add_argument("--min-samples", type=int, default=1000)
    p.add_argument("--owner", default="")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--write", action="store_true")
    p = sub.add_parser("audit")
    p.add_argument("root")
    p.add_argument("--metrics", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--alpha", type=float, default=0.05)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd == "upsert":
        data = upsert_experiment(
            ns.root,
            ns.id,
            episode=ns.episode,
            hypothesis=ns.hypothesis,
            variants=parse_variant(ns.variant),
            primary_metric=ns.primary_metric,
            min_samples=ns.min_samples,
            owner=ns.owner,
            alpha=ns.alpha,
        )
        if ns.write:
            path = save_experiments(ns.root, data)
            print(f"wrote {path}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    payload = audit_metrics(ns.root, Path(ns.metrics), alpha=ns.alpha)
    if ns.write:
        write_audit(ns.root, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 1 if payload.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
