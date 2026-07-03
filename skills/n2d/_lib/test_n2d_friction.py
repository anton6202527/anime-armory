#!/usr/bin/env python3
"""cd skills/n2d/_lib && python -m pytest test_n2d_friction.py"""
from __future__ import annotations

import json
from pathlib import Path

import n2d_friction as nf


def test_log_and_read_roundtrip(tmp_path):
    rec = nf.log_friction(
        str(tmp_path),
        "n2d-voice",
        "CosyVoice 不可用，全集静音占位",
        kind="workaround",
        stage="配音",
        episode="第1集",
        evidence="合成/第1集/配音/_占位说明.md",
        proposed="adapter 缺后端时早探活并提示安装",
        severity="warn",
    )
    assert rec is not None and rec["kind"] == nf.FRICTION_KIND
    path = Path(nf.friction_log_path(str(tmp_path)))
    assert path.is_file() and path.parent.name == nf.PRODUCTION_DIRNAME
    back = nf.read_friction(str(tmp_path))
    assert len(back) == 1
    assert back[0]["skill"] == "n2d-voice"
    assert back[0]["signal_kind"] == "workaround"
    assert back[0]["severity"] == "warn"


def test_append_accumulates(tmp_path):
    for i in range(3):
        nf.log_friction(str(tmp_path), "n2d-image", f"信号{i}", kind="defect")
    assert len(nf.read_friction(str(tmp_path))) == 3


def test_missing_required_fields_are_noops(tmp_path):
    assert nf.log_friction(str(tmp_path), "n2d-voice", "") is None  # 空 what
    assert nf.log_friction(str(tmp_path), "", "有现象") is None       # 空 skill
    assert nf.log_friction("", "n2d-voice", "有现象") is None         # 空 work_root
    assert nf.read_friction(str(tmp_path)) == []


def test_unknown_severity_degrades_to_info(tmp_path):
    rec = nf.log_friction(str(tmp_path), "n2d-script", "x", severity="catastrophic")
    assert rec["severity"] == "info"


def test_failure_is_swallowed_returns_none(tmp_path):
    # 让落点目录变成一个文件，使 makedirs/open 必失败——必须静默返回 None，不抛。
    bad = tmp_path / "blocked"
    bad.write_text("i am a file, not a dir", encoding="utf-8")
    assert nf.log_friction(str(bad), "n2d-voice", "现象") is None


def test_read_tolerates_garbage_lines(tmp_path):
    path = Path(nf.friction_log_path(str(tmp_path)))
    path.parent.mkdir(parents=True, exist_ok=True)
    nf.log_friction(str(tmp_path), "n2d-voice", "good one")
    with path.open("a", encoding="utf-8") as f:
        f.write("not json at all\n")
        f.write(json.dumps({"kind": "something_else"}) + "\n")  # 非本类信号
    back = nf.read_friction(str(tmp_path))
    assert len(back) == 1 and back[0]["what"] == "good one"


def test_summarize_clusters_by_skill_kind(tmp_path):
    nf.log_friction(str(tmp_path), "n2d-voice", "a", kind="workaround", severity="info")
    nf.log_friction(str(tmp_path), "n2d-voice", "b", kind="workaround", severity="block",
                    proposed="修适配层", evidence="e1")
    nf.log_friction(str(tmp_path), "n2d-image", "c", kind="defect", severity="warn")
    summary = nf.summarize_friction(nf.read_friction(str(tmp_path)))
    assert summary["total"] == 3
    assert summary["by_severity"] == {"info": 1, "warn": 1, "block": 1}
    # block 簇排最前
    top = summary["clusters"][0]
    assert top["skill"] == "n2d-voice" and top["signal_kind"] == "workaround"
    assert top["count"] == 2 and top["severity"] == "block"
    assert top["latest_proposed"] == "修适配层"
    assert "e1" in top["evidence"]
