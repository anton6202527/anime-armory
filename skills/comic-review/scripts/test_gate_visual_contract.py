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


def test_specific_target_containing_front_or_distance_word_is_not_vague() -> None:
    assert gate.is_vague_gaze_target("看前方") is True
    assert gate.is_vague_gaze_target("坚定眼神") is True
    assert gate.is_vague_gaze_target("画右前方云路") is False
    assert gate.is_vague_gaze_target("街巷前方未点亮的灯架") is False


def test_traditional_contract_missing_warns_not_blocks(tmp_path: Path) -> None:
    root = tmp_path
    chapter = "第1话"
    (root / "_设置.md").write_text("- 传统原稿流程：启用\n", encoding="utf-8")
    panel_script = {"panels": [{"panel_id": "P001", "description": "主角推门。"}]}
    layout = {"segments": [{"panels": [{"panel_id": "P001"}]}]}
    jobs = {"jobs": [{"panel_id": "P001"}]}
    findings: list[dict] = []

    gate.check_traditional_manga_contract(root, chapter, panel_script, layout, jobs, findings)

    assert "name_board_missing" in codes(findings)
    assert "finishing_plan_missing" in codes(findings)
    assert {item["severity"] for item in findings} == {"warn"}


def test_panel_post_qc_warn_acceptance_downgrades_to_info(tmp_path: Path) -> None:
    root = tmp_path
    chapter = "第1话"
    panel_dir = root / "出图" / chapter / "panels"
    panel_dir.mkdir(parents=True)
    (panel_dir / "P001.png").write_bytes(b"placeholder")
    acceptance_dir = root / "生产数据" / "panel_qc" / chapter
    acceptance_dir.mkdir(parents=True)
    (acceptance_dir / "P001.json").write_text(
        """{
          "panel_id": "P001",
          "verdict": "warn",
          "manual_review": {
            "reviewed_at": "2026-07-09T12:00:00",
            "verdict": "pass",
            "reason": "亮部是计划内雾光，不是空白气泡。"
          }
        }""",
        encoding="utf-8",
    )
    jobs = {
        "jobs": [
            {
                "panel_id": "P001",
                "status": "ready",
                "result_path": f"出图/{chapter}/panels/P001.png",
                "post_qc": {"verdict": "warn"},
            }
        ]
    }
    findings: list[dict] = []

    gate.check_panel_jobs_ready(root, chapter, jobs, findings)

    assert len(findings) == 1
    assert findings[0]["code"] == "panel_post_qc_warn"
    assert findings[0]["severity"] == "info"
    assert findings[0]["machine_severity"] == "warn"
    assert findings[0]["manual_acceptance"]["status"] == "accepted"


def test_ready_panel_generated_under_stale_contract_blocks(tmp_path: Path) -> None:
    root = tmp_path
    chapter = "第1话"
    panel_dir = root / "出图" / chapter / "panels"
    panel_dir.mkdir(parents=True)
    (panel_dir / "P001.png").write_bytes(b"placeholder")
    jobs = {
        "jobs": [
            {
                "panel_id": "P001",
                "status": "ready",
                "result_path": f"出图/{chapter}/panels/P001.png",
                "submit_prompt_sha256": "a" * 64,
                "generated_from_submit_prompt_sha256": "b" * 64,
            }
        ]
    }
    findings: list[dict] = []

    gate.check_panel_jobs_ready(root, chapter, jobs, findings)

    assert "panel_generated_under_stale_contract" in codes(findings)
    assert all(item["severity"] == "block" for item in findings)


def test_ready_panel_with_matching_generation_hash_passes(tmp_path: Path) -> None:
    root = tmp_path
    chapter = "第1话"
    panel_dir = root / "出图" / chapter / "panels"
    panel_dir.mkdir(parents=True)
    (panel_dir / "P001.png").write_bytes(b"placeholder")
    jobs = {
        "jobs": [
            {
                "panel_id": "P001",
                "status": "ready",
                "result_path": f"出图/{chapter}/panels/P001.png",
                "submit_prompt_sha256": "a" * 64,
                "generated_from_submit_prompt_sha256": "a" * 64,
            }
        ]
    }
    findings: list[dict] = []

    gate.check_panel_jobs_ready(root, chapter, jobs, findings)

    assert findings == []


def test_page_format_with_longstrip_geometry_blocks(tmp_path: Path) -> None:
    layout = {
        "format": "页漫",
        "geometry_profile": "longstrip_single_column",
        "canvas": {"width": 1440},
        "segments": [{"panels": [{"panel_id": "P001", "x": 72, "y": 28, "w": 1296, "h": 900}]}],
    }
    findings: list[dict] = []

    gate.check_format_geometry(tmp_path, "第1话", layout, findings)

    assert "format_geometry_mismatch" in codes(findings)
    assert findings[0]["severity"] == "block"


def test_page_format_with_real_grid_geometry_passes(tmp_path: Path) -> None:
    layout = {
        "format": "页漫",
        "canvas": {"width": 1440},
        "segments": [
            {
                "panels": [
                    {"panel_id": "P001", "x": 72, "y": 28, "w": 620, "h": 500},
                    {"panel_id": "P002", "x": 748, "y": 28, "w": 620, "h": 500},
                ]
            }
        ],
    }
    findings: list[dict] = []

    gate.check_format_geometry(tmp_path, "第1话", layout, findings)

    assert findings == []


def test_longstrip_format_single_column_is_fine(tmp_path: Path) -> None:
    layout = {
        "format": "条漫",
        "geometry_profile": "longstrip_single_column",
        "canvas": {"width": 1440},
        "segments": [{"panels": [{"panel_id": "P001", "x": 72, "y": 28, "w": 1296, "h": 900}]}],
    }
    findings: list[dict] = []

    gate.check_format_geometry(tmp_path, "第1话", layout, findings)

    assert findings == []


def test_style_anchor_placeholder_counts_as_missing(tmp_path: Path) -> None:
    root = tmp_path
    (root / "_设置.md").write_text("- 风格锚: 未指定\n", encoding="utf-8")
    findings: list[dict] = []

    gate.check_style_contract(root, findings)

    assert "style_anchor_missing" in codes(findings)


def test_style_anchor_real_value_passes(tmp_path: Path) -> None:
    root = tmp_path
    (root / "_设置.md").write_text("- 风格锚: STYLE_INK_WASH\n", encoding="utf-8")
    findings: list[dict] = []

    gate.check_style_contract(root, findings)

    assert findings == []
