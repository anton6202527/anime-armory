#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cutdown + reframe 纯函数单测。
    cd skills/ad-compose && python3 test_cutdown_reframe.py
"""
import unittest

import cutdown
import reframe


class ReframeTest(unittest.TestCase):
    def test_aspect_value(self):
        self.assertAlmostEqual(reframe.aspect_value("16:9"), 16 / 9)
        self.assertAlmostEqual(reframe.aspect_value("1920x1080"), 16 / 9)
        self.assertAlmostEqual(reframe.aspect_value("9:16"), 9 / 16)

    def test_out_resolution(self):
        self.assertEqual(reframe.out_resolution("9:16", 1920), (1080, 1920))
        self.assertEqual(reframe.out_resolution("1:1", 1920), (1920, 1920))
        self.assertEqual(reframe.out_resolution("16:9", 1920), (1920, 1080))

    def test_reframe_filter_crop(self):
        vf = reframe.reframe_filter("1920x1080", "9:16", "crop", 1920)
        self.assertIn("crop=1080:1920", vf)
        self.assertIn("force_original_aspect_ratio=increase", vf)

    def test_reframe_filter_pad(self):
        vf = reframe.reframe_filter("1920x1080", "9:16", "pad", 1920)
        self.assertIn("pad=1080:1920", vf)
        self.assertIn("decrease", vf)


class CutdownTest(unittest.TestCase):
    def _shots(self):
        return [
            {"shot_id": "S1", "section": "钩子", "duration": 3},
            {"shot_id": "S2", "section": "痛点", "duration": 5},
            {"shot_id": "S3", "section": "情境", "duration": 4},
            {"shot_id": "S4", "section": "产品", "duration": 6},
            {"shot_id": "S5", "section": "证据", "duration": 4},
            {"shot_id": "S6", "section": "CTA", "duration": 3},
        ]

    def test_priority_keeps_skeleton(self):
        kept, total, _ = cutdown.plan_cutdown(self._shots(), 15)
        ids = set(kept_id for kept_id in (s["shot_id"] for s in kept))
        # 钩子/产品/CTA 必保
        self.assertTrue({"S1", "S4", "S6"} <= ids)

    def test_order_preserved(self):
        kept, _, _ = cutdown.plan_cutdown(self._shots(), 15)
        ids = [s["shot_id"] for s in kept]
        self.assertEqual(ids, sorted(ids, key=lambda x: int(x[1:])))

    def test_explicit_priority_override(self):
        shots = [{"shot_id": "A", "duration": 3, "cutdown_priority": 99},
                 {"shot_id": "B", "duration": 3, "cutdown_priority": 10}]
        kept, _, _ = cutdown.plan_cutdown(shots, 3)
        self.assertIn("A", [s["shot_id"] for s in kept])

    def test_parse_seconds(self):
        self.assertEqual(cutdown.parse_seconds("6s"), 6.0)
        self.assertEqual(cutdown.parse_seconds("1:00"), 60.0)


if __name__ == "__main__":
    unittest.main()
