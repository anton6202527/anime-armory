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
import codex_panel_runner


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_panel_job_carries_visual_continuity_contract(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 生图模型：GPT Image 2\n- 生图渠道：Codex CLI\n- 基础视觉风格：彩色国漫条漫\n- 文字语言：中文\n",
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
    write_json(
        root / "出图" / chapter / "finishing" / "finishing_plan.json",
        {
            "render_stage": "网点完成稿",
            "panels": [
                {
                    "panel_id": "P001",
                    "ink_plan": "外轮廓更重，脸和手保持可读。",
                    "black_fill_plan": "匕首周围留白，人物背后加黑场。",
                    "tone_plan": "背景 20% 网点，衣服 40% 网点。",
                    "effects_plan": "集中线指向匕首反光。",
                    "no_bake_text_contract": "dialogue and narration stay out of raw images",
                }
            ],
        },
    )

    jobs = build_panel_jobs.build_jobs(root, chapter)
    job = jobs["jobs"][0]

    assert jobs["render_stage"] == "完成稿"
    assert jobs["schema_version"] == 2
    assert jobs["finishing_plan"] == "出图/第1话/finishing/finishing_plan.json"
    assert job["continuity_contract"]["scene_anchor_id"] == "LOC_HALL"
    assert job["traditional_finish_contract"]["tone_plan"] == "背景 20% 网点，衣服 40% 网点。"
    assert job["continuity_contract"]["gaze_target"] == "画右下方的匕首反光"
    assert "传统漫画原稿收尾契约" in job["production_contract_prompt"]
    assert "网点/灰阶计划" in job["production_contract_prompt"]
    assert "视线/眼神契约" in job["production_contract_prompt"]
    assert "场景一致性契约" in job["production_contract_prompt"]
    assert "looking at viewer" in job["production_negative_contract"]
    assert job["prompt_source_kind"] == "compiled_submit_prompt"
    assert job["prompt"] == job["submit_prompt"]
    assert job["prompt_compiler"]["kind"] == "comic_compiled_image_prompt"
    assert "匕首反光" in job["submit_prompt"]
    assert "CHAR_MAIN" not in job["submit_prompt"]
    assert "LOC_HALL" not in job["submit_prompt"]
    actual = codex_panel_runner.build_prompt(job, "work", chapter, [])
    assert job["submit_prompt"] in actual
    assert "传统漫画原稿收尾契约" not in actual
    assert "CHAR_MAIN" not in actual


def make_fixture(root: Path, chapter: str, *, description: str = "主角在祠堂内发现匕首反光。") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "_设置.md").write_text(
        "- 生图模型：GPT Image 2\n- 生图渠道：Codex CLI\n- 基础视觉风格：彩色国漫条漫\n- 文字语言：中文\n",
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
                    "description": description,
                    "characters": ["CHAR_MAIN"],
                    "references": ["CHAR_MAIN", "LOC_HALL"],
                    "location": "祠堂",
                    "scene_anchor_id": "LOC_HALL",
                    "gaze_target": "画右下方的匕首反光",
                    "eyeline_direction": "画右下方",
                    "character_integrity": "脸、发型、衣襟和双手完整可读。",
                }
            ],
        },
    )
    write_json(
        root / "排版" / chapter / "layout.json",
        {"segments": [{"panels": [{"panel_id": "P001", "w": 1000, "h": 800}]}]},
    )


def simulate_generated(root: Path, chapter: str, jobs: dict) -> None:
    """把 build_jobs 的产物模拟成已出图并落盘。"""
    panel_dir = root / "出图" / chapter / "panels"
    panel_dir.mkdir(parents=True, exist_ok=True)
    for job in jobs["jobs"]:
        pid = job["panel_id"]
        (panel_dir / f"{pid}.png").write_bytes(b"png-bytes")
        job.update(
            {
                "status": "ready",
                "result_path": f"出图/{chapter}/panels/{pid}.png",
                "generated_at": "2026-07-10T00:00:00",
                "artifact_sha256": "0" * 64,
                "generated_from_contract_sha256": job["source_contract_sha256"],
                "generated_from_submit_prompt_sha256": job["submit_prompt_sha256"],
            }
        )
    write_json(root / "出图" / chapter / "prompt" / "panel_jobs.json", jobs)


def test_preserve_keeps_ready_when_contract_unchanged(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    make_fixture(root, chapter)
    jobs = build_panel_jobs.build_jobs(root, chapter)
    simulate_generated(root, chapter, jobs)

    rebuilt = build_panel_jobs.build_jobs(root, chapter)
    preserved, stale = build_panel_jobs.preserve_ready_jobs(root, chapter, rebuilt)

    assert preserved == 1
    assert stale == []
    job = rebuilt["jobs"][0]
    assert job["status"] == "ready"
    assert job["generated_from_submit_prompt_sha256"] == job["submit_prompt_sha256"]


def test_preserve_resets_ready_when_submit_prompt_changed(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    make_fixture(root, chapter)
    jobs = build_panel_jobs.build_jobs(root, chapter)
    simulate_generated(root, chapter, jobs)

    make_fixture(root, chapter, description="主角回头，匕首已消失，门口出现黑影。")
    rebuilt = build_panel_jobs.build_jobs(root, chapter)
    preserved, stale = build_panel_jobs.preserve_ready_jobs(root, chapter, rebuilt)

    assert preserved == 0
    assert stale == ["P001"]
    assert rebuilt["jobs"][0]["status"] == "planned"
    assert not rebuilt["jobs"][0].get("result_path")


def test_check_stale_jobs_reports_contract_drift(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    make_fixture(root, chapter)
    jobs = build_panel_jobs.build_jobs(root, chapter)
    simulate_generated(root, chapter, jobs)

    fresh_same = build_panel_jobs.build_jobs(root, chapter)
    clean = build_panel_jobs.check_stale_jobs(root, chapter, fresh_same)
    assert clean["stale_panels"] == []
    assert clean["missing_panels"] == []
    assert clean["checked"] == 1

    make_fixture(root, chapter, description="主角回头，匕首已消失，门口出现黑影。")
    fresh_changed = build_panel_jobs.build_jobs(root, chapter)
    dirty = build_panel_jobs.check_stale_jobs(root, chapter, fresh_changed)
    assert dirty["stale_panels"] == ["P001"]
