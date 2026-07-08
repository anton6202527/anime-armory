#!/usr/bin/env python3
"""Tests for story_economy_audit.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import story_economy_audit as SEA  # noqa: E402


def _project(tmp_path: Path, clips) -> Path:
    root = tmp_path / "剧"
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({"clips": clips}, ensure_ascii=False), encoding="utf-8")
    return root


def test_non_premium_exposition_long_clip_blocks(tmp_path: Path) -> None:
    root = _project(tmp_path, [{
        "id": "Clip_01",
        "label": "上盘村狼妖危机",
        "duration": 28.0,
        "dramatic_function": "把狼妖危机和亲族被困说清。",
        "narration_indices": [1, 2, 3],
        "shots": [{"desc": "旁白：陈青源把飞鹰门折损、亲族被困、狼妖每日拖人说清。"}],
    }])

    report = SEA.build_report(root, "第1集")
    row = report["clips"][0]

    assert report["ok"] is False
    assert row["economy_class"] in {"compact_story", "selective_detail"}
    assert row["recommended_action"] in {"compress_or_narrate_before_video", "trim_to_selective_detail"}
    assert row["detail_allowed"] is False
    assert {f["code"] for f in report["findings"]} == {"non_premium_story_clip_too_long"}


def test_fight_clip_allows_detailed_runtime(tmp_path: Path) -> None:
    root = _project(tmp_path, [{
        "id": "Clip_02",
        "label": "狼爪集尾",
        "duration": 13.0,
        "template": "fight_exchange",
        "dramatic_function": "青面郎君弹爪下令，战斗在第一击前硬断。",
    }])

    report = SEA.build_report(root, "第1集")
    row = report["clips"][0]

    assert report["ok"] is True
    assert row["economy_class"] == "premium_detail"
    assert row["detail_allowed"] is True
    assert row["recommended_action"] == "keep_detail_but_split_video_shots"


def test_write_outputs(tmp_path: Path) -> None:
    root = _project(tmp_path, [{
        "id": "Clip_01",
        "duration": 4,
        "dramatic_function": "手掌按住刀柄，表明她准备离开。",
    }])
    report = SEA.build_report(root, "第1集")
    jp, mp = SEA.write_outputs(root, "第1集", report)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == SEA.KIND


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
