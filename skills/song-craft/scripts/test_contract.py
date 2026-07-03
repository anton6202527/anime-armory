#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""song-craft contract tests.

Can run without pytest:
    python3 skills/song-craft/scripts/test_contract.py
"""
import importlib.util
from pathlib import Path
import unittest


def load_local_contract():
    path = Path(__file__).with_name("contract.py")
    spec = importlib.util.spec_from_file_location("song_craft_contract_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


contract = load_local_contract()


class SongContractTest(unittest.TestCase):
    def test_choice_points_include_generation_controls(self):
        points = contract.choice_points()
        for key in ("歌曲用途", "目标时长", "语言", "BPM/速度", "调性", "生成版数", "挑版策略", "AI音频使用披露"):
            self.assertIn(key, points)
        self.assertIn("ACE-Step", points["作曲后端"])

    def test_stage_table_has_take_loop(self):
        keys = [stage["key"] for stage in contract.stage_table()]
        self.assertEqual(keys[:3], ["setup", "lyrics", "compose_plan"])
        self.assertIn("takes", keys)
        self.assertIn("selection", keys)

    def test_settings_markdown_lists_choices(self):
        md = contract.settings_markdown("测试歌", {"生成版数": "6"})
        self.assertIn("# _设置 · 测试歌", md)
        self.assertIn("- 生成版数: 6", md)
        self.assertIn("## 记录", md)


if __name__ == "__main__":
    unittest.main()
