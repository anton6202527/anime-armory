#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv-craft contract tests.

Can run without pytest:
    python3 skills/mv-craft/scripts/test_contract.py
"""
import unittest

import contract


class MvContractTest(unittest.TestCase):
    def test_choice_points_include_mv_controls(self):
        points = contract.choice_points()
        for key in ("MV用途", "MV视觉风格", "MV规划粒度", "卡点策略", "生视频AI", "出视频规格", "AI视觉使用披露"):
            self.assertIn(key, points)
        self.assertIn("Kling", points["生视频AI"])

    def test_profiles(self):
        self.assertEqual(contract.video_spec_profile("预算一般")["resolution"], "720p")
        self.assertEqual(contract.plan_granularity_profile("标准")["chorus_bars"], 1)

    def test_settings_markdown(self):
        md = contract.settings_markdown("测试MV", {"合成画幅": "9:16"})
        self.assertIn("# _设置 · 测试MV", md)
        self.assertIn("- 合成画幅: 9:16", md)
        self.assertIn("## 记录", md)

    def test_classify_image_backend(self):
        # 阶段1：官方后端放行，逆向禁，未知 WARN（unknown）
        self.assertEqual(contract.classify_image_backend("Codex"), ("codex", "approved"))
        self.assertEqual(contract.classify_image_backend("Seedream"), ("seedream", "approved"))
        self.assertEqual(contract.classify_image_backend("可灵主体库"), ("kling", "approved"))
        self.assertEqual(contract.classify_image_backend("Sora Cameo"), ("sora", "approved"))
        self.assertEqual(contract.classify_image_backend("即梦")[1], "forbidden")
        self.assertEqual(contract.classify_image_backend("Dreamina")[1], "forbidden")
        self.assertEqual(contract.classify_image_backend("某小众生图器")[1], "unknown")
        self.assertEqual(contract.DEFAULT_SETTINGS["生图AI"], "Codex")


if __name__ == "__main__":
    unittest.main()
