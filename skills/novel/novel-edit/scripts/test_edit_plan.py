#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import edit_plan
from reader_probe import build_reader_probe_snapshot


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def test_edit_plan_consumes_revision_balance_and_simulate_inputs():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        for chapter in (1, 2, 3):
            with open(os.path.join(root, "章节", f"第{chapter:02d}章.md"), "w", encoding="utf-8") as f:
                f.write(f"第{chapter}章正文。")
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
            "schema_version": 3,
            "analysis_mode": "surface_signals_only",
            "signal_only": True,
            "qualitative_completed": False,
            "scope": "opening",
            "chapters_read": [1, 2, 3],
            "source_snapshot": build_reader_probe_snapshot(root, "opening"),
            "surface_signals": {
                "hook_tail_markers": {"literal_marker_hits": 2},
                "lexical_4gram": {"unique_cjk_4gram_count": 18, "cjk_4gram_count": 24},
                "cliche_terms": {"literal_hits": 1},
            },
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
        assert not any("合成留存代理" in title for title in titles)
        probe_tasks = [task for task in plan["tasks"] if task["title"] == "合成叙事探针仅作人工复核假设"]
        assert probe_tasks[0]["priority"] == "P2"
        assert "章尾标记字面命中 2 次" in probe_tasks[0]["reason"]
        assert "未经校准" in probe_tasks[0]["reason"]


def test_edit_plan_stale_probe_only_requests_rerun_without_current_values():
    with tempfile.TemporaryDirectory() as root:
        chapter_dir = os.path.join(root, "章节")
        os.makedirs(chapter_dir, exist_ok=True)
        chapter_path = os.path.join(chapter_dir, "第01章.md")
        with open(chapter_path, "w", encoding="utf-8") as f:
            f.write("第一版正文。")
        write_json(os.path.join(root, "评分", "reader_panel_signals.json"), {
            "schema_version": 3,
            "kind": "novel_synthetic_reader_probe",
            "scope": "chapter",
            "scope_chapter": 1,
            "chapters_read": [1],
            "signal_only": True,
            "source_snapshot": build_reader_probe_snapshot(root, "chapter", 1),
            "surface_signals": {
                "hook_tail_markers": {"literal_marker_hits": 99},
                "lexical_4gram": {"unique_cjk_4gram_count": 9, "cjk_4gram_count": 10},
                "cliche_terms": {"literal_hits": 77},
            },
        })
        with open(chapter_path, "a", encoding="utf-8") as f:
            f.write("正文已经修改。")
        plan = edit_plan.build_plan(root)
        tasks = [task for task in plan["tasks"] if task["source"] == "评分/reader_panel_signals.json"]
        assert len(tasks) == 1
        assert tasks[0]["title"] == "合成叙事探针已过期，需重跑"
        assert "当前信号值不进入编辑计划" in tasks[0]["reason"]
        assert "99" not in tasks[0]["reason"]
        assert "77" not in tasks[0]["reason"]


def test_edit_plan_legacy_probe_freshness_is_unknown():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "评分", "reader_panel_signals.json"), {
            "schema_version": 2,
            "kind": "novel_synthetic_reader_probe",
            "signal_only": True,
            "retention_prior": 0.2,
        })
        plan = edit_plan.build_plan(root)
        tasks = [task for task in plan["tasks"] if task["source"] == "评分/reader_panel_signals.json"]
        assert len(tasks) == 1
        assert tasks[0]["title"] == "旧版合成叙事探针新鲜度未知"
        assert "0.2" not in tasks[0]["reason"]


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


def test_edit_plan_keeps_authenticity_read_author_controlled():
    with tempfile.TemporaryDirectory() as root:
        auth_path = os.path.join(root, "修订", "authenticity_read.json")
        payload = {
            "kind": "novel_authenticity_read",
            "required_for_release": True,
            "status": "planned",
            "scope": ["目标场景"],
            "reviewer": {"fit_statement": "熟悉本次场景语境"},
            "findings": [],
        }
        write_json(auth_path, payload)

        required = edit_plan.build_plan(root)
        tasks = [task for task in required["tasks"] if "真实性/文化审读" in task["title"]]
        assert required["inputs"]["authenticity_read"] is True
        assert tasks and {task["priority"] for task in tasks} == {"P1"}
        assert all(task["priority"] != "P0" for task in tasks)

        payload["required_for_release"] = False
        write_json(auth_path, payload)
        optional = edit_plan.build_plan(root)
        tasks = [task for task in optional["tasks"] if "真实性/文化审读" in task["title"]]
        assert tasks and {task["priority"] for task in tasks} == {"P2"}


def test_edit_plan_respects_flexible_craft_profile_without_forcing_six_fields():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
            f.write("# 设置\n- 创作工艺档：literary\n")
        write_json(os.path.join(root, "设定", "scene_cards.json"), {
            "kind": "novel_scene_cards",
            "scenes": [{
                "id": "SC-01",
                "chapter": 1,
                "viewpoint": "一位不可靠的旁观者",
                "motif_return": "生锈的站牌在三次离别里改变含义",
            }],
        })

        plan = edit_plan.build_plan(root)
        scene_tasks = [task for task in plan["tasks"] if "SC-01" in task["title"]]
        assert not any(task["priority"] == "P1" for task in scene_tasks)
        assert not any("人工复核场景叙事功能" in task["title"] for task in scene_tasks)

        packet = edit_plan.write_line_edit_packet(root, plan, 1)
        with open(packet, encoding="utf-8") as f:
            text = f.read()
        assert "当前创作工艺档：`literary`" in text
        assert "已登记叙事功能" in text
        assert "意象复现=生锈的站牌在三次离别里改变含义" in text
        assert "转折/价值变化" not in text


def test_edit_plan_fails_closed_for_unsupported_custom_craft_profile():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
            f.write("# 设置\n- 创作工艺档：hybrid_lyric\n")
        write_json(os.path.join(root, "设定", "scene_cards.json"), {
            "kind": "novel_scene_cards",
            "scenes": [{"id": "SC-X", "chapter": 1}],
        })

        plan = edit_plan.build_plan(root)
        tasks = [task for task in plan["tasks"] if "创作工艺档缺编辑适配" in task["title"]]
        assert tasks and tasks[0]["priority"] == "P1"
        assert not any("SC-X" in task["title"] and "契约字段" in task["title"] for task in plan["tasks"])

        packet = edit_plan.write_line_edit_packet(root, plan, 1)
        with open(packet, encoding="utf-8") as f:
            text = f.read()
        assert "自定义工艺档缺 editor adapter" in text
        assert "转折/价值变化" not in text


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
