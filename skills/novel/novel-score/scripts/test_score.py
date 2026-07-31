#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for novel-score automation engine."""
import unittest
import os
import json
import shutil
import sys
import tempfile
from datetime import date, timedelta

import score


def valid_assessment(score_task_id=None):
    payload = {
        "scores": [
            {"dimension": "topic_heat", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."},
            {"dimension": "opening_hook", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."},
            {"dimension": "payoff_density", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."},
            {"dimension": "character_power", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."},
            {"dimension": "plot_structure", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."},
            {"dimension": "prose", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."},
            {"dimension": "retention", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."},
            {"dimension": "novelty", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."}
        ],
        "deductions": [
            {"item": "Boring", "points": -5, "reason": "Too slow"}
        ],
        "title_check": {
            "scores": {"hook": 4, "platform_fit": 4, "character_identity": 3,
                       "anti_collision": 4, "memorability": 4},
            "comment": "书名贴平台、有钩子",
            "needs_rename": False,
        },
        "adaptation_check": {
            "scores": {"visual_scene": 4, "hook_cinematic": 4, "conflict_intensity": 3,
                       "episodic_beat": 3, "ip_freshness": 3},
            "comment": "可视化场景多、冲突浓，适合短剧改编",
            "low_potential": False,
        },
    }
    if score_task_id:
        payload["score_task_id"] = score_task_id
    return payload


class TestNovelScore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.score_dir = os.path.join(self.tmp, "评分")
        self.chapters_dir = os.path.join(self.tmp, "章节")
        os.makedirs(self.score_dir)
        os.makedirs(self.chapters_dir)
        
        with open(os.path.join(self.tmp, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "Test Book", "genre": "Fantasy"}, f)
        with open(os.path.join(self.score_dir, f"market_baseline_{date.today().isoformat()}.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_market_baseline",
                "baseline_date": date.today().isoformat(),
                "target_platform": "红果/抖音 商业爽文向",
                "expires_after_days": 21,
                "sources": [{"platform": "红果短剧", "url": "https://example.com", "status": "ok", "signals": ["仙侠"]}],
            }, f)
        with open(os.path.join(self.score_dir, f"题材热榜_{date.today().isoformat()}.md"), "w", encoding="utf-8") as f:
            f.write("# test baseline\n")
            
        with open(os.path.join(self.chapters_dir, "第01章.md"), "w", encoding="utf-8") as f:
            f.write("# 第01章 Start\nOnce upon a time...")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def generate_score_task(self, extra=None):
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp] + (extra or [])
        try:
            score.main()
        finally:
            sys.argv = old_argv
        task_path = os.path.join(self.score_dir, "score_task.json")
        self.assertTrue(os.path.exists(task_path))
        with open(task_path, encoding="utf-8") as f:
            return json.load(f)

    def test_calculation_logic(self):
        task = self.generate_score_task()
        mock_assessment = valid_assessment(task["score_task_id"])
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock_assessment, f)
            
        # Run main logic (simulated)
        import sys
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            score.main()
        finally:
            sys.argv = old_argv
            
        report_path = os.path.join(self.score_dir, "score_report.json")
        self.assertTrue(os.path.exists(report_path))
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
            
        # 100 - 5 = 95
        self.assertEqual(report["total_score"], 95.0)
        self.assertEqual(report["tier"], "爆款潜力")
        self.assertEqual(report["verdict"], "过")
        self.assertEqual(report["production_decision"]["decision"], "go")
        self.assertEqual(report["score_task_id"], task["score_task_id"])
        self.assertEqual(report["source_snapshot"]["kind"], "novel_text_snapshot")
        self.assertEqual(len(report["source_snapshot"]["files"]), 1)
        self.assertEqual(report["market_baseline"]["baseline_path"], f"评分/题材热榜_{date.today().isoformat()}.md")
        self.assertEqual(report["market_baseline"]["sources"][0]["platform"], "红果短剧")
        self.assertIn("judge_bias_advisory", report)
        self.assertEqual(report["judge_bias_advisory"]["score_adjustment"], 0)
        # 书名体检：19/25 且未撞名 → 不换名，也不路由 novel-title
        self.assertEqual(report["title_check"]["title"], "Test Book")
        self.assertEqual(report["title_check"]["total"], 19)
        self.assertFalse(report["title_check"]["needs_rename"])
        self.assertEqual(report["title_check"]["collision"]["status"], "unchecked")
        self.assertNotIn("novel-title", [a["recommended_skill"] for a in report["next_actions"]])

    def test_visual_target_stays_with_novel_decision(self):
        with open(os.path.join(self.tmp, "_设置.md"), "w", encoding="utf-8") as f:
            f.write("# 设置\n- 目标平台：红果\n- 输出格式：txt,docx\n")
        task = self.generate_score_task()
        self.assertIn("短剧改编潜力体检", task["assessment_prompt"])
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(valid_assessment(task["score_task_id"]), f, ensure_ascii=False)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            score.main()
        finally:
            sys.argv = old_argv
        with open(os.path.join(self.score_dir, "score_report.json"), encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["production_decision"]["decision"], "go")
        self.assertNotIn("external-adaptation", [a["recommended_skill"] for a in report["next_actions"]])

    def test_low_adaptation_potential_routes_to_condense(self):
        with open(os.path.join(self.tmp, "_设置.md"), "w", encoding="utf-8") as f:
            f.write("# 设置\n- 目标平台：红果\n- 输出格式：txt,docx\n")
        task = self.generate_score_task()
        mock = valid_assessment(task["score_task_id"])
        mock["adaptation_check"]["scores"] = {k: 2 for k, _ in score.ADAPTATION_CHECK_DIMENSIONS}
        mock["adaptation_check"]["low_potential"] = False
        mock["adaptation_check"]["comment"] = "镜头钩子和单元节拍不足"
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock, f, ensure_ascii=False)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            score.main()
        finally:
            sys.argv = old_argv
        with open(os.path.join(self.score_dir, "score_report.json"), encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["adaptation_check"]["total"], 10)
        actions = [a for a in report["next_actions"] if a.get("dimension") == "adaptation_check"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["priority"], "must")
        self.assertEqual(actions[0]["recommended_skill"], "novel-condense")

    def test_reader_telemetry_is_injected_and_reported(self):
        telemetry = {
            "schema_version": 1,
            "kind": "novel_reader_telemetry_summary",
            "generated_at": date.today().isoformat(),
            "platform": "红果测试",
            "latest_source_name": "小流量",
            "records_ingested": 3,
            "aggregate": {
                "chapter_count": 1,
                "total_starts": 100,
                "total_completes": 40,
                "total_drops": 45,
                "completion_rate": 0.4,
                "drop_rate": 0.45,
                "total_comments": 2,
            },
            "weakest_chapters": [1],
            "chapters": [{
                "chapter": 1,
                "completion_rate": 0.4,
                "drop_rate": 0.45,
                "flags": ["low_completion", "high_drop"],
            }],
        }
        with open(os.path.join(self.score_dir, "reader_telemetry_summary.json"), "w", encoding="utf-8") as f:
            json.dump(telemetry, f, ensure_ascii=False)
        task = self.generate_score_task()
        self.assertIn("真实读者反馈", task["assessment_prompt"])
        self.assertIn("总完读率 0.4", task["assessment_prompt"])
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(valid_assessment(task["score_task_id"]), f, ensure_ascii=False)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            score.main()
        finally:
            sys.argv = old_argv
        with open(os.path.join(self.score_dir, "score_report.json"), encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["reader_telemetry_path"], "评分/reader_telemetry_summary.json")
        self.assertEqual(report["reader_telemetry_summary"]["aggregate"]["drop_rate"], 0.45)
        self.assertEqual(report["pre_reader_feedback_score"], 95.0)
        self.assertEqual(report["reader_feedback_adjustment"]["points"], -7.0)
        self.assertEqual(report["total_score"], 88.0)
        self.assertTrue(any("真实完读率" in item for item in report["reader_feedback_adjustment"]["reasons"]))

    def test_reader_feedback_adjustment_uses_panel_and_ab_with_cap(self):
        adjustment = score.compute_reader_feedback_adjustment(
            reader_panel={"retention_prior": 0.35, "cliche_density_per_kchar": 4.5},
            ab_take_results={"winner": "B", "completion_uplift": -0.12, "confidence": "high"},
        )
        self.assertEqual(adjustment["raw_points"], -6.0)
        self.assertEqual(adjustment["points"], -6.0)
        self.assertEqual(adjustment["ab_take_results_summary"]["winner"], "B")

    def test_repetition_prior_feeds_reader_feedback_adjustment(self):
        # 跨章重复先验（确定性机检）→ retention 负向调分 + 留痕 source/reason
        adjustment = score.compute_reader_feedback_adjustment(
            repetition_prior={
                "summary": {"adjacent_max_jaccard": 0.30, "mechanical_opener_groups": 1,
                            "repeated_sentences": 4},
                "prior": {"level": "high", "points": -3,
                          "reasons": ["相邻章最高近重复 30%：注水/套模板，弃读风险"]},
            })
        self.assertEqual(adjustment["points"], -3.0)
        self.assertIn(score.REPETITION_PRIOR_SOURCE, adjustment["sources"])
        self.assertTrue(any("跨章重复机检先验" in r for r in adjustment["reasons"]))

    def test_repetition_prior_none_is_noop(self):
        adjustment = score.compute_reader_feedback_adjustment(repetition_prior=None)
        self.assertEqual(adjustment["points"], 0.0)
        self.assertNotIn(score.REPETITION_PRIOR_SOURCE, adjustment["sources"])

    def test_repetition_prior_text_injected_for_judge(self):
        self.assertIn("章节不足", score.repetition_prior_text(None))
        txt = score.repetition_prior_text({
            "summary": {"adjacent_max_jaccard": 0.22, "mechanical_opener_groups": 0,
                        "repeated_sentences": 0, "sentence_start_token_groups": 2,
                        "short_sentence_templates": 1, "low_chapter_compression_count": 2,
                        "compression_ratio": 0.32},
            "prior": {"level": "elevated", "points": -2,
                      "reasons": ["相邻章最高近重复 22%（≥18%）：注水/套模板，弃读风险"]},
        })
        self.assertIn("22%", txt)
        self.assertIn("短句式模板 1", txt)
        self.assertIn("低压缩章节 2", txt)
        self.assertIn("负向先验", txt)

    def test_prompt_and_advisory_are_length_format_neutral(self):
        task = self.generate_score_task()
        prompt = task["assessment_prompt"]
        self.assertIn("只评**内容质量本身**", prompt)
        self.assertIn("排版/markdown", prompt)
        self.assertIn("长度/篇幅相近时以内容质量为先", prompt)
        samples = [
            {"content": "# 第1章\n" + "\n".join(["- 事件推进"] * 20) + "\n" + ("他向前走。" * 900)},
            {"content": "# 第2章\n" + ("她停下脚步。" * 120)},
        ]
        adv = score.presentation_bias_advisory(samples)
        self.assertEqual(adv["level"], "review")
        self.assertEqual(adv["score_adjustment"], 0)
        self.assertEqual(adv["raw_score_adjustment"], 0)
        self.assertTrue(any("格式" in r or "长度" in r or "篇幅" in r for r in adv["reasons"]))

    def test_reference_distribution_percentile_reported(self):
        samples = []
        for total, raw in [(50, 5), (80, 8), (100, 10)]:
            samples.append({
                "title": f"sample-{total}",
                "rights_status": "original",
                "total_score": total,
                "scores": {dim: raw for dim, _label in score.DIMENSIONS},
            })
        with open(os.path.join(self.score_dir, "reference_distribution_2026-01-01.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_reference_score_distribution",
                "title": "测试参考分布",
                "sample_count": len(samples),
                "samples": samples,
            }, f, ensure_ascii=False)
        task = self.generate_score_task()
        self.assertIn("参考分布", task["assessment_prompt"])
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(valid_assessment(task["score_task_id"]), f, ensure_ascii=False)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            score.main()
        finally:
            sys.argv = old_argv
        with open(os.path.join(self.score_dir, "score_report.json"), encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["benchmark_percentile"]["status"], "ok")
        self.assertEqual(report["benchmark_percentile"]["sample_count"], 3)
        self.assertEqual(report["benchmark_percentile"]["total_score_percentile"], 66.7)

    def test_assessment_must_match_score_task(self):
        self.generate_score_task()
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(valid_assessment("wrong-task-id"), f)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            with self.assertRaises(SystemExit) as cm:
                score.main()
            self.assertEqual(cm.exception.code, 2)
        finally:
            sys.argv = old_argv

    def test_full_score_task_detects_added_chapter(self):
        task = self.generate_score_task(["--scope", "full"])
        with open(os.path.join(self.chapters_dir, "第02章.md"), "w", encoding="utf-8") as f:
            f.write("# 第02章 New\nA newly added chapter.")
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(valid_assessment(task["score_task_id"]), f)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--scope", "full", "--mock-assessment", mock_path]
        try:
            with self.assertRaises(SystemExit) as cm:
                score.main()
            self.assertEqual(cm.exception.code, 2)
        finally:
            sys.argv = old_argv

    def test_tier_verdict(self):
        self.assertEqual(score.get_tier_verdict(90), ("爆款潜力", "过", "high"))
        self.assertEqual(score.get_tier_verdict(75), ("合格偏上", "小改", "high"))
        self.assertEqual(score.get_tier_verdict(60), ("及格线下", "大改", "medium"))
        self.assertEqual(score.get_tier_verdict(40), ("不及格", "弃稿重立", "low"))

    def test_minor_next_actions_are_not_hard_rewrite_routes(self):
        processed = [
            {"dimension": "topic_heat", "raw_score": 8.2, "weight": 20},
            {"dimension": "plot_structure", "raw_score": 8.0, "weight": 12},
            {"dimension": "prose", "raw_score": 8.2, "weight": 8},
        ]
        actions = score.build_next_actions("小改", processed)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["priority"], "should")
        self.assertEqual(actions[0]["recommended_skill"], "novel-review")
        self.assertIn("压缩支线", actions[0]["action"])
        self.assertNotIn("重做题材", actions[0]["action"])

    def test_adaptation_check_low_potential_threshold(self):
        # 5 维各 2 分 = 10/25 < 15 → low_potential
        low = score.build_adaptation_check({
            "scores": {k: 2 for k, _ in score.ADAPTATION_CHECK_DIMENSIONS},
            "comment": "场景偏静、冲突弱", "low_potential": False,
        })
        self.assertTrue(low["low_potential"])
        self.assertEqual(low["total"], 10)
        # 5 维各 4 分 = 20/25 ≥ 15 → 不低
        ok = score.build_adaptation_check({
            "scores": {k: 4 for k, _ in score.ADAPTATION_CHECK_DIMENSIONS},
            "comment": "可改编", "low_potential": False,
        })
        self.assertFalse(ok["low_potential"])

    def test_validate_requires_adaptation_when_short_drama(self):
        assessment = valid_assessment("tid")
        assessment.pop("adaptation_check")
        errors = score.validate_assessment(assessment, expect_adaptation=True)
        self.assertTrue(any("adaptation_check" in e for e in errors))
        # 非短剧目标时不强制
        errors2 = score.validate_assessment(assessment, expect_adaptation=False)
        self.assertFalse(any("adaptation_check" in e for e in errors2))

    def test_is_short_drama_target_reads_settings_and_meta(self):
        self.assertTrue(score.is_short_drama_target({"目标平台": "红果"}, {}))
        self.assertTrue(score.is_short_drama_target({}, {"target_platform": "抖音漫剧"}))
        self.assertFalse(score.is_short_drama_target({"目标平台": "起点"}, {"genre": "Fantasy"}))

    def test_chapter_sort_uses_numeric_chapter_order(self):
        paths = [
            os.path.join(self.chapters_dir, "第10章.md"),
            os.path.join(self.chapters_dir, "第2章.md"),
            os.path.join(self.chapters_dir, "第01章.md"),
        ]
        ordered = sorted(paths, key=score.chapter_sort_key)
        self.assertEqual(
            [os.path.basename(path) for path in ordered],
            ["第01章.md", "第2章.md", "第10章.md"],
        )

    def test_stale_baseline_blocks_scoring(self):
        stale = "2000-01-01"
        with open(os.path.join(self.score_dir, f"market_baseline_{stale}.json"), "w", encoding="utf-8") as f:
            json.dump({
                "baseline_date": stale,
                "expires_after_days": 1,
                "sources": [{"platform": "old", "status": "ok", "signals": ["旧题材"]}],
            }, f)
        with open(os.path.join(self.score_dir, f"题材热榜_{stale}.md"), "w", encoding="utf-8") as f:
            f.write("# stale baseline\n")
        os.remove(os.path.join(self.score_dir, f"market_baseline_{date.today().isoformat()}.json"))
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", os.path.join(self.tmp, "missing.json")]
        try:
            with self.assertRaises(SystemExit) as cm:
                score.main()
            self.assertEqual(cm.exception.code, 2)
        finally:
            sys.argv = old_argv

    def test_baseline_without_effective_evidence_blocks_scoring(self):
        baseline_path = os.path.join(self.score_dir, f"market_baseline_{date.today().isoformat()}.json")
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_market_baseline",
                "baseline_date": date.today().isoformat(),
                "target_platform": "红果/抖音 商业爽文向",
                "expires_after_days": 21,
                "sources": [{"platform": "test", "status": "fetch_error", "signals": []}],
                "notes": [],
            }, f)
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump({"scores": [], "deductions": []}, f)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            with self.assertRaises(SystemExit) as cm:
                score.main()
            self.assertEqual(cm.exception.code, 2)
        finally:
            sys.argv = old_argv

    def test_unstructured_baseline_notes_do_not_count_as_effective_evidence(self):
        baseline = score.find_latest_baseline(self.tmp)
        baseline["sources"] = [{"platform": "test", "status": "fetch_error", "signals": []}]
        baseline["notes"] = ["2026-06-08 人工核验红果榜：仙侠复仇仍在上升。"]
        freshness = score.baseline_freshness(baseline)
        self.assertTrue(freshness["blocking"])
        self.assertEqual(freshness["status"], "no_evidence")

    def test_manual_baseline_evidence_counts_as_effective_evidence(self):
        baseline = score.find_latest_baseline(self.tmp)
        baseline["sources"] = [{"platform": "test", "status": "fetch_error", "signals": []}]
        baseline["manual_evidence"] = [{
            "platform": "红果短剧",
            # 相对今日的新鲜日期（21 天窗口内）——硬编固定日期会随 wall-clock 走过期变 flaky
            "date": (date.today() - timedelta(days=5)).isoformat(),
            "source": "第三方榜单",
            "summary": "仙侠复仇仍在上升。",
            "url": "https://example.com/rank",
        }]
        freshness = score.baseline_freshness(baseline)
        self.assertFalse(freshness["blocking"])
        self.assertEqual(freshness["status"], "fresh")

    def test_stale_manual_evidence_blocks_even_with_fresh_baseline_date(self):
        baseline = score.find_latest_baseline(self.tmp)
        baseline["baseline_date"] = date.today().isoformat()
        baseline["sources"] = [{"platform": "test", "status": "fetch_error", "signals": []}]
        baseline["manual_evidence"] = [{
            "platform": "红果短剧",
            "date": "2024-01-01",
            "source": "第三方榜单",
            "summary": "旧榜单显示某题材热。",
            "url": "https://example.com/old",
        }]
        freshness = score.baseline_freshness(baseline)
        self.assertTrue(freshness["blocking"])
        self.assertEqual(freshness["status"], "evidence_stale")

    def test_future_manual_evidence_does_not_count_as_fresh(self):
        baseline = score.find_latest_baseline(self.tmp)
        baseline["baseline_date"] = date.today().isoformat()
        baseline["sources"] = [{"platform": "test", "status": "fetch_error", "signals": []}]
        baseline["manual_evidence"] = [{
            "platform": "红果短剧",
            "date": (date.today() + timedelta(days=1)).isoformat(),
            "source": "第三方榜单",
            "summary": "未来日期不应提前算作新鲜证据。",
            "url": "https://example.com/future",
        }]
        freshness = score.baseline_freshness(baseline)
        self.assertTrue(freshness["blocking"])
        self.assertEqual(freshness["status"], "evidence_stale")

    def test_short_drama_target_requires_fresh_short_drama_coverage(self):
        baseline = score.find_latest_baseline(self.tmp)
        baseline["baseline_date"] = date.today().isoformat()
        baseline["sources"] = [{"platform": "番茄小说", "status": "ok", "signals": ["网文榜新鲜"]}]
        baseline["manual_evidence"] = [{
            "platform": "红果短剧",
            "date": "2024-01-01",
            "source": "第三方榜单",
            "summary": "旧榜单显示红果短剧题材热。",
            "url": "https://example.com/old",
        }]
        freshness = score.baseline_freshness(baseline)
        self.assertTrue(freshness["blocking"])
        self.assertEqual(freshness["status"], "coverage_gap")

    def test_quarter_old_short_drama_evidence_passes_coverage(self):
        # 红果/抖音漫剧 平台覆盖靠按月·季发布的行业证据：季度内（COVERAGE_EVIDENCE_MAX_AGE_DAYS）
        # 的真实证据应满足覆盖闸，不应被 21 天日榜窗口卡成 coverage_gap → 长期 stale-waiver。
        today = date.today()
        baseline = score.find_latest_baseline(self.tmp)
        baseline["baseline_date"] = today.isoformat()
        baseline["sources"] = [{"platform": "番茄小说", "status": "ok", "signals": ["网文榜新鲜"]}]
        baseline["manual_evidence"] = [{
            "platform": "红果短剧",
            "date": (today - timedelta(days=60)).isoformat(),
            "source": "QuestMobile行业报告",
            "summary": "红果短剧月活3亿+，系统流题材放量。",
            "url": "https://example.com/q",
        }]
        freshness = score.baseline_freshness(baseline)
        self.assertEqual(freshness["status"], "fresh")
        self.assertFalse(freshness["blocking"])

    def test_missing_baseline_markdown_blocks_scoring(self):
        md_path = os.path.join(self.score_dir, f"题材热榜_{date.today().isoformat()}.md")
        os.remove(md_path)
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump({"scores": [], "deductions": []}, f)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            with self.assertRaises(SystemExit) as cm:
                score.main()
            self.assertEqual(cm.exception.code, 2)
        finally:
            sys.argv = old_argv

    def test_allow_stale_baseline_records_waiver(self):
        stale = "2000-01-01"
        with open(os.path.join(self.score_dir, f"market_baseline_{stale}.json"), "w", encoding="utf-8") as f:
            json.dump({
                "baseline_date": stale,
                "expires_after_days": 1,
                "sources": [{"platform": "old", "status": "ok", "signals": ["旧题材"]}],
            }, f)
        with open(os.path.join(self.score_dir, f"题材热榜_{stale}.md"), "w", encoding="utf-8") as f:
            f.write("# stale baseline\n")
        os.remove(os.path.join(self.score_dir, f"market_baseline_{date.today().isoformat()}.json"))
        mock_path = os.path.join(self.tmp, "mock.json")
        task = self.generate_score_task(["--allow-stale-baseline"])
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(valid_assessment(task["score_task_id"]), f)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path, "--allow-stale-baseline"]
        try:
            score.main()
        finally:
            sys.argv = old_argv
        with open(os.path.join(self.score_dir, "score_report.json"), encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["waivers"][0]["type"], "score_baseline_freshness")
        self.assertEqual(report["waivers"][0]["scope"]["baseline_date"], stale)
        self.assertEqual(report["waivers"][0]["scope"]["freshness_status"], "expired")
        self.assertTrue(report["market_baseline"]["freshness"]["blocking"])
        with open(os.path.join(self.tmp, "审稿", "waiver_log.jsonl"), encoding="utf-8") as f:
            self.assertIn("score_baseline_freshness", f.read())

    def test_validate_assessment_requires_all_dimensions(self):
        errors = score.validate_assessment({
            "scores": [{"dimension": "topic_heat", "raw_score": 11}],
            "deductions": [{"item": "bad", "points": 1}],
        })
        self.assertTrue(any("raw_score" in e for e in errors))
        self.assertTrue(any("缺少评分维度" in e for e in errors))
        self.assertTrue(any("points" in e for e in errors))
        self.assertTrue(any("evidence" in e for e in errors))
        self.assertTrue(any("comment" in e for e in errors))
        self.assertTrue(any("improve_by" in e for e in errors))

    def test_judges_panel_validation_optional_and_shape_checked(self):
        # 不给 judges_panel → 单判官，合法（向后兼容）
        self.assertEqual(score.validate_assessment(valid_assessment()), [])
        # 给了但形状错 → 报错
        bad = valid_assessment()
        bad["judges_panel"] = {"评委A": {"topic_heat": 99, "unknown_dim": 5}}
        errors = score.validate_assessment(bad)
        self.assertTrue(any("1-10" in e for e in errors))
        self.assertTrue(any("未知维度" in e for e in errors))

    def test_apply_judge_debias_single_judge_disabled(self):
        out = score.apply_judge_debias(valid_assessment(), [])
        self.assertFalse(out["enabled"])  # 无 panel → 不做去偏，不改分
        self.assertEqual(out["method"], "single_judge")

    def test_apply_judge_debias_same_family_is_persona_panel_low_confidence(self):
        assessment = valid_assessment()
        assessment["judges_panel"] = {
            "商业编辑判官": {"retention": 8, "opening_hook": 8},
            "短剧制片判官": {"retention": 8, "opening_hook": 8},
            "审稿质检判官": {"retention": 8, "opening_hook": 8},
        }
        assessment["judge_families"] = {
            "商业编辑判官": "openai",
            "短剧制片判官": "openai",
            "审稿质检判官": "openai",
        }
        processed = [{"dimension": "retention"}, {"dimension": "opening_hook"}]
        out = score.apply_judge_debias(assessment, processed)
        self.assertTrue(out["enabled"])
        self.assertEqual(out["method"], "persona_panel")
        self.assertEqual(out["confidence"], "low")
        self.assertEqual(out["family_diversity"]["families_count"], 1)
        self.assertIn("persona_panel", out["note"])
        self.assertNotIn("dual-judge", out["note"])
        self.assertTrue(all(p["judge_confidence"] == "low" for p in processed))
        self.assertTrue(all(p["judge_decision"] == "review" for p in processed))

    def test_apply_judge_debias_flags_high_variance_dimension(self):
        assessment = valid_assessment()
        # 两判官在 opening_hook 上分歧极大（9 vs 2 → stdev>1）→ 低信心
        assessment["judges_panel"] = {
            "gpt-5": {"opening_hook": 9, "retention": 8},
            "claude-sonnet": {"opening_hook": 2, "retention": 8},
        }
        processed = [{"dimension": "opening_hook"}, {"dimension": "retention"}]
        out = score.apply_judge_debias(assessment, processed)
        self.assertTrue(out["enabled"])
        self.assertEqual(out["method"], "judge_panel")
        low_dims = {d["dimension"] for d in out["low_confidence_dimensions"]}
        self.assertIn("opening_hook", low_dims)
        self.assertNotIn("retention", low_dims)
        self.assertIn("opening_hook", {d["dimension"] for d in out["abstain_dimensions"]})
        self.assertEqual(out["escalation_actions"][0]["decision"], "abstain")
        self.assertFalse(out["family_diversity"]["meets_recommended"])
        # 注入到 processed_scores（advisory，不动 raw_score）
        hook = next(p for p in processed if p["dimension"] == "opening_hook")
        self.assertEqual(hook["judge_confidence"], "low")
        self.assertEqual(hook["judge_decision"], "abstain")
        self.assertNotIn("raw_score", hook)  # 没有改/造分

    def test_apply_judge_debias_three_families_recommended(self):
        assessment = valid_assessment()
        assessment["judges_panel"] = {
            "judge_a": {"retention": 8},
            "judge_b": {"retention": 8},
            "judge_c": {"retention": 8},
        }
        assessment["judge_families"] = {
            "judge_a": "openai",
            "judge_b": "anthropic",
            "judge_c": "google",
        }
        out = score.apply_judge_debias(assessment, [{"dimension": "retention"}])
        self.assertTrue(out["family_diversity"]["meets_recommended"])
        self.assertIn("≥3", out["note"])

    def test_validate_assessment_requires_title_check_when_title_set(self):
        payload = valid_assessment()
        del payload["title_check"]
        errors = score.validate_assessment(payload, expect_title_check=True)
        self.assertTrue(any("title_check" in e for e in errors))
        # 书名未定时可省略
        self.assertEqual(score.validate_assessment(payload, expect_title_check=False), [])

    def test_validate_assessment_checks_title_check_shape(self):
        payload = valid_assessment()
        payload["title_check"] = {
            "scores": {"hook": 6, "platform_fit": 3, "unknown_dim": 2},
            "comment": "",
            "needs_rename": "yes",
        }
        errors = score.validate_assessment(payload, expect_title_check=True)
        self.assertTrue(any("hook 必须是 1-5" in e for e in errors))
        self.assertTrue(any("未知维度：unknown_dim" in e for e in errors))
        self.assertTrue(any("缺少维度：anti_collision" in e for e in errors))
        self.assertTrue(any("comment 不能为空" in e for e in errors))
        self.assertTrue(any("needs_rename 必须是 bool" in e for e in errors))

    def test_weak_title_routes_to_novel_title(self):
        task = self.generate_score_task()
        mock = valid_assessment(task["score_task_id"])
        # 总分 10/25 < 阈值 15 → needs_rename，路由 novel-title
        mock["title_check"]["scores"] = {"hook": 2, "platform_fit": 2, "character_identity": 2,
                                         "anti_collision": 2, "memorability": 2}
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock, f, ensure_ascii=False)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            score.main()
        finally:
            sys.argv = old_argv
        with open(os.path.join(self.score_dir, "score_report.json"), encoding="utf-8") as f:
            report = json.load(f)
        self.assertTrue(report["title_check"]["needs_rename"])
        title_actions = [a for a in report["next_actions"] if a["recommended_skill"] == "novel-title"]
        self.assertEqual(len(title_actions), 1)
        self.assertEqual(title_actions[0]["dimension"], "title_check")

    def test_hard_collision_forces_rename(self):
        settings_dir = os.path.join(self.tmp, "设定")
        os.makedirs(settings_dir)
        with open(os.path.join(settings_dir, "书名撞名检查_2026-06-01.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_title_collision_check",
                "generated_at": "2026-06-01",
                "candidates": [{"candidate": "Test Book", "status": "hard_collision",
                                "collisions": [{"strength": "hard", "match": "Test Book"}]}],
            }, f, ensure_ascii=False)
        task = self.generate_score_task()
        mock = valid_assessment(task["score_task_id"])  # 5维高分也压不住硬撞名
        mock_path = os.path.join(self.tmp, "mock.json")
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(mock, f, ensure_ascii=False)
        old_argv = sys.argv
        sys.argv = ["score.py", self.tmp, "--mock-assessment", mock_path]
        try:
            score.main()
        finally:
            sys.argv = old_argv
        with open(os.path.join(self.score_dir, "score_report.json"), encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["title_check"]["collision"]["status"], "hard_collision")
        self.assertTrue(report["title_check"]["needs_rename"])
        self.assertIn("novel-title", [a["recommended_skill"] for a in report["next_actions"]])

    def test_build_title_check_threshold(self):
        tc = {"scores": {"hook": 3, "platform_fit": 3, "character_identity": 3,
                         "anti_collision": 3, "memorability": 3},
              "comment": "平", "needs_rename": False}
        # 15/25 恰好达线 → 不换名
        self.assertFalse(score.build_title_check(tc, "书名", None)["needs_rename"])
        tc["scores"]["hook"] = 2
        self.assertTrue(score.build_title_check(tc, "书名", None)["needs_rename"])
        # 无书名 → 无体检块
        self.assertIsNone(score.build_title_check(tc, None, None))


class TestFirstPartyGenrePrior(unittest.TestCase):
    """选题→投放→反哺选题闭环：读题材战绩库做第一方先验。"""

    def _records(self):
        return [
            {"kind": "genre_performance_record", "genre": "仙侠", "subgenres": ["复仇"],
             "metrics": {"retention_3s": 0.62, "follow_next_rate": 0.34, "roi": 1.3, "plays": 800000}},
            {"kind": "genre_performance_record", "genre": "仙侠", "subgenres": ["马甲"],
             "metrics": {"retention_3s": 0.50, "follow_next_rate": 0.20, "roi": 0.8, "plays": 200000}},
            {"kind": "genre_performance_record", "genre": "都市",
             "metrics": {"retention_3s": 0.70, "roi": 2.0, "plays": 500000}},
        ]

    def test_genre_match_weighted_aggregate(self):
        s = score.summarize_first_party_genre(self._records(), "仙侠")
        self.assertEqual(s["release_count"], 2)
        self.assertEqual(s["total_plays"], 1000000)
        # (0.62*800000 + 0.50*200000)/1000000 = 0.596
        self.assertAlmostEqual(s["metrics"]["retention_3s"], 0.596, places=4)
        self.assertAlmostEqual(s["metrics"]["roi"], 1.2, places=4)
        self.assertEqual(s["subgenres"], ["复仇", "马甲"])

    def test_genre_miss_falls_back_to_whole_library(self):
        s = score.summarize_first_party_genre(self._records(), "玄幻")
        self.assertIn("全库", s["genre"])
        self.assertEqual(s["release_count"], 3)

    def test_empty_ledger_returns_loop_hint(self):
        self.assertIsNone(score.summarize_first_party_genre([], "仙侠"))
        self.assertIn("回灌", score.first_party_genre_text(None))

    def test_ledger_roundtrip_jsonl(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "genre_ledger.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for r in self._records():
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.write("\n")  # 空行容错
                f.write("not-a-genre-record\n")  # 脏行容错
            loaded = score.load_genre_ledger(path)
            self.assertEqual(len(loaded), 3)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
