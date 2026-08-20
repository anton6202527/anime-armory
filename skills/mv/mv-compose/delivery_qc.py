#!/usr/bin/env python3
"""Technical QC for the mezzanine master and SDR delivery file."""
import argparse
import array
import json
import math
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CRAFT = os.path.abspath(os.path.join(HERE, "..", "mv-craft", "scripts"))
if CRAFT not in sys.path:
    sys.path.insert(0, CRAFT)
import mv_utils


AUDIO_IDENTITY_KIND = "mv_delivery_audio_identity"
AUDIO_IDENTITY_SCHEMA_VERSION = 1
AUDIO_IDENTITY_CONTRACT = "decoded_pcm_start_middle_end_correlation_v2"
AUDIO_IDENTITY_THRESHOLDS = {
    "minimum_correlation": 0.85,
    "maximum_abs_offset_ms": 50.0,
    "maximum_drift_ms": 30.0,
    "maximum_duration_delta_seconds": 0.10,
}
AUDIO_OUTPUT_ROLES = ("final", "master")


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


def _decode_pcm(path, sample_rate=8000):
    proc = subprocess.run([
        "ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-f", "f32le", "-",
    ], capture_output=True)
    if proc.returncode or not proc.stdout:
        return []
    values = array.array("f")
    values.frombytes(proc.stdout)
    if sys.byteorder != "little":
        values.byteswap()
    return list(values)


def _correlation(left, right):
    count = min(len(left), len(right))
    if count < 64:
        return None
    left, right = left[:count], right[:count]
    lm, rm = sum(left) / count, sum(right) / count
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    ld = math.sqrt(sum((a - lm) ** 2 for a in left))
    rd = math.sqrt(sum((b - rm) ** 2 for b in right))
    if ld < 1e-9 or rd < 1e-9:
        return None
    return numerator / (ld * rd)


def audio_identity(source, output, sample_rate=8000):
    """Compare decoded PCM at start/middle/end, including offset and drift."""
    src, dst = _decode_pcm(source, sample_rate), _decode_pcm(output, sample_rate)
    source_duration = round(len(src) / sample_rate, 6) if src else None
    output_duration = round(len(dst) / sample_rate, 6) if dst else None
    duration_delta = (
        round(output_duration - source_duration, 6)
        if source_duration is not None and output_duration is not None else None
    )
    base = {
        "contract": AUDIO_IDENTITY_CONTRACT,
        "sample_rate_hz": sample_rate,
        "thresholds": dict(AUDIO_IDENTITY_THRESHOLDS),
        "source_duration_seconds": source_duration,
        "output_duration_seconds": output_duration,
        "duration_delta_seconds": duration_delta,
    }
    if not src or not dst:
        return {**base, "status": "unavailable", "anchors": []}
    maximum_shift = round(
        sample_rate * AUDIO_IDENTITY_THRESHOLDS["maximum_abs_offset_ms"] / 1000.0
    )
    common_samples = min(len(src), len(dst))
    window = min(sample_rate * 2, common_samples - (2 * maximum_shift))
    if window < sample_rate // 2:
        return {**base, "status": "too_short", "anchors": []}
    positions = (
        ("start", maximum_shift),
        ("middle", (common_samples - window) // 2),
        ("end", common_samples - window - maximum_shift),
    )
    anchors = []
    for label, source_start in positions:
        output_start = source_start
        source_window = src[source_start:source_start + window:8]
        best = (None, 0)
        for shift in range(-maximum_shift, maximum_shift + 1, 8):
            shifted = output_start + shift
            if shifted < 0 or shifted + window > len(dst):
                continue
            score = _correlation(source_window, dst[shifted:shifted + window:8])
            if score is not None and (best[0] is None or score > best[0]):
                best = (score, shift)
        anchors.append({"anchor": label, "correlation": round(best[0], 5) if best[0] is not None else None,
                        "offset_ms": round(best[1] * 1000.0 / sample_rate, 3)})
    valid = [row for row in anchors if row["correlation"] is not None]
    if len(valid) != len(anchors):
        return {**base, "status": "unverifiable", "anchors": anchors}
    correlations = [row["correlation"] for row in valid]
    offsets = [row["offset_ms"] for row in valid]
    minimum_correlation = min(correlations)
    maximum_abs_offset = max(abs(value) for value in offsets)
    drift = round(max(offsets) - min(offsets), 3)
    duration_ok = (
        duration_delta is not None
        and abs(duration_delta) <= AUDIO_IDENTITY_THRESHOLDS["maximum_duration_delta_seconds"]
    )
    return {
        **base,
        "status": "ok" if (
            minimum_correlation >= AUDIO_IDENTITY_THRESHOLDS["minimum_correlation"]
            and maximum_abs_offset <= AUDIO_IDENTITY_THRESHOLDS["maximum_abs_offset_ms"]
            and drift <= AUDIO_IDENTITY_THRESHOLDS["maximum_drift_ms"]
            and duration_ok
        ) else "mismatch",
        "anchors": anchors,
        "min_correlation": minimum_correlation,
        "max_abs_offset_ms": maximum_abs_offset,
        "drift_ms": drift,
    }


def build_audio_identity_ledger(root, source, outputs, sample_rate=8000):
    """Bind independent PCM comparisons for both required delivery outputs."""
    source_rel = mv_utils.relpath(root, source) if source else ""
    source_sha = mv_utils.content_hash(source) if source else ""
    records = {}
    for role in AUDIO_OUTPUT_ROLES:
        path = outputs.get(role)
        if not source:
            result = {
                "contract": AUDIO_IDENTITY_CONTRACT,
                "sample_rate_hz": sample_rate,
                "thresholds": dict(AUDIO_IDENTITY_THRESHOLDS),
                "status": "missing_source",
                "source_duration_seconds": None,
                "output_duration_seconds": None,
                "duration_delta_seconds": None,
                "anchors": [],
            }
        elif not path:
            result = {
                "contract": AUDIO_IDENTITY_CONTRACT,
                "sample_rate_hz": sample_rate,
                "thresholds": dict(AUDIO_IDENTITY_THRESHOLDS),
                "status": "missing_output",
                "source_duration_seconds": None,
                "output_duration_seconds": None,
                "duration_delta_seconds": None,
                "anchors": [],
            }
        else:
            result = audio_identity(source, path, sample_rate=sample_rate)
        records[role] = {
            "role": role,
            "path": mv_utils.relpath(root, path) if path else "",
            "sha256": mv_utils.content_hash(path) if path else "",
            **result,
        }
    return {
        "schema_version": AUDIO_IDENTITY_SCHEMA_VERSION,
        "kind": AUDIO_IDENTITY_KIND,
        "contract": AUDIO_IDENTITY_CONTRACT,
        "source": {"path": source_rel, "sha256": source_sha},
        "required_roles": list(AUDIO_OUTPUT_ROLES),
        "outputs": records,
        "status": "ok" if source_sha and all(
            records[role].get("status") == "ok" for role in AUDIO_OUTPUT_ROLES
        ) else "block",
    }


def inspect_delivery(path, master=False, song_duration=None, source_loudness=None, expected_dimensions=None):
    data = probe(path)
    streams = data.get("streams") or []
    video = next((x for x in streams if x.get("codec_type") == "video"), {})
    audio = next((x for x in streams if x.get("codec_type") == "audio"), {})
    blocks, warnings = [], []
    if not video:
        blocks.append("missing_video_stream")
    if not audio:
        blocks.append("missing_audio_stream")
    if expected_dimensions and video:
        expected_width, expected_height = expected_dimensions
        if int(video.get("width") or 0) != expected_width or int(video.get("height") or 0) != expected_height:
            blocks.append(f"dimensions_not_expected_{expected_width}x{expected_height}")
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
    delivery = os.path.abspath(args.delivery if os.path.isabs(args.delivery) else os.path.join(root, args.delivery))
    master = (
        os.path.abspath(args.master if os.path.isabs(args.master) else os.path.join(root, args.master))
        if args.master else None
    )
    root_real = os.path.realpath(root)
    for label, path in (("delivery", delivery), ("master", master)):
        if not path:
            continue
        try:
            contained = os.path.commonpath((root_real, os.path.realpath(path))) == root_real
        except ValueError:
            contained = False
        if not contained:
            print(f"[err] {label} 必须位于作品根内：{path}", file=sys.stderr)
            return 2
    song = mv_utils.find_song(root)
    song_duration = mv_utils.audio_duration(song) if song else None
    source_loudness = loudness(song) if song else {}
    settings = mv_utils.parse_settings(root)
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    aspect = settings.get("合成画幅") or meta.get("aspect") or "16:9"
    expected_dimensions = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}.get(aspect)
    rows = [inspect_delivery(delivery, song_duration=song_duration, source_loudness=source_loudness,
                             expected_dimensions=expected_dimensions)]
    rows[0]["role"] = "final"
    if master:
        rows.append(inspect_delivery(master, master=True, song_duration=song_duration,
                                     source_loudness=source_loudness, expected_dimensions=expected_dimensions))
        rows[-1]["role"] = "master"
    if song and song_duration is None:
        rows[0]["blocks"].append("source_song_duration_scan_unavailable")
    if song and not source_loudness:
        rows[0]["blocks"].append("source_song_loudness_scan_unavailable")
    identity = build_audio_identity_ledger(
        root, song, {"final": delivery, "master": master},
    )
    rows_by_role = {row.get("role"): row for row in rows}
    for role in AUDIO_OUTPUT_ROLES:
        status = (identity.get("outputs") or {}).get(role, {}).get("status") or "missing"
        row = rows_by_role.get(role) or rows[0]
        if status != "ok":
            row["blocks"].append(f"audio_identity_{role}_{status}")
    blocks = sum(len(row["blocks"]) for row in rows)
    warnings = sum(len(row["warnings"]) for row in rows)
    output_paths = {"final": delivery, "master": master}
    for row in rows:
        output_path = output_paths[row["role"]]
        row["path"] = mv_utils.relpath(root, output_path)
        row["sha256"] = mv_utils.content_hash(output_path)
    report = {"schema_version": 3, "kind": "mv_delivery_qc", "generated_at": date.today().isoformat(),
              "audio_policy": "preserve_master_song_loudness; verify decoded PCM identity for final and master",
              "expected_delivery": {"aspect": aspect, "dimensions": expected_dimensions},
              "source_song": mv_utils.relpath(root, song) if song else "",
              "source_song_loudness": source_loudness,
              "audio_identity": identity,
              "summary": {"hard_blocks": blocks, "warnings": warnings,
                          "verdict": "block" if blocks else ("review" if warnings else "ok")},
              "files": rows,
              "inputs_sha256": {
                  row["path"]: mv_utils.content_hash(output_paths[row["role"]]) for row in rows
              }}
    if song:
        report["inputs_sha256"][mv_utils.relpath(root, song)] = mv_utils.content_hash(song)
    out = os.path.join(root, "生产数据", "delivery_qc", "delivery_qc.json")
    mv_utils.write_json(out, report)
    print(f"[ok] delivery QC → {out} ({report['summary']['verdict']})")
    return 1 if blocks else 0


if __name__ == "__main__":
    raise SystemExit(main())
