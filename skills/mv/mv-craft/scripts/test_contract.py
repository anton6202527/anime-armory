#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv-craft contract tests.

Can run without pytest:
    python3 skills/mv/mv-craft/scripts/test_contract.py
"""
import importlib.util
from pathlib import Path
import unittest


def load_local_contract():
    path = Path(__file__).with_name("contract.py")
    spec = importlib.util.spec_from_file_location("mv_craft_contract_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


contract = load_local_contract()


class MvContractTest(unittest.TestCase):
    def test_choice_points_include_mv_controls(self):
        points = contract.choice_points()
        for key in (
            "MV用途",
            "歌曲输入时序",
            "MV视觉风格",
            "MV规划粒度",
            "卡点策略",
            "生图AI",
            "生图模型",
            "生图渠道",
            "MV一致性增强",
            "生视频模型",
            "生视频渠道",
            "出视频规格",
            "AI视觉使用披露",
        ):
            self.assertIn(key, points)
        self.assertIn("Kling 3.0", points["生视频模型"])
        self.assertIn("Runway Gen-4.5", points["生视频模型"])
        self.assertIn("Seedance 2.5", points["生视频模型"])
        self.assertIn("Gemini Omni Flash Preview", points["生视频模型"])
        self.assertIn("Luma Ray3.2", points["生视频模型"])
        self.assertIn("Seedance 2.0", contract.MV_LEGACY_VIDEO_MODELS)
        self.assertNotIn("Sora 2", points["生视频模型"])
        self.assertIn("Sora 2", contract.MV_LEGACY_VIDEO_MODELS)
        self.assertIn("即梦/Dreamina", points["生视频渠道"])
        self.assertIn("+LoRA", points["MV一致性增强"])
        self.assertIn("后配歌曲", points["歌曲输入时序"])

    def test_profiles(self):
        self.assertEqual(contract.video_spec_profile("预算一般")["resolution"], "720p")
        self.assertEqual(contract.plan_granularity_profile("标准")["chorus_bars"], 1)
        self.assertEqual(contract.normalize_video_model("Runway"), "Runway Gen-4.5")
        self.assertEqual(contract.normalize_video_model("Seedance"), "Seedance 2.0")
        self.assertEqual(contract.normalize_video_model("Omni"), "Gemini Omni Flash Preview")
        self.assertEqual(contract.normalize_video_channel("dreamina"), "Dreamina")
        self.assertTrue(contract.video_model_profile("Kling")["multi_shot"])
        self.assertEqual(contract.legacy_video_route("即梦"), ("Seedance 2.0", "即梦"))
        self.assertEqual(contract.legacy_video_route("可灵"), ("Kling 3.0", "可灵"))
        self.assertEqual(contract.legacy_video_route("omni"), ("Gemini Omni Flash Preview", "Google Gemini API"))

    def test_current_default_and_plan_setting_digest(self):
        self.assertEqual(contract.DEFAULT_SETTINGS["生视频模型"], "Seedance 2.5")
        base = {key: contract.DEFAULT_SETTINGS[key] for key in contract.MV_PLAN_SETTING_KEYS}
        first = contract.plan_settings_digest(base)
        self.assertEqual(first, contract.plan_settings_digest(dict(reversed(list(base.items())))))
        self.assertEqual(first, contract.plan_settings_digest({**base, "发行目标平台": "YouTube"}))
        self.assertNotEqual(first, contract.plan_settings_digest({**base, "合成画幅": "9:16"}))

    def test_workflow_stage_order_by_song_timing(self):
        first = [s["key"] for s in contract.workflow_stage_table("先传音乐")]
        later = [s["key"] for s in contract.workflow_stage_table("后配歌曲")]
        self.assertLess(first.index("song_ingest"), first.index("beat"))
        self.assertLess(first.index("beat"), first.index("lyric_sync"))
        self.assertLess(first.index("lyric_sync"), first.index("script"))
        self.assertLess(first.index("plan"), first.index("semantic_plan"))
        self.assertLess(first.index("semantic_plan"), first.index("pacing_check"))
        self.assertLess(first.index("pacing_check"), first.index("image"))
        self.assertLess(first.index("image"), first.index("picture_lock"))
        self.assertLess(first.index("picture_lock"), first.index("video_jobs"))
        self.assertLess(later.index("script"), later.index("song_ingest"))
        self.assertLess(later.index("song_ingest"), later.index("beat"))
        self.assertLess(later.index("beat"), later.index("script_review"))
        self.assertLess(later.index("script_review"), later.index("plan"))
        self.assertLess(later.index("compose"), later.index("disclosure"))
        self.assertLess(later.index("disclosure"), later.index("provenance"))
        self.assertLess(later.index("provenance"), later.index("review"))
        self.assertLess(later.index("review"), later.index("handoff"))
        instrumental = [s["key"] for s in contract.workflow_stage_table("先传音乐", "无字幕", "关闭")]
        self.assertNotIn("lyric_sync", instrumental)
        self.assertEqual(contract.validate_stage_table(), [])

    def test_runtime_fields_are_derived_from_settings(self):
        state = contract.runtime_state_from_settings({
            "MV用途": "投放版", "歌曲输入时序": "后配歌曲",
            "合成画幅": "9:16", "发行目标平台": "抖音",
        })
        self.assertFalse(state["is_demo"])
        self.assertEqual(state["song_timing"], "后配歌曲")
        self.assertEqual(state["aspect"], "9:16")
        self.assertEqual(state["publish_target"], "抖音")
        legacy = contract.runtime_state_from_settings({"生视频AI": "可灵"})
        self.assertEqual(legacy["video_model"], "Kling 3.0")
        self.assertEqual(legacy["video_channel"], "可灵")

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
        self.assertEqual(contract.DEFAULT_SETTINGS["MV一致性增强"], "共享定妆+锚点")


if __name__ == "__main__":
    unittest.main()
