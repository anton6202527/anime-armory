#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_review_report tests. Can run without pytest."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import build_review_report as brr


HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "build_review_report.py")


class BuildReviewReportTest(unittest.TestCase):
    def test_mechanical_red_finding_becomes_review_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            os.makedirs(os.path.join(tmp, "章节"), exist_ok=True)
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"kind": "rewrite", "title": "测试"}, f, ensure_ascii=False)
            with open(os.path.join(tmp, "章节", "第01章.md"), "w", encoding="utf-8") as f:
                f.write("# 第1章\n正文\n")
            mechanical = os.path.join(tmp, "审稿", "mechanical_findings.json")
            with open(mechanical, "w", encoding="utf-8") as f:
                json.dump({
                    "kind": "novel_mechanical_findings",
                    "findings": [{
                        "chapter": 1,
                        "severity": "🔴",
                        "dim": "原文照搬",
                        "msg": "发现与原作连续雷同片段",
                        "evidence": "连续雷同片段",
                    }],
                }, f, ensure_ascii=False)

            report = brr.build_report(tmp, mechanical)
            self.assertEqual(report["summary"]["blocking_count"], 1)
            self.assertEqual(report["source_snapshot"]["kind"], "novel_text_snapshot")
            self.assertEqual(len(report["source_snapshot"]["files"]), 1)
            self.assertTrue(report["findings"][0]["blocking"])
            self.assertEqual(report["findings"][0]["recommended_skill"], "novel-rewrite")
            self.assertEqual(report["next_actions"][0]["priority"], "must")

    def test_cli_writes_review_report_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            mechanical = os.path.join(tmp, "审稿", "mechanical_findings.json")
            with open(mechanical, "w", encoding="utf-8") as f:
                json.dump({
                    "kind": "novel_mechanical_findings",
                    "findings": [{"chapter": 0, "severity": "🟡", "dim": "章号", "msg": "缺号：[2]"}],
                }, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--mechanical", mechanical],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            self.assertTrue(os.path.exists(os.path.join(tmp, "审稿", "review_report.json")))
            self.assertTrue(os.path.exists(os.path.join(tmp, "审稿", "审稿报告.md")))

    def test_missing_mechanical_file_is_hard_error_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("缺少机检文件", got.stderr)

            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--allow-missing-mechanical"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            with open(os.path.join(tmp, "审稿", "review_report.json"), encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report["summary"]["waiver_count"], 1)
            self.assertEqual(report["waivers"][0]["type"], "missing_mechanical")
            self.assertEqual(report["waivers"][0]["scope"]["review_scope"], "full")
            self.assertIn("source_aggregate_hash", report["waivers"][0]["scope"])
            self.assertIsNone(report["mechanical_findings_path"])
            with open(os.path.join(tmp, "审稿", "审稿报告.md"), encoding="utf-8") as f:
                md = f.read()
            self.assertIn("显式豁免", md)
            self.assertIn("missing_mechanical", md)


if __name__ == "__main__":
    unittest.main()
