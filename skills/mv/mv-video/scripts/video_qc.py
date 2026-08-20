#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic MV video QC.

Semantic visual checks still need human review, but this catches mechanical
issues before compose: duration drift, wrong aspect, stray audio, missing
selected files, and adjacent seam risk signals.
"""
import argparse
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "mv_utils.py")
COMPLETION_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "completion.py")
IMAGE_QC_PATH = os.path.join(REPO, "skills", "mv", "mv-image", "scripts", "image_qc.py")


def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv_utils = load_mv_utils()


def load_completion():
    spec = importlib.util.spec_from_file_location("mv_completion_for_video_qc", COMPLETION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_image_qc():
    try:
        spec = importlib.util.spec_from_file_location("mv_image_qc_for_video", IMAGE_QC_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


ASPECTS = {
    "9:16": 9 / 16,
    "16:9": 16 / 9,
    "1:1": 1.0,
}


try:
    from PIL import Image, ImageStat
except Exception:  # pragma: no cover - optional dependency
    Image = None
    ImageStat = None


def have_ffmpeg():
    return shutil.which("ffmpeg") is not None


def probe(path):
    data = mv_utils.ffprobe_json(path, "-show_entries", "format=duration", "-show_streams")
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = any(s.get("codec_type") == "audio" for s in streams)
    dur = None
    try:
        dur = float((data.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        pass
    fps = None
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate")
    if rate and "/" in rate:
        a, b = rate.split("/", 1)
        try:
            fps = float(a) / float(b) if float(b) else None
        except ValueError:
            fps = None
    return {
        "duration": dur,
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": fps,
        "has_audio": audio,
        "color_primaries": video.get("color_primaries"),
        "color_transfer": video.get("color_transfer"),
        "color_space": video.get("color_space"),
        "color_range": video.get("color_range"),
        "streams": len(streams),
    }


def safe_name(value):
    return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in str(value or "clip"))


def sample_times(duration):
    try:
        dur = float(duration)
    except (TypeError, ValueError):
        dur = 0
    if dur <= 0:
        return [("start", 0.0)]
    return [
        ("start", round(min(0.08, max(0.0, dur * 0.03)), 3)),
        ("mid", round(dur / 2, 3)),
        ("end", round(max(0.0, dur - min(0.08, max(0.02, dur * 0.03))), 3)),
    ]


def extract_frame(video_path, t, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{float(t):.3f}",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return proc.returncode == 0 and os.path.exists(out_path), proc.stderr.strip()


def image_stats(path):
    if Image is None or ImageStat is None or not os.path.exists(path):
        return {"available": False}
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((64, 64))
            stat = ImageStat.Stat(im)
            mean = [round(x, 2) for x in stat.mean[:3]]
            brightness = round(sum(mean) / 3, 2)
            return {
                "available": True,
                "size": list(im.size),
                "mean_rgb": mean,
                "brightness": brightness,
                "perceptual_hash": perceptual_hash(im),
            }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def perceptual_hash(image):
    gray = image.convert("L").resize((16, 16))
    pixels = list(gray.getdata())
    mean = sum(pixels) / len(pixels)
    return "".join("1" if value >= mean else "0" for value in pixels)


def hash_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return None
    return round(1.0 - sum(x != y for x, y in zip(a, b)) / len(a), 4)


def color_distance(a, b):
    if not a or not b or not a.get("available") or not b.get("available"):
        return None
    av = a.get("mean_rgb") or []
    bv = b.get("mean_rgb") or []
    if len(av) < 3 or len(bv) < 3:
        return None
    return round(math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(av[:3], bv[:3]))), 2)


def sample_frames(root, cid, video_path, duration, findings):
    rows = []
    if not have_ffmpeg():
        return rows, "ffmpeg_missing"
    frame_dir = os.path.join(root, "生产数据", "video_qc", "frames", safe_name(cid))
    for label, t in sample_times(duration):
        rel = os.path.join("生产数据", "video_qc", "frames", safe_name(cid), f"{label}.jpg").replace(os.sep, "/")
        out = os.path.join(root, rel)
        ok, err = extract_frame(video_path, t, out)
        row = {"label": label, "time": t, "path": rel, "ok": ok}
        if ok:
            row["stats"] = image_stats(out)
        else:
            row["error"] = err
            findings.append({"level": "warn", "code": "frame_extract_failed", "label": label, "time": t})
        rows.append(row)
    return rows, ""


def aspect_from_meta(root):
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    settings = mv_utils.parse_settings(root)
    return meta.get("aspect") or settings.get("合成画幅") or "9:16"


def duration_tol(expected):
    try:
        expected = float(expected)
    except (TypeError, ValueError):
        return 0.5
    return max(0.25, expected * 0.12)


def check_clip(root, clip, expected_aspect):
    rel = clip.get("video_path") or clip.get("selected_video_path")
    cid = clip.get("clip_id")
    findings = []
    if not rel:
        return {"clip_id": cid, "video_path": rel, "findings": [{"level": "block", "code": "missing_video_path"}], "verdict": "block"}
    path = os.path.join(root, rel)
    if not os.path.exists(path):
        return {"clip_id": cid, "video_path": rel, "findings": [{"level": "block", "code": "selected_video_missing"}], "verdict": "block"}
    info = probe(path)
    if not info.get("streams"):
        findings.append({"level": "block", "code": "ffprobe_failed"})
    dur = info.get("duration")
    expected_dur = clip.get("duration")
    if dur is not None and expected_dur is not None:
        diff = abs(float(expected_dur) - dur)
        if diff > duration_tol(expected_dur):
            findings.append({"level": "warn", "code": "duration_drift", "expected": expected_dur, "actual": round(dur, 3), "diff": round(diff, 3)})
    width, height = info.get("width"), info.get("height")
    if width and height:
        expected = ASPECTS.get(expected_aspect)
        if expected and abs((width / height) - expected) > 0.04:
            findings.append({"level": "warn", "code": "aspect_drift", "width": width, "height": height, "expected": expected_aspect})
        if min(width, height) < 720:
            findings.append({"level": "warn", "code": "low_resolution", "width": width, "height": height})
    if info.get("has_audio"):
        findings.append({"level": "warn", "code": "clip_has_audio", "msg": "compose should normally use the master song track; mute clip audio unless native audio is intentionally approved"})
    hdr_markers = {"bt2020", "smpte2084", "arib-std-b67"}
    color_values = {info.get("color_primaries"), info.get("color_transfer"), info.get("color_space")}
    if color_values & hdr_markers:
        findings.append({"level": "block", "code": "hdr_input_requires_explicit_tonemap",
                         "color": sorted(x for x in color_values if x)})
    elif not any((info.get("color_primaries"), info.get("color_transfer"), info.get("color_space"))):
        findings.append({"level": "warn", "code": "unmanaged_input_color",
                         "msg": "输入无色彩标签；正式调色需确认按 Rec.709 解释而非仅在输出补标签"})
    frames, frame_note = sample_frames(root, cid, path, dur or expected_dur, findings)
    if frame_note:
        findings.append({"level": "warn", "code": frame_note})
    visual_adherence = {}
    start_frame = next((row for row in frames if row.get("label") == "start" and row.get("ok")), {})
    first_image = clip.get("image_path")
    if first_image and os.path.exists(os.path.join(root, first_image)) and start_frame:
        source_stats = image_stats(os.path.join(root, first_image))
        start_stats = start_frame.get("stats") or {}
        similarity = hash_similarity(source_stats.get("perceptual_hash"), start_stats.get("perceptual_hash"))
        delta = color_distance(source_stats, start_stats)
        visual_adherence["first_frame"] = {"source": first_image, "perceptual_similarity": similarity, "mean_rgb_distance": delta}
        if similarity is not None and similarity < 0.45:
            findings.append({"level": "warn", "code": "first_frame_visual_drift", "similarity": similarity})
    end_target = clip.get("end_frame_path") if clip.get("need_end_frame") else None
    end_frame = next((row for row in frames if row.get("label") == "end" and row.get("ok")), {})
    if end_target and os.path.exists(os.path.join(root, end_target)) and end_frame:
        target_stats = image_stats(os.path.join(root, end_target))
        actual_stats = end_frame.get("stats") or {}
        similarity = hash_similarity(target_stats.get("perceptual_hash"), actual_stats.get("perceptual_hash"))
        visual_adherence["end_frame"] = {"target": end_target, "perceptual_similarity": similarity,
                                          "mean_rgb_distance": color_distance(target_stats, actual_stats)}
        if similarity is not None and similarity < 0.45:
            findings.append({"level": "warn", "code": "end_frame_visual_drift", "similarity": similarity})
    return {
        "clip_id": cid,
        "video_path": rel,
        "probe": info,
        "frame_samples": frames,
        "visual_adherence": visual_adherence,
        "findings": findings,
        "verdict": "block" if any(f.get("level") == "block" for f in findings) else ("review" if findings else "ok"),
    }


def location_key(clip):
    """clip 的场景键（与 mv-review shot_variety_audit 同口径：location_id/setup_group/location_name/section）。"""
    sd = clip.get("shot_design") or {}
    for key in ("location_id", "setup_group", "location_name"):
        value = str(sd.get(key) or "").strip()
        if value:
            return value
    return str(clip.get("section") or "").strip()


def load_discontinuity_exceptions(root):
    """已签署的「有意不连续」例外账本：制片/intentional_discontinuity.json。

    MV 常有刻意的段落 look 跳变（副歌切黑白/闪回/换色调）——机器只看色距会把导演意图
    误报成 seam risk。例外必须**具名**（reviewer）且写明 reason 才生效：把「这是刻意的」
    从口头共识变成留痕决定。只豁免 advisory 级的同场景硬切色跳；continuity_required
    接缝声明了连续又签不连续=矛盾信号，仍保留 risk 并另加提示。"""
    payload = mv_utils.load_json(os.path.join(root, "制片", "intentional_discontinuity.json"), {}) or {}
    out = {}
    for row in payload.get("entries") or []:
        if not isinstance(row, dict):
            continue
        key = (str(row.get("from") or ""), str(row.get("to") or ""))
        signed = str(row.get("reviewer") or "").strip() and str(row.get("reason") or row.get("notes") or "").strip()
        if all(key) and signed:
            out[key] = row
    return out


def seam_rows(clips, clip_rows, exceptions=None):
    rows = []
    exceptions = exceptions or {}
    for prev_clip, cur_clip, prev, cur in zip(clips, clips[1:], clip_rows, clip_rows[1:]):
        contract = prev_clip.get("seam_contract") or (prev_clip.get("continuity") or {}).get("outgoing_seam") or {}
        exception = exceptions.get((str(prev.get("clip_id")), str(cur.get("clip_id"))))
        risk = []
        if prev.get("verdict") != "ok" or cur.get("verdict") != "ok":
            risk.append("adjacent_clip_has_qc_warning")
        pd = ((prev.get("probe") or {}).get("duration"))
        cd = ((cur.get("probe") or {}).get("duration"))
        if pd and cd and (math.isnan(pd) or math.isnan(cd)):
            risk.append("duration_probe_nan")
        prev_end = next((f for f in prev.get("frame_samples", []) if f.get("label") == "end"), {})
        cur_start = next((f for f in cur.get("frame_samples", []) if f.get("label") == "start"), {})
        dist = color_distance((prev_end.get("stats") or {}), (cur_start.get("stats") or {}))
        if dist is not None and dist > 120:
            if contract.get("continuity_required"):
                risk.append("large_color_delta_breaks_continuous_seam")
                if exception:
                    # 声明了连续接缝却又签「有意不连续」——矛盾信号，不豁免，提示先改其一。
                    risk.append("intentional_exception_conflicts_continuous_seam")
            elif location_key(prev_clip) and location_key(prev_clip) == location_key(cur_clip):
                if not exception:
                    # 同场景硬切色跳：同一场景相邻镜主色/色温跳变=观感断裂。
                    # 非连续接缝无 end-frame 合同可依，只作 advisory 风险提示，人工并排复核。
                    # 已具名签署 intentional_discontinuity 的接缝豁免（导演刻意 look 跳变）。
                    risk.append("same_scene_hard_cut_color_jump")
        seam_similarity = hash_similarity(
            (prev_end.get("stats") or {}).get("perceptual_hash"),
            (cur_start.get("stats") or {}).get("perceptual_hash"),
        )
        if contract.get("continuity_required"):
            adherence = (prev.get("visual_adherence") or {}).get("end_frame") or {}
            if not adherence:
                risk.append("continuous_seam_missing_end_frame_evidence")
            if seam_similarity is not None and seam_similarity < 0.35:
                risk.append("continuous_seam_large_structure_jump")
        rows.append({
            "from": prev.get("clip_id"),
            "to": cur.get("clip_id"),
            "risk": risk,
            "intentional_discontinuity": exception or None,
            "end_frame": prev_end.get("path"),
            "start_frame": cur_start.get("path"),
            "mean_rgb_distance": dist,
            "perceptual_similarity": seam_similarity,
            "seam_contract": contract,
            "manual_review": contract.get("review") or [
                "identity", "wardrobe_props", "screen_direction", "subtitle_safe_area", "beat_hit"
            ],
        })
    return rows


FACE_DRIFT_FALLBACK = 0.45
# 重度脸漂带：低于（自标定阈值 - 该余量）视为「不是同一个人」级别的漂移。
# 阈值本身已含 0.05 视频运动余量；再让出 0.15 只拦板上钉钉的重漂——embedding 证据支撑的
# 确定性硬闸（B10 合规），轻/中度漂移仍走 warn+人审。唯一出口是具名+绑定视频 hash 的 waiver。
SEVERE_FACE_DRIFT_MARGIN = 0.15


def load_face_drift_waivers(root):
    """具名重度脸漂 waiver 账本：制片/face_drift_waivers.json。

    每条必须具名（reviewer）+ 写明 reason + 绑定当时 selected 视频 sha256；
    视频一重出/重选，绑定即失效，必须重新签。风格化 MV 中 embedding 系统性偏低而
    人眼确认同人时，这是显式留痕的逃生口——不是默认放行。"""
    payload = mv_utils.load_json(os.path.join(root, "制片", "face_drift_waivers.json"), {}) or {}
    out = {}
    for row in payload.get("entries") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("clip_id") or "")
        signed = str(row.get("reviewer") or "").strip() and str(row.get("reason") or "").strip()
        if cid and signed and str(row.get("bound_video_sha256") or ""):
            out[cid] = row
    return out


def face_drift_threshold(root):
    """脸相似阈值自标定：借 image_qc 主角定妆组 lead_floor（同人下限），留 0.05 视频运动余量。

    此前硬编码 0.45 与 image_qc『用本曲定妆组自标定、不写死阈值』的理念相悖——
    风格化 MV 脸跨帧余弦整体偏低，经验值会系统性误报 review。未自标定时回退 0.45。"""
    report = mv_utils.load_json(os.path.join(root, "生产数据", "image_qc", "image_qc.json"), {}) or {}
    face = (report.get("checks") or {}).get("face") or {}
    floor = face.get("lead_floor")
    if face.get("lead_calibrated") and isinstance(floor, (int, float)):
        return max(0.20, min(0.60, float(floor) - 0.05)), "image_qc_lead_floor_calibrated"
    return FACE_DRIFT_FALLBACK, "fallback_uncalibrated"


def apply_face_identity_qc(root, clips, clip_rows):
    image_qc = load_image_qc()
    app = image_qc._load_embedder() if image_qc else None
    if app is None:
        return "unavailable"
    threshold, threshold_source = face_drift_threshold(root)
    severe_floor = max(0.20, round(threshold - SEVERE_FACE_DRIFT_MARGIN, 4))
    waivers = load_face_drift_waivers(root)
    for clip, row in zip(clips, clip_rows):
        source = clip.get("image_path")
        if not source or not os.path.exists(os.path.join(root, source)):
            continue
        source_embedding = image_qc._embed(app, os.path.join(root, source))
        if source_embedding is None:
            continue
        scores = []
        for frame in row.get("frame_samples") or []:
            if not frame.get("ok"):
                continue
            embedding = image_qc._embed(app, os.path.join(root, frame["path"]))
            if embedding is not None:
                scores.append({"label": frame.get("label"), "score": round(image_qc.cosine(source_embedding, embedding), 4)})
        row["face_identity_adherence"] = {"mode": "insightface", "source": source, "samples": scores,
                                          "threshold": threshold, "threshold_source": threshold_source,
                                          "severe_floor": severe_floor}
        video_rel = row.get("video_path")
        current_sha = mv_utils.content_hash(os.path.join(root, video_rel)) if video_rel else ""
        findings, verdict = face_drift_verdict(
            scores, threshold, severe_floor, threshold_source,
            waivers.get(str(row.get("clip_id"))), current_sha,
        )
        row["findings"].extend(findings)
        if verdict == "block":
            row["verdict"] = "block"
        elif verdict == "review" and row["verdict"] != "block":
            row["verdict"] = "review"
    return "insightface"


def face_drift_verdict(scores, threshold, severe_floor, threshold_source, waiver, current_video_sha):
    """脸漂裁决（纯函数·可测）：轻/中度=warn+人审；重度=block，唯一出口是绑定当前视频 sha 的具名 waiver。

    重度脸漂＝embedding 证据级「换人」——出图侧 G1 是硬闸，视频侧同人底线不能反而只 warn。
    waiver 绑定 selected 视频 sha；视频重出/换版后旧 waiver 自动失效。"""
    low = [sample for sample in scores if sample["score"] < threshold]
    severe = [sample for sample in scores if sample["score"] < severe_floor]
    if severe:
        if waiver and current_video_sha and waiver.get("bound_video_sha256") == current_video_sha:
            return [{"level": "warn", "code": "video_face_identity_drift_severe_waived",
                     "samples": severe, "severe_floor": severe_floor,
                     "waiver": {"reviewer": waiver.get("reviewer"), "date": waiver.get("date")},
                     "message": "重度脸漂已具名 waiver（绑定当前视频）；换版后需重签"}], "review"
        return [{"level": "block", "code": "video_face_identity_drift_severe",
                 "samples": severe, "threshold": threshold,
                 "severe_floor": severe_floor,
                 "threshold_source": threshold_source,
                 "message": "视频帧与首帧脸 embedding 相距重度带以下（疑似换人）；"
                            "重出/换 take，或人眼确认同人后 "
                            "video_qc.py --accept-face-drift <Clip_ID> --reviewer <name> --notes <理由> 具名放行"}], "block"
    if low:
        return [{"level": "warn", "code": "video_face_identity_drift",
                 "samples": low, "threshold": threshold,
                 "threshold_source": threshold_source,
                 "message": "需与定妆/首帧并排人工复核"}], "review"
    return [], None


def build_report(root):
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    plan_by_id = {c.get("clip_id"): c for c in plan.get("clips", []) if isinstance(c, dict)}
    expected_aspect = aspect_from_meta(root)
    timeline_clips = timeline.get("clips") or []
    merged = []
    for row in timeline_clips:
        base = dict(plan_by_id.get(row.get("clip_id"), {}))
        base.update(row)
        merged.append(base)
    clip_rows = [check_clip(root, c, expected_aspect) for c in merged]
    face_mode = apply_face_identity_qc(root, merged, clip_rows)
    hard = sum(1 for r in clip_rows for f in r.get("findings", []) if f.get("level") == "block")
    warn = sum(1 for r in clip_rows for f in r.get("findings", []) if f.get("level") == "warn")
    seams = seam_rows(merged, clip_rows, load_discontinuity_exceptions(root))
    sampled = sum(1 for r in clip_rows for f in r.get("frame_samples", []) if f.get("ok"))
    input_paths = ("分镜/clip_plan.json", "分镜/timeline_manifest.json")
    selected_hashes = {row.get("video_path"): mv_utils.content_hash(os.path.join(root, row.get("video_path")))
                       for row in merged if row.get("video_path") and os.path.exists(os.path.join(root, row.get("video_path")))}
    report = {
        "schema_version": 2,
        "kind": "mv_video_qc",
        "generated_at": date.today().isoformat(),
        "root_rel": ".",
        "expected_aspect": expected_aspect,
        "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in input_paths},
        "selected_video_sha256": selected_hashes,
        "summary": {
            "clips": len(clip_rows),
            "hard_blocks": hard,
            "warnings": warn,
            "seams": len(seams),
            "frame_samples": sampled,
            "verdict": "block" if hard else ("review" if warn else "ok"),
            "semantic_scope": "deterministic first/end-frame and seam signals; identity/outfit/prop/pose require calibrated face/VLM or signed human review",
            "face_identity_mode": face_mode,
        },
        "clips": clip_rows,
        "seams": seams,
    }
    return report


def write_report(root, report):
    out_dir = os.path.join(root, "生产数据", "video_qc")
    mv_utils.write_json(os.path.join(out_dir, "video_qc.json"), report)
    lines = [
        "# video QC",
        "",
        f"- verdict: {report['summary']['verdict']}",
        f"- clips: {report['summary']['clips']}",
        f"- hard_blocks: {report['summary']['hard_blocks']}",
        f"- warnings: {report['summary']['warnings']}",
        f"- frame_samples: {report['summary'].get('frame_samples', 0)}",
        "",
    ]
    for row in report.get("clips", []):
        info = row.get("probe") or {}
        lines.append(f"## {row.get('clip_id')} · {row.get('verdict')}")
        if info:
            lines.append(f"- probe: {info.get('duration')}s · {info.get('width')}x{info.get('height')} · fps={info.get('fps')} · audio={info.get('has_audio')}")
        for frame in row.get("frame_samples", []):
            stats = frame.get("stats") or {}
            lines.append(f"- frame {frame.get('label')} @{frame.get('time')}s: {frame.get('path')} · ok={frame.get('ok')} · mean_rgb={stats.get('mean_rgb')}")
        for f in row.get("findings", []):
            lines.append(f"- {f.get('level')}: {f.get('code')}")
        if not row.get("findings"):
            lines.append("- ok")
        lines.append("")
    if report.get("seams"):
        lines.append("## Seams")
        for seam in report["seams"]:
            lines.append(
                f"- {seam.get('from')} -> {seam.get('to')}: mean_rgb_distance={seam.get('mean_rgb_distance')} "
                f"risk={','.join(seam.get('risk') or []) or 'none'}"
            )
    mv_utils.write_text(os.path.join(out_dir, "video_qc.md"), "\n".join(lines))
    return os.path.join(out_dir, "video_qc.json")


def main():
    ap = argparse.ArgumentParser(description="Run deterministic MV video QC")
    ap.add_argument("project_root")
    ap.add_argument("--no-fail", action="store_true")
    ap.add_argument("--accept-semantic", action="store_true", help="人工逐镜/逐接缝复核身份、服化道、空间、动作、口型和画风后签收")
    ap.add_argument("--accept-discontinuity", action="append", default=[], metavar="FROM:TO",
                    help="具名签署「有意不连续」接缝（如 Clip_03:Clip_04，可重复）；需 --reviewer 与 --notes 写明意图，"
                         "签署后该接缝的同场景硬切色跳不再报 advisory")
    ap.add_argument("--accept-face-drift", action="append", default=[], metavar="CLIP",
                    help="具名放行重度脸漂 clip（如 Clip_004，可重复）；需 --reviewer 与 --notes 说明人眼如何确认同人。"
                         "waiver 绑定该 clip 当前 selected 视频 sha256，视频重出/换版即失效")
    ap.add_argument("--reviewer", help="配合 --accept-semantic / --accept-discontinuity / --accept-face-drift，记录复核人")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    if args.accept_discontinuity:
        if not args.reviewer or not args.notes.strip():
            print("[err] --accept-discontinuity 必须同时提供 --reviewer 和 --notes（写明为什么是刻意的）", file=sys.stderr)
            return 2
        ledger_path = os.path.join(root, "制片", "intentional_discontinuity.json")
        ledger = mv_utils.load_json(ledger_path, {}) or {}
        entries = [row for row in ledger.get("entries") or [] if isinstance(row, dict)]
        for pair in args.accept_discontinuity:
            if ":" not in pair:
                print(f"[err] --accept-discontinuity 参数格式应为 FROM:TO，收到：{pair}", file=sys.stderr)
                return 2
            src, dst = (part.strip() for part in pair.split(":", 1))
            entries = [row for row in entries if not (row.get("from") == src and row.get("to") == dst)]
            entries.append({"from": src, "to": dst, "reviewer": args.reviewer,
                            "reason": args.notes, "date": date.today().isoformat()})
        mv_utils.write_json(ledger_path, {"kind": "mv_intentional_discontinuity", "entries": entries})
        print(f"[ok] 有意不连续例外 → {ledger_path}（{len(args.accept_discontinuity)} 条）")
    if args.accept_face_drift:
        if not args.reviewer or not args.notes.strip():
            print("[err] --accept-face-drift 必须同时提供 --reviewer 和 --notes（写明人眼如何确认同人）", file=sys.stderr)
            return 2
        timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
        video_by_clip = {str(c.get("clip_id")): c.get("video_path") for c in timeline.get("clips") or []
                         if isinstance(c, dict)}
        ledger_path = os.path.join(root, "制片", "face_drift_waivers.json")
        ledger = mv_utils.load_json(ledger_path, {}) or {}
        entries = [row for row in ledger.get("entries") or [] if isinstance(row, dict)]
        for cid in args.accept_face_drift:
            cid = cid.strip()
            video_rel = video_by_clip.get(cid)
            video_sha = mv_utils.content_hash(os.path.join(root, video_rel)) if video_rel else ""
            if not video_sha:
                print(f"[err] {cid} 无已选中的视频，waiver 无对象可绑定；先 --select 再签", file=sys.stderr)
                return 2
            entries = [row for row in entries if row.get("clip_id") != cid]
            entries.append({"clip_id": cid, "reviewer": args.reviewer, "reason": args.notes,
                            "date": date.today().isoformat(), "bound_video_sha256": video_sha})
        mv_utils.write_json(ledger_path, {"kind": "mv_face_drift_waivers", "entries": entries})
        print(f"[ok] 重度脸漂具名 waiver → {ledger_path}（{len(args.accept_face_drift)} 条，绑定当前视频 hash）")
    report = build_report(root)
    if args.accept_semantic:
        if not args.reviewer or not args.notes.strip():
            print("[err] --accept-semantic 必须同时提供 --reviewer 与非空 --notes", file=sys.stderr)
            return 2
        report["semantic_review"] = {
            "accepted": True,
            "reviewer": args.reviewer,
            "date": date.today().isoformat(),
            "notes": args.notes,
            "dimensions": ["identity", "hair_wardrobe", "props", "scene_topology", "screen_direction",
                           "pose_motion", "seam_intent_by_class", "lip_sync_if_applicable", "style_color", "subtitle_safe_area"],
            "bound_video_sha256": report.get("selected_video_sha256") or {},
            "bound_seam_contract_sha256": mv_utils.json_hash([
                seam.get("seam_contract") or {} for seam in report.get("seams") or []
            ]),
        }
    path = write_report(root, report)
    print(f"[ok] video QC → {path} ({report['summary']['verdict']})")
    if args.accept_semantic and not report["summary"]["hard_blocks"]:
        try:
            load_completion().mark_stage_complete(root, "video")
        except ValueError as exc:
            print(f"[err] video completion health 未通过：{exc}", file=sys.stderr)
            return 2
    if report["summary"]["hard_blocks"] and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
