#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a compliant reference score distribution from scored works."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date


ALLOWED_RIGHTS = {
    "public-domain",
    "user-owned",
    "user-declared",
    "original",
    "authorized",
    "licensed",
}


def parse_sample(value):
    parts = [p.strip() for p in value.split("|")]
    if len(parts) not in (2, 3, 4):
        raise argparse.ArgumentTypeError(
            "--sample 格式：score_report.json|rights_status[|source_label|title]"
        )
    path, rights = parts[:2]
    source_label = parts[2] if len(parts) >= 3 else ""
    title = parts[3] if len(parts) == 4 else ""
    if rights not in ALLOWED_RIGHTS:
        raise argparse.ArgumentTypeError(
            f"rights_status={rights!r} 不可纳入参考分布；允许：{', '.join(sorted(ALLOWED_RIGHTS))}"
        )
    return {"path": path, "rights_status": rights, "source_label": source_label, "title": title}


def load_report(path):
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or payload.get("kind") != "novel_score_report":
        raise ValueError(f"{path} 不是 novel_score_report")
    if not isinstance(payload.get("total_score"), (int, float)):
        raise ValueError(f"{path} 缺 total_score")
    return payload


def sample_from_report(spec):
    path = os.path.abspath(spec["path"])
    report = load_report(path)
    scores = {}
    for item in report.get("scores") or []:
        if isinstance(item, dict) and item.get("dimension") and isinstance(item.get("raw_score"), (int, float)):
            scores[item["dimension"]] = item["raw_score"]
    title = spec.get("title") or os.path.basename(os.path.dirname(os.path.dirname(path))) or report.get("project_root")
    return {
        "title": title,
        "source_label": spec.get("source_label") or os.path.relpath(path, os.getcwd()),
        "rights_status": spec["rights_status"],
        "total_score": report["total_score"],
        "verdict": report.get("verdict"),
        "tier": report.get("tier"),
        "scores": scores,
        "score_report_path": path,
    }


def build_distribution(samples, *, title):
    return {
        "schema_version": 1,
        "kind": "novel_reference_score_distribution",
        "title": title,
        "generated_at": date.today().isoformat(),
        "rights_policy": "Only public-domain, user-owned, user-declared, original, authorized, or licensed samples.",
        "sample_count": len(samples),
        "samples": samples,
    }


def main():
    ap = argparse.ArgumentParser(description="从合规 score_report.json 构建小说评分参考分布")
    ap.add_argument("out_path", help="输出 JSON，建议 <作品根>/评分/reference_distribution_<日期>.json")
    ap.add_argument("--sample", action="append", required=True,
                    help="score_report.json|rights_status[|source_label|title]，可重复")
    ap.add_argument("--title", default="novel_reference_distribution")
    args = ap.parse_args()

    try:
        specs = [parse_sample(value) for value in args.sample]
        samples = [sample_from_report(spec) for spec in specs]
    except Exception as exc:
        print(f"[err] 构建参考分布失败：{exc}", file=sys.stderr)
        return 2
    payload = build_distribution(samples, title=args.title)
    out_path = os.path.abspath(args.out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[ok] reference distribution → {out_path}")
    print(f"     samples: {len(samples)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
