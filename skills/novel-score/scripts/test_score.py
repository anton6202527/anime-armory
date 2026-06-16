#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for novel-score automation engine."""
import unittest
import os
import json
import shutil
import sys
import tempfile
from datetime import date

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
            {"dimension": "retention", "raw_score": 10, "evidence": "...", "comment": "...", "improve_by": "..."}
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
        # 书名体检：19/25 且未撞名 → 不换名，也不路由 novel-title
        self.assertEqual(report["title_check"]["title"], "Test Book")
        self.assertEqual(report["title_check"]["total"], 19)
        self.assertFalse(report["title_check"]["needs_rename"])
        self.assertEqual(report["title_check"]["collision"]["status"], "unchecked")
        self.assertNotIn("novel-title", [a["recommended_skill"] for a in report["next_actions"]])

    def test_n2d_target_gets_adapt_decision(self):
        with open(os.path.join(self.tmp, "_设置.md"), "w", encoding="utf-8") as f:
            f.write("# 设置\n- 目标平台：红果\n- 输出格式：txt,docx,n2d\n")
        task = self.generate_score_task()
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
        self.assertEqual(report["production_decision"]["decision"], "n2d-adapt")
        self.assertEqual(report["next_actions"][0]["recommended_skill"], "n2d")

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
            "date": "2026-06-08",
            "source": "第三方榜单",
            "summary": "仙侠复仇仍在上升。",
            "url": "https://example.com/rank",
        }]
        freshness = score.baseline_freshness(baseline)
        self.assertFalse(freshness["blocking"])
        self.assertEqual(freshness["status"], "fresh")

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
    """选题→投放→反哺选题闭环：读 n2d-feedback 写的题材战绩库做第一方先验。"""

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
        self.assertIn("n2d-feedback", score.first_party_genre_text(None))

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
