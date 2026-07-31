from __future__ import annotations

from pathlib import Path

import pytest

from compose_clip_resolver import resolve_clip_video


def test_required_lipsync_replaces_base_video(tmp_path: Path) -> None:
    base = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    final = tmp_path / "出视频" / "第1集" / "视频_lipsync" / "Clip_01_lipsync.mp4"
    base.parent.mkdir(parents=True)
    final.parent.mkdir(parents=True)
    base.write_bytes(b"base")
    final.write_bytes(b"lipsync")
    routes = {"Clip_01": {"audio_strategy": "base_video_then_post_lipsync", "post_lipsync_required": True}}

    path, source = resolve_clip_video(tmp_path, "第1集", "Clip_01", base, routes)

    assert path == final
    assert source == "post_lipsync"


def test_required_lipsync_never_silently_uses_base(tmp_path: Path) -> None:
    base = tmp_path / "Clip_01.mp4"
    base.write_bytes(b"base")
    routes = {"Clip_01": {"post_lipsync_required": True}}

    with pytest.raises(FileNotFoundError, match="neutral-mouth base plate"):
        resolve_clip_video(tmp_path, "第1集", "Clip_01", base, routes)


def test_explicit_preview_waiver_can_use_base(tmp_path: Path) -> None:
    base = tmp_path / "Clip_01.mp4"
    base.write_bytes(b"base")
    routes = {"Clip_01": {"post_lipsync_required": True}}

    path, source = resolve_clip_video(
        tmp_path, "第1集", "Clip_01", base, routes, allow_base_preview=True,
    )

    assert path == base
    assert source == "base_preview_waiver"
