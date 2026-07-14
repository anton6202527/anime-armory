#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("update_plan.py")
    spec = importlib.util.spec_from_file_location("comic_update_plan_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


update_plan = load_module()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_gate(root: Path, stage: str) -> None:
    scan = update_plan.PROGRESS_SCAN
    report_path = root / "生产数据" / f"comic_gate_{stage}_第1话.json"
    fingerprint = scan.stage_inputs_fingerprint(root, "第1话", stage)
    write_json(report_path, {
        "kind": "comic_gate", "chapter": "第1话", "stage": stage,
        "verdict": "pass", "summary": {"block_count": 0}, "findings": [],
        "inputs_fingerprint": fingerprint,
    })
    write_json(root / "生产数据" / "gate_receipts" / f"{stage}_第1话.json", {
        "kind": "comic_gate_receipt", "chapter": "第1话", "stage": stage,
        "verdict": "pass", "execution_authorized": True,
        "inputs_fingerprint_sha256": fingerprint["sha256"],
        "report_path": str(report_path.relative_to(root)),
        "report_sha256": scan.sha256_file(report_path),
    })


def make_current_contracts(project: Path) -> None:
    scan = update_plan.PROGRESS_SCAN
    (project / "_设置.md").write_text("- 传统原稿流程：启用\n", encoding="utf-8")
    contract = {
        "chapter": "第1话", "chapter_type": "one_shot", "format_profile": "vertical_serial",
        "source_mode": "original", "source_spans": [], "reader_promise": "promise",
        "core_conflict": "conflict", "turning_point": "turn", "payoff": "payoff",
        "ending_mode": "complete_closure", "budget": {"unit": "panels", "target": 1, "soft_range": [1, 2]},
        "status": "confirmed",
    }
    blueprint = {"kind": "comic_split_blueprint", "version": 2, "status": "confirmed", "chapters": [contract]}
    strategy = {"kind": "comic_adaptation_strategy", "version": 2, "status": "confirmed", "adaptation_boundary": "owned"}
    season = {"kind": "comic_season_arc", "version": 2, "status": "confirmed", "chapters": [{"chapter": "第1话"}]}
    write_json(project / "脚本" / "split_blueprint.json", blueprint)
    write_json(project / "开发包" / "adaptation_strategy.json", strategy)
    write_json(project / "开发包" / "season_arc.json", season)
    write_json(project / "脚本" / "第1话" / "panel_script.json", {
        "chapter_contract": {"chapter_contract_sha256": scan.canonical_sha256(contract), "status": "confirmed"},
        "visual_contract": {"style_baseline": "ink", "scene_anchors": {}}, "panels": [],
    })
    write_json(project / "开发包" / "signoff.json", {
        "reviewer": "editor", "role": "story_editor", "time": "2026-07-14T00:00:00Z",
        "file_sha256": {
            "adaptation_strategy": scan.sha256_file(project / "开发包" / "adaptation_strategy.json"),
            "season_arc": scan.sha256_file(project / "开发包" / "season_arc.json"),
            "split_blueprint": scan.sha256_file(project / "脚本" / "split_blueprint.json"),
        },
    })
    write_gate(project, "script")

    board = {
        "schema_version": 2, "kind": "comic_name_board", "workflow_status": "approved", "chapter": "第1话",
        "pages": [], "upstream_receipt": {
            "panel_script_sha256": scan.sha256_file(project / "脚本" / "第1话" / "panel_script.json"),
            "settings_sha256": scan.sha256_file(project / "_设置.md"),
        }, "validation": {"status": "pass", "errors": []}, "approval": {},
    }
    board["approval"] = {"status": "approved", "reviewed_by": "editor", "reviewed_at": "2026-07-14T00:00:00Z", "subject_sha256": scan._approval_subject_sha(board)}
    write_json(project / "排版" / "第1话" / "name_board.json", board)
    write_gate(project, "name")

    layout = {
        "schema_version": 2, "kind": "comic_layout", "workflow_status": "approved", "chapter": "第1话",
        "segments": [], "upstream_receipt": {
            "panel_script_sha256": scan.sha256_file(project / "脚本" / "第1话" / "panel_script.json"),
            "name_board_sha256": scan.sha256_file(project / "排版" / "第1话" / "name_board.json"),
            "settings_sha256": scan.sha256_file(project / "_设置.md"),
        }, "validation": {"status": "pass", "errors": []}, "approval": {},
    }
    layout["approval"] = {"status": "approved", "reviewed_by": "editor", "reviewed_at": "2026-07-14T00:00:00Z", "subject_sha256": scan._approval_subject_sha(layout)}
    write_json(project / "排版" / "第1话" / "layout.json", layout)
    write_gate(project, "layout")

    finishing = {
        "schema_version": 2, "kind": "comic_finishing_plan", "workflow_status": "validated", "chapter": "第1话",
        "panels": [], "validation": {"status": "pass", "errors": []}, "upstream_receipt": {
            "panel_script_sha256": scan.sha256_file(project / "脚本" / "第1话" / "panel_script.json"),
            "name_board_sha256": scan.sha256_file(project / "排版" / "第1话" / "name_board.json"),
            "layout_sha256": scan.sha256_file(project / "排版" / "第1话" / "layout.json"),
            "settings_sha256": scan.sha256_file(project / "_设置.md"),
        },
    }
    write_json(project / "出图" / "第1话" / "finishing" / "finishing_plan.json", finishing)
    write_gate(project, "finishing")

    write_json(project / "出图" / "共享" / "identity_registry.json", {"schema_version": 2, "kind": "comic_identity_registry", "assets": {}})
    write_json(project / "生产数据" / "comic_model_pack_report.json", {
        "kind": "comic_model_pack_report", "characters": [],
        "summary": {"characters": 0, "ready": 0, "needs_fix": 0, "needs_approval": 0},
    })
    input_paths = [
        project / "脚本" / "第1话" / "panel_script.json",
        project / "出图" / "共享" / "identity_registry.json",
        project / "生产数据" / "comic_memory_anchor_第1话.json",
        project / "_设置.md",
    ]
    plan = {
        "kind": "comic_reference_plan", "version": 2, "chapter": "第1话",
        "inputs": {"files": [{"path": str(path.relative_to(project)), "exists": path.is_file(), **({"sha256": scan.sha256_file(path)} if path.is_file() else {})} for path in input_paths]},
        "inputs_fingerprint": "inputs", "summary": {"block": 0, "panels_blocked": 0}, "panel_plans": [], "findings": [],
    }
    plan["plan_sha256"] = scan.canonical_sha256(plan)
    write_json(project / "生产数据" / "comic_reference_plan_第1话.json", plan)
    write_json(project / "出图" / "第1话" / "prompt" / "panel_jobs.json", {
        "schema_version": 2, "kind": "comic_panel_jobs", "chapter": "第1话",
        "reference_plan": {"plan_sha256": plan["plan_sha256"], "inputs_fingerprint": "inputs"}, "jobs": [],
    })
    write_json(project / "排版" / "第1话" / "lettering.json", {})
    write_json(project / "排版" / "第1话" / "export_manifest.json", {})
    for stage in ("image_preflight", "image", "compose", "review"):
        write_gate(project, stage)


def make_skill(root: Path, name: str, text: str = "x") -> None:
    skill = root / "skills" / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\n{text}\n", encoding="utf-8")


def make_project(root: Path) -> Path:
    project = root / "创作区" / "画漫画" / "测试漫画"
    (project / "脚本" / "第1话").mkdir(parents=True, exist_ok=True)
    (project / "排版" / "第1话").mkdir(parents=True, exist_ok=True)
    (project / "出图" / "第1话" / "prompt").mkdir(parents=True, exist_ok=True)
    (project / "生产数据").mkdir(parents=True, exist_ok=True)
    (project / "_meta.json").write_text(json.dumps({"title": "测试漫画"}, ensure_ascii=False), encoding="utf-8")
    (project / "_进度.md").write_text(
        "# 进度\n\n"
        "| 话 | 源本/企划 | 漫画脚本 | 页面排版 | 出图包 | 出图 | 嵌字合成 | 审查 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 第1话 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |\n",
        encoding="utf-8",
    )
    (project / "脚本" / "第1话" / "panel_script.json").write_text(
        json.dumps({"panels": [{"panel_id": "P001", "characters": ["CHAR_A"]}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (project / "排版" / "第1话" / "layout.json").write_text("{}", encoding="utf-8")
    (project / "出图" / "第1话" / "prompt" / "panel_jobs.json").write_text('{"jobs":[]}', encoding="utf-8")
    return project


def prepare_repo(tmp_path: Path) -> Path:
    for name in update_plan.SKILL_DEFAULT_STAGE:
        make_skill(tmp_path, name)
    update_plan.REPO_ROOT = str(tmp_path)
    update_plan.REPO_SKILLS = str(tmp_path / "skills")
    return tmp_path


def test_legacy_complete_project_rebuilds_from_script(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    plan = update_plan.build_plan(str(project))
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] == "script"
    assert "第1话" in [item["chapter"] for item in plan["affected_chapters"]]
    codes = {gap["code"] for gap in plan["structural_gaps"]}
    assert "visual_contract_missing" in codes
    assert "name_missing_or_invalid" in codes
    assert "finishing_plan_missing_or_invalid" in codes
    assert "split_blueprint_missing_or_invalid" in codes


def test_clean_project_records_no_rebuild(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    (project / "_进度.md").write_text(
        "# 进度\n\n"
        "| 话 | 源本/企划 | 漫画脚本 | 缩略分镜 | 页面排版 | 原稿收尾 | 出图包 | 出图 | 嵌字合成 | 审查 |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| 第1话 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |\n",
        encoding="utf-8",
    )
    make_current_contracts(project)
    update_plan.command_record(type("Args", (), {"project_root": str(project)})())
    plan = update_plan.build_plan(str(project))
    assert plan["rebuild_needed"] is False
    assert plan["structural_gaps"] == []


def test_changed_script_skill_rebuilds_from_script(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    (project / "_进度.md").write_text(
        "# 进度\n\n"
        "| 话 | 源本/企划 | 漫画脚本 | 缩略分镜 | 页面排版 | 原稿收尾 | 出图包 | 出图 | 嵌字合成 | 审查 |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| 第1话 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |\n",
        encoding="utf-8",
    )
    (project / "脚本" / "第1话" / "panel_script.json").write_text(
        json.dumps({"visual_contract": {"scene_anchors": {}}, "panels": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (project / "排版" / "第1话" / "name_board.json").write_text("{}", encoding="utf-8")
    (project / "出图" / "第1话" / "finishing").mkdir(parents=True, exist_ok=True)
    (project / "出图" / "第1话" / "finishing" / "finishing_plan.json").write_text("{}", encoding="utf-8")
    update_plan.command_record(type("Args", (), {"project_root": str(project)})())
    make_skill(tmp_path, "comic-script", "changed")
    plan = update_plan.build_plan(str(project))
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] == "script"
    assert "comic-script" in plan["changed_skills"]


def test_name_approval_content_change_replays_from_name(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    make_current_contracts(project)
    update_plan.command_record(type("Args", (), {"project_root": str(project)})())
    path = project / "排版" / "第1话" / "name_board.json"
    board = json.loads(path.read_text(encoding="utf-8"))
    board["editorial_note"] = "changed after approval"
    write_json(path, board)

    plan = update_plan.build_plan(str(project))

    assert plan["rerun_from"] == "name"
    assert plan["current_todo"]["skill"] == "comic-name"
    assert any(gap["code"] == "name_approval_stale" for gap in plan["structural_gaps"])
    commands = "\n".join(plan["commands"])
    assert "--submit-review" in commands
    assert "--approve --reviewed-by" in commands
    assert "--stage name" in commands


def test_missing_model_pack_report_routes_to_identity_and_image_jobs(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    make_current_contracts(project)
    registry_path = project / "出图" / "共享" / "identity_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["assets"]["CHAR_A"] = {
        "id": "CHAR_A", "type": "character", "library_tier": "core_full",
        "forms": {"FORM_BASE": {"id": "FORM_BASE"}},
        "outfits": {"OUTFIT_BASE": {"id": "OUTFIT_BASE"}},
        "expressions": {"EXPR_NEUTRAL": {"id": "EXPR_NEUTRAL"}},
        "states": {"STATE_BASE": {"id": "STATE_BASE"}},
        "default_binding": {
            "form_id": "FORM_BASE", "outfit_id": "OUTFIT_BASE",
            "expression_id": "EXPR_NEUTRAL", "state_id": "STATE_BASE",
        },
    }
    write_json(registry_path, registry)
    update_plan.command_record(type("Args", (), {"project_root": str(project)})())
    (project / "生产数据" / "comic_model_pack_report.json").unlink()

    plan = update_plan.build_plan(str(project))

    assert plan["rerun_from"] == "image_jobs"
    gap = next(item for item in plan["structural_gaps"] if item["code"] == "model_pack_report_missing_or_invalid")
    assert gap["next_skill"] == "comic-identity"
    assert plan["current_todo"]["skill"] == "comic-identity"


def test_reference_plan_input_change_is_a_minimal_image_jobs_replay(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    make_current_contracts(project)
    update_plan.command_record(type("Args", (), {"project_root": str(project)})())
    registry_path = project / "出图" / "共享" / "identity_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["note"] = "contract changed"
    write_json(registry_path, registry)

    plan = update_plan.build_plan(str(project))

    assert plan["rerun_from"] == "image_jobs"
    assert any(gap["code"] == "reference_plan_stale" for gap in plan["structural_gaps"])


def test_missing_review_receipt_only_reruns_review_gate(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    make_current_contracts(project)
    update_plan.command_record(type("Args", (), {"project_root": str(project)})())
    (project / "生产数据" / "gate_receipts" / "review_第1话.json").unlink()

    plan = update_plan.build_plan(str(project))

    assert plan["rerun_from"] == "review"
    assert [item["code"] for item in plan["structural_gaps"]] == ["review_gate_receipt_missing"]
    operational = [command for command in plan["commands"] if "update_plan.py record" not in command]
    assert operational == [f'python3 skills/comic-review/scripts/gate.py "{project}" --chapter 第1话 --stage review']


def test_current_review_receipt_supersedes_stale_earlier_receipts(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    make_current_contracts(project)
    update_plan.command_record(type("Args", (), {"project_root": str(project)})())
    early_path = project / "生产数据" / "gate_receipts" / "script_第1话.json"
    early = json.loads(early_path.read_text(encoding="utf-8"))
    early["inputs_fingerprint_sha256"] = "stale-on-purpose"
    early["execution_authorized"] = False
    write_json(early_path, early)

    plan = update_plan.build_plan(str(project))

    assert plan["structural_gaps"] == []
    assert plan["rebuild_needed"] is False


def test_stale_latest_review_receipt_replays_review_only(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    make_current_contracts(project)
    update_plan.command_record(type("Args", (), {"project_root": str(project)})())
    receipt_path = project / "生产数据" / "gate_receipts" / "review_第1话.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["inputs_fingerprint_sha256"] = "stale-on-purpose"
    write_json(receipt_path, receipt)

    plan = update_plan.build_plan(str(project))

    assert [item["code"] for item in plan["structural_gaps"]] == ["review_gate_receipt_stale"]
    assert plan["rerun_from"] == "review"
    operational = [command for command in plan["commands"] if "update_plan.py record" not in command]
    assert operational == [f'python3 skills/comic-review/scripts/gate.py "{project}" --chapter 第1话 --stage review']


def test_traditional_off_replay_keeps_name_but_skips_finishing(tmp_path: Path) -> None:
    prepare_repo(tmp_path)
    project = make_project(tmp_path)
    (project / "_设置.md").write_text("- 传统原稿流程：关闭\n", encoding="utf-8")

    plan = update_plan.build_plan(str(project))
    commands = "\n".join(plan["commands"])

    assert "comic-name/scripts/build_name_board.py" in commands
    assert "comic-finishing/scripts/build_finishing_plan.py" not in commands
    assert plan["progress"]["rows"][0]["stage_states"]["finishing"]["state"] == "not_applicable"
    assert "finishing" not in plan["progress"]["missing_stage_columns"]
