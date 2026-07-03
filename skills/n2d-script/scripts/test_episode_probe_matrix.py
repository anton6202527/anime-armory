#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import episode_probe_matrix as epm  # noqa: E402


def _write_storyboard(root: Path) -> None:
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "description": "冷开场门外突然传来脚步。"},
            {"id": "Clip_02", "description": "CHAR_01 和 CHAR_02 多人同框打斗爽点。", "character_ids": ["CHAR_01", "CHAR_02"]},
        ]
    }, ensure_ascii=False), encoding="utf-8")


def test_episode_probe_matrix_selects_opening_and_risk(monkeypatch, tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    monkeypatch.setattr(epm.sra, "audit", lambda root, ep: {
        "clips": [
            {"id": "Clip_01", "score": 1, "tags": []},
            {"id": "Clip_02", "score": 8, "tags": ["multi_character", "high_motion"]},
        ],
        "summary": {"max_score": 8},
    })

    matrix = epm.build_matrix(tmp_path, "第1集", limit=2)

    assert matrix["kind"] == epm.KIND
    assert [p["clip"] for p in matrix["probes"]] == ["Clip_01", "Clip_02"]
    assert "opening_probe" in matrix["probes"][0]["reasons"]
    assert "multi_subject_probe" in matrix["probes"][1]["reasons"]


def test_episode_probe_matrix_writes_outputs(monkeypatch, tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    monkeypatch.setattr(epm.sra, "audit", lambda root, ep: {"clips": [], "summary": {}})
    matrix = epm.build_matrix(tmp_path, "第1集")
    jp, mp = epm.write_outputs(tmp_path, "第1集", matrix)

    assert jp.exists()
    assert mp.exists()
