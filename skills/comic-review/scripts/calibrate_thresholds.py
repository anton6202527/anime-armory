#!/usr/bin/env python3
"""Calibrate advisory comic consistency thresholds from a human gold set.

Input is intentionally model-agnostic.  A metric declares whether lower or
higher values indicate a match and supplies human labels.  The tool selects a
threshold by balanced accuracy, records the gold-set SHA and never upgrades a
metric to a production BLOCK by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_positive(label: Any) -> bool:
    return str(label or "").strip().lower() in {"same", "match", "pass", "positive", "1", "true"}


def predict(value: float, threshold: float, direction: str) -> bool:
    return value <= threshold if direction == "lower_is_match" else value >= threshold


def score(samples: list[tuple[float, bool]], threshold: float, direction: str) -> dict[str, float | int]:
    tp = tn = fp = fn = 0
    for value, label in samples:
        result = predict(value, threshold, direction)
        if result and label:
            tp += 1
        elif result and not label:
            fp += 1
        elif not result and label:
            fn += 1
        else:
            tn += 1
    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "recall": round(tpr, 6),
        "specificity": round(tnr, 6),
        "precision": round(precision, 6),
        "balanced_accuracy": round((tpr + tnr) / 2, 6),
    }


def calibrate_metric(
    payload: Mapping[str, Any],
    *,
    min_positive: int = 10,
    min_negative: int = 10,
    min_balanced_accuracy: float = 0.8,
) -> dict[str, Any]:
    direction = str(payload.get("direction") or "lower_is_match")
    if direction not in {"lower_is_match", "higher_is_match"}:
        raise ValueError(f"unsupported direction: {direction}")
    samples = [
        (float(item["value"]), is_positive(item.get("label")))
        for item in payload.get("samples") or []
        if isinstance(item, Mapping) and item.get("value") is not None
    ]
    if not samples:
        raise ValueError("metric has no samples")
    values = sorted({value for value, _ in samples})
    candidates = values + [(left + right) / 2 for left, right in zip(values, values[1:])]
    ranked = []
    for threshold in candidates:
        metrics = score(samples, threshold, direction)
        ranked.append((metrics["balanced_accuracy"], metrics["precision"], -abs(threshold), threshold, metrics))
    _, _, _, threshold, metrics = max(ranked)
    positives = sum(label for _, label in samples)
    negatives = len(samples) - positives
    validated = (
        positives >= min_positive
        and negatives >= min_negative
        and float(metrics["balanced_accuracy"]) >= min_balanced_accuracy
    )
    return {
        "status": "validated" if validated else "draft",
        "threshold": round(float(threshold), 6),
        "direction": direction,
        "sample_count": len(samples),
        "positive_count": positives,
        "negative_count": negatives,
        "metrics": metrics,
        "validation_policy": {
            "min_positive": min_positive,
            "min_negative": min_negative,
            "min_balanced_accuracy": min_balanced_accuracy,
        },
        "enforcement": "warn_only",
    }


def build_registry(
    gold_path: Path,
    *,
    min_positive: int = 10,
    min_negative: int = 10,
    min_balanced_accuracy: float = 0.8,
) -> dict[str, Any]:
    gold = load_json(gold_path, {})
    metrics = gold.get("metrics") if isinstance(gold, Mapping) else None
    if not isinstance(metrics, Mapping) or not metrics:
        raise ValueError("gold set requires metrics object")
    calibrated: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, payload in metrics.items():
        if not isinstance(payload, Mapping):
            errors[str(name)] = "metric payload is not an object"
            continue
        try:
            calibrated[str(name)] = calibrate_metric(
                payload,
                min_positive=min_positive,
                min_negative=min_negative,
                min_balanced_accuracy=min_balanced_accuracy,
            )
        except (TypeError, ValueError) as exc:
            errors[str(name)] = str(exc)
    return {
        "schema_version": 1,
        "kind": "comic_consistency_threshold_registry",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "gold_set_path": str(gold_path),
        "gold_set_sha256": sha256_file(gold_path),
        "metrics": calibrated,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从人审金标集校准漫画一致性告警阈值")
    parser.add_argument("project_root")
    parser.add_argument("--gold-set", default="生产数据/consistency_gold_set.json")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min-positive", type=int, default=10)
    parser.add_argument("--min-negative", type=int, default=10)
    parser.add_argument("--min-balanced-accuracy", type=float, default=0.8)
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    gold_path = Path(args.gold_set)
    if not gold_path.is_absolute():
        gold_path = root / gold_path
    try:
        report = build_registry(
            gold_path,
            min_positive=args.min_positive,
            min_negative=args.min_negative,
            min_balanced_accuracy=args.min_balanced_accuracy,
        )
    except (OSError, ValueError) as exc:
        print(f"[err] {exc}")
        return 2
    if args.write:
        out = root / "生产数据" / "consistency_threshold_registry.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for name, row in report["metrics"].items():
            print(f"{name}: {row['status']} threshold={row['threshold']} balanced_accuracy={row['metrics']['balanced_accuracy']}")
    return 0 if report["metrics"] and not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
