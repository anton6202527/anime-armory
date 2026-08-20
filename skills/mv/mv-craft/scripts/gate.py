#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic gates for MV stages."""
import argparse
import importlib.util
import math
import os
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import mv_utils
import contract


REPO = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
IMAGE_RECEIPTS_PATH = os.path.join(
    REPO, "skills", "mv", "mv-image", "scripts", "image_receipts.py",
)
VIDEO_INHERIT_PATH = os.path.join(
    REPO, "skills", "mv", "mv-video", "scripts", "inherit_contract.py",
)
_IMAGE_RECEIPTS_MODULE = None
_VIDEO_INHERIT_MODULE = None


def _strict_int(value):
    """Return an integer only for an actual integral JSON number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = int(value)
    return number if float(value) == number else None


def _finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _schema_at_least(payload, version):
    return isinstance(payload, dict) and (_strict_int(payload.get("schema_version")) or -1) >= version


def _load_external_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _image_receipts_module():
    global _IMAGE_RECEIPTS_MODULE
    if _IMAGE_RECEIPTS_MODULE is None:
        _IMAGE_RECEIPTS_MODULE = _load_external_module(
            "mv_gate_image_receipts", IMAGE_RECEIPTS_PATH,
        )
    return _IMAGE_RECEIPTS_MODULE


def _video_inherit_module():
    global _VIDEO_INHERIT_MODULE
    if _VIDEO_INHERIT_MODULE is None:
        _VIDEO_INHERIT_MODULE = _load_external_module(
            "mv_gate_video_inherit", VIDEO_INHERIT_PATH,
        )
    return _VIDEO_INHERIT_MODULE


def _runtime_state(root):
    """Settings are the preference truth; `_meta.json` is compatibility only."""
    return contract.runtime_state_from_settings(mv_utils.parse_settings(root))


def _settings_mode(root, meta):
    return _runtime_state(root)["song_timing"]


def _has_rough_blueprint(root):
    text = mv_utils.read_text(os.path.join(root, "视觉蓝图.md"))
    return "rough（待成品歌/beatgrid 复核）" in text or "状态：rough" in text


def _lyrics_required(root, meta, stage=None):
    """Lyrics are conditional: instrumental/no-subtitle/no-lipsync MVs are valid."""
    if stage == "lyric_sync":
        return True
    runtime = _runtime_state(root)
    subtitle_mode = runtime["subtitle_language"]
    lip_mode = runtime["lip_sync_mode"]
    return subtitle_mode != "无字幕" or lip_mode != "关闭"


# 付费 / 不可逆阶段：进入前必须确认输入歌曲版权（音乐媒介的核心合规闸）。
_COSTLY_STAGES = {"image", "video_jobs", "video", "compose"}
_UNRESOLVED_RIGHTS = {"", "unknown", "未知", "未定", "未确认", "未声明", "待确认"}
_REQUIRED_SETTINGS = {
    "plan": ("MV用途", "歌曲输入时序", "MV规划粒度", "卡点策略"),
    "image": ("MV用途", "生图模型", "生图渠道"),
    "video_jobs": ("MV用途", "生视频模型", "生视频渠道", "出视频规格", "演唱口型"),
    "video": ("MV用途", "生视频模型", "生视频渠道", "出视频规格", "演唱口型"),
    "compose": ("MV用途", "合成画幅", "字幕语言", "演唱口型"),
}


def _settings_truth_errors(root, stage):
    required = _REQUIRED_SETTINGS.get(stage, ())
    if not required:
        return []
    path = os.path.join(root, "_设置.md")
    if not os.path.isfile(path):
        return ["缺 _设置.md；承重 gate 必须 settings-first，不能从 _meta.json 或默认值猜选择"]
    settings = mv_utils.parse_settings(root)
    unresolved = {"", "待填", "待定", "（未定）", "unknown"}
    missing = [key for key in required if str(settings.get(key) or "").strip() in unresolved]
    return [f"_设置.md 缺明确选择：{key}" for key in missing]


def _song_rights_status(root, meta):
    settings = mv_utils.parse_settings(root)
    return (settings.get("输入歌权利")
            or settings.get("权利来源")
            or meta.get("song_rights_status")
            or "").strip()


def _rights_errors(root, stage, meta):
    """音乐媒介合规：付费视觉生产前必须确认歌曲版权 + 翻唱/克隆授权。
    按 CLAUDE.md，合规/不可逆点每次都查（不因记过一次就永久放行 unknown）。"""
    if stage not in _COSTLY_STAGES:
        return []
    manifest = mv_utils.load_json(os.path.join(root, "合规", "rights_manifest.json"), None)
    if not isinstance(manifest, dict):
        return ["缺 合规/rights_manifest.json；付费/不可逆生产不因 demo 降级，需记录歌曲、"
                "视觉参考、真人肖像、品牌、场地和编舞权利状态"]
    allowed = {"owned", "public_domain", "licensed", "authorized", "cleared", "not_applicable"}
    assertions = manifest.get("assertions") or {}
    missing = [key for key in ("song", "visual_reference", "likeness", "brand", "location", "choreography")
               if assertions.get(key) not in allowed]
    if missing:
        return [f"rights_manifest 未解决：{', '.join(missing)}"]
    rights = _song_rights_status(root, meta)
    low = rights.lower()
    if low in _UNRESOLVED_RIGHTS:
        return ["输入歌曲版权状态未确认（song_rights_status）；进入出图/出视频/合成等付费不可逆阶段前，"
                "先确认歌曲为自有/公版/已授权（init 传 --song-rights-status 或在 _设置.md 记录）。"
                "翻唱与真人嗓音克隆需另有授权。"]
    if any(k in low for k in ("cover", "翻唱")) and not (meta.get("cover_authorized") or meta.get("翻唱授权")):
        return ["输入歌曲为翻唱/cover，但缺翻唱授权留痕（_meta.cover_authorized）；"
                "付费视觉生产前补授权，或改用自有/公版歌。"]
    if any(k in low for k in ("clone", "克隆")) and not (meta.get("voice_clone_authorized") or meta.get("声音克隆授权")):
        return ["输入歌曲使用克隆嗓音，但缺声音克隆授权留痕（_meta.voice_clone_authorized）；付费生产前补授权。"]
    return []


def _staleness_errors(root, stage, meta):
    """Verify that a plan still describes its exact upstream creative truth."""
    if stage not in _COSTLY_STAGES:
        return []
    plan = _load_plan(root)
    if not plan:
        return []
    errs = []
    input_paths = {
        "song": mv_utils.find_song(root),
        "beatgrid": os.path.join(root, "节拍", "beatgrid.json"),
        "lyrics": os.path.join(root, "词", "lyrics.md"),
        "blueprint": os.path.join(root, "视觉蓝图.md"),
        "alignment": os.path.join(root, "字幕", "alignment_report.json"),
    }
    expected_inputs = {
        key: mv_utils.content_hash(path) for key, path in input_paths.items()
    }
    expected_inputs["settings_plan"] = contract.plan_settings_digest(mv_utils.parse_settings(root))
    recorded_inputs = plan.get("inputs_sha256")
    if isinstance(recorded_inputs, dict):
        for key, current in expected_inputs.items():
            recorded = recorded_inputs.get(key)
            if key in {"lyrics", "alignment"} and not current and recorded == "":
                continue
            if recorded is None:
                errs.append(f"clip_plan.inputs_sha256 缺 {key}；重跑 mv-plan 建立完整输入收据")
            elif current != recorded:
                errs.append(f"{key} 自 mv-plan 后已变化；重跑 mv-plan，不能让旧分镜消费新输入")
        extra = sorted(set(recorded_inputs) - set(expected_inputs))
        if extra:
            errs.append(f"clip_plan.inputs_sha256 含旧/未知输入键 {extra}；重跑 mv-plan 迁移当前规划合同")
    else:
        errs.append("clip_plan 缺 inputs_sha256 全输入收据；preview 也不得让旧分镜消费新输入")

    # Legacy fields remain readable so demo/older projects receive precise
    # change detection while migrating to inputs_sha256.
    rec_bg = plan.get("beatgrid_hash")
    if rec_bg:
        cur_bg = mv_utils.content_hash(os.path.join(root, "节拍", "beatgrid.json"))
        if cur_bg and cur_bg != rec_bg:
            errs.append("节拍/beatgrid.json 自 mv-plan 之后已变（换歌/重测卡点）；"
                        "先重跑 mv-plan，否则 clip 时长/卡点与新节拍不符。")
    rec_song = plan.get("song_hash")
    if rec_song:
        cur_song = mv_utils.content_hash(mv_utils.find_song(root))
        if cur_song and cur_song != rec_song:
            errs.append("歌/song.* 自 mv-plan 之后已变（后配歌曲定稿/换歌）；先重跑 mv-beat + mv-plan。")
    return errs


def _beatgrid_contract(root, stage, meta, song):
    """Return deterministic errors/warnings for the music-timing truth source."""
    if stage not in {"plan", "image", "video_jobs", "video", "compose"}:
        return [], []
    path = os.path.join(root, "节拍", "beatgrid.json")
    payload = mv_utils.load_json(path, {}) or {}
    if not payload:
        return [], []  # the common existence gate owns the missing-file message
    errors, warnings = [], []
    recorded_song = str(payload.get("source_audio_sha256") or "")
    current_song = mv_utils.content_hash(song)
    if recorded_song and current_song != recorded_song:
        errors.append("beatgrid 不是由当前 歌/song.* 生成（source_audio_sha256 不一致）；先重跑 mv-beat")
    elif not recorded_song:
        message = "beatgrid 缺 source_audio_sha256，不能证明节拍来自当前歌曲；重跑 mv-beat"
        errors.append(message)

    for key in ("beats", "downbeats"):
        values = payload.get(key) or []
        if not values:
            errors.append(f"beatgrid.{key} 为空")
            continue
        try:
            floats = [float(value) for value in values]
        except (TypeError, ValueError):
            errors.append(f"beatgrid.{key} 含非数值时间戳")
            continue
        if any(right <= left for left, right in zip(floats, floats[1:])):
            errors.append(f"beatgrid.{key} 必须严格递增")

    sections = payload.get("sections") or []
    review = payload.get("timing_review") or {}
    if not payload.get("timing_verified"):
        errors.append("beatgrid timing_verified=false；需具名确认拍号、小节相位和完整段落边界")
    if not payload.get("downbeats_verified"):
        errors.append("beatgrid.downbeats_verified=false；不能把自动 onset 相位当人工确认")
    if not payload.get("sections_verified") or not payload.get("sections_complete"):
        errors.append("beatgrid 段落边界未完整覆盖全曲并签收；补 section timings 后重跑 mv-beat")
    if (not review.get("accepted") or not str(review.get("reviewer") or "").strip()
            or not str(review.get("notes") or "").strip()):
        errors.append("beatgrid 缺具名 timing_review；用 mv-beat --confirm-timing --reviewer <name> 重跑")
    if not sections:
        errors.append("beatgrid.sections 为空；不得按歌词字数伪造段落时长")

    measured = mv_utils.audio_duration(song) if song else None
    try:
        grid_duration = float(payload.get("duration"))
    except (TypeError, ValueError):
        grid_duration = None
    if measured and grid_duration is not None and abs(measured - grid_duration) > 0.25:
        errors.append(f"beatgrid.duration={grid_duration:.3f}s 与当前歌曲实测 {measured:.3f}s 不一致")
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))


def _timeline_contract_errors(root, stage, meta):
    if stage not in {"image", "video_jobs", "video", "compose"}:
        return []
    plan = _load_plan(root)
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    if not plan or not timeline:
        return []
    errors = []
    p_rows = plan.get("clips") or []
    t_rows = timeline.get("clips") or []
    if [r.get("clip_id") for r in p_rows] != [r.get("clip_id") for r in t_rows]:
        errors.append("timeline_manifest 与 clip_plan 的 clip 顺序/集合不一致；重跑 mv-plan")
        return errors
    for left, right in zip(p_rows, t_rows):
        for key in ("start", "end", "duration"):
            try:
                if abs(float(left.get(key)) - float(right.get(key))) > 0.001:
                    errors.append(f"{right.get('clip_id')} timeline.{key} 与 clip_plan 不一致")
                    break
            except (TypeError, ValueError):
                errors.append(f"{right.get('clip_id')} timeline/clip_plan 缺有效 {key}")
                break
    source_hash = timeline.get("source_clip_plan_sha256")
    if not source_hash:
        errors.append("timeline_manifest 缺 source_clip_plan_sha256；重跑 mv-plan")
    elif source_hash and source_hash != mv_utils.content_hash(os.path.join(root, "分镜", "clip_plan.json")):
        errors.append("timeline_manifest 未绑定当前 clip_plan；同步语义分镜后需刷新 timeline/OTIO")
    return list(dict.fromkeys(errors))


def _otio_document_errors(value, path="$"):
    errors = []
    if isinstance(value, dict):
        if str(value.get("OTIO_SCHEMA") or "").startswith("RationalTime."):
            frame = value.get("value")
            rate = value.get("rate")
            if isinstance(frame, bool) or not isinstance(frame, int):
                errors.append(f"OTIO {path}.value 不是 integer frame")
            if (isinstance(rate, bool) or not isinstance(rate, (int, float))
                    or not math.isfinite(float(rate)) or float(rate) <= 0):
                errors.append(f"OTIO {path}.rate 非法")
        for key, child in value.items():
            errors.extend(_otio_document_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_otio_document_errors(child, f"{path}[{index}]"))
    return errors


def _otio_contract_errors(root, stage, meta):
    if stage not in {"video_jobs", "video", "compose"}:
        return []
    otio_rel = "分镜/timeline.otio"
    receipt_rel = "生产数据/otio/otio_receipt.json"
    otio_path = os.path.join(root, otio_rel)
    receipt = mv_utils.load_json(os.path.join(root, receipt_rel), None)
    if not os.path.isfile(otio_path) or not isinstance(receipt, dict):
        return ["缺可编辑 OTIO + hash receipt；preview 需另走显式 fallback，不能靠 is_demo 绕过"]
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    beat_path = os.path.join(root, "节拍", "beatgrid.json")
    timeline = mv_utils.load_json(timeline_path, {}) or {}
    errors = []
    otio = mv_utils.load_json(otio_path, None)
    if not isinstance(otio, dict) or otio.get("OTIO_SCHEMA") != "Timeline.1":
        errors.append("timeline.otio 不是有效 OpenTimelineIO Timeline.1 文档")
    else:
        errors.extend(_otio_document_errors(otio))
        track_rows = ((otio.get("tracks") or {}).get("children") or [])
        kinds = [str(row.get("kind") or "") for row in track_rows if isinstance(row, dict)]
        if kinds.count("Video") != 1 or kinds.count("Audio") != 1 or len(kinds) != 2:
            errors.append("timeline.otio 必须精确包含 V1 Video + A1 Audio")
    if receipt.get("kind") != "mv_otio_export_receipt" or not _schema_at_least(receipt, 3):
        errors.append("OTIO receipt 必须是 schema>=3 mv_otio_export_receipt")
    if receipt.get("otio_sha256") != mv_utils.content_hash(otio_path):
        errors.append("timeline.otio 与 otio_receipt 不一致；重跑 export_otio.py")
    if receipt.get("timeline_edit_sha256") != mv_utils.timeline_edit_hash(timeline):
        errors.append("timeline.otio 未反映当前剪辑决定；重跑 export_otio.py")
    recorded = receipt.get("inputs_sha256") or {}
    if recorded.get("分镜/timeline_manifest.json") != mv_utils.content_hash(timeline_path):
        errors.append("OTIO receipt 已过期：timeline_manifest 在导出后变化")
    if recorded.get("节拍/beatgrid.json") != mv_utils.content_hash(beat_path):
        errors.append("OTIO receipt 已过期：beatgrid 在导出后变化")
    timebase = receipt.get("timebase") or {}
    if timebase.get("unit") != "frame" or timebase.get("integral_rational_time") is not True:
        errors.append("OTIO receipt 未声明 integer-frame timebase")
    rate = timeline.get("rate") or receipt.get("rate")
    try:
        rate = float(rate)
        if rate <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("timeline/OTIO 缺有效帧率")
        rate = None
    previous_end = 0
    for index, row in enumerate(timeline.get("clips") or []):
        clip_id = row.get("clip_id") or f"clip#{index + 1}"
        frame_values = tuple(row.get(key) for key in ("start_frame", "end_frame", "duration_frames"))
        if any(isinstance(value, bool) or not isinstance(value, int) for value in frame_values):
            errors.append(f"{clip_id} 缺 integer-frame start/end/duration contract")
            continue
        start_frame, end_frame, duration_frames = frame_values
        if start_frame != previous_end or end_frame - start_frame != duration_frames or duration_frames <= 0:
            errors.append(f"{clip_id} integer-frame 边界不连续或时长不守恒")
        previous_end = end_frame
        if rate is not None:
            for key, frame_key in (("start", "start_frame"), ("end", "end_frame"), ("duration", "duration_frames")):
                try:
                    if abs(float(row.get(key)) * rate - float(row.get(frame_key))) > 0.001:
                        errors.append(f"{clip_id}.{key} 未对齐 integer frame")
                        break
                except (TypeError, ValueError):
                    errors.append(f"{clip_id}.{key} 不是有效时间")
                    break
    roundtrip = receipt.get("official_roundtrip") or {}
    if roundtrip.get("status") != "ok" or not str(roundtrip.get("library_version") or "").strip():
        errors.append("OTIO 未经官方 OpenTimelineIO adapter 成功 read/write roundtrip；请在受支持环境重导")
    media = receipt.get("media_sha256") or {}
    expected_media = []
    for row in timeline.get("clips") or []:
        rel = str(row.get("video_path") or "") if isinstance(row, dict) else ""
        if rel and os.path.isfile(os.path.join(root, rel)) and rel not in expected_media:
            expected_media.append(rel)
    song_rel = str(timeline.get("song_path") or "")
    if song_rel and os.path.isfile(os.path.join(root, song_rel)) and song_rel not in expected_media:
        expected_media.append(song_rel)
    if set(media) != set(expected_media):
        errors.append("OTIO media receipt 未精确覆盖当前存在的 V1/A1 媒体")
    for rel, digest in media.items():
        if not digest or mv_utils.content_hash(os.path.join(root, rel)) != digest:
            errors.append(f"OTIO media receipt 已过期：{rel}")
    if stage == "compose" and receipt.get("missing_media"):
        errors.append(f"OTIO 仍有 {len(receipt['missing_media'])} 个 missing media；全部挑版后重导 OTIO")
    if receipt.get("tracks") != {"video": 1, "audio": 1}:
        errors.append("OTIO receipt 未证明精确 V1/A1 track 结构")
    return errors


def _pacing_receipt_errors(root, stage, meta):
    if stage not in {"image", "video_jobs", "video"}:
        return []
    rel = "评分/pacing_prescore.json"
    report = mv_utils.load_json(os.path.join(root, rel), None)
    if not isinstance(report, dict):
        return ["正式付费生产前缺 pacing_prescore；先跑 mv-score 的确定性节奏检查（可不设主观阈值）"]
    required = ("分镜/clip_plan.json", "节拍/beatgrid.json")
    recorded = report.get("inputs_sha256") or {}
    errors = []
    for input_rel in required:
        if recorded.get(input_rel) != mv_utils.content_hash(os.path.join(root, input_rel)):
            errors.append(f"pacing_prescore 已过期：{input_rel} 变化；重跑 mv-score")
    song = mv_utils.find_song(root)
    if song:
        song_rel = mv_utils.relpath(root, song)
        if recorded.get(song_rel) != mv_utils.content_hash(song):
            errors.append("pacing_prescore 已过期：当前歌曲变化；重跑 mv-score")
    if report.get("threshold") is not None and report.get("blocked"):
        errors.append("pacing_prescore 按项目显式阈值判定 blocked；先按 return_to_stages 回流")
    return errors


def _valid_named_reviewer(value):
    raw = str(value or "").strip()
    return bool(raw and raw.lower() not in {
        "<name>", "待填", "待定", "unknown", "anonymous", "reviewer", "n/a", "na", "none", "匿名",
    })


def _alignment_acceptance_binding(root, report):
    preaccept = {
        key: value for key, value in report.items()
        if key not in {"acceptance", "manual_review", "acoustic_evidence"}
    }

    def asset(rel):
        return {"path": rel, "sha256": mv_utils.content_hash(os.path.join(root, rel))}

    return {
        "master": asset(str(report.get("master_song") or "")),
        "alignment_audio": asset(str(report.get("audio") or "")),
        "lyrics": asset("词/lyrics.md"),
        "ass": asset("字幕/karaoke.ass"),
        "lrc": asset("字幕/lyrics.lrc"),
        "report_preaccept_content_sha256": mv_utils.json_hash(preaccept),
    }


def _alignment_acoustic_valid(report, expected_binding, lyric_lines):
    evidence = report.get("acoustic_evidence")
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
        if (not isinstance(row, dict) or isinstance(row.get("line_index"), bool)
                or not isinstance(row.get("line_index"), int)):
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
        and evidence.get("bound_inputs_sha256") == report.get("inputs_sha256")
        and evidence.get("bound_outputs_sha256") == report.get("outputs_sha256")
        and covered == set(range(lyric_lines))
    )


def _alignment_stem_timing_errors(root, report):
    """Recheck schema-v5 stem→master timing evidence without trusting its label."""
    timing = report.get("stem_master_timing") or {}
    errors = []
    if not isinstance(timing, dict) or timing.get("status") != "pass":
        errors.append("stem_master_timing 未通过")
        return errors

    master_rel = str(report.get("master_song") or "")
    audio_rel = str(report.get("audio") or "")

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
        if not _valid_named_reviewer(timing.get("reviewer")) or not str(timing.get("notes") or "").strip():
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


def _alignment_contract_errors(root, stage, meta):
    if stage not in {"video_jobs", "video", "compose"}:
        return []
    runtime = _runtime_state(root)
    plan = _load_plan(root)
    vocal_performance = any(
        str(clip.get("action_family") or "") == "performance_vocal" or clip.get("vocal_lyrics")
        for clip in plan.get("clips", []) if isinstance(clip, dict)
    )
    lip_mode = runtime["lip_sync_mode"]
    subtitle_mode = runtime["subtitle_language"]
    required = (stage in {"video_jobs", "video"} and vocal_performance and lip_mode != "关闭") or (
        stage == "compose" and subtitle_mode != "无字幕"
    )
    if not required:
        return []
    report = mv_utils.load_json(os.path.join(root, "字幕", "alignment_report.json"), None)
    if not isinstance(report, dict):
        purpose = "演唱口型镜" if stage in {"video_jobs", "video"} else "正式字幕"
        return [f"{purpose} 缺歌词强制对齐收据；先跑 mv-lyric-sync"]
    errors = []
    if report.get("kind") != "mv_lyric_alignment_report" or _strict_int(report.get("schema_version")) != 5:
        errors.append("alignment_report 必须是当前 schema v5 mv_lyric_alignment_report")
    if report.get("alignment_unit") != "character":
        errors.append("alignment_report 不是字符级强制对齐")
    if "alignment_confidence" in report:
        errors.append("schema v5 禁止 alignment_confidence；字符覆盖率不是声学置信度")
    errors.extend(_alignment_stem_timing_errors(root, report))
    recorded = report.get("inputs_sha256") or {}
    if not isinstance(recorded, dict):
        recorded = {}
        errors.append("alignment_report.inputs_sha256 必须是 object")
    lyrics_rel = "词/lyrics.md"
    if recorded.get(lyrics_rel) != mv_utils.content_hash(os.path.join(root, lyrics_rel)):
        errors.append("alignment_report 已过期：lyrics.md 变化；重跑 mv-lyric-sync")
    song = mv_utils.find_song(root)
    if song:
        song_rel = mv_utils.relpath(root, song)
        if recorded.get(song_rel) != mv_utils.content_hash(song):
            errors.append("alignment_report 已过期：主歌轨变化；重跑 mv-lyric-sync")
        if report.get("master_song") != song_rel:
            errors.append("alignment_report.master_song 未绑定当前主歌轨")
    audio_rel = str(report.get("audio") or "")
    if not audio_rel or recorded.get(audio_rel) != mv_utils.content_hash(os.path.join(root, audio_rel)):
        errors.append("alignment_report.audio 输入收据缺失或已过期")
    outputs = report.get("outputs_sha256") or {}
    if not isinstance(outputs, dict):
        outputs = {}
        errors.append("alignment_report.outputs_sha256 必须是 object")
    for rel in ("字幕/karaoke.ass", "字幕/lyrics.lrc"):
        if outputs.get(rel) != mv_utils.content_hash(os.path.join(root, rel)):
            errors.append(f"alignment_report 输出收据已过期：{rel}")
    try:
        text_coverage = float(report.get("character_coverage_ratio") or 0)
    except (TypeError, ValueError):
        text_coverage = 0.0
    line_coverage = []
    for row in report.get("lines") or []:
        if not isinstance(row, dict):
            continue
        try:
            line_coverage.append(float(row.get("line_character_coverage") or 0))
        except (TypeError, ValueError):
            line_coverage.append(0.0)
    aligned_lines = _strict_int(report.get("aligned_lines"))
    lyric_lines = _strict_int(report.get("lyric_lines"))
    text_timing_pass = bool(
        aligned_lines is not None and lyric_lines is not None and aligned_lines == lyric_lines
        and text_coverage >= 0.9
        and (not line_coverage or min(line_coverage) >= 0.85)
        and not report.get("timing_issues")
    )
    if report.get("coverage_metric") != "text_character_mapping_ratio_not_acoustic_confidence":
        errors.append("alignment_report 必须明示 character_coverage_ratio 只是文本字符映射覆盖，不是声学置信度")
    expected_binding = _alignment_acceptance_binding(root, report)
    acoustic_pass = _alignment_acoustic_valid(report, expected_binding, lyric_lines or 0)
    manual = report.get("manual_review") or {}
    if not isinstance(manual, dict):
        manual = {}
        errors.append("alignment_report.manual_review 必须是 object")
    manual_pass = bool(
        manual.get("accepted")
        and manual.get("kind") == "named_full_listening_review"
        and manual.get("verdict") == "pass"
        and _valid_named_reviewer(manual.get("reviewer"))
        and str(manual.get("notes") or "").strip()
    )
    if manual_pass and manual.get("bound_inputs_sha256") != recorded:
        manual_pass = False
    if manual_pass and manual.get("bound_outputs_sha256") != outputs:
        manual_pass = False
    if manual_pass and (
            manual.get("binding") != expected_binding
            or manual.get("bound_report_preaccept_sha256") != expected_binding["report_preaccept_content_sha256"]):
        manual_pass = False
    acceptance = report.get("acceptance") or {}
    if not isinstance(acceptance, dict):
        acceptance = {}
        errors.append("alignment_report.acceptance 必须是 object")
    acceptance_current = bool(
        acceptance.get("status") == "accepted"
        and acceptance.get("accepted") is True
        and acceptance.get("binding") == expected_binding
    )
    # Text mapping coverage proves that characters received timestamps; it is
    # not evidence that those timestamps acoustically match the sung phonemes.
    route = acceptance.get("route")
    if not acceptance_current:
        errors.append("alignment_report 尚未以当前 master/stem/lyrics/ASS/LRC/report binding 正式接受")
    elif route == "named_listening_review" and not manual_pass:
        errors.append("缺足够声学对齐证据；character_coverage_ratio 不得当 acoustic confidence，"
                      "需具名逐行听审并绑定当前 inputs/outputs")
    elif route == "named_listening_review" and acceptance.get("evidence_content_sha256") != mv_utils.json_hash(manual):
        errors.append("具名 listening review 内容已在签收后变化")
    elif route == "singing_acoustic_evidence" and not acoustic_pass:
        errors.append("singing acoustic evidence 未校准、未逐行覆盖或未绑定当前内容")
    elif route == "singing_acoustic_evidence" and acceptance.get("evidence_content_sha256") != mv_utils.json_hash(
            report.get("acoustic_evidence")):
        errors.append("声学证据内容已在签收后变化")
    elif route not in {"named_listening_review", "singing_acoustic_evidence"}:
        errors.append("alignment acceptance route 必须是 singing acoustic evidence 或 named listening review")
    if not text_timing_pass:
        correction = report.get("low_coverage_correction") or {}
        if not (
            correction.get("applied") is True
            and _valid_named_reviewer(correction.get("reviewer"))
            and str(correction.get("notes") or "").strip()
            and isinstance(correction.get("corrections"), list)
            and correction.get("corrections")
            and correction.get("bound_outputs_sha256") == outputs
        ):
            errors.append("歌词时间轴未达到完整行/90%字符/单行85%，必须先具名校正并绑定当前 ASS/LRC")
    for rel in ("字幕/karaoke.ass", "字幕/lyrics.lrc"):
        if stage == "compose" and not os.path.isfile(os.path.join(root, rel)):
            errors.append(f"正式字幕模式缺 {rel}")
    return errors


def _semantic_prompt_errors(root, stage, meta):
    if stage not in {"image", "video_jobs", "video", "compose"}:
        return []
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = _load_plan(root)
    receipt = mv_utils.load_json(os.path.join(root, "分镜", "semantic_prompts.json"), None)
    if not isinstance(receipt, dict):
        return ["缺语义分镜消费收据；preview 不得用 demo 标志绕过，用 compose_prompts.py 覆盖全部 clips"]
    errors = []
    if _strict_int(receipt.get("schema_version")) != 3:
        errors.append("semantic_prompts 必须是当前 schema v3")
    if receipt.get("complete") is not True:
        errors.append("semantic_prompts.complete 必须为 true；partial 收据不能进入付费/合成阶段")
    if int(receipt.get("updated_clips") or 0) != len(plan.get("clips") or []):
        errors.append("semantic_prompts 未覆盖全部 clip；正式项目不得用通用占位动作直接出图")
    if receipt.get("result_clip_plan_sha256") != mv_utils.content_hash(plan_path):
        errors.append("semantic_prompts 收据未绑定当前 clip_plan；重新注入或签收语义分镜")
    recorded = receipt.get("inputs_sha256") or {}
    for key, rel in (("lyrics", "词/lyrics.md"), ("blueprint", "视觉蓝图.md")):
        if recorded.get(key) != mv_utils.content_hash(os.path.join(root, rel)):
            errors.append(f"semantic_prompts 已过期：{rel} 变化")
    expected_ids = {
        str(clip.get("clip_id")) for clip in plan.get("clips") or []
        if isinstance(clip, dict) and clip.get("clip_id")
    }
    prompt_receipts = receipt.get("prompt_outputs_sha256")
    if not isinstance(prompt_receipts, dict) or set(prompt_receipts) != expected_ids:
        errors.append("semantic_prompts.prompt_outputs_sha256 未精确覆盖当前 clip 全集")
        prompt_receipts = {}
    for clip in plan.get("clips") or []:
        if not isinstance(clip, dict) or not clip.get("clip_id"):
            continue
        clip_id = str(clip["clip_id"])
        outputs = prompt_receipts.get(clip_id)
        if not isinstance(outputs, dict) or set(outputs) != {"image", "video"}:
            errors.append(f"semantic_prompts 缺 {clip_id} image/video prompt 输出收据")
            continue
        for key, field in (("image", "image_prompt_path"), ("video", "video_prompt_path")):
            prompt_rel = str(clip.get(field) or "")
            current = mv_utils.content_hash(os.path.join(root, prompt_rel)) if prompt_rel else ""
            if not current or outputs.get(key) != current:
                errors.append(f"semantic_prompts {clip_id}.{key} prompt 缺失或已变化")
    return errors


def _load_plan(root):
    return mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}


def _image_qc_path(root):
    return os.path.join(root, "生产数据", "image_qc", "image_qc.json")


def _image_ledger_audit(root):
    """Recompute B14 health; the ledger's cached summary is non-authoritative."""
    module = _image_receipts_module()
    return module.audit_ledger(Path(root))


def _image_qc_errors_warnings(root, stage):
    if stage not in {"video_jobs", "video", "compose"}:
        return [], []
    path = _image_qc_path(root)
    report = mv_utils.load_json(path, None)
    if not isinstance(report, dict):
        return [f"缺 mv-image 出图落档机检报告：{path}；先跑 `python3 skills/mv/mv-image/scripts/image_qc.py <作品根>`"], []
    summary = report.get("summary") or {}
    env = report.get("qc_environment") or {}
    errors = []
    warnings = []
    if report.get("kind") != "mv_image_qc" or (_strict_int(report.get("version")) or -1) < 3:
        errors.append("mv-image image_qc 必须是 version>=3 mv_image_qc")
    hard_value = summary.get("hard_blocks")
    if isinstance(hard_value, bool) or not isinstance(hard_value, (int, float)):
        return [f"mv-image image_qc 报告格式异常：summary.hard_blocks 缺失或不是数值（{path}）"], []
    hard = int(hard_value)
    if hard:
        errors.append(f"mv-image image_qc 仍有 hard block={hard}（主角脸崩/图损坏/禁用本地贴脸产物）；先回 mv-image 修复重跑")
    precision = str(env.get("precision_level") or "").strip()
    if precision != "full":
        errors.append(f"mv-image image_qc 机检精度为 {precision or 'unknown'}；B14 承重门只接受 full，"
                      "人工说明不得伪造机检通过")
    if summary.get("verdict") != "ok":
        errors.append(f"mv-image image_qc verdict={summary.get('verdict') or 'missing'}；只接受 ok")
    try:
        advisory = int(summary.get("advisory") or 0)
    except (TypeError, ValueError):
        advisory = 0
    if advisory or summary.get("verdict") == "review":
        warnings.append(f"mv-image image_qc 有非阻断初筛项 advisory={advisory}，进入视频前请确认主色/锚点/参考输入已复核")
    provenance = report.get("generation_provenance") or {}
    provenance_blocks = _strict_int((provenance.get("summary") or {}).get("block"))
    if not provenance.get("complete") or provenance_blocks is None or provenance_blocks:
        errors.append("出图缺逐资产 model+channel+prompt+reference+asset+B14 attempt 当前生成收据")

    plan = _load_plan(root)
    recorded_assets = report.get("assets_sha256")
    stale = []
    if isinstance(recorded_assets, dict):
        # 确定性新鲜度：QC 报告记录被检图片的内容 SHA-256；当前文件 hash 与之不符即过期。
        # （替代旧 mtime 口径——恢复旧图/版本回滚/跨机复制不会改 mtime 序，但骗不过内容 hash。）
        for clip in plan.get("clips", []):
            if not isinstance(clip, dict):
                continue
            rels = [clip.get("image_path")]
            if clip.get("need_end_frame"):
                rels.append(clip.get("end_frame_path"))
            for rel in rels:
                if not rel:
                    continue
                current = mv_utils.content_hash(os.path.join(root, rel))
                if current and current != str(recorded_assets.get(str(rel)) or ""):
                    stale.append(str(rel))
    else:
        errors.append("image_qc 缺 assets_sha256；旧 mtime 报告不得进入视频阶段")
    if stale:
        errors.append(f"mv-image image_qc 已过期：{len(stale)} 张图片与 QC 报告收据不一致，例：{stale[0]}；重跑 image_qc")
    try:
        audit = _image_ledger_audit(root)
    except Exception as exc:
        errors.append(f"B14 image acceptance ledger 动态审计失败：{exc}")
    else:
        audit_summary = audit.get("summary") or {}
        if not audit_summary.get("all_current_accepted"):
            examples = [
                f"{row.get('asset')}:{','.join(row.get('findings') or [])}"
                for row in audit.get("rows") or [] if row.get("status") != "accepted"
            ]
            errors.append(
                "B14 逐图 ledger 未全部 current/full/ok/具名通过："
                f"accepted={audit_summary.get('accepted', 0)}/{audit_summary.get('expected', 0)}"
                + (f"；例：{examples[0]}" if examples else "")
            )
        else:
            # B14 proves acceptance.  The aggregate QC must independently bind
            # that same complete current asset set; neither receipt substitutes
            # for the other.
            accepted_assets = {
                str(row.get("asset") or "") for row in audit.get("rows") or []
                if row.get("status") == "accepted" and row.get("asset")
            }
            missing_from_qc = sorted(
                rel for rel in accepted_assets
                if recorded_assets.get(rel) != mv_utils.content_hash(os.path.join(root, rel))
            )
            if missing_from_qc:
                errors.append(
                    "image_qc.assets_sha256 未完整绑定 B14 当前 accepted 集合；"
                    f"例：{missing_from_qc[0]}"
                )
    return errors, warnings


def _identity_readiness(root, stage, meta):
    """主角定妆包 readiness 闸：核心角色缺锚直接 BLOCK。

    此前定妆包不全只在 mv-review 汇总为 warn，付费 gate 不拦——定妆不 ready 时
    image_qc 的脸检 floor 无法自标定，出视频后主角漂移无人拦。image 期共享定妆
    本身尚在产出 → 只 warn 提醒先做定妆；video_jobs（正式）→ error。"""
    if stage not in {"image", "video_jobs", "video", "compose"}:
        return [], []
    formal_block = stage in {"video_jobs", "video", "compose"}
    registry = mv_utils.load_json(os.path.join(root, "设定", "identity_registry.json"), None)
    if not isinstance(registry, dict):
        msg = ("缺 设定/identity_registry.json（身份/参考真值）；"
               "先跑 `python3 skills/mv/mv-craft/scripts/identity_registry.py <作品根>`")
        return ([msg], []) if formal_block else ([], [msg])
    lead_id = registry.get("lead_id")
    lead = next((row for row in registry.get("identities") or []
                 if isinstance(row, dict) and row.get("id") == lead_id), None)
    if not isinstance(lead, dict):
        return [], ["identity_registry 缺主角身份行（lead_id 未命中 identities）；重跑 identity_registry.py"]
    groups = {g.get("id"): g for g in registry.get("reference_groups") or [] if isinstance(g, dict)}
    group = groups.get(lead.get("reference_group")) or {}
    existing = [p for p in group.get("paths") or [] if p and os.path.exists(os.path.join(root, str(p)))]
    if group.get("status") == "ready" and len(existing) >= 3:
        return [], []
    msg = (f"主角『{lead.get('display_name') or lead_id}』定妆包未 ready"
           f"（现存参考 {len(existing)} 张，需≥3：正面/侧脸或三分之二/全身…）；"
           "先补共享定妆再批量出图——定妆不全时脸机检 floor 无法自标定，出视频后漂移无人拦")
    return ([msg], []) if formal_block else ([], [msg])


def _demo_flag_warnings(root, stage, meta):
    """Warn when the compatibility demo mirror disagrees with settings truth.

    No hard gate consumes `_meta.is_demo`; preview is an explicit compose
    fallback path.  Keep ``formal_readiness`` in the action text because older
    clients discover that migration command from this advisory.
    """
    runtime = _runtime_state(root)
    meta_demo = bool(meta.get("is_demo"))
    if stage not in _COSTLY_STAGES:
        return []
    evidence = []
    lock = mv_utils.load_json(os.path.join(root, "制片", "picture_lock.json"), {}) or {}
    if lock.get("accepted"):
        evidence.append("picture_lock 已签收")
    jobs = (mv_utils.load_json(os.path.join(root, "出视频", "jobs_manifest.json"), {}) or {}).get("jobs") or []
    if any(isinstance(j, dict) and j.get("selected_take") for j in jobs):
        evidence.append("jobs_manifest 已有挑版记录")
    qc = mv_utils.load_json(_image_qc_path(root), {}) or {}
    if (qc.get("generation_provenance") or {}).get("complete"):
        evidence.append("出图生成收据完整")
    mismatch = meta_demo != runtime["is_demo"]
    if not mismatch and not (runtime["is_demo"] and evidence):
        return []
    context = f"；已有正式生产痕迹：{'；'.join(evidence)}" if evidence else ""
    return [
        f"_meta.is_demo={str(meta_demo).lower()} 与 _设置.md 派生值 "
        f"{str(runtime['is_demo']).lower()} 不一致{context}；gate 已按 settings-first 执行且不降级。"
        "可跑 formal_readiness.py 检查迁移后同步兼容镜像"
    ]


def _shot_variety_warnings(root, stage):
    """视觉多样性/构图冗余 事前机检（advisory · 出图前）。永不制造 block——只把 warn 抬进报告。

    出图（image）是最便宜的拦截点：clip_plan 已定、还没花积分出图/出视频。此层照『advisory 绝不
    造假 block』约定，全部落 warnings。"""
    if stage not in {"image", "video_jobs"}:
        return []
    clip_plan = os.path.join(root, "分镜", "clip_plan.json")
    if not os.path.exists(clip_plan):
        return []
    path = os.path.join(root, "生产数据", "shot_variety", "shot_variety.json")
    report = mv_utils.load_json(path, None)
    if not isinstance(report, dict):
        return ["未跑视觉多样性事前机检；出图前建议 `python3 skills/mv/mv-review/scripts/shot_variety_audit.py <作品根> --write`"
                "（查同构图反复/景别单调/副歌静镜/场景滞留/大变化镜头缺参考锚）"]
    warnings = []
    recorded = (report.get("inputs_sha256") or {}).get("分镜/clip_plan.json")
    if recorded and recorded != mv_utils.content_hash(clip_plan):
        warnings.append("视觉多样性机检已过期：clip_plan 变化后未重跑 shot_variety_audit")
    summary = report.get("summary") or {}
    try:
        warn = int(summary.get("warn") or 0)
    except (TypeError, ValueError):
        warn = 0
    if warn:
        codes = sorted({str(f.get("code")) for f in (report.get("findings") or [])
                        if f.get("severity") == "warn"})
        warnings.append(f"视觉多样性事前机检有 {warn} 条 advisory（{'/'.join(codes) or 'n/a'}）——"
                        "出图前回 mv-plan 换景别/机位/运镜/场景/补参考，别把同构图撑满全曲")
    return warnings


def _drift_risk_warnings(root, stage):
    """出图前漂移风险预测（advisory · mv-image drift_risk）。永不制造 block——缺/过期/high 都只进 warnings。

    与 _shot_variety_warnings 同惯例：gate 只消费报告文件，不 subprocess 跑 advisory 脚本。
    image 是最便宜的拦截点——参考锚该挂在哪、哪些镜先打样，应在花积分前知道。"""
    if stage not in {"image", "video_jobs"}:
        return []
    clip_plan = os.path.join(root, "分镜", "clip_plan.json")
    if not os.path.exists(clip_plan):
        return []
    path = os.path.join(root, "生产数据", "drift_risk", "drift_risk.json")
    report = mv_utils.load_json(path, None)
    if not isinstance(report, dict):
        return ["未跑出图前漂移风险预测；建议 `python3 skills/mv/mv-image/scripts/drift_risk.py <作品根> --write`"
                "（预测近景/大表情/换装/极端角度/多主体哪些 clip 最易漂，出图前挂参考锚最便宜）"]
    warnings = []
    recorded = (report.get("inputs_sha256") or {}).get("分镜/clip_plan.json")
    if recorded and recorded != mv_utils.content_hash(clip_plan):
        warnings.append("漂移风险预测已过期：clip_plan 变化后未重跑 drift_risk")
    summary = report.get("summary") or {}
    try:
        high = int(summary.get("high") or 0)
    except (TypeError, ValueError):
        high = 0
    if high:
        warnings.append(f"漂移风险预测有 {high} 个 high 风险 clip——出图前给这些镜挂定妆/表情/场景参考，"
                        "并让它们先进打样矩阵验证")
    return warnings


def _craft_audit_warnings(root, stage):
    """传统 MV 手法机检（advisory · mv-review craft_audit）。永不制造 block——只把 warn 抬进报告。

    副歌复现升级/动静对比/hook 上脸/冷开场/关键镜候选等结构律在出图前机检最便宜；
    与 _shot_variety_warnings 同惯例：gate 只消费报告文件。"""
    if stage not in {"image", "video_jobs"}:
        return []
    clip_plan = os.path.join(root, "分镜", "clip_plan.json")
    if not os.path.exists(clip_plan):
        return []
    path = os.path.join(root, "生产数据", "craft_audit", "craft_audit.json")
    report = mv_utils.load_json(path, None)
    if not isinstance(report, dict):
        return ["未跑传统手法机检；出图前建议 `python3 skills/mv/mv-review/scripts/craft_audit.py <作品根> --write`"
                "（查副歌复现无升级/动静无对比/hook 不上脸/冷开场过长/关键镜单候选/bridge 不换气）"]
    warnings = []
    recorded = (report.get("inputs_sha256") or {}).get("分镜/clip_plan.json")
    if recorded and recorded != mv_utils.content_hash(clip_plan):
        warnings.append("传统手法机检已过期：clip_plan 变化后未重跑 craft_audit")
    summary = report.get("summary") or {}
    try:
        warn = int(summary.get("warn") or 0)
    except (TypeError, ValueError):
        warn = 0
    if warn:
        codes = sorted({str(f.get("code")) for f in (report.get("findings") or [])
                        if f.get("severity") == "warn"})
        warnings.append(f"传统手法机检有 {warn} 条 advisory（{'/'.join(codes) or 'n/a'}）——"
                        "副歌要一次比一次大、主歌收副歌放、hook 至少一次上脸唱；回 mv-plan 调结构再出图")
    return warnings


# 正式项目 clip 数达到此规模仍未打样 → 提示先 mini-pilot（advisory）。小盘打样收益低，不打扰。
PILOT_MIN_CLIPS = 12


def _pilot_matrix_warnings(root, stage, meta):
    """打样探针矩阵（advisory · mv-plan pilot_matrix）。只对正式大盘提示，永不 block。

    全量出图是 MV 最大的单笔积分支出；正式项目大盘（≥PILOT_MIN_CLIPS）建议先出 3-5 个
    代表镜（开场/副歌爆点/最高漂移风险/最大运动/换装首镜）验证脸/风格/体感再全量。"""
    if stage != "image" or _runtime_state(root)["is_demo"]:
        return []
    plan = _load_plan(root)
    clips = [c for c in plan.get("clips") or [] if isinstance(c, dict)]
    if len(clips) < PILOT_MIN_CLIPS:
        return []
    path = os.path.join(root, "生产数据", "pilot_matrix", "pilot_matrix.json")
    report = mv_utils.load_json(path, None)
    if not isinstance(report, dict):
        return [f"正式项目 {len(clips)} 个 clip 将全量出图，未见打样矩阵；建议先 "
                "`python3 skills/mv/mv-plan/scripts/pilot_matrix.py <作品根> --write` "
                "挑 3-5 个代表镜打样验证脸/风格/爆点，再全量出图"]
    recorded = (report.get("inputs_sha256") or {}).get("分镜/clip_plan.json")
    if recorded and recorded != mv_utils.content_hash(os.path.join(root, "分镜", "clip_plan.json")):
        return ["打样矩阵已过期：clip_plan 变化后未重跑 pilot_matrix"]
    return []


def _route_contract_errors(route, capability, label):
    if not isinstance(route, dict):
        return [f"{label} 缺 provider_route"]
    errors = []
    if not str(route.get("provider_id") or "").strip():
        errors.append(f"{label} provider_route 缺 provider_id")
    if route.get("access_status") not in {"available", "legacy"}:
        errors.append(f"{label} provider_route access_status 不可执行")
    if route.get("capability_graph_version") != capability.CAPABILITY_GRAPH_VERSION:
        errors.append(f"{label} provider_route capability graph version 已过期")
    if route.get("capability_graph_sha256") != capability.graph_sha256():
        errors.append(f"{label} provider_route capability graph hash 已过期")
    route_body = {key: value for key, value in route.items() if key != "route_sha256"}
    if route.get("route_sha256") != capability.stable_hash(route_body):
        errors.append(f"{label} provider_route hash 无效")
    return errors


def _video_manifest_errors(root, stage):
    """Validate schema-4 jobs against the current capability implementation.

    The task package is an executable provider contract, not a planning hint:
    current prompts/controls/routes are checked dynamically and every selected
    result must carry an attested submit receipt.  Stored inherit reports are
    still required so the operator has a reviewable receipt, but are never the
    sole source of truth.
    """
    if stage not in {"video", "compose"}:
        return []
    manifest_rel = "出视频/jobs_manifest.json"
    manifest_path = os.path.join(root, manifest_rel)
    manifest = mv_utils.load_json(manifest_path, None)
    if not isinstance(manifest, dict):
        return [f"缺或损坏 {manifest_rel}；先生成 schema v4 视频任务包"]
    errors = []
    if manifest.get("kind") != "mv_video_jobs" or _strict_int(manifest.get("schema_version")) != 4:
        errors.append("jobs_manifest 必须是 schema v4 mv_video_jobs；旧任务包不得承担真实提交证据")
    try:
        inherit = _video_inherit_module()
        capability = inherit.video_capabilities
    except Exception as exc:
        return errors + [f"无法加载 mv-video 能力/继承权威实现：{exc}"]

    runtime = _runtime_state(root)
    expected_settings = {
        "video_model": runtime["video_model"],
        "video_channel": runtime["video_channel"],
        "video_spec": runtime["video_spec"],
    }
    for key, expected in expected_settings.items():
        if str(manifest.get(key) or "") != str(expected or ""):
            errors.append(f"jobs_manifest.{key} 未采用当前 _设置.md：{manifest.get(key)!r} != {expected!r}")

    if manifest.get("capability_graph_version") != capability.CAPABILITY_GRAPH_VERSION:
        errors.append("jobs_manifest capability_graph_version 已过期")
    if manifest.get("capability_graph_sha256") != capability.graph_sha256():
        errors.append("jobs_manifest capability_graph_sha256 已过期")
    errors.extend(_route_contract_errors(manifest.get("provider_route"), capability, "jobs_manifest"))

    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = _load_plan(root)
    plan_hash = mv_utils.content_hash(plan_path)
    if not plan_hash or manifest.get("clip_plan_sha256") != plan_hash:
        errors.append("jobs_manifest 未绑定当前 clip_plan")

    freshness = manifest.get("freshness") or {}
    if _strict_int(freshness.get("schema_version")) != 1:
        errors.append("jobs_manifest.freshness 必须是 schema 1")
    prompt_files = {}
    reference_files = {}
    for owner in list(manifest.get("jobs") or []) + list(manifest.get("sequence_units") or []):
        take_rows = owner.get("takes") or [owner]
        for take in take_rows:
            prompt_rel = str(take.get("prompt_path") or "")
            if prompt_rel:
                prompt_files[prompt_rel] = mv_utils.content_hash(os.path.join(root, prompt_rel))
            for ref in (take.get("compiled_request_controls") or {}).get("input_roles") or []:
                if not isinstance(ref, dict):
                    continue
                ref_rel = str(ref.get("path") or "")
                if ref_rel:
                    reference_files[ref_rel] = mv_utils.content_hash(os.path.join(root, ref_rel))
    required_project = {
        "_设置.md": mv_utils.content_hash(os.path.join(root, "_设置.md")),
        "分镜/clip_plan.json": plan_hash,
        "生产数据/image_qc/image_qc.json": mv_utils.content_hash(_image_qc_path(root)),
        **prompt_files,
        **reference_files,
    }
    project_snapshot = freshness.get("project_files") or {}
    for rel, digest in required_project.items():
        if not digest or project_snapshot.get(rel) != digest:
            errors.append(f"jobs_manifest freshness 缺失/过期：{rel}")
    implementation_snapshot = freshness.get("implementation_files") or {}
    required_implementation = {
        "skills/mv/_lib/mv_video_prompt_compiler.py",
        "skills/mv/_lib/video_capabilities.py",
    }
    for rel in required_implementation:
        digest = mv_utils.content_hash(os.path.join(REPO, rel))
        if not digest or implementation_snapshot.get(rel) != digest:
            errors.append(f"jobs_manifest implementation freshness 缺失/过期：{rel}")
    if freshness.get("settings_sha256") != required_project.get("_设置.md"):
        errors.append("jobs_manifest freshness.settings_sha256 已过期")
    if freshness.get("image_qc_sha256") != required_project.get("生产数据/image_qc/image_qc.json"):
        errors.append("jobs_manifest freshness.image_qc_sha256 已过期")
    if freshness.get("prompt_bundle_sha256") != capability.stable_hash(prompt_files):
        errors.append("jobs_manifest prompt bundle freshness hash 无效")
    if freshness.get("reference_inputs_sha256") != capability.stable_hash(reference_files):
        errors.append("jobs_manifest reference inputs freshness hash 无效")
    for finding in inherit.check_manifest_freshness(root, manifest):
        if finding.get("level") == "block":
            errors.append(f"jobs_manifest freshness block: {finding.get('code')}")

    plan_rows = [row for row in plan.get("clips") or [] if isinstance(row, dict)]
    job_rows = [row for row in manifest.get("jobs") or [] if isinstance(row, dict)]
    plan_ids = [str(row.get("clip_id") or "") for row in plan_rows]
    job_ids = [str(row.get("clip_id") or "") for row in job_rows]
    if not plan_ids or job_ids != plan_ids or len(set(job_ids)) != len(job_ids):
        errors.append("jobs_manifest.jobs 必须按当前 clip_plan 精确、唯一、同序覆盖全部 clips")
    jobs = {str(row.get("clip_id") or ""): row for row in job_rows}
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    timeline_rows = {str(row.get("clip_id") or ""): row for row in timeline.get("clips") or [] if isinstance(row, dict)}

    for clip in plan_rows:
        clip_id = str(clip.get("clip_id") or "")
        job = jobs.get(clip_id)
        if not job:
            continue
        expected_model = contract.normalize_video_model(clip.get("video_model") or runtime["video_model"])
        expected_channel = contract.normalize_video_channel(
            clip.get("video_channel") or clip.get("video_backend") or runtime["video_channel"]
        )
        if str(job.get("video_model") or "") != str(expected_model or ""):
            errors.append(f"{clip_id} video_model 未采用当前 settings/clip override")
        if str(job.get("backend") or "") != str(expected_channel or ""):
            errors.append(f"{clip_id} backend 未采用当前 settings/clip override")
        route = job.get("provider_route") or {}
        errors.extend(_route_contract_errors(route, capability, clip_id))
        if route.get("model") != job.get("video_model") or route.get("channel") != job.get("backend"):
            errors.append(f"{clip_id} provider_route 未绑定 job model×channel")
        takes = [row for row in job.get("takes") or [] if isinstance(row, dict)]
        if not takes:
            errors.append(f"{clip_id} 缺 take 合同")
            continue
        by_take = {}
        for take in takes:
            take_id = str(take.get("take_id") or "")
            if not take_id or take_id in by_take:
                errors.append(f"{clip_id} take_id 缺失或重复")
                continue
            by_take[take_id] = take
            take_route = take.get("provider_route") or route
            errors.extend(_route_contract_errors(take_route, capability, f"{clip_id}/{take_id}"))
            for field in ("planned_request_controls", "compiled_request_controls"):
                controls = take.get(field)
                digest = take.get(f"{field}_sha256")
                if not isinstance(controls, dict) or digest != capability.stable_hash(controls):
                    errors.append(f"{clip_id}/{take_id} {field} 或 SHA 无效")
            compiler = take.get("prompt_compiler") or {}
            if compiler.get("kind") != inherit.COMPILER_KIND or compiler.get("version") != inherit.COMPILER_VERSION:
                errors.append(f"{clip_id}/{take_id} 必须使用当前 prompt compiler v{inherit.COMPILER_VERSION}")
            prompt_rel = str(take.get("prompt_path") or "")
            prompt_text = mv_utils.read_text(os.path.join(root, prompt_rel)) if prompt_rel else ""
            for finding in inherit.check_compiled_prompt(
                    prompt_text, take, job.get("video_model") or job.get("backend")):
                if finding.get("level") == "block":
                    errors.append(f"{clip_id}/{take_id} compiled prompt block: {finding.get('code')}")
            registered = bool(take.get("video_sha256") or take.get("status") in {"registered", "selected"})
            if registered:
                video_rel = str(take.get("video_path") or "")
                if not video_rel or take.get("video_sha256") != mv_utils.content_hash(os.path.join(root, video_rel)):
                    errors.append(f"{clip_id}/{take_id} 登记视频已变化或缺 hash")
                for finding in inherit.check_submit_receipt(root, take, job):
                    if finding.get("level") == "block":
                        errors.append(f"{clip_id}/{take_id} submit receipt block: {finding.get('code')}")

        selected_id = str(job.get("selected_take") or "")
        selected = by_take.get(selected_id)
        if not selected:
            errors.append(f"{clip_id} 未挑版或 selected_take 不存在")
            continue
        if selected.get("status") != "selected":
            errors.append(f"{clip_id}/{selected_id} 未标记 selected")
        selected_rel = str(job.get("selected_video_path") or "")
        selected_hash = mv_utils.content_hash(os.path.join(root, selected_rel)) if selected_rel else ""
        if not selected_hash or selected_hash != selected.get("video_sha256"):
            errors.append(f"{clip_id} selected 视频未绑定登记 take 的当前 hash")
        timeline_row = timeline_rows.get(clip_id) or {}
        if str(timeline_row.get("video_path") or "") != selected_rel:
            errors.append(f"{clip_id} timeline.video_path 未绑定 jobs_manifest 挑版结果")
        score = selected.get("score") or {}
        score_fields = ["motion", "identity", "beat_fit", "clarity"]
        if (job.get("seam_contract") or {}).get("continuity_required"):
            score_fields.append("seam_fit")
        if job.get("lip_sync_required"):
            score_fields.append("lip_sync")
        score_invalid = (
            any(isinstance(score.get(key), bool) or not isinstance(score.get(key), (int, float)) for key in score_fields)
            or not str(selected.get("scored_by") or "").strip()
        )
        waiver = selected.get("selection_waiver") or {}
        waiver_ok = bool(str(waiver.get("reviewer") or "").strip() and str(waiver.get("reason") or "").strip())
        if score_invalid and not waiver_ok:
            errors.append(f"{clip_id}/{selected_id} 挑版缺具名完整评分或具名例外")

    for unit in manifest.get("sequence_units") or []:
        if not isinstance(unit, dict) or unit.get("status") != "split_registered":
            continue
        cut_map = unit.get("verified_cut_map") or {}
        boundaries = cut_map.get("actual_boundaries_seconds") or []
        try:
            numeric_boundaries = [float(value) for value in boundaries]
        except (TypeError, ValueError):
            numeric_boundaries = []
        cut_body = dict(cut_map) if isinstance(cut_map, dict) else {}
        cut_hash = cut_body.pop("cut_map_sha256", "")
        if (
            cut_map.get("kind") != "mv_video_sequence_cut_map"
            or _strict_int(cut_map.get("schema_version")) != 1
            or cut_hash != capability.stable_hash(cut_body)
            or cut_map.get("source_sha256") != unit.get("source_sha256")
            or not str(cut_map.get("reviewer") or "").strip()
            or not str(cut_map.get("notes") or "").strip()
            or cut_map.get("review_method") not in {
                "frame_accurate_visual_review", "nle_marker_export", "provider_shot_metadata_verified",
            }
            or len(numeric_boundaries) != len(unit.get("clip_ids") or []) + 1
            or any(right <= left for left, right in zip(numeric_boundaries, numeric_boundaries[1:]))
        ):
            errors.append(f"{unit.get('unit_id') or 'sequence'} verified cut map 无效")

    inherit_rel = "生产数据/video_inherit_contract/inherit_contract.json"
    persisted = mv_utils.load_json(os.path.join(root, inherit_rel), None)
    if (not isinstance(persisted, dict) or persisted.get("kind") != "mv_video_inherit_contract"
            or _strict_int(persisted.get("schema_version")) != 2):
        errors.append(f"缺或损坏当前 schema v2 {inherit_rel}")
    else:
        persisted_hard = _strict_int((persisted.get("summary") or {}).get("hard_blocks"))
        if persisted_hard is None or persisted_hard:
            errors.append(f"{inherit_rel} hard_blocks 缺失或不为 0")
        expected_inputs = {
            rel: mv_utils.content_hash(os.path.join(root, rel))
            for rel in ("分镜/clip_plan.json", manifest_rel, "设定/identity_registry.json", "分镜/reference_plan.json")
        }
        if any(not digest for digest in expected_inputs.values()) or persisted.get("inputs_sha256") != expected_inputs:
            errors.append(f"{inherit_rel} inputs_sha256 不完整或已过期")
    try:
        current_inherit = inherit.build_report(root)
        current_hard = _strict_int((current_inherit.get("summary") or {}).get("hard_blocks"))
        if current_hard is None or current_hard:
            errors.append(f"当前动态重算 inherit_contract 仍有 hard_blocks={current_hard!r}")
    except Exception as exc:
        errors.append(f"动态重算 inherit_contract 失败：{exc}")
    return list(dict.fromkeys(errors))


def _video_report_errors(root, stage):
    if stage not in {"video", "compose"}:
        return []
    errors = _video_manifest_errors(root, stage)
    report_rel = "生产数据/video_qc/video_qc.json"
    report = mv_utils.load_json(os.path.join(root, report_rel), None)
    if (not isinstance(report, dict) or report.get("kind") != "mv_video_qc"
            or _strict_int(report.get("schema_version")) != 2):
        return errors + [f"缺或损坏 schema v2 {report_rel}；全部视频挑版后重跑 video_qc"]
    hard = _strict_int((report.get("summary") or {}).get("hard_blocks"))
    if hard is None or hard:
        errors.append(f"{report_rel} hard_blocks 缺失或不为 0：{hard!r}")
    required_inputs = ("分镜/clip_plan.json", "分镜/timeline_manifest.json")
    recorded = report.get("inputs_sha256") or {}
    for rel in required_inputs:
        current = mv_utils.content_hash(os.path.join(root, rel))
        if not current or recorded.get(rel) != current:
            errors.append(f"{report_rel} 已过期：{rel} 与报告 hash 不一致；重跑对应检查")
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    expected_videos = {
        str(row.get("video_path")): mv_utils.content_hash(os.path.join(root, str(row.get("video_path"))))
        for row in timeline.get("clips") or [] if isinstance(row, dict) and row.get("video_path")
    }
    video_hashes = report.get("selected_video_sha256") or {}
    if not expected_videos or any(not digest for digest in expected_videos.values()) or video_hashes != expected_videos:
        errors.append(f"{report_rel} selected_video_sha256 未精确绑定 timeline 全集当前视频")
    semantic = report.get("semantic_review") or {}
    if not semantic.get("accepted") or not str(semantic.get("reviewer") or "").strip():
        errors.append("缺具名视频语义人工签收：逐镜/接缝复核后运行 video_qc.py --accept-semantic --reviewer <name>")
    else:
        if semantic.get("bound_video_sha256") != video_hashes:
            errors.append("视频语义签收未绑定当前 selected_video_sha256；重跑 video_qc 具名签收")
        seam_hash = mv_utils.json_hash([
            seam.get("seam_contract") or {} for seam in report.get("seams") or []
        ])
        if semantic.get("bound_seam_contract_sha256") != seam_hash:
            errors.append("视频语义签收未绑定当前接缝分类合同；重跑 video_qc 逐缝签收")
    return list(dict.fromkeys(errors))


def _color_contract_errors(root, stage):
    if stage != "compose":
        return []
    rel = "生产数据/color/color_input_manifest.json"
    manifest = mv_utils.load_json(os.path.join(root, rel), None)
    if (not isinstance(manifest, dict) or manifest.get("kind") != "mv_color_input_manifest"
            or _strict_int(manifest.get("schema_version")) != 2):
        return [f"缺或损坏 schema v2 {rel}；先跑 color_input_manifest.py"]
    errors = []
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    timeline = mv_utils.load_json(timeline_path, {}) or {}
    if manifest.get("timeline_sha256") != mv_utils.content_hash(timeline_path):
        errors.append("color_input_manifest 未绑定当前 timeline_manifest")
    selected = []
    for row in timeline.get("clips") or []:
        value = str(row.get("video_path") or "") if isinstance(row, dict) else ""
        if value and value not in selected:
            selected.append(value)
    expected_hashes = {path: mv_utils.content_hash(os.path.join(root, path)) for path in selected}
    input_rows = [row for row in manifest.get("inputs") or [] if isinstance(row, dict)]
    if not selected or [str(row.get("path") or "") for row in input_rows] != selected:
        errors.append("color_input_manifest.inputs 未按 timeline 精确同序覆盖选中视频")
    if any(not digest for digest in expected_hashes.values()) or manifest.get("inputs_sha256") != expected_hashes:
        errors.append("color_input_manifest.inputs_sha256 缺失或视频变化后已过期")
    acceptance = manifest.get("untagged_acceptance") or {}
    untagged_hashes = {
        str(row.get("path")): expected_hashes.get(str(row.get("path")))
        for row in input_rows if row.get("classification") == "untagged"
    }
    acceptance_ok = bool(
        untagged_hashes
        and acceptance.get("accepted") is True
        and acceptance.get("interpret_as") == "bt709"
        and str(acceptance.get("reviewer") or "").strip()
        and str(acceptance.get("notes") or "").strip()
        and acceptance.get("bound_inputs_sha256") == untagged_hashes
    )
    for row in input_rows:
        path = str(row.get("path") or "")
        if row.get("sha256") != expected_hashes.get(path):
            errors.append(f"color input row 已过期：{path}")
        classification = row.get("classification")
        transform = str(row.get("ffmpeg_input_filter") or "")
        if classification == "declared_bt709_limited":
            if row.get("interpretation") != "bt709_limited" or "range=tv" not in transform:
                errors.append(f"{path} limited Rec.709 解释/输出 transform 不完整")
        elif classification == "declared_bt709_full":
            if (row.get("interpretation") != "bt709_full"
                    or "in_range=full" not in transform or "out_range=limited" not in transform):
                errors.append(f"{path} full-range 输入缺显式 full→limited scale")
        elif classification == "untagged":
            if (not acceptance_ok
                    or row.get("interpretation") != "bt709_limited_by_named_source_interpretation"
                    or "range=tv" not in transform):
                errors.append(f"{path} untagged 输入缺具名、当前 hash 绑定的 Rec.709 解释")
        else:
            errors.append(f"{path} 不支持的 color classification：{classification or 'missing'}")
    hard = _strict_int((manifest.get("summary") or {}).get("hard_blocks"))
    if hard != 0 or (manifest.get("summary") or {}).get("verdict") != "ok":
        errors.append("color_input_manifest.summary 必须 hard_blocks=0 且 verdict=ok")
    if manifest.get("output_space") != "bt709_sdr_limited":
        errors.append("color_input_manifest.output_space 必须为 bt709_sdr_limited")
    return list(dict.fromkeys(errors))


def _picture_lock_errors(root, stage, meta):
    if stage not in {"video_jobs", "video", "compose"}:
        return []
    path = os.path.join(root, "制片", "picture_lock.json")
    payload = mv_utils.load_json(path, None)
    if not isinstance(payload, dict) or not payload.get("accepted"):
        return ["正式项目缺已签收 picture lock；先 render_animatic.py，再 picture_lock.py --reviewer <name>"]
    errors = []
    recorded_inputs = payload.get("inputs_sha256") or {}
    plan = _load_plan(root)
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    editorial_hash = mv_utils.timeline_edit_hash(timeline)
    if payload.get("editorial_timeline_sha256") != editorial_hash:
        errors.append("picture lock 已过期：镜头顺序/切点/时长/接缝意图发生变化；重渲 animatic 并重新签收")
    if payload.get("otio_timeline_sha256") != editorial_hash:
        errors.append("picture lock 未绑定同一 OTIO 编辑合同；重导 OTIO、重渲 animatic 并重新签收")
    required = {
        "分镜/clip_plan.json", "节拍/beatgrid.json", "分镜/animatic.mp4",
        "生产数据/animatic/animatic.json", "生产数据/image_qc/image_qc.json",
        "评分/pacing_prescore.json", "分镜/semantic_prompts.json",
    }
    song = mv_utils.find_song(root)
    if song:
        required.add(mv_utils.relpath(root, song))
    for clip in plan.get("clips", []):
        for key in ("image_path", "image_prompt_path", "video_prompt_path"):
            if clip.get(key):
                required.add(clip[key])
        if clip.get("need_end_frame") and clip.get("end_frame_path"):
            required.add(clip["end_frame_path"])
    settings = mv_utils.parse_settings(root)
    vocal_performance = any(
        clip.get("action_family") == "performance_vocal" or clip.get("vocal_lyrics")
        for clip in plan.get("clips", []) if isinstance(clip, dict)
    )
    if settings.get("字幕语言", "中文") != "无字幕" or (
        vocal_performance and settings.get("演唱口型", "仅正面演唱镜") != "关闭"
    ):
        required.add("字幕/alignment_report.json")
    for optional in ("视觉蓝图.md", "词/lyrics.md", "分镜/semantic_prompts.json"):
        if os.path.exists(os.path.join(root, optional)):
            required.add(optional)
    omitted = [rel for rel in required if rel not in recorded_inputs]
    if omitted:
        errors.append(f"picture lock 输入不完整，未绑定：{omitted[0]}")
    for rel, recorded in recorded_inputs.items():
        if mv_utils.content_hash(os.path.join(root, rel)) != recorded:
            errors.append(f"picture lock 已过期：{rel} 已变化；重渲 animatic 并重新签收")
            break
    animatic_report = mv_utils.load_json(os.path.join(root, "生产数据", "animatic", "animatic.json"), {}) or {}
    if animatic_report.get("output_sha256") != mv_utils.content_hash(os.path.join(root, "分镜", "animatic.mp4")):
        errors.append("animatic 报告未绑定当前 分镜/animatic.mp4；重跑 render_animatic.py")
    if animatic_report.get("timeline_edit_sha256") != editorial_hash:
        errors.append("animatic 不是当前编辑时间线的预演；重跑 render_animatic.py")
    return errors


def _vlm_judge_warnings(root, stage):
    """VLM 并排裁决覆盖率对账（advisory · 出图后看图判内容）。永不制造 block——只把 warn 抬进报告。

    参照同仓漫画线 2026-07-17 实证修的"机检空转"漏洞：裁决任务包生成后 0 条被执行、
    gate 不告警照样 pass，画错主体无人拦。mv 的数值机检（脸余弦/dHash）不看内容，
    "同一个人吗/接缝接得上吗"必须有看图裁决层；本函数照 gate『只读报告文件、不 subprocess』
    惯例消费 生产数据/vlm_judge/ 两个文件，做三档告警：缺任务包→建议跑；0 裁决→机检空转；
    部分裁决→覆盖率不足；suspect/低分→逐条转 warn。"""
    if stage not in {"image", "video_jobs", "compose"}:
        return []
    clip_plan = os.path.join(root, "分镜", "clip_plan.json")
    if not os.path.exists(clip_plan):
        return []
    tasks_file = os.path.join(root, "生产数据", "vlm_judge", "vlm_judge_tasks.json")
    tasks_payload = mv_utils.load_json(tasks_file, None)
    if not isinstance(tasks_payload, dict):
        return ["未生成 VLM 并排裁决任务包；出图后建议 `python3 skills/mv/mv-review/scripts/vlm_judge.py <作品根> --write`"
                "（主角身份/接缝连续两轴看图裁决——数值机检不看内容，这层缺席时换脸/断缝只能靠人肉抽查）"]
    warnings = []
    recorded = (tasks_payload.get("inputs_sha256") or {}).get("分镜/clip_plan.json")
    if recorded and recorded != mv_utils.content_hash(clip_plan):
        warnings.append("VLM 裁决任务包已过期：clip_plan 变化后未重跑 vlm_judge --write")
    task_list = [t for t in (tasks_payload.get("tasks") or []) if isinstance(t, dict)]
    if not task_list:
        return warnings
    # 合同校验：裁决必须复制 image_sha256/task_sha256 且带 evaluator，缺一即视为未裁决（防空壳/防陈旧）。
    expected = {
        str(t.get("task_id")): (str((t.get("image") or {}).get("sha256") or ""), str(t.get("task_sha256") or ""))
        for t in task_list
    }
    verdicts_payload = mv_utils.load_json(
        os.path.join(root, "生产数据", "vlm_judge", "vlm_judge_verdicts.json"), {}) or {}
    valid = {}
    for record in verdicts_payload.get("verdicts") or []:
        if not isinstance(record, dict):
            continue
        tid = str(record.get("task_id") or "")
        contract = expected.get(tid)
        evaluator = record.get("evaluator") if isinstance(record.get("evaluator"), dict) else {}
        if (contract and contract[0] and str(record.get("image_sha256") or "") == contract[0]
                and str(record.get("task_sha256") or "") == contract[1]
                and str(evaluator.get("model") or "").strip()):
            valid[tid] = record
    if not valid:
        warnings.append(f"VLM 并排裁决空转：任务包已生成 {len(task_list)} 条但 0 条有效裁决——"
                        "主角身份/接缝连续机检形同虚设，由多模态 agent 逐条看图打分写回 verdict 文件")
        return warnings
    if len(valid) < len(task_list):
        warnings.append(f"VLM 并排裁决覆盖率不足：{len(valid)}/{len(task_list)}——未裁决 clip 无内容级保障，补齐后重跑 gate")
    for tid, record in sorted(valid.items()):
        scores = record.get("scores") if isinstance(record.get("scores"), dict) else {}
        low = [f"{k}={v}" for k, v in scores.items() if isinstance(v, (int, float)) and v <= 2]
        if str(record.get("verdict") or "").lower() == "suspect" or low:
            warnings.append(f"VLM 裁决存疑 {tid}：{'、'.join(low) or 'verdict=suspect'}"
                            f"{('；' + str(record.get('notes'))) if record.get('notes') else ''}——并排人审，确认漂移则重抽该 clip")
    return warnings


def check(root, stage):
    errors = []
    warnings = []
    raw_meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    # All preference-like runtime fields come from canonical settings.  Keep
    # evidentiary compatibility fields (rights attestations, title, etc.) from
    # meta, but never let its stale demo/model/platform mirrors weaken a gate.
    meta = dict(raw_meta)
    meta.update(_runtime_state(root))
    errors.extend(_settings_truth_errors(root, stage))
    song = mv_utils.find_song(root)
    lyrics = os.path.join(root, "词", "lyrics.md")
    beatgrid = os.path.join(root, "节拍", "beatgrid.json")
    blueprint = os.path.join(root, "视觉蓝图.md")
    clip_plan = os.path.join(root, "分镜", "clip_plan.json")
    timeline = os.path.join(root, "分镜", "timeline_manifest.json")

    if stage in {"beat", "plan", "image", "video_jobs", "video", "lyric_sync", "compose"} and not song:
        errors.append("缺 歌/song.*，请先补入最终成品歌")
    if (stage in {"plan", "image", "video_jobs", "video", "lyric_sync", "compose"}
            and _lyrics_required(root, meta, stage) and not os.path.exists(lyrics)):
        errors.append("缺 词/lyrics.md")
    if stage in {"plan", "image", "video_jobs", "video", "compose"} and not os.path.exists(beatgrid):
        errors.append("缺 节拍/beatgrid.json，先跑 mv-beat")
    beat_errors, beat_warnings = _beatgrid_contract(root, stage, meta, song)
    errors.extend(beat_errors)
    warnings.extend(beat_warnings)
    if stage in {"script_review", "plan", "image", "video_jobs", "video"} and not os.path.exists(blueprint):
        errors.append("缺 视觉蓝图.md")
    if stage in {"plan", "image", "video_jobs", "video", "compose"} and _has_rough_blueprint(root):
        errors.append("视觉蓝图仍是 rough，正式产物阶段前先用 mv-script 复核")
    if stage in {"image", "video_jobs", "video", "compose"} and not os.path.exists(clip_plan):
        errors.append("缺 分镜/clip_plan.json，先跑 mv-plan")
    if stage == "compose" and not os.path.exists(timeline):
        errors.append("缺 分镜/timeline_manifest.json，compose 默认不按目录猜顺序")

    if stage == "video_jobs" and os.path.exists(clip_plan):
        plan = _load_plan(root)
        missing = []
        for clip in plan.get("clips", []):
            image_path = clip.get("image_path")
            if image_path and not os.path.exists(os.path.join(root, image_path)):
                missing.append(f"{clip.get('clip_id')}:{image_path}")
        if missing:
            errors.append(f"缺 {len(missing)} 个首帧 PNG，先跑 mv-image；例：{missing[0]}")

    qc_errors, qc_warnings = _image_qc_errors_warnings(root, stage)
    errors.extend(qc_errors)
    warnings.extend(qc_warnings)
    identity_errors, identity_warnings = _identity_readiness(root, stage, meta)
    errors.extend(identity_errors)
    warnings.extend(identity_warnings)
    warnings.extend(_demo_flag_warnings(root, stage, raw_meta))
    warnings.extend(_shot_variety_warnings(root, stage))
    warnings.extend(_craft_audit_warnings(root, stage))
    warnings.extend(_drift_risk_warnings(root, stage))
    warnings.extend(_vlm_judge_warnings(root, stage))
    warnings.extend(_pilot_matrix_warnings(root, stage, meta))
    errors.extend(_video_report_errors(root, stage))
    errors.extend(_color_contract_errors(root, stage))
    errors.extend(_picture_lock_errors(root, stage, meta))
    errors.extend(_timeline_contract_errors(root, stage, meta))
    errors.extend(_otio_contract_errors(root, stage, meta))
    errors.extend(_pacing_receipt_errors(root, stage, meta))
    errors.extend(_alignment_contract_errors(root, stage, meta))
    errors.extend(_semantic_prompt_errors(root, stage, meta))

    if stage == "compose" and os.path.exists(timeline):
        data = mv_utils.load_json(timeline, {}) or {}
        missing = []
        for clip in data.get("clips", []):
            video_path = clip.get("video_path")
            if not video_path or not os.path.exists(os.path.join(root, video_path)):
                missing.append(clip.get("clip_id") or video_path or "unknown")
        if missing:
            errors.append(f"timeline 有 {len(missing)} 个 clip 未选中视频，例：{missing[0]}")
        # 交叉核对挑版台账：timeline 仅按"文件存在"判选中，绕过 --select 手动丢入的 clip
        # 会冒充已选中且无 take/分记录。demo 可提醒，正式交付必须登记/评分/挑版。
        jobs = (mv_utils.load_json(os.path.join(root, "出视频", "jobs_manifest.json"), {}) or {}).get("jobs") or []
        if jobs:
            selected_ids = {j.get("clip_id") for j in jobs if j.get("selected_take")}
            unverified = [
                clip.get("clip_id") for clip in data.get("clips", [])
                if clip.get("video_path")
                and os.path.exists(os.path.join(root, clip["video_path"]))
                and clip.get("clip_id") not in selected_ids
            ]
            if unverified:
                message = (
                    f"{len(unverified)} 个 clip 有成片视频但 jobs_manifest 无挑版记录"
                    f"（可能绕过 --select 手动放入）：{unverified[0]}…；先登记、具名评分并挑版。"
                )
                errors.append(message)

    errors.extend(_rights_errors(root, stage, meta))
    errors.extend(_staleness_errors(root, stage, meta))

    if stage == "lyric_sync" and os.path.exists(lyrics):
        lines = [
            x.strip() for x in mv_utils.read_text(lyrics).splitlines()
            if x.strip() and not x.strip().startswith("#") and not mv_utils.SECTION_RE.match(x.strip())
        ]
        if not lines:
            errors.append("词/lyrics.md 没有可对齐歌词行")

    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description="检查制MV阶段前置 gate")
    ap.add_argument("project_root")
    ap.add_argument("stage")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    errors, warnings = check(root, args.stage)
    for msg in warnings:
        print(f"[warn] {msg}")
    if errors:
        for msg in errors:
            print(f"[err] {msg}", file=sys.stderr)
        return 1
    print(f"[ok] gate pass: {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
