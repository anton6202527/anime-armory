#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import story_acceptance_packets as sap  # noqa: E402


def _write_inputs(root: Path, ep: str = "第1集") -> None:
    ep_dir = root / "脚本" / ep
    ep_dir.mkdir(parents=True)
    (ep_dir / "voiceover.txt").write_text("1. 你终于来了。\n2. 令牌是真的。\n", encoding="utf-8")
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "duration": 4, "dramatic_function": "冷开钩子", "continuity": {"transition": "cut"}},
            {"id": "Clip_02", "duration": 5, "dramatic_function": "反转", "continuity": {"transition": "match_cut"}},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    (ep_dir / "镜头时长.json").write_text(json.dumps({"Clip_01": 4, "Clip_02": 5}, ensure_ascii=False), encoding="utf-8")


def test_scaffold_and_check_blocks_draft(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    sap.scaffold(tmp_path, "1", kind="both")
    report = sap.check(tmp_path, "第1集", kind="both")

    assert report["status"] == "block"
    assert report["summary"]["block"] == 5


def test_confirmed_packets_pass(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    sap.scaffold(tmp_path, "第1集", kind="both", confirmed=True)
    report = sap.check(tmp_path, "第1集", kind="both", write_missing=True)

    assert report["status"] == "pass"
    assert (tmp_path / "生产数据" / "animatic_第1集.html").is_file()
    animatic = json.loads((tmp_path / "脚本" / "第1集" / "animatic_packet.json").read_text(encoding="utf-8"))
    assert animatic["timeline"]["estimated_total_sec"] == 9


def test_confirmed_packet_blocks_after_storyboard_changes(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    sap.scaffold(tmp_path, "第1集", kind="animatic", confirmed=True)

    sb = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb.read_text(encoding="utf-8"))
    data["clips"].append({"id": "Clip_03", "duration": 2, "dramatic_function": "新转折"})
    sb.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    report = sap.check(tmp_path, "第1集", kind="animatic", write_missing=True)

    assert report["status"] == "block"
    assert any("inputs_fingerprint" in "；".join(row["issues"]) for row in report["files"])
