#!/usr/bin/env python3
import unittest

import beat_detect


class BeatPhaseTest(unittest.TestCase):
    def test_selects_strongest_bar_phase(self):
        frames = [0, 1, 2, 3, 4, 5, 6, 7]
        onset = [1, 2, 9, 1, 1, 2, 8, 1]
        phase, confidence, scores = beat_detect.estimate_bar_phase(frames, onset, 4)
        self.assertEqual(phase, 2)
        self.assertGreater(confidence, 0)
        self.assertEqual(len(scores), 4)

    def test_forced_phase_wins(self):
        phase, _confidence, _scores = beat_detect.estimate_bar_phase([0, 1, 2, 3], [1, 9, 1, 1], 4, forced=3)
        self.assertEqual(phase, 3)

    def test_section_coverage_requires_contiguous_full_song(self):
        ok, issues = beat_detect.section_coverage([
            {"start": 0.0, "end": 10.0},
            {"start": 10.0, "end": 20.0},
        ], 20.0)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

        ok, issues = beat_detect.section_coverage([
            {"start": 1.0, "end": 9.0},
            {"start": 10.0, "end": 18.0},
        ], 20.0)
        self.assertFalse(ok)
        self.assertIn("section_gap", issues)


if __name__ == "__main__":
    unittest.main()
