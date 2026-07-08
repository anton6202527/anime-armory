#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import array
import math
import os
import tempfile
import wave

import master_check


def write_wav(path, *, seconds=1.0, rate=44100, kind="tone"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = array.array("h")
    for i in range(int(seconds * rate)):
        if kind == "silent":
            value = 0
        elif kind == "clip":
            value = 32767 if i % 2 == 0 else -32767
        else:
            value = int(12000 * math.sin(2 * math.pi * 220 * i / rate))
        data.extend([value, value])
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def test_master_check_passes_clean_wav():
    with tempfile.TemporaryDirectory() as root:
        write_wav(os.path.join(root, "歌", "song.wav"))
        report = master_check.build_report(root, "streaming")
        assert report["passed"]
        assert report["metrics"]["sample_rate"] == 44100


def test_master_check_blocks_silent_wav():
    with tempfile.TemporaryDirectory() as root:
        write_wav(os.path.join(root, "歌", "song.wav"), kind="silent")
        report = master_check.build_report(root, "streaming")
        assert not report["passed"]
        assert any(item["id"] == "MASTER-SILENCE" for item in report["findings"])
