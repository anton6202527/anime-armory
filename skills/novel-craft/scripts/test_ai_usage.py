#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ai_usage.py contract tests.

Can run without pytest:
    python3 skills/novel-craft/scripts/test_ai_usage.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
AI_USAGE = os.path.join(HERE, "ai_usage.py")


class AiUsageTest(unittest.TestCase):
    def test_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "title": "测试新书",
                    "kind": "create",
                    "rights_status": "original",
                }, f, ensure_ascii=False)
            subprocess.run(
                [
                    sys.executable, AI_USAGE, tmp,
                    "--text-mode", "AI-generated",
                    "--publish-target", "KDP",
                    "--human-contribution", "用户提供蓝图、设定与人工审稿。",
                ],
                capture_output=True, text=True, check=True,
            )
            json_path = os.path.join(tmp, "合规", "ai_usage.json")
            md_path = os.path.join(tmp, "合规", "AI使用说明.md")
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(md_path))
            with open(json_path, encoding="utf-8") as f:
                payload = json.load(f)
            self.assertEqual(payload["text_mode"], "AI-generated")
            self.assertEqual(payload["publish_target"], "KDP")
            with open(md_path, encoding="utf-8") as f:
                md = f.read()
            self.assertIn("AI 使用说明", md)
            self.assertIn("用户提供蓝图", md)


if __name__ == "__main__":
    unittest.main()
