#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""video_jobs.py tests.

Can run without pytest:
    python3 skills/mv-video/scripts/test_video_jobs.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(HERE, "video_jobs.py")


def make_project(root):
    os.makedirs(os.path.join(root, "分镜"), exist_ok=True)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# _设置\n\n## 选择\n- 生视频AI: manual\n- 出视频规格: 预算一般\n")
    clips = [
        {
            "clip_id": "Clip_001",
            "section": "verse1",
            "start": 0,
            "end": 4,
            "duration": 4,
            "beat_role": "normal",
            "image_path": "出图/段落/图片/Clip_001.png",
            "selected_video_path": "出视频/视频/Clip_001.mp4",
            "transition": "动作切",
            "continuity": {"action": "缓推", "start_state": "开始", "end_state": "结束"},
        },
        {
            "clip_id": "Clip_002",
            "section": "chorus",
            "start": 4,
            "end": 6,
            "duration": 2,
            "beat_role": "key",
            "image_path": "出图/段落/图片/Clip_002.png",
            "selected_video_path": "出视频/视频/Clip_002.mp4",
            "transition": "卡点硬切",
            "continuity": {"action": "爆点", "start_state": "开始", "end_state": "结束"},
        },
    ]
    with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试MV", "clips": clips}, f, ensure_ascii=False)
    with open(os.path.join(root, "分镜", "timeline_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试MV", "clips": [{"clip_id": c["clip_id"], "video_path": c["selected_video_path"]} for c in clips]}, f, ensure_ascii=False)


class VideoJobsTest(unittest.TestCase):
    def test_creates_jobs_and_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            path = os.path.join(tmp, "出视频", "jobs_manifest.json")
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(len(manifest["jobs"]), 2)
            self.assertEqual(manifest["jobs"][0]["requested_takes"], 1)
            self.assertEqual(manifest["jobs"][1]["requested_takes"], 2)
            prompt = manifest["jobs"][1]["takes"][0]["prompt_path"]
            self.assertTrue(os.path.exists(os.path.join(tmp, prompt)))

    def test_register_score_select(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1"], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--score", "Clip_001", "--take", "1", "--motion-score", "5", "--identity-score", "4"], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--select", "Clip_001", "--take", "1"], capture_output=True, text=True, check=True)
            self.assertTrue(os.path.exists(os.path.join(tmp, "出视频", "视频", "Clip_001.mp4")))
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["jobs"][0]["selected_take"], "take_01")
            self.assertEqual(manifest["jobs"][0]["takes"][0]["score"]["motion"], 5)


if __name__ == "__main__":
    unittest.main()
