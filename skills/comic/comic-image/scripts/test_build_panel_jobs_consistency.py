#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import pytest
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


def write_identity_fixture(root: Path) -> dict:
    images = root / "出图" / "共享" / "图片"
    images.mkdir(parents=True, exist_ok=True)
    for name, payload in (("CHAR_MAIN__front.png", b"front"), ("CHAR_MAIN__face.png", b"face"), ("LOC_HALL__anchor.png", b"hall")):
        (images / name).write_bytes(payload)
    registry = {
        "schema_version": 2,
        "kind": "comic_identity_registry",
        "assets": {
            "CHAR_MAIN": {
                "id": "CHAR_MAIN", "type": "character", "display_name": "主角", "library_tier": "named_minimal",
                "views": {"front": "出图/共享/图片/CHAR_MAIN__front.png", "face": "出图/共享/图片/CHAR_MAIN__face.png"},
                "forms": {"FORM_BASE": {"id": "FORM_BASE", "name": "常态", "reference_images": ["出图/共享/图片/CHAR_MAIN__front.png"]}},
                "outfits": {"OUTFIT_BASE": {"id": "OUTFIT_BASE", "name": "灰衣", "description": "灰色交领", "reference_images": ["出图/共享/图片/CHAR_MAIN__front.png"]}},
                "expressions": {"EXPR_NEUTRAL": {"id": "EXPR_NEUTRAL", "name": "中性", "emotion": "neutral", "reference_images": ["出图/共享/图片/CHAR_MAIN__face.png"]}},
                "states": {"STATE_BASE": {"id": "STATE_BASE", "name": "正常", "form_id": "FORM_BASE", "outfit_id": "OUTFIT_BASE", "expression_id": "EXPR_NEUTRAL"}},
                "default_binding": {"form_id": "FORM_BASE", "outfit_id": "OUTFIT_BASE", "expression_id": "EXPR_NEUTRAL", "state_id": "STATE_BASE"},
            },
            "LOC_HALL": {"id": "LOC_HALL", "type": "location", "anchor_path": "出图/共享/图片/LOC_HALL__anchor.png"},
        },
    }
    write_json(root / "出图" / "共享" / "identity_registry.json", registry)
    return registry


BASE_BINDING = {
    "character_id": "CHAR_MAIN",
    "form_id": "FORM_BASE",
    "outfit_id": "OUTFIT_BASE",
    "expression_id": "EXPR_NEUTRAL",
    "state_id": "STATE_BASE",
}


def test_panel_job_carries_visual_continuity_contract(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 生图模型：GPT Image 2\n- 生图渠道：Codex CLI\n- 基础视觉风格：彩色国漫条漫\n"
        "- 文字语言：中文\n- 生图分辨率策略：按最终画布\n",
        encoding="utf-8",
    )
    write_identity_fixture(root)
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
                    "character_bindings": [BASE_BINDING],
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
    # continuity_from="none" 属占位值，不应进入提交 prompt
    assert "承接上一格" not in job["submit_prompt"]
    actual = codex_panel_runner.build_prompt(job, "work", chapter, [])
    assert job["submit_prompt"] in actual
    assert "传统漫画原稿收尾契约" not in actual
    assert "CHAR_MAIN" not in actual


def make_fixture(root: Path, chapter: str, *, description: str = "主角在祠堂内发现匕首反光。") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "_设置.md").write_text(
        "- 生图模型：GPT Image 2\n- 生图渠道：Codex CLI\n- 基础视觉风格：彩色国漫条漫\n"
        "- 文字语言：中文\n- 生图分辨率策略：按最终画布\n",
        encoding="utf-8",
    )
    write_identity_fixture(root)
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
                    "character_bindings": [BASE_BINDING],
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
    """把 build_jobs 的产物模拟成已出图并完成当前 SHA 的逐图双闸。"""
    from PIL import Image

    panel_dir = root / "出图" / chapter / "panels"
    panel_dir.mkdir(parents=True, exist_ok=True)
    for job in jobs["jobs"]:
        pid = job["panel_id"]
        panel = panel_dir / f"{pid}.png"
        Image.new("RGB", (100, 80), (40, 90, 130)).save(panel)
        job.update(
            {
                "result_path": f"出图/{chapter}/panels/{pid}.png",
                "generated_at": "2026-07-10T00:00:00",
                "artifact_sha256": codex_panel_runner.file_sha256(panel),
                "generated_from_contract_sha256": job["source_contract_sha256"],
                "generated_from_submit_prompt_sha256": job["submit_prompt_sha256"],
            }
        )
        declared = [ref for ref in job.get("references") or [] if isinstance(ref, dict)]
        post_qc = codex_panel_runner.post_qc_panel(root, chapter, job, panel, [], declared)
        job["post_qc"] = post_qc
        job["status"] = codex_panel_runner.status_after_post_qc(post_qc)
    write_json(root / "出图" / chapter / "prompt" / "panel_jobs.json", jobs)
    for job in jobs["jobs"]:
        codex_panel_runner.accept_panel_review(
            root,
            chapter,
            jobs,
            root / "出图" / chapter / "prompt" / "panel_jobs.json",
            str(job["panel_id"]),
            "test-reviewer",
            "fixture comparison packet reviewed",
        )


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


def test_preserve_keeps_ready_when_only_reference_execution_input_changes(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    make_fixture(root, chapter)
    jobs = build_panel_jobs.build_jobs(root, chapter)
    simulate_generated(root, chapter, jobs)

    rebuilt = build_panel_jobs.build_jobs(root, chapter)
    rebuilt["jobs"][0]["execution_input_sha256"] = "f" * 64
    rebuilt["jobs"][0]["references"].append(
        {
            "id": "CHAR_MAIN",
            "path": "出图/共享/图片/CHAR_MAIN__side.png",
            "sha256": "e" * 64,
        }
    )

    preserved, stale = build_panel_jobs.preserve_ready_jobs(root, chapter, rebuilt)

    assert preserved == 1
    assert stale == []
    assert rebuilt["jobs"][0]["status"] == "ready"


def test_outfit_binding_injects_refs_and_contract(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    make_fixture(root, chapter)
    outfit_img = root / "出图" / "共享" / "图片" / "CHAR_MAIN__outfit_prison.png"
    outfit_img.parent.mkdir(parents=True, exist_ok=True)
    outfit_img.write_bytes(b"outfit-ref")
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    character = registry["assets"]["CHAR_MAIN"]
    character["outfits"]["OUTFIT_PRISON"] = {
        "id": "OUTFIT_PRISON", "name": "囚服",
        "description": "粗麻灰囚服，右肩补丁，无纽扣",
        "forbidden": "官服玉带、任何金属饰物",
        "reference_images": ["出图/共享/图片/CHAR_MAIN__outfit_prison.png"],
    }
    character["states"]["STATE_PRISON"] = {
        "id": "STATE_PRISON", "name": "囚禁", "form_id": "FORM_BASE",
        "outfit_id": "OUTFIT_PRISON", "expression_id": "EXPR_NEUTRAL",
    }
    write_json(registry_path, registry)
    script_path = root / "脚本" / chapter / "panel_script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["panels"][0]["character_bindings"][0]["outfit_id"] = "OUTFIT_PRISON"
    script["panels"][0]["character_bindings"][0]["state_id"] = "STATE_PRISON"
    write_json(script_path, script)

    jobs = build_panel_jobs.build_jobs(root, chapter)
    job = jobs["jobs"][0]

    assert job["outfit_binding"] == {"ref_id": "CHAR_MAIN", "outfit_id": "OUTFIT_PRISON", "registered": True}
    outfit_refs = [ref for ref in job["references"] if str(ref.get("role", "")) == "outfit"]
    assert outfit_refs and outfit_refs[0]["path"].endswith("CHAR_MAIN__outfit_prison.png")
    assert "服装契约" in job["production_contract_prompt"]
    assert "囚服" in job["submit_prompt"]
    assert "官服玉带" in job["submit_prompt"]
    assert "OUTFIT_PRISON" not in job["submit_prompt"]


def test_unregistered_outfit_marks_binding(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    make_fixture(root, chapter)
    script_path = root / "脚本" / chapter / "panel_script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["panels"][0]["character_bindings"][0]["outfit_id"] = "OUTFIT_MISSING"
    write_json(script_path, script)

    with pytest.raises(build_panel_jobs.ReferencePlanBlocked, match="character_binding_outfit_id_unknown"):
        build_panel_jobs.build_jobs(root, chapter)


def test_continuity_from_compiles_into_submit_prompt(tmp_path: Path) -> None:
    root = tmp_path / "work"
    chapter = "第1话"
    make_fixture(root, chapter)
    script_path = root / "脚本" / chapter / "panel_script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["panels"][0]["continuity_from"] = "延续上一格的祠堂雨夜与画左灯笼"
    write_json(script_path, script)

    jobs = build_panel_jobs.build_jobs(root, chapter)
    prompt = jobs["jobs"][0]["submit_prompt"]

    assert "承接上一格:延续上一格的祠堂雨夜与画左灯笼" in prompt


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


def test_missing_structured_binding_blocks_job_build(tmp_path: Path) -> None:
    root = tmp_path / "work"
    make_fixture(root, "第1话")
    script_path = root / "脚本" / "第1话" / "panel_script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["panels"][0].pop("character_bindings")
    write_json(script_path, script)
    with pytest.raises(build_panel_jobs.ReferencePlanBlocked, match="missing_structured_character_binding"):
        build_panel_jobs.build_jobs(root, "第1话")


def test_reference_plan_input_change_is_stale(tmp_path: Path) -> None:
    root = tmp_path / "work"
    make_fixture(root, "第1话")
    plan = build_panel_jobs.reference_planner.build_plan(root, "第1话")
    script_path = root / "脚本" / "第1话" / "panel_script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["panels"][0]["art_notes"] = "改成低机位"
    write_json(script_path, script)
    with pytest.raises(build_panel_jobs.ReferencePlanBlocked, match="stale"):
        build_panel_jobs.reference_plan_for_build(root, "第1话", plan)


def test_explicit_strong_emotion_without_expression_reference_blocks(tmp_path: Path) -> None:
    root = tmp_path / "work"
    make_fixture(root, "第1话", description="主角情绪爆发。")
    script_path = root / "脚本" / "第1话" / "panel_script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["panels"][0]["story_function"] = "emotional_peak"
    write_json(script_path, script)
    with pytest.raises(build_panel_jobs.ReferencePlanBlocked, match="strong_emotion_expression_reference_missing"):
        build_panel_jobs.build_jobs(root, "第1话")
