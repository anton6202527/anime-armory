#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_voice 资金/产物安全单测：占位复用判定、外部导入 .bak 保护、上次清单读取。"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_voice as rv  # noqa: E402


def test_text_sha256_stable_and_strips():
    assert rv.text_sha256("你好") == rv.text_sha256(" 你好 ")
    assert rv.text_sha256("你好") != rv.text_sha256("你好呀")


def test_line_reusable_requires_same_text_and_voice_key(tmp_path, monkeypatch):
    wav = tmp_path / "line_01.wav"
    wav.write_bytes(b"fake wav")
    monkeypatch.setattr(rv, "probe_duration", lambda p: 1.2)
    key = "say:Tingting#placeholder"
    prev = {"text_sha256": rv.text_sha256("你好"), "voice_key": key}

    assert rv.line_reusable(prev, str(wav), rv.text_sha256("你好"), key)
    assert not rv.line_reusable(prev, str(wav), rv.text_sha256("文本变了"), key)
    assert not rv.line_reusable(prev, str(wav), rv.text_sha256("你好"), "say:Meijia#placeholder")
    assert not rv.line_reusable(None, str(wav), rv.text_sha256("你好"), key)
    assert not rv.line_reusable(prev, str(tmp_path / "missing.wav"), rv.text_sha256("你好"), key)


def test_line_reusable_rejects_unreadable_duration(tmp_path, monkeypatch):
    wav = tmp_path / "line_01.wav"
    wav.write_bytes(b"fake wav")
    monkeypatch.setattr(rv, "probe_duration", lambda p: None)
    key = "say:Tingting#placeholder"
    prev = {"text_sha256": rv.text_sha256("你好"), "voice_key": key}

    assert not rv.line_reusable(prev, str(wav), rv.text_sha256("你好"), key)


def test_import_external_wav_backs_up_existing_different_target(tmp_path):
    src = tmp_path / "src.wav"
    dst = tmp_path / "line_01.wav"
    src.write_bytes(b"new audio")
    dst.write_bytes(b"old audio")

    rv.import_external_wav(str(src), str(dst))

    assert dst.read_bytes() == b"new audio"
    assert (tmp_path / "line_01.wav.bak").read_bytes() == b"old audio"


def test_import_external_wav_same_content_no_bak(tmp_path):
    src = tmp_path / "src.wav"
    dst = tmp_path / "line_01.wav"
    src.write_bytes(b"same audio")
    dst.write_bytes(b"same audio")

    rv.import_external_wav(str(src), str(dst))

    assert dst.read_bytes() == b"same audio"
    assert not (tmp_path / "line_01.wav.bak").exists()


def test_import_external_wav_fresh_target_no_bak(tmp_path):
    src = tmp_path / "src.wav"
    dst = tmp_path / "line_01.wav"
    src.write_bytes(b"new audio")

    rv.import_external_wav(str(src), str(dst))

    assert dst.read_bytes() == b"new audio"
    assert not (tmp_path / "line_01.wav.bak").exists()


def test_load_prev_lines_maps_by_idx(tmp_path):
    path = tmp_path / "时长清单.json"
    path.write_text(json.dumps({
        "backend": "say",
        "lines": [{"idx": 1, "text_sha256": "a"}, {"idx": 2, "text_sha256": "b"}],
    }, ensure_ascii=False), encoding="utf-8")

    prev, backend = rv.load_prev_lines(str(path))

    assert backend == "say"
    assert prev[1]["text_sha256"] == "a"
    assert prev[2]["text_sha256"] == "b"


def test_load_prev_lines_missing_or_corrupt_returns_empty(tmp_path):
    assert rv.load_prev_lines(str(tmp_path / "缺失.json")) == ({}, "")
    bad = tmp_path / "坏.json"
    bad.write_text("{not json", encoding="utf-8")
    assert rv.load_prev_lines(str(bad)) == ({}, "")


def test_manifest_written_atomically_via_io_utils(tmp_path):
    # render_voice 的清单出口收敛到 io_utils.write_json_atomic：无半写、无 tmp 残留
    path = tmp_path / "配音" / "时长清单.json"
    rv.io_utils.write_json_atomic(str(path), {"lines": [], "backend": "say"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"lines": [], "backend": "say"}
    assert not list(path.parent.glob("*.tmp"))
    assert os.path.isfile(path)
