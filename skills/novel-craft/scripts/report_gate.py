#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI wrapper for novel QA gate reports.

Usage:
    python3 skills/novel-craft/scripts/report_gate.py <作品根> [--json-out path] [--no-fail]
"""
import argparse
import json
import os
import sys

from qa_gate import collect_gate_status, format_gate_status, missing_score_report_scope
from waivers import append_waiver, make_waiver


def main():
    ap = argparse.ArgumentParser(description="读取 novel review/score 机器报告，判断是否阻断 export")
    ap.add_argument("project_root")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--no-fail", action="store_true", help="即使阻断也返回 0，仅用于报告")
    ap.add_argument("--progress-mode", action="store_true",
                    help="只做续跑提示：缺 review_report 记 warning，不作为 export 阻断")
    ap.add_argument("--waive-missing-score", action="store_true",
                    help="显式豁免商业/漫剧项目缺 score_report；会写 审稿/waiver_log.jsonl")
    ap.add_argument("--reason", default="explicit --waive-missing-score during report gate",
                    help="配合 --waive-missing-score 写入 waiver reason")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    status = collect_gate_status(root, require_review_report=not args.progress_mode)
    if args.waive_missing_score:
        score_missing = [b for b in status.get("blockers") or [] if b.get("id") == "SCORE-MISSING"]
        if not score_missing:
            print(format_gate_status(status))
            print("[err] 当前没有 SCORE-MISSING 阻断，不能记录 missing_score_report 豁免。", file=sys.stderr)
            sys.exit(2)
        waiver = make_waiver(
            "missing_score_report",
            reason=args.reason,
            affected_gate="score_report",
            source="novel-craft/scripts/report_gate.py",
            details={"blockers": score_missing},
            scope=missing_score_report_scope(root),
        )
        waiver["risk"] = "商业/漫剧项目缺少市场评分；本次只能证明人工决定跳过评分，不能证明作品具备市场通过性。"
        log_path = append_waiver(root, waiver)
        print(f"[warn] 已记录 missing_score_report 豁免：{log_path}", file=sys.stderr)
        status = collect_gate_status(root, require_review_report=not args.progress_mode)
    print(format_gate_status(status))
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    if status["blocking"] and not args.no_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
