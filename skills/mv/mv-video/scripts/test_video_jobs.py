#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""video_jobs.py tests.

Can run without pytest:
    python3 skills/mv/mv-video/scripts/test_video_jobs.py
"""
import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(HERE, "video_jobs.py")
SPEC = importlib.util.spec_from_file_location("mv_video_jobs_test", JOBS)
video_jobs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(video_jobs)


def make_project(root):
    for sub in ("分镜", "歌", "词", "节拍", "出图/段落/图片"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# _设置\n\n## 选择\n- 生视频AI: manual\n- 出视频规格: 预算一般\n")
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试MV", "song_timing": "先传音乐", "has_song": True, "has_lyrics": True, "song_rights_status": "owned", "is_demo": True}, f, ensure_ascii=False)
    with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
        f.write("# 视觉蓝图\n")
    with open(os.path.join(root, "歌", "song.wav"), "wb") as f:
        f.write(b"fake wav")
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[verse1]\n一句歌词\n")
    with open(os.path.join(root, "节拍", "beatgrid.json"), "w", encoding="utf-8") as f:
        json.dump({"duration": 6, "beats": [1, 2, 3], "downbeats": [1, 3], "timing_verified": True}, f, ensure_ascii=False)
    clips = [
        {
            "clip_id": "Clip_001",
            "section": "verse1",
            "start": 0,
            "end": 4,
            "duration": 4,
            "beat_role": "normal",
            "image_path": "出图/段落/图片/Clip_001.png",
            "selected_video_path": "出视频/视频/Clip_001.mp4",
            "transition": "动作切",
            "continuity": {"action": "缓推", "start_state": "开始", "end_state": "结束"},
        },
        {
            "clip_id": "Clip_002",
            "section": "chorus",
            "start": 4,
            "end": 6,
            "duration": 2,
            "beat_role": "key",
            "action_family": "dance_hit/vfx_burst",
            "image_path": "出图/段落/图片/Clip_002.png",
            "selected_video_path": "出视频/视频/Clip_002.mp4",
            "transition": "卡点硬切",
            "continuity": {"action": "爆点", "start_state": "开始", "end_state": "结束"},
        },
    ]
    with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试MV", "clips": clips}, f, ensure_ascii=False)
    with open(os.path.join(root, "分镜", "timeline_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试MV", "clips": [{
            "clip_id": c["clip_id"], "start": c["start"], "end": c["end"],
            "duration": c["duration"], "video_path": c["selected_video_path"],
        } for c in clips]}, f, ensure_ascii=False)
    for clip in clips:
        with open(os.path.join(root, clip["image_path"]), "wb") as f:
            f.write(b"fake png")
    qc_dir = os.path.join(root, "生产数据", "image_qc")
    os.makedirs(qc_dir, exist_ok=True)
    with open(os.path.join(qc_dir, "image_qc.json"), "w", encoding="utf-8") as f:
        json.dump({
            "kind": "mv_image_qc",
            "summary": {"hard_blocks": 0, "advisory": 0, "verdict": "ok"},
            "qc_environment": {"precision_level": "full"},
        }, f, ensure_ascii=False)


class VideoJobsTest(unittest.TestCase):
    def test_multi_shot_capability_emits_sequence_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            clips = []
            for index in range(2):
                clips.append({
                    "clip_id": f"Clip_{index + 1:03d}", "section": "verse", "duration": 3,
                    "image_path": f"出图/段落/图片/Clip_{index + 1:03d}.png",
                    "shot_design": {"setup_group": "verse/stage", "camera_movement": "slow push"},
                    "continuity": {"action": "perform", "end_state": "hold"},
                })
            units = video_jobs.sequence_units(
                tmp, clips, "Seedance 2.0", "即梦/Dreamina",
                {"multi_shot": True, "max_sequence_seconds": 15},
            )
            self.assertEqual(len(units), 1)
            self.assertEqual(units[0]["clip_ids"], ["Clip_001", "Clip_002"])
            self.assertTrue(os.path.exists(os.path.join(tmp, units[0]["prompt_path"])))

    def test_sequence_unit_never_crosses_model_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            clips = [
                {"clip_id": "Clip_001", "section": "verse", "duration": 3,
                 "video_model": "Seedance 2.0", "video_channel": "即梦/Dreamina",
                 "shot_design": {"setup_group": "verse/stage"},
                 "continuity": {"action": "perform", "end_state": "hold"}},
                {"clip_id": "Clip_002", "section": "verse", "duration": 3,
                 "video_model": "Kling 3.0", "video_channel": "可灵/Kling",
                 "shot_design": {"setup_group": "verse/stage"},
                 "continuity": {"action": "perform", "end_state": "hold"}},
            ]
            units = video_jobs.sequence_units(
                tmp, clips, "Seedance 2.0", "即梦/Dreamina",
                {"multi_shot": True, "max_sequence_seconds": 15},
            )
            self.assertEqual(units, [])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg unavailable")
    def test_register_sequence_splits_back_into_take_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# _设置\n\n## 选择\n- 生视频模型: Seedance 2.0\n- 生视频渠道: 即梦\n- 出视频规格: 预算一般\n")
            plan_path = os.path.join(tmp, "分镜", "clip_plan.json")
            plan = json.load(open(plan_path, encoding="utf-8"))
            for index, clip in enumerate(plan["clips"]):
                clip.update({
                    "section": "verse1", "start": index * 0.25, "end": (index + 1) * 0.25,
                    "duration": 0.25, "shot_design": {"setup_group": "verse1/stage"},
                    "continuity": {"action": "perform", "end_state": "hold"},
                })
            json.dump(plan, open(plan_path, "w", encoding="utf-8"), ensure_ascii=False)
            timeline_path = os.path.join(tmp, "分镜", "timeline_manifest.json")
            json.dump({"clips": [
                {"clip_id": clip["clip_id"], "section": clip["section"], "start": clip["start"],
                 "end": clip["end"], "duration": clip["duration"],
                 "video_path": clip["selected_video_path"]}
                for clip in plan["clips"]
            ]}, open(timeline_path, "w", encoding="utf-8"), ensure_ascii=False)
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            source = os.path.join(tmp, "sequence.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                "-i", "color=c=red:s=320x180:r=24:d=0.5", "-an",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", source,
            ], check=True)
            subprocess.run([
                sys.executable, JOBS, tmp, "--register-sequence", source,
                "--unit", "Sequence_001", "--take", "1",
            ], capture_output=True, text=True, check=True)
            manifest = json.load(open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8"))
            self.assertEqual(manifest["sequence_units"][0]["status"], "split_registered")
            self.assertEqual(len(manifest["sequence_units"][0]["registrations"]), 2)
            for job in manifest["jobs"]:
                take = job["takes"][0]
                self.assertTrue(os.path.isfile(os.path.join(tmp, take["video_path"])))
                self.assertEqual(len(take["video_sha256"]), 64)

    def test_continuous_and_vocal_take_requires_extra_scores(self):
        take = {"score": {"motion": 5, "identity": 5, "beat_fit": 5, "clarity": 5}, "scored_by": "editor"}
        errors = video_jobs.selection_errors(take, {
            "seam_contract": {"continuity_required": True}, "lip_sync_required": True,
        })
        self.assertTrue(any("seam_fit" in error for error in errors))
        self.assertTrue(any("lip_sync" in error for error in errors))

    def test_creates_jobs_and_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            path = os.path.join(tmp, "出视频", "jobs_manifest.json")
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(len(manifest["jobs"]), 2)
            self.assertEqual(manifest["jobs"][0]["requested_takes"], 1)
            self.assertEqual(manifest["jobs"][1]["requested_takes"], 2)
            self.assertEqual(manifest["schema_version"], 3)
            take = manifest["jobs"][1]["takes"][0]
            prompt = take["prompt_path"]
            self.assertTrue(os.path.exists(os.path.join(tmp, prompt)))
            self.assertEqual(take["prompt_source_kind"], "compiled_submit_prompt")
            self.assertEqual(take["prompt_compiler"]["native_audio_policy"], "external_song_track")
            self.assertNotIn("identity_registry", take["submit_prompt"])
            with open(os.path.join(tmp, prompt), encoding="utf-8") as f:
                prompt_text = f.read()
            self.assertIn("### 后端编译提交 prompt", prompt_text)
            self.assertIn(take["submit_prompt"], prompt_text)

    def test_legacy_single_axis_backend_maps_to_explicit_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# _设置\n\n## 选择\n- 生视频AI: 即梦\n- 出视频规格: 预算一般\n")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["video_model"], "Seedance 2.0")
            self.assertEqual(manifest["video_channel"], "即梦")

    def test_quality_tier_and_motion_reference_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            # 用支持质量档 + 视频运动参考的渠道（可灵/Kling）覆盖默认 manual
            subprocess.run([sys.executable, JOBS, tmp, "--backend", "可灵/Kling"],
                           capture_output=True, text=True, check=True)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            verse, chorus = manifest["jobs"][0], manifest["jobs"][1]
            # verse 铺垫镜 → fast；副歌镜 → high
            self.assertEqual(verse["quality_tier"], "fast")
            self.assertEqual(chorus["quality_tier"], "high")
            # 副歌舞蹈镜 + 支持视频参考的后端 → applicable；verse 非舞蹈镜 → not applicable
            self.assertTrue(chorus["motion_reference"]["applicable"])
            self.assertFalse(verse["motion_reference"]["applicable"])

    def test_quality_tier_na_on_backend_without_tier(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            # 默认 manual 渠道无质量档 → n/a；无视频参考能力 → motion not applicable
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["jobs"][1]["quality_tier"], "n/a")
            self.assertFalse(manifest["jobs"][1]["motion_reference"]["applicable"])

    def test_register_score_select(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1"], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--score", "Clip_001", "--take", "1", "--motion-score", "5", "--identity-score", "4", "--beat-score", "5", "--clarity-score", "4", "--reviewer", "editor"], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--select", "Clip_001", "--take", "1"], capture_output=True, text=True, check=True)
            self.assertTrue(os.path.exists(os.path.join(tmp, "出视频", "视频", "Clip_001.mp4")))
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["jobs"][0]["selected_take"], "take_01")
            self.assertEqual(manifest["jobs"][0]["takes"][0]["score"]["motion"], 5)

    def test_register_records_frame_binding_and_generation_params(self):
        """登记时落首帧内容 SHA（出图→出视频像素级绑定）+ seed/参数留痕。"""
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                            "--seed", "42", "--generation-param", "cfg=7.5",
                            "--provider-job-id", "job_abc"], capture_output=True, text=True, check=True)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                take = json.load(f)["jobs"][0]["takes"][0]
            import hashlib
            expected = hashlib.sha256(b"fake png").hexdigest()
            self.assertEqual(take["first_frame_sha256"], expected)
            self.assertEqual(take["generation"]["seed"], "42")
            self.assertEqual(take["generation"]["params"], {"cfg": "7.5"})
            self.assertEqual(take["generation"]["provider_job_id"], "job_abc")

    def test_register_rejects_malformed_generation_param(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            proc = subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1",
                                   "--take", "1", "--generation-param", "cfg"],
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("K=V", proc.stderr)

    def test_rescore_average_does_not_include_previous_average(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"take")
            subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1"], capture_output=True, text=True, check=True)
            base = [sys.executable, JOBS, tmp, "--score", "Clip_001", "--take", "1", "--reviewer", "editor"]
            subprocess.run(base + ["--motion-score", "5", "--identity-score", "5", "--beat-score", "5", "--clarity-score", "5"], capture_output=True, text=True, check=True)
            subprocess.run(base + ["--motion-score", "1"], capture_output=True, text=True, check=True)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                score = json.load(f)["jobs"][0]["takes"][0]["score"]
            self.assertEqual(score["average"], 4.0)

    def test_reregistering_selected_take_invalidates_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"take-v1")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1"], capture_output=True, text=True, check=True)
            subprocess.run([
                sys.executable, JOBS, tmp, "--score", "1", "--take", "1",
                "--motion-score", "5", "--identity-score", "5", "--beat-score", "5",
                "--clarity-score", "5", "--reviewer", "editor",
            ], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--select", "1", "--take", "1"], capture_output=True, text=True, check=True)
            with open(src, "wb") as f:
                f.write(b"take-v2")
            subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1"], capture_output=True, text=True, check=True)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                job = json.load(f)["jobs"][0]
            self.assertIsNone(job["selected_take"])
            self.assertIn("re-registered", job["takes"][0]["selection_invalidated_reason"])

    def test_select_rejects_unscored_take(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1"], capture_output=True, text=True, check=True)
            proc = subprocess.run([sys.executable, JOBS, tmp, "--select", "1", "--take", "1"], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("评分缺字段", proc.stderr)

    def test_score_rejects_unregistered_take(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            proc = subprocess.run([
                sys.executable, JOBS, tmp, "--score", "1", "--take", "1",
                "--motion-score", "5", "--identity-score", "5", "--beat-score", "5",
                "--clarity-score", "5", "--reviewer", "editor",
            ], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("尚未 --register", proc.stderr)

    def test_selection_waiver_requires_named_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1"], capture_output=True, text=True, check=True)
            proc = subprocess.run([
                sys.executable, JOBS, tmp, "--select", "1", "--take", "1",
                "--waiver-reason", "director accepts rough motion",
            ], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("不能匿名", proc.stderr)


if __name__ == "__main__":
    unittest.main()
