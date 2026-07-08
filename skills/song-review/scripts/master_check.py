#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic master/delivery check for song.wav.

This is not a replacement for a real LUFS meter. With the standard library we
can still catch release-blocking issues: unreadable wav, silence, clipping,
sample rate/bit depth/channel problems, excessive edge silence, duration drift,
and low RMS proxy loudness.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import os
import wave
from datetime import date
from typing import Any


KIND = "song_master_check"
BLOCK = "blocking"
WARN = "warning"
INFO = "info"

PLATFORM_THRESHOLDS = {
    "demo": {"min_rate": 44100, "min_bits": 16, "max_peak_dbfs": -0.1, "edge_silence": 4.0},
    "streaming": {"min_rate": 44100, "min_bits": 16, "max_peak_dbfs": -0.5, "edge_silence": 2.5},
    "short_video": {"min_rate": 44100, "min_bits": 16, "max_peak_dbfs": -0.5, "edge_silence": 1.5},
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


def read_wav_metrics(path: str) -> dict[str, Any]:
    with wave.open(path, "rb") as w:
        channels = w.getnchannels()
        sample_width = w.getsampwidth()
        rate = w.getframerate()
        frames = w.getnframes()
        raw = w.readframes(frames)
    duration = frames / float(rate) if rate else 0.0
    bits = sample_width * 8
    metrics: dict[str, Any] = {
        "path": path,
        "duration_seconds": duration,
        "sample_rate": rate,
        "channels": channels,
        "bit_depth": bits,
        "sample_width_bytes": sample_width,
        "frames": frames,
    }
    if sample_width != 2 or not raw:
        metrics.update({
            "peak_dbfs": None,
            "rms_dbfs_proxy": None,
            "clipping_ratio": None,
            "head_silence_seconds": None,
            "tail_silence_seconds": None,
            "analysis_note": "amplitude analysis only supports 16-bit PCM wav",
        })
        return metrics
    samples = array.array("h")
    samples.frombytes(raw)
    if not samples:
        return metrics
    max_abs = max(abs(x) for x in samples)
    full = 32767.0
    peak = max_abs / full
    rms = math.sqrt(sum((x / full) ** 2 for x in samples) / len(samples))
    clip_count = sum(1 for x in samples if abs(x) >= int(full * 0.995))
    frame_abs = []
    for i in range(0, len(samples), channels):
        frame_abs.append(max(abs(x) for x in samples[i:i + channels]) / full)
    silence_threshold = 10 ** (-45 / 20)
    head = 0
    for value in frame_abs:
        if value > silence_threshold:
            break
        head += 1
    tail = 0
    for value in reversed(frame_abs):
        if value > silence_threshold:
            break
        tail += 1
    metrics.update({
        "peak_dbfs": 20 * math.log10(peak) if peak > 0 else -999.0,
        "rms_dbfs_proxy": 20 * math.log10(rms) if rms > 0 else -999.0,
        "clipping_ratio": clip_count / len(samples),
        "head_silence_seconds": head / float(rate) if rate else 0.0,
        "tail_silence_seconds": tail / float(rate) if rate else 0.0,
    })
    return metrics


def check_metrics(root: str, metrics: dict[str, Any], platform: str) -> dict[str, Any]:
    thresholds = PLATFORM_THRESHOLDS.get(platform, PLATFORM_THRESHOLDS["streaming"])
    findings: list[dict[str, str]] = []

    def issue(issue_id: str, severity: str, message: str) -> None:
        findings.append({"id": issue_id, "severity": severity, "message": message, "path": "歌/song.wav"})

    if not metrics:
        issue("MASTER-MISSING", BLOCK, "缺少或无法读取 歌/song.wav。")
    else:
        if metrics.get("sample_rate", 0) < thresholds["min_rate"]:
            issue("MASTER-SAMPLE-RATE", WARN, f"采样率 {metrics.get('sample_rate')}Hz 低于 {thresholds['min_rate']}Hz。")
        if metrics.get("bit_depth", 0) < thresholds["min_bits"]:
            issue("MASTER-BIT-DEPTH", WARN, f"位深 {metrics.get('bit_depth')}bit 低于 {thresholds['min_bits']}bit。")
        if metrics.get("channels") not in {1, 2}:
            issue("MASTER-CHANNELS", WARN, f"声道数 {metrics.get('channels')} 不常见，交付前确认。")
        if metrics.get("duration_seconds", 0) < 30:
            issue("MASTER-DURATION-SHORT", WARN, "时长低于 30s，可能是片段而非完整成品。")
        peak = metrics.get("peak_dbfs")
        if peak is not None:
            if peak <= -90:
                issue("MASTER-SILENCE", BLOCK, "音频近似全静音。")
            if peak > thresholds["max_peak_dbfs"]:
                issue("MASTER-PEAK", WARN, f"峰值 {peak:.2f}dBFS，高于建议上限 {thresholds['max_peak_dbfs']}dBFS。")
        clip = metrics.get("clipping_ratio")
        if clip is not None:
            if clip > 0.05:
                issue("MASTER-CLIPPING-BLOCK", BLOCK, f"削波样本占比 {clip*100:.2f}%，严重失真。")
            elif clip > 0.005:
                issue("MASTER-CLIPPING", WARN, f"削波样本占比 {clip*100:.2f}%。")
        rms = metrics.get("rms_dbfs_proxy")
        if rms is not None and -90 < rms < -30:
            issue("MASTER-RMS-LOW", WARN, f"RMS 代理响度 {rms:.1f}dBFS 偏低；正式母带建议用 LUFS 工具复核。")
        for key, label in (("head_silence_seconds", "开头"), ("tail_silence_seconds", "结尾")):
            value = metrics.get(key)
            if value is not None and value > thresholds["edge_silence"]:
                issue("MASTER-EDGE-SILENCE", WARN, f"{label}静音 {value:.1f}s，超过 {thresholds['edge_silence']}s。")
    target = load_json(os.path.join(root, "_meta.json"), {}) or {}
    target_duration = target.get("target_duration_seconds")
    if target_duration and metrics.get("duration_seconds"):
        actual = float(metrics["duration_seconds"])
        expected = float(target_duration)
        if expected and (actual < expected * 0.75 or actual > expected * 1.25):
            issue("MASTER-TARGET-DURATION", WARN, f"时长 {actual:.1f}s 偏离目标 {expected:.1f}s 超过 25%。")
    blockers = [item for item in findings if item["severity"] == BLOCK]
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "platform_profile": platform,
        "passed": not blockers,
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "metrics": metrics,
        "findings": findings,
        "lufs_note": "本脚本只用 RMS/peak 代理；正式发行母带建议用 LUFS/true-peak 专用工具复核。",
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") or {}
    lines = [
        "# Master Check",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- profile：{report.get('platform_profile')}",
        f"- passed：{report.get('passed')}",
        f"- 时长：{metrics.get('duration_seconds', 0):.1f}s" if metrics.get("duration_seconds") else "- 时长：未知",
        f"- 采样率/位深/声道：{metrics.get('sample_rate')}Hz / {metrics.get('bit_depth')}bit / {metrics.get('channels')}",
        f"- peak：{metrics.get('peak_dbfs') if metrics.get('peak_dbfs') is not None else 'n/a'} dBFS",
        f"- RMS proxy：{metrics.get('rms_dbfs_proxy') if metrics.get('rms_dbfs_proxy') is not None else 'n/a'} dBFS",
        "",
        "> " + report.get("lufs_note", ""),
    ]
    if report.get("findings"):
        lines.extend(["", "## Findings", ""])
        for item in report["findings"]:
            lines.append(f"- [{item['severity']}] {item['id']}: {item['message']}")
    return "\n".join(lines).rstrip() + "\n"


def build_report(root: str, platform: str = "streaming") -> dict[str, Any]:
    path = os.path.join(root, "歌", "song.wav")
    metrics: dict[str, Any] = {}
    if os.path.exists(path):
        try:
            metrics = read_wav_metrics(path)
            metrics["path"] = "歌/song.wav"
        except (wave.Error, EOFError) as exc:
            metrics = {"path": "歌/song.wav", "error": str(exc)}
    return check_metrics(root, metrics, platform)


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "混音")
    json_path = os.path.join(out_dir, "master_check.json")
    md_path = os.path.join(out_dir, "master_check.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="检查 song.wav 的母带/交付基础质量")
    ap.add_argument("project_root")
    ap.add_argument("--platform", default="streaming", choices=sorted(PLATFORM_THRESHOLDS))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    report = build_report(root, args.platform)
    if args.write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] master check JSON → {json_path}")
        print(f"[ok] master check MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
