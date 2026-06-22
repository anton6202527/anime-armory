#!/usr/bin/env python3
"""Generate consistency threshold recommendations from CAL jsonl rows."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Mapping


def _jsonl(path: str) -> List[dict]:
    rows: List[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except FileNotFoundError:
        pass
    return rows


def _calibration_path(root: str) -> str:
    for rel in ("生产数据/consistency_calibration.jsonl", "设定库/consistency_calibration.jsonl"):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return os.path.join(root, "生产数据", "consistency_calibration.jsonl")


def build_recommendations(root: str) -> dict:
    path = _calibration_path(root)
    rows = _jsonl(path)
    by_dim: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    examples: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        dim = str(row.get("dimension") or row.get("dim") or "(unknown)").strip()
        label = str(row.get("label") or row.get("review_label") or "").strip()
        if not dim or not label:
            continue
        by_dim[dim][label] += 1
        if len(examples[dim]) < 5:
            examples[dim].append({
                "label": label,
                "reason": row.get("reason"),
                "finding_hash": row.get("finding_hash") or row.get("source_hash"),
            })
    recs: List[dict] = []
    for dim, counts in sorted(by_dim.items()):
        fp = counts.get("false_positive", 0)
        missed = counts.get("missed_by_machine", 0)
        accepted = counts.get("accepted_intentional", 0)
        if fp < 2 and missed < 1 and accepted < 2:
            continue
        direction = "review_rule"
        if missed:
            direction = "tighten_threshold_or_add_rule"
        elif fp >= 2:
            direction = "loosen_threshold_or_add_exemption"
        elif accepted >= 2:
            direction = "add_intentional_override_pattern"
        recs.append({
            "dimension": dim,
            "direction": direction,
            "counts": dict(counts),
            "suggested_action": _suggested_action(dim, direction),
            "examples": examples[dim],
        })
    return {
        "kind": "n2d_consistency_threshold_recommendations",
        "version": 1,
        "root": root,
        "source": os.path.relpath(path, root),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "recommendations": recs,
    }


def _suggested_action(dim: str, direction: str) -> str:
    if direction == "tighten_threshold_or_add_rule":
        return f"{dim}: 漏检已出现，降低 warn/block 阈值或新增同类规则；复跑历史校准样本确认召回。"
    if direction == "loosen_threshold_or_add_exemption":
        return f"{dim}: 误报重复出现，提高阈值/加入遮挡、风格化或导演意图豁免；保留人工复核。"
    if direction == "add_intentional_override_pattern":
        return f"{dim}: 已有人审接受的导演意图样本，抽象成结构化 signoff 匹配规则。"
    return f"{dim}: 需要人工复核规则。"


def write_recommendations(root: str) -> str:
    path = os.path.join(root, "生产数据", "consistency_threshold_recommendations.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(build_recommendations(root), fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.write:
        path = write_recommendations(ns.root.rstrip("/"))
        if not ns.json:
            print(path)
            return 0
    payload = build_recommendations(ns.root.rstrip("/"))
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"recommendations: {len(payload.get('recommendations', []))}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(os.sys.argv[1:]))
