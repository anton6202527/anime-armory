#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Calibrate novel detectors by precision, recall and accepted repair yield.

Input is labelled production evidence, grouped by detector/dimension/craft
profile/genre.  Weak detectors are only recommended for advisory demotion;
this tool never deletes checks or silently promotes uncalibrated heuristics to
release blockers.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


KIND = "novel_detector_value_report"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def source_path(root: str | Path) -> Path:
    root_path = Path(root)
    for rel in ("生产数据/review_calibration.jsonl", "审稿/review_calibration.jsonl"):
        path = root_path / rel
        if path.is_file():
            return path
    return root_path / "生产数据" / "review_calibration.jsonl"


def _rows(path: Path) -> list[dict[str, Any]]:
    out = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _bool(value: Any) -> bool | None:
    text = str(value or "").strip().lower()
    if text in {"1", "true", "defect", "positive", "block", "fail", "bad"}:
        return True
    if text in {"0", "false", "clean", "negative", "pass", "ok", "good"}:
        return False
    return None


def classification(row: Mapping[str, Any]) -> tuple[bool, bool] | None:
    label = str(row.get("review_label") or row.get("label") or "").strip().lower()
    mapped = {
        "true_positive": (True, True), "false_positive": (True, False),
        "accepted_intentional": (True, False), "false_negative": (False, True),
        "missed_by_machine": (False, True), "true_negative": (False, False),
    }
    if label in mapped:
        return mapped[label]
    predicted = _bool(row.get("prediction") or row.get("machine_positive") or row.get("machine_verdict"))
    truth = _bool(row.get("ground_truth") or row.get("human_positive") or row.get("truth"))
    return (predicted, truth) if predicted is not None and truth is not None else None


def _division(a: int, b: int) -> float | None:
    return round(a / b, 6) if b else None


def summarize(counts: Mapping[str, int], *, min_positive: int = 8, min_negative: int = 8,
              min_repairs: int = 5, min_precision: float = 0.9,
              min_recall: float = 0.8, min_repair_yield: float = 0.6) -> dict[str, Any]:
    tp, fp, fn, tn = (int(counts.get(key) or 0) for key in ("tp", "fp", "fn", "tn"))
    repairs = int(counts.get("repair_attempts") or 0)
    accepted = int(counts.get("repair_accepted") or 0)
    total = tp + fp + fn + tn
    precision, recall = _division(tp, tp + fp), _division(tp, tp + fn)
    repair_yield = _division(accepted, repairs)
    utility = round(tp * 5 + accepted * 2 - fp * 2 - fn * 4 - total * 0.25 - max(0, repairs - accepted), 3)
    enough = tp + fn >= min_positive and fp + tn >= min_negative and repairs >= min_repairs
    eligible = bool(
        enough and precision is not None and recall is not None and repair_yield is not None
        and precision >= min_precision and recall >= min_recall
        and repair_yield >= min_repair_yield and utility > 0
    )
    if eligible:
        recommendation = "auto_block_eligible"
    elif total >= min_positive + min_negative and (tp == 0 or (precision is not None and precision < 0.5)) and utility <= 0:
        recommendation = "retire_candidate_advisory_only"
    elif enough:
        recommendation = "advisory_only"
    else:
        recommendation = "insufficient_evidence"
    return {
        "counts": {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "total": total,
                   "positive_n": tp + fn, "negative_n": fp + tn,
                   "repair_attempts": repairs, "repair_accepted": accepted},
        "precision": precision, "recall": recall,
        "false_positive_rate": _division(fp, fp + tn),
        "false_negative_rate": _division(fn, tp + fn),
        "repair_yield": repair_yield,
        "cost_weighted_utility": utility,
        "recommendation": recommendation,
        "auto_block_eligible": eligible,
        "targets": {"min_positive": min_positive, "min_negative": min_negative, "min_repairs": min_repairs,
                    "min_precision": min_precision, "min_recall": min_recall, "min_repair_yield": min_repair_yield},
    }


def build_report(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    source = source_path(root_path)
    grouped: dict[tuple[str, str, str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
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
            str(row.get("craft_profile") or "any"),
            str(row.get("genre") or "any"),
        )
        grouped[key]["tp" if predicted and truth else "fp" if predicted else "fn" if truth else "tn"] += 1
        repair_status = str(row.get("repair_status") or "").strip().lower()
        attempted = bool(row.get("repair_attempted")) or repair_status in {"fixed", "failed", "rejected", "accepted"}
        if attempted:
            grouped[key]["repair_attempts"] += 1
            if row.get("repair_accepted") is True or repair_status in {"fixed", "accepted"}:
                grouped[key]["repair_accepted"] += 1
    rows = []
    for key, counts in sorted(grouped.items()):
        detector, dimension, craft_profile, genre = key
        rows.append({"detector": detector, "dimension": dimension, "craft_profile": craft_profile, "genre": genre, **summarize(counts)})
    return {
        "schema_version": 1, "kind": KIND, "generated_at": now_iso(), "project_root": str(root_path),
        "source": os.path.relpath(source, root_path).replace(os.sep, "/"), "rows": rows,
        "ignored_unlabelled_rows": ignored,
        "summary": {
            "groups": len(rows),
            "auto_block_eligible": sum(row["recommendation"] == "auto_block_eligible" for row in rows),
            "advisory_only": sum(row["recommendation"] == "advisory_only" for row in rows),
            "retire_candidates": sum(row["recommendation"].startswith("retire_candidate") for row in rows),
            "insufficient_evidence": sum(row["recommendation"] == "insufficient_evidence" for row in rows),
        },
        "policy": "recommendations do not mutate detector enforcement; maintainers must review scope and call sites",
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Novel Detector Value Report", "",
        "| detector | dimension | craft/genre | n | precision | recall | repair yield | utility | recommendation |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"| {row.get('detector')} | {row.get('dimension')} | {row.get('craft_profile')}/{row.get('genre')} "
            f"| {(row.get('counts') or {}).get('total', 0)} | {row.get('precision')} | {row.get('recall')} "
            f"| {row.get('repair_yield')} | {row.get('cost_weighted_utility')} | {row.get('recommendation')} |"
        )
    lines.extend(["", "> retire candidate 只建议降为 advisory；本工具不自动删除或改阻断级别。", ""])
    return "\n".join(lines)


def write_report(root: str | Path, payload: Mapping[str, Any]) -> dict[str, str]:
    out = Path(root) / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "novel_detector_value_report.json"
    md_path = out / "novel_detector_value_report.md"
    tmp = json_path.with_name(f".{json_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    payload = build_report(ns.project_root)
    if ns.write:
        payload["outputs"] = write_report(ns.project_root, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
