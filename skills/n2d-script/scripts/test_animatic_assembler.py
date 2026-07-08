#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import animatic_assembler as aa  # noqa: E402


def test_animatic_assembler_writes_timed_preview(tmp_path: Path) -> None:
    ep = "第1集"
    ep_dir = tmp_path / "脚本" / ep
    ep_dir.mkdir(parents=True)
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "duration": 3, "dramatic_function": "开场钩子", "scene": "街口"},
            {"id": "Clip_02", "dramatic_function": "反转", "scene": "室内"},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    (ep_dir / "镜头时长.json").write_text(json.dumps({"Clip_02": 4}, ensure_ascii=False), encoding="utf-8")

    payload = aa.write_outputs(tmp_path, ep, aa.build_report(tmp_path, ep))

    assert payload["status"] == "pass"
    assert payload["summary"]["total_duration_sec"] == 7
    assert (tmp_path / payload["preview_artifact"]).is_file()
    assert (tmp_path / "生产数据" / "animatic_第1集.json").is_file()
