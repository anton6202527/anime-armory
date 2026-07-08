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
            os.makedirs(os.path.join(tmp, "章节"), exist_ok=True)
            with open(os.path.join(tmp, "章节", "第01章.md"), "w", encoding="utf-8") as f:
                f.write("正文\n")
            subprocess.run(
                [
                    sys.executable, AI_USAGE, tmp,
                    "--text-mode", "AI-generated",
                    "--publish-target", "KDP",
                    "--human-contribution", "用户提供蓝图、设定与人工审稿。",
                    "--text-directness", "outline_to_draft",
                    "--human-steering", "人工指定大纲、角色弧和终稿取舍。",
                    "--replaceability", "assistive_non_replaceable",
                    "--direct-incorporation", "substantial_passages",
                    "--default-chapter-mode", "human_revised_ai_draft",
                    "--review-step", "人工通读",
                    "--review-step", "设定一致性审稿",
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
            self.assertEqual(payload["text_authorship_mode"], "AI生成")
            self.assertEqual(payload["publish_target"], "KDP")
            self.assertEqual(payload["disclosure_detail"]["text_directness"], "outline_to_draft")
            self.assertEqual(payload["disclosure_detail"]["review_steps"], ["人工通读", "设定一致性审稿"])
            self.assertEqual(payload["chapter_usage"][0]["chapter"], 1)
            self.assertEqual(payload["chapter_usage"][0]["usage_mode"], "human_revised_ai_draft")
            with open(md_path, encoding="utf-8") as f:
                md = f.read()
            self.assertIn("AI 使用说明", md)
            self.assertIn("用户提供蓝图", md)
            self.assertIn("正文主创模式", md)
            self.assertIn("人工 steering", md)


if __name__ == "__main__":
    unittest.main()
