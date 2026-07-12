# -*- coding: utf-8 -*-
"""cd skills/novel/_lib && python3 -m pytest test_sweep_schedule.py"""
import unittest

from sweep_schedule import in_midstory_band, is_due, next_due_after, window_for


class SweepScheduleTest(unittest.TestCase):
    def test_base_interval_behavior_unchanged_without_target(self):
        # target 未知：只有 interval 整数倍 due，与原平铺行为一致。
        dues = [c for c in range(1, 21) if is_due(c, 5, 0)]
        self.assertEqual(dues, [5, 10, 15, 20])
        self.assertEqual(window_for(10, 5, 0), (6, 10))
        self.assertEqual(next_due_after(11, 5, 0), 15)

    def test_project_tail_is_due(self):
        self.assertTrue(is_due(23, 5, 23))
        self.assertEqual(window_for(23, 5, 23), (21, 23))

    def test_midstory_band_densifies(self):
        # target=50，带 [20,30]，half=2：中段偶数章加密 due。
        self.assertTrue(in_midstory_band(24, 50))
        self.assertFalse(in_midstory_band(12, 50))
        self.assertTrue(is_due(22, 5, 50))   # 中段加密点
        self.assertFalse(is_due(23, 5, 50))  # 带内奇数章非 due
        self.assertTrue(is_due(25, 5, 50))   # 基础 due 不受影响
        self.assertFalse(is_due(32, 5, 50))  # 带外恢复平铺

    def test_windows_tile_without_gaps_across_band_edges(self):
        # 无缝覆盖：所有 due 窗口拼起来恰好铺满 1..target，无缺口无重叠。
        target, interval = 50, 5
        covered = []
        for c in range(1, target + 1):
            if is_due(c, interval, target):
                start, end = window_for(c, interval, target)
                covered.extend(range(start, end + 1))
        self.assertEqual(covered, list(range(1, target + 1)))

    def test_short_project_no_densify(self):
        dues = [c for c in range(1, 9) if is_due(c, 5, 8)]
        self.assertEqual(dues, [5, 8])  # 仅基础 due + 项目尾

    def test_interval_off(self):
        self.assertFalse(is_due(10, 0, 50))
        self.assertIsNone(next_due_after(10, 0, 50))


if __name__ == "__main__":
    unittest.main()
