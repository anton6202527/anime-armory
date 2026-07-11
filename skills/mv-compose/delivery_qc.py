#!/usr/bin/env python3
"""Technical QC for the mezzanine master and SDR delivery file."""
import argparse
import json
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CRAFT = os.path.abspath(os.path.join(HERE, "..", "mv-craft", "scripts"))
if CRAFT not in sys.path:
    sys.path.insert(0, CRAFT)
import mv_utils


def probe(path):
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                          capture_output=True, text=True)
    return json.loads(proc.stdout) if proc.returncode == 0 else {}


def loudness(path):
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
                           "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True)
    match = None
    for candidate in reversed(proc.stderr.split("{", 1)):
        if "input_i" in candidate:
            match = "{" + candidate
            break
    if not match:
        return {}
    try:
        return json.loads(match[match.index("{"):match.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return {}


def signal_scan(path):
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
                           "-vf", "blackdetect=d=0.5:pix_th=0.02,freezedetect=n=-50dB:d=2", "-an", "-f", "null", "-"],
                          capture_output=True, text=True)
    return {"black_segments": proc.stderr.count("black_start:"), "freeze_segments": proc.stderr.count("freeze_start:")}


def inspect_delivery(path, master=False):
    data = probe(path)
    streams = data.get("streams") or []
    video = next((x for x in streams if x.get("codec_type") == "video"), {})
    audio = next((x for x in streams if x.get("codec_type") == "audio"), {})
    blocks, warnings = [], []
    if not video:
        blocks.append("missing_video_stream")
    if not audio:
        blocks.append("missing_audio_stream")
    if master:
        if video.get("codec_name") not in {"prores", "dnxhd"}:
            warnings.append("master_not_mezzanine_codec")
        if audio and not str(audio.get("codec_name", "")).startswith("pcm_"):
            warnings.append("master_audio_not_pcm")
    else:
        if video.get("codec_name") != "h264": blocks.append("delivery_video_not_h264")
        if video.get("pix_fmt") != "yuv420p": blocks.append("delivery_not_420_8bit")
        if video.get("color_primaries") != "bt709": blocks.append("color_primaries_not_bt709")
        if video.get("color_transfer") != "bt709": blocks.append("color_transfer_not_bt709")
        if video.get("color_space") != "bt709": blocks.append("color_matrix_not_bt709")
        if audio.get("sample_rate") != "48000": blocks.append("audio_not_48khz")
    loud = loudness(path)
    try:
        if float(loud.get("input_tp")) > -1.0:
            warnings.append("true_peak_above_minus_1dbtp")
    except (TypeError, ValueError):
        warnings.append("loudness_scan_unavailable")
    scan = signal_scan(path)
    if scan["black_segments"]: warnings.append("black_segment_review")
    if scan["freeze_segments"]: warnings.append("freeze_segment_review")
    return {"path": path, "probe": {"format": data.get("format"), "video": video, "audio": audio},
            "loudness": loud, "signal_scan": scan, "blocks": blocks, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("delivery")
    parser.add_argument("--master")
    args = parser.parse_args()
    root = os.path.abspath(args.project_root)
    rows = [inspect_delivery(args.delivery)]
    if args.master:
        rows.append(inspect_delivery(args.master, master=True))
    blocks = sum(len(row["blocks"]) for row in rows)
    warnings = sum(len(row["warnings"]) for row in rows)
    report = {"schema_version": 1, "kind": "mv_delivery_qc", "generated_at": date.today().isoformat(),
              "summary": {"hard_blocks": blocks, "warnings": warnings,
                          "verdict": "block" if blocks else ("review" if warnings else "ok")},
              "files": rows,
              "inputs_sha256": {mv_utils.relpath(root, row["path"]): mv_utils.content_hash(row["path"]) for row in rows}}
    out = os.path.join(root, "生产数据", "delivery_qc", "delivery_qc.json")
    mv_utils.write_json(out, report)
    print(f"[ok] delivery QC → {out} ({report['summary']['verdict']})")
    return 1 if blocks else 0


if __name__ == "__main__":
    raise SystemExit(main())
