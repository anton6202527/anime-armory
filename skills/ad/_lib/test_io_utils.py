#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""io_utils 原子写单测：账本类 JSON 绝不能被进程中断写坏。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import io_utils  # noqa: E402


def _no_tmp_leftover(directory: Path) -> bool:
    return not list(directory.glob("*.tmp"))


def test_write_json_atomic_roundtrip_creates_parents(tmp_path):
    path = tmp_path / "生产数据" / "manifest.json"
    io_utils.write_json_atomic(str(path), {"中文": 1, "jobs": []})

    raw = path.read_text(encoding="utf-8")
    assert json.loads(raw) == {"中文": 1, "jobs": []}
    assert "中文" in raw  # ensure_ascii=False
    assert raw.endswith("\n")
    assert _no_tmp_leftover(path.parent)


def test_write_json_overwrite_keeps_single_final_state(tmp_path):
    path = tmp_path / "manifest.json"
    io_utils.write_json(str(path), {"v": 1})
    io_utils.write_json(str(path), {"v": 2})

    assert json.loads(path.read_text(encoding="utf-8")) == {"v": 2}
    assert _no_tmp_leftover(tmp_path)


def test_write_text_atomic_failure_keeps_old_content_and_cleans_tmp(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    io_utils.write_text_atomic(str(path), "old")

    def broken_replace(src, dst):
        raise OSError("simulated crash")

    monkeypatch.setattr(io_utils.os, "replace", broken_replace)
    with pytest.raises(OSError, match="simulated crash"):
        io_utils.write_text_atomic(str(path), "new")

    assert path.read_text(encoding="utf-8") == "old"
    assert _no_tmp_leftover(tmp_path)
