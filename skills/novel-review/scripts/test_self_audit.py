#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""self_audit.py tests."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
SELF_AUDIT = os.path.join(HERE, "self_audit.py")


class NovelSelfAuditTest(unittest.TestCase):
    def test_repo_self_audit_has_no_blocks_or_warnings(self):
        got = subprocess.run(
            [sys.executable, SELF_AUDIT, "--json"],
            capture_output=True, text=True, check=True,
        )
        report = json.loads(got.stdout)
        self.assertEqual(report["summary"]["block"], 0, report["findings"])
        self.assertEqual(report["summary"]["warn"], 0, report["findings"])
        self.assertTrue(any(item["id"] == "MARKET-NO-PROJECT" for item in report["findings"]))

    def test_project_market_baseline_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            score_dir = os.path.join(tmp, "评分")
            os.makedirs(score_dir, exist_ok=True)
            baseline = {
                "baseline_date": date.today().isoformat(),
                "expires_after_days": 21,
                "sources": [{"name": "manual", "status": "ok", "signals": ["热题材"]}],
                "notes": [],
            }
            with open(os.path.join(score_dir, f"market_baseline_{date.today().isoformat()}.json"), "w", encoding="utf-8") as f:
                json.dump(baseline, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, SELF_AUDIT, "--json", "--project-root", tmp],
                capture_output=True, text=True, check=True,
            )
            report = json.loads(got.stdout)
            self.assertEqual(report["summary"]["block"], 0, report["findings"])
            self.assertEqual(report["summary"]["warn"], 0, report["findings"])
            self.assertTrue(any(item["id"] == "MARKET-FRESH" for item in report["findings"]))

    def test_ingests_open_optimization_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            sig_dir = os.path.join(tmp, "生产数据")
            os.makedirs(sig_dir, exist_ok=True)
            with open(os.path.join(sig_dir, "优化信号.jsonl"), "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "kind": "score_coverage_gap", "skill": "novel-score",
                    "severity": "warn", "title": "覆盖缺口", "detail": "d",
                    "suggested_fix": "补证据", "signature": "abc", "status": "open",
                }, ensure_ascii=False) + "\n")
                # a resolved one must NOT surface
                f.write(json.dumps({
                    "kind": "score_low_verdict", "skill": "novel-score",
                    "severity": "advice", "title": "旧信号", "detail": "d",
                    "signature": "def", "status": "resolved",
                }, ensure_ascii=False) + "\n")
            got = subprocess.run(
                [sys.executable, SELF_AUDIT, "--json", "--project-root", tmp],
                capture_output=True, text=True, check=True,
            )
            report = json.loads(got.stdout)
            by_id = {item["id"]: item for item in report["findings"]}
            self.assertIn("FRICTION-SCORE-COVERAGE-GAP", by_id)
            self.assertEqual(by_id["FRICTION-SCORE-COVERAGE-GAP"]["severity"], "warn")
            self.assertNotIn("FRICTION-SCORE-LOW-VERDICT", by_id)

    def test_no_open_signals_reports_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = subprocess.run(
                [sys.executable, SELF_AUDIT, "--json", "--project-root", tmp],
                capture_output=True, text=True, check=True,
            )
            report = json.loads(got.stdout)
            friction = [i for i in report["findings"] if i["id"].startswith("FRICTION-")]
            self.assertEqual([i["id"] for i in friction], ["FRICTION-NONE"])
            self.assertEqual(friction[0]["severity"], "info")


if __name__ == "__main__":
    unittest.main()

