#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cutdown + reframe + deliver 纯函数单测（plan/filter 构造逻辑直测，不依赖 ffmpeg）。
    cd skills/ad/ad-compose && python -m pytest test_cutdown_reframe.py
    （或 python3 test_cutdown_reframe.py）
"""
import unittest
import json
import tempfile
from unittest import mock
from pathlib import Path

import cutdown
import deliver
import delivery_qc
import reframe


class ReframeTest(unittest.TestCase):
    def test_aspect_value(self):
        self.assertAlmostEqual(reframe.aspect_value("16:9"), 16 / 9)
        self.assertAlmostEqual(reframe.aspect_value("1920x1080"), 16 / 9)
        self.assertAlmostEqual(reframe.aspect_value("9:16"), 9 / 16)

    def test_out_resolution(self):
        self.assertEqual(reframe.out_resolution("9:16", 1920), (1080, 1920))
        self.assertEqual(reframe.out_resolution("1:1", 1920), (1920, 1920))
        self.assertEqual(reframe.out_resolution("4:5", 1920), (1536, 1920))
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

    def test_dynamic_focus_plan_builds_time_aware_crop(self):
        vf = reframe.reframe_filter("1920x1080", "9:16", focus_plan=[
            {"start": 0, "end": 3, "x": 0.25, "y": 0.5},
            {"start": 3, "end": 6, "x": 0.75, "y": 0.5},
        ])
        self.assertIn("between(t", vf)
        self.assertIn("0.2500", vf)
        self.assertIn("0.7500", vf)


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

    def test_claim_disclosure_is_atomic_in_cutdown(self):
        shots = [
            {"shot_id": "S1", "section": "钩子", "duration": 3},
            {"shot_id": "S2", "section": "产品", "duration": 4, "claim_ids": ["claim_01"]},
            {"shot_id": "S3", "section": "证据", "duration": 2,
             "disclosures": [{"claim_id": "claim_01", "text": "来源与条件"}]},
            {"shot_id": "S4", "section": "CTA", "duration": 3},
        ]
        kept, _, findings = cutdown.plan_cutdown(shots, 8, duration_map=self._dmap(shots))
        ids = {s["shot_id"] for s in kept}
        self.assertIn("S2", ids)
        self.assertIn("S3", ids)
        self.assertFalse(any(f["severity"] == "block" for f in findings))

    def test_claim_without_disclosure_blocks_cutdown(self):
        shots = [{"shot_id": "S1", "section": "产品", "duration": 4, "claim_ids": ["claim_01"]}]
        _, _, findings = cutdown.plan_cutdown(shots, 6, duration_map=self._dmap(shots))
        self.assertTrue(any(f["kind"] == "cutdown_claim_disclosure_missing" and f["severity"] == "block"
                            for f in findings))

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
        self.assertEqual(plan["schema_version"], 5)
        self.assertEqual(plan["render_profile"]["path"], "生产数据/render_profile.json")
        self.assertEqual(plan["deliverables"][0]["render_profile"]["sha256"],
                         plan["render_profile"]["sha256"])

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
        # cutdown 可直接渲染；跨比例未签 adaptation plan 时不得自动中心裁切。
        self.assertIn("--render", cut["command"])
        self.assertIn("# BLOCK", ref["command"])

    def test_mechanical_reframe_command_uses_approved_focus_plan_and_render_profile(self):
        row = {"label": "竖版", "duration": "30s", "aspect": "9:16", "kind": "reframe",
               "spec": "平台默认", "status": "⬜", "path": ""}
        command = deliver.planned_command(
            row, "/tmp/ad-test",
            {"master_render": {"width": 1280, "height": 720}},
            {"status": "approved", "selected_mode": "mechanical_reframe",
             "evidence": {"focus_plan": {"path": "证据/focus.json"}}},
        )
        self.assertIn("--render", command)
        self.assertIn("--focus-plan", command)
        self.assertIn("focus.json", command)
        self.assertNotIn("--src 1920x1080", command)
        self.assertIn("--out-long 1280", command)

    def test_delivery_constraints_are_scoped_to_each_mapped_placement(self):
        md = """## 交付版本矩阵
| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |
|---|---|---|---|---|---|---|
| 主片 | 30s | 16:9 | master | 平台默认 | ⬜ | |
| reframe 9:16 | 30s | 9:16 | reframe | 平台默认 | ⬜ | |
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "需求").mkdir()
            (root / "需求" / "brief.json").write_text(json.dumps({
                "platforms": ["YouTube", "TikTok"],
                "placements": ["YouTube:in_stream", "TikTok:auction_in_feed"],
                "deliverable_placements": {
                    "master": ["YouTube:in_stream"],
                    "reframe_9x16": ["TikTok:auction_in_feed"],
                },
            }), encoding="utf-8")
            plan = deliver.build_plan(str(root), md)
        master = next(row for row in plan["deliverables"] if row["deliverable_id"] == "master")
        vertical = next(row for row in plan["deliverables"] if row["deliverable_id"] == "reframe_9x16")
        self.assertEqual([s["placement_key"] for s in master["platform_constraints"]], ["YouTube:in_stream"])
        self.assertEqual([s["placement_key"] for s in vertical["platform_constraints"]], ["TikTok:auction_in_feed"])

    def test_delivery_qc_measures_loudness_and_peak(self):
        item = {"deliverable_id": "master", "expected_path": "合成/成片_主片.mp4",
                "duration": "30s", "aspect": "16:9", "loudness_lufs": -16.0, "true_peak_db": -1.0,
                "delivery_profile": {"authority": "house_standard", "source": "test contract"},
                "technical_profile": {
                    "video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac",
                    "audio_sample_rate": 48000, "frame_rate_min": 23.0, "frame_rate_max": 30.1,
                    "color_primaries": "bt709", "color_transfer": "bt709", "color_space": "bt709",
                    "color_range": "tv", "scan_type": "progressive",
                    "min_bitrate_warn": 516000,
                }}
        probe = {"format": {"duration": "30.0"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
             "width": 1920, "height": 1080, "avg_frame_rate": "30/1", "bit_rate": "2000000",
             "color_primaries": "bt709", "color_transfer": "bt709", "color_space": "bt709",
             "color_range": "tv", "field_order": "progressive"},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
        ]}
        with mock.patch.object(delivery_qc, "probe", return_value=probe), \
             mock.patch.object(delivery_qc, "measure_loudness", return_value={
                 "integrated_lufs": -16.2, "true_peak_db": -1.2, "lra": 4.0,
             }):
            result = delivery_qc.inspect_item(Path("/tmp/ad"), item)
        self.assertTrue(result["passed"])
        self.assertEqual(result["loudness"]["integrated_lufs"], -16.2)

    def test_delivery_qc_rejects_codec_profile_drift(self):
        item = {"deliverable_id": "master", "expected_path": "合成/成片_主片.mp4",
                "duration": "30s", "aspect": "16:9", "loudness_lufs": -16.0, "true_peak_db": -1.0,
                "delivery_profile": {"authority": "house_standard", "source": "test contract"},
                "technical_profile": {
                    "video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac",
                    "audio_sample_rate": 48000, "frame_rate_min": 23.0, "frame_rate_max": 30.1,
                    "min_bitrate_warn": 516000,
                }}
        probe = {"format": {"duration": "30.0"}, "streams": [
            {"codec_type": "video", "codec_name": "hevc", "pix_fmt": "yuv420p10le",
             "width": 1920, "height": 1080, "avg_frame_rate": "60/1"},
            {"codec_type": "audio", "codec_name": "mp3", "sample_rate": "44100"},
        ]}
        with mock.patch.object(delivery_qc, "probe", return_value=probe), \
             mock.patch.object(delivery_qc, "measure_loudness", return_value={
                 "integrated_lufs": -16.0, "true_peak_db": -1.2, "lra": 4.0,
             }):
            result = delivery_qc.inspect_item(Path("/tmp/ad"), item)
        codes = {row["code"] for row in result["findings"]}
        self.assertFalse(result["passed"])
        self.assertTrue({"video_codec_mismatch", "pixel_format_mismatch", "frame_rate_mismatch",
                         "audio_codec_mismatch", "audio_sample_rate_mismatch"} <= codes)

    def test_delivery_qc_applies_target_platform_constraints(self):
        item = {"deliverable_id": "master", "expected_path": "合成/成片_主片.mp4",
                "duration": "30s", "aspect": "9:16", "loudness_lufs": -16.0, "true_peak_db": -1.0,
                "delivery_profile": {"authority": "house_standard", "source": "test contract"},
                "technical_profile": {"video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac",
                                      "audio_sample_rate": 48000, "frame_rate_min": 23, "frame_rate_max": 31},
                "platform_constraints": [{"platform": "TikTok", "aspect": "9:16", "allowed_aspects": ["9:16"],
                                            "min_resolution": "540x960", "min_bitrate_bps": 516000}]}
        probe = {"format": {"duration": "30.0"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 360,
             "height": 640, "avg_frame_rate": "30/1", "bit_rate": "300000"},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
        ]}
        with mock.patch.object(delivery_qc, "probe", return_value=probe), \
             mock.patch.object(delivery_qc, "measure_loudness", return_value={
                 "integrated_lufs": -16.0, "true_peak_db": -1.2, "lra": 4.0,
             }):
            result = delivery_qc.inspect_item(Path("/tmp/ad"), item)
        codes = {row["code"] for row in result["findings"]}
        self.assertIn("platform_resolution_below_minimum", codes)
        self.assertIn("platform_bitrate_below_minimum", codes)

    def test_delivery_qc_rejects_missing_bt709_metadata_when_profile_requires_it(self):
        item = {"deliverable_id": "master", "expected_path": "合成/成片_主片.mp4",
                "duration": "30s", "aspect": "16:9", "loudness_lufs": -16.0, "true_peak_db": -1.0,
                "delivery_profile": {"authority": "house_standard", "source": "test"},
                "technical_profile": {"video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac",
                                      "audio_sample_rate": 48000, "frame_rate_min": 23, "frame_rate_max": 31,
                                      "color_primaries": "bt709", "color_transfer": "bt709",
                                      "color_space": "bt709", "color_range": "tv", "scan_type": "progressive"}}
        probe = {"format": {"duration": "30.0"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
             "width": 1920, "height": 1080, "avg_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
        ]}
        with mock.patch.object(delivery_qc, "probe", return_value=probe), \
             mock.patch.object(delivery_qc, "measure_loudness", return_value={
                 "integrated_lufs": -16.0, "true_peak_db": -1.2, "lra": 4.0,
             }):
            result = delivery_qc.inspect_item(Path("/tmp/ad"), item)
        self.assertFalse(result["passed"])
        self.assertIn("color_primaries_mismatch", {f["code"] for f in result["findings"]})

    def test_delivery_qc_applies_placement_duration_constraints(self):
        item = {"deliverable_id": "cut_6s", "expected_path": "合成/cut.mp4", "duration": "6s", "aspect": "9:16",
                "loudness_lufs": -16.0, "true_peak_db": -1.0,
                "delivery_profile": {"authority": "house_standard", "source": "test"},
                "technical_profile": {"video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac",
                                      "audio_sample_rate": 48000, "frame_rate_min": 23, "frame_rate_max": 31},
                "platform_constraints": [{"placement_key": "YouTube:demand_gen", "allowed_aspects": ["9:16"],
                                            "min_duration_seconds": 5, "in_stream_eligible_min_duration_seconds": 10}]}
        probe = {"format": {"duration": "6.0"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 1080,
             "height": 1920, "avg_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
        ]}
        with mock.patch.object(delivery_qc, "probe", return_value=probe), \
             mock.patch.object(delivery_qc, "measure_loudness", return_value={
                 "integrated_lufs": -16.0, "true_peak_db": -1.2, "lra": 4.0,
             }):
            result = delivery_qc.inspect_item(Path("/tmp/ad"), item)
        codes = {f["code"] for f in result["findings"]}
        self.assertNotIn("placement_duration_below_minimum", codes)
        self.assertIn("placement_in_stream_ineligible", codes)

    def test_sound_off_placement_can_deliver_without_audio(self):
        item = {"deliverable_id": "oop", "expected_path": "合成/oop.mp4", "duration": "10s", "aspect": "9:16",
                "delivery_profile": {"authority": "house_standard", "source": "test"},
                "technical_profile": {"video_codec": "h264", "pixel_format": "yuv420p",
                                      "frame_rate_min": 23, "frame_rate_max": 31},
                "platform_constraints": [{"placement_key": "TikTok:out_of_phone", "sound_mode": "sound_off",
                                            "allowed_aspects": ["9:16"]}]}
        probe = {"format": {"duration": "10.0"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 1080,
             "height": 1920, "avg_frame_rate": "30/1"},
        ]}
        with mock.patch.object(delivery_qc, "probe", return_value=probe):
            result = delivery_qc.inspect_item(Path("/tmp/ad"), item)
        self.assertTrue(result["passed"])
        self.assertIn("sound_off_delivery", {f["code"] for f in result["findings"]})


if __name__ == "__main__":
    unittest.main()
