#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ai_usage.py tests.

Can run without pytest:
    python3 skills/mv-craft/scripts/test_ai_usage.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
AI_USAGE = os.path.join(HERE, "ai_usage.py")


class MvAiUsageTest(unittest.TestCase):
    def test_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "title": "测试MV",
                    "song_rights_status": "original",
                    "image_backend": "Codex",
                    "video_backend": "即梦",
                }, f, ensure_ascii=False)
            subprocess.run(
                [
                    sys.executable, AI_USAGE, tmp,
                    "--visual-mode", "AI-generated",
                    "--video-mode", "AI-generated",
                    "--publish-target", "抖音",
                    "--human-contribution", "用户挑选视觉方案并审片。",
                ],
                capture_output=True, text=True, check=True,
            )
            json_path = os.path.join(tmp, "合规", "ai_usage.json")
            md_path = os.path.join(tmp, "合规", "AI使用说明.md")
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(md_path))
            with open(json_path, encoding="utf-8") as f:
                payload = json.load(f)
            self.assertEqual(payload["visual_mode"], "AI-generated")
            self.assertEqual(payload["image_backend"], "Codex")
            with open(md_path, encoding="utf-8") as f:
                md = f.read()
            self.assertIn("AI 使用说明", md)
            self.assertIn("用户挑选视觉方案", md)


if __name__ == "__main__":
    unittest.main()
