#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""route 纯函数 + 端到端单测。
    cd skills/ad-video/scripts && python3 -m pytest test_route.py
"""
import json
import os
import tempfile
import unittest

import route as rt


class ClassifyTest(unittest.TestCase):
    def test_classify_product_hero(self):
        self.assertEqual(rt.classify_shot({"frame": "产品 hero shot，包装正面"}), "product_hero")

    def test_classify_emotion(self):
        self.assertEqual(rt.classify_shot({"section": "痛点", "frame": "人物特写·情绪"}), "emotion_closeup")

    def test_classify_demo_handheld(self):
        self.assertEqual(rt.classify_shot({"frame": "手持开箱实拍"}), "demo_handheld")

    def test_classify_endcard(self):
        self.assertEqual(rt.classify_shot({"frame": "end card: logo+slogan+CTA"}), "endcard")

    def test_classify_empty(self):
        self.assertEqual(rt.classify_shot({"frame": "空镜·城市转场"}), "empty_transition")

    def test_classify_default(self):
        self.assertEqual(rt.classify_shot({"frame": "走在路上"}), "general_motion")


class RouteCapabilityTest(unittest.TestCase):
    def test_product_routes_to_subject_lock_backend(self):
        r = rt.choose_route({"frame": "产品 hero shot"})
        self.assertEqual(r["capability"], rt.CAP_SUBJECT_LOCK)
        self.assertIn(rt.CAP_SUBJECT_LOCK, rt.BACKEND_PROFILES[r["primary"]]["caps"])

    def test_prod_asset_forces_subject_lock_even_if_text_generic(self):
        # 文本看不出是产品镜，但 assets 绑定 PROD_ → 仍按产品镜路由主体一致后端
        r = rt.choose_route({"frame": "走两步", "assets": {"PROD_main": True}})
        self.assertEqual(r["shot_type"], "product_hero")
        self.assertEqual(r["capability"], rt.CAP_SUBJECT_LOCK)

    def test_emotion_routes_to_cinematic(self):
        r = rt.choose_route({"frame": "代言人情绪特写"})
        self.assertEqual(r["capability"], rt.CAP_CINEMATIC)
        self.assertIn(rt.CAP_CINEMATIC, rt.BACKEND_PROFILES[r["primary"]]["caps"])

    def test_demo_routes_to_realistic_motion(self):
        r = rt.choose_route({"frame": "手持实拍 demo"})
        self.assertEqual(r["capability"], rt.CAP_REALISTIC_MOTION)
        self.assertIn(rt.CAP_REALISTIC_MOTION, rt.BACKEND_PROFILES[r["primary"]]["caps"])

    def test_general_prefers_default_backend(self):
        r = rt.choose_route({"frame": "痛点叙事镜"}, default_backend="dreamina")
        self.assertEqual(r["primary"], "dreamina")

    def test_fallback_dedup_no_primary(self):
        r = rt.choose_route({"frame": "产品 hero"})
        self.assertNotIn(r["primary"], r["fallback"])
        self.assertEqual(len(r["fallback"]), len(set(r["fallback"])))


class ClipLengthCapTest(unittest.TestCase):
    def test_block_when_too_long(self):
        # 即梦上限 8s
        f = rt.clip_length_cap_check("dreamina", 12.0)
        self.assertIsNotNone(f)
        self.assertEqual(f["severity"], "block")

    def test_seedance_allows_long_clip(self):
        # Seedance 上限 15s，12s 不超
        self.assertIsNone(rt.clip_length_cap_check("seedance", 12.0))

    def test_warn_near_limit(self):
        f = rt.clip_length_cap_check("veo", 7.5)  # veo 8s 上限，7.5 ≥ 90%
        self.assertEqual(f["severity"], "warn")

    def test_none_when_short(self):
        self.assertIsNone(rt.clip_length_cap_check("dreamina", 3.0))

    def test_none_when_no_duration(self):
        self.assertIsNone(rt.clip_length_cap_check("dreamina", 0.0))


class BuildRoutesTest(unittest.TestCase):
    def test_build_routes_and_cap_block(self):
        sb = {"shots": [
            {"shot_id": "S1", "frame": "产品 hero 环绕", "duration": 4.0, "assets": {"PROD_main": True}},
            # 痛点叙事镜 12s，default=dreamina 上限 8s → block
            {"shot_id": "S2", "frame": "痛点叙事", "duration": 12.0},
        ]}
        routes, summary = rt.build_routes(sb, default_backend="dreamina")
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0]["clip"], "镜头01")
        self.assertEqual(routes[0]["capability"], rt.CAP_SUBJECT_LOCK)
        self.assertEqual(summary["block"], 1)
        self.assertTrue(any(f["code"] == "clip_too_long_for_backend"
                            for f in routes[1]["findings"]))

    def test_build_routes_no_block_with_capable_backend(self):
        sb = {"shots": [{"shot_id": "S1", "frame": "产品 hero", "duration": 12.0,
                         "assets": {"PROD_main": True}}]}
        routes, summary = rt.build_routes(sb)
        # 产品镜路由到 Seedance(15s)/可灵(10s) 系——primary 应能容 12s 或仅 warn，不 block
        self.assertEqual(summary["block"], 0)


class EndToEndTest(unittest.TestCase):
    def _project(self, td, storyboard, settings=None):
        os.makedirs(os.path.join(td, "脚本"), exist_ok=True)
        with open(os.path.join(td, "脚本", "storyboard.json"), "w", encoding="utf-8") as f:
            json.dump(storyboard, f, ensure_ascii=False)
        if settings is not None:
            with open(os.path.join(td, "_设置.md"), "w", encoding="utf-8") as f:
                f.write(settings)

    def test_run_writes_routes_json(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td, {"shots": [{"shot_id": "S1", "frame": "产品 hero", "duration": 4.0}]})
            payload = rt.run(td)
            out = os.path.join(td, "出视频", "分镜", "prompt", "video_model_routes.json")
            self.assertTrue(os.path.isfile(out))
            self.assertEqual(payload["kind"], rt.VIDEO_MODEL_ROUTES_KIND)
            with open(out, encoding="utf-8") as f:
                disk = json.load(f)
            self.assertEqual(disk["routes"][0]["clip"], "镜头01")

    def test_main_exit_code_block_on_too_long(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td, {"shots": [{"shot_id": "S1", "frame": "痛点叙事", "duration": 20.0}]},
                          settings="生视频模型：即梦\n")
            with self.assertRaises(SystemExit) as cm:
                rt.main([td])
            self.assertEqual(cm.exception.code, 1)

    def test_main_exit_code_pass(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td, {"shots": [{"shot_id": "S1", "frame": "产品 hero", "duration": 4.0}]})
            with self.assertRaises(SystemExit) as cm:
                rt.main([td])
            self.assertEqual(cm.exception.code, 0)

    def test_settings_default_backend(self):
        with tempfile.TemporaryDirectory() as td:
            self._project(td, {"shots": [{"shot_id": "S1", "frame": "痛点叙事", "duration": 3.0}]},
                          settings="生视频模型：Seedance\n")
            payload = rt.run(td)
            self.assertEqual(payload["default_backend"], "seedance")
            self.assertEqual(payload["routes"][0]["primary"], "seedance")


class ThreeAxisTest(unittest.TestCase):
    def test_quality_tier_high_for_product_and_brand_shots(self):
        # 产品 hero 镜 primary=seedance（支持档位）→ high
        self.assertEqual(rt.quality_tier_for("product_hero", "seedance"), "high")
        self.assertEqual(rt.quality_tier_for("endcard", "seedance"), "high")
        # 普通镜 → fast
        self.assertEqual(rt.quality_tier_for("painpoint_narrative", "seedance"), "fast")
        # 无档位后端（veo）→ n/a
        self.assertEqual(rt.quality_tier_for("product_hero", "veo"), "n/a")

    def test_route_entry_carries_quality_tier(self):
        routes, _ = rt.build_routes({"shots": [{"shot_id": "S1", "frame": "产品 hero shot", "duration": 4.0}]})
        # 产品镜路由到主体一致后端（seedance/kling）；seedance 支持档位→high，kling 不支持→n/a
        self.assertIn(routes[0]["quality_tier"], ("high", "n/a"))
        self.assertIn("motion_reference", routes[0])

    def test_motion_reference_applicable_for_demo_on_motion_ref_backend(self):
        plan = rt.motion_reference_plan("demo_handheld", "seedance")
        self.assertTrue(plan["applicable"])
        self.assertFalse(rt.motion_reference_plan("empty_transition", "seedance")["applicable"])
        self.assertFalse(rt.motion_reference_plan("demo_handheld", "veo")["applicable"])  # veo 无 motion_ref

    def test_multishot_groups_consecutive_demo_on_seedance(self):
        # 三条连续短 demo 镜（各 3s，3+3+3=9 ≤ seedance 15s）→ 成一组；逐镜不被合并
        routes = [
            {"clip": "镜头01", "shot_type": "demo_handheld", "primary": "seedance", "duration": 3.0},
            {"clip": "镜头02", "shot_type": "demo_handheld", "primary": "seedance", "duration": 3.0},
            {"clip": "镜头03", "shot_type": "demo_handheld", "primary": "seedance", "duration": 3.0},
        ]
        groups = rt.annotate_multishot_groups(routes)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["members"], ["镜头01", "镜头02", "镜头03"])
        self.assertEqual(groups[0]["approx_seconds"], 9.0)
        self.assertEqual(routes[0]["multishot_candidate"]["group_id"], "MSG_01")

    def test_multishot_capped_by_duration(self):
        # 两条 10s demo：10+10=20 > 15 → 物理上一次出不下 → 不成组
        routes = [
            {"clip": "镜头01", "shot_type": "demo_handheld", "primary": "seedance", "duration": 10.0},
            {"clip": "镜头02", "shot_type": "demo_handheld", "primary": "seedance", "duration": 10.0},
        ]
        self.assertEqual(rt.annotate_multishot_groups(routes), [])

    def test_no_multishot_on_non_multishot_backend(self):
        # veo 无 multishot_native → 即便连续同型也不标注（判定走能力）
        routes = [
            {"clip": "镜头01", "shot_type": "demo_handheld", "primary": "veo", "duration": 3.0},
            {"clip": "镜头02", "shot_type": "demo_handheld", "primary": "veo", "duration": 3.0},
        ]
        self.assertEqual(rt.annotate_multishot_groups(routes), [])


if __name__ == "__main__":
    unittest.main()
