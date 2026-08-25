#!/usr/bin/env python3
"""Measure Comic detector value by genre/craft profile and repair yield.

Weak detectors are demoted to advisory recommendations; this report never
deletes a check or silently upgrades a heuristic to a hard gate.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Mapping


def _division(a: float, b: float) -> float | None:
    return round(a / b, 6) if b else None


def classification(row: Mapping[str, Any]) -> tuple[bool, bool] | None:
    label = str(row.get("review_label") or row.get("label") or "").lower()
    mapped = {
        "true_positive": (True, True), "false_positive": (True, False),
        "accepted_intentional": (True, False), "false_negative": (False, True),
        "missed_by_machine": (False, True), "true_negative": (False, False),
    }
    return mapped.get(label)


def summarize(counts: Mapping[str, float], *, min_positive: int = 8, min_negative: int = 8) -> dict[str, Any]:
    tp, fp, fn, tn = (int(counts.get(key) or 0) for key in ("tp", "fp", "fn", "tn"))
    repairs, successful = int(counts.get("repairs") or 0), int(counts.get("successful_repairs") or 0)
    inspection_cost = float(counts.get("inspection_cost") or 0)
    repair_cost = float(counts.get("repair_cost") or 0)
    precision, recall = _division(tp, tp + fp), _division(tp, tp + fn)
    repair_yield = _division(successful, repairs)
    enough = tp + fn >= min_positive and fp + tn >= min_negative
    utility = round(successful * 5 - fp * 2 - inspection_cost - repair_cost, 3)
    eligible = bool(enough and precision is not None and recall is not None and repair_yield is not None and precision >= .9 and recall >= .8 and repair_yield >= .7 and utility > 0)
    if eligible: recommendation = "auto_block_eligible"
    elif enough and utility <= 0: recommendation = "deprioritize_to_advisory"
    elif enough: recommendation = "advisory_only"
    else: recommendation = "insufficient_evidence"
    return {
        "counts": {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "repairs": repairs, "successful_repairs": successful},
        "precision": precision, "recall": recall, "repair_yield": repair_yield,
        "cost_weighted_utility": utility, "recommendation": recommendation,
        "auto_block_eligible": eligible,
    }


def build_report(root: Path) -> dict[str, Any]:
    source = root / "生产数据" / "review_calibration.jsonl"
    groups: dict[tuple[str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    ignored = 0
    try: lines = source.read_text(encoding="utf-8").splitlines()
    except OSError: lines = []
    for line in lines:
        try: row = json.loads(line)
        except ValueError: ignored += 1; continue
        pair = classification(row) if isinstance(row, dict) else None
        if pair is None: ignored += 1; continue
        key = (str(row.get("detector") or row.get("dimension") or "unknown"), str(row.get("genre") or "any"), str(row.get("craft_profile") or "any"))
        predicted, truth = pair
        groups[key]["tp" if predicted and truth else "fp" if predicted else "fn" if truth else "tn"] += 1
        if row.get("repair_attempted"): groups[key]["repairs"] += 1
        if row.get("repair_succeeded"): groups[key]["successful_repairs"] += 1
        groups[key]["inspection_cost"] += float(row.get("inspection_cost") or 0)
        groups[key]["repair_cost"] += float(row.get("repair_cost") or 0)
    rows = [{"detector": key[0], "genre": key[1], "craft_profile": key[2], **summarize(value)} for key, value in sorted(groups.items())]
    return {
        "schema_version": 1, "kind": "comic_detector_value_report",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": str(source.relative_to(root)), "rows": rows, "ignored_rows": ignored,
        "policy": "heuristics remain advisory unless sufficiently labelled data, repair yield and positive cost utility all qualify",
    }


def write_report(root: Path, payload: Mapping[str, Any]) -> Path:
    path = root / "生产数据" / "detector_value_report.json"; path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); os.replace(tmp, path)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("project_root"); parser.add_argument("--write", action="store_true"); parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv); root = Path(args.project_root).expanduser().resolve(); report = build_report(root)
    if args.write: report["output"] = str(write_report(root, report))
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else f"detector groups={len(report['rows'])}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
