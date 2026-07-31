#!/usr/bin/env python3
"""Build an optional light J-cut voice track from per-line wav files.

Default n2d-compose uses the original voice_<lang>.wav track. This helper is
only for an explicit post pass: it shifts the whole voice track earlier by a
small fixed amount (a uniform "audio-leads" J-cut, not a per-cut early entry),
so speech lands slightly before the visual cut. Subtitles keep the original SRT
timing, so voice leads subtitles by up to this amount. Keep the value small and
avoid it for front-facing lip-sync shots.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 6:
        print("usage: build_jcut_voice.py <manifest.json> <voice_dir> <jcut_sec> <duration_sec> <out.wav>")
        return 2

    manifest_p = Path(sys.argv[1])
    voice_dir = Path(sys.argv[2])
    jcut = max(0.0, min(float(sys.argv[3]), 0.4))
    total_dur = float(sys.argv[4])
    out_p = Path(sys.argv[5])

    data = json.loads(manifest_p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print(f"manifest is not a list: {manifest_p}")
        return 1

    items = []
    for item in data:
        if not isinstance(item, dict):
            continue
        wav = item.get("line_wav")
        start = item.get("start")
        if not wav or start is None:
            continue
        wav_p = voice_dir / wav
        if not wav_p.exists():
            print(f"missing line wav: {wav_p}")
            return 1
        idx = int(item.get("idx", len(items)))
        start_f = float(start)
        if idx > 0:
            start_f = max(0.0, start_f - jcut)
        items.append((wav_p, start_f))

    if not items:
        print("no line wav entries found in manifest")
        return 1

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for wav_p, _ in items:
        cmd += ["-i", str(wav_p)]

    parts = []
    labels = []
    for i, (_, start_f) in enumerate(items):
        delay_ms = max(0, int(round(start_f * 1000)))
        label = f"a{i}"
        parts.append(
            f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms}[{label}]"
        )
        labels.append(f"[{label}]")

    filt = (
        ";".join(parts)
        + ";"
        + "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:normalize=0,"
        + f"atrim=0:{total_dur:.3f},apad=whole_dur={total_dur:.3f},"
        + "alimiter=limit=0.95[out]"
    )
    cmd += ["-filter_complex", filt, "-map", "[out]", "-t", f"{total_dur:.3f}", "-ar", "44100", "-ac", "2", str(out_p)]
    subprocess.check_call(cmd)
    print(f"built J-cut voice track: {out_p} (jcut={jcut:.3f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
