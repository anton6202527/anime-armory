#!/usr/bin/env python3
"""Measure and A/B-audit n2d image prompt compiler cohorts.

The report joins real image generation events, immutable compiler metadata and
the latest image QC rows.  It never changes a prompt profile automatically:
promotion requires an explicitly registered experiment, per-variant sample
floors and no face/hand safety regression.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


KIND = "n2d_image_prompt_metrics"
VERSION = 1
REGISTRY_KIND = "n2d_image_prompt_experiments"
REPORT_JSON = Path("生产数据") / "image_prompt_metrics.json"
REPORT_MD = Path("生产数据") / "image_prompt_metrics.md"
REGISTRY_JSON = Path("生产数据") / "image_prompt_experiments.json"
EVENTS_JSONL = Path("生产数据") / "production_events.jsonl"
FAIL_VERDICTS = {"block", "fail", "failed", "reject", "rejected"}
EVALUATED_VERDICTS = FAIL_VERDICTS | {"ok", "pass", "passed", "warn", "warning"}


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _rate(numerator: int, denominator: int) -> Optional[float]:
    return round(numerator / denominator, 6) if denominator else None


def _asset_key(episode: str, value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    return f"{episode}/{Path(text).name}" if text else ""


def _event_meta(event: Mapping[str, Any]) -> Mapping[str, Any]:
    return event.get("meta") if isinstance(event.get("meta"), Mapping) else {}


def _event_generation(event: Mapping[str, Any]) -> Mapping[str, Any]:
    return event.get("generation") if isinstance(event.get("generation"), Mapping) else {}


def load_receipt_index(root: Path) -> Dict[str, Dict[str, Any]]:
    """Index latest compiler receipt by episode + target basename."""
    base = root / "生产数据" / "compiled_image_requests"
    indexed: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    if not base.is_dir():
        return {}
    for path in base.rglob("*.json"):
        data = _read_json(path, {})
        if not isinstance(data, dict):
            continue
        episode = str(data.get("episode") or path.parent.name)
        key = _asset_key(episode, data.get("target"))
        compiler = data.get("compiler") if isinstance(data.get("compiler"), dict) else {}
        if not key or not compiler:
            continue
        stamp = path.stat().st_mtime
        if key not in indexed or stamp >= indexed[key][0]:
            indexed[key] = (stamp, compiler)
    return {key: row[1] for key, row in indexed.items()}


def _compiler_fields(event: Mapping[str, Any], receipt: Mapping[str, Any]) -> Dict[str, str]:
    meta = _event_meta(event)

    def pick(meta_key: str, receipt_key: str = "") -> str:
        return str(meta.get(meta_key) or receipt.get(receipt_key or meta_key) or "").strip()

    experiment = receipt.get("experiment") if isinstance(receipt.get("experiment"), Mapping) else {}
    return {
        "compiler_version": pick("prompt_compiler_version", "version") or "unknown",
        "profile_version": pick("prompt_profile_version", "profile_version") or "unknown",
        "profile": pick("prompt_profile", "profile") or "unknown",
        "backend": pick("backend", "backend") or str(event.get("provider") or "unknown"),
        "model": pick("model", "model") or "unknown",
        "task_type": pick("prompt_task_type", "task_type") or "unknown",
        "experiment_id": pick("image_prompt_experiment_id") or str(experiment.get("experiment_id") or ""),
        "variant": pick("image_prompt_variant") or str(experiment.get("variant") or ""),
    }


def collect_attempts(root: Path) -> List[Dict[str, Any]]:
    seen_assets: Dict[str, int] = defaultdict(int)
    attempts: List[Dict[str, Any]] = []
    for order, event in enumerate(_read_jsonl(root / EVENTS_JSONL)):
        if str(event.get("stage") or "") != "image" or str(event.get("event") or "") not in {"generation", "redraw"}:
            continue
        generation = _event_generation(event)
        episode = str(event.get("episode") or "")
        asset = str(generation.get("asset") or event.get("asset") or "")
        key = _asset_key(episode, asset)
        if not key:
            continue
        meta = _event_meta(event)
        receipt_ref = str(meta.get("compiled_request_receipt") or "").strip()
        receipt_path = Path(receipt_ref) if receipt_ref else None
        if receipt_path is not None and not receipt_path.is_absolute():
            receipt_path = root / receipt_path
        receipt = _read_json(receipt_path, {}) if receipt_path is not None else {}
        compiler = receipt.get("compiler") if isinstance(receipt, Mapping) and isinstance(receipt.get("compiler"), Mapping) else {}
        fields = _compiler_fields(event, compiler)
        metrics = compiler.get("metrics") if isinstance(compiler.get("metrics"), Mapping) else {}
        cost = event.get("cost") if isinstance(event.get("cost"), Mapping) else {}
        seen_assets[key] += 1
        attempts.append({
            "order": order,
            "episode": episode,
            "asset": asset,
            "asset_key": key,
            "status": str(generation.get("status") or "").lower(),
            "event": str(event.get("event") or ""),
            "is_first_draw": seen_assets[key] == 1,
            "is_redraw": str(event.get("event") or "") == "redraw" or bool(generation.get("redraw_reason")),
            "input_tokens": _number(meta.get("compiled_estimated_text_tokens") or metrics.get("estimated_text_tokens")),
            "prompt_chars": _number(meta.get("compiled_prompt_chars") or metrics.get("prompt_chars")),
            "cost_amount": _number(cost.get("amount")),
            "cost_unit": str(cost.get("unit") or cost.get("currency") or "").strip(),
            **fields,
        })
    return attempts


def collect_latest_qc(root: Path) -> Dict[str, Dict[str, str]]:
    """Return latest evaluated face/anatomy verdict per rendered asset."""
    reports = sorted(
        (root / "生产数据").glob("**/image_qc*.json"),
        key=lambda path: (path.stat().st_mtime, str(path)),
    ) if (root / "生产数据").is_dir() else []
    out: Dict[str, Dict[str, str]] = {}
    for path in reports:
        data = _read_json(path, {})
        if not isinstance(data, Mapping):
            continue
        episode = str(data.get("episode") or "")
        if not episode:
            for part in path.parts:
                if part.startswith("第") and part.endswith("集"):
                    episode = part
                    break
        checks = data.get("checks") if isinstance(data.get("checks"), Mapping) else {}
        for check_name, row_key, metric_name in (
            ("face", "shots", "identity"),
            ("human_anatomy", "shots", "hand"),
        ):
            check = checks.get(check_name) if isinstance(checks.get(check_name), Mapping) else {}
            for row in check.get(row_key) or []:
                if not isinstance(row, Mapping):
                    continue
                verdict = str(row.get("verdict") or "").lower()
                if verdict not in EVALUATED_VERDICTS:
                    continue
                key = _asset_key(episode, row.get("png") or row.get("image") or row.get("path"))
                if key:
                    out.setdefault(key, {})[metric_name] = verdict
    return out


def _cohort_key(row: Mapping[str, Any]) -> Tuple[str, ...]:
    return tuple(str(row.get(key) or "") for key in (
        "compiler_version", "profile_version", "profile", "backend", "model",
        "experiment_id", "variant",
    ))


def summarize_cohorts(attempts: Sequence[Mapping[str, Any]], qc: Mapping[str, Mapping[str, str]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, ...], List[Mapping[str, Any]]] = defaultdict(list)
    for row in attempts:
        groups[_cohort_key(row)].append(row)
    latest_by_asset = {row["asset_key"]: row for row in attempts}
    first_by_asset = {row["asset_key"]: row for row in reversed(attempts)}
    cohorts: List[Dict[str, Any]] = []
    keys = ("compiler_version", "profile_version", "profile", "backend", "model", "experiment_id", "variant")
    for group_key, rows in sorted(groups.items()):
        first_rows = [row for row in rows if row.get("is_first_draw")]
        assets = {str(row.get("asset_key")) for row in rows}
        first_pass = sum(str(row.get("status")) == "pass" for row in first_rows)
        pass_attempts = sum(str(row.get("status")) == "pass" for row in rows)
        redraws = sum(bool(row.get("is_redraw")) for row in rows)
        identity_checks = identity_failures = hand_checks = hand_failures = 0
        for asset in assets:
            latest = latest_by_asset.get(asset)
            first = first_by_asset.get(asset)
            # QC is attributed to the compiler cohort that produced the latest
            # landed frame; first-draw efficiency stays attributed to attempt 1.
            if not latest or _cohort_key(latest) != group_key:
                continue
            verdicts = qc.get(asset) or {}
            if verdicts.get("identity") in EVALUATED_VERDICTS:
                identity_checks += 1
                identity_failures += verdicts.get("identity") in FAIL_VERDICTS
            if verdicts.get("hand") in EVALUATED_VERDICTS:
                hand_checks += 1
                hand_failures += verdicts.get("hand") in FAIL_VERDICTS
        costs: Dict[str, float] = defaultdict(float)
        for row in rows:
            if row.get("cost_unit"):
                costs[str(row.get("cost_unit"))] += float(row.get("cost_amount") or 0)
        input_tokens = sum(float(row.get("input_tokens") or 0) for row in rows)
        prompt_chars = sum(float(row.get("prompt_chars") or 0) for row in rows)
        cohort = dict(zip(keys, group_key))
        cohort.update({
            "assets": len(assets),
            "generation_attempts": len(rows),
            "attempt_pass_rate": _rate(pass_attempts, len(rows)),
            "first_draw_assets": len(first_rows),
            "first_draw_passes": first_pass,
            "first_draw_pass_rate": _rate(first_pass, len(first_rows)),
            "redraw_count": redraws,
            "redraw_rate": _rate(redraws, len(rows)),
            "identity_checks": identity_checks,
            "identity_drift_failures": identity_failures,
            "identity_drift_rate": _rate(identity_failures, identity_checks),
            "hand_checks": hand_checks,
            "hand_failures": hand_failures,
            "hand_failure_rate": _rate(hand_failures, hand_checks),
            "cost_totals": {key: round(value, 6) for key, value in sorted(costs.items())},
            "input_tokens": int(round(input_tokens)),
            "avg_input_tokens_per_attempt": round(input_tokens / len(rows), 3) if rows else None,
            "avg_prompt_chars_per_attempt": round(prompt_chars / len(rows), 3) if rows else None,
        })
        cohorts.append(cohort)
    return cohorts


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> List[float]:
    if total <= 0:
        return [0.0, 1.0]
    p = successes / total
    den = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / den
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [round(max(0.0, centre - margin), 6), round(min(1.0, centre + margin), 6)]


def two_proportion_pvalue(x_a: int, n_a: int, x_b: int, n_b: int) -> Optional[float]:
    if n_a <= 0 or n_b <= 0:
        return None
    p_a, p_b = x_a / n_a, x_b / n_b
    pooled = (x_a + x_b) / (n_a + n_b)
    variance = pooled * (1 - pooled) * (1 / n_a + 1 / n_b)
    if variance <= 0:
        return 1.0 if abs(p_a - p_b) < 1e-12 else 0.0
    return math.erfc(abs((p_b - p_a) / math.sqrt(variance)) / math.sqrt(2.0))


def load_experiment_registry(root: Path) -> Dict[str, Any]:
    data = _read_json(root / REGISTRY_JSON, {})
    if not isinstance(data, dict) or data.get("kind") != REGISTRY_KIND:
        return {"kind": REGISTRY_KIND, "version": 1, "experiments": []}
    data.setdefault("experiments", [])
    return data


def register_experiment(
    root: Path,
    experiment_id: str,
    *,
    variants: Sequence[str],
    control: str,
    min_samples: int,
    hypothesis: str,
) -> Path:
    clean = list(dict.fromkeys(str(item).strip() for item in variants if str(item).strip()))
    if len(clean) < 2 or control not in clean:
        raise ValueError("experiment requires at least two variants and control must be one of them")
    data = load_experiment_registry(root)
    row = {
        "experiment_id": experiment_id,
        "hypothesis": hypothesis,
        "variants": clean,
        "control_variant": control,
        "min_samples_per_variant": int(min_samples),
        "primary_metric": "first_draw_pass_rate",
        "safety_metrics": ["identity_drift_rate", "hand_failure_rate"],
        "status": "running",
    }
    data["experiments"] = sorted(
        [item for item in data.get("experiments") or [] if item.get("experiment_id") != experiment_id] + [row],
        key=lambda item: str(item.get("experiment_id")),
    )
    path = root / REGISTRY_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def analyze_experiments(cohorts: Sequence[Mapping[str, Any]], registry: Mapping[str, Any]) -> List[Dict[str, Any]]:
    analyses: List[Dict[str, Any]] = []
    for experiment in registry.get("experiments") or []:
        if not isinstance(experiment, Mapping):
            continue
        exp_id = str(experiment.get("experiment_id") or "")
        variants = [str(item) for item in experiment.get("variants") or []]
        control = str(experiment.get("control_variant") or (variants[0] if variants else ""))
        minimum = int(experiment.get("min_samples_per_variant") or 0)
        summaries = {
            variant: next((dict(row) for row in cohorts if row.get("experiment_id") == exp_id and row.get("variant") == variant), None)
            for variant in variants
        }
        underpowered = [
            variant for variant, row in summaries.items()
            if not row or int(row.get("first_draw_assets") or 0) < minimum
        ]
        comparisons: List[Dict[str, Any]] = []
        control_row = summaries.get(control) or {}
        correction = max(1, len(variants) - 1)
        for variant in variants:
            if variant == control:
                continue
            row = summaries.get(variant) or {}
            pvalue = two_proportion_pvalue(
                int(control_row.get("first_draw_passes") or 0),
                int(control_row.get("first_draw_assets") or 0),
                int(row.get("first_draw_passes") or 0),
                int(row.get("first_draw_assets") or 0),
            )
            adjusted = min(1.0, pvalue * correction) if pvalue is not None else None
            control_rate = control_row.get("first_draw_pass_rate")
            candidate_rate = row.get("first_draw_pass_rate")
            lift = (
                float(candidate_rate) - float(control_rate)
                if candidate_rate is not None and control_rate is not None else None
            )
            safety_regressions = []
            for metric in ("identity_drift_rate", "hand_failure_rate"):
                base_rate, candidate_safety = control_row.get(metric), row.get(metric)
                if base_rate is not None and candidate_safety is not None and float(candidate_safety) > float(base_rate) + 0.02:
                    safety_regressions.append(metric)
            comparisons.append({
                "control": control,
                "candidate": variant,
                "absolute_first_draw_lift": round(lift, 6) if lift is not None else None,
                "p_value": round(pvalue, 8) if pvalue is not None else None,
                "adjusted_p_value": round(adjusted, 8) if adjusted is not None else None,
                "significant": adjusted is not None and adjusted < 0.05,
                "safety_regressions": safety_regressions,
            })
        promotable = [
            row for row in comparisons
            if row.get("significant") and float(row.get("absolute_first_draw_lift") or 0) > 0 and not row.get("safety_regressions")
        ]
        if underpowered:
            decision, winner = "insufficient_samples", ""
        elif promotable:
            best = max(promotable, key=lambda row: float(row.get("absolute_first_draw_lift") or 0))
            decision, winner = "promote_candidate", str(best.get("candidate") or "")
        elif any(row.get("safety_regressions") for row in comparisons):
            decision, winner = "keep_control_safety_regression", control
        else:
            decision, winner = "no_significant_difference", ""
        for variant, row in summaries.items():
            if row:
                row["first_draw_ci95"] = wilson_interval(
                    int(row.get("first_draw_passes") or 0),
                    int(row.get("first_draw_assets") or 0),
                )
        analyses.append({
            "experiment_id": exp_id,
            "hypothesis": experiment.get("hypothesis") or "",
            "control_variant": control,
            "min_samples_per_variant": minimum,
            "variant_metrics": summaries,
            "underpowered_variants": underpowered,
            "comparisons": comparisons,
            "decision": decision,
            "winner": winner,
            "promotion_policy": "fixed horizon; Bonferroni vs control; no face/hand safety regression",
        })
    return analyses


def build_report(root: Path) -> Dict[str, Any]:
    attempts = collect_attempts(root)
    qc = collect_latest_qc(root)
    cohorts = summarize_cohorts(attempts, qc)
    registry = load_experiment_registry(root)
    analyses = analyze_experiments(cohorts, registry)
    tagged = sum(bool(row.get("experiment_id") and row.get("variant")) for row in attempts)
    qc_assets = {row.get("asset_key") for row in attempts if row.get("asset_key") in qc}
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "inputs": {
            "events": str(root / EVENTS_JSONL),
            "experiment_registry": str(root / REGISTRY_JSON),
        },
        "summary": {
            "generation_attempts": len(attempts),
            "assets": len({row.get("asset_key") for row in attempts}),
            "cohorts": len(cohorts),
            "tagged_experiment_attempts": tagged,
            "untagged_attempts": len(attempts) - tagged,
            "qc_joined_assets": len(qc_assets),
            "qc_join_coverage": _rate(len(qc_assets), len({row.get("asset_key") for row in attempts})),
        },
        "cohorts": cohorts,
        "experiments": analyses,
        "interpretation": {
            "first_draw_pass": "first generation/redraw event observed for an asset has status=pass",
            "identity_drift_failure": "latest evaluated face QC verdict is block/fail/rejected",
            "hand_failure": "latest evaluated human_anatomy QC verdict is block/fail/rejected",
            "causality": "only explicitly tagged fixed-horizon experiments may promote a profile; untagged version cohorts are observational",
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    lines = [
        "# Image Prompt Compiler 实测报告",
        "",
        f"- 生成尝试：{summary.get('generation_attempts', 0)}",
        f"- 资产：{summary.get('assets', 0)}",
        f"- QC join 覆盖：{summary.get('qc_join_coverage')}",
        f"- A/B 已标记尝试：{summary.get('tagged_experiment_attempts', 0)}；未标记：{summary.get('untagged_attempts', 0)}",
        "",
        "## Compiler / Profile cohorts",
        "",
        "| compiler | profile version | profile | backend/model | variant | 首抽通过 | 身份漂移 | 手部失败 | 重抽 | 成本 | input tokens |",
        "|---|---|---|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for row in report.get("cohorts") or []:
        costs = " / ".join(f"{key} {value:g}" for key, value in (row.get("cost_totals") or {}).items()) or "—"
        variant = "/".join(filter(None, (str(row.get("experiment_id") or ""), str(row.get("variant") or "")))) or "—"
        lines.append(
            f"| {row.get('compiler_version')} | {row.get('profile_version')} | {row.get('profile')} | "
            f"{row.get('backend')}/{row.get('model')} | {variant} | {row.get('first_draw_pass_rate')} | "
            f"{row.get('identity_drift_rate')} | {row.get('hand_failure_rate')} | {row.get('redraw_rate')} | "
            f"{costs} | {row.get('input_tokens')} |"
        )
    lines += ["", "## A/B decisions", ""]
    if not report.get("experiments"):
        lines.append("- 尚无已注册的 image prompt A/B；版本 cohort 只能做观察，不能作因果结论。")
    for row in report.get("experiments") or []:
        lines.append(
            f"- `{row.get('experiment_id')}`：{row.get('decision')}"
            f"{('，winner=' + str(row.get('winner'))) if row.get('winner') else ''}；"
            f"每变体最少 {row.get('min_samples_per_variant')} 个首抽资产。"
        )
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> Tuple[Path, Path]:
    json_path, md_path = root / REPORT_JSON, root / REPORT_MD
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_tmp = json_path.with_name(f"{json_path.name}.tmp.{os.getpid()}")
    md_tmp = md_path.with_name(f"{md_path.name}.tmp.{os.getpid()}")
    json_tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_tmp.write_text(render_markdown(report), encoding="utf-8")
    os.replace(json_tmp, json_path)
    os.replace(md_tmp, md_path)
    return json_path, md_path


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Measure image prompt compiler/profile outcomes from real n2d events and QC")
    sub = ap.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report")
    report.add_argument("root")
    report.add_argument("--write", action="store_true")
    report.add_argument("--json", action="store_true")
    register = sub.add_parser("register")
    register.add_argument("root")
    register.add_argument("experiment_id")
    register.add_argument("--variant", action="append", required=True)
    register.add_argument("--control", required=True)
    register.add_argument("--min-samples", type=int, default=30)
    register.add_argument("--hypothesis", required=True)
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    if ns.command == "register":
        try:
            path = register_experiment(
                root,
                ns.experiment_id,
                variants=ns.variant,
                control=ns.control,
                min_samples=ns.min_samples,
                hypothesis=ns.hypothesis,
            )
        except ValueError as exc:
            print(f"[error] {exc}")
            return 2
        print(path)
        return 0
    report = build_report(root)
    if ns.write:
        paths = write_report(root, report)
        if not ns.json:
            print("\n".join(str(path) for path in paths))
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif not ns.write:
        print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(os.sys.argv[1:]))
