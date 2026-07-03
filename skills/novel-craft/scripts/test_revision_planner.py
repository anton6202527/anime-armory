#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import revision_planner as rp


def test_revision_plan_merges_review_score_feedback_and_simulate():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": [{
                "problem": "第1章钩子弱",
                "blocking": True,
                "affected_files": ["章节/第01章.md"],
                "recommended_skill": "novel-rewrite",
                "return_to_stage": "rewrite",
            }]}, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "score_report.json"), "w", encoding="utf-8") as f:
            json.dump({"verdict": "大改", "rewrite_roi": "high", "next_actions": []}, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "reader_telemetry_summary.json"), "w", encoding="utf-8") as f:
            json.dump({
                "weakest_chapters": [2],
                "experiments": {"best_by_ab_test": [{
                    "ab_test_id": "hook",
                    "variant_id": "A",
                    "take_ids": ["take-a"],
                }]},
            }, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "reader_panel_signals.json"), "w", encoding="utf-8") as f:
            json.dump({"signal_only": True, "analysis_mode": "signal_only"}, f)

        plan = rp.build_plan(root)
        ids = {task["id"] for task in plan["tasks"]}
        assert {"REV-001", "SCORE-VERDICT", "FEEDBACK-CH02", "EXPERIMENT-hook", "SIMULATE-SIGNAL-ONLY"} <= ids
        json_path, md_path = rp.write_plan(root, plan)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)


def test_revision_plan_consumes_pacing_signals_schema():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "评分", "pacing_signals.json"), "w", encoding="utf-8") as f:
            json.dump({
                "kind": "novel_pacing_signals",
                "chapters": [{
                    "chapter": 7,
                    "verdict": "注水偏弱",
                    "reason": "目标推进不足，重复解释过多。",
                }],
                "烂尾预警": {
                    "回收率": 0.33,
                    "超期伏笔数": 2,
                    "烂尾级超期": 1,
                    "through_chapter": 9,
                },
            }, f, ensure_ascii=False)

        plan = rp.build_plan(root)
        ids = {task["id"] for task in plan["tasks"]}
        assert {"PACING-CH07", "PACING-ENDRISK-SUMMARY"} <= ids
        assert plan["inputs"]["pacing_signals"] is True
        by_id = {task["id"]: task for task in plan["tasks"]}
        assert by_id["PACING-CH07"]["recommended_skill"] == "novel-balance"
        assert by_id["PACING-ENDRISK-SUMMARY"]["chapter"] == 9


def test_revision_plan_consumes_market_evidence_tasks_and_jobs():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "评分", "market_evidence_tasks.json"), "w", encoding="utf-8") as f:
            json.dump({
                "kind": "novel_market_evidence_tasks",
                "tasks": [{
                    "priority": "P1",
                    "title": "补齐红果证据",
                    "recommended_skill": "novel-research",
                    "return_to_stage": "market_baseline",
                    "reason": "coverage gap",
                }],
            }, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "market_evidence_jobs.json"), "w", encoding="utf-8") as f:
            json.dump({"kind": "novel_market_evidence_jobs", "jobs": [{"id": "MARKET-SEARCH-001"}]}, f)

        plan = rp.build_plan(root)
        ids = {task["id"] for task in plan["tasks"]}
        assert {"MARKET-EVIDENCE-001", "MARKET-EVIDENCE-JOBS"} <= ids
        assert plan["inputs"]["market_evidence_tasks"] is True
        assert plan["inputs"]["market_evidence_jobs"] is True


def test_kill_verdict_demotes_non_score_p0():
    """评分结论为「弃稿重立」时，非评分来源的 P0 应降为 P2。"""
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        # review_report：1 个 P0（blocking）
        with open(os.path.join(root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": [{
                "problem": "第3章主线矛盾",
                "blocking": True,
                "affected_files": ["章节/第03章.md"],
                "recommended_skill": "novel-rewrite",
                "return_to_stage": "rewrite",
            }]}, f, ensure_ascii=False)
        # score_report：「弃稿重立」
        with open(os.path.join(root, "评分", "score_report.json"), "w", encoding="utf-8") as f:
            json.dump({
                "verdict": "弃稿重立", "rewrite_roi": "low",
                "next_actions": [{"action": "重做方向设定", "recommended_skill": "novel-create",
                                  "return_to_stage": "direction_spec", "priority": "P0"}],
            }, f, ensure_ascii=False)

        plan = rp.build_plan(root)
        by_id = {task["id"]: task for task in plan["tasks"]}
        # review P0 应降级
        assert by_id["REV-001"]["priority"] == "P2", "非评分 P0 应降为 P2"
        assert "[已降级" in by_id["REV-001"]["title"]
        assert by_id["REV-001"]["resolution"]["type"] == "score_kill_demotes_non_score_p0"
        # score P0 不变
        assert by_id["SCORE-VERDICT"]["priority"] == "P0", "评分 P0 不应降级"
        assert plan["kill_verdict_demotions"] >= 1
        assert any(
            item["resolution"]["type"] == "score_kill_demotes_non_score_p0"
            for item in plan["conflict_summary"]
        )


def test_kill_verdict_does_not_demote_non_p0():
    """弃稿重立不应影响 P1/P2 任务。"""
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": [{
                "problem": "第2章节奏偏慢",
                "blocking": False,
                "affected_files": ["章节/第02章.md"],
                "recommended_skill": "novel-review",
                "return_to_stage": "review",
            }]}, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "score_report.json"), "w", encoding="utf-8") as f:
            json.dump({"verdict": "弃稿重立", "rewrite_roi": "low", "next_actions": []}, f, ensure_ascii=False)

        plan = rp.build_plan(root)
        by_id = {task["id"]: task for task in plan["tasks"]}
        assert by_id["REV-001"]["priority"] == "P1", "非阻塞 review 不应降级"


def test_conflict_detection_review_vs_balance():
    """review 和 balance 对同一章给出不同 return_to_stage 时应标记冲突。"""
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": [{
                "problem": "第5章主线偏题",
                "blocking": True,
                "affected_files": ["章节/第05章.md"],
                "recommended_skill": "novel-rewrite",
                "return_to_stage": "rewrite",
            }]}, f, ensure_ascii=False)
        # balance 对同一章建议返回 review
        with open(os.path.join(root, "审稿", "balance_findings.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": [{
                "message": "第5章节奏坍塌",
                "blocking": True,
                "chapter": 5,
                "recommended_skill": "novel-balance",
                "return_to_stage": "balance",
            }]}, f, ensure_ascii=False)

        plan = rp.build_plan(root)
        by_id = {task["id"]: task for task in plan["tasks"]}
        rev = by_id["REV-001"]
        bal = by_id["BALANCE-balance_findings.json-001"]
        assert rev.get("conflict"), "review 任务应标记冲突"
        assert bal.get("conflict"), "balance 任务应标记冲突"
        assert bal["id"] in rev.get("conflict_with", []), "应交叉引用对方 ID"
        assert rev["conflict_resolution"]["decision"] == "hold_for_editor_arbitration"
        assert any(
            item["resolution"]["type"] == "cross_source_stage_conflict"
            and item["task_id"] == "REV-001"
            for item in plan["conflict_summary"]
        )


def test_conflict_detection_review_vs_pacing():
    """pacing 任务 source 为 'pacing_signals'（不含 'balance'）——是 balance 侧主力
    信号，必须能与 review 在同一章触发跨源冲突，否则节奏冲突永远漏检。"""
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": [{
                "problem": "第7章主线偏题",
                "blocking": True,
                "affected_files": ["章节/第07章.md"],
                "recommended_skill": "novel-rewrite",
                "return_to_stage": "rewrite",
            }]}, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "pacing_signals.json"), "w", encoding="utf-8") as f:
            json.dump({
                "kind": "novel_pacing_signals",
                "chapters": [{"chapter": 7, "verdict": "注水过慢", "reason": "信息回报低"}],
            }, f, ensure_ascii=False)

        plan = rp.build_plan(root)
        by_id = {task["id"]: task for task in plan["tasks"]}
        rev = by_id["REV-001"]
        pacing = by_id["PACING-CH07"]
        assert rev.get("conflict"), "review 任务应与 pacing 标记冲突"
        assert pacing.get("conflict"), "pacing 任务应标记冲突"
        assert pacing["id"] in rev.get("conflict_with", []), "应交叉引用 pacing 任务 ID"
        assert pacing["conflict_resolution"]["winner"] == "manual_editor_review"
