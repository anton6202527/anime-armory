#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV stage output receipts and guarded progress completion.

This module checks what a stage *produced*.  It deliberately does not reuse
``gate.check()``, whose job is to decide whether a stage may start.  Stage
scripts can call :func:`mark_stage_complete`, or use the CLI:

    python3 completion.py health <作品根> [stage] --json
    python3 completion.py complete <作品根> image
    python3 completion.py complete <作品根> review
    python3 completion.py complete <作品根> handoff --reviewer <name> --notes <notes>
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import contract  # noqa: E402
import mv_utils  # noqa: E402
import provenance as provenance_contract  # noqa: E402


OUTPUT_HEALTH_STAGES = (
    "beat", "lyric_sync", "plan", "semantic_plan", "pacing_check",
    "image", "picture_lock", "video_jobs", "video", "compose",
    "disclosure", "provenance", "review", "handoff",
)
CONTROLLED_COMPLETION_STAGES = frozenset(OUTPUT_HEALTH_STAGES)


_SETTINGS_BY_STAGE = {
    "beat": ("歌曲输入时序",),
    "lyric_sync": ("字幕语言", "演唱口型"),
    "plan": ("MV用途", "歌曲输入时序", "MV视觉风格", "MV规划粒度", "卡点策略", "合成画幅", "出视频规格"),
    "semantic_plan": ("MV用途", "歌曲输入时序"),
    "pacing_check": ("卡点策略",),
    "image": ("生图模型", "生图渠道", "MV一致性增强"),
    "picture_lock": ("合成画幅", "字幕语言", "演唱口型"),
    "video_jobs": ("生视频模型", "生视频渠道", "出视频规格", "演唱口型"),
    "video": ("生视频模型", "生视频渠道", "出视频规格", "演唱口型", "合成画幅"),
    "compose": ("合成画幅", "字幕语言", "演唱口型"),
    "disclosure": (
        "AI视觉使用披露", "发行目标平台", "生图模型", "生图渠道",
        "生视频模型", "生视频渠道",
    ),
    "provenance": ("AI视觉使用披露", "发行目标平台"),
    "review": ("AI视觉使用披露", "发行目标平台"),
    "handoff": ("发行目标平台",),
}


def _strict_int(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = int(value)
    return number if math.isfinite(float(value)) and float(value) == number else None


def _finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _schema_at_least(payload, version):
    actual = _strict_int((payload or {}).get("schema_version"))
    return actual is not None and actual >= version


def _inside_project(root, path):
    try:
        return os.path.commonpath((os.path.abspath(root), os.path.abspath(path))) == os.path.abspath(root)
    except ValueError:
        return False


def _live_c2pa_verification(root, c2pa):
    """Re-run c2patool; persisted booleans are never self-authenticating."""
    if c2pa.get("requested") is not True:
        return []
    errors = []
    output_rel = str(c2pa.get("output") or "")
    output = os.path.abspath(os.path.join(root, output_rel)) if output_rel else ""
    if not output or not _inside_project(root, output) or not os.path.isfile(output):
        return ["C2PA live verify 找不到作品根内 signed output"]
    tool = shutil.which("c2patool")
    if not tool:
        return ["C2PA requested 但当前环境无 c2patool，无法重新验证 signed asset"]

    source = c2pa.get("trust_source")
    trust_argument = ""
    if not isinstance(source, dict):
        errors.append("C2PA 缺可移植 trust_source，无法重放信任链验证")
    elif source.get("kind") == "url":
        raw = str(source.get("url") or "")
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append("C2PA trust_source.url 无效")
        else:
            trust_argument = raw
    elif source.get("kind") == "project_file":
        rel = str(source.get("path") or "")
        path = os.path.abspath(os.path.join(root, rel)) if rel else ""
        current = mv_utils.content_hash(path) if path and _inside_project(root, path) else ""
        if not current or current != source.get("sha256"):
            errors.append("C2PA 项目内 trust anchors 缺失、越界或 SHA-256 已变化")
        else:
            trust_argument = path
    else:
        errors.append("C2PA trust_source.kind 必须是 url 或 project_file")
    if errors:
        return errors

    command = [tool, output, "trust", "--trust_anchors", trust_argument]
    proc = subprocess.run(command, capture_output=True, text=True, cwd=root)
    if proc.returncode:
        return [f"C2PA live verify 执行失败：{(proc.stderr or proc.stdout).strip()}"]
    try:
        store = json.loads((proc.stdout or "").strip())
    except json.JSONDecodeError:
        return ["C2PA live verify 未返回可解析 JSON"]
    if not isinstance(store, dict):
        return ["C2PA live verify 返回值不是 manifest store"]
    live = provenance_contract.evaluate_validation_store(
        store,
        trust_checked=True,
        test_certificate=str(c2pa.get("certificate_profile") or "").lower().startswith("test"),
    )
    required = {
        "structurally_valid": True,
        "signature_valid": True,
        "trusted": True,
    }
    if c2pa.get("timestamp_exception_allowed") is not True:
        required["timestamp_trusted"] = True
    for key, expected in required.items():
        if live.get(key) is not expected:
            errors.append(f"C2PA live verify {key}={live.get(key)!r}，不能完成生产来源链")
    for key in (
        "structurally_valid", "signature_valid", "trust_checked", "trusted",
        "timestamp_validated", "timestamp_trusted", "timestamped",
    ):
        if c2pa.get(key) is not live.get(key):
            errors.append(
                f"C2PA provenance.{key}={c2pa.get(key)!r} 与 live verify={live.get(key)!r} 不一致"
            )
    if c2pa.get("active_manifest") and c2pa.get("active_manifest") != live.get("active_manifest"):
        errors.append("C2PA active_manifest 与 live verify 不一致")
    return errors


def _load_image_receipts():
    """Load the MV-local B14 authority without creating a cross-line dependency."""
    path = os.path.abspath(os.path.join(
        SCRIPT_DIR, "..", "..", "mv-image", "scripts", "image_receipts.py"
    ))
    spec = importlib.util.spec_from_file_location("mv_completion_image_receipts", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load B14 image receipt authority: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_video_authorities():
    """Load the MV-local v4 job and inheritance authorities dynamically."""
    scripts = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "mv-video", "scripts"))
    loaded = {}
    for name in ("video_jobs", "inherit_contract"):
        path = os.path.join(scripts, f"{name}.py")
        spec = importlib.util.spec_from_file_location(f"mv_completion_{name}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load MV video authority: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        loaded[name] = module
    return loaded["video_jobs"], loaded["inherit_contract"]


def _result(stage, errors=None, warnings=None, evidence=None):
    errors = list(errors or [])
    return {
        "kind": "mv_stage_output_health",
        "schema_version": 1,
        "stage": stage,
        "ok": not errors,
        "errors": errors,
        "warnings": list(warnings or []),
        "evidence": evidence or {},
    }


def _payload(root, rel):
    return mv_utils.load_json(os.path.join(root, rel), None)


def _settings_first_errors(root, stage):
    """Require the project settings truth before interpreting any receipt."""
    path = os.path.join(root, "_设置.md")
    if not os.path.isfile(path):
        return ["缺 _设置.md；completion health 不从 _meta.json 猜运行时选择"]
    settings = mv_utils.parse_settings(root)
    if not isinstance(settings, dict):
        return ["_设置.md 无法解析；completion health 必须 settings-first"]
    errors = []
    for key in _SETTINGS_BY_STAGE.get(stage, ()):
        value = str(settings.get(key) or "").strip()
        if not value or value in {"待填", "待定", "（未定）", "unknown"}:
            errors.append(f"_设置.md 缺明确选择：{key}")
    return errors


def _current_binding_errors(root, bindings, *, label, required=()):
    errors = []
    if not isinstance(bindings, dict):
        return [f"{label} 缺 inputs_sha256/hash 绑定"]
    for rel in required:
        if rel not in bindings:
            errors.append(f"{label} 未绑定 {rel}")
    for rel, recorded in bindings.items():
        rel = str(rel or "")
        path = os.path.abspath(os.path.join(root, rel)) if rel else ""
        if not rel or os.path.isabs(rel) or not _inside_project(root, path):
            errors.append(f"{label} 含作品根外或非相对路径绑定：{rel!r}")
            continue
        current = mv_utils.content_hash(path)
        if not current:
            errors.append(f"{label} 绑定的文件不存在：{rel}")
        elif recorded != current:
            errors.append(f"{label} 已过期：{rel} 当前 SHA-256 与收据不符")
    return errors


def _named_review_current(root, review, inputs, outputs=()):
    """A named review is evidence only while all of its bindings are current."""
    if not isinstance(review, dict):
        return False
    if not (
        review.get("accepted") is True
        and _valid_reviewer(review.get("reviewer"))
        and str(review.get("notes") or "").strip()
    ):
        return False
    expected_inputs = dict(inputs or {})
    if review.get("bound_inputs_sha256") != expected_inputs:
        return False
    expected_outputs = dict(outputs or {})
    if expected_outputs and review.get("bound_outputs_sha256") != expected_outputs:
        return False
    for rel, recorded in {**expected_inputs, **expected_outputs}.items():
        if not recorded or recorded != mv_utils.content_hash(os.path.join(root, str(rel))):
            return False
    return True


def _expected_plan_images(plan):
    expected = []
    for clip in (plan or {}).get("clips") or []:
        if not isinstance(clip, dict):
            continue
        if clip.get("image_path"):
            expected.append(str(clip["image_path"]))
        if clip.get("need_end_frame") and clip.get("end_frame_path"):
            expected.append(str(clip["end_frame_path"]))
    return list(dict.fromkeys(expected))


def _health_beat(root):
    rel = "节拍/beatgrid.json"
    payload = _payload(root, rel)
    errors = []
    if not isinstance(payload, dict) or payload.get("kind") != "mv_beatgrid":
        return _result("beat", [f"缺或损坏 {rel}"])
    if _strict_int(payload.get("schema_version")) != 2:
        errors.append("beatgrid 必须是当前 schema v2 mv_beatgrid")
    song = mv_utils.find_song(root)
    if not song:
        errors.append("beatgrid 完成态缺当前 歌/song.*")
    else:
        song_rel = mv_utils.relpath(root, song)
        if payload.get("song") != song_rel:
            errors.append("beatgrid.song 未绑定当前主歌轨路径")
        if payload.get("source_audio_sha256") != mv_utils.content_hash(song):
            errors.append("beatgrid.source_audio_sha256 未绑定当前主歌轨")

    duration = _finite_number(payload.get("duration"))
    if duration is None or duration <= 0:
        errors.append("beatgrid.duration 缺有效正数时长")
    for key in ("beats", "downbeats"):
        raw = payload.get(key)
        values = [_finite_number(value) for value in raw] if isinstance(raw, list) else []
        if not values or any(value is None for value in values):
            errors.append(f"beatgrid.{key} 必须是非空有限时间戳数组")
            continue
        if any(right <= left for left, right in zip(values, values[1:])):
            errors.append(f"beatgrid.{key} 必须严格递增")
        if duration is not None and any(value < 0 or value > duration + 0.15 for value in values):
            errors.append(f"beatgrid.{key} 含歌曲时长外时间戳")

    sections = payload.get("sections")
    section_ranges = []
    if not isinstance(sections, list) or not sections:
        errors.append("beatgrid.sections 必须非空并覆盖全曲")
    else:
        for index, row in enumerate(sections):
            start = _finite_number(row.get("start")) if isinstance(row, dict) else None
            end = _finite_number(row.get("end")) if isinstance(row, dict) else None
            if start is None or end is None or start < 0 or end <= start:
                errors.append(f"beatgrid.sections[{index}] 缺有效 start/end")
                continue
            section_ranges.append((start, end))
        if section_ranges:
            if section_ranges[0][0] > 0.15:
                errors.append("beatgrid.sections 未从歌曲开头覆盖")
            if duration is not None and abs(section_ranges[-1][1] - duration) > 0.15:
                errors.append("beatgrid.sections 未覆盖到歌曲结尾")
            if any(abs(right[0] - left[1]) > 0.15 for left, right in zip(section_ranges, section_ranges[1:])):
                errors.append("beatgrid.sections 存在未声明空洞或重叠")
    if not all(payload.get(key) is True for key in (
        "timing_verified", "downbeats_verified", "sections_verified", "sections_complete",
    )):
        errors.append("beatgrid 拍号/小节相位/段落边界尚未完整验证")
    review = payload.get("timing_review") or {}
    if not (
        isinstance(review, dict) and review.get("accepted") is True
        and _valid_reviewer(review.get("reviewer")) and _valid_notes(review.get("notes"))
    ):
        errors.append("beatgrid 缺具名且含 notes 的 timing_review")
    measured = mv_utils.audio_duration(song) if song else None
    if measured is not None and duration is not None and abs(float(measured) - duration) > 0.25:
        errors.append("beatgrid.duration 与当前主歌轨实测时长不一致")
    return _result("beat", list(dict.fromkeys(errors)), evidence={"receipt": rel})


def _health_plan(root):
    plan_rel = "分镜/clip_plan.json"
    timeline_rel = "分镜/timeline_manifest.json"
    plan = _payload(root, plan_rel)
    timeline = _payload(root, timeline_rel)
    errors = []
    if not isinstance(plan, dict) or plan.get("kind") != "mv_clip_plan":
        return _result("plan", [f"缺或损坏 {plan_rel}"])
    if not isinstance(timeline, dict) or timeline.get("kind") != "mv_timeline_manifest":
        return _result("plan", [f"缺或损坏 {timeline_rel}"])
    if _strict_int(plan.get("schema_version")) != 3:
        errors.append("clip_plan 必须是当前 schema v3")
    if _strict_int(timeline.get("schema_version")) != 3:
        errors.append("timeline_manifest 必须是当前 schema v3")
    if plan.get("root_rel") != "." or timeline.get("root_rel") != ".":
        errors.append("plan/timeline root_rel 必须为可移植的 '.'")

    song = mv_utils.find_song(root)
    inputs = {
        "song": mv_utils.content_hash(song),
        "beatgrid": mv_utils.content_hash(os.path.join(root, "节拍", "beatgrid.json")),
        "lyrics": mv_utils.content_hash(os.path.join(root, "词", "lyrics.md")),
        "blueprint": mv_utils.content_hash(os.path.join(root, "视觉蓝图.md")),
        "alignment": mv_utils.content_hash(os.path.join(root, "字幕", "alignment_report.json")),
        "settings_plan": contract.plan_settings_digest(mv_utils.parse_settings(root)),
    }
    if not inputs["song"] or not inputs["beatgrid"] or not inputs["blueprint"]:
        errors.append("clip_plan 当前承重输入 song/beatgrid/blueprint 不完整")
    if plan.get("inputs_sha256") != inputs:
        errors.append("clip_plan.inputs_sha256 未精确绑定当前规划输入与 settings digest")

    clips = plan.get("clips")
    if not isinstance(clips, list) or not clips:
        errors.append("clip_plan.clips 必须是非空数组")
        clips = []
    clip_ids = [str(row.get("clip_id") or "") for row in clips if isinstance(row, dict)]
    if len(clip_ids) != len(clips) or any(not value for value in clip_ids) or len(set(clip_ids)) != len(clip_ids):
        errors.append("clip_plan clip_id 缺失或重复")
    for index, row in enumerate(clips):
        if not isinstance(row, dict):
            continue
        start = _finite_number(row.get("start"))
        end = _finite_number(row.get("end"))
        duration = _finite_number(row.get("duration"))
        if (start is None or end is None or duration is None or start < 0
                or end <= start or abs((end - start) - duration) > 0.002):
            errors.append(f"clip_plan.clips[{index}] 时间范围无效或不守恒")

    plan_sha = mv_utils.content_hash(os.path.join(root, plan_rel))
    if timeline.get("source_clip_plan_sha256") != plan_sha:
        errors.append("timeline_manifest 未绑定当前 clip_plan")
    song_rel = mv_utils.relpath(root, song) if song else ""
    if timeline.get("song_path") != song_rel:
        errors.append("timeline_manifest.song_path 未绑定当前主歌轨")
    if timeline.get("beatgrid_path") != "节拍/beatgrid.json":
        errors.append("timeline_manifest.beatgrid_path 无效")
    if timeline.get("audio_policy") != "locked_master_song_only; generated_clip_audio_discarded":
        errors.append("timeline_manifest.audio_policy 未锁定原始主歌轨")

    rate = _strict_int(timeline.get("rate"))
    timebase = timeline.get("timebase") or {}
    if rate is None or rate <= 0:
        errors.append("timeline_manifest.rate 必须是正整数帧率")
    if not (
        isinstance(timebase, dict) and timebase.get("rate") == rate
        and timebase.get("unit") == "frame" and timebase.get("quantized") is True
    ):
        errors.append("timeline_manifest.timebase 不是当前 integer-frame 合同")
    timeline_clips = timeline.get("clips")
    if not isinstance(timeline_clips, list):
        timeline_clips = []
        errors.append("timeline_manifest.clips 必须是数组")
    if [str(row.get("clip_id") or "") for row in timeline_clips if isinstance(row, dict)] != clip_ids:
        errors.append("timeline_manifest 未精确覆盖 clip_plan 顺序/集合")
    if rate:
        cursor = int(math.floor(float(clips[0].get("start") or 0) * rate + 0.5)) if clips else 0
        for index, (source, row) in enumerate(zip(clips, timeline_clips)):
            if not isinstance(source, dict) or not isinstance(row, dict):
                continue
            source_end = _finite_number(source.get("end"))
            expected_end = (
                max(cursor + 1, int(math.floor(source_end * rate + 0.5)))
                if source_end is not None else None
            )
            values = tuple(_strict_int(row.get(key)) for key in (
                "start_frame", "end_frame", "duration_frames",
            ))
            if (expected_end is None or None in values or values[0] != cursor
                    or values[1] != expected_end or values[2] != expected_end - cursor
                    or values[2] <= 0):
                errors.append(f"timeline_manifest.clips[{index}] integer-frame 边界与 plan 不一致")
                if expected_end is not None:
                    cursor = expected_end
                continue
            for key, expected in (
                ("start", values[0] / rate), ("end", values[1] / rate),
                ("duration", values[2] / rate),
            ):
                actual = _finite_number(row.get(key))
                if actual is None or abs(actual - expected) > 1e-6:
                    errors.append(f"timeline_manifest.clips[{index}].{key} 未量化到整数帧")
                    break
            cursor = values[1]
    return _result(
        "plan", list(dict.fromkeys(errors)),
        evidence={"clip_plan": plan_rel, "timeline": timeline_rel, "clips": len(clip_ids)},
    )


def _health_pacing_check(root):
    rel = "评分/pacing_prescore.json"
    payload = _payload(root, rel)
    errors = []
    if not isinstance(payload, dict) or payload.get("kind") != "mv_pacing_prescore":
        return _result("pacing_check", [f"缺或损坏 {rel}"])
    if _strict_int(payload.get("schema_version")) != 3:
        errors.append("pacing_prescore 必须是当前 schema v3")
    expected = {
        "分镜/clip_plan.json": mv_utils.content_hash(os.path.join(root, "分镜", "clip_plan.json")),
        "节拍/beatgrid.json": mv_utils.content_hash(os.path.join(root, "节拍", "beatgrid.json")),
    }
    song = mv_utils.find_song(root)
    if song:
        expected[mv_utils.relpath(root, song)] = mv_utils.content_hash(song)
    if any(not digest for digest in expected.values()) or payload.get("inputs_sha256") != expected:
        errors.append("pacing_prescore.inputs_sha256 未精确绑定当前 plan/beatgrid/song")
    if payload.get("blocked") is not False:
        errors.append("pacing_prescore 仍为 blocked 或缺明确 false")
    if _finite_number(payload.get("pacing_score")) is None:
        errors.append("pacing_prescore 缺有限 pacing_score")
    if not isinstance(payload.get("metrics"), dict):
        errors.append("pacing_prescore.metrics 必须是完整 object")
    return _result("pacing_check", errors, evidence={"receipt": rel})


def _health_picture_lock(root):
    rel = "制片/picture_lock.json"
    payload = _payload(root, rel)
    errors = []
    if not isinstance(payload, dict) or payload.get("kind") != "mv_picture_lock":
        return _result("picture_lock", [f"缺或损坏 {rel}"])
    if _strict_int(payload.get("schema_version")) != 2:
        errors.append("picture_lock 必须是当前 schema v2")
    if payload.get("accepted") is not True or payload.get("decision") != "picture_locked":
        errors.append("picture_lock 尚未明确 accepted/picture_locked")
    if not _valid_reviewer(payload.get("reviewer")) or not _valid_notes(payload.get("notes")):
        errors.append("picture_lock 缺真实具名 reviewer 或非空 notes")

    plan = _payload(root, "分镜/clip_plan.json") or {}
    timeline = _payload(root, "分镜/timeline_manifest.json") or {}
    if plan.get("kind") != "mv_clip_plan" or _strict_int(plan.get("schema_version")) != 3:
        errors.append("picture_lock 的当前 clip_plan 不是 schema v3")
    if timeline.get("kind") != "mv_timeline_manifest" or _strict_int(timeline.get("schema_version")) != 3:
        errors.append("picture_lock 的当前 timeline_manifest 不是 schema v3")
    editorial_hash = mv_utils.timeline_edit_hash(timeline)
    if not editorial_hash or payload.get("editorial_timeline_sha256") != editorial_hash:
        errors.append("picture_lock 未绑定当前 timeline 编辑合同")
    if payload.get("otio_timeline_sha256") != editorial_hash:
        errors.append("picture_lock 未绑定同一 OTIO 编辑合同")
    required = {
        "分镜/clip_plan.json", "节拍/beatgrid.json", "分镜/animatic.mp4",
        "生产数据/animatic/animatic.json", "生产数据/image_qc/image_qc.json",
        "评分/pacing_prescore.json", "分镜/semantic_prompts.json",
    }
    song = mv_utils.find_song(root)
    if song:
        required.add(mv_utils.relpath(root, song))
    else:
        errors.append("picture_lock 完成态缺当前主歌轨")
    for clip in plan.get("clips") or []:
        if not isinstance(clip, dict):
            continue
        for key in ("image_path", "image_prompt_path", "video_prompt_path"):
            if clip.get(key):
                required.add(str(clip[key]))
        if clip.get("need_end_frame") and clip.get("end_frame_path"):
            required.add(str(clip["end_frame_path"]))
    settings = mv_utils.parse_settings(root)
    vocal = any(
        isinstance(clip, dict) and (
            clip.get("action_family") == "performance_vocal" or clip.get("vocal_lyrics")
        ) for clip in plan.get("clips") or []
    )
    if settings.get("字幕语言") != "无字幕" or (vocal and settings.get("演唱口型") != "关闭"):
        required.add("字幕/alignment_report.json")
    for optional in ("视觉蓝图.md", "词/lyrics.md"):
        if os.path.isfile(os.path.join(root, optional)):
            required.add(optional)
    bindings = payload.get("inputs_sha256")
    errors.extend(_current_binding_errors(
        root, bindings, label="picture_lock.inputs_sha256", required=tuple(sorted(required)),
    ))

    animatic_rel = "生产数据/animatic/animatic.json"
    animatic = _payload(root, animatic_rel)
    if not isinstance(animatic, dict) or animatic.get("kind") != "mv_animatic_render":
        errors.append(f"缺或损坏 {animatic_rel}")
    else:
        if _strict_int(animatic.get("schema_version")) != 2:
            errors.append("animatic report 必须是当前 schema v2")
        if animatic.get("output") != "分镜/animatic.mp4" or animatic.get("output_sha256") != mv_utils.content_hash(
                os.path.join(root, "分镜", "animatic.mp4")):
            errors.append("animatic report 未绑定当前分镜/animatic.mp4")
        if animatic.get("timeline_edit_sha256") != editorial_hash:
            errors.append("animatic report 未绑定当前 timeline 编辑合同")
        animatic_required = ["分镜/clip_plan.json"]
        if song:
            animatic_required.append(mv_utils.relpath(root, song))
        errors.extend(_current_binding_errors(
            root, animatic.get("inputs_sha256"), label="animatic.inputs_sha256",
            required=tuple(animatic_required),
        ))
    return _result("picture_lock", list(dict.fromkeys(errors)), evidence={"receipt": rel})


def _health_semantic_plan(root):
    rel = "分镜/semantic_prompts.json"
    payload = _payload(root, rel)
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = mv_utils.load_json(plan_path, {}) or {}
    errors = []
    if not isinstance(payload, dict) or payload.get("kind") != "mv_semantic_prompts":
        return _result("semantic_plan", [f"缺或损坏 {rel}"])
    if _strict_int(payload.get("schema_version")) != 3:
        errors.append("semantic_prompts 必须是当前 schema v3")
    if payload.get("complete") is not True:
        errors.append("semantic_prompts.complete 必须为 true；partial 收据不能完成阶段")
    current_plan = mv_utils.content_hash(plan_path)
    if payload.get("result_clip_plan_sha256") != current_plan:
        errors.append("semantic_prompts 未绑定当前注入后的 clip_plan")
    expected_ids = {
        str(row.get("clip_id")) for row in plan.get("clips") or []
        if isinstance(row, dict) and row.get("clip_id")
    }
    receipt_ids = {
        str(row.get("clip_id")) for row in payload.get("clips") or []
        if isinstance(row, dict) and row.get("clip_id")
    }
    if expected_ids != receipt_ids:
        errors.append(
            f"语义覆盖不完整：expected={len(expected_ids)} receipt={len(receipt_ids)}"
        )
    if payload.get("updated_clips") != len(expected_ids):
        errors.append("semantic_prompts.updated_clips 与当前 clip 数不一致")
    prompt_receipts = payload.get("prompt_outputs_sha256")
    if not isinstance(prompt_receipts, dict) or set(prompt_receipts) != expected_ids:
        errors.append("semantic_prompts.prompt_outputs_sha256 未精确覆盖当前 clip 全集")
        prompt_receipts = {}
    for clip in plan.get("clips") or []:
        if not isinstance(clip, dict) or not clip.get("clip_id"):
            continue
        clip_id = str(clip["clip_id"])
        recorded = prompt_receipts.get(clip_id)
        if not isinstance(recorded, dict) or set(recorded) != {"image", "video"}:
            errors.append(f"semantic_prompts 缺 {clip_id} image/video prompt 输出收据")
            continue
        for key, field in (("image", "image_prompt_path"), ("video", "video_prompt_path")):
            prompt_rel = str(clip.get(field) or "")
            current = mv_utils.content_hash(os.path.join(root, prompt_rel)) if prompt_rel else ""
            if not current or recorded.get(key) != current:
                errors.append(f"semantic_prompts {clip_id}.{key} prompt 缺失或已变化")
    inputs = payload.get("inputs_sha256") or {}
    for key, relpath in (("lyrics", "词/lyrics.md"), ("blueprint", "视觉蓝图.md")):
        current = mv_utils.content_hash(os.path.join(root, relpath))
        if current and inputs.get(key) != current:
            errors.append(f"semantic_prompts 已过期：{relpath} 已变化")
    return _result("semantic_plan", errors, evidence={"receipt": rel, "clips": len(expected_ids)})


def _health_image(root):
    plan = _payload(root, "分镜/clip_plan.json") or {}
    qc_rel = "生产数据/image_qc/image_qc.json"
    ledger_rel = "生产数据/image_acceptance/image_acceptance.json"
    qc = _payload(root, qc_rel)
    ledger = _payload(root, ledger_rel)
    errors = []
    warnings = []
    if not isinstance(qc, dict) or qc.get("kind") != "mv_image_qc":
        errors.append(f"缺或损坏 {qc_rel}")
        qc = {}
    qc_version = _strict_int(qc.get("version"))
    if qc_version is None:
        qc_version = _strict_int(qc.get("schema_version"))
    if qc_version is None or qc_version < 3:
        errors.append("image_qc 不是当前 v3 聚合报告；旧报告可读但不能证明完成")
    summary = qc.get("summary") or {}
    if _strict_int(summary.get("hard_blocks")) != 0:
        errors.append(f"image_qc hard_blocks 缺失或不为 0：{summary.get('hard_blocks')!r}")
    if summary.get("verdict") != "ok":
        errors.append(f"image_qc verdict={summary.get('verdict')!r}，逐图完成态只接受 ok")
    precision = (qc.get("qc_environment") or {}).get("precision_level")
    if precision != "full":
        errors.append(f"image_qc precision_level={precision!r}，逐图完成态要求 full")
    qc_hashes = qc.get("assets_sha256") or {}
    if not qc_hashes:
        errors.append("image_qc 缺 assets_sha256，不能证明检查的是当前像素")
    errors.extend(_current_binding_errors(root, qc_hashes, label="image_qc.assets_sha256"))
    provenance = qc.get("generation_provenance") or {}
    if (provenance.get("complete") is not True
            or _strict_int((provenance.get("summary") or {}).get("block")) != 0):
        errors.append("image_qc generation_provenance 必须 complete 且 block=0")

    if not isinstance(ledger, dict) or ledger.get("kind") != "mv_image_acceptance_ledger":
        errors.append(f"缺或损坏逐图双闸账本 {ledger_rel}")
        ledger = {}
    try:
        ledger_audit = _load_image_receipts().audit_ledger(Path(root), ledger=ledger)
    except Exception as exc:
        ledger_audit = {"summary": {}, "rows": []}
        errors.append(f"逐图双闸账本无法复算：{exc}")
    ledger_summary = ledger_audit.get("summary") or {}
    if ledger_summary.get("all_current_accepted") is not True:
        errors.append("逐图双闸账本尚未达到 all_current_accepted=true")
    for row in ledger_audit.get("rows") or []:
        if row.get("status") != "accepted":
            findings = ",".join(str(item) for item in row.get("findings") or [])
            errors.append(f"逐图双闸验收失效：{row.get('asset')} ({findings or 'unknown'})")
    assets = ledger.get("assets") or {}
    expected = (
        set(_expected_plan_images(plan))
        | set(qc_hashes)
        | {str(row.get("asset")) for row in ledger_audit.get("rows") or [] if row.get("asset")}
    )
    audited_assets = {
        str(row.get("asset")) for row in ledger_audit.get("rows") or [] if row.get("asset")
    }
    if set(qc_hashes) != audited_assets:
        missing = sorted(audited_assets - set(qc_hashes))
        extra = sorted(set(qc_hashes) - audited_assets)
        errors.append(
            "image_qc 聚合资产全集与 B14 动态审计不一致"
            f"：missing={missing[:3]} extra={extra[:3]}"
        )
    for rel in sorted(expected):
        path = os.path.join(root, rel)
        current_sha = mv_utils.content_hash(path)
        if not current_sha:
            errors.append(f"计划图片不存在：{rel}")
            continue
        row = assets.get(rel) if isinstance(assets, dict) else None
        current = (row or {}).get("current") or {}
        post = current.get("postflight") or {}
        if post.get("status") != "accepted":
            errors.append(f"图片未逐张 accepted：{rel}")
            continue
        if post.get("asset_sha256") != current_sha:
            errors.append(f"图片验收已过期：{rel} 当前像素 SHA-256 已变化")
        machine = post.get("machine_qc") or {}
        if machine.get("verdict") != "ok" or machine.get("precision_level") != "full":
            errors.append(f"图片机器 QC 未以 full/ok 通过：{rel}")
        visual = post.get("visual_review") or {}
        if visual.get("verdict") not in {"accepted", "pass", "ok"} or not visual.get("reviewer"):
            errors.append(f"图片缺当前像素具名目视签收：{rel}")
    return _result(
        "image", errors, warnings,
        {
            "image_qc": qc_rel,
            "acceptance_ledger": ledger_rel,
            "expected_assets": len(expected),
            "recomputed_summary": ledger_summary,
        },
    )


def _health_video_jobs(root):
    plan_rel = "分镜/clip_plan.json"
    manifest_rel = "出视频/jobs_manifest.json"
    plan = _payload(root, plan_rel) or {}
    manifest = _payload(root, manifest_rel)
    errors = []
    warnings = []
    if not isinstance(manifest, dict) or manifest.get("kind") != "mv_video_jobs":
        return _result("video_jobs", [f"缺或损坏 {manifest_rel}"])
    if _strict_int(manifest.get("schema_version")) != 4:
        errors.append("jobs_manifest 必须是 schema v4；旧任务包可读但不能进入完成态")
    if manifest.get("clip_plan_sha256") != mv_utils.content_hash(os.path.join(root, plan_rel)):
        errors.append("jobs_manifest 已过期：未绑定当前 clip_plan")
    expected = [
        str(row.get("clip_id")) for row in plan.get("clips") or []
        if isinstance(row, dict) and row.get("clip_id")
    ]
    actual = [
        str(row.get("clip_id")) for row in manifest.get("jobs") or []
        if isinstance(row, dict) and row.get("clip_id")
    ]
    if len(actual) != len(set(actual)):
        errors.append("jobs_manifest 有重复 clip_id")
    if expected != actual:
        errors.append(f"jobs_manifest 覆盖不完整：expected={len(expected)} jobs={len(set(actual))}")
    try:
        video_jobs, inherit = _load_video_authorities()
        capability = video_jobs.video_capabilities
        if manifest.get("capability_graph_version") != capability.CAPABILITY_GRAPH_VERSION:
            errors.append("jobs_manifest capability_graph_version 不是当前能力图版本")
        if manifest.get("capability_graph_sha256") != capability.graph_sha256():
            errors.append("jobs_manifest capability_graph_sha256 已过期")
        for message in video_jobs.freshness_errors(root, manifest):
            errors.append(f"jobs_manifest freshness：{message}")
        expected_freshness = video_jobs.build_freshness_snapshot(root, manifest)
        if manifest.get("freshness") != expected_freshness:
            errors.append("jobs_manifest freshness snapshot 未精确覆盖当前 settings/plan/image_qc/prompts/references/implementation")
        snapshot = manifest.get("freshness") or {}
        for rel in ("_设置.md", "分镜/clip_plan.json", "生产数据/image_qc/image_qc.json"):
            if not (snapshot.get("project_files") or {}).get(rel):
                errors.append(f"jobs_manifest freshness 缺当前承重输入：{rel}")
        for rel, digest in (snapshot.get("project_files") or {}).items():
            if not digest:
                errors.append(f"jobs_manifest freshness 记录空 SHA：{rel}")
        for rel, digest in (snapshot.get("implementation_files") or {}).items():
            if not digest:
                errors.append(f"jobs_manifest implementation freshness 记录空 SHA：{rel}")

        settings = mv_utils.parse_settings(root)
        runtime = contract.runtime_state_from_settings(settings)
        expected_default_model = video_jobs.normalize_model(runtime["video_model"])
        expected_default_channel = video_jobs.normalize_channel(runtime["video_channel"])
        if str(manifest.get("video_model") or "") != str(expected_default_model):
            errors.append("jobs_manifest.video_model 与当前 _设置.md 不一致")
        if str(manifest.get("video_channel") or manifest.get("backend") or "") != str(expected_default_channel):
            errors.append("jobs_manifest.video_channel 与当前 _设置.md 不一致")
        if str(manifest.get("video_spec") or "") != str(runtime["video_spec"]):
            errors.append("jobs_manifest.video_spec 与当前 _设置.md 不一致")

        adapter = None
        adapter_rel = str(manifest.get("provider_adapter_path") or "")
        if adapter_rel and os.path.isabs(adapter_rel):
            errors.append("jobs_manifest provider_adapter_path 不得是不可移植绝对路径")
        if adapter_rel and not os.path.isabs(adapter_rel):
            adapter = _payload(root, adapter_rel)
            if manifest.get("provider_adapter_sha256") != capability.stable_hash(adapter):
                errors.append("jobs_manifest provider adapter hash 已过期")
        try:
            expected_default_route = video_jobs.resolve_provider_route(
                expected_default_model, expected_default_channel, adapter, "completion:default"
            )
        except SystemExit as exc:
            errors.append(f"默认 capability route 不可执行：{exc}")
            expected_default_route = {}
        if expected_default_route and manifest.get("provider_route") != expected_default_route:
            errors.append("jobs_manifest.provider_route 与当前 settings/capability authority 不一致")
        plan_by_id = {
            str(row.get("clip_id")): row for row in plan.get("clips") or []
            if isinstance(row, dict) and row.get("clip_id")
        }
        for job in manifest.get("jobs") or []:
            if not isinstance(job, dict):
                errors.append("jobs_manifest.jobs 含非 object 行")
                continue
            clip_id = str(job.get("clip_id") or "?")
            clip = plan_by_id.get(clip_id) or {}
            model = video_jobs.normalize_model(clip.get("video_model") or expected_default_model)
            channel = video_jobs.normalize_channel(
                clip.get("video_channel") or clip.get("video_backend") or expected_default_channel
            )
            try:
                expected_route = video_jobs.resolve_provider_route(
                    model, channel, adapter, f"completion:{clip_id}"
                )
            except SystemExit as exc:
                errors.append(f"{clip_id} capability route 不可执行：{exc}")
                expected_route = {}
            route = job.get("provider_route") or {}
            if job.get("video_model") != model or (job.get("video_channel") or job.get("backend")) != channel:
                errors.append(f"{clip_id} model×channel 未继承当前设置/clip override")
            if expected_route and route != expected_route:
                errors.append(f"{clip_id} provider_route 与当前 capability authority 不一致")
            takes = job.get("takes") or []
            if not takes:
                errors.append(f"{clip_id} 缺 planned takes")
            for take in takes:
                if not isinstance(take, dict):
                    errors.append(f"{clip_id} takes 含非 object 行")
                    continue
                take_id = str(take.get("take_id") or "?")
                controls = take.get("compiled_request_controls")
                if not isinstance(controls, dict):
                    errors.append(f"{clip_id}/{take_id} 缺 compiled_request_controls")
                elif take.get("compiled_request_controls_sha256") != capability.stable_hash(controls):
                    errors.append(f"{clip_id}/{take_id} compiled controls hash 不一致")
                planned = take.get("planned_request_controls")
                if not isinstance(planned, dict):
                    errors.append(f"{clip_id}/{take_id} 缺 planned_request_controls")
                elif take.get("planned_request_controls_sha256") != capability.stable_hash(planned):
                    errors.append(f"{clip_id}/{take_id} planned controls hash 不一致")
                if take.get("provider_route") != expected_route:
                    errors.append(f"{clip_id}/{take_id} provider_route 未绑定当前 capability authority")
                submit_prompt = str(take.get("submit_prompt") or "")
                if take.get("submit_prompt_sha256") != hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest():
                    errors.append(f"{clip_id}/{take_id} submit_prompt_sha256 无效")
                prompt_rel = str(take.get("prompt_path") or "")
                prompt_text = mv_utils.read_text(os.path.join(root, prompt_rel)) if prompt_rel else ""
                for finding in inherit.check_compiled_prompt(
                    prompt_text, take, model, allow_legacy=False,
                ):
                    if finding.get("level") == "block":
                        errors.append(
                            f"{clip_id}/{take_id} compiled prompt：{finding.get('code')}"
                        )
                    else:
                        warnings.append(
                            f"{clip_id}/{take_id} compiled prompt：{finding.get('code')}"
                        )
        for unit in manifest.get("sequence_units") or []:
            if not isinstance(unit, dict):
                errors.append("sequence_units 含非 object 行")
                continue
            controls = unit.get("compiled_request_controls")
            if not isinstance(controls, dict) or unit.get("compiled_request_controls_sha256") != capability.stable_hash(controls):
                errors.append(f"{unit.get('unit_id') or '?'} sequence compiled controls 缺失/失配")
            planned = unit.get("planned_request_controls")
            if not isinstance(planned, dict) or unit.get("planned_request_controls_sha256") != capability.stable_hash(planned):
                errors.append(f"{unit.get('unit_id') or '?'} sequence planned controls 缺失/失配")
            try:
                expected_unit_route = video_jobs.resolve_provider_route(
                    video_jobs.normalize_model(unit.get("video_model")),
                    video_jobs.normalize_channel(unit.get("video_channel")),
                    adapter, f"completion:{unit.get('unit_id') or '?'}",
                )
            except SystemExit as exc:
                errors.append(f"{unit.get('unit_id') or '?'} sequence capability route 不可执行：{exc}")
                expected_unit_route = {}
            if expected_unit_route and unit.get("provider_route") != expected_unit_route:
                errors.append(f"{unit.get('unit_id') or '?'} sequence provider_route 已过期")
            prompt_rel = str(unit.get("prompt_path") or "")
            if not prompt_rel or not mv_utils.content_hash(os.path.join(root, prompt_rel)):
                errors.append(f"{unit.get('unit_id') or '?'} sequence prompt 缺失")
    except Exception as exc:
        errors.append(f"video v4 authority 无法复算：{exc}")
    return _result(
        "video_jobs", errors, warnings,
        evidence={"manifest": manifest_rel, "jobs": len(actual), "schema_version": manifest.get("schema_version")},
    )


def _health_video(root):
    timeline = _payload(root, "分镜/timeline_manifest.json") or {}
    manifest = _payload(root, "出视频/jobs_manifest.json") or {}
    qc_rel = "生产数据/video_qc/video_qc.json"
    qc = _payload(root, qc_rel)
    errors = list(_health_video_jobs(root)["errors"])
    warnings = []
    settings = mv_utils.parse_settings(root)
    if settings.get("演唱口型", "关闭") != "关闭":
        alignment_errors, alignment_warnings = _alignment_health(root)
        errors.extend(alignment_errors)
        warnings.extend(alignment_warnings)
    selected = {}
    timeline_by_id = {}
    for row in timeline.get("clips") or []:
        if not isinstance(row, dict):
            continue
        timeline_by_id[str(row.get("clip_id") or "")] = row
        rel = row.get("video_path")
        if not rel or not mv_utils.content_hash(os.path.join(root, rel)):
            errors.append(f"timeline clip {row.get('clip_id') or '?'} 缺当前选中视频")
        else:
            selected[str(rel)] = mv_utils.content_hash(os.path.join(root, rel))
    timeline_ids = set(timeline_by_id)
    job_ids = {
        str(row.get("clip_id")) for row in manifest.get("jobs") or []
        if isinstance(row, dict) and row.get("clip_id")
    }
    if timeline_ids != job_ids:
        errors.append(
            f"timeline/jobs clip 覆盖不一致：timeline={len(timeline_ids)} jobs={len(job_ids)}"
        )
    try:
        _video_jobs, inherit = _load_video_authorities()
        for finding in inherit.check_manifest_freshness(root, manifest):
            message = f"video manifest：{finding.get('code')}"
            (errors if finding.get("level") == "block" else warnings).append(message)
        for job in manifest.get("jobs") or []:
            if not isinstance(job, dict):
                continue
            clip_id = str(job.get("clip_id") or "?")
            for registered_take in job.get("takes") or []:
                if not isinstance(registered_take, dict) or not registered_take.get("video_sha256"):
                    continue
                registered_rel = str(registered_take.get("video_path") or "")
                if (not registered_rel
                        or registered_take.get("video_sha256") != mv_utils.content_hash(os.path.join(root, registered_rel))):
                    errors.append(f"{clip_id}/{registered_take.get('take_id') or '?'} 登记视频 hash 已过期")
                for finding in inherit.check_submit_receipt(root, registered_take, job):
                    if finding.get("level") == "block":
                        errors.append(
                            f"{clip_id}/{registered_take.get('take_id') or '?'} submit receipt：{finding.get('code')}"
                        )
                    else:
                        warnings.append(
                            f"{clip_id}/{registered_take.get('take_id') or '?'} submit receipt：{finding.get('code')}"
                        )
            selected_take = str(job.get("selected_take") or "")
            take = next(
                (row for row in job.get("takes") or []
                 if isinstance(row, dict) and str(row.get("take_id") or "") == selected_take),
                None,
            )
            if not selected_take or not isinstance(take, dict):
                errors.append(f"{clip_id} 缺 selected_take")
                continue
            source_rel = str(take.get("video_path") or "")
            selected_rel = str(job.get("selected_video_path") or "")
            timeline_rel = str((timeline_by_id.get(clip_id) or {}).get("video_path") or "")
            source_sha = mv_utils.content_hash(os.path.join(root, source_rel))
            selected_sha = mv_utils.content_hash(os.path.join(root, selected_rel))
            if not source_sha or take.get("video_sha256") != source_sha:
                errors.append(f"{clip_id}/{selected_take} 登记视频缺失或 video_sha256 已过期")
            if not selected_sha or selected_sha != source_sha:
                errors.append(f"{clip_id} 挑版副本不是当前 registered take")
            if timeline_rel != selected_rel:
                errors.append(f"{clip_id} timeline 未指向 jobs_manifest 当前挑版")
            if take.get("status") != "selected":
                errors.append(f"{clip_id}/{selected_take} 未标记 selected")

        capability = _video_jobs.video_capabilities
        for unit in manifest.get("sequence_units") or []:
            if not isinstance(unit, dict) or unit.get("status") != "split_registered":
                continue
            cut_map = unit.get("verified_cut_map") or {}
            cut_body = dict(cut_map) if isinstance(cut_map, dict) else {}
            cut_hash = cut_body.pop("cut_map_sha256", "")
            try:
                boundaries = [float(value) for value in cut_map.get("actual_boundaries_seconds") or []]
                source_duration = float(unit.get("source_duration"))
            except (AttributeError, TypeError, ValueError):
                boundaries, source_duration = [], -1.0
            if (
                cut_map.get("kind") != "mv_video_sequence_cut_map"
                or _strict_int(cut_map.get("schema_version")) != 1
                or cut_hash != capability.stable_hash(cut_body)
                or cut_map.get("source_sha256") != unit.get("source_sha256")
                or not _valid_reviewer(cut_map.get("reviewer"))
                or not str(cut_map.get("notes") or "").strip()
                or cut_map.get("review_method") not in {
                    "frame_accurate_visual_review", "nle_marker_export", "provider_shot_metadata_verified",
                }
                or len(boundaries) != len(unit.get("clip_ids") or []) + 1
                or any(right <= left for left, right in zip(boundaries, boundaries[1:]))
                or not boundaries or abs(boundaries[0]) > 1 / 24
                or source_duration <= 0 or abs(boundaries[-1] - source_duration) > max(1 / 24, source_duration * 0.01)
            ):
                errors.append(f"{unit.get('unit_id') or '?'} sequence verified cut map 无效")

        inherit_rel = "生产数据/video_inherit_contract/inherit_contract.json"
        persisted = _payload(root, inherit_rel)
        if not isinstance(persisted, dict) or persisted.get("kind") != "mv_video_inherit_contract":
            errors.append(f"缺或损坏 {inherit_rel}")
        else:
            if not _schema_at_least(persisted, 2):
                errors.append("inherit_contract 必须是当前 schema v2")
            if (persisted.get("summary") or {}).get("hard_blocks", 0):
                errors.append("persisted inherit_contract 仍有 hard block")
            errors.extend(_current_binding_errors(
                root, persisted.get("inputs_sha256") or {},
                label="inherit_contract.inputs_sha256",
                required=(
                    "分镜/clip_plan.json", "出视频/jobs_manifest.json",
                    "设定/identity_registry.json", "分镜/reference_plan.json",
                ),
            ))
        recomputed = inherit.build_report(root)
        if (recomputed.get("summary") or {}).get("hard_blocks", 0):
            errors.append("当前重算 inherit_contract 仍有 hard block")
    except Exception as exc:
        errors.append(f"video inheritance/submit authority 无法复算：{exc}")
    if not isinstance(qc, dict) or qc.get("kind") != "mv_video_qc":
        return _result("video", errors + [f"缺或损坏 {qc_rel}"], warnings)
    if not _schema_at_least(qc, 2):
        errors.append("video_qc 必须是当前 schema v2")
    if (_strict_int((qc.get("summary") or {}).get("hard_blocks")) != 0
            or (qc.get("summary") or {}).get("verdict") == "block"):
        errors.append("video_qc 仍有 hard block")
    recorded = qc.get("selected_video_sha256") or {}
    if selected != recorded:
        errors.append("video_qc 未精确绑定 timeline 当前选中视频全集")
    semantic = qc.get("semantic_review") or {}
    if not (
        semantic.get("accepted") is True
        and _valid_reviewer(semantic.get("reviewer"))
        and str(semantic.get("notes") or "").strip()
        and semantic.get("bound_video_sha256") == recorded
    ):
        errors.append("视频缺绑定当前选中视频全集的具名语义签收")
    seam_hash = mv_utils.json_hash([
        row.get("seam_contract") or {} for row in qc.get("seams") or []
        if isinstance(row, dict)
    ])
    if semantic.get("bound_seam_contract_sha256") != seam_hash:
        errors.append("视频语义签收未绑定当前逐缝合同")
    errors.extend(_current_binding_errors(
        root, qc.get("inputs_sha256") or {}, label="video_qc.inputs_sha256",
        required=("分镜/clip_plan.json", "分镜/timeline_manifest.json"),
    ))
    return _result(
        "video", errors, warnings,
        evidence={"video_qc": qc_rel, "selected": len(selected), "jobs_schema": manifest.get("schema_version")},
    )


def _walk_otio_integer_frames(value, path="$"):
    errors = []
    if isinstance(value, dict):
        schema = str(value.get("OTIO_SCHEMA") or "")
        if schema.startswith("RationalTime."):
            frame = value.get("value")
            rate = value.get("rate")
            if isinstance(frame, bool) or not isinstance(frame, int):
                errors.append(f"OTIO 非整数帧 RationalTime：{path}.value={frame!r}")
            if not isinstance(rate, (int, float)) or isinstance(rate, bool) or not math.isfinite(float(rate)) or float(rate) <= 0:
                errors.append(f"OTIO 非法帧率：{path}.rate={rate!r}")
        for key, item in value.items():
            errors.extend(_walk_otio_integer_frames(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_walk_otio_integer_frames(item, f"{path}[{index}]"))
    return errors


def _otio_health(root):
    otio_rel = "分镜/timeline.otio"
    receipt_rel = "生产数据/otio/otio_receipt.json"
    timeline_rel = "分镜/timeline_manifest.json"
    beat_rel = "节拍/beatgrid.json"
    otio = _payload(root, otio_rel)
    receipt = _payload(root, receipt_rel)
    timeline = _payload(root, timeline_rel) or {}
    errors = []
    if not isinstance(otio, dict) or otio.get("OTIO_SCHEMA") != "Timeline.1":
        errors.append(f"缺或损坏 {otio_rel}")
    else:
        errors.extend(_walk_otio_integer_frames(otio))
        tracks = ((otio.get("tracks") or {}).get("children") or [])
        kinds = [str(row.get("kind") or "") for row in tracks if isinstance(row, dict)]
        if kinds.count("Video") != 1 or kinds.count("Audio") != 1 or len(kinds) != 2:
            errors.append("OTIO 必须精确包含一条 V1 Video 与一条 A1 Audio track")
    if not isinstance(receipt, dict) or receipt.get("kind") != "mv_otio_export_receipt":
        return errors + [f"缺或损坏 {receipt_rel}"]
    if not _schema_at_least(receipt, 3):
        errors.append("OTIO receipt 必须是 schema v3 integer-frame 合同")
    timebase = receipt.get("timebase") or {}
    if timebase.get("unit") != "frame" or timebase.get("integral_rational_time") is not True:
        errors.append("OTIO receipt 未声明 frame + integral_rational_time=true")
    previous_end = 0
    for row in timeline.get("clips") or []:
        values = tuple(row.get(key) for key in ("start_frame", "end_frame", "duration_frames"))
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            errors.append(f"timeline clip {row.get('clip_id') or '?'} 缺 integer-frame 边界")
            continue
        start, end, duration = values
        if start != previous_end or end - start != duration or duration <= 0:
            errors.append(f"timeline clip {row.get('clip_id') or '?'} 帧边界不连续/不守恒")
        previous_end = end
    if receipt.get("otio_sha256") != mv_utils.content_hash(os.path.join(root, otio_rel)):
        errors.append("OTIO receipt 未绑定当前 timeline.otio")
    if receipt.get("timeline_edit_sha256") != mv_utils.timeline_edit_hash(timeline):
        errors.append("OTIO 未绑定当前 timeline 编辑合同")
    errors.extend(_current_binding_errors(
        root, receipt.get("inputs_sha256") or {}, label="otio_receipt.inputs_sha256",
        required=(timeline_rel, beat_rel),
    ))
    if receipt.get("missing_media"):
        errors.append(f"OTIO 仍有 {len(receipt.get('missing_media') or [])} 个 missing media")
    expected_media = {
        str(row.get("video_path")) for row in timeline.get("clips") or []
        if isinstance(row, dict) and row.get("video_path")
    }
    if timeline.get("song_path"):
        expected_media.add(str(timeline["song_path"]))
    if set((receipt.get("media_sha256") or {}).keys()) != expected_media:
        errors.append(
            "OTIO receipt.media_sha256 未精确覆盖当前 V1/A1 媒体"
            f"：expected={len(expected_media)} actual={len(receipt.get('media_sha256') or {})}"
        )
    errors.extend(_current_binding_errors(
        root, receipt.get("media_sha256") or {}, label="otio_receipt.media_sha256",
    ))
    roundtrip = receipt.get("official_roundtrip") or {}
    if roundtrip.get("status") != "ok" or not str(roundtrip.get("library_version") or "").strip():
        errors.append(
            "OTIO 未通过官方 OpenTimelineIO adapter roundtrip"
            f"：status={roundtrip.get('status')!r}"
        )
    if receipt.get("tracks") != {"video": 1, "audio": 1}:
        errors.append("OTIO receipt 未证明精确 V1/A1 track 结构")
    return errors


def _color_manifest_health(root):
    rel = "生产数据/color/color_input_manifest.json"
    payload = _payload(root, rel)
    timeline = _payload(root, "分镜/timeline_manifest.json") or {}
    if not isinstance(payload, dict) or payload.get("kind") != "mv_color_input_manifest":
        return [f"缺或损坏 {rel}"]
    errors = []
    if _strict_int(payload.get("schema_version")) != 2:
        errors.append("color_input_manifest 必须是 schema v2")
    summary = payload.get("summary") or {}
    if _strict_int(summary.get("hard_blocks")) != 0 or summary.get("verdict") != "ok":
        errors.append(
            f"color_input_manifest 未通过：hard_blocks={summary.get('hard_blocks')} "
            f"verdict={summary.get('verdict')!r}"
        )
    if payload.get("output_space") != "bt709_sdr_limited":
        errors.append("color_input_manifest.output_space 不是 bt709_sdr_limited")
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    if payload.get("timeline_sha256") != mv_utils.content_hash(timeline_path):
        errors.append("color_input_manifest 未绑定当前 timeline_manifest")
    expected_order = []
    for row in timeline.get("clips") or []:
        value = str(row.get("video_path") or "") if isinstance(row, dict) else ""
        if value and value not in expected_order:
            expected_order.append(value)
    expected = set(expected_order)
    row_list = [
        row for row in payload.get("inputs") or []
        if isinstance(row, dict) and row.get("path")
    ]
    rows = {str(row.get("path")): row for row in row_list}
    if len(rows) != len(row_list):
        errors.append("color_input_manifest.inputs 含重复 path")
    if not expected:
        errors.append("timeline 没有可合成的当前选中视频")
    if [str(row.get("path")) for row in row_list] != expected_order:
        errors.append(
            "color_input_manifest 未精确同序覆盖 timeline 当前视频全集"
            f"：expected={len(expected)} actual={len(rows)}"
        )
    current_hashes = {
        path: mv_utils.content_hash(os.path.join(root, path)) for path in expected_order
    }
    if any(not digest for digest in current_hashes.values()) or payload.get("inputs_sha256") != current_hashes:
        errors.append("color_input_manifest.inputs_sha256 不完整或已过期")
    untagged = {}
    for path, row in rows.items():
        current = current_hashes.get(path) or mv_utils.content_hash(os.path.join(root, path))
        if not current or row.get("sha256") != current:
            errors.append(f"color_input_manifest 已过期：{path}")
        classification = row.get("classification")
        transform = str(row.get("ffmpeg_input_filter") or "")
        if classification == "declared_bt709_limited":
            if row.get("interpretation") != "bt709_limited" or "range=tv" not in transform:
                errors.append(f"limited BT.709 input 缺明确解释/limited transform：{path}")
        elif classification == "declared_bt709_full":
            if (row.get("interpretation") != "bt709_full"
                    or "in_range=full" not in transform or "out_range=limited" not in transform):
                errors.append(f"full-range BT.709 input 缺显式 full→limited transform：{path}")
        elif classification == "untagged":
            untagged[path] = current
            if (row.get("interpretation") != "bt709_limited_by_named_source_interpretation"
                    or "range=tv" not in transform):
                errors.append(f"无标签素材未显式解释为 limited BT.709：{path}")
        else:
            errors.append(f"color input classification 不可交付：{path}={classification!r}")
    if untagged:
        acceptance = payload.get("untagged_acceptance") or {}
        if not (
            acceptance.get("accepted") is True
            and acceptance.get("interpret_as") == "bt709"
            and _valid_reviewer(acceptance.get("reviewer"))
            and str(acceptance.get("notes") or "").strip()
            and acceptance.get("bound_inputs_sha256") == untagged
        ):
            errors.append("无标签素材缺具名且绑定当前输入的 Rec.709 interpretation")
    return errors


def _alignment_acceptance_binding(root, payload):
    preaccept = {
        key: value for key, value in payload.items()
        if key not in {"acceptance", "manual_review", "acoustic_evidence"}
    }

    def asset(label, rel):
        return {"path": rel, "sha256": mv_utils.content_hash(os.path.join(root, rel))}

    master = str(payload.get("master_song") or "")
    audio = str(payload.get("audio") or "")
    return {
        "master": asset("master", master),
        "alignment_audio": asset("alignment_audio", audio),
        "lyrics": asset("lyrics", "词/lyrics.md"),
        "ass": asset("ass", "字幕/karaoke.ass"),
        "lrc": asset("lrc", "字幕/lyrics.lrc"),
        "report_preaccept_content_sha256": mv_utils.json_hash(preaccept),
    }


def _alignment_acoustic_valid(payload, expected_binding, lyric_lines):
    evidence = payload.get("acoustic_evidence")
    if not isinstance(evidence, dict):
        return False
    model = evidence.get("model") or {}
    try:
        confidence = float(evidence.get("confidence"))
        threshold = float(evidence.get("threshold"))
    except (TypeError, ValueError):
        return False
    if not all(math.isfinite(value) and 0 <= value <= 1 for value in (confidence, threshold)):
        return False
    rows = evidence.get("per_line") or evidence.get("phonemes") or []
    covered = set()
    for row in rows:
        if not isinstance(row, dict) or isinstance(row.get("line_index"), bool) or not isinstance(row.get("line_index"), int):
            return False
        index = row["line_index"]
        if index < 0 or index >= lyric_lines:
            return False
        try:
            score = float(row.get("score"))
            row_threshold = float(row.get("threshold", threshold))
        except (TypeError, ValueError):
            return False
        if (not math.isfinite(score) or not math.isfinite(row_threshold)
                or score < row_threshold or str(row.get("status") or "pass").lower() not in {"pass", "sufficient"}):
            return False
        covered.add(index)
    return bool(
        evidence.get("kind") == "mv_singing_alignment_acoustic_evidence"
        and _strict_int(evidence.get("schema_version")) == 1
        and str(model.get("name") or "").strip()
        and str(model.get("version") or "").strip()
        and evidence.get("singing_specific") is True
        and evidence.get("calibrated") is True
        and evidence.get("acceptance_eligible") is True
        and str(evidence.get("metric") or "").strip()
        and str(evidence.get("method") or "").strip()
        and confidence >= threshold
        and str(evidence.get("status") or "").lower() in {"pass", "sufficient"}
        and evidence.get("binding") == expected_binding
        and evidence.get("bound_inputs_sha256") == payload.get("inputs_sha256")
        and evidence.get("bound_outputs_sha256") == payload.get("outputs_sha256")
        and covered == set(range(lyric_lines))
    )


def _alignment_stem_timing_errors(root, payload):
    timing = payload.get("stem_master_timing") or {}
    errors = []
    if not isinstance(timing, dict) or timing.get("status") != "pass":
        return ["stem_master_timing 未通过"]
    master_rel = str(payload.get("master_song") or "")
    audio_rel = str(payload.get("audio") or "")

    def asset(rel):
        return {"path": rel, "sha256": mv_utils.content_hash(os.path.join(root, rel))}

    expected = {"master": asset(master_rel), "alignment_audio": asset(audio_rel)}
    if timing.get("bindings") != expected:
        errors.append("stem_master_timing 未绑定当前 master/alignment audio")
    method = str(timing.get("method") or "")
    offset = _finite_number(timing.get("offset_seconds"))
    drift = _finite_number(timing.get("drift_seconds"))
    if offset is None or drift is None:
        errors.append("stem_master_timing 缺有限 offset/drift")

    if audio_rel == master_rel:
        if method != "same_master_file" or offset != 0.0 or drift != 0.0:
            errors.append("对齐音频就是 master 时必须使用 identity 时间基准")
        return errors
    if method == "named_offset_drift_declaration":
        if not _valid_reviewer(timing.get("reviewer")) or not str(timing.get("notes") or "").strip():
            errors.append("显式 stem offset/drift 缺具名 reviewer 或 notes")
    elif method == "automatic_exact_content_hash":
        if expected["master"]["sha256"] != expected["alignment_audio"]["sha256"]:
            errors.append("automatic_exact_content_hash 与当前 master/stem 内容不符")
        if offset != 0.0 or drift != 0.0:
            errors.append("内容完全相同时 offset/drift 必须为 0")
    elif method == "automatic_ffmpeg_rms_envelope_correlation":
        thresholds = timing.get("thresholds") or {}
        if not isinstance(thresholds, dict):
            thresholds = {}
            errors.append("自动 stem timing thresholds 必须是 object")
        minimum = _finite_number(thresholds.get("minimum_correlation"))
        maximum_drift = _finite_number(thresholds.get("maximum_absolute_drift_seconds"))
        search = _finite_number(thresholds.get("search_seconds"))
        maximum_duration_delta = _finite_number(
            thresholds.get("maximum_absolute_duration_delta_seconds")
        )
        if minimum is None or not 0.15 <= minimum <= 1.0:
            errors.append("自动 stem timing 缺有效 minimum_correlation>=0.15")
        if maximum_drift is None or not 0.0 <= maximum_drift <= 0.08:
            errors.append("自动 stem timing 缺有效 maximum_absolute_drift_seconds<=0.08")
        if search is None or not 0.0 < search <= 10.0:
            errors.append("自动 stem timing 缺有效 offset 搜索窗")
        if maximum_duration_delta is None or not 0.0 <= maximum_duration_delta <= 0.25:
            errors.append("自动 stem timing 缺有效时长差阈值<=0.25s")
        windows = timing.get("windows") or []
        correlations = []
        if not isinstance(windows, list) or len(windows) < 3:
            errors.append("自动 stem timing 必须保留至少早/中/晚三个相关性窗口")
        else:
            for index, row in enumerate(windows):
                correlation = _finite_number(row.get("correlation")) if isinstance(row, dict) else None
                window_offset = _finite_number(row.get("offset_seconds")) if isinstance(row, dict) else None
                if correlation is None or window_offset is None:
                    errors.append(f"自动 stem timing window[{index}] 缺 correlation/offset")
                    continue
                correlations.append(correlation)
                if minimum is not None and correlation < minimum:
                    errors.append(f"自动 stem timing window[{index}] 相关性未达阈值")
        recorded_minimum = _finite_number(timing.get("minimum_correlation"))
        if correlations and (
                recorded_minimum is None or abs(recorded_minimum - min(correlations)) > 1e-5):
            errors.append("自动 stem timing minimum_correlation 与窗口证据不一致")
        duration_delta = _finite_number(timing.get("duration_delta_seconds"))
        if (duration_delta is None or maximum_duration_delta is None
                or abs(duration_delta) > maximum_duration_delta):
            errors.append("自动 stem timing 的 stem/master 时长差未通过阈值")
        if drift is None or maximum_drift is None or abs(drift) > maximum_drift:
            errors.append("自动 stem timing drift 未通过阈值")
    else:
        errors.append("非 master 对齐音频缺自动验证或显式具名 offset/drift")
    return errors


def _alignment_health(root):
    rel = "字幕/alignment_report.json"
    payload = _payload(root, rel)
    if not isinstance(payload, dict) or payload.get("kind") != "mv_lyric_alignment_report":
        return [f"缺或损坏 {rel}"], []
    errors = []
    warnings = []
    if _strict_int(payload.get("schema_version")) != 5:
        errors.append("alignment_report 必须是当前 schema v5；旧 fixture 可读但不能完成正式合成")
    if "alignment_confidence" in payload:
        errors.append("schema v5 禁止 alignment_confidence；字符覆盖率不是声学置信度")
    if payload.get("alignment_unit") != "character":
        errors.append("alignment_report 不是字符级强制对齐")
    if payload.get("coverage_metric") != "text_character_mapping_ratio_not_acoustic_confidence":
        errors.append("alignment_report 必须明确字符覆盖率不是声学置信度")
    errors.extend(_alignment_stem_timing_errors(root, payload))
    inputs = payload.get("inputs_sha256") or {}
    outputs = payload.get("outputs_sha256") or {}
    if not isinstance(inputs, dict):
        inputs = {}
        errors.append("alignment_report.inputs_sha256 必须是 object")
    if not isinstance(outputs, dict):
        outputs = {}
        errors.append("alignment_report.outputs_sha256 必须是 object")
    required_inputs = ["词/lyrics.md"]
    song = mv_utils.find_song(root)
    if song:
        required_inputs.append(mv_utils.relpath(root, song))
        if payload.get("master_song") != mv_utils.relpath(root, song):
            errors.append("alignment_report.master_song 未绑定当前主歌轨")
    audio_rel = str(payload.get("audio") or "")
    if not audio_rel or inputs.get(audio_rel) != mv_utils.content_hash(os.path.join(root, audio_rel)):
        errors.append("alignment_report.audio 输入收据缺失或已过期")
    errors.extend(_current_binding_errors(
        root, inputs, label="alignment_report.inputs_sha256", required=tuple(required_inputs),
    ))
    errors.extend(_current_binding_errors(
        root, outputs, label="alignment_report.outputs_sha256",
        required=("字幕/karaoke.ass", "字幕/lyrics.lrc"),
    ))
    try:
        coverage = float(payload.get("character_coverage_ratio"))
    except (TypeError, ValueError):
        coverage = -1.0
        errors.append("alignment_report 缺 character_coverage_ratio")
    aligned_lines = _strict_int(payload.get("aligned_lines"))
    lyric_lines = _strict_int(payload.get("lyric_lines"))
    per_line = []
    for row in payload.get("lines") or []:
        try:
            per_line.append(float(row.get("line_character_coverage")))
        except (AttributeError, TypeError, ValueError):
            per_line.append(0.0)
    text_complete = bool(
        aligned_lines is not None and lyric_lines is not None and aligned_lines == lyric_lines
        and coverage >= 0.9
        and (not per_line or min(per_line) >= 0.85)
        and not payload.get("timing_issues")
    )
    if not text_complete:
        correction = payload.get("low_coverage_correction") or {}
        if not (
            correction.get("applied") is True
            and _valid_reviewer(correction.get("reviewer"))
            and str(correction.get("notes") or "").strip()
            and isinstance(correction.get("corrections"), list)
            and correction.get("corrections")
            and correction.get("bound_outputs_sha256") == outputs
        ):
            errors.append("歌词文本覆盖/时序未达标，必须先具名校正并绑定当前 ASS/LRC")

    expected_binding = _alignment_acceptance_binding(root, payload)
    acceptance = payload.get("acceptance") or {}
    if not isinstance(acceptance, dict):
        acceptance = {}
        errors.append("alignment_report.acceptance 必须是 object")
    route = acceptance.get("route")
    accepted = bool(
        acceptance.get("status") == "accepted"
        and acceptance.get("accepted") is True
        and acceptance.get("binding") == expected_binding
    )
    manual = payload.get("manual_review") or {}
    if not isinstance(manual, dict):
        manual = {}
        errors.append("alignment_report.manual_review 必须是 object")
    manual_current = bool(
        _named_review_current(root, manual, inputs, outputs)
        and manual.get("kind") == "named_full_listening_review"
        and manual.get("verdict") == "pass"
        and manual.get("binding") == expected_binding
        and manual.get("bound_report_preaccept_sha256") == expected_binding["report_preaccept_content_sha256"]
    )
    acoustic_current = _alignment_acoustic_valid(payload, expected_binding, lyric_lines or 0)
    if not accepted:
        errors.append("alignment_report 尚未以当前 binding 正式接受")
    elif route == "named_listening_review":
        if not manual_current:
            errors.append("低/缺声学证据必须由具名逐行听审绑定当前输入输出和报告前置内容")
        elif acceptance.get("evidence_content_sha256") != mv_utils.json_hash(manual):
            errors.append("具名 listening review 内容已在签收后变化")
    elif route == "singing_acoustic_evidence":
        if not acoustic_current:
            errors.append("singing acoustic evidence 未校准、未逐行覆盖或未绑定当前内容")
        elif acceptance.get("evidence_content_sha256") != mv_utils.json_hash(
                payload.get("acoustic_evidence")):
            errors.append("声学证据内容已在签收后变化")
    else:
        errors.append("alignment acceptance route 必须是 singing acoustic evidence 或 named listening review")
    return errors, warnings


def _health_lyric_sync(root):
    errors, warnings = _alignment_health(root)
    return _result(
        "lyric_sync", errors, warnings,
        evidence={"receipt": "字幕/alignment_report.json"},
    )


_DELIVERY_AUDIO_IDENTITY_KIND = "mv_delivery_audio_identity"
_DELIVERY_AUDIO_IDENTITY_CONTRACT = "decoded_pcm_start_middle_end_correlation_v2"
_DELIVERY_AUDIO_IDENTITY_ROLES = {
    "final": "成片_MV.mp4",
    "master": "成片_MV_master.mov",
}
_DELIVERY_AUDIO_IDENTITY_THRESHOLDS = {
    "minimum_correlation": 0.85,
    "maximum_abs_offset_ms": 50.0,
    "maximum_drift_ms": 30.0,
    "maximum_duration_delta_seconds": 0.10,
}


def _delivery_audio_identity_errors(root, payload, song):
    """Validate independent, hash-current PCM evidence for final and master."""
    if not isinstance(payload, dict):
        return ["delivery_qc.audio_identity 必须分别证明 final/master PCM 身份"]
    errors = []
    if (payload.get("kind") != _DELIVERY_AUDIO_IDENTITY_KIND
            or _strict_int(payload.get("schema_version")) != 1
            or payload.get("contract") != _DELIVERY_AUDIO_IDENTITY_CONTRACT):
        errors.append("delivery_qc.audio_identity 不是当前双输出 PCM 身份合同")
    if payload.get("required_roles") != list(_DELIVERY_AUDIO_IDENTITY_ROLES):
        errors.append("delivery_qc.audio_identity.required_roles 必须精确为 final/master")

    song_rel = mv_utils.relpath(root, song)
    song_sha = mv_utils.content_hash(song)
    source = payload.get("source")
    if not isinstance(source, dict):
        source = {}
    if source.get("path") != song_rel or source.get("sha256") != song_sha:
        errors.append("delivery_qc.audio_identity.source 未绑定当前主歌轨")

    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        return errors + ["delivery_qc.audio_identity.outputs 缺 final/master"]
    if set(outputs) != set(_DELIVERY_AUDIO_IDENTITY_ROLES):
        errors.append("delivery_qc.audio_identity.outputs 必须精确覆盖 final/master")
    for role, rel in _DELIVERY_AUDIO_IDENTITY_ROLES.items():
        row = outputs.get(role)
        if not isinstance(row, dict):
            errors.append(f"delivery_qc.audio_identity 缺 {role} PCM 证据")
            continue
        current_sha = mv_utils.content_hash(os.path.join(root, rel))
        if row.get("role") != role or row.get("path") != rel or row.get("sha256") != current_sha:
            errors.append(f"delivery_qc.audio_identity.{role} 未绑定当前 {rel}")
        if row.get("status") != "ok":
            errors.append(f"delivery_qc.audio_identity.{role} status={row.get('status')!r}，必须为 ok")
        if row.get("contract") != _DELIVERY_AUDIO_IDENTITY_CONTRACT:
            errors.append(f"delivery_qc.audio_identity.{role} contract 无效")
        if _strict_int(row.get("sample_rate_hz")) != 8000:
            errors.append(f"delivery_qc.audio_identity.{role} 缺固定 8kHz PCM 比较采样率")
        if row.get("thresholds") != _DELIVERY_AUDIO_IDENTITY_THRESHOLDS:
            errors.append(f"delivery_qc.audio_identity.{role} 阈值不是当前严格合同")

        anchors = row.get("anchors") or []
        labels = [item.get("anchor") for item in anchors if isinstance(item, dict)]
        if len(anchors) != 3 or labels != ["start", "middle", "end"]:
            errors.append(f"delivery_qc.audio_identity.{role} 缺首/中/尾三点证据")
            continue
        correlations = [_finite_number(item.get("correlation")) for item in anchors]
        offsets = [_finite_number(item.get("offset_ms")) for item in anchors]
        if any(value is None for value in correlations + offsets):
            errors.append(f"delivery_qc.audio_identity.{role} 三点 correlation/offset 非有限数")
            continue
        minimum = min(correlations)
        maximum_offset = max(abs(value) for value in offsets)
        drift = max(offsets) - min(offsets)
        if minimum < _DELIVERY_AUDIO_IDENTITY_THRESHOLDS["minimum_correlation"]:
            errors.append(f"delivery_qc.audio_identity.{role} 首/中/尾相关性未达阈值")
        if maximum_offset > _DELIVERY_AUDIO_IDENTITY_THRESHOLDS["maximum_abs_offset_ms"]:
            errors.append(f"delivery_qc.audio_identity.{role} offset 超阈值")
        if drift > _DELIVERY_AUDIO_IDENTITY_THRESHOLDS["maximum_drift_ms"]:
            errors.append(f"delivery_qc.audio_identity.{role} drift 超阈值")
        recorded_minimum = _finite_number(row.get("min_correlation"))
        recorded_offset = _finite_number(row.get("max_abs_offset_ms"))
        recorded_drift = _finite_number(row.get("drift_ms"))
        if recorded_minimum is None or abs(recorded_minimum - minimum) > 1e-5:
            errors.append(f"delivery_qc.audio_identity.{role}.min_correlation 与三点证据不一致")
        if recorded_offset is None or abs(recorded_offset - maximum_offset) > 1e-3:
            errors.append(f"delivery_qc.audio_identity.{role}.max_abs_offset_ms 与三点证据不一致")
        if recorded_drift is None or abs(recorded_drift - drift) > 1e-3:
            errors.append(f"delivery_qc.audio_identity.{role}.drift_ms 与三点证据不一致")

        source_duration = _finite_number(row.get("source_duration_seconds"))
        output_duration = _finite_number(row.get("output_duration_seconds"))
        duration_delta = _finite_number(row.get("duration_delta_seconds"))
        if source_duration is None or output_duration is None or duration_delta is None:
            errors.append(f"delivery_qc.audio_identity.{role} 缺 PCM duration 证据")
        elif (abs((output_duration - source_duration) - duration_delta) > 1e-5
              or abs(duration_delta) > _DELIVERY_AUDIO_IDENTITY_THRESHOLDS["maximum_duration_delta_seconds"]):
            errors.append(f"delivery_qc.audio_identity.{role} PCM duration 差超阈值或不守恒")
    if payload.get("status") != "ok":
        errors.append("delivery_qc.audio_identity 总状态必须为 ok")
    return errors


def _health_compose(root):
    required_files = ("成片_MV.mp4", "成片_MV_master.mov")
    qc_rel = "生产数据/delivery_qc/delivery_qc.json"
    qc = _payload(root, qc_rel)
    errors = [
        f"缺正式交付产物：{rel}" for rel in required_files
        if not mv_utils.content_hash(os.path.join(root, rel))
    ]
    warnings = []
    errors.extend(_otio_health(root))
    errors.extend(_color_manifest_health(root))
    settings = mv_utils.parse_settings(root)
    if settings.get("字幕语言") != "无字幕" or settings.get("演唱口型", "关闭") != "关闭":
        alignment_errors, alignment_warnings = _alignment_health(root)
        errors.extend(alignment_errors)
        warnings.extend(alignment_warnings)
    if not isinstance(qc, dict) or qc.get("kind") != "mv_delivery_qc":
        return _result("compose", errors + [f"缺或损坏 {qc_rel}"], warnings)
    if not _schema_at_least(qc, 3):
        errors.append("delivery_qc 必须是 schema v3；旧 QC 可读但不能证明当前正式交付")
    summary = qc.get("summary") or {}
    if summary.get("hard_blocks", 0) or summary.get("verdict") == "block":
        errors.append("delivery_qc 仍有 hard block")
    required_bindings = list(required_files)
    song = mv_utils.find_song(root)
    if song:
        required_bindings.append(mv_utils.relpath(root, song))
    else:
        errors.append("缺当前主歌轨，无法验证 final/master PCM 身份")
    errors.extend(_current_binding_errors(
        root, qc.get("inputs_sha256") or {}, label="delivery_qc.inputs_sha256",
        required=tuple(required_bindings),
    ))
    runtime = contract.runtime_state_from_settings(settings)
    expected_dimensions = {
        "16:9": [1920, 1080], "9:16": [1080, 1920], "1:1": [1080, 1080],
    }.get(runtime["aspect"])
    expected_delivery = qc.get("expected_delivery") or {}
    if expected_delivery.get("aspect") != runtime["aspect"]:
        errors.append("delivery_qc.expected_delivery.aspect 与当前 _设置.md 不一致")
    if list(expected_delivery.get("dimensions") or []) != list(expected_dimensions or []):
        errors.append("delivery_qc.expected_delivery.dimensions 与当前画幅不一致")
    if song:
        errors.extend(_delivery_audio_identity_errors(root, qc.get("audio_identity"), song))
    file_rows = qc.get("files")
    if not isinstance(file_rows, list):
        file_rows = []
        errors.append("delivery_qc.files 必须是 final/master 数组")
    by_role = {
        str(row.get("role") or ""): row for row in file_rows if isinstance(row, dict)
    }
    if len(file_rows) != 2 or set(by_role) != {"final", "master"}:
        errors.append("delivery_qc.files 必须精确区分 final/master 两个输出")
    for role, rel in _DELIVERY_AUDIO_IDENTITY_ROLES.items():
        row = by_role.get(role)
        current = mv_utils.content_hash(os.path.join(root, rel))
        if not isinstance(row, dict) or row.get("path") != rel or row.get("sha256") != current or not current:
            errors.append(f"delivery_qc.files.{role} 未以作品相对路径和 SHA-256 绑定当前 {rel}")
    file_blocks = [
        block for row in file_rows if isinstance(row, dict)
        for block in row.get("blocks") or []
    ]
    if file_blocks:
        errors.append(f"delivery_qc.files 仍含 blocks：{file_blocks[0]}")
    return _result(
        "compose", errors, warnings,
        evidence={"delivery_qc": qc_rel, "otio": "生产数据/otio/otio_receipt.json", "color": "生产数据/color/color_input_manifest.json"},
    )


def _health_disclosure(root):
    rel = "合规/ai_usage.json"
    payload = _payload(root, rel)
    errors = []
    if not isinstance(payload, dict) or payload.get("kind") != "mv_ai_usage":
        return _result("disclosure", [f"缺或损坏 {rel}"])
    if not _schema_at_least(payload, 2) or payload.get("complete") is not True:
        errors.append("ai_usage 必须是 schema v2 complete 收据")
    reviewer = str(payload.get("reviewer") or "").strip()
    if reviewer in {"", "<name>", "待填", "待定", "unknown"}:
        errors.append("ai_usage 缺真实具名 reviewer")
    if not str(payload.get("human_contribution") or "").strip():
        errors.append("ai_usage 缺人工贡献说明")
    if os.path.isabs(str(payload.get("project_root") or "")):
        errors.append("ai_usage.project_root 不得持久化工作站绝对路径")
    if payload.get("visual_mode") not in contract.AI_VISUAL_USAGE_MODES:
        errors.append("ai_usage.visual_mode 不在契约枚举内")
    if payload.get("video_mode") not in contract.AI_VISUAL_USAGE_MODES:
        errors.append("ai_usage.video_mode 不在契约枚举内")
    runtime = contract.runtime_state_from_settings(mv_utils.parse_settings(root))
    expected_platform = runtime["publish_target"]
    if payload.get("visual_mode") != runtime["ai_visual_usage"]:
        errors.append("ai_usage.visual_mode 与当前 _设置.md AI视觉使用披露不一致")
    if payload.get("video_mode") != runtime["ai_visual_usage"]:
        errors.append("ai_usage.video_mode 与当前 _设置.md AI视觉使用披露不一致")
    if expected_platform != "未定" and payload.get("publish_target") != expected_platform:
        errors.append("ai_usage.publish_target 与当前 _设置.md 发行目标平台不一致")
    for field in ("image_model", "image_channel", "video_model", "video_channel"):
        if payload.get(field) != runtime[field]:
            errors.append(f"ai_usage.{field} 与当前 _设置.md 不一致")
    territories = payload.get("territories") or []
    if not territories or any(str(row).strip() in {"", "未定", "unknown"} for row in territories):
        errors.append("ai_usage.territories 必须明确法域")
    if payload.get("realism") not in {"stylized", "photorealistic", "mixed"}:
        errors.append("ai_usage.realism 未明确")
    if payload.get("real_person_status") not in {"none", "authorized"}:
        errors.append("ai_usage.real_person_status 必须明确为 none 或 authorized")
    if payload.get("music_mode") not in {"human", "AI-assisted", "AI-generated"}:
        errors.append("ai_usage.music_mode 未明确")
    if payload.get("gen_ai_classification") not in {"no_gen_ai", "partly_gen_ai", "fully_gen_ai"}:
        errors.append("ai_usage.gen_ai_classification 无效")
    errors.extend(_current_binding_errors(
        root, payload.get("inputs_sha256") or {}, label="ai_usage.inputs_sha256", required=("_设置.md",),
    ))
    return _result("disclosure", errors, evidence={"receipt": rel})


def _health_provenance(root):
    rel = "合规/provenance.json"
    payload = _payload(root, rel)
    errors = []
    warnings = []
    required = ("成片_MV.mp4", "成片_MV_master.mov", "合规/ai_usage.json")
    if not isinstance(payload, dict) or payload.get("kind") != "mv_provenance":
        return _result("provenance", [f"缺或损坏 {rel}"])
    if _strict_int(payload.get("schema_version")) != 2:
        errors.append("provenance 必须是 schema v2；旧来源清单可读但不能完成")
    if payload.get("complete") is not True:
        errors.append("provenance.complete 必须为 true")
    asset_rows = [
        row for row in payload.get("assets") or [] if isinstance(row, dict) and row.get("path")
    ]
    assets = {str(row.get("path")): row.get("sha256") for row in asset_rows}
    if len(assets) != len(asset_rows):
        errors.append("provenance.assets 含重复 path")
    expected_assets = set(provenance_contract.existing_assets(
        root,
        os.path.join(root, "成片_MV.mp4"),
        os.path.join(root, "成片_MV_master.mov"),
    ))
    c2pa_candidate = payload.get("c2pa") if isinstance(payload.get("c2pa"), dict) else {}
    signed_rel = str((c2pa_candidate or {}).get("output") or "")
    if signed_rel:
        expected_assets.add(signed_rel)
    if set(assets) != expected_assets:
        missing = sorted(expected_assets - set(assets))
        extra = sorted(set(assets) - expected_assets)
        errors.append(
            "provenance.assets 未精确覆盖当前应交付资产全集"
            f"：missing={missing[:3]} extra={extra[:3]}"
        )
    errors.extend(_current_binding_errors(root, assets, label="provenance.assets", required=required))
    errors.extend(_current_binding_errors(
        root, payload.get("inputs_sha256") or {}, label="provenance.inputs_sha256",
        required=("_设置.md", "合规/ai_usage.json"),
    ))
    ai_usage = _payload(root, "合规/ai_usage.json") or {}
    if payload.get("ai_usage") != ai_usage:
        errors.append("provenance.ai_usage 未绑定当前披露内容")
    current_ai_sha = mv_utils.content_hash(os.path.join(root, "合规", "ai_usage.json"))
    if payload.get("ai_usage_sha256") != current_ai_sha:
        errors.append("provenance.ai_usage_sha256 未绑定当前披露文件")
    relationships = payload.get("relationships") or {}
    for field, expected in (
        ("final", "成片_MV.mp4"), ("master", "成片_MV_master.mov"),
        ("disclosure", "合规/ai_usage.json"),
    ):
        if relationships.get(field) != expected:
            errors.append(f"provenance.relationships.{field} 不指向当前标准交付关系")
    ingredients = relationships.get("ingredients") or []
    if not isinstance(ingredients, list) or set(ingredients) != set((payload.get("inputs_sha256") or {}).keys()):
        errors.append("provenance.relationships.ingredients 与 inputs_sha256 不一致")

    c2pa = payload.get("c2pa")
    if not isinstance(c2pa, dict):
        errors.append("provenance 缺分层 C2PA 状态对象")
        c2pa = {}
    for field in (
        "requested", "embedded", "structurally_valid", "signature_valid",
        "trust_checked", "trusted", "timestamp_validated", "timestamp_trusted",
        "timestamped", "timestamp_exception_allowed",
    ):
        if not isinstance(c2pa.get(field), bool):
            errors.append(f"provenance.c2pa.{field} 必须是显式 boolean 分层状态")
    if c2pa.get("timestamped") is not c2pa.get("timestamp_trusted"):
        errors.append("provenance.c2pa.timestamped 必须与 timestamp_trusted 同义，不能把普通签署时间冒充 TSA")
    if c2pa.get("timestamp_trusted") is True and c2pa.get("timestamp_validated") is not True:
        errors.append("provenance.c2pa.timestamp_trusted=true 但 timestamp_validated 不是 true")
    c2pa_manifest_rel = "合规/c2pa_manifest.json"
    current_manifest_sha = mv_utils.content_hash(os.path.join(root, c2pa_manifest_rel))
    if not current_manifest_sha or c2pa.get("manifest_sha256") != current_manifest_sha:
        errors.append("C2PA manifest 缺失或 provenance.c2pa.manifest_sha256 已过期")
    if c2pa.get("requested") is True:
        if c2pa.get("embedded") is not True:
            errors.append("C2PA requested 但 embedded=false")
        if c2pa.get("structurally_valid") is not True:
            errors.append("C2PA structural validation 未通过")
        if c2pa.get("signature_valid") is not True:
            errors.append("C2PA signature validation 未通过")
        if c2pa.get("trust_checked") is not True:
            errors.append("C2PA trust chain 未检查")
        if c2pa.get("trusted") is not True:
            errors.append("C2PA credential 不受信任")
        profile = str(c2pa.get("certificate_profile") or "")
        if profile != "production":
            errors.append(f"C2PA certificate_profile={profile!r}，测试证书不能完成 provenance")
        if c2pa.get("timestamp_trusted") is not True:
            if c2pa.get("timestamp_exception_allowed") is True:
                warnings.append("C2PA production credential 未含可信 TSA 时间戳；当前为显式 no-timestamp 例外")
            else:
                errors.append("C2PA production credential 缺可信 TSA 时间戳，且未记录显式例外")
        output = str(c2pa.get("output") or "")
        current_output_sha = mv_utils.content_hash(os.path.join(root, output)) if output else ""
        if not output or not current_output_sha or c2pa.get("output_sha256") != current_output_sha:
            errors.append("C2PA signed output 缺失或 SHA-256 已过期")
        elif assets.get(output) != current_output_sha:
            errors.append("C2PA signed output 未进入 provenance.assets 当前资产链")
    elif c2pa.get("embedded") is True:
        errors.append("C2PA embedded=true 但 requested 不是 true，状态自相矛盾")
    if c2pa.get("requested") is True:
        errors.extend(_live_c2pa_verification(root, c2pa))
    return _result(
        "provenance", errors, warnings,
        evidence={
            "receipt": rel, "assets": len(assets),
            "c2pa": {
                key: c2pa.get(key) for key in (
                    "requested", "embedded", "structurally_valid", "signature_valid",
                    "trust_checked", "trusted", "timestamp_validated", "timestamp_trusted",
                    "timestamped", "timestamp_exception_allowed", "certificate_profile",
                )
            },
        },
    )


def _review_acceptance(payload):
    human = payload.get("human_signoff") or {}
    accepted = payload.get("accepted") is True and human.get("accepted") is True
    reviewer = human.get("reviewer")
    return accepted, reviewer


_RELEASE_DECISION_CONTRACT = None


def _load_release_decision_contract():
    global _RELEASE_DECISION_CONTRACT
    if _RELEASE_DECISION_CONTRACT is None:
        path = os.path.join(SCRIPT_DIR, "release_decision.py")
        spec = importlib.util.spec_from_file_location("mv_completion_release_contract", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load release decision contract: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _RELEASE_DECISION_CONTRACT = module
    return _RELEASE_DECISION_CONTRACT


def _release_decision_errors(root):
    rel = "合规/release_decision.json"
    payload = _payload(root, rel)
    if not isinstance(payload, dict) or payload.get("kind") != "mv_release_decision":
        return [f"缺或损坏 {rel}"]
    errors = []
    try:
        release_contract = _load_release_decision_contract()
    except Exception as exc:
        return [f"无法加载 release_decision 权威规则：{type(exc).__name__}: {exc}"]
    if _strict_int(payload.get("schema_version")) != 1:
        errors.append("release_decision 必须是 schema v1")
    if payload.get("decision") != "ready_for_handoff":
        errors.append("release_decision 尚未 ready_for_handoff")
    if payload.get("ruleset_version") != release_contract.RULESET_VERSION:
        errors.append(
            f"release_decision ruleset_version={payload.get('ruleset_version')!r} "
            f"不是当前 {release_contract.RULESET_VERSION}"
        )
    operator = str(payload.get("operator") or "").strip()
    if not _valid_reviewer(operator) or not _valid_notes(payload.get("notes")):
        errors.append("release_decision 缺真实具名 operator/notes")
    platforms = payload.get("platforms")
    territories = payload.get("territories")
    if (not isinstance(platforms, list) or not platforms
            or not all(str(row).strip() for row in platforms)
            or not isinstance(territories, list) or not territories
            or not all(str(row).strip() for row in territories)):
        errors.append("release_decision 缺具体平台或法域")
        platforms = platforms if isinstance(platforms, list) else []
        territories = territories if isinstance(territories, list) else []
    disclosure = _payload(root, "合规/ai_usage.json") or {}
    target = str(disclosure.get("publish_target") or "")
    if target in {"", "未定"}:
        errors.append("ai_usage.publish_target 未明确，不能发布交接")
    elif target != "跨平台" and target not in platforms:
        errors.append("release_decision.platforms 未覆盖当前 ai_usage.publish_target")
    disclosed_territories = {
        str(row).upper() for row in disclosure.get("territories") or [] if str(row).strip()
    }
    if disclosed_territories and not disclosed_territories.issubset(
        {str(row).upper() for row in territories}
    ):
        errors.append("release_decision.territories 未覆盖 ai_usage 已披露法域")
    errors.extend(_current_binding_errors(
        root, payload.get("inputs_sha256") or {}, label="release_decision.inputs_sha256",
        required=("成片_MV.mp4", "合规/ai_usage.json", "合规/provenance.json"),
    ))
    expected_rows = release_contract.applicable_requirements(disclosure, platforms, territories)
    current_provenance = _payload(root, "合规/provenance.json") or {}
    recorded_rows = payload.get("requirements")
    if not isinstance(recorded_rows, list):
        errors.append("release_decision.requirements 必须是当前规则全集")
        recorded_rows = []
    recorded_by_id = {
        str(row.get("id")): row for row in recorded_rows
        if isinstance(row, dict) and row.get("id")
    }
    if len(recorded_by_id) != len(recorded_rows):
        errors.append("release_decision.requirements 含重复或无效 id")
    expected_ids = {str(row["id"]) for row in expected_rows}
    if set(recorded_by_id) != expected_ids:
        errors.append(
            "release_decision.requirements 未与当前规则重算全集一致："
            f"expected={sorted(expected_ids)}, actual={sorted(recorded_by_id)}"
        )
    for expected in expected_rows:
        row = recorded_by_id.get(str(expected["id"])) or {}
        for key in ("required", "source", "evidence_class"):
            if row.get(key) != expected.get(key):
                errors.append(f"release requirement {expected['id']} {key} 与当前规则不一致")
        if row.get("status") != "completed":
            errors.append(f"release requirement 未完成：{expected['id']}")
        evidence = row.get("evidence") or {}
        evidence_rel = str(evidence.get("path") or "")
        if not evidence_rel:
            errors.append(f"release requirement 证据缺失/过期：{expected['id']}")
        else:
            errors.extend(_current_binding_errors(
                root, {evidence_rel: evidence.get("sha256")},
                label=f"release requirement {expected['id']} evidence",
                required=(evidence_rel,),
            ))
            errors.extend(release_contract.validate_requirement_evidence(
                root, evidence, evidence_class=str(expected.get("evidence_class") or ""),
                machine_label_method=str(payload.get("machine_label_method") or ""),
                provenance=current_provenance,
            ))
    submission = payload.get("submission") or {}
    receipt = submission.get("receipt") or {}
    receipt_rel = str(receipt.get("path") or "")
    published_url = str(submission.get("published_url") or "")
    if submission.get("status") != "uploaded" or not published_url:
        errors.append("release_decision 缺真实 uploaded 状态或 published_url")
    errors.extend(release_contract.published_url_errors(published_url, platforms))
    receipt_binding_errors = []
    if not receipt_rel:
        errors.append("release_decision 上传回执缺失/过期")
    else:
        receipt_binding_errors = _current_binding_errors(
            root, {receipt_rel: receipt.get("sha256")},
            label="release_decision upload receipt", required=(receipt_rel,),
        )
        errors.extend(receipt_binding_errors)
    if receipt_rel and not receipt_binding_errors:
        receipt_path = os.path.join(root, receipt_rel)
        receipt_claim, receipt_errors = release_contract.validate_upload_receipt(
            root, receipt_path, platforms=platforms, operator=operator,
            published_url=published_url,
            machine_label_method=str(payload.get("machine_label_method") or ""),
            provenance=current_provenance,
        )
        errors.extend(receipt_errors)
        expected_claim = release_contract.upload_receipt_claim(receipt_claim)
        if submission.get("receipt_claim") != expected_claim:
            errors.append("release_decision.submission.receipt_claim 未绑定当前结构化上传回执")
    method = payload.get("machine_label_method")
    if method not in release_contract.MACHINE_LABEL_METHODS or method == "pending":
        errors.append("release_decision.machine_label_method 无效或仍 pending")
    if method == "c2pa":
        provenance = _payload(root, "合规/provenance.json") or {}
        c2pa = provenance.get("c2pa") or {}
        required_truths = ("embedded", "structurally_valid", "signature_valid", "trusted", "timestamped")
        if c2pa.get("certificate_profile") != "production" or any(c2pa.get(key) is not True for key in required_truths):
            errors.append("release_decision 声称 C2PA，但当前 provenance 不是 trusted+timestamped production credential")
    if payload.get("errors") not in ([], None):
        errors.append("release_decision 自身仍记录 errors，不得 ready_for_handoff")
    return list(dict.fromkeys(errors))


def _health_review(root):
    rel = "生产数据/review/review_receipt.json"
    payload = _payload(root, rel)
    required = (
        "成片_MV.mp4", "成片_MV_master.mov", "生产数据/delivery_qc/delivery_qc.json",
        "合规/provenance.json", "合规/ai_usage.json",
    )
    errors = []
    if not isinstance(payload, dict) or payload.get("kind") != "mv_review_receipt":
        return _result("review", [f"缺或损坏 {rel}"])
    if _strict_int(payload.get("schema_version")) != 1:
        errors.append("review receipt 必须是 schema v1")
    accepted, reviewer = _review_acceptance(payload)
    human = payload.get("human_signoff")
    if not isinstance(human, dict):
        human = {}
        errors.append("review receipt 缺 human_signoff 对象")
    notes = str(human.get("notes") or "").strip()
    confirmation = human.get("confirmation") or {}
    if not accepted or not _valid_reviewer(reviewer) or not _valid_notes(notes):
        errors.append("review receipt 缺具名、含 notes 的双层 accepted 人工签收")
    if (confirmation.get("kind") != "explicit_current_delivery_acceptance"
            or confirmation.get("accepted_current_delivery") is not True):
        errors.append("review receipt 缺当前交付显式确认")
    if not str(payload.get("reviewed_at") or "").strip() or human.get("reviewed_at") != payload.get("reviewed_at"):
        errors.append("review receipt reviewed_at 缺失或人审时间不一致")
    machine = payload.get("machine_review")
    if not isinstance(machine, dict):
        machine = {}
        errors.append("review receipt 缺 machine_review 对象")
    hard_blocks = _strict_int(machine.get("hard_blocks"))
    if hard_blocks != 0:
        errors.append(f"review receipt 仍有 hard_blocks={machine.get('hard_blocks')!r}")
    machine_findings = machine.get("findings")
    if not isinstance(machine_findings, list):
        errors.append("review receipt machine_review.findings 必须是完整 list")
        machine_findings = []
    elif machine.get("findings_sha256") != mv_utils.json_hash(machine_findings):
        errors.append("review receipt machine findings_sha256 与 findings 内容不一致")
    warning_count = sum(1 for row in machine_findings if isinstance(row, dict) and row.get("sev") == "🟡")
    info_count = sum(1 for row in machine_findings if isinstance(row, dict) and row.get("sev") == "🟢")
    if _strict_int(machine.get("warnings")) != warning_count or _strict_int(machine.get("infos")) != info_count:
        errors.append("review receipt machine findings 计数与 warnings/infos 不一致")
    errors.extend(_current_binding_errors(
        root, payload.get("inputs_sha256") or {}, label="review_receipt.inputs_sha256", required=required,
    ))
    provenance = _payload(root, "合规/provenance.json") or {}
    current_c2pa = provenance.get("c2pa") or {}
    recorded_c2pa = machine.get("c2pa")
    if not isinstance(recorded_c2pa, dict):
        errors.append("review receipt 未记录分层 C2PA 审查快照")
    else:
        expected_c2pa = {
            "requested": current_c2pa.get("requested") is True,
            "embedded": current_c2pa.get("embedded") is True,
            "structurally_valid": current_c2pa.get("structurally_valid") is True,
            "signature_valid": current_c2pa.get("signature_valid") is True,
            "trust_checked": current_c2pa.get("trust_checked") is True,
            "trusted": current_c2pa.get("trusted") is True,
            "test_certificate": str(current_c2pa.get("certificate_profile") or "").lower().startswith("test"),
            "certificate_profile": current_c2pa.get("certificate_profile") or None,
            "timestamp_validated": current_c2pa.get("timestamp_validated") is True,
            "timestamp_trusted": current_c2pa.get("timestamp_trusted") is True,
            "timestamped": current_c2pa.get("timestamped") is True,
            "timestamp_exception_allowed": current_c2pa.get("timestamp_exception_allowed") is True,
            "output": current_c2pa.get("output"),
            "output_sha256": current_c2pa.get("output_sha256"),
        }
        if recorded_c2pa != expected_c2pa:
            errors.append("review receipt C2PA 审查快照与当前 provenance 不一致")
    return _result("review", errors, evidence={"receipt": rel, "reviewer": reviewer})


def _health_handoff(root):
    rel = "合规/handoff_receipt.json"
    payload = _payload(root, rel)
    required = (
        "成片_MV.mp4", "合规/ai_usage.json", "合规/provenance.json",
        "生产数据/review/review_receipt.json", "合规/release_decision.json",
    )
    errors = []
    if not isinstance(payload, dict) or payload.get("kind") != "mv_handoff_receipt":
        return _result("handoff", [f"缺或损坏 {rel}"])
    if (payload.get("accepted") is not True or not _valid_reviewer(payload.get("reviewer"))
            or not _valid_notes(payload.get("notes"))):
        errors.append("handoff receipt 缺具名、含 notes 的 accepted 发布确认")
    errors.extend(_current_binding_errors(
        root, payload.get("inputs_sha256") or {}, label="handoff_receipt.inputs_sha256", required=required,
    ))
    errors.extend(_release_decision_errors(root))
    runtime = contract.runtime_state_from_settings(mv_utils.parse_settings(root))
    if runtime["publish_target"] in ("", "未定"):
        errors.append("handoff 前必须在 _设置.md 明确发行目标平台")
    if payload.get("publish_target") != runtime["publish_target"]:
        errors.append("handoff publish_target 与当前 _设置.md 不一致")
    return _result("handoff", errors, evidence={"receipt": rel, "reviewer": payload.get("reviewer")})


_HEALTH_CHECKS = {
    "beat": _health_beat,
    "lyric_sync": _health_lyric_sync,
    "plan": _health_plan,
    "semantic_plan": _health_semantic_plan,
    "pacing_check": _health_pacing_check,
    "image": _health_image,
    "picture_lock": _health_picture_lock,
    "video_jobs": _health_video_jobs,
    "video": _health_video,
    "compose": _health_compose,
    "disclosure": _health_disclosure,
    "provenance": _health_provenance,
    "review": _health_review,
    "handoff": _health_handoff,
}


def stage_health(root, stage):
    checker = _HEALTH_CHECKS.get(stage)
    if checker is None:
        return _result(stage, [f"stage={stage} 没有登记 output receipt health validator"])
    root = os.path.abspath(root)
    settings_errors = _settings_first_errors(root, stage)
    if settings_errors:
        return _result(
            stage, settings_errors,
            evidence={"settings_sha256": mv_utils.content_hash(os.path.join(root, "_设置.md"))},
        )
    try:
        row = checker(root)
    except Exception as exc:
        return _result(
            stage, [f"output receipt validator fail-closed：{type(exc).__name__}: {exc}"],
            evidence={"settings_sha256": mv_utils.content_hash(os.path.join(root, "_设置.md"))},
        )
    evidence = dict(row.get("evidence") or {})
    evidence["settings_sha256"] = mv_utils.content_hash(os.path.join(root, "_设置.md"))
    row["evidence"] = evidence
    return row


def receipt_health(root, stages=None):
    if stages is None:
        runtime = contract.runtime_state_from_settings(mv_utils.parse_settings(root))
        workflow = contract.workflow_stage_table(
            runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"],
        )
        stages = tuple(
            row["key"] for row in workflow if row["key"] in CONTROLLED_COMPLETION_STAGES
        )
    else:
        stages = tuple(stages)
    return [stage_health(root, stage) for stage in stages]


def _valid_reviewer(value):
    raw = str(value or "").strip()
    lowered = raw.lower()
    if len(raw) < 2 or lowered in {"<name>", "待填", "待定", "unknown", "ai", "匿名"}:
        return False
    return not any(token in lowered for token in (
        "codex", "chatgpt", "claude", "agent", "bot", "机器人", "自动化",
    ))


def _valid_notes(value):
    raw = str(value or "").strip()
    return bool(raw and raw not in {"<notes>", "待填", "待定", "unknown", "n/a"})


def _write_handoff_receipt(root, reviewer, notes=""):
    if not _valid_reviewer(reviewer):
        raise ValueError("handoff completion 需要真实具名 --reviewer，不能使用占位值")
    if not _valid_notes(notes):
        raise ValueError("handoff completion 需要非空 --notes 说明发布确认")
    prereq_errors = []
    for stage in ("compose", "disclosure", "provenance", "review"):
        health = stage_health(root, stage)
        prereq_errors.extend(f"{stage}: {msg}" for msg in health["errors"])
    prereq_errors.extend(f"release: {message}" for message in _release_decision_errors(root))
    if prereq_errors:
        raise ValueError("handoff 前置未通过：\n- " + "\n- ".join(prereq_errors))
    inputs = (
        "成片_MV.mp4", "合规/ai_usage.json", "合规/provenance.json",
        "生产数据/review/review_receipt.json", "合规/release_decision.json",
    )
    runtime = contract.runtime_state_from_settings(mv_utils.parse_settings(root))
    if runtime["publish_target"] in ("", "未定"):
        raise ValueError("handoff 前必须在 _设置.md 明确发行目标平台")
    payload = {
        "schema_version": 1,
        "kind": "mv_handoff_receipt",
        "accepted": True,
        "reviewer": str(reviewer).strip(),
        "reviewed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "publish_target": runtime["publish_target"],
        "notes": str(notes or "").strip(),
        "confirmation": {
            "kind": "explicit_current_delivery_acceptance",
            "accepted_current_delivery": True,
        },
        "inputs_sha256": {
            rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in inputs
        },
    }
    out = os.path.join(root, "合规", "handoff_receipt.json")
    mv_utils.write_json(out, payload)
    return out


_DONE_FRACTION_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


def _progress_status_done(status):
    raw = str(status or "").strip()
    if "[x]" in raw.lower() or "✅" in raw:
        return True
    match = _DONE_FRACTION_RE.search(raw)
    return bool(match and int(match.group(2)) > 0 and int(match.group(1)) >= int(match.group(2)))


def _current_workflow_progress_rows(root):
    """Read only the canonical 制MV table without importing progress (avoids a cycle)."""
    text = mv_utils.read_text(os.path.join(root, "_进度.md"), "")
    by_label = {row["label"]: row["key"] for row in contract.stage_table()}
    rows = []
    in_section = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if in_section and not ("制MV" in heading and "阶段" in heading):
                break
            in_section = "制MV" in heading and "阶段" in heading
            continue
        if not in_section or not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"阶段", "---"} or set(cells[0]) <= {"-", ":"}:
            continue
        label = mv_utils.clean_stage_label(cells[0])
        rows.append({"key": by_label.get(label), "label": label, "status": cells[2]})
    return rows


def _predecessor_completion_errors(root, stage):
    """Require every settings-derived predecessor row and output receipt to be current."""
    settings_errors = _settings_first_errors(root, stage)
    if settings_errors:
        return settings_errors
    settings = mv_utils.parse_settings(root)
    unresolved = {"", "待填", "待定", "（未定）", "unknown"}
    missing_workflow = [
        key for key in ("歌曲输入时序", "字幕语言", "演唱口型")
        if str(settings.get(key) or "").strip() in unresolved
    ]
    if missing_workflow:
        return [f"_设置.md 缺工作流派生选择：{key}" for key in missing_workflow]
    runtime = contract.runtime_state_from_settings(settings)
    workflow = contract.workflow_stage_table(
        runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"],
    )
    expected_keys = [row["key"] for row in workflow]
    if stage not in expected_keys:
        return [f"stage={stage} 不属于当前 _设置.md 派生工作流"]
    rows = _current_workflow_progress_rows(root)
    actual_keys = [row.get("key") for row in rows]
    if actual_keys != expected_keys:
        return ["_进度.md 阶段表缺失、重复或顺序不符合当前 _设置.md 派生工作流；先运行 state_contract sync"]
    by_key = {row["key"]: row for row in rows}
    errors = []
    for predecessor in expected_keys[:expected_keys.index(stage)]:
        row = by_key[predecessor]
        if not _progress_status_done(row.get("status")):
            errors.append(f"前驱 stage={predecessor} 尚未完成")
        if predecessor in OUTPUT_HEALTH_STAGES:
            health = stage_health(root, predecessor)
            if not health["ok"]:
                first = (health.get("errors") or ["output receipt health 未通过"])[0]
                errors.append(f"前驱 stage={predecessor} output health 已失效：{first}")
    return errors


def mark_stage_complete(root, stage, *, reviewer="", notes=""):
    """Validate ordered predecessors and stage outputs before marking done."""
    root = os.path.abspath(root)
    if stage not in CONTROLLED_COMPLETION_STAGES:
        raise ValueError(f"stage={stage} 未登记 completion controller")
    predecessor_errors = _predecessor_completion_errors(root, stage)
    if predecessor_errors:
        raise ValueError(
            f"stage={stage} 前驱完成态未通过：\n- " + "\n- ".join(predecessor_errors)
        )
    if stage == "handoff":
        _write_handoff_receipt(root, reviewer, notes)
    health = stage_health(root, stage)
    if not health["ok"]:
        raise ValueError(
            f"stage={stage} output receipt health 未通过：\n- " + "\n- ".join(health["errors"])
        )
    changed = mv_utils.update_progress_stage(root, stage, "[x]")
    if not changed:
        raise ValueError(f"_进度.md 未找到 stage={stage}；先同步完整阶段表")
    mv_utils.update_meta_flags(root)
    return health


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p_health = sub.add_parser("health")
    p_health.add_argument("project_root")
    p_health.add_argument("stage", nargs="?", choices=OUTPUT_HEALTH_STAGES)
    p_health.add_argument("--json", action="store_true")
    p_complete = sub.add_parser("complete")
    p_complete.add_argument("project_root")
    p_complete.add_argument("stage", choices=OUTPUT_HEALTH_STAGES)
    p_complete.add_argument("--reviewer", default="")
    p_complete.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    if args.command == "health":
        rows = [stage_health(root, args.stage)] if args.stage else receipt_health(root)
        if args.json:
            print(json.dumps(rows[0] if args.stage else rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                print(f"[{'ok' if row['ok'] else 'stale'}] {row['stage']}")
                for message in row["errors"]:
                    print(f"  - {message}")
        return 0 if all(row["ok"] for row in rows) else 1
    try:
        health = mark_stage_complete(
            root, args.stage, reviewer=args.reviewer, notes=args.notes,
        )
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    print(f"[ok] stage={args.stage} output receipt health 通过并回写 _进度.md")
    return 0 if health["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
