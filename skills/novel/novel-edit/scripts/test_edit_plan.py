#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import edit_plan


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def test_edit_plan_consumes_revision_balance_and_simulate_inputs():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "修订", "revision_plan.json"), {
            "kind": "novel_revision_plan",
            "inputs": {"pacing_signals": True, "reader_panel_signals": True},
            "tasks": [{
                "id": "PACING-CH07",
                "priority": "P1",
                "chapter": 7,
                "title": "节奏诊断：第7章 注水偏弱",
                "reason": "目标推进不足。",
                "source": "pacing_signals",
                "return_to_stage": "balance",
                "recommended_skill": "novel-balance",
            }],
        })
        write_json(os.path.join(root, "评分", "pacing_signals.json"), {
            "kind": "novel_pacing_signals",
            "chapters": [{
                "chapter": 8,
                "verdict": "🔴 三项皆低，弃书点风险",
                "reason": "冲突、信息、回收都弱。",
            }],
            "烂尾预警": {
                "回收率": 0.25,
                "超期伏笔数": 3,
                "烂尾级超期": 1,
                "through_chapter": 9,
            },
        })
        write_json(os.path.join(root, "评分", "reader_panel_signals.json"), {
            "analysis_mode": "signal_only",
            "signal_only": True,
            "qualitative_completed": False,
            "chapters_read": [1, 2, 3],
            "hook_strength": 0.2,
            "retention_prior": 0.31,
        })

        plan = edit_plan.build_plan(root)
        assert plan["inputs"]["revision_plan"] is True
        assert plan["inputs"]["pacing_signals"] is True
        assert plan["inputs"]["reader_panel_signals"] is True

        titles = {task["title"] for task in plan["tasks"]}
        assert "节奏诊断：第7章 注水偏弱" in titles
        assert any("弃书点风险" in title for title in titles)
        assert any("伏笔回收编辑排程" in title for title in titles)
        assert "合成叙事探针仅作人工复核假设" in titles
        assert any("合成留存代理偏低" in title for title in titles)
        probe_tasks = [task for task in plan["tasks"] if "合成留存代理偏低" in task["title"]]
        assert probe_tasks[0]["priority"] == "P2"


def test_edit_plan_writes_editorial_deliverables():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "审稿", "review_report.json"), {
            "findings": [{
                "severity": "blocking",
                "chapter": 1,
                "dimension": "plot",
                "problem": "主线冲突未成立",
                "fix_hint": "重写第一章目标和阻碍。",
            }],
        })
        plan = edit_plan.build_plan(root)
        edit_plan.write_editorial_letter(os.path.join(root, "修订", "editorial_letter.md"), plan)
        edit_plan.write_style_sheet(os.path.join(root, "修订", "style_sheet.md"), root)
        edit_plan.write_proof_checklist(os.path.join(root, "修订", "proof_checklist.md"), plan)

        for rel in ("修订/editorial_letter.md", "修订/style_sheet.md", "修订/proof_checklist.md"):
            assert os.path.exists(os.path.join(root, rel))


def test_close_edit_task_updates_plan_and_closure_log():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "修订", "edit_plan.json"), {
            "kind": "novel_edit_plan",
            "generated_at": "2026-07-08",
            "tasks": [{
                "id": "EDIT-001",
                "phase": "developmental_edit",
                "priority": "P0",
                "title": "主线冲突未成立",
                "status": "open",
            }],
        })

        task = edit_plan.close_edit_task(
            root,
            "EDIT-001",
            status="fixed",
            actor="editor-a",
            note="已重写第一章目标与阻碍。",
        )
        assert task["status"] == "fixed"
        assert task["closed_by"] == "editor-a"
        with open(os.path.join(root, "修订", "edit_plan.json"), encoding="utf-8") as f:
            payload = json.load(f)
        assert payload["tasks"][0]["closure_note"] == "已重写第一章目标与阻碍。"
        assert os.path.exists(os.path.join(root, "修订", "edit_task_closure.jsonl"))


def test_editor_query_log_can_be_answered():
    with tempfile.TemporaryDirectory() as root:
        query = edit_plan.add_editor_query(
            root,
            task_id="EDIT-001",
            question="这里是否必须保留悲剧结局？",
            severity="P1",
            asker="editor-a",
        )
        assert query["query_id"] == "EQ-001"
        assert edit_plan.open_editor_query_count(root) == 1

        answered = edit_plan.answer_editor_query(
            root,
            "EQ-001",
            answer="必须保留，但可以降低误伤读者的表达。",
            actor="author",
            status="answered",
        )
        assert answered["status"] == "answered"
        assert edit_plan.open_editor_query_count(root) == 0
        with open(os.path.join(root, "修订", "editor_queries.jsonl"), encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert lines[0]["answer_by"] == "author"
