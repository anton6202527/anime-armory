#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import series_bible as sb  # noqa: E402


def test_series_bible_aggregates_episode_and_character_gaps(tmp_path: Path) -> None:
    root = tmp_path
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text("真相到底是谁藏起来？门外突然传来脚步。🪝\n", encoding="utf-8")
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "description": "沈念发现 LOC_HALL 的 PROP_TOKEN，真相反转。",
            "character_ids": ["CHAR_01"],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_01",
            "name": "沈念",
            "scope": "全篇主角",
            "forms": [{"form": "常态", "asset_key": "沈念常态"}],
        }]
    }, ensure_ascii=False), encoding="utf-8")

    bible = sb.build_series_bible(root)

    assert bible["kind"] == sb.KIND
    assert bible["narrative_graph"]["episode_nodes"][0]["characters"] == ["CHAR_01"]
    assert bible["narrative_graph"]["episode_nodes"][0]["assets"] == ["LOC_HALL", "PROP_TOKEN"]
    assert any(f["code"] == "core_character_missing_performance_signature" for f in bible["findings"])


def test_series_bible_write_outputs(tmp_path: Path) -> None:
    bible = sb.build_series_bible(tmp_path)
    jp, mp = sb.write_outputs(tmp_path, bible)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == sb.KIND
