#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

import formal_readiness
import production_pack


def make_project(root):
    for sub in ("分镜", "歌", "词", "出视频/视频", "设定"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试MV", "is_demo": True}, f, ensure_ascii=False)
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[chorus]\n一句歌词\n第二句歌词\n")
    clips = [
        {
            "clip_id": "Clip_001",
            "section": "chorus",
            "start": 0,
            "end": 3,
            "duration": 3,
            "image_path": "出图/段落/图片/Clip_001.png",
            "selected_video_path": "出视频/视频/Clip_001.mp4",
            "transition": "卡点硬切",
            "lyric_hint": "一句歌词",
            "shot_design": {
                "setup_group": "chorus/LOC_STAGE",
                "location_id": "LOC_STAGE",
                "location_name": "舞台",
                "lighting": "逆光",
                "shot_size": "中景",
                "angle": "低角度",
                "camera_movement": "快推",
            },
            "continuity": {"action": "举剑"},
        }
    ]
    with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "mv_clip_plan", "scope": "demo_excerpt", "clips": clips}, f, ensure_ascii=False)
    with open(os.path.join(root, "分镜", "timeline_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"song_path": "歌/song.wav", "clips": [{"clip_id": "Clip_001", "video_path": "出视频/视频/Clip_001.mp4"}]}, f, ensure_ascii=False)
    with open(os.path.join(root, "出视频", "jobs_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"jobs": [{"clip_id": "Clip_001", "selected_take": "take_01", "selected_video_path": "出视频/视频/Clip_001.mp4"}]}, f, ensure_ascii=False)
    with open(os.path.join(root, "设定", "identity_registry.json"), "w", encoding="utf-8") as f:
        json.dump({"reference_groups": [{"id": "REF_A", "status": "ready"}, {"id": "REF_B", "status": "planned"}]}, f, ensure_ascii=False)


class FormalProductionTest(unittest.TestCase):
    def test_demo_project_is_not_formal_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            report = formal_readiness.build_report(tmp)
            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertGreaterEqual(report["summary"]["blockers"], 1)

    def test_production_pack_builds_shot_list_and_animatic(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            shot_list, setups, animatic = production_pack.build_artifacts(tmp)
            self.assertEqual(len(shot_list), 1)
            self.assertEqual(setups[0]["setup_group"], "chorus/LOC_STAGE")
            self.assertEqual(animatic["clips"][0]["clip_id"], "Clip_001")


if __name__ == "__main__":
    unittest.main()
