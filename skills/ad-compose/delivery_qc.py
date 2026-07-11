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


def probe(path: Path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.is_file():
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
    proc = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                          capture_output=True, text=True)
    if proc.returncode:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
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
    actual = seconds((data.get("format") or {}).get("duration"))
    expected = seconds(item.get("duration"))
    tol = max(0.25, expected * 0.03) if expected else 0.5
    if expected and abs(actual - expected) > tol:
        findings.append({"severity": "block", "code": "duration_mismatch",
                         "msg": f"实测 {actual:.3f}s 与交付目标 {expected:.3f}s 偏差超过 {tol:.3f}s"})
    if not audio:
        findings.append({"severity": "block", "code": "audio_missing", "msg": "正式广告交付件无音轨"})
        loudness = None
    else:
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
    return {
        "deliverable_id": item["deliverable_id"], "path": item["expected_path"],
        "duration_seconds": actual, "width": width, "height": height,
        "has_audio": bool(audio), "loudness": loudness,
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
