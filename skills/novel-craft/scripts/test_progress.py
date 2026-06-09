#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Progress contract tests.

Can run without pytest:
    python3 skills/novel-craft/scripts/test_progress.py
"""
import os
import json
import subprocess
import sys
import tempfile
import unittest

import contract
import progress


class ProgressContractTest(unittest.TestCase):
    def test_scan_progress_prefers_stable_stage_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_进度.md"), "w", encoding="utf-8") as f:
                f.write("# 进度\n\n")
                f.write(contract.derived_stage_markdown("expand"))
                f.write("\n\n## 人类细节\n- [ ] 事件骨架精筛\n")
            items = progress.scan_progress(tmp)
            self.assertEqual(items[0]["stage"], "source_model")
            self.assertIn("事件骨架", items[0]["item"])

    def test_scan_progress_reads_create_stage_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_进度.md"), "w", encoding="utf-8") as f:
                f.write("# 进度\n\n")
                f.write(contract.create_stage_markdown())
                f.write("\n\n## 人类细节\n- [ ] 创作蓝图细化\n")
            items = progress.scan_progress(tmp)
            self.assertEqual(items[0]["stage"], "blueprint")
            self.assertIn("创作蓝图", items[0]["item"])

    def test_progress_reports_stage_owner_and_qa_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"kind": "create", "title": "测试"}, f, ensure_ascii=False)
            with open(os.path.join(tmp, "_进度.md"), "w", encoding="utf-8") as f:
                f.write(contract.create_stage_markdown().replace("[ ] 导出", "[ ] 导出"))
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            with open(os.path.join(tmp, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "findings": [{
                        "id": "REV-001",
                        "blocking": True,
                        "return_to_stage": "outline",
                        "recommended_skill": "novel-create",
                        "problem": "主线断裂",
                    }],
                    "next_actions": [{
                        "priority": "must",
                        "action": "重修章纲",
                        "recommended_skill": "novel-create",
                        "return_to_stage": "outline",
                    }],
                }, f, ensure_ascii=False)
            out = subprocess.run(
                [sys.executable, progress.__file__, tmp],
                capture_output=True, text=True, check=True,
            ).stdout
            self.assertIn("owner: novel-create", out)
            self.assertIn("[block]", out)
            self.assertIn("REV-001", out)

    def test_completed_progress_still_reports_qa_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"kind": "create", "title": "测试"}, f, ensure_ascii=False)
            progress_md = contract.create_stage_markdown().replace("- [ ]", "- [x]")
            with open(os.path.join(tmp, "_进度.md"), "w", encoding="utf-8") as f:
                f.write(progress_md)
            os.makedirs(os.path.join(tmp, "评分"), exist_ok=True)
            with open(os.path.join(tmp, "评分", "score_report.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "verdict": "大改",
                    "next_actions": [{
                        "recommended_skill": "novel-rewrite",
                        "return_to_stage": "direction_spec",
                    }],
                }, f, ensure_ascii=False)
            out = subprocess.run(
                [sys.executable, progress.__file__, tmp],
                capture_output=True, text=True, check=True,
            ).stdout
            self.assertIn("QA gate 仍有阻断", out)
            self.assertIn("SCORE-VERDICT", out)


if __name__ == "__main__":
    unittest.main()
