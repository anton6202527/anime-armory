#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate/progress tests.

Can run without pytest:
    python3 skills/mv/mv-craft/scripts/test_gate_progress.py
"""
import json
import os
import tempfile
import unittest
from unittest import mock

import gate
import mv_utils


def make_project(root):
    for sub in ("歌", "词", "节拍", "分镜", "出图/段落/图片"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试", "song_timing": "先传音乐", "song_rights_status": "自有", "is_demo": True}, f, ensure_ascii=False)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write(
            "# _设置\n\n## 选择\n"
            "- MV用途: 歌曲Demo\n- 歌曲输入时序: 先传音乐\n"
            "- MV规划粒度: 标准\n- 卡点策略: 副歌强卡点\n"
            "- 字幕语言: 无字幕\n- 演唱口型: 关闭\n"
            "- 生图模型: Seedream 4.0\n- 生图渠道: 即梦/Dreamina\n"
            "- 生视频模型: Seedance 2.5\n- 生视频渠道: 即梦/Dreamina\n"
            "- 出视频规格: 预算一般\n- 合成画幅: 16:9 横屏\n"
            "- 输入歌权利: 自有\n"
        )
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write("""# 进度

## 制MV 阶段
| 阶段 | skill | 状态 |
|---|---|---|
| 项目骨架 | mv/scripts/init_project.py | [x] |
| clip/timeline 规划 | mv-plan/scripts/plan_clips.py | [ ] |
""")
    with open(os.path.join(root, "歌", "song.mp3"), "wb") as f:
        f.write(b"fake")
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[verse]\n一句歌词\n")
    with open(os.path.join(root, "节拍", "beatgrid.json"), "w", encoding="utf-8") as f:
        json.dump({
            "duration": 5,
            "source_audio_sha256": mv_utils.content_hash(os.path.join(root, "歌", "song.mp3")),
            "beats": [0, 1, 2, 3, 4], "downbeats": [0, 4],
            "timing_verified": True, "downbeats_verified": True,
            "sections_verified": True, "sections_complete": True,
            "sections": [{"section": "verse", "start": 0, "end": 5}],
            "timing_review": {"accepted": True, "reviewer": "剪辑师", "notes": "逐拍确认"},
        }, f, ensure_ascii=False)
    with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
        f.write("# 视觉蓝图\n")
    os.makedirs(os.path.join(root, "合规"), exist_ok=True)
    with open(os.path.join(root, "合规", "rights_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"assertions": {key: "owned" for key in (
            "song", "visual_reference", "likeness", "brand", "location", "choreography"
        )}}, f, ensure_ascii=False)


def write_clip_plan_with_image(root):
    os.makedirs(os.path.join(root, "出图", "段落", "图片"), exist_ok=True)
    with open(os.path.join(root, "出图", "段落", "图片", "Clip_001.png"), "wb") as f:
        f.write(b"fake")
    inputs = {
        "song": mv_utils.content_hash(mv_utils.find_song(root)),
        "beatgrid": mv_utils.content_hash(os.path.join(root, "节拍", "beatgrid.json")),
        "lyrics": mv_utils.content_hash(os.path.join(root, "词", "lyrics.md")),
        "blueprint": mv_utils.content_hash(os.path.join(root, "视觉蓝图.md")),
        "settings": mv_utils.content_hash(os.path.join(root, "_设置.md")),
    }
    with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"inputs_sha256": inputs, "clips": [{
            "clip_id": "Clip_001", "start": 0, "end": 5, "duration": 5,
            "image_path": "出图/段落/图片/Clip_001.png",
        }]}, f, ensure_ascii=False)


def write_image_qc(root, hard=0, precision="full", advisory=0):
    path = os.path.join(root, "生产数据", "image_qc", "image_qc.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image_rel = "出图/段落/图片/Clip_001.png"
    assets = ({image_rel: mv_utils.content_hash(os.path.join(root, image_rel))}
              if os.path.isfile(os.path.join(root, image_rel)) else {})
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "kind": "mv_image_qc", "version": 3,
            "summary": {
                "hard_blocks": hard,
                "advisory": advisory,
                "verdict": "block" if hard else ("review" if advisory else "ok"),
            },
            "qc_environment": {"precision_level": precision},
            "assets_sha256": assets,
            "generation_provenance": {
                "complete": not hard,
                "summary": {"block": hard, "ok": len(assets) if not hard else 0},
            },
        }, f, ensure_ascii=False)


def accepted_image_audit():
    return {
        "summary": {"expected": 1, "accepted": 1, "all_current_accepted": True},
        "rows": [{"asset": "出图/段落/图片/Clip_001.png", "status": "accepted", "findings": []}],
    }


class GateProgressTest(unittest.TestCase):
    def test_beatgrid_source_hash_mismatch_blocks_even_demo(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            path = os.path.join(tmp, "节拍", "beatgrid.json")
            payload = json.load(open(path, encoding="utf-8"))
            payload["source_audio_sha256"] = "0" * 64
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            errors, _warnings = gate._beatgrid_contract(
                tmp, "plan", {"is_demo": True}, mv_utils.find_song(tmp)
            )
            self.assertTrue(any("source_audio_sha256" in error for error in errors))

    def test_plan_receipt_invalidates_on_lyrics_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            plan = {
                "inputs_sha256": {
                    "song": mv_utils.content_hash(mv_utils.find_song(tmp)),
                    "beatgrid": mv_utils.content_hash(os.path.join(tmp, "节拍", "beatgrid.json")),
                    "lyrics": mv_utils.content_hash(os.path.join(tmp, "词", "lyrics.md")),
                    "blueprint": mv_utils.content_hash(os.path.join(tmp, "视觉蓝图.md")),
                    "alignment": "",
                    "settings_plan": gate.contract.plan_settings_digest(mv_utils.parse_settings(tmp)),
                },
                "clips": [],
            }
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as handle:
                json.dump(plan, handle)
            with open(os.path.join(tmp, "词", "lyrics.md"), "a", encoding="utf-8") as handle:
                handle.write("改词\n")
            errors = gate._staleness_errors(tmp, "image", {"is_demo": True})
            self.assertTrue(any("lyrics" in error for error in errors))

    def test_find_song_and_plan_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            self.assertEqual(os.path.basename(mv_utils.find_song(tmp)), "song.mp3")
            errors, _warnings = gate.check(tmp, "plan")
            self.assertEqual(errors, [])

    def test_instrumental_no_subtitle_no_lipsync_does_not_require_lyrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.remove(os.path.join(tmp, "词", "lyrics.md"))
            settings_path = os.path.join(tmp, "_设置.md")
            settings = mv_utils.read_text(settings_path)
            with open(settings_path, "w", encoding="utf-8") as handle:
                handle.write(settings)
            errors, _warnings = gate.check(tmp, "plan")
            self.assertEqual(errors, [])

    def test_progress_stage_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            self.assertTrue(mv_utils.update_progress_stage(tmp, "plan"))
            text = mv_utils.read_text(os.path.join(tmp, "_进度.md"))
            self.assertIn("| clip/timeline 规划 | mv-plan/scripts/plan_clips.py | [x] |", text)

    def test_rough_blueprint_blocks_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "视觉蓝图.md"), "w", encoding="utf-8") as f:
                f.write("- 状态：rough（待成品歌/beatgrid 复核）\n")
            errors, _warnings = gate.check(tmp, "plan")
            self.assertTrue(any("rough" in e for e in errors))

    def test_video_jobs_requires_image_qc(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            errors, _warnings = gate._image_qc_errors_warnings(tmp, "video_jobs")
            self.assertTrue(any("image_qc" in e for e in errors))

    def test_video_jobs_blocks_image_qc_hard_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp, hard=1)
            errors, _warnings = gate._image_qc_errors_warnings(tmp, "video_jobs")
            self.assertTrue(any("hard block=1" in e for e in errors))

    def test_video_jobs_passes_full_image_qc(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp)
            with mock.patch.object(gate, "_image_ledger_audit", return_value=accepted_image_audit()):
                errors, _warnings = gate._image_qc_errors_warnings(tmp, "video_jobs")
            self.assertEqual(errors, [])

    def test_image_qc_stale_by_assets_sha256_blocks(self):
        """收据 hash 与当前图片不符 → 过期 error（mtime 不变也拦得住，替代旧 mtime 口径）。"""
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            path = os.path.join(tmp, "生产数据", "image_qc", "image_qc.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"kind": "mv_image_qc",
                           "summary": {"hard_blocks": 0, "advisory": 0, "verdict": "ok"},
                           "qc_environment": {"precision_level": "full"},
                           "assets_sha256": {"出图/段落/图片/Clip_001.png": "0" * 64}}, f)
            with mock.patch.object(gate, "_image_ledger_audit", return_value=accepted_image_audit()):
                errors, _warnings = gate._image_qc_errors_warnings(tmp, "video_jobs")
            self.assertTrue(any("已过期" in e for e in errors))

    def test_image_qc_fresh_assets_sha256_passes_without_legacy_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            image_rel = "出图/段落/图片/Clip_001.png"
            path = os.path.join(tmp, "生产数据", "image_qc", "image_qc.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"kind": "mv_image_qc", "version": 3,
                           "summary": {"hard_blocks": 0, "advisory": 0, "verdict": "ok"},
                           "qc_environment": {"precision_level": "full"},
                           "assets_sha256": {image_rel: mv_utils.content_hash(os.path.join(tmp, image_rel))},
                           "generation_provenance": {"complete": True, "summary": {"block": 0, "ok": 1}}}, f)
            with mock.patch.object(gate, "_image_ledger_audit", return_value=accepted_image_audit()):
                errors, warnings = gate._image_qc_errors_warnings(tmp, "video_jobs")
            self.assertEqual(errors, [])
            self.assertFalse(any("assets_sha256" in w for w in warnings))

    def test_image_qc_legacy_report_warns_contract_upgrade(self):
        """旧版报告缺 assets_sha256 时 fail-closed，不再用 mtime 代替内容收据。"""
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp)
            path = os.path.join(tmp, "生产数据", "image_qc", "image_qc.json")
            report = json.load(open(path, encoding="utf-8"))
            report.pop("assets_sha256")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False)
            errors, warnings = gate._image_qc_errors_warnings(tmp, "video_jobs")
            self.assertTrue(any("assets_sha256" in error for error in errors))
            self.assertEqual(warnings, [])

    def test_formal_video_jobs_requires_picture_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            meta_path = os.path.join(tmp, "_meta.json")
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            meta["is_demo"] = False
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp)
            errors = gate._picture_lock_errors(tmp, "video_jobs", {"is_demo": True})
            self.assertTrue(any("picture lock" in error for error in errors))

    def test_compose_video_reports_are_hash_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            for rel in ("出视频", "设定", "生产数据/video_inherit_contract", "生产数据/video_qc", "出视频/视频"):
                os.makedirs(os.path.join(tmp, rel), exist_ok=True)
            inputs = {
                "分镜/clip_plan.json": {"clips": [{"clip_id": "Clip_001"}]},
                "分镜/timeline_manifest.json": {"clips": [{"clip_id": "Clip_001", "video_path": "出视频/视频/Clip_001.mp4"}]},
                "出视频/jobs_manifest.json": {"jobs": []},
                "设定/identity_registry.json": {},
                "分镜/reference_plan.json": {},
            }
            for rel, payload in inputs.items():
                with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
                    json.dump(payload, f)
            video_rel = "出视频/视频/Clip_001.mp4"
            with open(os.path.join(tmp, video_rel), "wb") as f:
                f.write(b"video-v1")
            inherit_inputs = ("分镜/clip_plan.json", "出视频/jobs_manifest.json", "设定/identity_registry.json", "分镜/reference_plan.json")
            video_inputs = ("分镜/clip_plan.json", "分镜/timeline_manifest.json")
            inherit = {"summary": {"hard_blocks": 0}, "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(tmp, rel)) for rel in inherit_inputs}}
            video_hashes = {video_rel: mv_utils.content_hash(os.path.join(tmp, video_rel))}
            video = {
                "kind": "mv_video_qc", "schema_version": 2,
                "summary": {"hard_blocks": 0},
                "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(tmp, rel)) for rel in video_inputs},
                "selected_video_sha256": video_hashes,
                "seams": [],
                "semantic_review": {
                    "accepted": True, "reviewer": "导演", "bound_video_sha256": video_hashes,
                    "bound_seam_contract_sha256": mv_utils.json_hash([]),
                },
            }
            with open(os.path.join(tmp, "生产数据/video_inherit_contract/inherit_contract.json"), "w", encoding="utf-8") as f:
                json.dump(inherit, f)
            with open(os.path.join(tmp, "生产数据/video_qc/video_qc.json"), "w", encoding="utf-8") as f:
                json.dump(video, f)
            errors = gate._video_report_errors(tmp, "compose")
            self.assertTrue(any("schema v4" in error for error in errors))
            self.assertTrue(any("schema v2" in error for error in errors))
            with open(os.path.join(tmp, video_rel), "wb") as f:
                f.write(b"video-v2")
            self.assertTrue(any("selected_video_sha256" in error for error in gate._video_report_errors(tmp, "compose")))

    def test_degraded_image_qc_legacy_boolean_no_longer_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp, precision="degraded")
            path = os.path.join(tmp, "生产数据", "image_qc", "image_qc.json")
            report = json.load(open(path, encoding="utf-8"))
            report["manual_review_accepted"] = True
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False)
            errors, _warnings = gate._image_qc_errors_warnings(tmp, "video_jobs")
            self.assertTrue(any("只接受 full" in e for e in errors))

    def test_degraded_image_qc_bound_manual_review_still_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp, precision="degraded")
            path = os.path.join(tmp, "生产数据", "image_qc", "image_qc.json")
            report = json.load(open(path, encoding="utf-8"))
            binding = mv_utils.json_hash({k: v for k, v in report.items()
                                          if k not in ("manual_review", "json_path", "markdown_path")})
            report["manual_review"] = {"accepted": True, "reviewer": "审图人",
                                       "notes": "逐图并排看过", "bound_report_sha256": binding}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False)
            with mock.patch.object(gate, "_image_ledger_audit", return_value=accepted_image_audit()):
                errors, warnings = gate._image_qc_errors_warnings(tmp, "video_jobs")
            self.assertTrue(any("只接受 full" in error for error in errors))
            self.assertFalse(any("具名人工放行" in warning for warning in warnings))

    def _write_identity_registry(self, root, ref_count=3):
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        os.makedirs(os.path.join(root, "出图", "共享", "图片"), exist_ok=True)
        paths = []
        for idx in range(ref_count):
            rel = f"出图/共享/图片/定妆_主角_{idx}.png"
            with open(os.path.join(root, rel), "wb") as f:
                f.write(b"fake")
            paths.append(rel)
        registry = {
            "lead_id": "CHAR_lead",
            "identities": [{"id": "CHAR_lead", "display_name": "主角",
                            "reference_group": "REF_lead"}],
            "reference_groups": [{"id": "REF_lead", "identity_id": "CHAR_lead",
                                  "status": "ready" if ref_count >= 3 else "partial",
                                  "paths": paths}],
        }
        with open(os.path.join(root, "设定", "identity_registry.json"), "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False)

    def test_formal_video_jobs_requires_lead_costume_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            errors, warnings = gate._identity_readiness(tmp, "video_jobs", {"is_demo": False})
            self.assertTrue(any("identity_registry" in e for e in errors))
            self._write_identity_registry(tmp, ref_count=1)
            errors, warnings = gate._identity_readiness(tmp, "video_jobs", {"is_demo": False})
            self.assertTrue(any("定妆包未 ready" in e for e in errors))
            self._write_identity_registry(tmp, ref_count=3)
            errors, warnings = gate._identity_readiness(tmp, "video_jobs", {"is_demo": False})
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_demo_identity_readiness_is_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            errors, warnings = gate._identity_readiness(tmp, "video_jobs", {"is_demo": True})
            self.assertTrue(any("identity_registry" in error for error in errors))
            self.assertEqual(warnings, [])
            errors, warnings = gate._identity_readiness(tmp, "image", {"is_demo": False})
            self.assertEqual(errors, [])  # image 期共享定妆本身在产出，只提醒
            self.assertTrue(warnings)

    def test_demo_flag_with_formal_traces_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            self.assertEqual(gate._demo_flag_warnings(tmp, "image", {"is_demo": True}), [])
            os.makedirs(os.path.join(tmp, "制片"), exist_ok=True)
            with open(os.path.join(tmp, "制片", "picture_lock.json"), "w", encoding="utf-8") as f:
                json.dump({"accepted": True}, f)
            warnings = gate._demo_flag_warnings(tmp, "image", {"is_demo": True})
            self.assertTrue(any("正式生产痕迹" in w for w in warnings))
            self.assertTrue(gate._demo_flag_warnings(tmp, "image", {"is_demo": False}))

    def test_settings_are_runtime_truth_and_demo_never_skips_semantic_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            meta = {"is_demo": False, "song_timing": "后配歌曲"}
            self.assertEqual(gate._settings_mode(tmp, meta), "先传音乐")
            self.assertTrue(gate._runtime_state(tmp)["is_demo"])
            write_clip_plan_with_image(tmp)
            errors = gate._semantic_prompt_errors(tmp, "image", {"is_demo": True})
            self.assertTrue(any("语义分镜" in error for error in errors))

    def test_semantic_gate_rejects_partial_or_stale_prompt_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.makedirs(os.path.join(tmp, "出图", "段落", "prompt"), exist_ok=True)
            os.makedirs(os.path.join(tmp, "出视频", "prompt"), exist_ok=True)
            image_rel = "出图/段落/prompt/Clip_001.md"
            video_rel = "出视频/prompt/Clip_001.md"
            for rel, content in ((image_rel, "image"), (video_rel, "video")):
                with open(os.path.join(tmp, rel), "w", encoding="utf-8") as handle:
                    handle.write(content)
            plan_path = os.path.join(tmp, "分镜", "clip_plan.json")
            with open(plan_path, "w", encoding="utf-8") as handle:
                json.dump({"clips": [{"clip_id": "Clip_001",
                    "image_prompt_path": image_rel, "video_prompt_path": video_rel}]}, handle)
            receipt = {
                "schema_version": 3, "kind": "mv_semantic_prompts", "complete": False,
                "updated_clips": 1, "result_clip_plan_sha256": mv_utils.content_hash(plan_path),
                "inputs_sha256": {
                    "lyrics": mv_utils.content_hash(os.path.join(tmp, "词", "lyrics.md")),
                    "blueprint": mv_utils.content_hash(os.path.join(tmp, "视觉蓝图.md")),
                },
                "prompt_outputs_sha256": {"Clip_001": {
                    "image": mv_utils.content_hash(os.path.join(tmp, image_rel)),
                    "video": mv_utils.content_hash(os.path.join(tmp, video_rel)),
                }},
            }
            with open(os.path.join(tmp, "分镜", "semantic_prompts.json"), "w", encoding="utf-8") as handle:
                json.dump(receipt, handle)
            errors = gate._semantic_prompt_errors(tmp, "image", {})
            self.assertTrue(any("complete" in error for error in errors))
            receipt["complete"] = True
            receipt["prompt_outputs_sha256"]["Clip_001"]["video"] = "0" * 64
            with open(os.path.join(tmp, "分镜", "semantic_prompts.json"), "w", encoding="utf-8") as handle:
                json.dump(receipt, handle)
            errors = gate._semantic_prompt_errors(tmp, "image", {})
            self.assertTrue(any("video prompt" in error for error in errors))

    def test_costly_gate_missing_settings_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.remove(os.path.join(tmp, "_设置.md"))
            errors, _warnings = gate.check(tmp, "image")
            self.assertTrue(any("settings-first" in error for error in errors))

    def test_alignment_text_coverage_is_not_acoustic_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            settings_path = os.path.join(tmp, "_设置.md")
            settings = mv_utils.read_text(settings_path).replace("字幕语言: 无字幕", "字幕语言: 中文")
            with open(settings_path, "w", encoding="utf-8") as handle:
                handle.write(settings)
            os.makedirs(os.path.join(tmp, "字幕"), exist_ok=True)
            for rel, content in (("字幕/karaoke.ass", "ass"), ("字幕/lyrics.lrc", "lrc")):
                with open(os.path.join(tmp, rel), "w", encoding="utf-8") as handle:
                    handle.write(content)
            song = mv_utils.find_song(tmp)
            inputs = {
                "词/lyrics.md": mv_utils.content_hash(os.path.join(tmp, "词", "lyrics.md")),
                mv_utils.relpath(tmp, song): mv_utils.content_hash(song),
            }
            outputs = {
                rel: mv_utils.content_hash(os.path.join(tmp, rel))
                for rel in ("字幕/karaoke.ass", "字幕/lyrics.lrc")
            }
            report = {
                "kind": "mv_lyric_alignment_report", "schema_version": 5,
                "alignment_unit": "character",
                "inputs_sha256": inputs, "outputs_sha256": outputs,
                "master_song": mv_utils.relpath(tmp, song), "audio": mv_utils.relpath(tmp, song),
                "aligned_lines": 1, "lyric_lines": 1, "character_coverage_ratio": 1.0,
                "coverage_metric": "text_character_mapping_ratio_not_acoustic_confidence",
                "lines": [{"line_character_coverage": 1.0}], "timing_issues": [],
                "stem_master_timing": {
                    "schema_version": 1, "status": "pass", "method": "same_master_file",
                    "offset_seconds": 0.0, "drift_seconds": 0.0,
                    "bindings": {
                        "master": {"path": mv_utils.relpath(tmp, song),
                                   "sha256": mv_utils.content_hash(song)},
                        "alignment_audio": {"path": mv_utils.relpath(tmp, song),
                                            "sha256": mv_utils.content_hash(song)},
                    },
                },
            }
            binding = gate._alignment_acceptance_binding(tmp, report)
            report["acceptance"] = {"status": "pending", "accepted": False,
                                    "required_binding": binding}
            path = os.path.join(tmp, "字幕", "alignment_report.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False)
            errors = gate._alignment_contract_errors(tmp, "compose", {"is_demo": True})
            self.assertTrue(any("尚未" in error for error in errors))
            report["manual_review"] = {
                "kind": "named_full_listening_review", "accepted": True, "verdict": "pass",
                "reviewer": "对白剪辑师", "notes": "逐行听审并校正爆破音起点",
                "binding": binding,
                "bound_report_preaccept_sha256": binding["report_preaccept_content_sha256"],
                "bound_inputs_sha256": inputs, "bound_outputs_sha256": outputs,
            }
            report["acceptance"] = {"status": "accepted", "accepted": True,
                                    "route": "named_listening_review", "binding": binding,
                                    "evidence_content_sha256": mv_utils.json_hash(report["manual_review"])}
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False)
            self.assertEqual(gate._alignment_contract_errors(tmp, "compose", {"is_demo": True}), [])
            report["manual_review"]["notes"] = "签收后被手改"
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False)
            self.assertTrue(any(
                "签收后变化" in error
                for error in gate._alignment_contract_errors(tmp, "compose", {"is_demo": True})
            ))

    def test_alignment_stem_timing_requires_current_bindings_and_strict_automatic_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            master = mv_utils.find_song(tmp)
            stem = os.path.join(tmp, "歌", "vocals.wav")
            with open(stem, "wb") as handle:
                handle.write(b"stem")
            master_rel = mv_utils.relpath(tmp, master)
            stem_rel = mv_utils.relpath(tmp, stem)
            report = {
                "master_song": master_rel,
                "audio": stem_rel,
                "stem_master_timing": {
                    "status": "pass",
                    "method": "automatic_ffmpeg_rms_envelope_correlation",
                    "offset_seconds": 0.0,
                    "drift_seconds": 0.0,
                    "bindings": {
                        "master": {"path": master_rel, "sha256": mv_utils.content_hash(master)},
                        "alignment_audio": {"path": stem_rel, "sha256": mv_utils.content_hash(stem)},
                    },
                    "windows": [
                        {"correlation": 0.9, "offset_seconds": 0.0},
                        {"correlation": 0.9, "offset_seconds": 0.0},
                        {"correlation": 0.9, "offset_seconds": 0.0},
                    ],
                    "minimum_correlation": 0.9,
                    "duration_delta_seconds": 0.0,
                    "thresholds": {"minimum_correlation": 0.01},
                },
            }
            errors = gate._alignment_stem_timing_errors(tmp, report)
            self.assertTrue(any("minimum_correlation>=0.15" in error for error in errors))
            self.assertTrue(any("maximum_absolute_drift_seconds" in error for error in errors))

    def test_otio_requires_integer_frames_and_official_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            plan_path = os.path.join(tmp, "分镜", "clip_plan.json")
            timeline_path = os.path.join(tmp, "分镜", "timeline_manifest.json")
            timeline = {
                "rate": 24, "source_clip_plan_sha256": mv_utils.content_hash(plan_path),
                "clips": [{
                    "clip_id": "Clip_001", "start": 0, "end": 5, "duration": 5,
                    "start_frame": 0, "end_frame": 120, "duration_frames": 120,
                }],
            }
            with open(timeline_path, "w", encoding="utf-8") as handle:
                json.dump(timeline, handle)
            otio_path = os.path.join(tmp, "分镜", "timeline.otio")
            with open(otio_path, "w", encoding="utf-8") as handle:
                json.dump({
                    "OTIO_SCHEMA": "Timeline.1",
                    "tracks": {"OTIO_SCHEMA": "Stack.1", "children": [
                        {"OTIO_SCHEMA": "Track.1", "kind": "Video", "children": [{
                            "OTIO_SCHEMA": "Clip.2", "source_range": {
                                "OTIO_SCHEMA": "TimeRange.1",
                                "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0, "rate": 24},
                                "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": 120, "rate": 24},
                            },
                        }]},
                        {"OTIO_SCHEMA": "Track.1", "kind": "Audio", "children": []},
                    ]},
                }, handle)
            receipt_path = os.path.join(tmp, "生产数据", "otio", "otio_receipt.json")
            os.makedirs(os.path.dirname(receipt_path), exist_ok=True)
            receipt = {
                "kind": "mv_otio_export_receipt", "schema_version": 3, "rate": 24,
                "timebase": {"unit": "frame", "integral_rational_time": True},
                "otio_sha256": mv_utils.content_hash(otio_path),
                "timeline_edit_sha256": mv_utils.timeline_edit_hash(timeline),
                "inputs_sha256": {
                    "分镜/timeline_manifest.json": mv_utils.content_hash(timeline_path),
                    "节拍/beatgrid.json": mv_utils.content_hash(os.path.join(tmp, "节拍", "beatgrid.json")),
                },
                "media_sha256": {}, "missing_media": [],
                "tracks": {"video": 1, "audio": 1},
                "official_roundtrip": {"status": "ok", "library_version": "0.18.1"},
            }
            with open(receipt_path, "w", encoding="utf-8") as handle:
                json.dump(receipt, handle)
            self.assertEqual(gate._otio_contract_errors(tmp, "video_jobs", {}), [])
            receipt["official_roundtrip"] = {"status": "unavailable"}
            with open(receipt_path, "w", encoding="utf-8") as handle:
                json.dump(receipt, handle)
            self.assertTrue(any("official" in error.lower() or "官方" in error
                                for error in gate._otio_contract_errors(tmp, "video_jobs", {})))
            receipt["official_roundtrip"] = {"status": "ok", "library_version": "0.18.1"}
            timeline["clips"][0].pop("duration_frames")
            with open(timeline_path, "w", encoding="utf-8") as handle:
                json.dump(timeline, handle)
            self.assertTrue(any("integer-frame" in error
                                for error in gate._otio_contract_errors(tmp, "video_jobs", {})))

    def test_color_manifest_schema2_is_exact_and_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.makedirs(os.path.join(tmp, "出视频", "视频"), exist_ok=True)
            video_rel = "出视频/视频/Clip_001.mp4"
            with open(os.path.join(tmp, video_rel), "wb") as handle:
                handle.write(b"video")
            timeline_path = os.path.join(tmp, "分镜", "timeline_manifest.json")
            with open(timeline_path, "w", encoding="utf-8") as handle:
                json.dump({"clips": [{"clip_id": "Clip_001", "video_path": video_rel}]}, handle)
            digest = mv_utils.content_hash(os.path.join(tmp, video_rel))
            color = {
                "kind": "mv_color_input_manifest", "schema_version": 2,
                "output_space": "bt709_sdr_limited",
                "timeline_sha256": mv_utils.content_hash(timeline_path),
                "inputs_sha256": {video_rel: digest},
                "inputs": [{
                    "path": video_rel, "sha256": digest,
                    "classification": "declared_bt709_limited", "interpretation": "bt709_limited",
                    "ffmpeg_input_filter": "setparams=color_primaries=bt709:range=tv",
                }],
                "summary": {"hard_blocks": 0, "verdict": "ok"},
            }
            path = os.path.join(tmp, "生产数据", "color", "color_input_manifest.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(color, handle)
            self.assertEqual(gate._color_contract_errors(tmp, "compose"), [])
            color["inputs"][0].update({
                "classification": "declared_bt709_full", "interpretation": "bt709_full",
                "ffmpeg_input_filter": "setparams=range=tv",
            })
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(color, handle)
            self.assertTrue(any("full→limited" in error for error in gate._color_contract_errors(tmp, "compose")))
            with open(os.path.join(tmp, video_rel), "ab") as handle:
                handle.write(b"changed")
            self.assertTrue(any("已过期" in error for error in gate._color_contract_errors(tmp, "compose")))

    def test_schema4_registered_video_requires_actual_submit_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            os.makedirs(os.path.join(tmp, "出视频", "takes", "Clip_001"), exist_ok=True)
            video_rel = "出视频/takes/Clip_001/take_01.mp4"
            with open(os.path.join(tmp, video_rel), "wb") as handle:
                handle.write(b"take")
            plan_path = os.path.join(tmp, "分镜", "clip_plan.json")
            timeline_path = os.path.join(tmp, "分镜", "timeline_manifest.json")
            with open(timeline_path, "w", encoding="utf-8") as handle:
                json.dump({"clips": [{"clip_id": "Clip_001", "video_path": video_rel}]}, handle)
            inherit = gate._video_inherit_module()
            capability = inherit.video_capabilities
            controls = {}
            manifest = {
                "kind": "mv_video_jobs", "schema_version": 4,
                "video_model": "Seedance 2.5", "video_channel": "即梦/Dreamina",
                "video_spec": "预算一般", "clip_plan_sha256": mv_utils.content_hash(plan_path),
                "capability_graph_version": capability.CAPABILITY_GRAPH_VERSION,
                "capability_graph_sha256": capability.graph_sha256(),
                "provider_route": {}, "freshness": {"schema_version": 1},
                "jobs": [{
                    "clip_id": "Clip_001", "video_model": "Seedance 2.5", "backend": "即梦/Dreamina",
                    "provider_route": {}, "selected_take": "take_01", "selected_video_path": video_rel,
                    "takes": [{
                        "take_id": "take_01", "status": "selected", "provider_route": {},
                        "planned_request_controls": controls,
                        "planned_request_controls_sha256": capability.stable_hash(controls),
                        "compiled_request_controls": controls,
                        "compiled_request_controls_sha256": capability.stable_hash(controls),
                        "prompt_compiler": {"kind": inherit.COMPILER_KIND, "version": inherit.COMPILER_VERSION},
                        "video_path": video_rel, "video_sha256": mv_utils.content_hash(os.path.join(tmp, video_rel)),
                        "score": {"motion": 4, "identity": 4, "beat_fit": 4, "clarity": 4},
                        "scored_by": "导演",
                    }],
                }],
                "sequence_units": [],
            }
            manifest_path = os.path.join(tmp, "出视频", "jobs_manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(manifest, handle, ensure_ascii=False)
            errors = gate._video_manifest_errors(tmp, "video")
            self.assertTrue(any("missing_actual_submit_receipt" in error for error in errors))

    def test_drift_risk_advisory_never_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            # 无 clip_plan → 静默
            self.assertEqual(gate._drift_risk_warnings(tmp, "image"), [])
            clips = [{"clip_id": f"Clip_{i:02d}"} for i in range(1, 13)]
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": clips}, f, ensure_ascii=False)
            # 有 clip_plan、未跑 → 提示先跑（advisory）
            self.assertTrue(any("drift_risk" in w for w in gate._drift_risk_warnings(tmp, "image")))
            # 报告有 high → warn；hash 一致不报过期
            plan_hash = mv_utils.content_hash(os.path.join(tmp, "分镜", "clip_plan.json"))
            dr = os.path.join(tmp, "生产数据", "drift_risk", "drift_risk.json")
            os.makedirs(os.path.dirname(dr), exist_ok=True)
            with open(dr, "w", encoding="utf-8") as f:
                json.dump({"inputs_sha256": {"分镜/clip_plan.json": plan_hash},
                           "summary": {"high": 2}}, f, ensure_ascii=False)
            warnings = gate._drift_risk_warnings(tmp, "image")
            self.assertTrue(any("high 风险" in w for w in warnings))
            self.assertFalse(any("过期" in w for w in warnings))
            # clip_plan 变化 → 过期提示（仍只是 warning）
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": clips + [{"clip_id": "Clip_99"}]}, f, ensure_ascii=False)
            self.assertTrue(any("过期" in w for w in gate._drift_risk_warnings(tmp, "image")))

    def test_craft_audit_advisory_never_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            self.assertEqual(gate._craft_audit_warnings(tmp, "image"), [])  # 无 clip_plan → 静默
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": [{"clip_id": "Clip_01"}]}, f, ensure_ascii=False)
            self.assertTrue(any("craft_audit" in w for w in gate._craft_audit_warnings(tmp, "image")))
            plan_hash = mv_utils.content_hash(os.path.join(tmp, "分镜", "clip_plan.json"))
            ca = os.path.join(tmp, "生产数据", "craft_audit", "craft_audit.json")
            os.makedirs(os.path.dirname(ca), exist_ok=True)
            with open(ca, "w", encoding="utf-8") as f:
                json.dump({"inputs_sha256": {"分镜/clip_plan.json": plan_hash},
                           "summary": {"warn": 2},
                           "findings": [{"severity": "warn", "code": "chorus_no_escalation"},
                                        {"severity": "warn", "code": "no_dynamics_contrast"}]},
                          f, ensure_ascii=False)
            warnings = gate._craft_audit_warnings(tmp, "image")
            self.assertTrue(any("chorus_no_escalation" in w for w in warnings))
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": [{"clip_id": "Clip_01"}, {"clip_id": "Clip_02"}]}, f, ensure_ascii=False)
            self.assertTrue(any("过期" in w for w in gate._craft_audit_warnings(tmp, "image")))

    def test_pilot_matrix_advisory_formal_big_project_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            settings_path = os.path.join(tmp, "_设置.md")
            settings_text = mv_utils.read_text(settings_path).replace("MV用途: 歌曲Demo", "MV用途: 正式MV")
            with open(settings_path, "w", encoding="utf-8") as handle:
                handle.write(settings_text)
            small = [{"clip_id": f"Clip_{i:02d}"} for i in range(1, 5)]
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": small}, f, ensure_ascii=False)
            # 小盘不打扰
            self.assertEqual(gate._pilot_matrix_warnings(tmp, "image", {"is_demo": False}), [])
            big = [{"clip_id": f"Clip_{i:02d}"} for i in range(1, 13)]
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": big}, f, ensure_ascii=False)
            # settings-first：传入的 meta demo 标志不能覆盖 _设置.md 的正式用途。
            self.assertTrue(any("打样" in w for w in gate._pilot_matrix_warnings(tmp, "image", {"is_demo": False})))
            self.assertTrue(gate._pilot_matrix_warnings(tmp, "image", {"is_demo": True}))
            # 有绑定当前 clip_plan 的矩阵 → 安静；clip_plan 变化 → 过期
            plan_hash = mv_utils.content_hash(os.path.join(tmp, "分镜", "clip_plan.json"))
            pm = os.path.join(tmp, "生产数据", "pilot_matrix", "pilot_matrix.json")
            os.makedirs(os.path.dirname(pm), exist_ok=True)
            with open(pm, "w", encoding="utf-8") as f:
                json.dump({"inputs_sha256": {"分镜/clip_plan.json": plan_hash}, "probes": []}, f, ensure_ascii=False)
            self.assertEqual(gate._pilot_matrix_warnings(tmp, "image", {"is_demo": False}), [])
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": big + [{"clip_id": "Clip_99"}]}, f, ensure_ascii=False)
            self.assertTrue(any("过期" in w for w in gate._pilot_matrix_warnings(tmp, "image", {"is_demo": False})))


if __name__ == "__main__":
    unittest.main()
