#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ai_usage.py tests.

Can run without pytest:
    python3 skills/mv/mv-craft/scripts/test_ai_usage.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import contract


HERE = os.path.dirname(os.path.abspath(__file__))
AI_USAGE = os.path.join(HERE, "ai_usage.py")


class MvAiUsageTest(unittest.TestCase):
    def test_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write(contract.settings_markdown("测试MV", contract.DEFAULT_SETTINGS))
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
                    "--territory", "CN",
                    "--realism", "stylized",
                    "--real-person", "none",
                    "--music-mode", "human",
                    "--human-contribution", "用户挑选视觉方案并审片。",
                    "--reviewer", "王导演",
                    "--no-progress",
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
            self.assertEqual(payload["project_root"], ".")
            self.assertEqual(payload["reviewer"], "王导演")
            self.assertIn("_设置.md", payload["inputs_sha256"])
            with open(md_path, encoding="utf-8") as f:
                md = f.read()
            self.assertIn("AI 使用说明", md)
            self.assertIn("用户挑选视觉方案", md)

    def test_default_command_does_not_hide_missing_progress_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write(contract.settings_markdown("测试MV", contract.DEFAULT_SETTINGS))
            result = subprocess.run([
                sys.executable, AI_USAGE, tmp,
                "--visual-mode", "AI-generated", "--video-mode", "AI-generated",
                "--publish-target", "抖音", "--territory", "CN", "--realism", "stylized",
                "--real-person", "none", "--music-mode", "human",
                "--human-contribution", "人工导演与挑版", "--reviewer", "王导演",
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("完成态未建立", result.stderr)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "合规", "ai_usage.json")))


if __name__ == "__main__":
    unittest.main()
