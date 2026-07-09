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
    assert "name_board_missing" in codes
    assert "finishing_plan_missing" in codes


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
    (project / "脚本" / "第1话" / "panel_script.json").write_text(
        json.dumps({"visual_contract": {"scene_anchors": {}}, "panels": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (project / "排版" / "第1话" / "name_board.json").write_text("{}", encoding="utf-8")
    (project / "出图" / "第1话" / "finishing").mkdir(parents=True, exist_ok=True)
    (project / "出图" / "第1话" / "finishing" / "finishing_plan.json").write_text("{}", encoding="utf-8")
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
