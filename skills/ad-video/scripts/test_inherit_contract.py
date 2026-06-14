#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inherit_contract 纯函数 + 端到端单测。
    cd skills/ad-video/scripts && python3 -m pytest test_inherit_contract.py
"""
import json
import os
import tempfile
import unittest

import inherit_contract as ic


class InheritContractTest(unittest.TestCase):
    def test_brand_color_inherited_ok(self):
        c = {"品牌色": "#E60012", "光位锚": "45°主光", "轴线": "左到右"}
        txt = "运镜推近，品牌色 #E60012 铺底，45°主光，左到右轴线"
        self.assertEqual(ic.diff_contract(c, txt), [])

    def test_brand_color_drift_block(self):
        c = {"品牌色": "#E60012"}
        f = ic.diff_contract(c, "环绕运镜，暖调")
        self.assertTrue(any(x["field"] == "品牌色" and x["severity"] == "block" for x in f))

    def test_light_axis_block(self):
        c = {"光位锚": "45°主光", "轴线": "左到右"}
        f = ic.diff_contract(c, "随便拍")
        fields = {x["field"] for x in f if x["severity"] == "block"}
        self.assertIn("光位锚", fields)
        self.assertIn("轴线", fields)

    def test_soft_field_warn(self):
        c = {"画风": "写实电影感"}
        f = ic.diff_contract(c, "推近")
        self.assertTrue(any(x["field"] == "画风" and x["severity"] == "warn" for x in f))

    def test_missing_upstream_field_not_required(self):
        self.assertEqual(ic.diff_contract({}, "任意 prompt"), [])

    # ── 新增：HEX 格式变体不再误判（#E60012 vs rgb(230,0,18)） ──────────────────
    def test_brand_color_hex_vs_rgb_no_false_block(self):
        c = {"品牌色": "#E60012"}
        # 视频侧用 rgb() 写同一个颜色 → 不该 block
        f = ic.diff_contract(c, "环绕推近，主色 rgb(230, 0, 18) 铺底")
        self.assertEqual([x for x in f if x["field"] == "品牌色"], [])

    def test_brand_color_rgb_upstream_hex_clip(self):
        c = {"品牌色": "rgb(230,0,18)"}
        f = ic.diff_contract(c, "品牌色 #e60012 铺底")
        self.assertEqual([x for x in f if x["field"] == "品牌色"], [])

    def test_brand_color_short_hex(self):
        c = {"品牌色": "#f00"}
        f = ic.diff_contract(c, "主色 #FF0000")
        self.assertEqual([x for x in f if x["field"] == "品牌色"], [])

    def test_brand_color_real_drift_still_blocks(self):
        c = {"品牌色": "#E60012"}
        f = ic.diff_contract(c, "主色 rgb(0,0,255) 蓝调")
        self.assertTrue(any(x["field"] == "品牌色" and x["severity"] == "block" for x in f))

    def test_axis_paraphrase_superset_ok(self):
        c = {"轴线": "左到右"}
        # 归一化超集：标点/语气词差异不算漂移
        self.assertEqual(ic.diff_contract(c, "视线·左到右，越轴禁止"), [])

    # ── 新增：产品形态交接 ──────────────────────────────────────────────────
    def test_product_handoff_block_when_ref_dropped(self):
        f = ic.check_product_handoff({"PROD_main"}, "环绕推近产品，暖光")
        self.assertTrue(any(x["severity"] == "block" and x["field"] == "产品形态" for x in f))

    def test_product_handoff_ok_with_asset_ref(self):
        self.assertEqual(ic.check_product_handoff({"PROD_main"}, "资产引用：PROD_main 环绕推近"), [])

    def test_product_handoff_ok_with_lock_sentence(self):
        self.assertEqual(
            ic.check_product_handoff({"PROD_main"}, "推近，与产品参考图①同一包装、同一 logo、同一品牌色"), [])

    def test_product_handoff_no_prod_no_check(self):
        self.assertEqual(ic.check_product_handoff(set(), "随便拍"), [])

    # ── 新增：overview 解析（HEX + 别名标签） ──────────────────────────────
    def test_parse_overview_contract(self):
        md = (
            "# 出图总览\n\n"
            "## 视觉一致性契约\n"
            "- 品牌主色：#E60012（主色铺底）\n"
            "- 光位：45°主光\n"
            "- 轴线视线：左到右\n"
            "- 基础视觉风格：写实电影感\n"
            "\n## 别的节\n- 不该被吃进契约\n"
        )
        c = ic.parse_overview_contract(md)
        self.assertEqual(c["光位锚"], "45°主光")
        self.assertEqual(c["轴线"], "左到右")
        self.assertEqual(c["画风"], "写实电影感")
        self.assertIn("E60012", c["品牌色"])
        self.assertNotIn("构图", c)

    def test_storyboard_prod_by_index(self):
        sb = {"shots": [
            {"shot_id": "S1", "assets": {"CHAR_user": True, "PROD_main": False}},
            {"shot_id": "S2", "assets": {"PROD_main": True}},
        ]}
        out = ic.storyboard_prod_by_index(sb)
        self.assertEqual(out[1], set())
        self.assertEqual(out[2], {"PROD_main"})


class EndToEndTest(unittest.TestCase):
    def _project(self, td, *, overview=None, storyboard=None, prompts=None):
        if storyboard is not None:
            os.makedirs(os.path.join(td, "脚本"), exist_ok=True)
            with open(os.path.join(td, "脚本", "storyboard.json"), "w", encoding="utf-8") as f:
                json.dump(storyboard, f, ensure_ascii=False)
        if overview is not None:
            d = os.path.join(td, "出图", "分镜", "prompt")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "00_总览.md"), "w", encoding="utf-8") as f:
                f.write(overview)
        pd = os.path.join(td, "出视频", "分镜", "prompt")
        os.makedirs(pd, exist_ok=True)
        for name, body in (prompts or {}).items():
            with open(os.path.join(pd, name), "w", encoding="utf-8") as f:
                f.write(body)

    def test_overview_is_source_of_truth(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(
                td,
                overview="## 视觉一致性契约\n- 品牌色：#E60012\n- 光位锚：45°主光\n",
                # storyboard 故意给冲突的旧种子，验证优先读 overview
                storyboard={"visual_contract": {"品牌色": "#000000"}, "shots": []},
                prompts={"镜头01.md": "推近，品牌色 #E60012，45°主光"},
            )
            payload = ic.run(td)
            self.assertEqual(payload["contract_source"],
                             os.path.join("出图", "分镜", "prompt", "00_总览.md"))
            self.assertEqual(payload["summary"]["block"], 0)

    def test_fallback_to_storyboard_when_no_overview(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(
                td,
                storyboard={"visual_contract": {"品牌色": "#E60012"}, "shots": []},
                prompts={"镜头01.md": "推近，暖调"},  # 丢品牌色 → block
            )
            payload = ic.run(td)
            self.assertEqual(payload["contract_source"],
                             os.path.join("脚本", "storyboard.json"))
            self.assertGreaterEqual(payload["summary"]["block"], 1)

    def test_product_handoff_end_to_end_block(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(
                td,
                overview="## 视觉一致性契约\n- 品牌色：#E60012\n",
                storyboard={"visual_contract": {},
                            "shots": [{"shot_id": "S1", "assets": {"PROD_main": True}}]},
                # 镜头01 绑定 PROD_main 但 prompt 丢了产品引用
                prompts={"镜头01.md": "环绕推近，品牌色 #E60012"},
            )
            payload = ic.run(td)
            self.assertTrue(any(f["field"] == "产品形态" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_main_exit_code_block(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(
                td,
                overview="## 视觉一致性契约\n- 品牌色：#E60012\n- 光位锚：45°主光\n",
                storyboard={"shots": []},
                prompts={"镜头01.md": "随便拍，无任何继承"},
            )
            out = os.path.join(td, "出视频", "分镜", "contract_inheritance.json")
            with self.assertRaises(SystemExit) as cm:
                ic.main([td, "--json", out])
            self.assertEqual(cm.exception.code, 1)
            with open(out, encoding="utf-8") as f:
                payload = json.load(f)
            self.assertGreater(payload["summary"]["block"], 0)

    def test_main_exit_code_pass(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(
                td,
                overview="## 视觉一致性契约\n- 品牌色：#E60012\n- 光位锚：45°主光\n- 轴线：左到右\n",
                storyboard={"shots": [{"shot_id": "S1", "assets": {"PROD_main": True}}]},
                prompts={"镜头01.md": "推近，品牌色 #E60012，45°主光，左到右轴线，资产引用：PROD_main"},
            )
            with self.assertRaises(SystemExit) as cm:
                ic.main([td])
            self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
