#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

import video_qc


class VideoQcPureTest(unittest.TestCase):
    def test_sample_times_uses_start_mid_end(self):
        self.assertEqual(video_qc.sample_times(10), [("start", 0.08), ("mid", 5.0), ("end", 9.92)])

    def test_color_distance(self):
        a = {"available": True, "mean_rgb": [0, 0, 0]}
        b = {"available": True, "mean_rgb": [3, 4, 0]}
        self.assertEqual(video_qc.color_distance(a, b), 5.0)
        self.assertIsNone(video_qc.color_distance({"available": False}, b))

    def test_location_key_prefers_shot_design_then_section(self):
        self.assertEqual(video_qc.location_key({"shot_design": {"location_id": "竹林"}}), "竹林")
        self.assertEqual(video_qc.location_key({"shot_design": {}, "section": "chorus1"}), "chorus1")
        self.assertEqual(video_qc.location_key({}), "")

    def _seam_fixture(self, prev_clip, cur_clip, prev_rgb, cur_rgb):
        clip_rows = [
            {"clip_id": "Clip_001", "verdict": "ok", "probe": {"duration": 4.0},
             "frame_samples": [{"label": "end", "ok": True,
                                "stats": {"available": True, "mean_rgb": prev_rgb, "perceptual_hash": None}}],
             "visual_adherence": {}},
            {"clip_id": "Clip_002", "verdict": "ok", "probe": {"duration": 4.0},
             "frame_samples": [{"label": "start", "ok": True,
                                "stats": {"available": True, "mean_rgb": cur_rgb, "perceptual_hash": None}}],
             "visual_adherence": {}},
        ]
        return video_qc.seam_rows([prev_clip, cur_clip], clip_rows)

    def test_same_scene_hard_cut_color_jump_flagged(self):
        prev = {"clip_id": "Clip_001", "shot_design": {"location_id": "竹林"}}
        cur = {"clip_id": "Clip_002", "shot_design": {"location_id": "竹林"}}
        rows = self._seam_fixture(prev, cur, [10, 10, 10], [200, 200, 200])
        self.assertIn("same_scene_hard_cut_color_jump", rows[0]["risk"])

    def test_cross_scene_hard_cut_color_jump_not_flagged(self):
        prev = {"clip_id": "Clip_001", "shot_design": {"location_id": "竹林"}}
        cur = {"clip_id": "Clip_002", "shot_design": {"location_id": "宫殿"}}
        rows = self._seam_fixture(prev, cur, [10, 10, 10], [200, 200, 200])
        self.assertNotIn("same_scene_hard_cut_color_jump", rows[0]["risk"])

    def test_continuous_seam_keeps_original_code(self):
        prev = {"clip_id": "Clip_001", "shot_design": {"location_id": "竹林"},
                "seam_contract": {"continuity_required": True}}
        cur = {"clip_id": "Clip_002", "shot_design": {"location_id": "竹林"}}
        rows = self._seam_fixture(prev, cur, [10, 10, 10], [200, 200, 200])
        self.assertIn("large_color_delta_breaks_continuous_seam", rows[0]["risk"])
        self.assertNotIn("same_scene_hard_cut_color_jump", rows[0]["risk"])

    def test_face_drift_threshold_calibrates_from_image_qc(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 无报告 → 经验回退
            threshold, source = video_qc.face_drift_threshold(tmp)
            self.assertEqual(threshold, video_qc.FACE_DRIFT_FALLBACK)
            self.assertEqual(source, "fallback_uncalibrated")
            out = os.path.join(tmp, "生产数据", "image_qc")
            os.makedirs(out)
            report = {"checks": {"face": {"lead_floor": 0.38, "lead_calibrated": True}}}
            with open(os.path.join(out, "image_qc.json"), "w", encoding="utf-8") as f:
                json.dump(report, f)
            threshold, source = video_qc.face_drift_threshold(tmp)
            self.assertAlmostEqual(threshold, 0.33)   # lead_floor - 0.05 运动余量
            self.assertEqual(source, "image_qc_lead_floor_calibrated")
            # 未自标定（单张定妆）→ 不采用，回退
            report["checks"]["face"]["lead_calibrated"] = False
            with open(os.path.join(out, "image_qc.json"), "w", encoding="utf-8") as f:
                json.dump(report, f)
            threshold, source = video_qc.face_drift_threshold(tmp)
            self.assertEqual(threshold, video_qc.FACE_DRIFT_FALLBACK)

    def test_face_drift_threshold_clamps_extremes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "生产数据", "image_qc")
            os.makedirs(out)
            report = {"checks": {"face": {"lead_floor": 0.05, "lead_calibrated": True}}}
            with open(os.path.join(out, "image_qc.json"), "w", encoding="utf-8") as f:
                json.dump(report, f)
            threshold, _source = video_qc.face_drift_threshold(tmp)
            self.assertEqual(threshold, 0.20)   # 下限保护：不许阈值烂到形同虚设


if __name__ == "__main__":
    unittest.main()
