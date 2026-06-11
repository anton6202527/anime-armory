#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad_law_check 单测。

从脚本自身目录跑：
    cd skills/ad-script && python -m pytest test_ad_law_check.py
或：
    cd skills/ad-script && python3 test_ad_law_check.py
"""
import unittest

import ad_law_check as alc


def terms(findings):
    return {f["term"] for f in findings}


def cats(findings):
    return {f["category"] for f in findings}


class AdLawCheckTest(unittest.TestCase):
    def test_absolute_terms_block(self):
        f = alc.scan_text("本品是国家级最佳产品，全国第一。")
        self.assertIn("国家级", terms(f))
        self.assertIn("最佳", terms(f))
        self.assertIn("全国第一", terms(f))
        self.assertTrue(all(x["severity"] == "block" for x in f if x["term"] in ("国家级", "最佳", "全国第一")))

    def test_medical_terms_block(self):
        f = alc.scan_text("七天根治，无副作用，100%有效。")
        self.assertIn("根治", terms(f))
        self.assertIn("无副作用", terms(f))
        self.assertTrue(any(x["category"] == "医疗保健极限词" and x["severity"] == "block" for x in f))

    def test_whitelist_not_flagged(self):
        # “最后/最初/第一时间/第一步” 是时间/序数义，不应作为绝对化用语命中
        f = alc.scan_text("最后一步，第一时间通知你，最初的设计。")
        self.assertNotIn("最后", terms(f))
        # 单字“最/第一”在白名单复合词内不报疑似
        suspected = [x for x in f if x["category"] == "绝对化用语(疑似)"]
        self.assertEqual(suspected, [])

    def test_loose_superlative_is_warn(self):
        # 裸“最”做最高级（非白名单、非严格词）→ 疑似 warn，交人判
        f = alc.scan_text("这是最懂你的助手。")
        sus = [x for x in f if x["category"] == "绝对化用语(疑似)"]
        self.assertTrue(sus)
        self.assertTrue(all(x["severity"] == "warn" for x in sus))

    def test_region_overseas_downgrades_absolute(self):
        f = alc.scan_text("全球第一的选择。", region="海外")
        hit = [x for x in f if x["term"] == "全球第一"][0]
        self.assertEqual(hit["severity"], "warn")

    def test_clean_text_no_findings(self):
        f = alc.scan_text("用更轻盈的方式，开启你的一天。")
        self.assertEqual(f, [])

    def test_scan_files_summary(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "广告脚本.md")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("国家级品质，最后冲刺。")
            report = alc.scan_files([p], "中国大陆")
            self.assertEqual(report["summary"]["block"], 1)  # 仅 国家级
            self.assertGreaterEqual(report["files"][0]["hits"], 1)


if __name__ == "__main__":
    unittest.main()
