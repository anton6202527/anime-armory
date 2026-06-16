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


if __name__ == "__main__":
    unittest.main()

