#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import gate


def codes(findings: list[dict]) -> set[str]:
    return {str(item.get("code")) for item in findings}


def test_visual_contract_missing_blocks_character_and_scene_panels(tmp_path: Path) -> None:
    panel_script = {
        "panels": [
            {
                "panel_id": "P001",
                "description": "主角站在祠堂里。",
                "characters": ["CHAR_MAIN"],
                "location": "祠堂",
            }
        ]
    }
    findings: list[dict] = []

    gate.check_panel_visual_contract(tmp_path, "第1话", panel_script, findings)

    assert "visual_contract_missing" in codes(findings)
    assert "panel_character_contract_missing" in codes(findings)
    assert "panel_scene_contract_missing" in codes(findings)


def test_visual_contract_allows_scene_anchor_inheritance(tmp_path: Path) -> None:
    panel_script = {
        "visual_contract": {
            "character_integrity_policy": "锁脸型、眼型、发际线、服装主色和完整手脚。",
            "scene_anchors": {
                "LOC_HALL": {
                    "spatial_layout": "门在画右后景，香案在中央。",
                    "lighting_anchor": "画左上冷窗光。",
                    "axis_eyeline": "主角画左看画右。",
                }
            },
        },
        "panels": [
            {
                "panel_id": "P001",
                "description": "主角站在祠堂里。",
                "characters": ["CHAR_MAIN"],
                "references": ["CHAR_MAIN", "LOC_HALL"],
                "scene_anchor_id": "LOC_HALL",
                "gaze_target": "画右的对手",
                "eyeline_direction": "画右",
                "character_integrity": "脸、发型、衣摆、手脚完整可读。",
            }
        ],
    }
    findings: list[dict] = []

    gate.check_panel_visual_contract(tmp_path, "第1话", panel_script, findings)

    assert findings == []


def test_visual_contract_blocks_camera_gaze_and_unregistered_scene(tmp_path: Path) -> None:
    panel_script = {
        "visual_contract": {
            "character_integrity_policy": "锁脸型、眼型、发际线、服装主色和完整手脚。",
            "scene_anchors": {
                "LOC_HALL": {
                    "spatial_layout": "门在画右后景，香案在中央。",
                    "lighting_anchor": "画左上冷窗光。",
                    "axis_eyeline": "主角画左看画右。",
                }
            },
        },
        "panels": [
            {
                "panel_id": "P001",
                "description": "主角和对手在陌生祠堂对峙。",
                "characters": ["CHAR_MAIN", "CHAR_RIVAL"],
                "references": ["CHAR_MAIN", "CHAR_RIVAL", "LOC_UNKNOWN"],
                "scene_anchor_id": "LOC_UNKNOWN",
                "spatial_layout": "门在画右后景，香案在中央。",
                "lighting_anchor": "画左上冷窗光。",
                "axis_eyeline": "主角画左看画右。",
                "gaze_target": "看镜头",
                "eyeline_direction": "正前方",
                "character_integrity": "脸型、眼型、发际线、发型和双手完整可读。",
            }
        ],
    }
    findings: list[dict] = []

    gate.check_panel_visual_contract(tmp_path, "第1话", panel_script, findings)

    assert "panel_camera_gaze_unjustified" in codes(findings)
    assert "panel_scene_anchor_unregistered" in codes(findings)
    assert "panel_multi_character_staging_missing" in codes(findings)
