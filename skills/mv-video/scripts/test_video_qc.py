#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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


if __name__ == "__main__":
    unittest.main()
