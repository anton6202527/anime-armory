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


def _duration(data):
    try:
        return float((data.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        return None


def inspect_delivery(path, master=False, song_duration=None, source_loudness=None):
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
            blocks.append("master_not_mezzanine_codec")
        if video and video.get("pix_fmt") != "yuv422p10le":
            blocks.append("master_not_422_10bit")
        if audio and not str(audio.get("codec_name", "")).startswith("pcm_"):
            blocks.append("master_audio_not_pcm")
        if audio.get("sample_rate") != "48000":
            blocks.append("master_audio_not_48khz")
        if video.get("color_primaries") != "bt709": blocks.append("master_color_primaries_not_bt709")
        if video.get("color_transfer") != "bt709": blocks.append("master_color_transfer_not_bt709")
        if video.get("color_space") != "bt709": blocks.append("master_color_matrix_not_bt709")
    else:
        if video.get("codec_name") != "h264": blocks.append("delivery_video_not_h264")
        if "high" not in str(video.get("profile") or "").lower(): blocks.append("delivery_h264_profile_not_high")
        if video.get("pix_fmt") != "yuv420p": blocks.append("delivery_not_420_8bit")
        if video.get("color_primaries") != "bt709": blocks.append("color_primaries_not_bt709")
        if video.get("color_transfer") != "bt709": blocks.append("color_transfer_not_bt709")
        if video.get("color_space") != "bt709": blocks.append("color_matrix_not_bt709")
        if str(video.get("color_range") or "").lower() not in {"tv", "mpeg"}:
            blocks.append("color_range_not_limited")
        if str(video.get("field_order") or "progressive") not in {"progressive", "unknown"}:
            blocks.append("delivery_not_progressive")
        if audio.get("codec_name") != "aac": blocks.append("delivery_audio_not_aac")
        if audio.get("sample_rate") != "48000": blocks.append("audio_not_48khz")
        if audio and int(audio.get("channels") or 0) != 2:
            warnings.append("delivery_audio_not_stereo")
    loud = loudness(path)
    try:
        true_peak = float(loud.get("input_tp"))
        if true_peak > 0.0:
            blocks.append("true_peak_above_0dbtp")
        elif true_peak > -1.0:
            warnings.append("true_peak_above_minus_1dbtp")
    except (TypeError, ValueError):
        blocks.append("loudness_scan_unavailable")
    duration = _duration(data)
    if song_duration is not None and duration is not None and abs(duration - song_duration) > 0.10:
        blocks.append("duration_differs_from_master_song_over_100ms")
    if source_loudness:
        try:
            drift = abs(float(loud.get("input_i")) - float(source_loudness.get("input_i")))
            if drift > 0.5:
                blocks.append("integrated_loudness_changed_over_0_5lu")
        except (TypeError, ValueError):
            pass
    scan = signal_scan(path)
    if scan["black_segments"]: warnings.append("black_segment_review")
    if scan["freeze_segments"]: warnings.append("freeze_segment_review")
    return {"path": path, "duration": duration,
            "probe": {"format": data.get("format"), "video": video, "audio": audio},
            "loudness": loud, "signal_scan": scan, "blocks": blocks, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("delivery")
    parser.add_argument("--master")
    args = parser.parse_args()
    root = os.path.abspath(args.project_root)
    song = mv_utils.find_song(root)
    song_duration = mv_utils.audio_duration(song) if song else None
    source_loudness = loudness(song) if song else {}
    rows = [inspect_delivery(args.delivery, song_duration=song_duration, source_loudness=source_loudness)]
    if args.master:
        rows.append(inspect_delivery(args.master, master=True, song_duration=song_duration, source_loudness=source_loudness))
    if song and song_duration is None:
        rows[0]["blocks"].append("source_song_duration_scan_unavailable")
    if song and not source_loudness:
        rows[0]["blocks"].append("source_song_loudness_scan_unavailable")
    blocks = sum(len(row["blocks"]) for row in rows)
    warnings = sum(len(row["warnings"]) for row in rows)
    report = {"schema_version": 2, "kind": "mv_delivery_qc", "generated_at": date.today().isoformat(),
              "audio_policy": "preserve_master_song_loudness; no automatic loudness normalization",
              "source_song": mv_utils.relpath(root, song) if song else "",
              "source_song_loudness": source_loudness,
              "summary": {"hard_blocks": blocks, "warnings": warnings,
                          "verdict": "block" if blocks else ("review" if warnings else "ok")},
              "files": rows,
              "inputs_sha256": {mv_utils.relpath(root, row["path"]): mv_utils.content_hash(row["path"]) for row in rows}}
    if song:
        report["inputs_sha256"][mv_utils.relpath(root, song)] = mv_utils.content_hash(song)
    out = os.path.join(root, "生产数据", "delivery_qc", "delivery_qc.json")
    mv_utils.write_json(out, report)
    print(f"[ok] delivery QC → {out} ({report['summary']['verdict']})")
    return 1 if blocks else 0


if __name__ == "__main__":
    raise SystemExit(main())
