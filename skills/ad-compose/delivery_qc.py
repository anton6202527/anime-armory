#!/usr/bin/env python3
"""Technical QA for every master/cutdown/reframe deliverable."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def seconds(value) -> float:
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group()) if m else 0.0


def frame_rate(value) -> float:
    raw = str(value or "0")
    if "/" in raw:
        a, b = raw.split("/", 1)
        try:
            return float(a) / float(b)
        except (ValueError, ZeroDivisionError):
            return 0.0
    return seconds(raw)


def resolution(value):
    match = re.fullmatch(r"\s*(\d+)\s*[x×]\s*(\d+)\s*", str(value or ""), re.I)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def probe(path: Path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.is_file():
        return None
    proc = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                          capture_output=True, text=True)
    if proc.returncode:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def measure_loudness(path: Path):
    """Measure integrated LUFS and true peak from the rendered file itself."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path.is_file():
        return None
    proc = subprocess.run([
        ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
        "-af", "loudnorm=I=-24:TP=-2:LRA=7:print_format=json", "-f", "null", "-",
    ], capture_output=True, text=True)
    text = proc.stderr or ""
    matches = re.findall(r"\{[\s\S]*?\}", text)
    if not matches:
        return None
    try:
        row = json.loads(matches[-1])
        return {
            "integrated_lufs": float(row["input_i"]),
            "true_peak_db": float(row["input_tp"]),
            "lra": float(row["input_lra"]),
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def inspect_item(root: Path, item: dict):
    path = root / item["expected_path"]
    findings = []
    data = probe(path)
    if data is None:
        findings.append({"severity": "block", "code": "media_unreadable", "msg": f"交付件不存在或 ffprobe 不可读：{path}"})
        return {"deliverable_id": item["deliverable_id"], "path": item["expected_path"], "passed": False, "findings": findings}
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    tech = item.get("technical_profile") if isinstance(item.get("technical_profile"), dict) else None
    if item.get("placement_mapping_error"):
        findings.append({"severity": "block", "code": "placement_mapping_invalid",
                         "msg": str(item.get("placement_mapping_error"))})
    if not tech:
        findings.append({"severity": "block", "code": "technical_profile_missing",
                         "msg": "交付计划缺 contract 派生的技术母版标准"})
    delivery_profile = item.get("delivery_profile") if isinstance(item.get("delivery_profile"), dict) else None
    if (not delivery_profile or not delivery_profile.get("authority") or not delivery_profile.get("source")
            or item.get("delivery_profile_error")):
        findings.append({"severity": "block", "code": "delivery_profile_provenance_missing",
                         "msg": str(item.get("delivery_profile_error") or "响度/真峰值目标缺 authority/source")})
    actual = seconds((data.get("format") or {}).get("duration"))
    expected = seconds(item.get("duration"))
    tol = max(0.25, expected * 0.03) if expected else 0.5
    if expected and abs(actual - expected) > tol:
        findings.append({"severity": "block", "code": "duration_mismatch",
                         "msg": f"实测 {actual:.3f}s 与交付目标 {expected:.3f}s 偏差超过 {tol:.3f}s"})
    constraints = item.get("platform_constraints") if isinstance(item.get("platform_constraints"), list) else []
    silent_allowed = bool(constraints) and all(spec.get("sound_mode") == "sound_off" for spec in constraints)
    if not audio:
        if not silent_allowed:
            findings.append({"severity": "block", "code": "audio_missing", "msg": "正式广告交付件无音轨"})
        else:
            findings.append({"severity": "info", "code": "sound_off_delivery",
                             "msg": "该交付件仅映射 sound-off placement；无音轨按版位策略放行，信息须由画面/字幕完整承载"})
        loudness = None
    else:
        if tech and str(audio.get("codec_name") or "") != str(tech.get("audio_codec") or ""):
            findings.append({"severity": "block", "code": "audio_codec_mismatch",
                             "msg": f"音频 codec={audio.get('codec_name')}，母版要求 {tech.get('audio_codec')}"})
        if tech and int(audio.get("sample_rate") or 0) != int(tech.get("audio_sample_rate") or 0):
            findings.append({"severity": "block", "code": "audio_sample_rate_mismatch",
                             "msg": f"音频采样率={audio.get('sample_rate')}，母版要求 {tech.get('audio_sample_rate')}Hz"})
        loudness = measure_loudness(path)
        if loudness is None:
            findings.append({"severity": "block", "code": "loudness_unmeasured", "msg": "无法实测交付响度/真峰值"})
        elif item.get("loudness_lufs") is None or item.get("true_peak_db") is None:
            findings.append({"severity": "block", "code": "delivery_profile_missing",
                             "msg": "交付计划缺 contract 派生的响度/真峰值目标"})
        else:
            target_lufs = float(item["loudness_lufs"])
            target_tp = float(item["true_peak_db"])
            if abs(loudness["integrated_lufs"] - target_lufs) > 1.5:
                findings.append({
                    "severity": "block", "code": "loudness_mismatch",
                    "msg": f"实测 {loudness['integrated_lufs']:.2f} LUFS，目标 {target_lufs:.2f}±1.5 LUFS",
                })
            if loudness["true_peak_db"] > target_tp + 0.2:
                findings.append({
                    "severity": "block", "code": "true_peak_exceeded",
                    "msg": f"实测真峰值 {loudness['true_peak_db']:.2f} dBTP，高于上限 {target_tp:.2f} dBTP",
                })
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    if not width or not height:
        findings.append({"severity": "block", "code": "video_stream_missing", "msg": "缺有效视频流/分辨率"})
    else:
        a, _, b = str(item.get("aspect") or "").replace("x", ":").partition(":")
        try:
            target = float(a) / float(b)
            if abs(width / height - target) > 0.02:
                findings.append({"severity": "block", "code": "aspect_mismatch",
                                 "msg": f"实测 {width}x{height} 与目标比例 {item.get('aspect')} 不符"})
        except (ValueError, ZeroDivisionError):
            findings.append({"severity": "warn", "code": "aspect_unknown", "msg": "无法解析目标比例"})
    fps = frame_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    if tech:
        if str(video.get("codec_name") or "") != str(tech.get("video_codec") or ""):
            findings.append({"severity": "block", "code": "video_codec_mismatch",
                             "msg": f"视频 codec={video.get('codec_name')}，母版要求 {tech.get('video_codec')}"})
        if str(video.get("pix_fmt") or "") != str(tech.get("pixel_format") or ""):
            findings.append({"severity": "block", "code": "pixel_format_mismatch",
                             "msg": f"pixel format={video.get('pix_fmt')}，母版要求 {tech.get('pixel_format')}"})
        if not (float(tech.get("frame_rate_min") or 0) <= fps <= float(tech.get("frame_rate_max") or 999)):
            findings.append({"severity": "block", "code": "frame_rate_mismatch",
                             "msg": f"实测 {fps:.3f}fps 超出母版范围"})
        color_fields = {
            "color_primaries": "color_primaries", "color_transfer": "color_transfer",
            "color_space": "color_space", "color_range": "color_range",
        }
        for profile_key, stream_key in color_fields.items():
            expected_color = str(tech.get(profile_key) or "")
            if expected_color and str(video.get(stream_key) or "") != expected_color:
                findings.append({
                    "severity": "block", "code": f"{profile_key}_mismatch",
                    "msg": f"{stream_key}={video.get(stream_key) or 'unspecified'}，SDR 母版要求 {expected_color}",
                })
        if tech.get("scan_type") == "progressive" and str(video.get("field_order") or "") != "progressive":
            findings.append({"severity": "block", "code": "scan_type_mismatch",
                             "msg": f"field_order={video.get('field_order') or 'unknown'}，母版要求 progressive"})
        bitrate = int(video.get("bit_rate") or (data.get("format") or {}).get("bit_rate") or 0)
        if bitrate and bitrate < int(tech.get("min_bitrate_warn") or 0):
            findings.append({"severity": "warn", "code": "bitrate_low",
                             "msg": f"实测 bitrate={bitrate}bps，低于内部/已登记平台快筛线"})
    for spec in constraints:
        platform = str(spec.get("placement_key") or (
            f"{spec.get('platform')}:{spec.get('placement')}" if spec.get("placement") else spec.get("platform")
        ) or spec.get("platform_key") or "platform")
        allowed = spec.get("allowed_aspects") or []
        if allowed and item.get("aspect") not in allowed:
            findings.append({"severity": "block", "code": "platform_aspect_mismatch",
                             "msg": f"{platform} 当前规格不含交付比例 {item.get('aspect')}"})
        minimum = (spec.get("min_resolution_by_aspect") or {}).get(item.get("aspect"))
        if not minimum and item.get("aspect") == spec.get("aspect"):
            minimum = spec.get("min_resolution")
        min_w, min_h = resolution(minimum)
        if min_w and min_h and (width < min_w or height < min_h):
            findings.append({"severity": "block", "code": "platform_resolution_below_minimum",
                             "msg": f"{platform} 实测 {width}x{height}，低于当前登记最低 {min_w}x{min_h}"})
        min_bitrate = int(spec.get("min_bitrate_bps") or 0)
        bitrate = int(video.get("bit_rate") or (data.get("format") or {}).get("bit_rate") or 0)
        if min_bitrate and bitrate and bitrate < min_bitrate:
            findings.append({"severity": "warn", "code": "platform_bitrate_below_minimum",
                             "msg": f"{platform} 实测 bitrate={bitrate}bps，低于当前登记最低 {min_bitrate}bps"})
        max_mb = float(spec.get("max_file_size_mb") or 0)
        if max_mb and path.is_file() and path.stat().st_size > max_mb * 1024 * 1024:
            findings.append({"severity": "block", "code": "platform_file_too_large",
                             "msg": f"{platform} 文件超过当前登记上限 {max_mb:g}MB"})
        min_duration = float(spec.get("min_duration_seconds") or 0)
        max_duration = float(spec.get("max_duration_seconds") or 0)
        if min_duration and actual + 0.05 < min_duration:
            findings.append({"severity": "block", "code": "placement_duration_below_minimum",
                             "msg": f"{platform} 实测 {actual:.2f}s，低于当前登记最低 {min_duration:g}s"})
        if max_duration and actual - 0.05 > max_duration:
            findings.append({"severity": "block", "code": "placement_duration_above_maximum",
                             "msg": f"{platform} 实测 {actual:.2f}s，超过当前登记上限 {max_duration:g}s"})
        eligible = float(spec.get("in_stream_eligible_min_duration_seconds") or 0)
        if eligible and actual + 0.05 < eligible:
            findings.append({"severity": "warn", "code": "placement_in_stream_ineligible",
                             "msg": f"{platform} 实测 {actual:.2f}s；低于 {eligible:g}s 时不具备当前登记的 in-stream 展示资格"})
    return {
        "deliverable_id": item["deliverable_id"], "path": item["expected_path"],
        "duration_seconds": actual, "width": width, "height": height, "fps": fps,
        "has_audio": bool(audio), "loudness": loudness,
        "color": {key: video.get(key) for key in
                  ("color_primaries", "color_transfer", "color_space", "color_range", "field_order")},
        "passed": not any(f["severity"] == "block" for f in findings),
        "findings": findings,
    }


def build_report(root: Path, plan: dict):
    items = [inspect_item(root, item) for item in plan.get("deliverables") or [] if item.get("exists")]
    findings = [dict(f, deliverable_id=item["deliverable_id"]) for item in items for f in item["findings"]]
    return {
        "schema_version": 1, "kind": "ad_delivery_qc", "items": items,
        "summary": {
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "passed": sum(1 for item in items if item["passed"]),
        },
        "findings": findings,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--plan", default=None)
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    plan_path = Path(ns.plan) if ns.plan else root / "合成" / "delivery_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    report = build_report(root, plan)
    out = root / "合成" / "delivery_qc.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# delivery QC block={report['summary']['block']} passed={report['summary']['passed']}")
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
