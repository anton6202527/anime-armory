#!/usr/bin/env python3
"""Measure whether each n2d detector improves deliverable production yield.

Consumes labelled production review rows and emits per
``detector/dimension/backend/style/shot_class`` confusion metrics plus a
cost-weighted enforcement recommendation.  It never deletes a detector; weak
or uncalibrated detectors are demoted to advisory until evidence improves.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


KIND = "n2d_detector_value_report"
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _rows(path: Path) -> list[Dict[str, Any]]:
    out: list[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                out.append(row)
    except OSError:
        pass
    return out


def source_path(root: str | Path) -> Path:
    root_path = Path(root)
    for rel in ("生产数据/consistency_calibration.jsonl", "设定库/consistency_calibration.jsonl"):
        path = root_path / rel
        if path.is_file():
            return path
    return root_path / "生产数据" / "consistency_calibration.jsonl"


def _bool_label(value: Any) -> Optional[bool]:
    text = str(value or "").strip().lower()
    if text in {"1", "true", "positive", "defect", "fail", "block", "drift", "bad"}:
        return True
    if text in {"0", "false", "negative", "clean", "pass", "ok", "good"}:
        return False
    return None


def classification(row: Mapping[str, Any]) -> Optional[Tuple[bool, bool]]:
    review = str(row.get("review_label") or row.get("label") or "").strip().lower()
    mapped = {
        "true_positive": (True, True),
        "false_positive": (True, False),
        "accepted_intentional": (True, False),
        "missed_by_machine": (False, True),
        "false_negative": (False, True),
        "true_negative": (False, False),
    }
    if review in mapped:
        return mapped[review]
    predicted = _bool_label(
        row.get("prediction") or row.get("machine_positive") or row.get("machine_verdict")
    )
    truth = _bool_label(
        row.get("ground_truth") or row.get("human_positive") or row.get("truth")
    )
    return (predicted, truth) if predicted is not None and truth is not None else None


def _division(a: int, b: int) -> Optional[float]:
    return round(a / b, 6) if b else None


def summarize_counts(
    counts: Mapping[str, int],
    *,
    min_positive: int = 10,
    min_negative: int = 10,
    min_precision: float = 0.90,
    min_recall: float = 0.80,
    inspection_cost: float = 1.0,
    avoided_defect_cost: float = 5.0,
    false_positive_cost: float = 2.0,
) -> Dict[str, Any]:
    tp, fp, fn, tn = (int(counts.get(key) or 0) for key in ("tp", "fp", "fn", "tn"))
    positive_n, negative_n, total = tp + fn, fp + tn, tp + fp + fn + tn
    precision = _division(tp, tp + fp)
    recall = _division(tp, tp + fn)
    fpr = _division(fp, negative_n)
    fnr = _division(fn, positive_n)
    utility = round(tp * avoided_defect_cost - fp * false_positive_cost - total * inspection_cost, 3)
    enough = positive_n >= min_positive and negative_n >= min_negative
    eligible = (
        enough and precision is not None and recall is not None
        and precision >= min_precision and recall >= min_recall and utility > 0
    )
    if eligible:
        recommendation = "auto_block_eligible"
    elif total >= min_positive + min_negative and (tp == 0 or (precision is not None and precision < 0.5)) and utility <= 0:
        recommendation = "retire_candidate"
    elif enough:
        recommendation = "advisory_only"
    else:
        recommendation = "insufficient_evidence"
    return {
        "counts": {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "positive_n": positive_n, "negative_n": negative_n, "total": total},
        "precision": precision,
        "recall": recall,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "cost_weighted_utility": utility,
        "recommendation": recommendation,
        "auto_block_eligible": eligible,
        "targets": {
            "min_positive": min_positive, "min_negative": min_negative,
            "min_precision": min_precision, "min_recall": min_recall,
        },
    }


def build_report(root: str | Path) -> Dict[str, Any]:
    root_path = Path(root)
    source = source_path(root_path)
    grouped: Dict[tuple[str, str, str, str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    ignored = 0
    for row in _rows(source):
        pair = classification(row)
        if pair is None:
            ignored += 1
            continue
        predicted, truth = pair
        key = (
            str(row.get("detector") or row.get("dimension") or row.get("dim") or "unknown"),
            str(row.get("dimension") or row.get("dim") or "unknown"),
            str(row.get("backend") or "any"),
            str(row.get("style") or "any"),
            str(row.get("shot_class") or row.get("shot_type") or "any"),
        )
        outcome = "tp" if predicted and truth else "fp" if predicted else "fn" if truth else "tn"
        grouped[key][outcome] += 1
    rows = []
    for key, counts in sorted(grouped.items()):
        detector, dimension, backend, style, shot_class = key
        rows.append({
            "detector": detector,
            "dimension": dimension,
            "backend": backend,
            "style": style,
            "shot_class": shot_class,
            **summarize_counts(counts),
        })
    return {
        "kind": KIND,
        "version": VERSION,
        "root": str(root_path),
        "source": str(source.relative_to(root_path)) if source.is_absolute() else str(source),
        "generated_at": now_iso(),
        "rows": rows,
        "ignored_unlabelled_rows": ignored,
        "summary": {
            "groups": len(rows),
            "auto_block_eligible": sum(1 for row in rows if row["recommendation"] == "auto_block_eligible"),
            "advisory_only": sum(1 for row in rows if row["recommendation"] == "advisory_only"),
            "retire_candidates": sum(1 for row in rows if row["recommendation"] == "retire_candidate"),
            "insufficient_evidence": sum(1 for row in rows if row["recommendation"] == "insufficient_evidence"),
        },
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Detector Value Report", "",
        "| detector | dimension | backend/style/shot | n | precision | recall | utility | recommendation |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in payload.get("rows") or []:
        counts = row.get("counts") or {}
        lines.append(
            f"| {row.get('detector')} | {row.get('dimension')} | {row.get('backend')}/{row.get('style')}/{row.get('shot_class')} "
            f"| {counts.get('total', 0)} | {row.get('precision')} | {row.get('recall')} "
            f"| {row.get('cost_weighted_utility')} | {row.get('recommendation')} |"
        )
    lines.extend(["", "> 退役候选只会降级为 advisory；删除仍需维护者审阅调用关系。", ""])
    return "\n".join(lines)


def write_report(root: str | Path, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, str]:
    root_path = Path(root)
    data = dict(payload or build_report(root_path))
    path = root_path / "生产数据" / "detector_value_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    md = path.with_suffix(".md")
    md.write_text(render_markdown(data), encoding="utf-8")
    return {"json": str(path), "markdown": str(md)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    payload = build_report(ns.root)
    if ns.write:
        payload["outputs"] = write_report(ns.root, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
