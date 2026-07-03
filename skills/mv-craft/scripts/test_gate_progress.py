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
        json.dump({"title": "测试", "song_timing": "先传音乐", "song_rights_status": "自有"}, f, ensure_ascii=False)
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


def write_clip_plan_with_image(root):
    os.makedirs(os.path.join(root, "出图", "段落", "图片"), exist_ok=True)
    with open(os.path.join(root, "出图", "段落", "图片", "Clip_001.png"), "wb") as f:
        f.write(b"fake")
    with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"clips": [{"clip_id": "Clip_001", "image_path": "出图/段落/图片/Clip_001.png"}]},
                  f, ensure_ascii=False)


def write_image_qc(root, hard=0, precision="full", advisory=0):
    path = os.path.join(root, "生产数据", "image_qc", "image_qc.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "kind": "mv_image_qc",
            "summary": {
                "hard_blocks": hard,
                "advisory": advisory,
                "verdict": "block" if hard else ("review" if advisory else "ok"),
            },
            "qc_environment": {"precision_level": precision},
        }, f, ensure_ascii=False)


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

    def test_video_jobs_requires_image_qc(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            errors, _warnings = gate.check(tmp, "video_jobs")
            self.assertTrue(any("image_qc" in e for e in errors))

    def test_video_jobs_blocks_image_qc_hard_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp, hard=1)
            errors, _warnings = gate.check(tmp, "video_jobs")
            self.assertTrue(any("hard block=1" in e for e in errors))

    def test_video_jobs_passes_full_image_qc(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp)
            errors, _warnings = gate.check(tmp, "video_jobs")
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
