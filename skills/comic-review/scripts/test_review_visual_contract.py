#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import review


def issue_reasons(issues: list[dict]) -> str:
    return "；".join(str(item.get("reason") or "") for item in issues)


def test_review_visual_contract_reports_camera_gaze_and_scene_gaps() -> None:
    panel_script = {
        "visual_contract": {
            "character_integrity_policy": "保持人物完整。",
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
                "description": "两人对峙。",
                "characters": ["CHAR_MAIN", "CHAR_RIVAL"],
                "references": ["CHAR_MAIN", "CHAR_RIVAL", "LOC_UNKNOWN"],
                "scene_anchor_id": "LOC_UNKNOWN",
                "spatial_layout": "门在画右后景，香案在中央。",
                "lighting_anchor": "画左上冷窗光。",
                "axis_eyeline": "主角画左看画右。",
                "gaze_target": "看镜头",
                "eyeline_direction": "正前方",
                "character_integrity": "保持人物完整。",
            }
        ],
    }
    issues: list[dict] = []

    review.check_visual_contract_issues(panel_script, "第1话", issues)

    reasons = issue_reasons(issues)
    assert "指向读者/镜头" in reasons
    assert "未登记该场景锚" in reasons
    assert "缺少人物左右/前后景/遮挡或轴线关系" in reasons
    assert any(issue.get("severity") == "block" for issue in issues)
