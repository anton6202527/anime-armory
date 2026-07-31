#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d 交付矩阵纯逻辑单测（cutdown 选镜 / reframe 几何 / deliver 规格派生）。
不依赖 ffmpeg —— 只测纯计算部分。

    cd skills/n2d/n2d-compose && python -m pytest test_delivery_matrix.py
    （或 python3 test_delivery_matrix.py）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cutdown
import deliver
import reframe


# ── reframe 几何 ──────────────────────────────────────────────────────────
class ReframeTest(unittest.TestCase):
    def test_aspect_value(self):
        self.assertAlmostEqual(reframe.aspect_value("16:9"), 16 / 9)
        self.assertAlmostEqual(reframe.aspect_value("1080x1920"), 9 / 16)
        self.assertAlmostEqual(reframe.aspect_value("9:16"), 9 / 16)

    def test_out_resolution(self):
        self.assertEqual(reframe.out_resolution("16:9", 1920), (1920, 1080))
        self.assertEqual(reframe.out_resolution("1:1", 1920), (1920, 1920))
        self.assertEqual(reframe.out_resolution("9:16", 1920), (1080, 1920))

    def test_crop_center(self):
        vf = reframe.reframe_filter("1080x1920", "16:9", "crop", 1920)
        self.assertIn("crop=1920:1080", vf)
        self.assertIn("force_original_aspect_ratio=increase", vf)
        self.assertNotIn("max(0", vf)  # 无焦点=中心裁切

    def test_pad_keeps_full_frame(self):
        # 竖转横首选 pad：保全画加边
        vf = reframe.reframe_filter("1080x1920", "16:9", "pad", 1920)
        self.assertIn("pad=1920:1080", vf)
        self.assertIn("decrease", vf)

    def test_crop_focal_point_clamped(self):
        vf = reframe.reframe_filter("1080x1920", "1:1", "crop", 1920,
                                    crop_x=0.5, crop_y=0.42)
        self.assertIn("crop=1920:1920:", vf)
        self.assertIn("0.4200", vf)
        self.assertIn("max(0", vf)
        # 越界焦点夹进 [0,1]
        vf2 = reframe.reframe_filter("1080x1920", "1:1", "crop", 1920, crop_y=-1.0)
        self.assertIn("0.0000", vf2)


# ── cutdown 选镜（n2d 漫剧语境：保钩子/爽点/反转/集尾） ──────────────────────
class CutdownPriorityTest(unittest.TestCase):
    def test_rhythm_drives_must_keep(self):
        clips = [
            {"id": "C1", "rhythm": "钩子开场", "duration": 3},
            {"id": "C2", "rhythm": "铺垫日常", "duration": 5},
            {"id": "C3", "rhythm": "细节对白", "duration": 4},
            {"id": "C4", "rhythm": "爽点爆发", "duration": 5},
            {"id": "C5", "rhythm": "留白定格", "duration": 3},
            {"id": "C6", "rhythm": "集尾断点", "duration": 3},
        ]
        dmap = {c["id"]: float(c["duration"]) for c in clips}
        kept, total, _ = cutdown.plan_cutdown(clips, 15, duration_map=dmap)
        ids = set(c["id"] for c in kept)
        # 骨架：钩子 C1 / 爽点 C4 / 集尾 cliffhanger C6 必保
        self.assertTrue({"C1", "C4", "C6"} <= ids)

    def test_cliffhanger_via_hook_field(self):
        # 钩子字段 end 也判 cliffhanger 骨架（无 rhythm 时）
        clips = [{"id": "C1", "钩子": "hook", "duration": 3},
                 {"id": "C2", "钩子": "", "duration": 4},
                 {"id": "C3", "钩子": "end", "duration": 3}]
        dmap = {c["id"]: float(c["duration"]) for c in clips}
        kept, _, _ = cutdown.plan_cutdown(clips, 6, duration_map=dmap)
        ids = set(c["id"] for c in kept)
        self.assertTrue({"C1", "C3"} <= ids)

    def test_order_preserved(self):
        clips = [{"id": f"C{i}", "rhythm": r, "duration": 3}
                 for i, r in enumerate(["钩子", "铺垫", "爽点", "细节", "集尾"], 1)]
        dmap = {c["id"]: 3.0 for c in clips}
        kept, _, _ = cutdown.plan_cutdown(clips, 15, duration_map=dmap)
        ids = [c["id"] for c in kept]
        self.assertEqual(ids, sorted(ids, key=lambda x: int(x[1:])))

    def test_explicit_priority_override(self):
        clips = [{"id": "A", "duration": 3, "cutdown_priority": 99},
                 {"id": "B", "duration": 3, "cutdown_priority": 10}]
        kept, _, _ = cutdown.plan_cutdown(clips, 3, duration_map={"A": 3.0, "B": 3.0})
        self.assertIn("A", [c["id"] for c in kept])

    def test_overflow_keeps_skeleton(self):
        # 必保镜合计超目标 → overflow 提示但仍保留全部必保镜
        clips = [{"id": "C1", "rhythm": "钩子", "duration": 5},
                 {"id": "C2", "rhythm": "爽点", "duration": 5},
                 {"id": "C3", "rhythm": "集尾", "duration": 5}]
        dmap = {c["id"]: 5.0 for c in clips}
        kept, total, findings = cutdown.plan_cutdown(clips, 6, duration_map=dmap)
        self.assertTrue({"C1", "C2", "C3"} <= set(c["id"] for c in kept))
        self.assertIn("cutdown_overflow", [f["kind"] for f in findings])
        self.assertGreater(total, 6)

    def test_underflow(self):
        clips = [{"id": "C1", "rhythm": "钩子", "duration": 3}]
        kept, total, findings = cutdown.plan_cutdown(clips, 30, duration_map={"C1": 3.0})
        self.assertIn("cutdown_underflow", [f["kind"] for f in findings])


# ── cutdown 时长源（n2d 镜头时长.json 是字典 schema） ───────────────────────
class CutdownDurationSourceTest(unittest.TestCase):
    def test_duration_map_dict_schema(self):
        # n2d finalize_storyboard 写的是 {镜头键: 秒} 字典
        fin = {"EP01_CLIP01": 3.0, "EP01_CLIP02": 0, "EP01_CLIP03": 4.5}
        dmap = cutdown.duration_map_from_finalize(fin)
        self.assertEqual(dmap, {"EP01_CLIP01": 3.0, "EP01_CLIP03": 4.5})  # 0 不入

    def test_duration_map_list_schema_compat(self):
        # 兼容广告式列表 schema
        fin = {"shots": [{"shot_id": "S1", "duration": 3.0},
                         {"shot_id": "S2", "duration": 0}]}
        dmap = cutdown.duration_map_from_finalize(fin)
        self.assertEqual(dmap, {"S1": 3.0})

    def test_missing_must_keep_duration_blocks(self):
        # P0 假通过防护：必保镜在 镜头时长.json 缺/为 0 → block，拒绝出计划
        clips = [{"id": "C1", "rhythm": "钩子"}, {"id": "C2", "rhythm": "集尾"}]
        kept, total, findings = cutdown.plan_cutdown(clips, 15, duration_map={})
        self.assertEqual(kept, [])
        self.assertEqual(total, 0.0)
        self.assertTrue(any(f["severity"] == "block" for f in findings))
        self.assertIn("cutdown_missing_duration", [f["kind"] for f in findings])

    def test_authoritative_overrides_storyboard_zero(self):
        # storyboard duration=0，镜头时长.json 有实测 → 用实测，不 block
        clips = [{"id": "C1", "rhythm": "钩子", "duration": 0},
                 {"id": "C2", "rhythm": "集尾", "duration": 0}]
        dmap = {"C1": 3.0, "C2": 3.0}
        kept, total, findings = cutdown.plan_cutdown(clips, 6, duration_map=dmap)
        self.assertEqual(total, 6.0)
        self.assertFalse(any(f["severity"] == "block" for f in findings))

    def test_optional_missing_duration_skipped(self):
        clips = [{"id": "C1", "rhythm": "钩子", "duration": 3},
                 {"id": "C2", "rhythm": "铺垫"},  # 可选缺时长
                 {"id": "C3", "rhythm": "集尾", "duration": 3}]
        dmap = {"C1": 3.0, "C3": 3.0}
        kept, _, findings = cutdown.plan_cutdown(clips, 15, duration_map=dmap)
        self.assertNotIn("C2", set(c["id"] for c in kept))
        self.assertIn("cutdown_optional_no_duration", [f["kind"] for f in findings])

    def test_shot_id_prefers_镜头_then_id(self):
        self.assertEqual(cutdown.shot_id({"镜头": "镜头1", "id": "C1"}), "镜头1")
        self.assertEqual(cutdown.shot_id({"id": "C1"}), "C1")

    def test_parse_seconds(self):
        self.assertEqual(cutdown.parse_seconds("15s"), 15.0)
        self.assertEqual(cutdown.parse_seconds(" 30 S "), 30.0)
        self.assertEqual(cutdown.parse_seconds("1:30"), 90.0)

    def test_safe_label(self):
        self.assertEqual(cutdown.safe_label(" 15 S "), "15s")
        self.assertEqual(cutdown.safe_label("16:9"), "16x9")


# ── deliver 规格派生矩阵 ─────────────────────────────────────────────────────
class DeliverMatrixTest(unittest.TestCase):
    def test_parse_setting(self):
        md = "## 设置\n- 目标平台: 抖音\n画幅：9:16\n交付时长: 30s、15s\n"
        self.assertEqual(deliver.parse_setting(md, "目标平台"), "抖音")
        self.assertEqual(deliver.parse_setting(md, "画幅"), "9:16")
        self.assertEqual(deliver.parse_setting(md, "交付时长"), "30s、15s")
        self.assertIsNone(deliver.parse_setting(md, "不存在键"))

    def test_loudness_key_for_platform(self):
        self.assertEqual(deliver.loudness_key_for_platform("抖音"), "tiktok")
        self.assertEqual(deliver.loudness_key_for_platform("B站"), "bilibili")
        self.assertEqual(deliver.loudness_key_for_platform("YouTube"), "youtube")
        self.assertEqual(deliver.loudness_key_for_platform("广电电视"), "broadcast")
        self.assertEqual(deliver.loudness_key_for_platform("红果"), "default")
        self.assertEqual(deliver.loudness_key_for_platform(None), "default")

    def test_aspects_native_first(self):
        # B站推荐 16:9+9:16，母带画幅 9:16 应置首（原生不重出）
        aspects, native = deliver.aspects_for("B站", "9:16")
        self.assertEqual(native, "9:16")
        self.assertEqual(aspects[0], "9:16")
        self.assertIn("16:9", aspects)

    def test_aspects_multi(self):
        aspects, native = deliver.aspects_for("抖音", "多比例")
        self.assertEqual(set(aspects), set(deliver.ALL_ASPECTS))

    def test_aspects_default_single(self):
        # 平台未定 + 画幅 9:16 → 仅母带比例
        aspects, native = deliver.aspects_for(None, "9:16")
        self.assertEqual(aspects, ["9:16"])

    def test_durations_default_and_explicit(self):
        self.assertEqual(deliver.durations_for(None), ["30s", "15s"])
        self.assertEqual(deliver.durations_for("正片、15s"), ["15s"])
        self.assertEqual(deliver.durations_for("30s,15s,6s"), ["30s", "15s", "6s"])

    def test_build_matrix_expands_cutdown_and_reframe(self):
        # 横屏母带（16:9）+ 多比例 → cutdown(原生比例) + reframe(9:16,1:1)
        m = deliver.build_matrix("/tmp/n2d-x", "第1集", "跨平台", "16:9", "30s,15s",
                                 aspects_override=None, durations_override=None)
        self.assertEqual(m["native_aspect"], "16:9")
        kinds = [d["kind"] for d in m["deliverables"]]
        self.assertEqual(kinds.count("cutdown"), 2)
        # reframe 只对非原生比例（9:16, 1:1）
        ref_aspects = set(d["aspect"] for d in m["deliverables"] if d["kind"] == "reframe")
        self.assertEqual(ref_aspects, {"9:16", "1:1"})
        self.assertNotIn("16:9", ref_aspects)
        # cutdown 用母带原生比例
        cut_aspects = set(d["aspect"] for d in m["deliverables"] if d["kind"] == "cutdown")
        self.assertEqual(cut_aspects, {"16:9"})

    def test_build_matrix_loudness_from_platform(self):
        m = deliver.build_matrix("/tmp/n2d-x", "第1集", "抖音", "9:16", None)
        self.assertEqual(m["loudness_key"], "tiktok")
        self.assertEqual(m["target_lufs"], -14.0)  # tiktok 目标

    def test_build_matrix_override(self):
        m = deliver.build_matrix("/tmp/n2d-x", "第1集", "抖音", "9:16", None,
                                 aspects_override=["9:16", "1:1"],
                                 durations_override=["15s"])
        self.assertEqual(m["native_aspect"], "9:16")
        self.assertEqual(m["durations"], ["15s"])
        self.assertEqual(set(d["aspect"] for d in m["deliverables"] if d["kind"] == "reframe"),
                         {"1:1"})

    def test_master_missing_is_none(self):
        m = deliver.build_matrix("/tmp/n2d-nonexistent-xyz", "第99集", "抖音", "9:16", None)
        self.assertIsNone(m["master"])


if __name__ == "__main__":
    unittest.main()


class TestPlatformEncoding(unittest.TestCase):
    def test_encoding_for_platform(self):
        self.assertEqual(deliver.encoding_for_platform("抖音")["profile"], "vertical_short")
        self.assertEqual(deliver.encoding_for_platform("B站")["profile"], "bilibili")
        self.assertEqual(deliver.encoding_for_platform("YouTube")["profile"], "youtube")
        self.assertEqual(deliver.encoding_for_platform("未定")["profile"], "default")
        self.assertEqual(deliver.encoding_for_platform(None)["profile"], "default")
        spec = deliver.encoding_for_platform("红果")
        self.assertEqual(spec["video_codec"], "h264")
        self.assertTrue(spec["video_bitrate"])

    def test_matrix_carries_encoding(self):
        m = deliver.build_matrix("/tmp/不存在的作品根", "第1集", "抖音", "9:16", None)
        self.assertEqual(m["encoding"]["profile"], "vertical_short")

    def test_reframe_encoding_args(self):
        import reframe
        args = reframe._encoding_args({"video_bitrate": "8M", "maxrate": "12M"})
        self.assertEqual(args, ["-b:v", "8M", "-maxrate", "12M", "-bufsize", "24M"])
        self.assertEqual(reframe._encoding_args(None), [])
        self.assertEqual(reframe._encoding_args({}), [])
