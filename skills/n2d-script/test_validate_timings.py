#!/usr/bin/env python3
"""Tests for validate_timings deterministic helpers.

Run from this directory:
    cd skills/n2d-script && python3 -m pytest test_validate_timings.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importing the module triggers its own sys.path.insert for ../common.
import validate_timings as V  # noqa: E402


_SRT = (
    "1\n"
    "00:00:00,000 --> 00:00:02,500\n"
    "第一句中文\n"
    "First line\n"
    "\n"
    "2\n"
    "00:00:02,500 --> 00:00:05,000\n"
    "第二句中文\n"
    "Second line\n"
)


# ── srt_blocks / _srt_text ──
def test_srt_blocks_count(tmp_path):
    p = tmp_path / "sub.srt"
    p.write_text(_SRT, encoding="utf-8")
    blocks = V.srt_blocks(str(p))
    assert len(blocks) == 2


def test_srt_blocks_missing_file():
    assert V.srt_blocks("/nonexistent/path/x.srt") == []


def test_srt_text_extracts_text_lines(tmp_path):
    p = tmp_path / "sub.srt"
    p.write_text(_SRT, encoding="utf-8")
    blocks = V.srt_blocks(str(p))
    txt = V._srt_text(blocks[0])
    # index line + timecode stripped; text lines (3rd onward) joined
    assert "第一句中文" in txt
    assert "First line" in txt
    assert "00:00:00" not in txt


# ── _is_placeholder_en_blocks ──
def test_is_placeholder_en_blocks_true():
    placeholder = (
        "1\n00:00:00,000 --> 00:00:02,000\n"
        "English subtitles for overseas platforms (TODO placeholder)\n"
    )
    blocks = placeholder.strip().split("\n\n")
    # Build blocks the same way srt_blocks would (single block here)
    assert V._is_placeholder_en_blocks([placeholder.strip()]) is True


def test_is_placeholder_en_blocks_false_real_text(tmp_path):
    p = tmp_path / "en.srt"
    p.write_text(_SRT, encoding="utf-8")
    blocks = V.srt_blocks(str(p))
    assert V._is_placeholder_en_blocks(blocks) is False


def test_is_placeholder_en_blocks_empty():
    assert V._is_placeholder_en_blocks([]) is False


# ── srt_last_end time math ──
def test_srt_last_end_value(tmp_path):
    p = tmp_path / "sub.srt"
    p.write_text(_SRT, encoding="utf-8")
    last = V.srt_last_end(str(p))
    # last block ends at 00:00:05,000 = 5.0s
    assert abs(last - 5.0) < 1e-6


def test_srt_last_end_missing():
    assert V.srt_last_end("/nonexistent/x.srt") is None


# ── _validate_native_av branch ──
def _make_native(root, ep, shots, clips):
    sdir = os.path.join(root, "脚本", ep)
    os.makedirs(sdir, exist_ok=True)
    shots_p = os.path.join(sdir, "镜头时长.json")
    json.dump(shots, open(shots_p, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"clips": clips},
              open(os.path.join(sdir, "storyboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    return shots_p


def test_native_av_pass_when_matching(tmp_path, capsys):
    root, ep = str(tmp_path), "第1集"
    # ∑镜头时长 = 5.0; ∑clip.duration = 5.0 → within tol → rc 0
    shots_p = _make_native(root, ep,
                           {"镜头1": 2.0, "镜头2": 3.0},
                           [{"duration": 2.0}, {"duration": 3.0}])
    rc = V._validate_native_av(root, ep, shots_p, 0.5)
    assert rc == 0


def test_native_av_fail_when_mismatched(tmp_path):
    root, ep = str(tmp_path), "第1集"
    # ∑镜头时长 = 5.0; ∑clip.duration = 8.0 → diff 3.0 > tol → rc 1
    shots_p = _make_native(root, ep,
                           {"镜头1": 2.0, "镜头2": 3.0},
                           [{"duration": 4.0}, {"duration": 4.0}])
    rc = V._validate_native_av(root, ep, shots_p, 0.5)
    assert rc == 1


def test_native_av_missing_shots_file_fails(tmp_path):
    root, ep = str(tmp_path), "第1集"
    shots_p = os.path.join(root, "脚本", ep, "镜头时长.json")  # not created
    rc = V._validate_native_av(root, ep, shots_p, 0.5)
    assert rc == 1
