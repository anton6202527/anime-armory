#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import revision_planner as rp
from reader_probe import build_reader_probe_snapshot


def test_revision_plan_merges_review_score_feedback_and_simulate():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("第一章正文。")
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
            json.dump({
                "schema_version": 3,
                "kind": "novel_synthetic_reader_probe",
                "scope": "opening",
                "chapters_read": [1],
                "source_snapshot": build_reader_probe_snapshot(root, "opening"),
                "surface_signals": {},
                "signal_only": True,
                "analysis_mode": "surface_signals_only",
            }, f)

        plan = rp.build_plan(root)
        ids = {task["id"] for task in plan["tasks"]}
        assert {"REV-001", "SCORE-VERDICT", "FEEDBACK-CH02", "EXPERIMENT-hook", "SIMULATE-SIGNAL-ONLY"} <= ids
        json_path, md_path = rp.write_plan(root, plan)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)


def test_revision_plan_stale_simulate_only_requests_rerun():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        chapter_path = os.path.join(root, "章节", "第01章.md")
        with open(chapter_path, "w", encoding="utf-8") as f:
            f.write("第一版正文。")
        with open(os.path.join(root, "评分", "reader_panel_signals.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 3,
                "kind": "novel_synthetic_reader_probe",
                "scope": "chapter",
                "scope_chapter": 1,
                "chapters_read": [1],
                "source_snapshot": build_reader_probe_snapshot(root, "chapter", 1),
                "surface_signals": {"cliche_terms": {"literal_hits": 88}},
                "signal_only": True,
            }, f)
        with open(chapter_path, "a", encoding="utf-8") as f:
            f.write("正文已修改。")
        tasks = rp.tasks_from_simulate(root)
        assert len(tasks) == 1
        assert tasks[0]["id"] == "SIMULATE-STALE"
        assert "当前信号值不进入修订计划" in tasks[0]["reason"]
        assert "88" not in tasks[0]["reason"]


def test_revision_plan_legacy_simulate_freshness_unknown():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "评分", "reader_panel_signals.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 2,
                "kind": "novel_synthetic_reader_probe",
                "signal_only": True,
                "retention_prior": 0.1,
            }, f)
        tasks = rp.tasks_from_simulate(root)
        assert len(tasks) == 1
        assert tasks[0]["id"] == "SIMULATE-FRESHNESS-UNKNOWN"
        assert "新鲜度未知" in tasks[0]["title"]
        assert "0.1" not in tasks[0]["reason"]


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


def test_kill_verdict_does_not_override_evidence_backed_review_p0():
    """主观评分不得降级审稿中可复核的 P0。"""
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
        assert by_id["REV-001"]["priority"] == "P0"
        assert "已降级" not in by_id["REV-001"]["title"]
        assert by_id["SCORE-VERDICT"]["priority"] == "P1"
        assert plan["kill_verdict_demotions"] == 0


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
    """证据优先级明确时自动保留 P0 review，不再无谓等待人工。"""
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
        assert not rev.get("conflict")
        assert not bal.get("conflict")
        assert bal["status"] == "superseded"
        assert bal["superseded_by"] == rev["id"]
        assert rev["auto_resolution"]["decision"] == "auto_evidence_advantage"
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
        assert not rev.get("conflict")
        assert pacing["status"] == "superseded"
        assert pacing["superseded_by"] == rev["id"]
        assert pacing["auto_resolution"]["winner"] == rev["id"]


def test_tier_classification_and_macro_first_discipline():
    import revision_planner as rp
    tasks = [
        rp._task("REV-001", "review_report", "第3章主线结构崩塌需要重排", priority="P0",
                 chapter=3, stage="rewrite"),
        rp._task("REV-002", "review_report", "第3章过滤词密度过高需要润色", priority="P1",
                 chapter=3, stage="review"),
        rp._task("REV-003", "review_report", "第5章钩子偏弱", priority="P1",
                 chapter=5, stage="review"),
    ]
    summary = rp.apply_tier_discipline(tasks)
    by_id = {t["id"]: t for t in tasks}
    assert by_id["REV-001"]["tier"] == "structure"
    assert by_id["REV-002"]["tier"] == "line"
    assert by_id["REV-003"]["tier"] == "scene"
    # 存在未决结构级 P0 → 行文级任务标缓办
    assert by_id["REV-002"].get("deferred_until_structure") is True
    assert summary["deferred_line_tasks"] == 1 and summary["structure_open"] is True
    # 同优先级内 structure 排在 line 前
    ids = [t["id"] for t in tasks]
    assert ids.index("REV-001") < ids.index("REV-002")


def test_no_structure_open_line_not_deferred():
    import revision_planner as rp
    tasks = [rp._task("REV-001", "review_report", "第2章行文润色·文风统一", priority="P2",
                      chapter=2, stage="review")]
    summary = rp.apply_tier_discipline(tasks)
    assert tasks[0]["tier"] == "line"
    assert "deferred_until_structure" not in tasks[0]
    assert summary["structure_open"] is False
