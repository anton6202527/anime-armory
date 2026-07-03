#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_clips.py tests.

Can run without pytest:
    python3 skills/mv-plan/scripts/test_plan_clips.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, "plan_clips.py")


def make_project(root):
    for sub in ("词", "节拍", "歌"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试MV", "structure": ["verse1", "chorus"]}, f, ensure_ascii=False)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# _设置\n\n## 选择\n- MV规划粒度: 标准\n- 卡点策略: 副歌强卡点\n- MV视觉风格: 国风写意\n")
    with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
        f.write("# 视觉蓝图\n少年下山。\n")
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[verse1]\n山门外风起\n\n[chorus]\n仗剑下山闯人间\n")
    with open(os.path.join(root, "歌", "song.mp3"), "wb") as f:
        f.write(b"fake mp3")
    bg = {
        "duration": 16.0,
        "bpm": 120,
        "meter": 4,
        "beats": [x * 0.5 for x in range(1, 32)],
        "downbeats": [0, 2, 4, 6, 8, 10, 12, 14, 16],
        "sections": [
            {"section": "verse1", "start": 0, "end": 8},
            {"section": "chorus", "start": 8, "end": 16},
        ],
    }
    with open(os.path.join(root, "节拍", "beatgrid.json"), "w", encoding="utf-8") as f:
        json.dump(bg, f, ensure_ascii=False)


class PlanClipsTest(unittest.TestCase):
    def test_generates_clip_plan_and_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run([sys.executable, PLAN, tmp], capture_output=True, text=True, check=True)
            plan_path = os.path.join(tmp, "分镜", "clip_plan.json")
            timeline_path = os.path.join(tmp, "分镜", "timeline_manifest.json")
            self.assertTrue(os.path.exists(plan_path))
            self.assertTrue(os.path.exists(timeline_path))
            with open(plan_path, encoding="utf-8") as f:
                plan = json.load(f)
            self.assertGreaterEqual(len(plan["clips"]), 4)
            self.assertEqual(plan["visual_style"], "国风写意")
            with open(timeline_path, encoding="utf-8") as f:
                timeline = json.load(f)
            self.assertEqual(timeline["song_path"], "歌/song.mp3")
            first = plan["clips"][0]
            self.assertIn("action_family", first)
            self.assertIn("action_peak", first)
            self.assertIn("visual_motif", first)
            self.assertTrue(os.path.exists(os.path.join(tmp, first["image_prompt_path"])))
            self.assertTrue(os.path.exists(os.path.join(tmp, first["video_prompt_path"])))


if __name__ == "__main__":
    unittest.main()
