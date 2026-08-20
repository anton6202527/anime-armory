#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""video_jobs.py tests.

Can run without pytest:
    python3 skills/mv/mv-video/scripts/test_video_jobs.py
"""
import json
import importlib.util
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import hashlib
from pathlib import Path
from unittest import mock


HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(HERE, "video_jobs.py")
SPEC = importlib.util.spec_from_file_location("mv_video_jobs_test", JOBS)
video_jobs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(video_jobs)

IMAGE_RECEIPTS = os.path.join(HERE, "..", "..", "mv-image", "scripts", "image_receipts.py")
IMAGE_RECEIPTS_SPEC = importlib.util.spec_from_file_location(
    "mv_image_receipts_for_video_jobs_test", IMAGE_RECEIPTS
)
image_receipts = importlib.util.module_from_spec(IMAGE_RECEIPTS_SPEC)
IMAGE_RECEIPTS_SPEC.loader.exec_module(image_receipts)

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
REFERENCE_PATHS = [
    "设定/reference_images/lead_front.png",
    "设定/reference_images/lead_three_quarter.png",
    "设定/reference_images/lead_full.png",
]


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def write_settings(root, model="Seedance 2.0", channel="即梦/Dreamina", legacy_ai=""):
    rows = [
        "# _设置", "", "## 选择",
        "- MV用途: 歌曲Demo",
        "- 歌曲输入时序: 先传音乐",
        "- MV视觉风格: 二次元",
        "- MV规划粒度: 标准",
        "- 卡点策略: 副歌强卡点",
        "- 生图模型: GPT Image 2",
        "- 生图渠道: Codex",
        "- MV一致性增强: 共享定妆+锚点",
        "- 字幕语言: 无字幕",
        "- 演唱口型: 关闭",
        "- 输入歌权利: 自有",
    ]
    if legacy_ai:
        rows.append(f"- 生视频AI: {legacy_ai}")
    rows.extend([
        f"- 生视频模型: {model}",
        f"- 生视频渠道: {channel}",
        "- 出视频规格: 预算一般",
        "- 合成画幅: 16:9 横屏",
    ])
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(rows) + "\n")


def write_image_qc(root, processed_assets, all_assets):
    root_path = Path(root)
    ledger = image_receipts.load_ledger(root_path)
    integrity = []
    face = []
    palette = []
    provenance = []
    hashes = {}
    for asset in processed_assets:
        current = ledger["assets"][asset]["current"]
        digest = image_receipts.sha256_path(root_path / asset)
        hashes[asset] = digest
        integrity.append({"asset": asset, "png": asset, "verdict": "ok"})
        face.append({"png": asset, "verdict": "ok"})
        palette.append({"png": asset, "verdict": "ok"})
        provenance.append({
            "asset": asset,
            "verdict": "ok",
            "b14_attempt_id": current["attempt_id"],
            "b14_preflight_sha256": current["preflight"]["receipt_sha256"],
            "b14_submission_sha256": current["submission"]["receipt_sha256"],
        })
    payload = {
        "kind": "mv_image_qc",
        "version": 3,
        "summary": {"hard_blocks": 0, "advisory": 0, "verdict": "ok"},
        "qc_environment": {"precision_level": "full"},
        "assets_sha256": hashes,
        "asset_integrity": {"rows": integrity},
        "checks": {"face": {"shots": face}, "palette": {"shots": palette}},
        "generation_provenance": {
            "complete": len(processed_assets) == len(all_assets),
            "uniform": True,
            "summary": {"block": 0, "ok": len(processed_assets)},
            "rows": provenance,
        },
        "prohibited_local_patch_outputs": {"outputs": []},
    }
    write_json(os.path.join(root, "生产数据", "image_qc", "image_qc.json"), payload)


def rebuild_image_evidence(root, clips):
    """Create current local-route B14 preflight/submission/QC/postflight evidence."""
    root_path = Path(root)
    image_receipts.write_ledger(root_path, image_receipts.empty_ledger())
    assets = [clip["image_path"] for clip in clips]
    processed = []
    for clip in clips:
        asset = clip["image_path"]
        prompt = clip["image_prompt_path"]
        image_receipts.create_preflight(
            root_path,
            asset=asset,
            asset_kind="clip_start",
            owner="lead:fixture",
            use="clip_start",
            identity_scope="contains_identity",
            model="local:fixture-model",
            channel="local",
            prompt=prompt,
            reference_specs=[f"{REFERENCE_PATHS[0]}::lead:fixture::identity_anchor"],
            notes="test fixture freezes the exact prompt and identity reference",
        )
        image_receipts.record_submission(
            root_path,
            asset=asset,
            model="local:fixture-model",
            channel="local",
            prompt=prompt,
            references=[REFERENCE_PATHS[0]],
        )
        processed.append(asset)
        write_image_qc(root, processed, assets)
        result = image_receipts.record_postflight(
            root_path,
            asset=asset,
            qc_report="生产数据/image_qc/image_qc.json",
            reviewer="fixture image reviewer",
            visual_verdict="pass",
            notes="compared current pixels side by side with the bound identity reference",
        )
        assert result["accepted"]
    write_image_qc(root, processed, assets)


def refresh_strict_contracts(root):
    """Re-sign every upstream contract after a fixture changes settings or plan."""
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = json.load(open(plan_path, encoding="utf-8"))
    clips = plan["clips"]
    song_rel = "歌/song.wav"
    song_path = os.path.join(root, song_rel)
    duration = max(float(clip["end"]) for clip in clips)
    beatgrid_path = os.path.join(root, "节拍", "beatgrid.json")
    write_json(beatgrid_path, {
        "schema_version": 2,
        "kind": "mv_beatgrid",
        "song": song_rel,
        "duration": duration,
        "source_audio_sha256": video_jobs.mv_utils.content_hash(song_path),
        "beats": list(range(0, int(duration) + 1)),
        "downbeats": [0, min(4, int(duration))] if duration >= 1 else [0],
        "timing_verified": True,
        "downbeats_verified": True,
        "sections_verified": True,
        "sections_complete": True,
        "sections": [{"section": "full", "start": 0, "end": duration}],
        "timing_review": {
            "accepted": True,
            "reviewer": "fixture music editor",
            "notes": "checked meter phase, downbeats, and full section coverage",
        },
    })
    plan.update({
        "schema_version": 3,
        "kind": "mv_clip_plan",
        "root_rel": ".",
    })
    plan["inputs_sha256"] = {
        "song": video_jobs.mv_utils.content_hash(song_path),
        "beatgrid": video_jobs.mv_utils.content_hash(beatgrid_path),
        "lyrics": video_jobs.mv_utils.content_hash(os.path.join(root, "词", "lyrics.md")),
        "blueprint": video_jobs.mv_utils.content_hash(os.path.join(root, "视觉蓝图.md")),
        "alignment": video_jobs.mv_utils.content_hash(os.path.join(root, "字幕", "alignment_report.json")),
        "settings_plan": video_jobs.contract.plan_settings_digest(
            video_jobs.mv_utils.parse_settings(root)
        ),
    }
    write_json(plan_path, plan)

    rebuild_image_evidence(root, clips)
    plan_sha = video_jobs.mv_utils.content_hash(plan_path)
    semantic_path = os.path.join(root, "分镜", "semantic_prompts.json")
    write_json(semantic_path, {
        "schema_version": 3,
        "kind": "mv_semantic_prompts",
        "complete": True,
        "updated_clips": len(clips),
        "clips": [{"clip_id": clip["clip_id"]} for clip in clips],
        "result_clip_plan_sha256": plan_sha,
        "inputs_sha256": {
            "lyrics": video_jobs.mv_utils.content_hash(os.path.join(root, "词", "lyrics.md")),
            "blueprint": video_jobs.mv_utils.content_hash(os.path.join(root, "视觉蓝图.md")),
        },
        "prompt_outputs_sha256": {
            clip["clip_id"]: {
                "image": video_jobs.mv_utils.content_hash(os.path.join(root, clip["image_prompt_path"])),
                "video": video_jobs.mv_utils.content_hash(os.path.join(root, clip["video_prompt_path"])),
            }
            for clip in clips
        },
    })

    rate = 24
    timeline_rows = []
    for clip in clips:
        start_frame = round(float(clip["start"]) * rate)
        end_frame = round(float(clip["end"]) * rate)
        timeline_rows.append({
            "clip_id": clip["clip_id"],
            "section": clip.get("section"),
            "start": clip["start"],
            "end": clip["end"],
            "duration": clip["duration"],
            "start_frame": start_frame,
            "end_frame": end_frame,
            "duration_frames": end_frame - start_frame,
            "video_path": clip["selected_video_path"],
            "transition": clip.get("transition"),
        })
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    timeline = {
        "schema_version": 3,
        "kind": "mv_timeline_manifest",
        "root_rel": ".",
        "title": "测试MV",
        "rate": rate,
        "timebase": {"rate": rate, "unit": "frame", "quantized": True},
        "song_path": song_rel,
        "beatgrid_path": "节拍/beatgrid.json",
        "audio_policy": "locked_master_song_only; generated_clip_audio_discarded",
        "source_clip_plan_sha256": plan_sha,
        "clips": timeline_rows,
    }
    write_json(timeline_path, timeline)
    editorial_hash = video_jobs.mv_utils.timeline_edit_hash(timeline)

    otio_path = os.path.join(root, "分镜", "timeline.otio")
    write_json(otio_path, {
        "OTIO_SCHEMA": "Timeline.1",
        "name": "fixture timeline",
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "children": [
                {"OTIO_SCHEMA": "Track.1", "kind": "Video", "children": []},
                {"OTIO_SCHEMA": "Track.1", "kind": "Audio", "children": []},
            ],
        },
    })
    write_json(os.path.join(root, "生产数据", "otio", "otio_receipt.json"), {
        "schema_version": 3,
        "kind": "mv_otio_export_receipt",
        "otio_sha256": video_jobs.mv_utils.content_hash(otio_path),
        "timeline_edit_sha256": editorial_hash,
        "inputs_sha256": {
            "分镜/timeline_manifest.json": video_jobs.mv_utils.content_hash(timeline_path),
            "节拍/beatgrid.json": video_jobs.mv_utils.content_hash(beatgrid_path),
        },
        "timebase": {"unit": "frame", "integral_rational_time": True},
        "rate": rate,
        "official_roundtrip": {"status": "ok", "library_version": "fixture-verified"},
        "media_sha256": {song_rel: video_jobs.mv_utils.content_hash(song_path)},
        "tracks": {"video": 1, "audio": 1},
        "missing_media": [],
    })

    write_json(os.path.join(root, "评分", "pacing_prescore.json"), {
        "schema_version": 3,
        "kind": "mv_pacing_prescore",
        "blocked": False,
        "threshold": None,
        "pacing_score": 100.0,
        "metrics": {"fixture": "all locked boundaries reviewed"},
        "inputs_sha256": {
            "分镜/clip_plan.json": plan_sha,
            "节拍/beatgrid.json": video_jobs.mv_utils.content_hash(beatgrid_path),
            song_rel: video_jobs.mv_utils.content_hash(song_path),
        },
    })
    animatic_path = os.path.join(root, "分镜", "animatic.mp4")
    with open(animatic_path, "wb") as handle:
        handle.write(b"fixture animatic tied to the current editorial timeline")
    animatic_report_path = os.path.join(root, "生产数据", "animatic", "animatic.json")
    write_json(animatic_report_path, {
        "schema_version": 2,
        "kind": "mv_animatic_render",
        "output": "分镜/animatic.mp4",
        "output_sha256": video_jobs.mv_utils.content_hash(animatic_path),
        "timeline_edit_sha256": editorial_hash,
        "inputs_sha256": {
            "分镜/clip_plan.json": video_jobs.mv_utils.content_hash(plan_path),
            song_rel: video_jobs.mv_utils.content_hash(song_path),
        },
    })

    lock_inputs = {
        "分镜/clip_plan.json",
        "节拍/beatgrid.json",
        "分镜/animatic.mp4",
        "生产数据/animatic/animatic.json",
        "生产数据/image_qc/image_qc.json",
        "评分/pacing_prescore.json",
        "分镜/semantic_prompts.json",
        song_rel,
        "视觉蓝图.md",
        "词/lyrics.md",
    }
    for clip in clips:
        lock_inputs.add(clip["image_path"])
        lock_inputs.add(clip["image_prompt_path"])
        lock_inputs.add(clip["video_prompt_path"])
    write_json(os.path.join(root, "制片", "picture_lock.json"), {
        "schema_version": 2,
        "kind": "mv_picture_lock",
        "accepted": True,
        "reviewer": "fixture director",
        "notes": "reviewed the current animatic and locked all editorial boundaries",
        "decision": "picture_locked",
        "editorial_timeline_sha256": editorial_hash,
        "otio_timeline_sha256": editorial_hash,
        "inputs_sha256": {
            rel: video_jobs.mv_utils.content_hash(os.path.join(root, rel))
            for rel in sorted(lock_inputs)
        },
    })


def set_video_route(root, model, channel, legacy_ai=""):
    write_settings(root, model=model, channel=channel, legacy_ai=legacy_ai)
    refresh_strict_contracts(root)


def make_project(root):
    for sub in ("分镜", "歌", "词", "节拍", "出图/段落/图片", "出图/段落/prompt",
                "设定/reference_images", "合规", "制片"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    write_settings(root)
    runtime = video_jobs.contract.runtime_state_from_settings(
        video_jobs.mv_utils.parse_settings(root)
    )
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "title": "测试MV", **runtime, "has_song": True, "has_lyrics": True,
            "song_rights_status": "owned",
        }, f, ensure_ascii=False)
    workflow = video_jobs.contract.workflow_stage_table(
        runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"]
    )
    video_jobs_index = [row["key"] for row in workflow].index("video_jobs")
    progress_rows = ["## 制MV 阶段", "", "| 阶段 | skill | 状态 |", "|---|---|---|"]
    progress_rows.extend(
        f"| {stage['label']} | {stage['owner']} | {'[x]' if index < video_jobs_index else '[ ]'} |"
        for index, stage in enumerate(workflow)
    )
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(progress_rows) + "\n")
    with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
        f.write("# 视觉蓝图\n")
    with open(os.path.join(root, "歌", "song.wav"), "wb") as f:
        f.write(b"fake wav")
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[verse1]\n一句歌词\n")
    clips = [
        {
            "clip_id": "Clip_001",
            "section": "verse1",
            "start": 0,
            "end": 4,
            "duration": 4,
            "beat_role": "normal",
            "image_path": "出图/段落/图片/Clip_001.png",
            "image_prompt_path": "出图/段落/prompt/Clip_001.md",
            "video_prompt_path": "分镜/prompts/video/Clip_001.md",
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
            "image_prompt_path": "出图/段落/prompt/Clip_002.md",
            "video_prompt_path": "分镜/prompts/video/Clip_002.md",
            "selected_video_path": "出视频/视频/Clip_002.mp4",
            "transition": "卡点硬切",
            "continuity": {"action": "爆点", "start_state": "开始", "end_state": "结束"},
        },
    ]
    with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试MV", "clips": clips}, f, ensure_ascii=False)
    for clip in clips:
        with open(os.path.join(root, clip["image_path"]), "wb") as f:
            f.write(PNG_BYTES)
        with open(os.path.join(root, clip["image_prompt_path"]), "w", encoding="utf-8") as f:
            f.write(f"# {clip['clip_id']}\n\n身份锚点：fixture lead；禁止换脸、换衣。\n")
        video_prompt_path = os.path.join(root, clip["video_prompt_path"])
        os.makedirs(os.path.dirname(video_prompt_path), exist_ok=True)
        with open(video_prompt_path, "w", encoding="utf-8") as handle:
            handle.write(f"# {clip['clip_id']} video\n\n主动作与运镜语义已确认。\n")
    for rel in REFERENCE_PATHS:
        with open(os.path.join(root, rel), "wb") as handle:
            handle.write(PNG_BYTES)
    write_json(os.path.join(root, "设定", "identity_registry.json"), {
        "lead_id": "CHAR_LEAD",
        "identities": [{
            "id": "CHAR_LEAD",
            "display_name": "fixture lead",
            "reference_group": "REF_LEAD",
        }],
        "reference_groups": [{
            "id": "REF_LEAD",
            "status": "ready",
            "paths": REFERENCE_PATHS,
        }],
    })
    write_json(os.path.join(root, "合规", "rights_manifest.json"), {
        "assertions": {
            "song": "owned",
            "visual_reference": "owned",
            "likeness": "authorized",
            "brand": "not_applicable",
            "location": "not_applicable",
            "choreography": "not_applicable",
        },
    })
    refresh_strict_contracts(root)


def write_manual_adapter(root, model="manual", channel="manual"):
    os.makedirs(os.path.join(root, "出视频"), exist_ok=True)
    payload = {
        "schema_version": 1,
        "kind": "mv_video_provider_adapter",
        "model": model,
        "channel": channel,
        "provider_id": "vendor.manual.test",
        "access_status": "available",
        "adapter_kind": "manual",
        "reviewer": "test operator",
        "notes": "fixture adapter with an explicit capability contract",
        "capability": video_jobs.video_capabilities.MODEL_CAPABILITIES["Seedance 2.0"],
    }
    path = os.path.join(root, "出视频", "provider_adapter.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def write_omni_adapter(root):
    """Explicit account-scoped capability; not an official global matrix."""
    os.makedirs(os.path.join(root, "出视频"), exist_ok=True)
    payload = {
        "schema_version": 1,
        "kind": video_jobs.video_capabilities.ADAPTER_KIND,
        "model": "Gemini Omni Flash Preview",
        "channel": "Google Gemini API",
        "provider_id": "google.gemini_api",
        "access_status": "available",
        "adapter_kind": "api",
        "reviewer": "fixture integration owner",
        "notes": "account-specific smoke test; values must not be promoted to the official graph",
        "capability": {
            "input_roles": {
                "start_frame": {"max_count": 1, "required_for_image2video": True},
                "end_frame": {"max_count": 0},
                "reference_image": {"max_count": 0},
                "reference_video": {"max_count": 0},
                "reference_audio": {"max_count": 0},
                "keyframe": {"max_count": 0},
            },
            "allowed_input_combinations": [["start_frame"]],
            "duration_seconds": {"allowed": [2.0, 4.0]},
            "fps": [24],
            "resolutions": ["720p"],
            "native_audio": {
                "produces": True,
                "disableable": None,
                "disableability_status": "account_observed_not_confirmed",
            },
            "multi_shot": False,
            "legacy_compatibility": False,
            "provenance": {
                "source": "named account smoke test",
                "source_date_or_collected": "2026-08-20",
            },
        },
    }
    path = os.path.join(root, "出视频", "provider_adapter.json")
    write_json(path, payload)
    return path


def complete_receipt(
    root, item_id="Clip_001", take_id="take_01", *, sequence=False, source_path=""
):
    suffix = f"{item_id}_{take_id}.submit.json"
    path = os.path.join(root, "出视频", "receipts", suffix)
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    payload["template_only"] = False
    payload["provider_job_id"] = f"provider:{item_id}:{take_id}"
    payload["provider_status"] = "succeeded"
    payload["submitted_at"] = "2026-08-20T12:00:00+08:00"
    for row in payload.get("submitted_refs") or []:
        row["confirmed_submitted"] = True
    output_sha = (
        video_jobs.mv_utils.content_hash(source_path) if source_path else "d" * 64
    )
    evidence = payload.get("provider_evidence")
    if isinstance(evidence, dict):
        kind = evidence.get("kind")
        if kind in {"", None, "provider_ui_capture"}:
            evidence_rel = f"出视频/provider_evidence/{item_id}_{take_id}.provider.png"
            evidence_path = os.path.join(root, evidence_rel)
            os.makedirs(os.path.dirname(evidence_path), exist_ok=True)
            with open(evidence_path, "wb") as handle:
                handle.write(PNG_BYTES)
            evidence.update({
                "kind": "provider_ui_capture",
                "execution_transport": "web",
                "adapter_id": "named_ui_observation.v1",
                "path": evidence_rel,
                "sha256": video_jobs.mv_utils.content_hash(evidence_path),
                "ui_observation": {
                    "reviewer": "test web operator",
                    "notes": "read completed job, model, status and preview in provider UI",
                    "observed_at": payload["submitted_at"],
                    "submitted_at": payload["submitted_at"],
                    "provider_id": payload["provider_id"],
                    "provider_job_id": payload["provider_job_id"],
                    "model": payload["model"],
                    "status": payload["provider_status"],
                    "capture_method": "browser_screenshot",
                },
            })
        elif kind == "local_runner_receipt_json":
            evidence_rel = f"出视频/provider_evidence/{item_id}_{take_id}.local.json"
            write_json(os.path.join(root, evidence_rel), {
                "kind": "mv_video_local_runner_receipt", "schema_version": 1,
                "provider_id": payload["provider_id"],
                "runner": {
                    "name": "fixture-local-runner", "version": "1",
                    "operator": "test local operator", "command_sha256": "c" * 64,
                },
                "execution": {
                    "job_id": payload["provider_job_id"], "submitted_at": payload["submitted_at"],
                    "model": payload["model"], "status": payload["provider_status"], "exit_code": 0,
                    "request_controls_sha256": payload["compiled_request_controls_sha256"],
                    "submitted_refs_sha256": video_jobs.stable_hash(payload.get("submitted_refs") or []),
                    "output_asset_sha256": output_sha,
                },
            })
            evidence.update({
                "adapter_id": "mv_video.local_runner_receipt.v1",
                "path": evidence_rel,
                "sha256": video_jobs.mv_utils.content_hash(os.path.join(root, evidence_rel)),
            })
        else:
            evidence_rel = f"出视频/provider_evidence/{item_id}_{take_id}.api.json"
            if evidence.get("adapter_id") == "runway.task.v1":
                document = {
                    "id": payload["provider_job_id"], "createdAt": payload["submitted_at"],
                    "model": payload["model"], "status": payload["provider_status"],
                }
            else:
                evidence["adapter_id"] = "google.gemini.operation.v1"
                document = {
                    "name": payload["provider_job_id"],
                    "metadata": {"createTime": payload["submitted_at"], "model": payload["model"]},
                    "done": True,
                }
            write_json(os.path.join(root, evidence_rel), document)
            evidence.update({
                "execution_transport": "api", "path": evidence_rel,
                "sha256": video_jobs.mv_utils.content_hash(os.path.join(root, evidence_rel)),
            })
        evidence["selected_asset"] = {
            "sha256": output_sha, "bound_by": "test download operator",
            "notes": "bound the exact registered source bytes to this completed provider job",
        }
    if payload.get("channel") == "manual":
        payload["manual_attestation"] = {
            "reviewer": "test operator", "notes": "personally submitted these exact controls and files",
        }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def register_cli(root, src, clip="1", take="1", extra=None):
    receipt = complete_receipt(
        root, video_jobs.normalize_clip_id(clip), video_jobs.normalize_take_id(take),
        source_path=src,
    )
    return [
        sys.executable, JOBS, root, "--register", src, "--clip", str(clip), "--take", str(take),
        "--submit-receipt", receipt, *(extra or []),
    ]


class VideoJobsTest(unittest.TestCase):
    def test_model_channel_pair_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            set_video_route(tmp, "Veo 3.1", "Runway API")
            proc = subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("model×channel", proc.stderr)

    def test_current_models_require_explicit_exact_version_and_are_not_downgraded(self):
        for model, channel in (("Seedance 2.5", "即梦/Dreamina"), ("Luma Ray3.2", "Luma Dream Machine")):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as tmp:
                make_project(tmp)
                set_video_route(tmp, model, channel)
                subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
                manifest = json.load(open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8"))
                self.assertEqual(manifest["video_model"], model)

    def test_omni_preview_google_api_requires_capability_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            set_video_route(tmp, "Gemini Omni Flash Preview", "Google Gemini API")
            blocked = subprocess.run(
                [sys.executable, JOBS, tmp], capture_output=True, text=True
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("missing_explicit_adapter_record", blocked.stderr)

            adapter_path = write_omni_adapter(tmp)
            subprocess.run(
                [sys.executable, JOBS, tmp, "--adapter-record", adapter_path],
                capture_output=True, text=True, check=True,
            )
            manifest = json.load(open(
                os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8"
            ))
            self.assertEqual(manifest["video_model"], "Gemini Omni Flash Preview")
            self.assertEqual(manifest["provider_route"]["release_stage"], "preview")
            self.assertEqual(manifest["provider_route"]["declared_route_status"], "adapter_required")
            self.assertTrue(manifest["provider_route"]["adapter_required"])

    def test_multi_shot_capability_emits_sequence_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            clips = []
            for index in range(2):
                image_path = f"出图/段落/图片/Clip_{index + 1:03d}.png"
                os.makedirs(os.path.join(tmp, os.path.dirname(image_path)), exist_ok=True)
                with open(os.path.join(tmp, image_path), "wb") as f:
                    f.write(f"pixels-{index}".encode("utf-8"))
                clips.append({
                    "clip_id": f"Clip_{index + 1:03d}", "section": "verse", "duration": 3,
                    "image_path": image_path,
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

    def test_sequence_cut_map_requires_named_observed_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "sequence.mp4")
            with open(source, "wb") as f:
                f.write(b"sequence")
            unit = {"unit_id": "Sequence_001"}
            jobs = [{"clip_id": "Clip_001", "duration": 2}, {"clip_id": "Clip_002", "duration": 2}]
            blind_plan_copy = {
                "schema_version": 1, "kind": "mv_video_sequence_cut_map",
                "unit_id": "Sequence_001", "source_sha256": hashlib.sha256(b"sequence").hexdigest(),
                "actual_boundaries_seconds": [0, 2, 4],
                "review_method": "planned_boundaries", "reviewer": "", "notes": "",
            }
            with self.assertRaisesRegex(SystemExit, "cut map"):
                video_jobs.validate_cut_map(unit, jobs, source, 4.0, blind_plan_copy)

    def test_sequence_split_workdirs_are_unique_and_cleanup_is_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = video_jobs._sequence_split_work_dir(tmp, "Sequence_001", "take_01")
            second = video_jobs._sequence_split_work_dir(tmp, "Sequence_001", "take_01")
            split_root = os.path.realpath(os.path.join(tmp, "出视频", "takes", "_sequence_split"))
            self.assertNotEqual(first, second)
            self.assertEqual(os.path.commonpath((split_root, os.path.realpath(first))), split_root)
            self.assertEqual(os.path.commonpath((split_root, os.path.realpath(second))), split_root)
            marker = os.path.join(second, "belongs-to-second-invocation")
            with open(marker, "w", encoding="utf-8") as handle:
                handle.write("keep")
            try:
                video_jobs._cleanup_sequence_split_work_dir(tmp, first)
                self.assertFalse(os.path.exists(first))
                self.assertTrue(os.path.isfile(marker))
                with self.assertRaisesRegex(RuntimeError, "refusing to clean"):
                    video_jobs._cleanup_sequence_split_work_dir(tmp, split_root)
            finally:
                video_jobs._cleanup_sequence_split_work_dir(tmp, second)

    @unittest.skipIf(video_jobs.fcntl is None, "fcntl unavailable")
    def test_registration_lock_serializes_across_processes(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker = os.path.join(tmp, "lock_worker.py")
            with open(worker, "w", encoding="utf-8") as handle:
                handle.write(
                    "import importlib.util, os, sys, time\n"
                    f"spec = importlib.util.spec_from_file_location('video_jobs_worker', {JOBS!r})\n"
                    "module = importlib.util.module_from_spec(spec)\n"
                    "spec.loader.exec_module(module)\n"
                    "root, marker, release = sys.argv[1:]\n"
                    "open(marker + '.attempted', 'w', encoding='utf-8').write('attempted')\n"
                    "with module._registration_lock(root):\n"
                    "    open(marker, 'w', encoding='utf-8').write('locked')\n"
                    "    while release != '-' and not os.path.exists(release):\n"
                    "        time.sleep(0.01)\n"
                )

            first_marker = os.path.join(tmp, "first.locked")
            second_marker = os.path.join(tmp, "second.locked")
            release = os.path.join(tmp, "release-first")
            first = subprocess.Popen([sys.executable, worker, tmp, first_marker, release])
            second = None
            try:
                deadline = time.monotonic() + 5
                while not os.path.exists(first_marker) and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(os.path.exists(first_marker), "first worker never acquired registration lock")

                second = subprocess.Popen([sys.executable, worker, tmp, second_marker, "-"])
                deadline = time.monotonic() + 5
                while not os.path.exists(second_marker + ".attempted") and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(os.path.exists(second_marker + ".attempted"))
                self.assertFalse(os.path.exists(second_marker), "second worker bypassed registration lock")

                Path(release).touch()
                self.assertEqual(first.wait(timeout=5), 0)
                self.assertEqual(second.wait(timeout=5), 0)
                self.assertTrue(os.path.exists(second_marker))
            finally:
                for proc in (first, second):
                    if proc is not None and proc.poll() is None:
                        proc.kill()
                        proc.wait()

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg unavailable")
    def test_register_sequence_splits_back_into_take_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            write_settings(tmp, "Seedance 2.0", "即梦")
            plan_path = os.path.join(tmp, "分镜", "clip_plan.json")
            plan = json.load(open(plan_path, encoding="utf-8"))
            for index, clip in enumerate(plan["clips"]):
                clip.update({
                    "section": "verse1", "start": index * 2, "end": (index + 1) * 2,
                    "duration": 2, "shot_design": {"setup_group": "verse1/stage"},
                    "continuity": {"action": "perform", "end_state": "hold"},
                })
            json.dump(plan, open(plan_path, "w", encoding="utf-8"), ensure_ascii=False)
            refresh_strict_contracts(tmp)
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            source = os.path.join(tmp, "sequence.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                "-i", "color=c=red:s=320x180:r=24:d=4", "-an",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", source,
            ], check=True)
            receipt = complete_receipt(
                tmp, "Sequence_001", "take_01", sequence=True, source_path=source
            )
            cut_map = os.path.join(tmp, "sequence_cut_map.json")
            with open(cut_map, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 1, "kind": "mv_video_sequence_cut_map",
                    "unit_id": "Sequence_001", "source_sha256": hashlib.sha256(open(source, "rb").read()).hexdigest(),
                    "actual_boundaries_seconds": [0.0, 2.0, 4.0],
                    "review_method": "frame_accurate_visual_review",
                    "reviewer": "test editor", "notes": "reviewed the visible shot change frame by frame",
                }, f, ensure_ascii=False)
            subprocess.run([
                sys.executable, JOBS, tmp, "--register-sequence", source,
                "--unit", "Sequence_001", "--take", "1", "--cut-map", cut_map,
                "--submit-receipt", receipt,
            ], capture_output=True, text=True, check=True)
            manifest = json.load(open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8"))
            self.assertEqual(manifest["sequence_units"][0]["status"], "split_registered")
            self.assertEqual(len(manifest["sequence_units"][0]["registrations"]), 2)
            for job in manifest["jobs"]:
                take = job["takes"][0]
                self.assertTrue(os.path.isfile(os.path.join(tmp, take["video_path"])))
                self.assertEqual(len(take["video_sha256"]), 64)
            split_root = os.path.join(tmp, "出视频", "takes", "_sequence_split")
            self.assertTrue(os.path.isdir(split_root))
            self.assertEqual(os.listdir(split_root), [])

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
            self.assertEqual(manifest["schema_version"], 4)
            self.assertEqual(manifest["root_rel"], ".")
            self.assertNotIn("project_root", manifest)
            take = manifest["jobs"][1]["takes"][0]
            prompt = take["prompt_path"]
            self.assertTrue(os.path.exists(os.path.join(tmp, prompt)))
            self.assertEqual(take["prompt_source_kind"], "compiled_submit_prompt")
            self.assertEqual(take["prompt_compiler"]["native_audio_policy"], "external_song_track")
            self.assertEqual(
                take["compiled_request_controls_sha256"],
                video_jobs.stable_hash(take["compiled_request_controls"]),
            )
            self.assertIn("settings_sha256", manifest["freshness"])
            self.assertNotIn("identity_registry", take["submit_prompt"])
            with open(os.path.join(tmp, prompt), encoding="utf-8") as f:
                prompt_text = f.read()
            self.assertIn("### 后端编译提交 prompt", prompt_text)
            self.assertIn(take["submit_prompt"], prompt_text)

    def test_legacy_absolute_project_root_manifest_remains_readable(self):
        """Old manifests may retain an absolute audit hint; readers ignore it."""
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            path = os.path.join(tmp, "出视频", "jobs_manifest.json")
            with open(path, encoding="utf-8") as f:
                manifest = json.load(f)
            manifest["schema_version"] = 3
            manifest.pop("root_rel", None)
            manifest["project_root"] = tmp
            with open(path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            _path, loaded = video_jobs.load_manifest(tmp)
            self.assertEqual(loaded["project_root"], tmp)

    def test_legacy_single_axis_backend_maps_to_explicit_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            self.assertEqual(
                video_jobs.contract.legacy_video_route("即梦"),
                ("Seedance 2.0", "即梦"),
            )
            set_video_route(tmp, "Seedance 2.0", "即梦", legacy_ai="即梦")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["video_model"], "Seedance 2.0")
            self.assertEqual(manifest["video_channel"], "即梦")

    def test_quality_tier_and_motion_reference_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            set_video_route(tmp, "Kling 3.0", "可灵/Kling")
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
            set_video_route(tmp, "manual", "manual")
            write_manual_adapter(tmp)
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
            subprocess.run(register_cli(tmp, src), capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--score", "Clip_001", "--take", "1", "--motion-score", "5", "--identity-score", "4", "--beat-score", "5", "--clarity-score", "4", "--reviewer", "editor"], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--select", "Clip_001", "--take", "1"], capture_output=True, text=True, check=True)
            self.assertTrue(os.path.exists(os.path.join(tmp, "出视频", "视频", "Clip_001.mp4")))
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["jobs"][0]["selected_take"], "take_01")
            self.assertEqual(manifest["jobs"][0]["takes"][0]["score"]["motion"], 5)

    def test_select_never_marks_demo_video_done_without_semantic_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "出视频", "takes", "Clip_001"), exist_ok=True)
            src_rel = "出视频/takes/Clip_001/take_01.mp4"
            src = os.path.join(tmp, src_rel)
            with open(src, "wb") as handle:
                handle.write(b"registered video")
            manifest = {
                "schema_version": 3,
                "kind": "mv_video_jobs",
                "jobs": [{
                    "clip_id": "Clip_001",
                    "selected_take": None,
                    "selected_video_path": "出视频/视频/Clip_001.mp4",
                    "takes": [{
                        "take_id": "take_01", "status": "scored", "video_path": src_rel,
                        "video_sha256": video_jobs.mv_utils.content_hash(src),
                        "score": {"motion": 5, "identity": 5, "beat_fit": 5, "clarity": 5},
                        "scored_by": "editor",
                    }],
                }],
            }
            write_json(os.path.join(tmp, "出视频", "jobs_manifest.json"), manifest)
            write_json(os.path.join(tmp, "_meta.json"), {"is_demo": True})
            progress = os.path.join(tmp, "_进度.md")
            with open(progress, "w", encoding="utf-8") as handle:
                handle.write("| 视频登记/挑版 | backend + video_jobs.py | [ ] |\n")
            with mock.patch.object(video_jobs, "run_final_video_checks") as final_checks, \
                    mock.patch.object(video_jobs.mv_utils, "update_progress_stage") as update_progress:
                video_jobs.select_take(tmp, "Clip_001", "take_01")
            final_checks.assert_called_once_with(tmp)
            update_progress.assert_not_called()
            self.assertIn("| [ ] |", Path(progress).read_text(encoding="utf-8"))

    def test_schema_v4_register_requires_attested_submit_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            proc = subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("submit-receipt", proc.stderr)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                take = json.load(f)["jobs"][0]["takes"][0]
            self.assertNotIn("first_frame_sha256", take)

    def test_formal_route_rejects_self_declared_job_and_time_without_provider_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as handle:
                handle.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            receipt = complete_receipt(tmp, source_path=src)
            payload = json.load(open(receipt, encoding="utf-8"))
            payload.pop("provider_evidence", None)
            write_json(receipt, payload)
            proc = subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                 "--submit-receipt", receipt], capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("provider_evidence_missing", proc.stderr)

    def test_provider_evidence_rejects_arbitrary_job_time_and_hash_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as handle:
                handle.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            receipt = complete_receipt(tmp, source_path=src)
            payload = json.load(open(receipt, encoding="utf-8"))
            payload["provider_job_id"] = "operator-invented-job"
            write_json(receipt, payload)
            mismatch = subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                 "--submit-receipt", receipt], capture_output=True, text=True,
            )
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("provider_evidence_job_id_mismatch", mismatch.stderr)

            receipt = complete_receipt(tmp, source_path=src)
            payload = json.load(open(receipt, encoding="utf-8"))
            evidence_path = os.path.join(tmp, payload["provider_evidence"]["path"])
            with open(evidence_path, "a", encoding="utf-8") as handle:
                handle.write("\n")
            drift = subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                 "--submit-receipt", receipt], capture_output=True, text=True,
            )
            self.assertNotEqual(drift.returncode, 0)
            self.assertIn("provider_evidence_sha256_mismatch", drift.stderr)

    def test_provider_evidence_requires_project_containment_and_timezone(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as handle:
                handle.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            receipt = complete_receipt(tmp, source_path=src)
            payload = json.load(open(receipt, encoding="utf-8"))
            payload["provider_evidence"]["path"] = "../outside.json"
            write_json(receipt, payload)
            outside = subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                 "--submit-receipt", receipt], capture_output=True, text=True,
            )
            self.assertNotEqual(outside.returncode, 0)
            self.assertIn("provider_evidence_path_outside_project", outside.stderr)

            receipt = complete_receipt(tmp, source_path=src)
            payload = json.load(open(receipt, encoding="utf-8"))
            payload["submitted_at"] = "2026-08-20T12:00:00"
            payload["provider_evidence"]["ui_observation"]["observed_at"] = payload["submitted_at"]
            write_json(receipt, payload)
            naive = subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                 "--submit-receipt", receipt], capture_output=True, text=True,
            )
            self.assertNotEqual(naive.returncode, 0)
            self.assertIn("submitted_at_not_timezone_aware_iso8601", naive.stderr)

    def test_manual_submit_receipt_requires_named_attestation(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            set_video_route(tmp, "manual", "manual")
            write_manual_adapter(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            receipt = complete_receipt(tmp, source_path=src)
            payload = json.load(open(receipt, encoding="utf-8"))
            payload["manual_attestation"] = {"reviewer": "", "notes": ""}
            with open(receipt, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            proc = subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                 "--submit-receipt", receipt], capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("manual_receipt_reviewer_missing", proc.stderr)

    def test_manual_v1_named_receipt_remains_registerable(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            set_video_route(tmp, "manual", "manual")
            write_manual_adapter(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as handle:
                handle.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            receipt = complete_receipt(tmp, source_path=src)
            payload = json.load(open(receipt, encoding="utf-8"))
            payload["schema_version"] = 1
            payload.pop("provider_evidence", None)
            write_json(receipt, payload)
            subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                 "--submit-receipt", receipt], capture_output=True, text=True, check=True,
            )

    def test_receipt_must_bind_exact_model_channel_controls_and_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            receipt = complete_receipt(tmp, source_path=src)
            with open(receipt, encoding="utf-8") as f:
                payload = json.load(f)
            payload["model"] = "Veo 3.1"
            with open(receipt, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            proc = subprocess.run(
                [sys.executable, JOBS, tmp, "--register", src, "--clip", "1", "--take", "1",
                 "--submit-receipt", receipt], capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("receipt_model_mismatch", proc.stderr)

    def test_manifest_freshness_binds_compiled_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            manifest = json.load(open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8"))
            prompt = os.path.join(tmp, manifest["jobs"][0]["takes"][0]["prompt_path"])
            with open(prompt, "a", encoding="utf-8") as f:
                f.write("\nmanual drift\n")
            with self.assertRaisesRegex(SystemExit, "prompt"):
                video_jobs.load_manifest(tmp)

    def test_register_records_only_receipt_attested_frame_binding(self):
        """First-frame evidence comes from the actual submit receipt only."""
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            subprocess.run(register_cli(tmp, src), capture_output=True, text=True, check=True)
            with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), encoding="utf-8") as f:
                take = json.load(f)["jobs"][0]["takes"][0]
            expected = video_jobs.mv_utils.content_hash(
                os.path.join(tmp, "出图", "段落", "图片", "Clip_001.png")
            )
            self.assertEqual(take["first_frame_sha256"], expected)
            self.assertEqual(take["submit_receipt"]["submitted_refs"][0]["sha256"], expected)
            self.assertNotIn("generation", take)

    def test_schema_v4_rejects_uncompiled_generation_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "clip.mp4")
            with open(src, "wb") as f:
                f.write(b"fake mp4 bytes")
            subprocess.run([sys.executable, JOBS, tmp], capture_output=True, text=True, check=True)
            proc = subprocess.run(
                register_cli(tmp, src, extra=["--generation-param", "cfg=7.5"]),
                capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("未编译", proc.stderr)

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
            subprocess.run(register_cli(tmp, src), capture_output=True, text=True, check=True)
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
            subprocess.run(register_cli(tmp, src), capture_output=True, text=True, check=True)
            subprocess.run([
                sys.executable, JOBS, tmp, "--score", "1", "--take", "1",
                "--motion-score", "5", "--identity-score", "5", "--beat-score", "5",
                "--clarity-score", "5", "--reviewer", "editor",
            ], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, JOBS, tmp, "--select", "1", "--take", "1"], capture_output=True, text=True, check=True)
            with open(src, "wb") as f:
                f.write(b"take-v2")
            subprocess.run(register_cli(tmp, src), capture_output=True, text=True, check=True)
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
            subprocess.run(register_cli(tmp, src), capture_output=True, text=True, check=True)
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
            subprocess.run(register_cli(tmp, src), capture_output=True, text=True, check=True)
            proc = subprocess.run([
                sys.executable, JOBS, tmp, "--select", "1", "--take", "1",
                "--waiver-reason", "director accepts rough motion",
            ], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("不能匿名", proc.stderr)


if __name__ == "__main__":
    unittest.main()
