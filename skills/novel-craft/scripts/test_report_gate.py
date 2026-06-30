#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_gate CLI tests. Can run without pytest."""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
REPORT_GATE = os.path.join(HERE, "report_gate.py")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


class ReportGateTest(unittest.TestCase):
    def test_waive_missing_score_logs_scoped_waiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "章节"), exist_ok=True)
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"draft_mode": "商业连载", "target_platform": "番茄"}, f, ensure_ascii=False)
            with open(os.path.join(tmp, "章节", "第01章.md"), "w", encoding="utf-8") as f:
                f.write("# 第1章\n正文\n")

            got = subprocess.run(
                [
                    sys.executable, REPORT_GATE, tmp,
                    "--progress-mode",
                    "--waive-missing-score",
                    "--reason", "test waiver",
                ],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            self.assertIn("SCORE-MISSING", got.stdout)
            waiver_log = os.path.join(tmp, "审稿", "waiver_log.jsonl")
            self.assertTrue(os.path.exists(waiver_log))
            with open(waiver_log, encoding="utf-8") as f:
                waiver = json.loads(f.readline())
            self.assertEqual(waiver["type"], "missing_score_report")
            self.assertEqual(waiver["scope"]["draft_mode"], "商业连载")
            self.assertEqual(waiver["scope"]["target_platform"], "番茄")
            self.assertEqual(waiver["scope"]["chapter_count"], 1)
            self.assertIn("source_aggregate_hash", waiver["scope"])


if __name__ == "__main__":
    unittest.main()
