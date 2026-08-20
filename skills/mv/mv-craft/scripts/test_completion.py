#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Output completion receipt tests (no network/provider calls)."""
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from PIL import Image

import completion
import contract
import mv_utils
import release_decision
import progress_set


def write_json(root, rel, payload):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


def write_bytes(root, rel, value=b"asset"):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(value)
    return path


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def make_delivery_audio_identity(root, song, final, master):
    contract_name = "decoded_pcm_start_middle_end_correlation_v2"
    thresholds = {
        "minimum_correlation": 0.85,
        "maximum_abs_offset_ms": 50.0,
        "maximum_drift_ms": 30.0,
        "maximum_duration_delta_seconds": 0.10,
    }

    def output(role, rel, path):
        return {
            "role": role, "path": rel, "sha256": mv_utils.content_hash(path),
            "contract": contract_name, "sample_rate_hz": 8000,
            "thresholds": thresholds,
            "source_duration_seconds": 4.0, "output_duration_seconds": 4.0,
            "duration_delta_seconds": 0.0, "status": "ok",
            "anchors": [
                {"anchor": "start", "correlation": 1.0, "offset_ms": 0.0},
                {"anchor": "middle", "correlation": 1.0, "offset_ms": 0.0},
                {"anchor": "end", "correlation": 1.0, "offset_ms": 0.0},
            ],
            "min_correlation": 1.0, "max_abs_offset_ms": 0.0, "drift_ms": 0.0,
        }

    return {
        "schema_version": 1, "kind": "mv_delivery_audio_identity",
        "contract": contract_name,
        "source": {"path": "歌/song.wav", "sha256": mv_utils.content_hash(song)},
        "required_roles": ["final", "master"],
        "outputs": {
            "final": output("final", "成片_MV.mp4", final),
            "master": output("master", "成片_MV_master.mov", master),
        },
        "status": "ok",
    }


def make_settings(root, **overrides):
    settings = dict(contract.DEFAULT_SETTINGS)
    settings.update({"发行目标平台": "跨平台", "字幕语言": "无字幕", "演唱口型": "关闭"})
    settings.update(overrides)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as handle:
        handle.write(contract.settings_markdown("测试", settings))
    return settings


class ProgressSetGuardTest(unittest.TestCase):
    def test_receipt_health_omits_non_applicable_optional_alignment(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root, **{"字幕语言": "无字幕", "演唱口型": "关闭"})
            stages = [row["stage"] for row in completion.receipt_health(root)]
        self.assertNotIn("lyric_sync", stages)
        self.assertIn("beat", stages)

    def test_alternate_done_markers_use_output_completion_controller(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(sys, "argv", ["progress_set.py", root, "compose", "--status", "✅"]), \
                 mock.patch.object(progress_set.completion, "mark_stage_complete") as complete, \
                 mock.patch.object(progress_set.mv_utils, "update_progress_stage") as direct:
                self.assertEqual(progress_set.main(), 0)
            complete.assert_called_once_with(root, "compose", reviewer="", notes="")
            direct.assert_not_called()

    def test_fractional_done_marker_cannot_bypass_output_health(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(sys, "argv", ["progress_set.py", root, "video", "--status", "1/1"]), \
                 mock.patch.object(progress_set.completion, "mark_stage_complete", side_effect=ValueError("stale")), \
                 mock.patch.object(progress_set.mv_utils, "update_progress_stage") as direct:
                self.assertEqual(progress_set.main(), 2)
            direct.assert_not_called()

    def test_receipt_bearing_stage_done_cannot_bypass_output_health(self):
        controlled = ("beat", "lyric_sync", "plan", "pacing_check", "picture_lock")
        self.assertTrue(set(controlled).issubset(completion.CONTROLLED_COMPLETION_STAGES))
        for target in controlled:
            with self.subTest(stage=target), tempfile.TemporaryDirectory() as root:
                settings = make_settings(root, **{"字幕语言": "中文", "演唱口型": "仅正面演唱镜"})
                runtime = contract.runtime_state_from_settings(settings)
                stages = contract.workflow_stage_table(
                    runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"],
                )
                target_index = next(index for index, row in enumerate(stages) if row["key"] == target)
                rows = "\n".join(
                    f"| {row['label']} | {row['owner']} | {'[x]' if index < target_index else '[ ]'} |"
                    for index, row in enumerate(stages)
                )
                write_bytes(root, "_进度.md", (
                    "# 进度\n\n## 制MV 阶段\n| 阶段 | skill | 状态 |\n|---|---|---|\n" + rows + "\n"
                ).encode("utf-8"))
                with mock.patch.object(
                    sys, "argv", ["progress_set.py", root, target, "--status", "✅"],
                ), mock.patch.object(completion, "_predecessor_completion_errors", return_value=[]):
                    self.assertEqual(progress_set.main(), 2)
                row = next(item for item in completion._current_workflow_progress_rows(root) if item["key"] == target)
                self.assertFalse(completion._progress_status_done(row["status"]))

    def test_completion_rejects_skipping_compose_before_disclosure(self):
        with tempfile.TemporaryDirectory() as root:
            settings = make_settings(root)
            runtime = contract.runtime_state_from_settings(settings)
            stages = contract.workflow_stage_table(
                runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"],
            )
            rows = "\n".join(
                f"| {row['label']} | {row['owner']} | {'[ ]' if row['key'] in {'compose', 'disclosure'} else '[x]'} |"
                for row in stages
            )
            write_bytes(root, "_进度.md", (
                "# 进度\n\n## 制MV 阶段\n| 阶段 | skill | 状态 |\n|---|---|---|\n" + rows + "\n"
            ).encode("utf-8"))
            healthy = {"ok": True, "errors": [], "warnings": [], "evidence": {}}
            with mock.patch.object(completion, "stage_health", return_value=healthy):
                with self.assertRaisesRegex(ValueError, "前驱 stage=compose 尚未完成"):
                    completion.mark_stage_complete(root, "disclosure")
            disclosure = next(
                item for item in completion._current_workflow_progress_rows(root)
                if item["key"] == "disclosure"
            )
            self.assertFalse(completion._progress_status_done(disclosure["status"]))


def make_compose_chain(root):
    """Create a hash-current compose chain without probing fake media."""
    runtime = contract.runtime_state_from_settings(mv_utils.parse_settings(root))
    song = write_bytes(root, "歌/song.wav", b"song")
    selected_rel = "出视频/视频/Clip_001.mp4"
    selected = write_bytes(root, selected_rel, b"selected-video")
    timeline_rel = "分镜/timeline_manifest.json"
    timeline_path = write_json(root, timeline_rel, {
        "kind": "mv_timeline_manifest", "title": "测试", "rate": 24,
        "song_path": "歌/song.wav",
        "clips": [{"clip_id": "Clip_001", "section": "verse", "start": 0, "end": 4,
                   "duration": 4, "start_frame": 0, "end_frame": 96,
                   "duration_frames": 96, "video_path": selected_rel,
                   "transition": "cut", "speed_mode": "none", "seam_contract": {}}],
    })
    beat_rel = "节拍/beatgrid.json"
    beat_path = write_json(root, beat_rel, {"bpm": 120, "sections": []})
    otio_rel = "分镜/timeline.otio"
    otio_path = write_json(root, otio_rel, {
        "OTIO_SCHEMA": "Timeline.1", "name": "测试",
        "tracks": {"OTIO_SCHEMA": "Stack.1", "children": [
            {"OTIO_SCHEMA": "Track.1", "kind": "Video", "children": [{
                "OTIO_SCHEMA": "Clip.2",
                "source_range": {"OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0, "rate": 24.0},
                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": 96, "rate": 24.0}},
            }]},
            {"OTIO_SCHEMA": "Track.1", "kind": "Audio", "children": [{
                "OTIO_SCHEMA": "Clip.2",
                "source_range": {"OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0, "rate": 24.0},
                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": 96, "rate": 24.0}},
            }]},
        ]},
    })
    write_json(root, "生产数据/otio/otio_receipt.json", {
        "schema_version": 3, "kind": "mv_otio_export_receipt", "rate": 24.0,
        "timebase": {"unit": "frame", "integral_rational_time": True},
        "timeline_edit_sha256": mv_utils.timeline_edit_hash(read_json(timeline_path)),
        "inputs_sha256": {timeline_rel: mv_utils.content_hash(timeline_path),
                          beat_rel: mv_utils.content_hash(beat_path)},
        "media_sha256": {selected_rel: mv_utils.content_hash(selected),
                         "歌/song.wav": mv_utils.content_hash(song)},
        "tracks": {"video": 1, "audio": 1},
        "missing_media": [], "otio_sha256": mv_utils.content_hash(otio_path),
        "official_roundtrip": {"status": "ok", "library_version": "fixture"},
    })
    write_json(root, "生产数据/color/color_input_manifest.json", {
        "schema_version": 2, "kind": "mv_color_input_manifest",
        "output_space": "bt709_sdr_limited",
        "timeline_sha256": mv_utils.content_hash(timeline_path),
        "inputs_sha256": {selected_rel: mv_utils.content_hash(selected)},
        "inputs": [{"path": selected_rel, "sha256": mv_utils.content_hash(selected),
                    "classification": "declared_bt709_limited", "interpretation": "bt709_limited",
                    "ffmpeg_input_filter": "setparams=color_primaries=bt709:range=tv"}],
        "untagged_acceptance": None,
        "summary": {"hard_blocks": 0, "blocks": [], "verdict": "ok"},
    })
    final = write_bytes(root, "成片_MV.mp4", b"final-v1")
    master = write_bytes(root, "成片_MV_master.mov", b"master-v1")
    dimensions = {"16:9": [1920, 1080], "9:16": [1080, 1920], "1:1": [1080, 1080]}[runtime["aspect"]]
    delivery_rel = "生产数据/delivery_qc/delivery_qc.json"
    delivery_path = write_json(root, delivery_rel, {
        "schema_version": 3, "kind": "mv_delivery_qc",
        "summary": {"hard_blocks": 0, "warnings": 0, "verdict": "ok"},
        "expected_delivery": {"aspect": runtime["aspect"], "dimensions": dimensions},
        "audio_identity": make_delivery_audio_identity(root, song, final, master),
        "files": [
            {"role": "final", "path": "成片_MV.mp4", "sha256": mv_utils.content_hash(final),
             "blocks": [], "warnings": []},
            {"role": "master", "path": "成片_MV_master.mov", "sha256": mv_utils.content_hash(master),
             "blocks": [], "warnings": []},
        ],
        "inputs_sha256": {"成片_MV.mp4": mv_utils.content_hash(final),
                          "成片_MV_master.mov": mv_utils.content_hash(master),
                          "歌/song.wav": mv_utils.content_hash(song)},
    })
    return {"final": final, "master": master, "song": song, "selected": selected,
            "delivery_rel": delivery_rel, "delivery_path": delivery_path,
            "timeline_path": timeline_path, "otio_path": otio_path}


def make_ai_usage(root):
    runtime = contract.runtime_state_from_settings(mv_utils.parse_settings(root))
    rel = "合规/ai_usage.json"
    path = write_json(root, rel, {
        "schema_version": 2, "kind": "mv_ai_usage", "complete": True,
        "project_root": ".", "reviewer": "披露复核人",
        "human_contribution": "人工导演、挑版、剪辑与终审。",
        "visual_mode": runtime["ai_visual_usage"], "video_mode": runtime["ai_visual_usage"],
        "publish_target": runtime["publish_target"], "territories": ["CN"],
        "realism": "stylized", "real_person_status": "none", "music_mode": "human",
        "gen_ai_classification": "partly_gen_ai", "image_model": runtime["image_model"],
        "image_channel": runtime["image_channel"], "video_model": runtime["video_model"],
        "video_channel": runtime["video_channel"],
        "inputs_sha256": {"_设置.md": mv_utils.content_hash(os.path.join(root, "_设置.md"))},
    })
    return rel, path


def make_provenance(root, ai_rel, ai_path):
    final = os.path.join(root, "成片_MV.mp4")
    master = os.path.join(root, "成片_MV_master.mov")
    c2pa_manifest = write_json(root, "合规/c2pa_manifest.json", {"claim_generator": "fixture"})
    asset_rels = completion.provenance_contract.existing_assets(root, final, master)
    ingredients = [rel for rel in asset_rels if rel not in {"成片_MV.mp4", "成片_MV_master.mov"}]
    rel = "合规/provenance.json"
    path = write_json(root, rel, {
        "schema_version": 2, "kind": "mv_provenance", "complete": True,
        "assets": [{"path": item, "sha256": mv_utils.content_hash(os.path.join(root, item))}
                   for item in asset_rels],
        "relationships": {"final": "成片_MV.mp4", "master": "成片_MV_master.mov",
                          "ingredients": ingredients, "disclosure": ai_rel},
        "inputs_sha256": {item: mv_utils.content_hash(os.path.join(root, item)) for item in ingredients},
        "ai_usage": read_json(ai_path), "ai_usage_sha256": mv_utils.content_hash(ai_path),
        "c2pa": {"requested": False, "embedded": False, "structurally_valid": False,
                 "signature_valid": False, "trust_checked": False, "trusted": False,
                 "timestamp_validated": False, "timestamp_trusted": False,
                 "timestamped": False, "timestamp_exception_allowed": False,
                 "certificate_profile": None,
                 "manifest_sha256": mv_utils.content_hash(c2pa_manifest)},
    })
    return rel, path


def video_clip():
    return {
        "clip_id": "Clip_001", "section": "verse", "start": 0, "end": 4,
        "duration": 4, "beat_role": "normal", "image_path": "出图/Clip_001.png",
        "need_end_frame": False, "reference_inputs": [],
        "continuity": {"start_state": "站立", "action": "缓慢转头", "end_state": "看向镜头",
            "constraints": ["same person"], "negative": ["identity drift"],
            "identity_state": "lead", "wardrobe_state": "look_a", "prop_state": "none",
            "scene_topology": "stage_a", "screen_direction": "left_to_right", "eyeline": "camera",
            "motion_vector": "slow", "lighting_state": "blue_key"},
        "identity_contract": {"lead_identity_anchor": "主唱·lead"},
        "shot_design": {"camera_movement": "中景缓推", "lighting": "蓝色主光"},
    }


def make_video_jobs(root):
    make_settings(root)
    stages = contract.workflow_stage_table("先传音乐", "无字幕", "关闭")
    rows = "\n".join(
        f"| {stage['label']} | {stage['owner']} | [ ] |" for stage in stages
    )
    write_bytes(root, "_进度.md", (
        "# 进度\n\n## 制MV 阶段\n| 阶段 | skill | 状态 |\n|---|---|---|\n" + rows + "\n"
    ).encode("utf-8"))
    write_bytes(root, "出图/Clip_001.png", b"first-frame")
    write_json(root, "生产数据/image_qc/image_qc.json", {"kind": "fixture_image_qc"})
    write_json(root, "分镜/clip_plan.json", {"kind": "mv_clip_plan", "title": "测试", "clips": [video_clip()]})
    write_json(root, "设定/identity_registry.json", {"kind": "mv_identity_registry", "subjects": []})
    write_json(root, "分镜/reference_plan.json", {"kind": "mv_reference_plan", "clips": []})
    video_jobs, inherit = completion._load_video_authorities()
    video_jobs.mv_gate.check = lambda _root, _stage: ([], [])
    controller = SimpleNamespace(mark_stage_complete=lambda *_args, **_kwargs: None)
    with mock.patch.object(video_jobs, "load_completion", return_value=controller):
        _path, manifest = video_jobs.create_jobs(root, SimpleNamespace(adapter_record="", backend="", video_spec=""))
    return video_jobs, inherit, manifest


def make_selected_video(root):
    video_jobs, inherit, _manifest = make_video_jobs(root)
    manifest_path = os.path.join(root, "出视频", "jobs_manifest.json")
    manifest = read_json(manifest_path)
    job, take = manifest["jobs"][0], manifest["jobs"][0]["takes"][0]
    receipt = video_jobs.receipt_template(job, take)
    receipt.update({"template_only": False, "provider_job_id": "provider-job-001",
                    "provider_status": "succeeded",
                    "submitted_at": "2026-08-20T12:00:00+08:00"})
    source = write_bytes(root, "tmp/generated.mp4", b"generated-video")
    source_sha = mv_utils.content_hash(source)
    evidence_rel = "出视频/provider_evidence/Clip_001_take_01.png"
    evidence_path = os.path.join(root, evidence_rel)
    os.makedirs(os.path.dirname(evidence_path), exist_ok=True)
    Image.new("RGB", (32, 32), (16, 32, 64)).save(evidence_path)
    route = take.get("provider_route") or job.get("provider_route") or {}
    receipt["provider_evidence"] = {
        "schema_version": 2, "kind": "provider_ui_capture", "execution_transport": "web",
        "adapter_id": "named_ui_observation.v1",
        "route_sha256": route.get("route_sha256") or "",
        "path": evidence_rel, "sha256": mv_utils.content_hash(evidence_path),
        "ui_observation": {
            "reviewer": "视频登记人", "notes": "已在提供方任务页核对成功状态与输出",
            "observed_at": receipt["submitted_at"], "submitted_at": receipt["submitted_at"],
            "provider_id": route.get("provider_id"),
            "provider_job_id": receipt["provider_job_id"], "model": receipt["model"],
            "status": "succeeded", "capture_method": "browser_screenshot",
        },
        "selected_asset": {"sha256": source_sha, "bound_by": "视频登记人",
                           "notes": "已核对当前登记视频就是提供方页面所示输出"},
    }
    normalized, evidence_errors = video_jobs.provider_evidence.validate_provider_evidence(
        root, route, receipt, source_sha,
    )
    if evidence_errors:
        raise AssertionError(evidence_errors)
    receipt["provider_evidence"] = normalized
    for row in receipt["submitted_refs"]:
        row["confirmed_submitted"] = True
    receipt_path = write_json(root, "出视频/receipts/actual.submit.json", receipt)
    video_jobs.register_take(root, "Clip_001", "take_01", source, submit_receipt=receipt_path)
    manifest = read_json(manifest_path)
    job, take = manifest["jobs"][0], manifest["jobs"][0]["takes"][0]
    take.update({"status": "selected", "score": {"motion": 5, "identity": 5, "beat_fit": 5,
                 "clarity": 5, "average": 5}, "scored_by": "挑版人", "scored_at": "2026-08-20"})
    job.update({"selected_take": "take_01", "selected_at": "2026-08-20"})
    selected_rel = job["selected_video_path"]
    selected_path = os.path.join(root, selected_rel)
    os.makedirs(os.path.dirname(selected_path), exist_ok=True)
    shutil.copyfile(os.path.join(root, take["video_path"]), selected_path)
    write_json(root, "出视频/jobs_manifest.json", manifest)
    timeline_path = write_json(root, "分镜/timeline_manifest.json", {
        "kind": "mv_timeline_manifest", "rate": 24,
        "clips": [{"clip_id": "Clip_001", "start": 0, "end": 4, "duration": 4,
                   "duration_frames": 96, "video_path": selected_rel, "seam_contract": {}}],
    })
    write_json(root, "生产数据/video_inherit_contract/inherit_contract.json", inherit.build_report(root))
    selected_hashes = {selected_rel: mv_utils.content_hash(selected_path)}
    write_json(root, "生产数据/video_qc/video_qc.json", {
        "schema_version": 2, "kind": "mv_video_qc",
        "summary": {"hard_blocks": 0, "warnings": 0, "verdict": "ok"},
        "inputs_sha256": {"分镜/clip_plan.json": mv_utils.content_hash(os.path.join(root, "分镜", "clip_plan.json")),
                          "分镜/timeline_manifest.json": mv_utils.content_hash(timeline_path)},
        "selected_video_sha256": selected_hashes, "seams": [],
        "semantic_review": {"accepted": True, "reviewer": "总审人", "notes": "逐镜与逐缝复核",
            "bound_video_sha256": selected_hashes, "bound_seam_contract_sha256": mv_utils.json_hash([])},
    })
    return video_jobs, inherit


class CompletionHealthTest(unittest.TestCase):
    def test_settings_first_missing_settings_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            health = completion.stage_health(root, "semantic_plan")
            self.assertFalse(health["ok"])
            self.assertTrue(any("settings-first" in m or "_设置.md" in m for m in health["errors"]))

    def test_semantic_health_requires_v3_complete_and_current_prompt_outputs(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            image_prompt = write_bytes(root, "出图/段落/prompt/Clip_001.md", b"image prompt")
            video_prompt = write_bytes(root, "出视频/prompt/Clip_001.md", b"video prompt")
            plan_path = write_json(root, "分镜/clip_plan.json", {
                "clips": [{"clip_id": "Clip_001",
                           "image_prompt_path": "出图/段落/prompt/Clip_001.md",
                           "video_prompt_path": "出视频/prompt/Clip_001.md"}],
            })
            receipt_rel = "分镜/semantic_prompts.json"
            receipt = {
                "schema_version": 3, "kind": "mv_semantic_prompts", "complete": True,
                "updated_clips": 1, "result_clip_plan_sha256": mv_utils.content_hash(plan_path),
                "inputs_sha256": {}, "clips": [{"clip_id": "Clip_001"}],
                "prompt_outputs_sha256": {"Clip_001": {
                    "image": mv_utils.content_hash(image_prompt),
                    "video": mv_utils.content_hash(video_prompt),
                }},
            }
            write_json(root, receipt_rel, receipt)
            self.assertTrue(completion.stage_health(root, "semantic_plan")["ok"])
            write_bytes(root, "出视频/prompt/Clip_001.md", b"changed")
            stale = completion.stage_health(root, "semantic_plan")
            self.assertTrue(any("video prompt" in message for message in stale["errors"]))
            receipt["complete"] = False
            write_json(root, receipt_rel, receipt)
            partial = completion.stage_health(root, "semantic_plan")
            self.assertTrue(any("complete" in message for message in partial["errors"]))

    def test_lipsync_requires_alignment_at_video_and_compose_even_without_subtitles(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root, **{"字幕语言": "无字幕", "演唱口型": "仅正面演唱镜"})
            video = completion.stage_health(root, "video")
            self.assertTrue(any("alignment_report" in message for message in video["errors"]))
            make_compose_chain(root)
            compose = completion.stage_health(root, "compose")
            self.assertTrue(any("alignment_report" in message for message in compose["errors"]))

    def test_image_health_binds_current_pixels_and_b14_aggregate(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            image_rel, prompt_rel = "出图/段落/图片/Clip_001.png", "出图/段落/prompt/Clip_001.txt"
            write_bytes(root, prompt_rel, b"draw a blue frame")
            write_json(root, "分镜/clip_plan.json", {"clips": [{"clip_id": "Clip_001", "image_path": image_rel}]})
            receipts = completion._load_image_receipts()
            receipts.create_preflight(Path(root), asset=image_rel, asset_kind="clip_start", owner="Clip_001",
                use="start_frame", identity_scope="no_identity", model="local:test-model",
                channel="local", prompt=prompt_rel, reference_specs=[])
            image_path = os.path.join(root, image_rel)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            Image.new("RGB", (32, 32), (0, 0, 255)).save(image_path)
            image_sha = mv_utils.content_hash(image_path)
            submitted = receipts.record_submission(Path(root), asset=image_rel, model="local:test-model",
                                                    channel="local", prompt=prompt_rel, references=[])
            qc_rel = "生产数据/image_qc/image_qc.json"
            write_json(root, qc_rel, {"version": 3, "kind": "mv_image_qc",
                "summary": {"hard_blocks": 0, "verdict": "ok"},
                "qc_environment": {"precision_level": "full"}, "assets_sha256": {image_rel: image_sha},
                "asset_integrity": {"rows": [{"png": image_rel, "verdict": "ok"}]},
                "generation_provenance": {"complete": True, "summary": {"block": 0, "ok": 1},
                    "rows": [{"png": image_rel, "verdict": "ok",
                    "b14_attempt_id": submitted["attempt_id"],
                    "b14_preflight_sha256": submitted["preflight_sha256"],
                    "b14_submission_sha256": submitted["submission"]["receipt_sha256"]}]}})
            receipts.record_postflight(Path(root), asset=image_rel, qc_report=qc_rel, reviewer="审图人",
                                       visual_verdict="pass", notes="逐图并排确认当前像素")
            self.assertTrue(completion.stage_health(root, "image")["ok"])
            Image.new("RGB", (32, 32), (255, 0, 0)).save(image_path)
            stale = completion.stage_health(root, "image")
            self.assertFalse(stale["ok"])
            self.assertTrue(any("已过期" in m for m in stale["errors"]))

    def test_video_jobs_requires_schema4_exact_coverage_capability_and_freshness(self):
        with tempfile.TemporaryDirectory() as root:
            _video_jobs, _inherit, manifest = make_video_jobs(root)
            health = completion.stage_health(root, "video_jobs")
            self.assertTrue(health["ok"], health["errors"])
            manifest["jobs"] = []
            write_json(root, "出视频/jobs_manifest.json", manifest)
            health = completion.stage_health(root, "video_jobs")
            self.assertTrue(any("覆盖不完整" in m for m in health["errors"]))

    def test_legacy_video_jobs_is_readable_but_not_complete(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            plan = write_json(root, "分镜/clip_plan.json", {"clips": [{"clip_id": "Clip_001"}]})
            write_json(root, "出视频/jobs_manifest.json", {"schema_version": 3, "kind": "mv_video_jobs",
                "clip_plan_sha256": mv_utils.content_hash(plan), "jobs": [{"clip_id": "Clip_001"}]})
            health = completion.stage_health(root, "video_jobs")
            self.assertTrue(any("schema v4" in m for m in health["errors"]))

    def test_video_health_requires_current_submit_receipt_and_inherit_report(self):
        with tempfile.TemporaryDirectory() as root:
            make_selected_video(root)
            health = completion.stage_health(root, "video")
            self.assertTrue(health["ok"], health["errors"])
            write_bytes(root, "出图/Clip_001.png", b"changed-frame")
            stale = completion.stage_health(root, "video")
            self.assertFalse(stale["ok"])
            self.assertTrue(any("submitted_reference_changed" in m or "freshness" in m for m in stale["errors"]))

    def test_video_health_rejects_invalid_sequence_cut_map(self):
        with tempfile.TemporaryDirectory() as root:
            make_selected_video(root)
            manifest_path = os.path.join(root, "出视频", "jobs_manifest.json")
            manifest = read_json(manifest_path)
            manifest["sequence_units"] = [{"unit_id": "Sequence_001", "status": "split_registered",
                "compiled_request_controls": {}, "compiled_request_controls_sha256": mv_utils.json_hash({}),
                "submit_receipt": {"kind": "mv_video_sequence_submit_receipt"},
                "verified_cut_map": {"kind": "mv_video_sequence_cut_map", "reviewer": "审片人"}}]
            write_json(root, "出视频/jobs_manifest.json", manifest)
            health = completion.stage_health(root, "video")
            self.assertTrue(any("sequence_cut_map_invalid" in m for m in health["errors"]))

    def test_alignment_never_treats_text_coverage_as_acoustic_confidence(self):
        with tempfile.TemporaryDirectory() as root:
            write_bytes(root, "歌/song.wav", b"song")
            write_bytes(root, "词/lyrics.md", "歌词".encode("utf-8"))
            write_bytes(root, "字幕/karaoke.ass", b"ass")
            write_bytes(root, "字幕/lyrics.lrc", b"lrc")
            inputs = {"歌/song.wav": mv_utils.content_hash(os.path.join(root, "歌", "song.wav")),
                      "词/lyrics.md": mv_utils.content_hash(os.path.join(root, "词", "lyrics.md"))}
            outputs = {"字幕/karaoke.ass": mv_utils.content_hash(os.path.join(root, "字幕", "karaoke.ass")),
                       "字幕/lyrics.lrc": mv_utils.content_hash(os.path.join(root, "字幕", "lyrics.lrc"))}
            report = {
                "schema_version": 5, "kind": "mv_lyric_alignment_report", "alignment_unit": "character",
                "coverage_metric": "text_character_mapping_ratio_not_acoustic_confidence",
                "master_song": "歌/song.wav", "audio": "歌/song.wav",
                "character_coverage_ratio": 1.0,
                "aligned_lines": 1, "lyric_lines": 1, "timing_issues": [],
                "lines": [{"line_character_coverage": 1.0}],
                "inputs_sha256": inputs, "outputs_sha256": outputs,
                "stem_master_timing": {
                    "schema_version": 1, "status": "pass", "method": "same_master_file",
                    "offset_seconds": 0.0, "drift_seconds": 0.0,
                    "bindings": {
                        "master": {"path": "歌/song.wav", "sha256": inputs["歌/song.wav"]},
                        "alignment_audio": {"path": "歌/song.wav", "sha256": inputs["歌/song.wav"]},
                    },
                },
            }
            binding = completion._alignment_acceptance_binding(root, report)
            report["acceptance"] = {"status": "pending", "accepted": False,
                                    "required_binding": binding}
            report_path = write_json(root, "字幕/alignment_report.json", report)
            errors, _warnings = completion._alignment_health(root)
            self.assertTrue(any("尚未" in m for m in errors))
            report = read_json(report_path)
            preaccept_file = "a" * 64
            report["manual_review"] = {
                "kind": "named_full_listening_review", "accepted": True, "verdict": "pass",
                "reviewer": "逐行听审人", "notes": "已逐行听审校正", "binding": binding,
                "bound_report_preaccept_sha256": binding["report_preaccept_content_sha256"],
                "bound_preaccept_report_file_sha256": preaccept_file,
                "bound_inputs_sha256": inputs, "bound_outputs_sha256": outputs,
            }
            report["acceptance"] = {
                "status": "accepted", "accepted": True, "route": "named_listening_review",
                "binding": binding, "bound_preaccept_report_file_sha256": preaccept_file,
                "evidence_content_sha256": mv_utils.json_hash(report["manual_review"]),
            }
            write_json(root, "字幕/alignment_report.json", report)
            self.assertEqual(completion._alignment_health(root)[0], [])
            report["manual_review"]["notes"] = "签收后篡改"
            write_json(root, "字幕/alignment_report.json", report)
            self.assertTrue(any("签收后变化" in error for error in completion._alignment_health(root)[0]))

    def test_compose_requires_integer_otio_roundtrip_color_and_delivery(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            chain = make_compose_chain(root)
            health = completion.stage_health(root, "compose")
            self.assertTrue(health["ok"], health["errors"])
            otio = read_json(chain["otio_path"])
            otio["tracks"]["children"][0]["children"][0]["source_range"]["duration"]["value"] = 95.5
            write_json(root, "分镜/timeline.otio", otio)
            receipt_path = os.path.join(root, "生产数据", "otio", "otio_receipt.json")
            receipt = read_json(receipt_path)
            receipt["otio_sha256"] = mv_utils.content_hash(chain["otio_path"])
            write_json(root, "生产数据/otio/otio_receipt.json", receipt)
            bad = completion.stage_health(root, "compose")
            self.assertTrue(any("非整数帧" in m for m in bad["errors"]))

    def test_compose_rejects_stale_or_blocked_color_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            chain = make_compose_chain(root)
            color_rel = "生产数据/color/color_input_manifest.json"
            color = read_json(os.path.join(root, color_rel))
            color["summary"] = {"hard_blocks": 1, "verdict": "block"}
            write_json(root, color_rel, color)
            blocked = completion.stage_health(root, "compose")
            self.assertTrue(any("color_input_manifest 未通过" in m for m in blocked["errors"]))
            color["summary"] = {"hard_blocks": 0, "verdict": "ok"}
            write_json(root, color_rel, color)
            write_bytes(root, "出视频/视频/Clip_001.mp4", b"changed-selected-video")
            stale = completion.stage_health(root, "compose")
            self.assertTrue(any("color_input_manifest 已过期" in m for m in stale["errors"]))

    def test_compose_rejects_unofficial_otio_and_stale_delivery(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            make_compose_chain(root)
            receipt_path = os.path.join(root, "生产数据", "otio", "otio_receipt.json")
            receipt = read_json(receipt_path)
            receipt["official_roundtrip"] = {"status": "unavailable"}
            write_json(root, "生产数据/otio/otio_receipt.json", receipt)
            self.assertTrue(any("官方" in m for m in completion.stage_health(root, "compose")["errors"]))
            receipt["official_roundtrip"] = {"status": "ok"}
            write_json(root, "生产数据/otio/otio_receipt.json", receipt)
            write_bytes(root, "成片_MV.mp4", b"final-v2")
            stale = completion.stage_health(root, "compose")
            self.assertTrue(any("delivery_qc.inputs_sha256 已过期" in m for m in stale["errors"]))

    def test_compose_rejects_absolute_or_stale_delivery_file_rows(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            chain = make_compose_chain(root)
            payload = read_json(chain["delivery_path"])
            payload["files"][0]["path"] = chain["final"]
            write_json(root, chain["delivery_rel"], payload)
            errors = completion.stage_health(root, "compose")["errors"]
            self.assertTrue(any("files.final" in message and "相对路径" in message for message in errors), errors)
            payload["files"][0]["path"] = "成片_MV.mp4"
            payload["files"][0]["sha256"] = "0" * 64
            write_json(root, chain["delivery_rel"], payload)
            errors = completion.stage_health(root, "compose")["errors"]
            self.assertTrue(any("files.final" in message and "SHA-256" in message for message in errors), errors)

    def test_compose_requires_current_ok_pcm_identity_for_final_and_master(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            chain = make_compose_chain(root)
            pristine = read_json(chain["delivery_path"])
            self.assertTrue(completion.stage_health(root, "compose")["ok"])

            for role in ("final", "master"):
                with self.subTest(role=role, failure="missing"):
                    payload = json.loads(json.dumps(pristine))
                    del payload["audio_identity"]["outputs"][role]
                    write_json(root, chain["delivery_rel"], payload)
                    errors = completion.stage_health(root, "compose")["errors"]
                    self.assertTrue(any(role in message for message in errors), errors)
                with self.subTest(role=role, failure="not_ok"):
                    payload = json.loads(json.dumps(pristine))
                    payload["audio_identity"]["outputs"][role]["status"] = "mismatch"
                    write_json(root, chain["delivery_rel"], payload)
                    errors = completion.stage_health(root, "compose")["errors"]
                    self.assertTrue(any(f"audio_identity.{role} status" in message for message in errors), errors)

            write_json(root, chain["delivery_rel"], pristine)
            write_bytes(root, "成片_MV_master.mov", b"master-v2")
            errors = completion.stage_health(root, "compose")["errors"]
            self.assertTrue(any("audio_identity.master 未绑定当前" in message for message in errors), errors)

            write_bytes(root, "成片_MV_master.mov", b"master-v1")
            os.remove(chain["song"])
            errors = completion.stage_health(root, "compose")["errors"]
            self.assertTrue(any("缺当前主歌轨" in message for message in errors), errors)

    def test_provenance_schema2_complete_and_c2pa_dimensions(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            make_compose_chain(root)
            ai_rel, ai_path = make_ai_usage(root)
            provenance_rel, provenance_path = make_provenance(root, ai_rel, ai_path)
            self.assertTrue(completion.stage_health(root, "provenance")["ok"])
            signed_rel = "成片_MV.c2pa.mp4"
            signed_path = write_bytes(root, signed_rel, b"signed")
            payload = read_json(provenance_path)
            payload["assets"].append({"path": signed_rel, "sha256": mv_utils.content_hash(signed_path)})
            payload["c2pa"].update({"requested": True, "embedded": False, "structurally_valid": False,
                "signature_valid": False, "trust_checked": False, "trusted": False,
                "timestamp_validated": False, "timestamp_trusted": False, "timestamped": False,
                "timestamp_exception_allowed": False,
                "certificate_profile": "test_untrusted", "output": signed_rel,
                "output_sha256": mv_utils.content_hash(signed_path)})
            write_json(root, provenance_rel, payload)
            blocked = completion.stage_health(root, "provenance")
            self.assertTrue(any("embedded=false" in m for m in blocked["errors"]))
            self.assertTrue(any("structural validation" in m for m in blocked["errors"]))
            self.assertTrue(any("signature validation" in m for m in blocked["errors"]))
            self.assertTrue(any("trust chain" in m for m in blocked["errors"]))
            self.assertTrue(any("不受信任" in m for m in blocked["errors"]))
            self.assertTrue(any("测试证书" in m for m in blocked["errors"]))
            payload["c2pa"].update({"embedded": True, "structurally_valid": True,
                "signature_valid": True, "trust_checked": True, "trusted": True,
                "certificate_profile": "production", "timestamped": False})
            write_json(root, provenance_rel, payload)
            no_tsa = completion.stage_health(root, "provenance")
            self.assertTrue(any("可信 TSA 时间戳" in m for m in no_tsa["errors"]))
            payload["c2pa"]["timestamp_exception_allowed"] = True
            write_json(root, provenance_rel, payload)
            live_blocked = completion.stage_health(root, "provenance")
            self.assertTrue(any("c2patool" in m or "live verify" in m for m in live_blocked["errors"]))
            with mock.patch.object(completion, "_live_c2pa_verification", return_value=[]):
                accepted = completion.stage_health(root, "provenance")
            self.assertTrue(accepted["ok"], accepted["errors"])
            self.assertTrue(any("时间戳" in m for m in accepted["warnings"]))

    def test_review_health_rejects_handwritten_minimal_acceptance(self):
        with tempfile.TemporaryDirectory() as root:
            make_settings(root)
            for rel in (
                "成片_MV.mp4", "成片_MV_master.mov",
                "生产数据/delivery_qc/delivery_qc.json",
                "合规/provenance.json", "合规/ai_usage.json",
            ):
                write_bytes(root, rel, b"fixture")
            inputs = {
                rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in (
                    "成片_MV.mp4", "成片_MV_master.mov",
                    "生产数据/delivery_qc/delivery_qc.json",
                    "合规/provenance.json", "合规/ai_usage.json",
                )
            }
            write_json(root, "生产数据/review/review_receipt.json", {
                "kind": "mv_review_receipt", "accepted": True,
                "reviewer": "总审人", "inputs_sha256": inputs,
            })
            health = completion.stage_health(root, "review")
            self.assertFalse(health["ok"])
            self.assertTrue(any("human_signoff" in message for message in health["errors"]))
            self.assertTrue(any("machine_review" in message for message in health["errors"]))

    def test_handoff_controller_requires_current_release_chain_and_marks_progress(self):
        with tempfile.TemporaryDirectory() as root:
            settings = make_settings(root)
            runtime = contract.runtime_state_from_settings(settings)
            write_json(root, "_meta.json", {"title": "测试", **runtime})
            stages = contract.workflow_stage_table(runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"])
            table = "\n".join(f"| {row['label']} | {row['owner']} | {'[ ]' if row['key'] == 'handoff' else '[x]'} |" for row in stages)
            with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as handle:
                handle.write("# 进度\n\n## 制MV 阶段\n| 阶段 | skill | 状态 |\n|---|---|---|\n" + table + "\n")
            chain = make_compose_chain(root)
            ai_rel, ai_path = make_ai_usage(root)
            provenance_rel, provenance_path = make_provenance(root, ai_rel, ai_path)
            review_rel = "生产数据/review/review_receipt.json"
            reviewed_at = "2026-08-20T16:00:00+08:00"
            current_c2pa = read_json(provenance_path)["c2pa"]
            c2pa_review = {
                "requested": False, "embedded": False, "structurally_valid": False,
                "signature_valid": False, "trust_checked": False, "trusted": False,
                "test_certificate": False, "certificate_profile": None,
                "timestamp_validated": False, "timestamp_trusted": False,
                "timestamped": False, "timestamp_exception_allowed": False,
                "output": current_c2pa.get("output"), "output_sha256": current_c2pa.get("output_sha256"),
            }
            review_path = write_json(root, review_rel, {
                "schema_version": 1, "kind": "mv_review_receipt", "accepted": True,
                "reviewed_at": reviewed_at,
                "machine_review": {"hard_blocks": 0, "warnings": 0, "infos": 0,
                    "findings": [], "findings_sha256": mv_utils.json_hash([]), "c2pa": c2pa_review},
                "human_signoff": {"accepted": True, "reviewer": "总审人",
                    "notes": "已逐项观看当前成片并确认交付", "reviewed_at": reviewed_at,
                    "confirmation": {"kind": "explicit_current_delivery_acceptance",
                                     "accepted_current_delivery": True}},
                "inputs_sha256": {"成片_MV.mp4": mv_utils.content_hash(chain["final"]),
                    "成片_MV_master.mov": mv_utils.content_hash(chain["master"]),
                    chain["delivery_rel"]: mv_utils.content_hash(chain["delivery_path"]),
                    provenance_rel: mv_utils.content_hash(provenance_path), ai_rel: mv_utils.content_hash(ai_path)}})
            platform = write_bytes(root, "合规/平台声明截图.png", b"\x89PNG\r\n\x1a\nplatform")
            machine = write_json(root, "合规/机器标识导出.json", {"aigc_label": True})
            provider = write_bytes(root, "合规/平台上传成功截图.png", b"\x89PNG\r\n\x1a\nprovider")
            published_url = "https://www.douyin.com/video/7391234567890"
            upload_rel = "合规/上传回执.json"
            upload = write_json(root, upload_rel, {
                "schema_version": 3, "kind": "mv_platform_upload_receipt",
                "source": "platform_ui_export", "platform": "抖音",
                "remote_asset_id": "7391234567890", "operator": "发行负责人",
                "uploaded_at": "2026-08-20T16:30:00+08:00",
                "published_url": published_url,
                "uploaded_asset": {"path": "成片_MV.mp4", "sha256": mv_utils.content_hash(chain["final"])},
                "provider_evidence": {"path": "合规/平台上传成功截图.png",
                                      "sha256": mv_utils.content_hash(provider)},
                "ui_observation": {
                    "reviewer": "发行负责人", "notes": "已在平台页面核对发布结果",
                    "observed_at": "2026-08-20T16:30:30+08:00",
                    "remote_asset_id": "7391234567890", "published_url": published_url,
                },
            })
            upload_payload = read_json(upload)
            receipt_claim = {
                key: upload_payload.get(key) for key in (
                    "kind", "schema_version", "source", "platform", "remote_asset_id",
                    "operator", "uploaded_at", "published_url",
                )
            }
            receipt_claim["uploaded_asset"] = dict(upload_payload["uploaded_asset"])
            release_rel = "合规/release_decision.json"
            disclosure = read_json(ai_path)
            requirements = release_decision.applicable_requirements(disclosure, ["抖音"], ["CN"])
            for row in requirements:
                row["status"] = "completed"
                evidence_path = machine if row["evidence_class"] == "machine" else platform
                row["evidence"] = {
                    "path": mv_utils.relpath(root, evidence_path),
                    "sha256": mv_utils.content_hash(evidence_path),
                }
            write_json(root, release_rel, {"schema_version": 1, "kind": "mv_release_decision",
                "ruleset_version": release_decision.RULESET_VERSION, "decision": "ready_for_handoff", "operator": "发行负责人",
                "notes": "已核验平台标签和上传结果", "platforms": ["抖音"], "territories": ["CN"],
                "machine_label_method": "platform_metadata",
                "requirements": requirements, "errors": [],
                "submission": {"status": "uploaded", "published_url": published_url,
                               "receipt": {"path": upload_rel, "sha256": mv_utils.content_hash(upload)},
                               "receipt_claim": receipt_claim},
                "inputs_sha256": {"成片_MV.mp4": mv_utils.content_hash(chain["final"]),
                                  ai_rel: mv_utils.content_hash(ai_path),
                                  provenance_rel: mv_utils.content_hash(provenance_path)}})
            with mock.patch.object(completion, "_predecessor_completion_errors", return_value=[]):
                health = completion.mark_stage_complete(
                    root, "handoff", reviewer="发行负责人", notes="发布前最终确认",
                )
            self.assertTrue(health["ok"])
            receipt = read_json(os.path.join(root, "合规", "handoff_receipt.json"))
            self.assertEqual(receipt["reviewer"], "发行负责人")
            self.assertEqual(receipt["inputs_sha256"][review_rel], mv_utils.content_hash(review_path))
            self.assertIn(release_rel, receipt["inputs_sha256"])
            self.assertIn("| 发布/交平台 | mv-craft/scripts/completion.py | [x] |",
                          mv_utils.read_text(os.path.join(root, "_进度.md")))
            release_payload = read_json(os.path.join(root, release_rel))
            release_payload["requirements"] = []
            write_json(root, release_rel, release_payload)
            self.assertTrue(any("重算全集" in message for message in completion._release_decision_errors(root)))


if __name__ == "__main__":
    unittest.main()
