#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run.py（mv 单一入口编排器）tests。

Can run without pytest:
    python3 skills/mv/test_run.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location("mv_run_test", os.path.join(HERE, "run.py"))
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)


def make_project(root, plan_done=False):
    for sub in ("歌", "词", "节拍", "分镜", "出图/段落/图片"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试", "song_timing": "先传音乐",
                   "song_rights_status": "自有", "is_demo": True}, f, ensure_ascii=False)
    rows = [
        ("项目骨架", "mv/scripts/init_project.py", "[x]"),
        ("歌曲入库/定稿", "user-file-ingest", "[x]"),
        ("节拍/能量", "mv-beat/scripts/beat_detect.py", "[x]"),
        ("clip/timeline 规划", "mv-plan/scripts/plan_clips.py", "[x]" if plan_done else "[ ]"),
        ("定妆/首帧/尾帧", "mv-image", "[ ]"),
    ]
    table = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows)
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write("# 进度\n\n## 制MV 阶段\n| 阶段 | skill | 状态 |\n|---|---|---|\n" + table + "\n")
    with open(os.path.join(root, "歌", "song.mp3"), "wb") as f:
        f.write(b"fake")
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[verse]\n一句歌词\n")
    with open(os.path.join(root, "节拍", "beatgrid.json"), "w", encoding="utf-8") as f:
        json.dump({"duration": 5, "beats": [1, 2], "downbeats": [1], "timing_verified": True}, f)
    with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
        f.write("# 视觉蓝图\n")


class NextActionTest(unittest.TestCase):
    def test_missing_progress_stops_with_init_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "missing_progress")
            self.assertIn("init_project", action["action_card"]["exact_command"])

    def test_frontier_plan_ready_to_run_with_exact_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            action = run.build_next_action(tmp)
            self.assertEqual(action["frontier"]["key"], "plan")
            self.assertEqual(action["stop_reason"], "ready_to_run")
            self.assertIn("plan_clips.py", action["action_card"]["exact_command"])
            self.assertEqual(action["gate"]["errors"], [])

    def test_gate_error_becomes_blocked_by_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "视觉蓝图.md"), "w", encoding="utf-8") as f:
                f.write("- 状态：rough（待成品歌/beatgrid 复核）\n")
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "blocked_by_gate")
            self.assertTrue(any("rough" in e for e in action["gate"]["errors"]))

    def test_paid_frontier_marks_paid_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp, plan_done=True)
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": [{"clip_id": "Clip_001",
                                      "image_path": "出图/段落/图片/Clip_001.png"}]}, f)
            action = run.build_next_action(tmp)
            self.assertEqual(action["frontier"]["key"], "image")
            self.assertTrue(action["action_card"]["paid_or_irreversible"])

    def test_all_stop_reasons_in_stage_actions_registered(self):
        for key, (stop, _cmd, _paid) in run.STAGE_ACTIONS.items():
            self.assertIn(stop, run.STOP_REASONS, f"stage {key} 用了未登记停因 {stop}")

    def test_na_rejects_unregistered_stop_reason(self):
        with self.assertRaises(ValueError):
            run.na({"stop_reason": "made_up_reason"})


class ImpactTest(unittest.TestCase):
    def _project(self, tmp):
        make_project(tmp, plan_done=True)
        clips = [
            {"clip_id": "Clip_001", "image_path": "出图/段落/图片/Clip_001.png",
             "seam_contract": {"type": "match_action"}},
            {"clip_id": "Clip_002", "image_path": "出图/段落/图片/Clip_002.png",
             "seam_contract": {"type": "beat_cut"}},
        ]
        with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
            json.dump({"clips": clips}, f, ensure_ascii=False)
        os.makedirs(os.path.join(tmp, "出视频"), exist_ok=True)
        with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"jobs": [{"clip_id": "Clip_001",
                                 "takes": [{"take_id": "take_01", "video_sha256": "f" * 64}]}]},
                      f, ensure_ascii=False)

    def test_unknown_clip_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            result = run.build_impact(tmp, "Clip_099", "image")
            self.assertIn("error", result)

    def test_image_change_cascades_to_registered_takes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            result = run.build_impact(tmp, "Clip_001", "image")
            actions = " ".join(s["action"] for s in result["steps"])
            self.assertIn("image_qc", actions)
            self.assertIn("first_frame_sha256", actions)
            self.assertIn("inherit_contract", actions)

    def test_edit_change_starts_from_replan(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            result = run.build_impact(tmp, "Clip_001", "edit")
            self.assertEqual(result["steps"][0]["stage"], "plan")

    def test_neighbor_seam_notes_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            result = run.build_impact(tmp, "Clip_002", "image")
            positions = {row["position"] for row in result["affected_neighbors"]}
            self.assertIn("prev", positions)

    def test_no_video_manifest_skips_video_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            os.remove(os.path.join(tmp, "出视频", "jobs_manifest.json"))
            result = run.build_impact(tmp, "Clip_002", "image")
            stages = {s["stage"] for s in result["steps"]}
            self.assertNotIn("video", stages)


if __name__ == "__main__":
    unittest.main()
