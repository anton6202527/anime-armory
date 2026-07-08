from __future__ import annotations

import json
from pathlib import Path

import script_supervisor_log as ssl


def _storyboard(root: Path, ep: str = "第1集") -> None:
    ep_dir = root / "脚本" / ep
    ep_dir.mkdir(parents=True)
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "continuity": {"transition": "cut", "eyeline": "A看B"}},
            {"id": "Clip_02", "continuity": {"transition": "match_cut", "eyeline": "B看门"}},
        ]
    }, ensure_ascii=False), encoding="utf-8")


def test_script_supervisor_log_blocks_missing_take(tmp_path: Path) -> None:
    _storyboard(tmp_path)
    video = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"fake mp4")

    report = ssl.check_log(tmp_path, "第1集", write_missing=True)

    assert report["status"] == "block"
    assert any(f["code"] == "clip_without_accepted_take" and f["clip_id"] == "Clip_02" for f in report["findings"])


def test_script_supervisor_log_passes_with_valid_accepted_takes(tmp_path: Path, monkeypatch) -> None:
    _storyboard(tmp_path)
    base = tmp_path / "出视频" / "第1集" / "视频"
    base.mkdir(parents=True)
    (base / "Clip_01.mp4").write_bytes(b"fake mp4")
    (base / "Clip_02.mp4").write_bytes(b"fake mp4")
    monkeypatch.setattr(ssl, "ffprobe_duration", lambda _path: 1.25)

    report = ssl.check_log(tmp_path, "第1集", write_missing=True)

    assert report["status"] == "pass"
    assert (tmp_path / "生产数据" / "script_supervisor_log_第1集.jsonl").is_file()
    assert report["summary"]["accepted_clips"] == 2


def test_script_supervisor_log_blocks_unreadable_accepted_take(tmp_path: Path, monkeypatch) -> None:
    _storyboard(tmp_path)
    base = tmp_path / "出视频" / "第1集" / "视频"
    base.mkdir(parents=True)
    (base / "Clip_01.mp4").write_bytes(b"fake mp4")
    (base / "Clip_02.mp4").write_bytes(b"fake mp4")
    monkeypatch.setattr(ssl, "ffprobe_duration", lambda _path: None)

    report = ssl.check_log(tmp_path, "第1集", write_missing=True)

    assert report["status"] == "block"
    assert any(f["code"] == "accepted_take_media_invalid" for f in report["findings"])
