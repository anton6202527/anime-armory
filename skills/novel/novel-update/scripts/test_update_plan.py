#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import tempfile


def load_module():
    path = os.path.join(os.path.dirname(__file__), "update_plan.py")
    spec = importlib.util.spec_from_file_location("novel_update_plan_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


update_plan = load_module()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def fake_repo(root):
    skills = [
        "novel",
        "novel-craft",
        "novel-create",
        "novel-dashboard",
        "novel-progress",
        "novel-review",
        "novel-score",
        "novel-update",
    ]
    for skill in skills:
        skill_root = os.path.join(root, "skills", "novel")
        if skill != "novel":
            skill_root = os.path.join(skill_root, skill)
        write(os.path.join(skill_root, "SKILL.md"), f"---\nname: {skill}\n---\n# {skill}\n")
    update_plan.REPO_ROOT = root
    update_plan.REPO_SKILLS = os.path.join(root, "skills")


def matrix_project(root):
    write_json(os.path.join(root, "_meta.json"), {"title": "测试小说", "kind": "create"})
    write(os.path.join(root, "_进度.md"), """# 进度 — 《测试小说》

## 状态总览
<!-- novel-progress-schema: 1; kind: create -->

| 章节 | 标题 | 字数 | 大纲 | 细纲 | 正文初稿 | 机检 | 审稿 | 评分 | 改写 | 导出 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 第01章 | 开端 | 1200 | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ |

## 待办 / 记录
- [x] 项目初始化
""")


def checklist_project(root):
    write_json(os.path.join(root, "_meta.json"), {"title": "清单小说", "kind": "create"})
    write(os.path.join(root, "_进度.md"), """# 进度
<!-- novel-progress-schema: 1; kind: create -->

## 原创阶段（机器读）
<!-- novel-create-stage-table: 1; kind: create -->
- [x] 项目骨架 <!-- stage:setup -->
- [x] 创作蓝图 <!-- stage:blueprint -->
- [ ] 设定圣经 <!-- stage:setting_bible -->
""")


def test_check_missing_baseline_is_read_only_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        project = os.path.join(tmp, "project")
        fake_repo(repo)
        matrix_project(project)

        plan = update_plan.build_plan(project)

        assert plan["baseline_bootstrapped"] is False
        assert plan["needs_record"] is True
        assert plan["rebuild_needed"] is False
        assert not os.path.exists(os.path.join(project, "生产数据", "novel_skill_update_snapshot.json"))


def test_check_bootstrap_explicitly_writes_missing_baseline():
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        project = os.path.join(tmp, "project")
        fake_repo(repo)
        matrix_project(project)

        plan = update_plan.build_plan(project, bootstrap=True)

        assert plan["baseline_bootstrapped"] is True
        assert plan["needs_record"] is False
        assert os.path.exists(os.path.join(project, "生产数据", "novel_skill_update_snapshot.json"))


def test_changed_review_skill_triggers_rework_up_to_current_stage():
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        project = os.path.join(tmp, "project")
        fake_repo(repo)
        matrix_project(project)

        update_plan.command_record(type("Args", (), {"project_root": project})())
        write(os.path.join(repo, "skills", "novel", "novel-review", "SKILL.md"), "---\nname: novel-review\n---\n# changed\n")

        plan = update_plan.build_plan(project)

        assert "novel-review" in plan["changed_skills"]
        assert plan["current_stage"] == "human_review"
        assert plan["rebuild_needed"] is True
        assert plan["rerun_from"] == "mechanical_review"
        assert plan["rerun_until"] == "human_review"


def test_observe_only_skill_change_does_not_rebuild_text():
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        project = os.path.join(tmp, "project")
        fake_repo(repo)
        matrix_project(project)

        update_plan.command_record(type("Args", (), {"project_root": project})())
        write(os.path.join(repo, "skills", "novel", "novel-dashboard", "SKILL.md"), "---\nname: novel-dashboard\n---\n# changed\n")

        plan = update_plan.build_plan(project)

        assert "novel-dashboard" in plan["changed_skills"]
        assert plan["observe_only_changed_skills"] == ["novel-dashboard"]
        assert plan["rebuild_needed"] is False


def test_stage_checklist_progress_is_supported():
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        project = os.path.join(tmp, "project")
        fake_repo(repo)
        checklist_project(project)

        plan = update_plan.build_plan(project)

        assert plan["progress"]["schema"] == "stage_checklist"
        assert plan["current_stage"] == "blueprint"
        assert plan["current_todo"]["stage_key"] == "setting"
