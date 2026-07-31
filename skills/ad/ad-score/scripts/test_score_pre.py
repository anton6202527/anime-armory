#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad-score 纯函数 + 端到端单测。
    cd skills/ad/ad-score/scripts && python3 -m pytest test_score_pre.py
"""
import json
import os
import tempfile
import unittest

import score_pre as sp


class DeterministicDimTest(unittest.TestCase):
    def test_adlaw_block_is_hard_block(self):
        score, block, warn, hard = sp.adlaw_score({"summary": {"block": 2, "warn": 1}})
        self.assertTrue(hard)
        self.assertEqual(block, 2)
        self.assertEqual(warn, 1)

    def test_adlaw_warn_only_no_hard_block(self):
        score, block, warn, hard = sp.adlaw_score({"summary": {"block": 0, "warn": 3}})
        self.assertFalse(hard)
        self.assertEqual(score, 100.0 - 24.0)

    def test_adlaw_missing_report_no_risk(self):
        score, block, warn, hard = sp.adlaw_score(None)
        self.assertFalse(hard)
        self.assertEqual(score, 100.0)

    def test_brand_exposure_sweet_spot(self):
        sb = {"shots": [{"frame": "产品 hero"}, {"frame": "走在路上"}, {"frame": "logo 定格"}, {"frame": "空镜"}]}
        score, brand, total = sp.brand_exposure_score(sb)
        self.assertEqual((brand, total), (2, 4))  # 0.5 落甜点
        self.assertEqual(score, 100.0)

    def test_brand_exposure_too_low(self):
        sb = {"shots": [{"frame": "空镜"}] * 9 + [{"frame": "logo"}]}  # 0.1
        score, brand, total = sp.brand_exposure_score(sb)
        self.assertLess(score, 100.0)

    def test_brand_exposure_via_prod_asset(self):
        sb = {"shots": [{"frame": "走路", "assets": {"PROD_01": "x.png"}}, {"frame": "空镜"}]}
        _, brand, total = sp.brand_exposure_score(sb)
        self.assertEqual((brand, total), (1, 2))

    def test_brand_exposure_reads_storyboard_scene_shot_prompt_and_brand_asset(self):
        sb = {"clips": [
            {"scene": "星盒界面", "shot": "手机特写", "prompt": "星盒 App", "assets": {"BRAND_01": True}},
            {"scene": "空镜"},
        ]}
        _, brand, total = sp.brand_exposure_score(sb)
        self.assertEqual((brand, total), (1, 2))

    def test_duration_fit_on_target(self):
        score, dev = sp.duration_fit_score(30.0, 30.0)
        self.assertEqual(score, 100.0)

    def test_duration_fit_over_budget(self):
        score, dev = sp.duration_fit_score(45.0, 30.0)  # 50% 超
        self.assertEqual(score, 0.0)

    def test_duration_fit_no_target_not_penalized(self):
        score, dev = sp.duration_fit_score(30.0, 0)
        self.assertEqual(score, 100.0)

    def test_cta_mandatory_but_missing_is_zero(self):
        sb = {"shots": [{"frame": "产品镜"}]}
        self.assertEqual(sp.cta_score(sb, ["必须有 CTA 行动号召"]), 0.0)

    def test_cta_mandatory_and_present(self):
        sb = {"shots": [{"frame": "end card: 立即下单"}]}
        self.assertEqual(sp.cta_score(sb, ["CTA"]), 100.0)

    def test_cta_mandatory_dict_and_present(self):
        sb = {"shots": [{"shot": "片尾 end card", "product_lock": "CTA 立即预约"}]}
        self.assertEqual(sp.cta_score(sb, {"endcard_cta": "立即预约"}), 100.0)

    def test_first_3s_identity_present(self):
        sb = {"shots": [{"duration": 3, "shot": "产品 hero", "assets": {"PROD_APP": True}}]}
        score, checked = sp.first_3s_brand_product_score(sb)
        self.assertEqual(score, 100.0)
        self.assertTrue(checked[0]["has_identity"])

    def test_first_3s_identity_missing(self):
        sb = {"shots": [{"duration": 3, "shot": "空镜"}]}
        score, checked = sp.first_3s_brand_product_score(sb)
        self.assertEqual(score, 0.0)

    def test_hook_strong_first_shot(self):
        self.assertEqual(sp.hook_score({"shots": [{"frame": "痛点：你还在为X烦恼？"}]}), 100.0)

    def test_hook_slow_open_penalized(self):
        self.assertEqual(sp.hook_score({"shots": [{"frame": "空镜·城市缓起势"}]}), 30.0)


class DecisionTest(unittest.TestCase):
    def test_hard_block_always_reject(self):
        tier, blocked, reasons = sp.decide_tier(95, True, 80)
        self.assertEqual(tier, "reject")
        self.assertTrue(blocked)

    def test_no_threshold_is_advisory(self):
        tier, blocked, reasons = sp.decide_tier(50, False, None)
        self.assertEqual(tier, "advisory")
        self.assertFalse(blocked)

    def test_go_above_threshold(self):
        tier, blocked, _ = sp.decide_tier(85, False, 80)
        self.assertEqual(tier, "go")
        self.assertFalse(blocked)

    def test_revise_band(self):
        tier, blocked, _ = sp.decide_tier(70, False, 80)  # [60,80)
        self.assertEqual(tier, "revise")
        self.assertFalse(blocked)

    def test_reject_below_band(self):
        tier, blocked, _ = sp.decide_tier(50, False, 80)
        self.assertEqual(tier, "reject")
        self.assertFalse(blocked)

    def test_map_dim_stage(self):
        self.assertEqual(sp.map_dim_stage("钩子吸引力"), "ad-concept")
        self.assertEqual(sp.map_dim_stage("卖点清晰度"), "ad-script")
        self.assertEqual(sp.map_dim_stage("品牌调性"), "ad-image")
        self.assertEqual(sp.map_dim_stage("未知维度"), "ad-script")

    def test_combine_score_no_llm_equals_det(self):
        self.assertEqual(sp.combine_score(72.0, {}), 72.0)

    def test_combine_score_weighted(self):
        # 0.6*80 + 0.4*60 = 72
        self.assertEqual(sp.combine_score(80.0, {"a": 60.0}), 72.0)

    def test_parse_dims(self):
        self.assertEqual(sp.parse_dims(["钩子=72", "卖点=80.5", "坏的"]), {"钩子": 72.0, "卖点": 80.5})


class AffectedItemsTest(unittest.TestCase):
    def test_hard_block_yields_adscript_item(self):
        pre = {"hard_block": True, "dims": {"adlaw": 0, "brand_exposure": 100, "duration_fit": 100,
                                            "first_3s_brand_product": 100, "cta_present": 100, "hook": 100},
               "facts": {"adlaw_block": 2}}
        items = sp.affected_items(pre, {}, 80)
        self.assertTrue(any(i["item"] == "广告法机检" and i["return_to_stage"] == "ad-script" for i in items))

    def test_no_brand_routes_to_image(self):
        pre = {"hard_block": False, "dims": {"adlaw": 100, "brand_exposure": 0, "duration_fit": 100,
                                             "first_3s_brand_product": 100, "cta_present": 100, "hook": 100},
               "facts": {"brand_shots": 0}}
        items = sp.affected_items(pre, {}, 80)
        self.assertTrue(any(i["item"] == "brand_exposure" and i["return_to_stage"] == "ad-image" for i in items))


class EndToEndTest(unittest.TestCase):
    def _project(self, root, *, adlaw_block=0, shots=None, master="30s", total_seconds=30.0):
        os.makedirs(os.path.join(root, "脚本"), exist_ok=True)
        os.makedirs(os.path.join(root, "需求"), exist_ok=True)
        with open(os.path.join(root, "需求", "brief.json"), "w", encoding="utf-8") as f:
            json.dump({"master_duration": master, "mandatories": ["logo", "CTA 行动号召"]}, f, ensure_ascii=False)
        with open(os.path.join(root, "脚本", "广告法机检报告.json"), "w", encoding="utf-8") as f:
            json.dump({"region": "中国大陆", "summary": {"block": adlaw_block, "warn": 0}, "findings": []},
                      f, ensure_ascii=False)
        sb = {"shots": shots or [
            {"frame": "痛点：你还在为X烦恼？"}, {"frame": "产品 hero", "assets": {"PROD_01": "p.png"}},
            {"frame": "卖点演示"}, {"frame": "end card: logo + 立即下单 CTA"}]}
        with open(os.path.join(root, "脚本", "storyboard.json"), "w", encoding="utf-8") as f:
            json.dump(sb, f, ensure_ascii=False)
        with open(os.path.join(root, "脚本", "镜头时长.json"), "w", encoding="utf-8") as f:
            json.dump({"total_seconds": total_seconds}, f, ensure_ascii=False)

    def test_clean_project_goes(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td)
            payload = sp.build_payload(td, "30s", 70, {})
            self.assertEqual(payload["tier"], "go")
            self.assertFalse(payload["blocked"])

    def test_build_payload_reads_nested_deliverables_master_duration(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td)
            with open(os.path.join(td, "需求", "brief.json"), "w", encoding="utf-8") as f:
                json.dump({"deliverables": {"master_duration": "30s"},
                           "mandatories": {"endcard_cta": "立即下单"}}, f, ensure_ascii=False)
            payload = sp.build_payload(td, None, None, {})
            self.assertEqual(payload["master_target_seconds"], 30.0)
            self.assertEqual(payload["dims"]["duration_fit"], 100.0)

    def test_adlaw_block_rejects_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td, adlaw_block=1)
            payload = sp.build_payload(td, "30s", 70, {})
            self.assertEqual(payload["tier"], "reject")
            self.assertTrue(payload["hard_block"])
            self.assertTrue(any(i["return_to_stage"] == "ad-script" for i in payload["affected_items"]))

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td)
            self.assertEqual(sp.main([td, "--master", "30s", "--threshold", "70"]), 0)
            self._project(td, adlaw_block=2)
            self.assertEqual(sp.main([td, "--master", "30s", "--threshold", "70"]), 1)

    def test_main_missing_inputs_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(sp.main([td]), 2)

    def test_enqueue_writes_file(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td, adlaw_block=1)
            sp.main([td, "--threshold", "70", "--enqueue"])
            self.assertTrue(os.path.isfile(os.path.join(td, "评分", "回流清单.json")))


if __name__ == "__main__":
    unittest.main()
