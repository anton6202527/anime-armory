#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure a song master with ITU-R BS.1770-compatible ffmpeg meters."""
from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import wave
from datetime import date
from typing import Any


KIND = "song_master_check"
BLOCK, WARN, INFO = "blocking", "warning", "info"
PLATFORM_THRESHOLDS = {
    "demo": {"min_rate": 44100, "min_bits": 16, "edge_silence": 4.0},
    "streaming": {"min_rate": 44100, "min_bits": 16, "edge_silence": 2.5},
    "short_video": {"min_rate": 44100, "min_bits": 16, "edge_silence": 1.5},
    "archive": {"min_rate": 44100, "min_bits": 24, "edge_silence": 2.5},
    "apple_digital_masters": {"min_rate": 44100, "min_bits": 24, "edge_silence": 2.5},
}


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_wav_metrics(path: str) -> dict[str, Any]:
    with wave.open(path, "rb") as w:
        channels, sample_width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(frames)
    metrics: dict[str, Any] = {
        "duration_seconds": frames / float(rate) if rate else 0.0,
        "sample_rate": rate,
        "channels": channels,
        "bit_depth": sample_width * 8,
        "sample_width_bytes": sample_width,
    }
    if sample_width != 2 or not raw:
        metrics.update({"sample_peak_dbfs": None, "rms_dbfs_proxy": None, "clipping_ratio": None,
                        "head_silence_seconds": None, "tail_silence_seconds": None})
        return metrics
    samples = array.array("h")
    samples.frombytes(raw)
    full = 32767.0
    peak = max(abs(value) for value in samples) / full if samples else 0
    rms = math.sqrt(sum((value / full) ** 2 for value in samples) / len(samples)) if samples else 0
    clip_count = sum(1 for value in samples if abs(value) >= int(full * 0.995))
    frame_abs = [max(abs(value) for value in samples[i:i + channels]) / full for i in range(0, len(samples), channels)]
    silence_threshold = 10 ** (-45 / 20)
    head = next((i for i, value in enumerate(frame_abs) if value > silence_threshold), len(frame_abs))
    tail = next((i for i, value in enumerate(reversed(frame_abs)) if value > silence_threshold), len(frame_abs))
    metrics.update({
        "sample_peak_dbfs": 20 * math.log10(peak) if peak else -999.0,
        "rms_dbfs_proxy": 20 * math.log10(rms) if rms else -999.0,
        "clipping_ratio": clip_count / len(samples) if samples else 0,
        "head_silence_seconds": head / float(rate) if rate else 0,
        "tail_silence_seconds": tail / float(rate) if rate else 0,
    })
    return metrics


def probe_audio_metrics(path: str) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise wave.Error("WAV requires ffprobe but ffprobe was not found")
    proc = subprocess.run([
        ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries",
        "stream=sample_rate,channels,bits_per_raw_sample,bits_per_sample,sample_fmt,duration",
        "-of", "json", path,
    ], capture_output=True, text=True, check=True)
    stream = (json.loads(proc.stdout).get("streams") or [{}])[0]
    bits = int(stream.get("bits_per_raw_sample") or stream.get("bits_per_sample") or 0)
    return {
        "duration_seconds": float(stream.get("duration") or 0),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "bit_depth": bits,
        "sample_fmt": stream.get("sample_fmt"),
        "sample_peak_dbfs": None,
        "rms_dbfs_proxy": None,
        "clipping_ratio": None,
        "head_silence_seconds": None,
        "tail_silence_seconds": None,
    }


def read_audio_metrics(path: str) -> dict[str, Any]:
    try:
        return read_wav_metrics(path)
    except wave.Error:
        return probe_audio_metrics(path)


def measure_bs1770(path: str) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"complete": False, "error": "ffmpeg_not_found"}
    proc = subprocess.run([
        ffmpeg, "-hide_banner", "-nostats", "-i", path, "-af",
        "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-",
    ], capture_output=True, text=True)
    matches = re.findall(r"\{\s*\"input_i\".*?\}", proc.stderr, flags=re.S)
    if proc.returncode or not matches:
        return {"complete": False, "error": proc.stderr[-1200:]}
    raw = json.loads(matches[-1])
    def number(key: str) -> float | None:
        try:
            value = float(raw[key])
            return value if math.isfinite(value) else None
        except (KeyError, TypeError, ValueError):
            return None
    integrated, true_peak = number("input_i"), number("input_tp")
    return {
        "complete": integrated is not None and true_peak is not None,
        "standard": "ITU-R BS.1770 (ffmpeg loudnorm analysis)",
        "integrated_lufs": integrated,
        "true_peak_dbtp": true_peak,
        "loudness_range_lu": number("input_lra"),
        "threshold_lufs": number("input_thresh"),
    }


def check_metrics(root: str, metrics: dict[str, Any], platform: str) -> dict[str, Any]:
    thresholds = PLATFORM_THRESHOLDS[platform]
    findings: list[dict[str, str]] = []
    relpath = str(metrics.get("path") or "歌/song.wav")
    def issue(issue_id: str, severity: str, message: str) -> None:
        findings.append({"id": issue_id, "severity": severity, "message": message, "path": relpath})

    if not metrics or metrics.get("error"):
        issue("MASTER-MISSING", BLOCK, "缺少或无法读取母版 WAV。")
    else:
        if metrics.get("sample_rate", 0) < thresholds["min_rate"]:
            issue("MASTER-SAMPLE-RATE", BLOCK, f"采样率低于 {thresholds['min_rate']}Hz。")
        if metrics.get("bit_depth", 0) < thresholds["min_bits"]:
            severity = BLOCK if platform in {"archive", "apple_digital_masters"} else WARN
            issue("MASTER-BIT-DEPTH", severity, f"位深低于 {thresholds['min_bits']}bit。")
        if metrics.get("channels") not in {1, 2}:
            issue("MASTER-CHANNELS", WARN, f"声道数 {metrics.get('channels')} 不常见，交付前确认。")
        peak = metrics.get("sample_peak_dbfs")
        if peak is not None and peak <= -90:
            issue("MASTER-SILENCE", BLOCK, "音频近似全静音。")
        clip = metrics.get("clipping_ratio")
        if clip is not None and clip > 0.05:
            issue("MASTER-CLIPPING-BLOCK", BLOCK, f"削波样本占比 {clip*100:.2f}%，严重失真。")
        elif clip is not None and clip > 0.005:
            issue("MASTER-CLIPPING", WARN, f"削波样本占比 {clip*100:.2f}%。")
        meter = metrics.get("bs1770") or {}
        if not meter.get("complete"):
            issue("MASTER-METER-INCOMPLETE", BLOCK, "未取得 ITU-R BS.1770 响度/true-peak 测量。")
        else:
            lufs, true_peak = meter.get("integrated_lufs"), meter.get("true_peak_dbtp")
            if true_peak is not None and true_peak > 0:
                issue("MASTER-TRUE-PEAK-CLIP", BLOCK, f"true peak {true_peak:.2f} dBTP 超过 0。")
            spotify_limit = -2.0 if lufs is not None and lufs > -14 else -1.0
            if platform in {"streaming", "short_video"} and true_peak is not None and true_peak > spotify_limit:
                issue("MASTER-TRUE-PEAK-HEADROOM", WARN, f"true peak {true_peak:.2f} dBTP；流媒体编码建议不高于 {spotify_limit:.1f} dBTP。")
            if lufs is not None and (lufs < -24 or lufs > -7):
                issue("MASTER-LOUDNESS-OUTLIER", WARN, f"integrated loudness {lufs:.1f} LUFS 属异常区间；请按作品动态与发行语境复核，不自动压到 -14。")
        for key, label in (("head_silence_seconds", "开头"), ("tail_silence_seconds", "结尾")):
            value = metrics.get(key)
            if value is not None and value > thresholds["edge_silence"]:
                issue("MASTER-EDGE-SILENCE", WARN, f"{label}静音 {value:.1f}s，超过 {thresholds['edge_silence']}s。")
    target = load_json(os.path.join(root, "_meta.json"), {}) or {}
    target_duration = target.get("target_duration_seconds")
    if target_duration and metrics.get("duration_seconds"):
        actual, expected = float(metrics["duration_seconds"]), float(target_duration)
        if expected and (actual < expected * 0.75 or actual > expected * 1.25):
            issue("MASTER-TARGET-DURATION", WARN, f"时长 {actual:.1f}s 偏离目标 {expected:.1f}s 超过 25%。")
    blockers = [item for item in findings if item["severity"] == BLOCK]
    return {
        "schema_version": 2,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "platform_profile": platform,
        "passed": not blockers,
        "measurement_complete": bool((metrics.get("bs1770") or {}).get("complete")),
        "blocking": len(blockers),
        "warnings": sum(item["severity"] == WARN for item in findings),
        "metrics": metrics,
        "findings": findings,
        "standard_note": "响度与 true peak 按 ITU-R BS.1770 测量；-14 LUFS 仅作流媒体归一化参考，不是统一母带硬目标。",
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics, meter = report.get("metrics") or {}, (report.get("metrics") or {}).get("bs1770") or {}
    lines = [
        "# Master Check", "", f"- 生成日期：{report.get('generated_at')}",
        f"- profile：{report.get('platform_profile')}", f"- passed：{report.get('passed')}",
        f"- source：{metrics.get('path')} sha256={metrics.get('sha256', '')}",
        f"- 时长：{metrics.get('duration_seconds', 0):.1f}s" if metrics.get("duration_seconds") else "- 时长：未知",
        f"- 采样率/位深/声道：{metrics.get('sample_rate')}Hz / {metrics.get('bit_depth')}bit / {metrics.get('channels')}",
        f"- integrated：{meter.get('integrated_lufs')} LUFS",
        f"- true peak：{meter.get('true_peak_dbtp')} dBTP",
        f"- LRA：{meter.get('loudness_range_lu')} LU", "", "> " + report.get("standard_note", ""),
    ]
    if report.get("findings"):
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- [{item['severity']}] {item['id']}: {item['message']}" for item in report["findings"])
    return "\n".join(lines).rstrip() + "\n"


def master_path(root: str, explicit: str = "") -> tuple[str, str]:
    if explicit:
        path = os.path.abspath(explicit)
        return path, os.path.relpath(path, root).replace(os.sep, "/")
    for relpath in ("导出/master.wav", "歌/song.wav"):
        path = os.path.join(root, relpath)
        if os.path.exists(path):
            return path, relpath
    return os.path.join(root, "导出", "master.wav"), "导出/master.wav"


def build_report(root: str, platform: str = "streaming", audio_path: str = "") -> dict[str, Any]:
    path, relpath = master_path(root, audio_path)
    metrics: dict[str, Any] = {}
    if os.path.exists(path):
        try:
            metrics = read_audio_metrics(path)
            metrics.update({"path": relpath, "sha256": sha256_file(path), "bs1770": measure_bs1770(path)})
        except (wave.Error, EOFError, OSError) as exc:
            metrics = {"path": relpath, "error": str(exc)}
    return check_metrics(root, metrics, platform)


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "混音")
    json_path, md_path = os.path.join(out_dir, "master_check.json"), os.path.join(out_dir, "master_check.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="以 BS.1770 检查歌曲母版与交付质量")
    ap.add_argument("project_root")
    ap.add_argument("--platform", default="streaming", choices=sorted(PLATFORM_THRESHOLDS))
    ap.add_argument("--audio", default="", help="显式指定待测 WAV；默认优先 导出/master.wav")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    report = build_report(root, args.platform, args.audio)
    if args.write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] master check JSON -> {json_path}")
        print(f"[ok] master check MD   -> {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
