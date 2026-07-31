#!/usr/bin/env python3
"""Reviewer calibration for n2d visual review."""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


CASES_FILE = "review_calibration_cases.json"
REPORT_JSON = "review_calibration.json"
REPORT_MD = "review_calibration.md"
KIND = "n2d_review_calibration"


def production_dir(root: str) -> Path:
    return Path(root) / "生产数据"


def cases_path(root: str) -> Path:
    return production_dir(root) / CASES_FILE


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def default_cases() -> Dict[str, Any]:
    return {
        "kind": "n2d_review_calibration_cases",
        "version": 1,
        "cases": [
            {
                "case_id": "CAL_FACE_001",
                "dimension": "character_consistency",
                "asset": "TODO: review_ui frame/clip path",
                "gold_label": "block",
                "rationale": "同一角色五官比例明显漂移",
            },
            {
                "case_id": "CAL_SEAM_001",
                "dimension": "scene_continuity",
                "asset": "TODO: seam frame pair",
                "gold_label": "warn",
                "rationale": "接缝构图轻微跳变但不影响叙事",
            },
        ],
    }


def write_cases(root: str, *, force: bool = False) -> Path:
    path = cases_path(root)
    if path.exists() and not force:
        raise RuntimeError(f"{path} already exists; use --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_cases(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_cases(root: str) -> Dict[str, Dict[str, Any]]:
    data = load_json(cases_path(root))
    if not isinstance(data, dict) or data.get("kind") != "n2d_review_calibration_cases":
        raise ValueError(f"missing or invalid {cases_path(root)}")
    out: Dict[str, Dict[str, Any]] = {}
    for item in data.get("cases") or []:
        if isinstance(item, dict) and item.get("case_id"):
            out[str(item["case_id"])] = item
    return out


def read_votes(path: Path) -> List[Dict[str, str]]:
    if path.suffix.lower() == ".jsonl":
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append({str(k): str(v) for k, v in item.items()})
        return rows
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    aliases = {"pass": "pass", "ok": "pass", "通过": "pass", "block": "block", "阻断": "block", "warn": "warn", "warning": "warn", "提醒": "warn"}
    return aliases.get(text, text)


def score_votes(root: str, votes_path: Path) -> Dict[str, Any]:
    cases = load_cases(root)
    votes = read_votes(votes_path)
    by_reviewer: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    by_dimension: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    by_case: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    unknown_cases: List[str] = []
    for vote in votes:
        case_id = str(vote.get("case_id") or "").strip()
        reviewer = str(vote.get("reviewer") or vote.get("reviewer_id") or "unknown").strip()
        label = normalize_label(vote.get("label") or vote.get("decision"))
        case = cases.get(case_id)
        if not case:
            unknown_cases.append(case_id)
            continue
        gold = normalize_label(case.get("gold_label"))
        correct = label == gold
        by_reviewer[reviewer]["total"] += 1
        by_reviewer[reviewer]["correct"] += int(correct)
        dim = str(case.get("dimension") or "unknown")
        by_dimension[dim]["total"] += 1
        by_dimension[dim]["correct"] += int(correct)
        by_case[case_id].append({"reviewer": reviewer, "label": label, "gold": gold})
    reviewer_rows = []
    for reviewer, row in sorted(by_reviewer.items()):
        total = row["total"]
        reviewer_rows.append({"reviewer": reviewer, "total": total, "accuracy": round(row["correct"] / total, 4) if total else None})
    dimension_rows = []
    for dim, row in sorted(by_dimension.items()):
        total = row["total"]
        dimension_rows.append({"dimension": dim, "total": total, "accuracy": round(row["correct"] / total, 4) if total else None})
    disagreements = []
    for case_id, rows in sorted(by_case.items()):
        labels = {row["label"] for row in rows}
        if len(labels) > 1:
            disagreements.append({"case_id": case_id, "labels": sorted(labels), "votes": rows})
    return {
        "kind": KIND,
        "version": 1,
        "root": root,
        "votes_path": str(votes_path),
        "case_count": len(cases),
        "vote_count": len(votes),
        "reviewers": reviewer_rows,
        "dimensions": dimension_rows,
        "disagreements": disagreements,
        "unknown_cases": sorted(set(unknown_cases)),
        "status": "needs_calibration" if disagreements or unknown_cases or any((r.get("accuracy") or 0) < 0.8 for r in reviewer_rows) else "pass",
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d 人审校准",
        "",
        f"- 状态：{payload.get('status')}",
        f"- case：{payload.get('case_count')}",
        f"- votes：{payload.get('vote_count')}",
        "",
        "## Reviewer",
        "",
        "| reviewer | total | accuracy |",
        "|---|---:|---:|",
    ]
    for row in payload.get("reviewers") or []:
        lines.append(f"| {row.get('reviewer')} | {row.get('total')} | {row.get('accuracy')} |")
    lines.extend(["", "## 分歧", ""])
    disagreements = payload.get("disagreements") or []
    lines.extend([f"- {d.get('case_id')}: {', '.join(d.get('labels') or [])}" for d in disagreements] or ["- 无"])
    lines.append("")
    return "\n".join(lines)


def write_report(root: str, payload: Dict[str, Any]) -> None:
    pdir = production_dir(root)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / REPORT_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (pdir / REPORT_MD).write_text(render_markdown(payload), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d reviewer calibration")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("root")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("score")
    p.add_argument("root")
    p.add_argument("--votes", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd == "init":
        path = write_cases(ns.root, force=ns.force)
        print(f"wrote {path}")
        return 0
    payload = score_votes(ns.root, Path(ns.votes))
    if ns.write:
        write_report(ns.root, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 1 if payload.get("status") != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
