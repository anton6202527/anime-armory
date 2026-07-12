#!/usr/bin/env python3
"""Technical QC for ad VO line WAVs and stitched track."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def probe(path: Path):
    exe = shutil.which("ffprobe")
    if not exe or not path.is_file():
        return None
    proc = subprocess.run([exe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                          capture_output=True, text=True)
    if proc.returncode:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def volume(path: Path):
    exe = shutil.which("ffmpeg")
    if not exe or not path.is_file():
        return None
    proc = subprocess.run([exe, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                          capture_output=True, text=True)
    text = proc.stderr or ""
    mean = re.search(r"mean_volume:\s*(-?inf|-?\d+(?:\.\d+)?)\s*dB", text, re.I)
    peak = re.search(r"max_volume:\s*(-?inf|-?\d+(?:\.\d+)?)\s*dB", text, re.I)
    if not mean or not peak:
        return None
    def val(raw):
        return None if raw.lower() == "-inf" else float(raw)
    return {"mean_db": val(mean.group(1)), "max_db": val(peak.group(1))}


def seconds(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def inspect(root: Path):
    root = root.resolve()
    manifest_path = root / "配音" / "时长清单.json"
    manifest = load(manifest_path, {}) or {}
    findings = []
    items = []
    placeholder = bool(manifest.get("has_placeholder"))
    lines = manifest.get("lines") or []
    if not lines:
        findings.append({"severity": "block", "code": "voice_lines_missing", "msg": "时长清单没有 lines[]"})
    for pos, line in enumerate(lines, 1):
        rel = str(line.get("line_wav") or f"line_{pos:02d}.wav")
        path = root / rel
        if not path.is_file():
            path = root / "配音" / rel
        data = probe(path)
        row = {"idx": line.get("idx", pos), "path": str(path.relative_to(root)) if path.is_file() else rel}
        if not data:
            findings.append({"severity": "block", "code": "voice_audio_unreadable", "idx": pos,
                             "msg": f"逐句音频不存在或 ffprobe 不可读：{rel}"})
            items.append(row)
            continue
        stream = next((s for s in data.get("streams") or [] if s.get("codec_type") == "audio"), {})
        actual = seconds((data.get("format") or {}).get("duration") or stream.get("duration"))
        declared = seconds(line.get("seconds"))
        row.update({"actual_seconds": actual, "declared_seconds": declared,
                    "sample_rate": int(stream.get("sample_rate") or 0), "channels": int(stream.get("channels") or 0)})
        if actual <= 0.05:
            findings.append({"severity": "block", "code": "voice_duration_invalid", "idx": pos,
                             "msg": f"逐句音频无有效时长：{rel}"})
        elif declared and abs(actual - declared) > max(0.15, declared * 0.08):
            findings.append({"severity": "block", "code": "voice_duration_drift", "idx": pos,
                             "msg": f"{rel} 实测 {actual:.3f}s 与清单 {declared:.3f}s 不符"})
        if row["sample_rate"] and row["sample_rate"] != 48000:
            findings.append({"severity": "warn", "code": "voice_sample_rate_non_master", "idx": pos,
                             "msg": f"{rel} 为 {row['sample_rate']}Hz；合成将统一重采样 48kHz"})
        levels = volume(path)
        row["levels"] = levels
        if levels is None:
            findings.append({"severity": "block", "code": "voice_level_unmeasured", "idx": pos,
                             "msg": f"无法测量 {rel} 电平"})
        elif levels["mean_db"] is None and not placeholder:
            findings.append({"severity": "block", "code": "voice_line_silent", "idx": pos,
                             "msg": f"正式 VO {rel} 为全静音"})
        elif levels["max_db"] is not None and levels["max_db"] > -0.1:
            findings.append({"severity": "warn", "code": "voice_peak_near_full_scale", "idx": pos,
                             "msg": f"{rel} 峰值 {levels['max_db']:.2f}dBFS，需人工听检削波"})
        items.append(row)
    stitched = root / "配音" / "vo.wav"
    if not placeholder and not probe(stitched):
        findings.append({"severity": "block", "code": "stitched_voice_missing", "msg": "正式 VO 缺可读的 配音/vo.wav"})
    precision = "full" if shutil.which("ffmpeg") and shutil.which("ffprobe") else "structural"
    if precision != "full":
        findings.append({"severity": "block", "code": "voice_qc_precision", "msg": "缺 ffmpeg/ffprobe，不能完成正式 VO 技术验收"})
    return {
        "schema_version": 1, "kind": "ad_voice_qc", "items": items,
        "qc_environment": {"precision_level": precision},
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings)},
        "findings": findings,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="ad VO technical QC")
    ap.add_argument("project_root")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    payload = inspect(root)
    out = root / "配音" / "voice_qc.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# voice QC block={payload['summary']['block']} warn={payload['summary']['warn']}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
