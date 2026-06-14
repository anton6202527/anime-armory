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

    # ── 归一化绕过：全角/零宽/插空格/繁体都要命中 ──────────────────────────
    def test_fullwidth_bypass(self):
        # 全角 １００％ 经 NFKC 归一化后应等价于 100%，命中绝对化
        f = alc.scan_text("效果１００％满意。")
        self.assertIn("100%", terms(f))

    def test_inserted_space_bypass(self):
        # "最 佳" / "国 家 级" 中间插空格仍应命中
        f = alc.scan_text("本品是最 佳之选，国 家 级 认证。")
        self.assertIn("最佳", terms(f))
        self.assertIn("国家级", terms(f))

    def test_zero_width_bypass(self):
        # 零宽字符插入也应被剥掉后命中
        zwsp = "​"
        f = alc.scan_text(f"治{zwsp}愈系产品，根{zwsp}治失眠。")
        self.assertIn("治愈", terms(f))
        self.assertIn("根治", terms(f))

    def test_traditional_variant_bypass(self):
        # 繁体 療效 / 國家級 应归一化成 疗效 / 国家级 后命中
        f = alc.scan_text("本品有療效，國家級認證。")
        self.assertIn("疗效", terms(f))
        self.assertIn("国家级", terms(f))

    # ── 词库扩展：监管补充词必须命中 ────────────────────────────────────
    def test_regulator_gap_terms(self):
        f = alc.scan_text("销量遥遥领先，行业领导者，填补国内空白。")
        t = terms(f)
        self.assertIn("遥遥领先", t)
        self.assertIn("领导者", t)
        self.assertIn("填补国内空白", t)

    def test_cosmetics_forbidden_efficacy(self):
        f = alc.scan_text("祛斑生发，七天瘦身。")
        self.assertTrue(any(x["category"] == "化妆品禁用功效" and x["severity"] == "block" for x in f))
        self.assertIn("祛斑", terms(f))

    def test_finance_education_terms(self):
        f = alc.scan_text("保收益稳健高回报，名师押题保录取。")
        t = terms(f)
        self.assertIn("保收益", t)
        self.assertIn("保录取", t)

    def test_100pct_deduped(self):
        # "100%有效" 不应同时被 绝对化"100%" 与 医疗"100%有效" 双计同一位置
        f = alc.scan_text("本品100%有效。")
        at_zero = [x for x in f if x["line"] == 1 and x["col"] == f[0]["col"]]
        # 同一起点只保留一条（更长/更具体的医疗词）
        starts = [x["col"] for x in f]
        self.assertEqual(len(starts), len(set(starts)))

    # ── 海外口径：绝对化降级 warn，但促销欺诈仍硬 block ──────────────────
    def test_overseas_promo_still_blocks(self):
        f = alc.scan_text("全网最低价，仅此一天！", region="海外")
        promo = [x for x in f if x["category"] == "促销欺诈"]
        self.assertTrue(promo)
        self.assertTrue(all(x["severity"] == "block" for x in promo))

    def test_overseas_absolute_downgraded(self):
        f = alc.scan_text("全球第一的选择。", region="海外")
        hit = [x for x in f if x["term"] == "全球第一"][0]
        self.assertEqual(hit["severity"], "warn")

    # ── region 关闭：仍写 disabled 报告，不只 print ────────────────────
    def test_disabled_report(self):
        rep = alc.disabled_report("关闭")
        self.assertTrue(rep["disabled"])
        self.assertEqual(rep["summary"], {"block": 0, "warn": 0})
        self.assertIn("reason", rep)

    # ── storyboard.json 递归抽文本字段并扫描 ──────────────────────────
    def test_scan_storyboard_json(self):
        import os
        import json
        import tempfile
        sb = {"shots": [{"frame": "产品 hero shot 国家级认证",
                          "legal_lines": ["100%有效"]}]}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "storyboard.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(sb, fh, ensure_ascii=False)
            report = alc.scan_files([p], "中国大陆")
            self.assertGreaterEqual(report["summary"]["block"], 2)

    def test_disabled_region_writes_report_file(self):
        # region 关闭：main 仍写一份 disabled 报告，不只 print-and-exit
        import os
        import sys
        import json
        import subprocess
        import tempfile
        here = os.path.dirname(os.path.abspath(__file__))
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "脚本", "广告法机检报告.json")
            cmd = [sys.executable, os.path.join(here, "ad_law_check.py"), d,
                   "--region", "关闭", "--json", out]
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.isfile(out))
            with open(out, encoding="utf-8") as fh:
                rep = json.load(fh)
            self.assertTrue(rep["disabled"])
            self.assertEqual(rep["summary"], {"block": 0, "warn": 0})


if __name__ == "__main__":
    unittest.main()
