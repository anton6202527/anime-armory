#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run lightweight golden calibration cases for the novel pipeline.

The fixture projects are intentionally tiny. They validate deterministic
contracts around pipeline routing, retrieval golden cases, score report fields,
and review blocker counts without calling model APIs or using real projects.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from typing import Any


HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, "..", "_lib"))
for path in (HERE, LIB):
    if path not in sys.path:
        sys.path.insert(0, path)

from novel_pipeline import dry_run_plan  # noqa: E402
import vector_store_eval  # noqa: E402


DEFAULT_CASES = os.path.join(HERE, "tests", "golden_projects.json")


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_fixture(root: str, rel_path: str, value: Any) -> None:
    path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(value, (dict, list)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(value))


def materialize_case(root: str, case: dict[str, Any]) -> None:
    for rel_path, value in (case.get("files") or {}).items():
        write_fixture(root, rel_path, value)


def check_case(root: str, case: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    expected = case.get("expected") or {}
    plan = dry_run_plan(root)
    if "next_stage" in expected and plan.get("next_stage") != expected["next_stage"]:
        failures.append(f"next_stage expected {expected['next_stage']} got {plan.get('next_stage')}")
    done = {stage["key"] for stage in plan.get("stages") or [] if stage.get("status") == "done"}
    for key in expected.get("done_stages") or []:
        if key not in done:
            failures.append(f"stage {key} expected done")

    retrieval = None
    if expected.get("retrieval_passed") is not None:
        retrieval = vector_store_eval.evaluate_project(
            root, top_k=int(expected.get("retrieval_top_k") or 1), engine="production")  # 校准上线引擎
        if bool(retrieval.get("passed")) is not bool(expected["retrieval_passed"]):
            failures.append(f"retrieval_passed expected {expected['retrieval_passed']} got {retrieval.get('passed')}")

    score_report = load_json(os.path.join(root, "评分", "score_report.json")) if os.path.exists(os.path.join(root, "评分", "score_report.json")) else {}
    if "score_total" in expected and float(score_report.get("total_score") or 0) != float(expected["score_total"]):
        failures.append(f"score_total expected {expected['score_total']} got {score_report.get('total_score')}")
    if "score_verdict" in expected and score_report.get("verdict") != expected["score_verdict"]:
        failures.append(f"score_verdict expected {expected['score_verdict']} got {score_report.get('verdict')}")

    review_report = load_json(os.path.join(root, "审稿", "review_report.json")) if os.path.exists(os.path.join(root, "审稿", "review_report.json")) else {}
    if "review_blocking_count" in expected:
        summary = review_report.get("summary") if isinstance(review_report.get("summary"), dict) else {}
        blocking = summary.get("blocking_count")
        if blocking is None:
            blocking = sum(1 for item in review_report.get("findings") or [] if item.get("blocking"))
        if int(blocking or 0) != int(expected["review_blocking_count"]):
            failures.append(f"review_blocking_count expected {expected['review_blocking_count']} got {blocking}")

    return {
        "name": case.get("name") or os.path.basename(root),
        "passed": not failures,
        "failures": failures,
        "next_stage": plan.get("next_stage"),
        "project_kind": plan.get("project_kind"),
        "retrieval": None if retrieval is None else {
            "passed": retrieval.get("passed"),
            "metrics": retrieval.get("metrics"),
        },
    }


def run_calibration(cases_path: str = DEFAULT_CASES, *, keep: bool = False) -> dict[str, Any]:
    cases = load_json(cases_path)
    if not isinstance(cases, list):
        raise ValueError("golden projects fixture must be a list")
    results = []
    keep_roots: list[str] = []
    for case in cases:
        if keep:
            root = tempfile.mkdtemp(prefix=f"novel_golden_{case.get('name', 'case')}_")
            materialize_case(root, case)
            results.append(check_case(root, case) | {"project_root": root})
            keep_roots.append(root)
        else:
            with tempfile.TemporaryDirectory() as root:
                materialize_case(root, case)
                results.append(check_case(root, case))
    passed = all(item.get("passed") for item in results)
    return {
        "schema_version": 1,
        "kind": "novel_golden_calibration_report",
        "cases_path": cases_path,
        "case_count": len(results),
        "passed": passed,
        "failure_count": sum(1 for item in results if not item.get("passed")),
        "results": results,
        "kept_roots": keep_roots,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run lightweight novel golden calibration cases")
    parser.add_argument("--cases", default=DEFAULT_CASES)
    parser.add_argument("--keep", action="store_true", help="keep materialized temp projects for inspection")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run_calibration(args.cases, keep=args.keep)
    except Exception as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"golden calibration: {'passed' if report['passed'] else 'failed'} ({report['case_count']} cases)")
        for item in report["results"]:
            print(f"- {item['name']}: {'pass' if item['passed'] else 'fail'} next={item.get('next_stage')}")
            for failure in item.get("failures") or []:
                print(f"  - {failure}")
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
