#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""motion_axes.py 纯函数测试（mv 线两轴：质量档 + 运动参考）。

Can run without pytest:
    python3 skills/mv/mv-video/scripts/test_motion_axes.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import motion_axes


SEEDANCE = "Seedance 2.0"
KLING = "可灵/Kling"
MANUAL = "manual"


class QualityTierTest(unittest.TestCase):
    def test_chorus_clip_is_high(self):
        clip = {"section": "chorus", "beat_role": "key"}
        self.assertEqual(motion_axes.quality_tier_for_clip(clip, SEEDANCE), "high")

    def test_chorus_by_section_name_only(self):
        # 即使 beat_role 缺，section 含 chorus 也判 high（判据来源 section）
        clip = {"section": "Chorus 2"}
        self.assertEqual(motion_axes.quality_tier_for_clip(clip, SEEDANCE), "high")

    def test_beat_hit_transition_is_high(self):
        clip = {"section": "verse1", "transition": "卡点硬切"}
        self.assertEqual(motion_axes.quality_tier_for_clip(clip, SEEDANCE), "high")

    def test_high_energy_is_high(self):
        clip = {"section": "verse2", "energy_level": "Level 9"}
        self.assertEqual(motion_axes.quality_tier_for_clip(clip, SEEDANCE), "high")

    def test_verse_clip_is_fast(self):
        clip = {"section": "verse1", "beat_role": "normal", "transition": "动作切",
                "energy_level": "Level 3"}
        self.assertEqual(motion_axes.quality_tier_for_clip(clip, SEEDANCE), "fast")

    def test_backend_without_quality_tier_is_na(self):
        clip = {"section": "chorus", "beat_role": "key"}
        self.assertEqual(motion_axes.quality_tier_for_clip(clip, MANUAL), "n/a")

    def test_missing_signals_degrade_to_fast(self):
        # 缺所有信号不臆造副歌，降级 fast
        clip = {}
        self.assertEqual(motion_axes.quality_tier_for_clip(clip, KLING), "fast")


class MotionReferenceTest(unittest.TestCase):
    def test_dance_clip_supported_backend_applicable(self):
        clip = {"section": "chorus", "action_family": "dance_hit/vfx_burst"}
        plan = motion_axes.motion_reference_plan(clip, SEEDANCE)
        self.assertTrue(plan["applicable"])
        self.assertEqual(plan["use"], "prior_approved_clip_as_video_reference")

    def test_orbit_motif_applicable(self):
        clip = {"section": "chorus", "action_family": "performance_pose",
                "transition_motif": "光效切/whip pan"}
        plan = motion_axes.motion_reference_plan(clip, KLING)
        self.assertTrue(plan["applicable"])

    def test_non_dance_clip_not_applicable(self):
        clip = {"section": "verse1", "action_family": "performance_pose/expressive_walk"}
        plan = motion_axes.motion_reference_plan(clip, SEEDANCE)
        self.assertFalse(plan["applicable"])

    def test_backend_without_motion_reference_not_applicable(self):
        # 舞蹈镜但后端不支持视频参考 → not applicable
        clip = {"section": "chorus", "action_family": "dance_hit/vfx_burst"}
        plan = motion_axes.motion_reference_plan(clip, "Veo 3.1")
        self.assertFalse(plan["applicable"])

    def test_manual_backend_not_applicable(self):
        clip = {"section": "chorus", "action_family": "dance_hit"}
        plan = motion_axes.motion_reference_plan(clip, MANUAL)
        self.assertFalse(plan["applicable"])


if __name__ == "__main__":
    unittest.main()
