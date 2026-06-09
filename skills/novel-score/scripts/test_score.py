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
        ]
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
                "sources": [{"platform": "test", "url": "https://example.com", "status": "ok", "signals": ["仙侠"]}],
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
        self.assertEqual(report["score_task_id"], task["score_task_id"])
        self.assertEqual(report["source_snapshot"]["kind"], "novel_text_snapshot")
        self.assertEqual(len(report["source_snapshot"]["files"]), 1)
        self.assertEqual(report["market_baseline"]["baseline_path"], f"评分/题材热榜_{date.today().isoformat()}.md")
        self.assertEqual(report["market_baseline"]["sources"][0]["platform"], "test")

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

    def test_manual_baseline_notes_count_as_effective_evidence(self):
        baseline = score.find_latest_baseline(self.tmp)
        baseline["sources"] = [{"platform": "test", "status": "fetch_error", "signals": []}]
        baseline["notes"] = ["2026-06-08 人工核验红果榜：仙侠复仇仍在上升。"]
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
