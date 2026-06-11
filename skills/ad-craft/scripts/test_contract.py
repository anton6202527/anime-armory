#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad-craft contract tests.

从脚本自身目录跑（仓库无中央 runner）：
    cd skills/ad-craft/scripts && python -m pytest test_contract.py
或不装 pytest：
    cd skills/ad-craft/scripts && python3 test_contract.py
"""
import unittest

import contract


class AdContractTest(unittest.TestCase):
    def test_choice_points_include_ad_controls(self):
        points = contract.choice_points()
        for key in (
            "广告类型", "创意路线", "基础视觉风格", "主片时长", "交付比例",
            "cutdown版本", "生图AI", "一致性增强", "生视频AI", "出视频规格",
            "配音后端", "音乐来源", "品牌包装模板", "字幕语言", "广告法地区",
            "交付规格", "AI视觉使用披露",
        ):
            self.assertIn(key, points)
        self.assertIn("+LoRA", points["一致性增强"])
        self.assertIn("9:16", points["交付比例"])

    def test_stage_table_order(self):
        keys = [s["key"] for s in contract.stage_table()]
        self.assertEqual(
            keys[:8],
            ["brief", "concept", "script", "voice", "storyboard", "image", "video", "compose"],
        )
        # 高风险阶段是花钱/不可逆步骤的子集
        for g in contract.GATE_STAGES:
            self.assertIn(g, keys)

    def test_profiles(self):
        self.assertEqual(contract.video_spec_profile("预算一般")["resolution"], "720p")
        self.assertEqual(contract.delivery_profile("广电TVC")["loudness_lufs"], -23.0)
        self.assertEqual(contract.delivery_profile("平台默认")["loudness_lufs"], -16.0)

    def test_default_deliverables_cutdowns(self):
        rows = contract.default_deliverables("30s", "16:9", "主片+15s+6s")
        ids = [r["deliverable_id"] for r in rows]
        self.assertEqual(ids, ["master", "cut_15s", "cut_6s"])
        self.assertEqual(rows[0]["kind"], "master")
        only = contract.default_deliverables(cutdown_plan="仅主片")
        self.assertEqual([r["deliverable_id"] for r in only], ["master"])

    def test_classify_image_backend(self):
        self.assertEqual(contract.classify_image_backend("Codex"), ("codex", "approved"))
        self.assertEqual(contract.classify_image_backend("Seedream"), ("seedream", "approved"))
        self.assertEqual(contract.classify_image_backend("可灵主体库"), ("kling", "approved"))
        self.assertEqual(contract.classify_image_backend("即梦")[1], "forbidden")
        self.assertEqual(contract.classify_image_backend("某小众生图器")[1], "unknown")
        self.assertEqual(contract.DEFAULT_SETTINGS["生图AI"], "Codex")

    def test_settings_markdown(self):
        md = contract.settings_markdown("测试广告", {"交付比例": "9:16"})
        self.assertIn("# _设置 · 测试广告", md)
        self.assertIn("- 交付比例: 9:16", md)
        self.assertIn("## 记录", md)

    def test_progress_markdown(self):
        md = contract.progress_markdown("测试广告")
        self.assertIn("阶段进度", md)
        self.assertIn("交付版本矩阵", md)
        self.assertIn("剪辑包装", md)


if __name__ == "__main__":
    unittest.main()
