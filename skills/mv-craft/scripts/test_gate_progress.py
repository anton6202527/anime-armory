#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate/progress tests.

Can run without pytest:
    python3 skills/mv-craft/scripts/test_gate_progress.py
"""
import json
import os
import tempfile
import unittest

import gate
import mv_utils


def make_project(root):
    for sub in ("歌", "词", "节拍", "分镜", "出图/段落/图片"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试", "song_timing": "先传音乐"}, f, ensure_ascii=False)
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write("""# 进度

## 制MV 阶段
| 阶段 | skill | 状态 |
|---|---|---|
| 项目骨架 | mv/scripts/init_project.py | [x] |
| clip/timeline 规划 | mv-plan/scripts/plan_clips.py | [ ] |
""")
    with open(os.path.join(root, "歌", "song.mp3"), "wb") as f:
        f.write(b"fake")
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[verse]\n一句歌词\n")
    with open(os.path.join(root, "节拍", "beatgrid.json"), "w", encoding="utf-8") as f:
        json.dump({"duration": 5, "beats": [1, 2], "downbeats": [1]}, f)
    with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
        f.write("# 视觉蓝图\n")


class GateProgressTest(unittest.TestCase):
    def test_find_song_and_plan_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            self.assertEqual(os.path.basename(mv_utils.find_song(tmp)), "song.mp3")
            errors, _warnings = gate.check(tmp, "plan")
            self.assertEqual(errors, [])

    def test_progress_stage_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            self.assertTrue(mv_utils.update_progress_stage(tmp, "plan"))
            text = mv_utils.read_text(os.path.join(tmp, "_进度.md"))
            self.assertIn("| clip/timeline 规划 | mv-plan/scripts/plan_clips.py | [x] |", text)

    def test_rough_blueprint_blocks_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "视觉蓝图.md"), "w", encoding="utf-8") as f:
                f.write("- 状态：rough（待成品歌/beatgrid 复核）\n")
            errors, _warnings = gate.check(tmp, "plan")
            self.assertTrue(any("rough" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
