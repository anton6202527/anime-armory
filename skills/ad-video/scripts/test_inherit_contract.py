#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inherit_contract 纯函数单测。
    cd skills/ad-video/scripts && python3 test_inherit_contract.py
"""
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


if __name__ == "__main__":
    unittest.main()
