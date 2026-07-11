#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

import contract
import gate
import progress_set


class ProgressSetTest(unittest.TestCase):
    def test_set_stage_text(self):
        md = contract.progress_markdown("测试广告")
        out = progress_set.set_stage_text(md, "script", "✅", "脚本/广告脚本.md", "0 block", "脚本完成")
        self.assertIn("| 广告脚本+VO+时间轴 | ✅ | 脚本/广告脚本.md | 0 block |", out)
        self.assertIn("脚本完成", out)

    def test_set_deliverable_text(self):
        md = contract.progress_markdown("测试广告")
        out = progress_set.set_deliverable_text(md, "cut_15s", "✅", "合成/cutdown/成片_15s.mp4")
        self.assertIn("| cutdown 15s | 15s | 16:9 | cutdown | 平台默认 | ✅ | 合成/cutdown/成片_15s.mp4 |", out)


class GateTest(unittest.TestCase):
    def _write_json(self, root, rel, payload):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _base_project(self, root):
        self._write_json(root, "需求/brief.json", {
            "brand": "山岚",
            "product": "手冲咖啡",
            "usp": ["48小时内烘焙"],
            "audience": "都市白领",
            "campaign_objective": "转化行动",
            "measurement": {"primary_kpi": "CVR", "conversion_event": "完成下单"},
            "claims": [{
                "claim": "48小时内烘焙", "evidence": "批次烘焙记录",
                "evidence_file": "证据/批次记录.pdf", "method": "按批次核验",
                "sample": "2026Q3 全批次", "date": "2026-07-01",
                "territory": "中国大陆", "approved_by": "法务甲",
            }],
            "rights": {"talent": "未使用真人", "music": "授权曲库", "fonts": "思源黑体", "assets": "自有素材"},
            "mandatories": {"legal_lines": ["广告"]},
        })
        self._write_json(root, "脚本/广告法机检报告.json", {"summary": {"block": 0, "warn": 0}})
        self._write_json(root, "脚本/storyboard.json", {"shots": [{
            "shot_id": "S1", "duration": 3,
            "assets": {"PROD_SHANLAN_COFFEE": True, "BRAND_SHANLAN": True},
        }]})
        self._write_json(root, "脚本/镜头时长.json", {"findings": []})
        self._write_json(root, "配音/时长清单.json", {"has_placeholder": False, "lines": []})

    def test_image_gate_passes_base_project(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            payload = gate.run_gate(root, "image")
            self.assertEqual(payload["summary"]["block"], 0)

    def test_gate_blocks_deferred_brief(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "需求/brief.json", {
                "brand": "山岚", "product": "咖啡", "usp": ["现磨"], "audience": "白领",
                "claims": ["待补"], "rights": {"talent": "未使用真人", "music": "待补", "fonts": "待补", "assets": "待补"},
                "mandatories": {"legal_lines": ["待补"]},
            })
            payload = gate.run_gate(root, "image")
            self.assertGreater(payload["summary"]["block"], 0)
            self.assertTrue(any(f["code"] == "brief_deferred_missing" for f in payload["findings"]))

    def test_compose_blocks_placeholder_voice(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "配音/时长清单.json", {"has_placeholder": True, "lines": []})
            os.makedirs(os.path.join(root, "出图", "分镜"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "镜头1.png"), "wb").close()
            os.makedirs(os.path.join(root, "出视频", "分镜", "视频"), exist_ok=True)
            open(os.path.join(root, "出视频", "分镜", "视频", "clip_01.mp4"), "wb").close()
            payload = gate.run_gate(root, "compose")
            self.assertTrue(any(f["code"] == "voice_placeholder" and f["severity"] == "block" for f in payload["findings"]))

    def test_image_gate_warns_placeholder_not_block(self):
        # image 阶段占位 VO 应是 warn（可先出定妆），不是 block。
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "配音/时长清单.json", {"has_placeholder": True, "lines": []})
            payload = gate.run_gate(root, "image")
            self.assertTrue(any(f["code"] == "voice_placeholder" and f["severity"] == "warn" for f in payload["findings"]))

    def test_image_gate_blocks_forbidden_backend(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "_meta.json", {"image_backend": "即梦"})
            payload = gate.run_gate(root, "image")
            self.assertTrue(any(f["code"] == "image_backend_forbidden" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_image_gate_requires_signoff_for_non_codex_backend(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "_meta.json", {"image_backend": "Dreamina/即梦官方 CLI"})
            payload = gate.run_gate(root, "image")
            self.assertTrue(any(f["code"] == "image_backend_non_codex_requires_signoff"
                                and f["severity"] == "block" for f in payload["findings"]))

    def test_image_gate_accepts_signed_non_codex_backend_exception(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "_meta.json", {"image_backend": "Dreamina/即梦官方 CLI"})
            self._write_json(root, "合规/image_backend_override.json", {
                "approved": True,
                "scope": "image",
                "backend": "dreamina_official",
                "reason": "用户明确指定的单项目例外",
            })
            payload = gate.run_gate(root, "image")
            self.assertFalse(any(f["code"] == "image_backend_non_codex_requires_signoff"
                                 for f in payload["findings"]))

    def test_image_gate_blocks_mixed_backend(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- 生图AI: Codex\n")
            self._write_json(root, "_meta.json", {"image_backend": "Seedream"})
            payload = gate.run_gate(root, "image")
            self.assertTrue(any(f["code"] == "image_backend_mixed" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_ad_law_malformed_report_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "脚本/广告法机检报告.json", {"region": "中国大陆"})  # 无 summary
            payload = gate.run_gate(root, "image")
            self.assertTrue(any(f["code"] == "ad_law_report_malformed" for f in payload["findings"]))

    def test_ad_law_disabled_warns_not_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "脚本/广告法机检报告.json", {"region": "海外", "disabled": True})
            payload = gate.run_gate(root, "image")
            self.assertFalse(any(f["code"].startswith("ad_law_block") for f in payload["findings"]))
            self.assertTrue(any(f["code"] == "ad_law_disabled" and f["severity"] == "warn"
                                for f in payload["findings"]))

    def test_video_gate_blocks_product_qc(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            os.makedirs(os.path.join(root, "出图", "分镜"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "镜头1.png"), "wb").close()
            self._write_json(root, "出图/分镜/product_qc.json", {"summary": {"block": 2, "warn": 0}})
            self._write_json(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
            payload = gate.run_gate(root, "video")
            self.assertTrue(any(f["code"] == "product_qc_block" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_video_gate_accepts_nested_image_frame_folder(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            os.makedirs(os.path.join(root, "出图", "分镜", "图片"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "图片", "镜头1.png"), "wb").write(b"png")
            self._write_json(root, "出图/分镜/product_qc.json", {
                "summary": {"block": 0, "warn": 0},
                "qc_environment": {"precision_level": "full", "pending_product_images": 0},
                "findings": [],
            })
            self._write_json(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
            payload = gate.run_gate(root, "video")
            self.assertFalse(any(f["code"] == "image_frames_missing" for f in payload["findings"]))

    def test_video_gate_blocks_non_codex_landed_image_backend(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- 生图AI: Codex\n")
            os.makedirs(os.path.join(root, "出图", "分镜", "图片"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "图片", "镜头1.png"), "wb").write(b"png")
            self._write_json(root, "出图/分镜/image_jobs_manifest.json", {
                "jobs": [{"job_id": "shot_01_first", "status": "done", "backend": "Dreamina/即梦官方 CLI"}],
            })
            self._write_json(root, "出图/分镜/product_qc.json", {
                "summary": {"block": 0, "warn": 0},
                "qc_environment": {"precision_level": "full", "pending_product_images": 0},
                "findings": [],
            })
            self._write_json(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
            payload = gate.run_gate(root, "video")
            self.assertTrue(any(f["code"] == "image_output_non_codex_requires_redraw" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_video_gate_blocks_degraded_product_qc(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            os.makedirs(os.path.join(root, "出图", "分镜"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "镜头1.png"), "wb").close()
            self._write_json(root, "出图/分镜/product_qc.json", {
                "summary": {"block": 0, "warn": 0},
                "qc_environment": {"precision_level": "degraded"},
                "findings": [],
            })
            self._write_json(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
            payload = gate.run_gate(root, "video")
            self.assertTrue(any(f["code"] == "product_qc_precision_not_full" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_video_gate_blocks_pending_product_qc_images(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            os.makedirs(os.path.join(root, "出图", "分镜"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "镜头1.png"), "wb").close()
            self._write_json(root, "出图/分镜/product_qc.json", {
                "summary": {"block": 0, "warn": 0},
                "qc_environment": {"precision_level": "full", "pending_product_images": 1},
                "findings": [],
            })
            self._write_json(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
            payload = gate.run_gate(root, "video")
            self.assertTrue(any(f["code"] == "product_qc_pending_images" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_compose_gate_blocks_missing_video_qc(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            os.makedirs(os.path.join(root, "出图", "分镜"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "镜头1.png"), "wb").write(b"png")
            os.makedirs(os.path.join(root, "出视频", "分镜", "视频"), exist_ok=True)
            open(os.path.join(root, "出视频", "分镜", "视频", "镜头01.mp4"), "wb").write(b"mp4")
            self._write_json(root, "出图/分镜/product_qc.json", {
                "summary": {"block": 0, "warn": 0},
                "qc_environment": {"precision_level": "full"},
                "findings": [],
            })
            self._write_json(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
            payload = gate.run_gate(root, "compose")
            self.assertTrue(any(f["code"] == "video_qc_missing" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_compose_gate_reports_pending_video_submit_ids(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            os.makedirs(os.path.join(root, "出图", "分镜", "图片"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "图片", "镜头1.png"), "wb").write(b"png")
            self._write_json(root, "出图/分镜/product_qc.json", {
                "summary": {"block": 0, "warn": 0},
                "qc_environment": {"precision_level": "full"},
                "findings": [],
            })
            self._write_json(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
            self._write_json(root, "出视频/分镜/video_jobs_manifest.json", {
                "jobs": [{"clip": "镜头01", "submit_id": "sub_123", "status": "submitted"}],
            })
            self._write_json(root, "出视频/分镜/video_qc.json", {"summary": {"block": 1, "warn": 0}})
            payload = gate.run_gate(root, "compose")
            self.assertTrue(any(f["code"] == "video_clips_pending" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_compose_gate_blocks_video_qc_block(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            os.makedirs(os.path.join(root, "出图", "分镜"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "镜头1.png"), "wb").write(b"png")
            os.makedirs(os.path.join(root, "出视频", "分镜", "视频"), exist_ok=True)
            open(os.path.join(root, "出视频", "分镜", "视频", "镜头01.mp4"), "wb").write(b"mp4")
            self._write_json(root, "出图/分镜/product_qc.json", {
                "summary": {"block": 0, "warn": 0},
                "qc_environment": {"precision_level": "full"},
                "findings": [],
            })
            self._write_json(root, "出视频/分镜/contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
            self._write_json(root, "出视频/分镜/video_qc.json", {"summary": {"block": 1, "warn": 0}})
            payload = gate.run_gate(root, "compose")
            self.assertTrue(any(f["code"] == "video_qc_block" and f["severity"] == "block"
                                for f in payload["findings"]))


class GateProgressWritebackTest(unittest.TestCase):
    def _make_progress(self, root):
        with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
            f.write(contract.progress_markdown("测试广告"))

    def test_get_stage_status_default(self):
        md = contract.progress_markdown("测试广告")
        self.assertEqual(progress_set.get_stage_status(md, "image"), "⬜")

    def test_writeback_blocks_then_clears(self):
        with tempfile.TemporaryDirectory() as root:
            self._make_progress(root)
            blocked = {"summary": {"block": 1}, "findings": [
                {"severity": "block", "code": "image_backend_forbidden", "msg": "x"}]}
            gate._write_progress_state(root, "image", blocked)
            _, text = progress_set.read_progress(root)
            self.assertEqual(progress_set.get_stage_status(text, "image"), "🔴block")
            # 通过后应清回 ⬜
            passing = {"summary": {"block": 0}, "findings": []}
            gate._write_progress_state(root, "image", passing)
            _, text2 = progress_set.read_progress(root)
            self.assertEqual(progress_set.get_stage_status(text2, "image"), "⬜")

    def test_writeback_pass_does_not_touch_done(self):
        with tempfile.TemporaryDirectory() as root:
            self._make_progress(root)
            _, text = progress_set.read_progress(root)
            progress_set.write_progress(os.path.join(root, "_进度.md"),
                                        progress_set.set_stage_text(text, "image", "✅"))
            gate._write_progress_state(root, "image", {"summary": {"block": 0}, "findings": []})
            _, text2 = progress_set.read_progress(root)
            self.assertEqual(progress_set.get_stage_status(text2, "image"), "✅")


class ContractDeliverableTest(unittest.TestCase):
    def test_multi_aspect_emits_reframe_rows(self):
        rows = contract.default_deliverables("30s", "多比例", "仅主片")
        kinds = {r["kind"] for r in rows}
        self.assertIn("reframe", kinds)
        aspects = {r["aspect"] for r in rows if r["kind"] == "reframe"}
        self.assertTrue({"9:16", "1:1"}.issubset(aspects))

    def test_single_aspect_no_reframe(self):
        rows = contract.default_deliverables("30s", "16:9", "主片+15s")
        self.assertFalse(any(r["kind"] == "reframe" for r in rows))

    def test_reconfirm_includes_costly_points(self):
        for cp in ("生图AI", "生视频模型", "生视频渠道", "出视频规格"):
            self.assertIn(cp, contract.RECONFIRM_CHOICE_POINTS)

    def test_channel_menu_has_no_alias_dupes(self):
        menu = contract.VIDEO_CHANNELS_MENU
        self.assertEqual(len(menu), len(set(menu)))
        self.assertNotIn("即梦", menu)  # 别名不入菜单
        self.assertIn("即梦/Dreamina", menu)


if __name__ == "__main__":
    unittest.main()
