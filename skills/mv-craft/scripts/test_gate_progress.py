#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate/progress tests.

Can run without pytest:
    python3 skills/mv-craft/scripts/test_gate_progress.py
"""
import json
import os
import tempfile
import unittest

import gate
import mv_utils


def make_project(root):
    for sub in ("歌", "词", "节拍", "分镜", "出图/段落/图片"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试", "song_timing": "先传音乐", "song_rights_status": "自有", "is_demo": True}, f, ensure_ascii=False)
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
        json.dump({"duration": 5, "beats": [1, 2], "downbeats": [1], "timing_verified": True}, f)
    with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
        f.write("# 视觉蓝图\n")


def write_clip_plan_with_image(root):
    os.makedirs(os.path.join(root, "出图", "段落", "图片"), exist_ok=True)
    with open(os.path.join(root, "出图", "段落", "图片", "Clip_001.png"), "wb") as f:
        f.write(b"fake")
    with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"clips": [{"clip_id": "Clip_001", "image_path": "出图/段落/图片/Clip_001.png"}]},
                  f, ensure_ascii=False)


def write_image_qc(root, hard=0, precision="full", advisory=0):
    path = os.path.join(root, "生产数据", "image_qc", "image_qc.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "kind": "mv_image_qc",
            "summary": {
                "hard_blocks": hard,
                "advisory": advisory,
                "verdict": "block" if hard else ("review" if advisory else "ok"),
            },
            "qc_environment": {"precision_level": precision},
        }, f, ensure_ascii=False)


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
                    "settings": mv_utils.content_hash(os.path.join(tmp, "_设置.md")),
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
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as handle:
                handle.write("# _设置\n\n## 选择\n- 字幕语言: 无字幕\n- 演唱口型: 关闭\n")
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
            errors, _warnings = gate.check(tmp, "video_jobs")
            self.assertTrue(any("image_qc" in e for e in errors))

    def test_video_jobs_blocks_image_qc_hard_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp, hard=1)
            errors, _warnings = gate.check(tmp, "video_jobs")
            self.assertTrue(any("hard block=1" in e for e in errors))

    def test_video_jobs_passes_full_image_qc(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_clip_plan_with_image(tmp)
            write_image_qc(tmp)
            errors, _warnings = gate.check(tmp, "video_jobs")
            self.assertEqual(errors, [])

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
            errors, _warnings = gate.check(tmp, "video_jobs")
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
            video = {"summary": {"hard_blocks": 0}, "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(tmp, rel)) for rel in video_inputs},
                     "selected_video_sha256": {video_rel: mv_utils.content_hash(os.path.join(tmp, video_rel))}}
            with open(os.path.join(tmp, "生产数据/video_inherit_contract/inherit_contract.json"), "w", encoding="utf-8") as f:
                json.dump(inherit, f)
            with open(os.path.join(tmp, "生产数据/video_qc/video_qc.json"), "w", encoding="utf-8") as f:
                json.dump(video, f)
            self.assertEqual(gate._video_report_errors(tmp, "compose"), [])
            with open(os.path.join(tmp, video_rel), "wb") as f:
                f.write(b"video-v2")
            self.assertTrue(any("已变化" in error for error in gate._video_report_errors(tmp, "compose")))

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
            errors, _warnings = gate.check(tmp, "video_jobs")
            self.assertTrue(any("旧式 manual_review_accepted" in e for e in errors))

    def test_degraded_image_qc_bound_manual_review_passes(self):
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
            errors, warnings = gate.check(tmp, "video_jobs")
            self.assertEqual(errors, [])
            self.assertTrue(any("具名人工放行" in w for w in warnings))
            # 报告内容变化（如重跑 QC）后绑定失效，必须重新放行
            report["summary"]["advisory"] = 5
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False)
            errors, _warnings = gate.check(tmp, "video_jobs")
            self.assertTrue(any("绑定 hash 与当前报告不符" in e for e in errors))

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
            self.assertEqual(errors, [])
            self.assertTrue(any("identity_registry" in w for w in warnings))
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
            self.assertEqual(gate._demo_flag_warnings(tmp, "image", {"is_demo": False}), [])

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
            small = [{"clip_id": f"Clip_{i:02d}"} for i in range(1, 5)]
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": small}, f, ensure_ascii=False)
            # 小盘不打扰
            self.assertEqual(gate._pilot_matrix_warnings(tmp, "image", {"is_demo": False}), [])
            big = [{"clip_id": f"Clip_{i:02d}"} for i in range(1, 13)]
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": big}, f, ensure_ascii=False)
            # 正式大盘未打样 → 提示；demo 不提示
            self.assertTrue(any("打样" in w for w in gate._pilot_matrix_warnings(tmp, "image", {"is_demo": False})))
            self.assertEqual(gate._pilot_matrix_warnings(tmp, "image", {"is_demo": True}), [])
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
