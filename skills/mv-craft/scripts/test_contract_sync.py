#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漂移护栏：mv-craft/scripts/contract.py 的 CHOICE_POINTS（mv-craft 生成 _设置.md
菜单用）与 mv/_lib/settings.py 的 SETTING_SPECS（设置校验用）是两条独立 import 路径下的 vendored 契约。

不变量：**contract 菜单里给用户的每个候选值，settings 校验器都必须接受**
（contract.CHOICE_POINTS[key] ⊆ settings_spec(key, "mv").allowed）。
否则会出现「菜单给了 1:1 / 自定义，用户一选 validate_setting 却判 invalid」这类
split-brain。settings 允许额外携带便捷别名（如 Seedance↔Seedance 2.0），故用子集而非等值。

从脚本自身目录跑：
    cd skills/mv-craft/scripts && python3 -m pytest test_contract_sync.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MV_LIB = os.path.join(REPO, "skills", "mv", "_lib")
sys.path.insert(0, HERE)
sys.path.insert(0, MV_LIB)

import contract  # mv-craft/scripts/contract.py
import settings as mv_settings  # mv/_lib/settings.py


class ContractSettingsSyncTest(unittest.TestCase):
    def test_choice_points_subset_of_settings_allowed(self):
        for key, values in contract.CHOICE_POINTS.items():
            with self.subTest(choice_point=key):
                spec = mv_settings.get_setting_spec(key, family="mv")
                self.assertIsNotNone(
                    spec, f"contract 选择点 {key!r} 在 settings.SETTING_SPECS(mv) 里没有对应 SettingSpec")
                # 空 allowed = 自由文本（parameterized），不做候选校验，跳过
                if not spec.allowed:
                    continue
                missing = sorted(set(values) - set(spec.allowed))
                self.assertEqual(
                    missing, [],
                    f"契约菜单 {key!r} 提供了 settings 校验器拒绝的候选 {missing}；"
                    f"两份必须同步（settings.allowed 需是 contract 候选的超集）。",
                )

    def test_default_settings_keys_have_specs(self):
        for key in contract.DEFAULT_SETTINGS:
            with self.subTest(default_key=key):
                self.assertIsNotNone(
                    mv_settings.get_setting_spec(key, family="mv"),
                    f"contract.DEFAULT_SETTINGS 的 {key!r} 在 settings(mv) 无 SettingSpec")


if __name__ == "__main__":
    unittest.main()
