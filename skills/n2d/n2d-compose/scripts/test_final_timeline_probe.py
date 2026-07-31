from __future__ import annotations

import json
from pathlib import Path

import final_timeline_probe as ftp


def test_storyboard_segments_and_cuts() -> None:
    segments = ftp.storyboard_segments([
        {"id": "EP01_CLIP01", "duration": 2.5},
        {"id": "EP01_CLIP02", "duration": "3.0"},
    ])

    assert segments[0]["expected_start_sec"] == 0.0
    assert segments[1]["expected_start_sec"] == 2.5
    assert segments[1]["expected_end_sec"] == 5.5
    assert ftp.cut_rows(segments)[0]["cut"] == "Clip_01->Clip_02"


def test_write_report_creates_production_sidecar(tmp_path: Path) -> None:
    payload = {"kind": "n2d_final_timeline_probe", "episode": "第1集", "segments": []}

    rel = ftp.write_report(tmp_path, "第1集", payload)

    assert rel == "生产数据/final_timeline_probe_第1集.json"
    data = json.loads((tmp_path / rel).read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_final_timeline_probe"
