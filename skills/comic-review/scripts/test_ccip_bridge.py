#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ccip_bridge 协议与降级行为的封闭测试（不要求 imgutils 存在）。"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ccip_bridge


def test_unavailable_bridge_returns_none_per_pair(monkeypatch) -> None:
    monkeypatch.setattr(ccip_bridge, "resolve_interpreter", lambda: "")
    bridge = ccip_bridge.CCIPBridge()
    assert bridge.available() is False
    assert bridge.mode() == "unavailable"
    assert bridge.batch_differences([("a", "b"), ("c", "d")]) == [None, None]


def test_empty_pairs_short_circuit() -> None:
    bridge = ccip_bridge.CCIPBridge()
    assert bridge.batch_differences([]) == []


def test_env_override_requires_existing_interpreter(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ccip_bridge, "_inprocess_available", lambda: False)
    monkeypatch.setenv("COMIC_CCIP_PYTHON", str(tmp_path / "missing-python"))
    monkeypatch.setattr(ccip_bridge, "_CONDA_ENV_GLOBS", ())
    assert ccip_bridge.resolve_interpreter() == ""


def test_env_override_accepts_interpreter_with_imgutils(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ccip_bridge, "_inprocess_available", lambda: False)
    fake_env = tmp_path / "env"
    python = fake_env / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n")
    site = fake_env / "lib" / "python3.11" / "site-packages" / "imgutils"
    site.mkdir(parents=True)
    monkeypatch.setenv("COMIC_CCIP_PYTHON", str(python))
    assert ccip_bridge.resolve_interpreter() == str(python)


def test_inprocess_wins_when_importable(monkeypatch) -> None:
    monkeypatch.setattr(ccip_bridge, "_inprocess_available", lambda: True)
    assert ccip_bridge.resolve_interpreter() == "inprocess"


def test_broken_worker_marks_bridge_unavailable(monkeypatch, tmp_path) -> None:
    bad = tmp_path / "python"
    bad.write_text("")  # 不可执行
    bridge = ccip_bridge.CCIPBridge()
    bridge._interpreter = str(bad)
    result = bridge.batch_differences([("a", "b")])
    assert result == [None]
    assert bridge.available() is False
