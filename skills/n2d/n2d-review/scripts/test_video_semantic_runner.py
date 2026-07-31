#!/usr/bin/env python3
"""Tests for video_semantic_runner manifest mapping."""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import video_semantic_runner as vsr  # noqa: E402


def test_clip_label_preserves_split_relay_part_suffix() -> None:
    assert vsr._clip_label("Clip_07_part1") == "Clip_07_part1"
    assert vsr._clip_label("Clip_07_part2") == "Clip_07_part2"
    assert vsr._clip_base("Clip_07_part2") == "Clip_07"


def test_storyboard_parent_is_not_duplicated_when_manifest_has_parts() -> None:
    items = {"Clip_07_part1": {}, "Clip_07_part2": {}}
    storyboard = {"Clip_07": {}, "Clip_08": {}}
    item_bases = {vsr._clip_base(label) for label in items}
    storyboard_labels = {label for label in storyboard if vsr._clip_base(label) not in item_bases}
    labels = sorted(set(items) | storyboard_labels, key=lambda x: (vsr._clip_num(x) or 9999, x))
    assert labels == ["Clip_07_part1", "Clip_07_part2", "Clip_08"]


def test_existing_video_rebases_stale_absolute_split_part_path(tmp_path) -> None:
    ep = "第1集"
    video_dir = tmp_path / "出视频" / ep / "视频"
    video_dir.mkdir(parents=True)
    part1 = video_dir / "Clip_07_标题_part1.mp4"
    part2 = video_dir / "Clip_07_标题_part2.mp4"
    part1.write_bytes(b"part1")
    part2.write_bytes(b"part2")

    stale = f"/Users/other/work/创作区/制漫剧/x/出视频/{ep}/视频/Clip_07_标题_part2.mp4"

    assert vsr._existing_video(tmp_path, ep, "Clip_07_part2", stale) == part2
