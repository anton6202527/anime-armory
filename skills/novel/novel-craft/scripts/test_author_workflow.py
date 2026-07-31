#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import author_workflow


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def touch(path, text="x\n"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def test_author_workflow_reports_next_step_and_writes_artifacts():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        touch(os.path.join(root, "_设置.md"), "# 设置\n文本主创模式：AI辅助\n")
        touch(os.path.join(root, "_进度.md"), "# 进度\n")

        payload = author_workflow.build_workflow(root)
        assert payload["kind"] == "novel_author_workflow"
        assert payload["current_step"] == "blueprint"
        assert payload["steps"][0]["status"] == "done"

        json_path, md_path = author_workflow.write_workflow(root, payload)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)


def test_author_workflow_reaches_release_when_manifest_ready():
    with tempfile.TemporaryDirectory() as root:
        for rel in ["_设置.md", "_进度.md", "设定/创作蓝图.md", "设定/读者契约.md", "设定/角色卡.md"]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书"})
        write_json(os.path.join(root, "设定", "author_intent.json"), {
            "kind": "novel_author_intent",
            "core_theme": "信任需要承担代价",
            "non_negotiables": ["主角不牺牲无辜者换胜利"],
        })
        write_json(os.path.join(root, "设定", "scene_cards.json"), {"kind": "novel_scene_cards", "scenes": []})
        write_json(os.path.join(root, "审稿", "demo_gate.json"), {"status": "passed"})
        touch(os.path.join(root, "章节", "第01章.md"))
        write_json(os.path.join(root, "审稿", "state_ledger.json"), {"chapter_deltas": {}})
        write_json(os.path.join(root, "审稿", "review_report.json"), {"findings": []})
        write_json(os.path.join(root, "评分", "reader_telemetry_summary.json"), {"weakest_chapters": []})
        write_json(os.path.join(root, "修订", "edit_plan.json"), {"tasks": []})
        for rel in ["修订/editorial_letter.md", "修订/style_sheet.md", "修订/proof_checklist.md"]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "导出", "release_manifest.json"), {"release_ready": True})

        payload = author_workflow.build_workflow(root)
        assert payload["current_step"] == "evidence"
        evidence_step = [s for s in payload["steps"] if s["key"] == "evidence"][0]
        assert evidence_step["status"] == "warning"


def test_author_workflow_reads_blockers_from_reports():
    with tempfile.TemporaryDirectory() as root:
        for rel in [
            "_设置.md",
            "_进度.md",
            "设定/创作蓝图.md",
            "设定/读者契约.md",
            "设定/角色卡.md",
            "资料/research_sources.json",
        ]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        write_json(os.path.join(root, "设定", "scene_cards.json"), {"kind": "novel_scene_cards", "scenes": []})
        write_json(os.path.join(root, "审稿", "demo_gate.json"), {"status": "passed"})
        touch(os.path.join(root, "章节", "第01章.md"))
        write_json(os.path.join(root, "审稿", "state_ledger.json"), {"chapter_deltas": {}})
        write_json(os.path.join(root, "审稿", "review_report.json"), {
            "summary": {"blocking_count": 1, "verdict": "needs_work"},
            "findings": [{"blocking": True, "problem": "主线冲突未成立"}],
        })
        write_json(os.path.join(root, "评分", "score_report.json"), {
            "production_decision": {"decision": "revise"},
            "verdict": "小改",
        })

        payload = author_workflow.build_workflow(root)
        review_step = [s for s in payload["steps"] if s["key"] == "review_score"][0]
        assert review_step["status"] == "pending"
        assert any("review_report" in item or "主线冲突" in item for item in review_step["blockers"])
        md = author_workflow.render_markdown(payload)
        assert "阻断" in md
        assert "主线冲突未成立" in md


def test_author_workflow_accepts_scoped_reader_data_waiver():
    with tempfile.TemporaryDirectory() as root:
        for rel in [
            "_设置.md",
            "_进度.md",
            "设定/创作蓝图.md",
            "设定/读者契约.md",
            "设定/角色卡.md",
            "资料/research_sources.json",
        ]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        write_json(os.path.join(root, "设定", "scene_cards.json"), {"kind": "novel_scene_cards", "scenes": []})
        write_json(os.path.join(root, "审稿", "demo_gate.json"), {"status": "passed"})
        touch(os.path.join(root, "章节", "第01章.md"))
        write_json(os.path.join(root, "审稿", "state_ledger.json"), {"chapter_deltas": {}})
        write_json(os.path.join(root, "审稿", "review_report.json"), {"summary": {"blocking_count": 0}, "findings": []})
        write_json(os.path.join(root, "评分", "score_report.json"), {"production_decision": {"decision": "go"}, "verdict": "pass"})
        write_json(os.path.join(root, "评分", "reader_test_plan.json"), {"kind": "novel_reader_test_plan"})
        with open(os.path.join(root, "审稿", "waiver_log.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "reader_data_missing",
                "reason": "封闭项目无读者数据。",
                "scope": {"release_profile": "platform_publish"},
            }, ensure_ascii=False) + "\n")

        payload = author_workflow.build_workflow(root)
        reader_step = [s for s in payload["steps"] if s["key"] == "reader_validation"][0]
        assert reader_step["status"] == "warning"
        assert reader_step["blockers"] == []
        assert "waiver" in reader_step["warnings"][0]


def test_author_workflow_blocks_open_editor_queries():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书"})
        write_json(os.path.join(root, "修订", "edit_plan.json"), {"tasks": []})
        for rel in ["修订/editorial_letter.md", "修订/style_sheet.md", "修订/proof_checklist.md"]:
            touch(os.path.join(root, rel))
        os.makedirs(os.path.join(root, "修订"), exist_ok=True)
        with open(os.path.join(root, "修订", "editor_queries.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "query_id": "QUERY-001",
                "task_id": "EDIT-001",
                "status": "open",
                "question": "结局是否保留牺牲？",
            }, ensure_ascii=False) + "\n")

        payload = author_workflow.build_workflow(root)
        edit_step = [s for s in payload["steps"] if s["key"] == "edit"][0]
        assert edit_step["status"] == "pending"
        assert "editor query" in edit_step["blockers"][0]
