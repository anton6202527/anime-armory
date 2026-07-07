from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("video_face_drift_watch.py")
spec = importlib.util.spec_from_file_location("video_face_drift_watch", SCRIPT)
watch = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(watch)


def test_sample_times_interval_and_cap() -> None:
    assert watch.sample_times(1.0, 2.0, 0.5, 20) == [1.0, 1.5, 2.0]

    capped = watch.sample_times(0.0, 10.0, 1.0, 4)

    assert capped == [0.0, 3.0, 7.0, 10.0]


def test_clip_for_time_uses_segment_boundaries() -> None:
    segments = [
        {"clip": "Clip_06", "start_sec": 67.563, "end_sec": 82.149},
        {"clip": "Clip_07", "start_sec": 82.149, "end_sec": 93.346},
    ]

    assert watch.clip_for_time(segments, 80.0) == "Clip_06"
    assert watch.clip_for_time(segments, 82.149) == "Clip_07"


def test_ep_label_normalizes_plain_number() -> None:
    assert watch.ep_label("1") == "第1集"
    assert watch.ep_label("第2集") == "第2集"
