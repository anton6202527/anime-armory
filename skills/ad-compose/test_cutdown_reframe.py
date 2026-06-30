#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cutdown + reframe + deliver 纯函数单测（plan/filter 构造逻辑直测，不依赖 ffmpeg）。
    cd skills/ad-compose && python -m pytest test_cutdown_reframe.py
    （或 python3 test_cutdown_reframe.py）
"""
import unittest

import cutdown
import deliver
import reframe


class ReframeTest(unittest.TestCase):
    def test_aspect_value(self):
        self.assertAlmostEqual(reframe.aspect_value("16:9"), 16 / 9)
        self.assertAlmostEqual(reframe.aspect_value("1920x1080"), 16 / 9)
        self.assertAlmostEqual(reframe.aspect_value("9:16"), 9 / 16)

    def test_out_resolution(self):
        self.assertEqual(reframe.out_resolution("9:16", 1920), (1080, 1920))
        self.assertEqual(reframe.out_resolution("1:1", 1920), (1920, 1920))
        self.assertEqual(reframe.out_resolution("16:9", 1920), (1920, 1080))

    def test_reframe_filter_crop(self):
        vf = reframe.reframe_filter("1920x1080", "9:16", "crop", 1920)
        self.assertIn("crop=1080:1920", vf)
        self.assertIn("force_original_aspect_ratio=increase", vf)
        # 无焦点 → 中心裁切，crop 无显式 x:y
        self.assertNotIn("max(0", vf)

    def test_reframe_filter_pad_resolution(self):
        # pad 模式：滤镜含目标分辨率的 pad，且 decrease（保全画加边）
        vf = reframe.reframe_filter("1920x1080", "9:16", "pad", 1920)
        self.assertIn("pad=1080:1920", vf)
        self.assertIn("scale=1080:1920", vf)
        self.assertIn("decrease", vf)
        # 1:1 pad 分辨率
        vf2 = reframe.reframe_filter("1920x1080", "1:1", "pad", 1920)
        self.assertIn("pad=1920:1920", vf2)

    def test_reframe_filter_crop_focal_point(self):
        vf = reframe.reframe_filter("1920x1080", "9:16", "crop", 1920,
                                    crop_x=0.4, crop_y=0.45)
        self.assertIn("crop=1080:1920:", vf)
        # 焦点裁切带夹边表达式
        self.assertIn("0.4000", vf)
        self.assertIn("0.4500", vf)
        self.assertIn("max(0", vf)

    def test_reframe_focal_clamped(self):
        # 越界焦点被夹进 [0,1]
        vf = reframe.reframe_filter("1920x1080", "9:16", "crop", 1920, crop_x=2.0)
        self.assertIn("1.0000", vf)


class CutdownTest(unittest.TestCase):
    def _shots(self):
        return [
            {"shot_id": "S1", "section": "钩子", "duration": 3},
            {"shot_id": "S2", "section": "痛点", "duration": 5},
            {"shot_id": "S3", "section": "情境", "duration": 4},
            {"shot_id": "S4", "section": "产品", "duration": 6},
            {"shot_id": "S5", "section": "证据", "duration": 4},
            {"shot_id": "S6", "section": "CTA", "duration": 3},
        ]

    def _dmap(self, shots):
        return {s["shot_id"]: float(s["duration"]) for s in shots}

    def test_priority_keeps_skeleton(self):
        shots = self._shots()
        kept, total, _ = cutdown.plan_cutdown(shots, 15, duration_map=self._dmap(shots))
        ids = set(s["shot_id"] for s in kept)
        self.assertTrue({"S1", "S4", "S6"} <= ids)

    def test_order_preserved(self):
        shots = self._shots()
        kept, _, _ = cutdown.plan_cutdown(shots, 15, duration_map=self._dmap(shots))
        ids = [s["shot_id"] for s in kept]
        self.assertEqual(ids, sorted(ids, key=lambda x: int(x[1:])))

    def test_explicit_priority_override(self):
        shots = [{"shot_id": "A", "duration": 3, "cutdown_priority": 99},
                 {"shot_id": "B", "duration": 3, "cutdown_priority": 10}]
        kept, _, _ = cutdown.plan_cutdown(shots, 3, duration_map=self._dmap(shots))
        self.assertIn("A", [s["shot_id"] for s in kept])

    def test_must_keeps_seeded_before_optionals(self):
        # 必保镜先占预算：S1(钩子3)+S4(产品6)+S6(CTA3)=12s。目标12s时可选镜应几乎进不来，
        # 且总时长不因可选镜先吃预算而把必保镜挤掉/溢出。
        shots = self._shots()
        kept, total, findings = cutdown.plan_cutdown(shots, 12, duration_map=self._dmap(shots))
        ids = set(s["shot_id"] for s in kept)
        self.assertTrue({"S1", "S4", "S6"} <= ids)
        self.assertGreaterEqual(total, 12 - 0.6)

    def test_overflow_finding_when_mustkeeps_exceed_target(self):
        # 必保镜合计 12s，目标 6s → 必保镜本身溢出，应出 overflow 提示但仍保留全部必保镜
        shots = self._shots()
        kept, total, findings = cutdown.plan_cutdown(shots, 6, duration_map=self._dmap(shots))
        ids = set(s["shot_id"] for s in kept)
        self.assertTrue({"S1", "S4", "S6"} <= ids)
        kinds = [f["kind"] for f in findings]
        self.assertIn("cutdown_overflow", kinds)
        self.assertGreater(total, 6)

    def test_underflow_finding(self):
        # 只有一个 3s 必保镜，目标 30s → underflow
        shots = [{"shot_id": "S1", "section": "钩子", "duration": 3}]
        kept, total, findings = cutdown.plan_cutdown(shots, 30, duration_map=self._dmap(shots))
        kinds = [f["kind"] for f in findings]
        self.assertIn("cutdown_underflow", kinds)

    def test_missing_duration_blocks_no_false_pass(self):
        # P0 假通过：storyboard 有镜但镜头时长.json 缺 / 为 0 → block，拒绝出计划（不算 0.00s 通过）
        shots = [{"shot_id": "S1", "section": "钩子"},   # 无 duration
                 {"shot_id": "S6", "section": "CTA"}]
        kept, total, findings = cutdown.plan_cutdown(shots, 15, duration_map={})
        self.assertEqual(kept, [])
        self.assertEqual(total, 0.0)
        kinds = [f["kind"] for f in findings]
        self.assertIn("cutdown_missing_duration", kinds)
        self.assertTrue(any(f["severity"] == "block" for f in findings))

    def test_zero_duration_in_storyboard_blocks(self):
        # storyboard duration=0 也是未解析 → block（不是误算 0s 通过）
        shots = [{"shot_id": "S1", "section": "钩子", "duration": 0}]
        kept, total, findings = cutdown.plan_cutdown(shots, 15, duration_map={})
        self.assertEqual(kept, [])
        self.assertTrue(any(f["severity"] == "block" for f in findings))

    def test_authoritative_duration_overrides_storyboard(self):
        # 镜头时长.json 是权威源：storyboard 里写 0，时长清单里有实测 → 用实测，不 block
        shots = [{"shot_id": "S1", "section": "钩子", "duration": 0},
                 {"shot_id": "S6", "section": "CTA", "duration": 0}]
        dmap = {"S1": 3.0, "S6": 3.0}
        kept, total, findings = cutdown.plan_cutdown(shots, 6, duration_map=dmap)
        self.assertEqual(total, 6.0)
        self.assertFalse(any(f["severity"] == "block" for f in findings))

    def test_optional_missing_duration_skipped_not_zero(self):
        # 可选镜缺时长 → 跳过 + warn，而非误算 0 进 plan
        shots = [{"shot_id": "S1", "section": "钩子", "duration": 3},
                 {"shot_id": "S2", "section": "痛点"},  # 可选，缺时长
                 {"shot_id": "S6", "section": "CTA", "duration": 3}]
        dmap = {"S1": 3.0, "S6": 3.0}
        kept, total, findings = cutdown.plan_cutdown(shots, 15, duration_map=dmap)
        ids = set(s["shot_id"] for s in kept)
        self.assertNotIn("S2", ids)
        self.assertIn("cutdown_optional_no_duration", [f["kind"] for f in findings])

    def test_parse_seconds(self):
        self.assertEqual(cutdown.parse_seconds("6s"), 6.0)
        self.assertEqual(cutdown.parse_seconds("1:00"), 60.0)
        self.assertEqual(cutdown.parse_seconds("1:30"), 90.0)

    def test_parse_seconds_spaced_uppercase(self):
        # cut_id 来自交付矩阵时长，可能含空格/大写 S
        self.assertEqual(cutdown.parse_seconds(" 15 S "), 15.0)
        self.assertEqual(cutdown.parse_seconds("6S"), 6.0)
        self.assertEqual(cutdown.parse_seconds(" 1:30 "), 90.0)

    def test_safe_label_spaced_uppercase(self):
        # 文件名安全化：去空格 + 小写 + : → x（保留 s 后缀，与 成片_15s.mp4 命名一致）
        self.assertEqual(cutdown.safe_label(" 15 S "), "15s")
        self.assertEqual(cutdown.safe_label("6S"), "6s")
        self.assertEqual(cutdown.safe_label("1:30"), "1x30")

    def test_duration_map_from_finalize(self):
        fin = {"shots": [{"shot_id": "S1", "duration": 3.0},
                         {"shot_id": "S2", "duration": 0},  # 0 不入 map
                         {"shot_id": "S3", "duration": 4.5}]}
        dmap = cutdown.duration_map_from_finalize(fin)
        self.assertEqual(dmap, {"S1": 3.0, "S3": 4.5})


class DeliverTest(unittest.TestCase):
    def test_parse_deliverables(self):
        md = """# test

## 交付版本矩阵

| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |
|---|---|---|---|---|---|---|
| 主片 | 30s | 16:9 | master | 平台默认 | ⬜ | |
| cutdown 15s | 15s | 16:9 | cutdown | 平台默认 | ⬜ | |
"""
        rows = deliver.parse_deliverables(md)
        self.assertEqual(len(rows), 2)
        self.assertEqual(deliver.expected_relpath(rows[0]), "合成/成片_主片.mp4")
        self.assertEqual(deliver.expected_relpath(rows[1]), "合成/cutdown/成片_15s.mp4")

    def test_build_plan_has_commands(self):
        md = """## 交付版本矩阵
| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |
|---|---|---|---|---|---|---|
| 主片 | 30s | 16:9 | master | 平台默认 | ⬜ | |
"""
        plan = deliver.build_plan("/tmp/ad-test", md)
        self.assertEqual(plan["deliverables"][0]["deliverable_id"], "master")
        self.assertIn("compose.sh", plan["deliverables"][0]["command"])

    def test_cutdown_command_renders(self):
        md = """## 交付版本矩阵
| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |
|---|---|---|---|---|---|---|
| cutdown 15s | 15s | 16:9 | cutdown | 平台默认 | ⬜ | |
| 竖版 | 30s | 9:16 | reframe | 平台默认 | ⬜ | |
"""
        plan = deliver.build_plan("/tmp/ad-test", md)
        cut = next(d for d in plan["deliverables"] if d["kind"] == "cutdown")
        ref = next(d for d in plan["deliverables"] if d["kind"] == "reframe")
        # cutdown / reframe 命令现在真正 --render 出 MP4，不再是 "# 手工..." 注释
        self.assertIn("--render", cut["command"])
        self.assertIn("--render", ref["command"])
        self.assertNotIn("#", ref["command"])


if __name__ == "__main__":
    unittest.main()
