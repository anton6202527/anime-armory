#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_panel_jobs


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_panel_job_carries_visual_continuity_contract(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 生图模型：自定义\n- 生图渠道：manual\n- 基础视觉风格：彩色国漫条漫\n- 文字语言：中文\n",
        encoding="utf-8",
    )
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {
            "schema_version": 1,
            "visual_contract": {
                "character_integrity_policy": "锁脸型、眼型、发际线、服装主色和完整手脚。",
                "scene_anchors": {
                    "LOC_HALL": {
                        "spatial_layout": "祠堂门在画右后景，香案在中央。",
                        "lighting_anchor": "画左上 5600K 冷窗光。",
                        "axis_eyeline": "主角画左看画右。",
                    }
                },
            },
            "panels": [
                {
                    "panel_id": "P001",
                    "description": "主角在祠堂内发现匕首反光。",
                    "characters": ["CHAR_MAIN"],
                    "references": ["CHAR_MAIN", "LOC_HALL"],
                    "location": "祠堂",
                    "scene_anchor_id": "LOC_HALL",
                    "gaze_target": "画右下方的匕首反光",
                    "eyeline_direction": "画右下方",
                    "character_integrity": "脸、发型、衣襟和双手完整可读。",
                    "continuity_from": "none",
                }
            ],
        },
    )
    write_json(
        root / "排版" / chapter / "layout.json",
        {"segments": [{"panels": [{"panel_id": "P001", "w": 1000, "h": 800}]}]},
    )

    jobs = build_panel_jobs.build_jobs(root, chapter)
    job = jobs["jobs"][0]

    assert job["continuity_contract"]["scene_anchor_id"] == "LOC_HALL"
    assert job["continuity_contract"]["gaze_target"] == "画右下方的匕首反光"
    assert "视线/眼神契约" in job["prompt"]
    assert "场景一致性契约" in job["prompt"]
    assert "looking at viewer" in job["negative_prompt"]
