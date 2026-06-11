#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""finalize_storyboard 纯函数单测。
    cd skills/ad-script && python3 test_finalize_storyboard.py
"""
import unittest

import finalize_storyboard as fs


class FinalizeStoryboardTest(unittest.TestCase):
    def test_parse_seconds(self):
        self.assertEqual(fs.parse_seconds("30s"), 30.0)
        self.assertEqual(fs.parse_seconds("15"), 15.0)
        self.assertEqual(fs.parse_seconds("1:30"), 90.0)

    def test_vo_total(self):
        dl = [{"时长": 2.0, "gap_after": 0.5}, {"时长": 3.0, "占位": True}]
        total, ph = fs.vo_total(dl)
        self.assertEqual(total, 5.5)
        self.assertTrue(ph)

    def test_shot_durations(self):
        sb = {"shots": [{"shot_id": "S1", "duration": 5}, {"clip_id": "S2", "时长": 4}]}
        self.assertEqual(fs.shot_durations(sb), [("S1", 5.0), ("S2", 4.0)])

    def test_fit_check_master_mismatch_block(self):
        f = fs.fit_check(30, 20, 0)
        self.assertTrue(any(x["kind"] == "master_duration_mismatch" and x["severity"] == "block" for x in f))

    def test_fit_check_within_tol_ok(self):
        self.assertEqual(fs.fit_check(30, 30.2, 28), [])

    def test_fit_check_vo_overflow_block(self):
        f = fs.fit_check(30, 28, 32)
        self.assertTrue(any(x["kind"] == "vo_overflow" and x["severity"] == "block" for x in f))

    def test_seam_check_warn(self):
        sb = {"shots": [{"continuity": {"need_end_frame": True}}]}
        f = fs.seam_check(sb)
        self.assertTrue(any(x["kind"] == "seam_missing_transition" for x in f))


if __name__ == "__main__":
    unittest.main()
