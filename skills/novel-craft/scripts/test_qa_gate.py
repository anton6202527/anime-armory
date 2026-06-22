#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA gate tests. Can run without pytest."""
import json
import os
import tempfile
import unittest
import hashlib

import qa_gate
from report_snapshot import snapshot_chapters, snapshot_files
from settings import normalize_setting_value
from waivers import baseline_freshness_scope, make_waiver, append_waiver


def write_chapter(root, text="# 第1章\n正文\n"):
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    chapter = os.path.join(root, "章节", "第01章.md")
    with open(chapter, "w", encoding="utf-8") as f:
        f.write(text)
    return chapter


def valid_review_report(root, **extra):
    payload = {
        "schema_version": 1,
        "kind": "novel_review_report",
        "project_root": os.path.abspath(root),
        "generated_at": "2026-06-09",
        "scope": {"mode": "full"},
        "source_snapshot": snapshot_chapters(root, mode="review:full"),
        "summary": {
            "blocking_count": 0,
            "suggestion_count": 0,
            "polish_count": 0,
            "waiver_count": 0,
            "verdict": "pass",
        },
        "mechanical_findings_path": "审稿/mechanical_findings.json",
        "waivers": [],
        "findings": [],
        "next_actions": [],
    }
    payload.update(extra)
    return payload


def valid_score_report(root, chapter, freshness=None, **extra):
    freshness = freshness or {"status": "fresh", "blocking": False, "reason": ""}
    payload = {
        "schema_version": 1,
        "kind": "novel_score_report",
        "project_root": os.path.abspath(root),
        "generated_at": "2026-06-09",
        "target_platform": "商业爽文向",
        "score_task_id": "task-1",
        "score_task_path": "评分/score_task.json",
        "assessment_prompt_hash": "hash-1",
        "scope": {"mode": "opening", "chapter_count": 1},
        "source_snapshot": snapshot_files(root, [chapter], mode="score:opening"),
        "market_baseline": {"freshness": freshness},
        "scores": [],
        "deductions": [],
        "total_score": 90,
        "tier": "爆款潜力",
        "verdict": "过",
        "production_decision": {
            "decision": "go",
            "route": "novel-review",
            "reason": "评分达标",
            "score": 90,
            "verdict": "过",
        },
        "rewrite_roi": "high",
        "waivers": [],
        "next_actions": [],
    }
    payload.update(extra)
    return payload


def write_state_closure(root, chapter_num=1):
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    delta_path = os.path.join(root, "审稿", f"state_delta_第{chapter_num:02d}章.json")
    with open(delta_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_state_delta",
            "chapter": chapter_num,
        }, f, ensure_ascii=False)
    chapter_path = os.path.join(root, "章节", f"第{chapter_num:02d}章.md")
    verification = {
        "chapter": chapter_num,
        "status": "passed",
        "chapter_file_hash": file_sha256(chapter_path),
        "delta_hash": file_sha256(delta_path),
    }
    with open(os.path.join(root, "审稿", "state_ledger.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_state_ledger",
            "chapter_deltas": {f"chapter_{chapter_num:02d}": {"merged": True, "verification": verification}},
        }, f, ensure_ascii=False)


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_ai_usage(root, text_mode="AI-generated", human_contribution="人工完成创意、改写、审稿取舍。"):
    os.makedirs(os.path.join(root, "合规"), exist_ok=True)
    with open(os.path.join(root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_ai_usage",
            "generated_at": "2026-06-21",
            "project_root": os.path.abspath(root),
            "title": "测试书",
            "publish_target": "红果",
            "human_contribution": human_contribution,
            "rights_status": "original",
            "text_mode": text_mode,
            "image_mode": "未使用AI图片",
        }, f, ensure_ascii=False)


class QAGateTest(unittest.TestCase):
    def test_blocks_review_and_score_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            os.makedirs(os.path.join(tmp, "评分"), exist_ok=True)
            chapter = write_chapter(tmp)
            with open(os.path.join(tmp, "评分", "score_task.json"), "w", encoding="utf-8") as f:
                json.dump({}, f)
            with open(os.path.join(tmp, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
                review = valid_review_report(tmp, findings=[{
                    "id": "REV-001",
                    "blocking": True,
                    "return_to_stage": "demo",
                    "recommended_skill": "novel-create",
                    "problem": "文风漂移",
                }])
                json.dump(review, f, ensure_ascii=False)
            with open(os.path.join(tmp, "评分", "score_report.json"), "w", encoding="utf-8") as f:
                json.dump(valid_score_report(tmp, chapter, verdict="大改", next_actions=[{
                    "recommended_skill": "novel-rewrite",
                    "return_to_stage": "direction_spec",
                }]), f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertEqual(len(status["blockers"]), 2)
            text = qa_gate.format_gate_status(status)
            self.assertIn("不能直接进入 export", text)
            self.assertIn("REV-001", text)

    def test_review_schema_blocks_export_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            write_chapter(tmp)
            with open(os.path.join(tmp, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "kind": "novel_review_report",
                    "source_snapshot": snapshot_chapters(tmp, mode="review:full"),
                    "waivers": [],
                    "findings": [],
                    "next_actions": [],
                }, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp, require_review_report=True)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "REVIEW-SCHEMA" for b in status["blockers"]))

    def test_score_schema_blocks_when_score_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "评分"), exist_ok=True)
            chapter = write_chapter(tmp)
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"draft_mode": "商业连载", "target_platform": "番茄"}, f, ensure_ascii=False)
            with open(os.path.join(tmp, "评分", "score_report.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "verdict": "大改",
                    "source_snapshot": snapshot_files(tmp, [chapter], mode="score:opening"),
                    "market_baseline": {"freshness": {"status": "fresh", "blocking": False}},
                }, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "SCORE-SCHEMA" for b in status["blockers"]))

    def test_absent_reports_do_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = qa_gate.collect_gate_status(tmp)
            self.assertFalse(status["blocking"])
            self.assertTrue(any(w["id"] == "REVIEW-MISSING" for w in status["warnings"]))
            self.assertTrue(any(w["id"] == "SCORE-MISSING" for w in status["warnings"]))

    def test_missing_review_report_blocks_export_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = qa_gate.collect_gate_status(tmp, require_review_report=True)
            self.assertTrue(status["blocking"])
            self.assertEqual(status["blockers"][0]["id"], "REVIEW-MISSING")

    def test_missing_score_blocks_when_commercial_score_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"draft_mode": "商业连载", "target_platform": "番茄"}, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "SCORE-MISSING" for b in status["blockers"]))

    def test_require_score_false_does_not_block_commercial_drafting(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"draft_mode": "商业连载", "target_platform": "番茄"}, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp, require_score_report=False)
            self.assertFalse(any(b["id"] == "SCORE-MISSING" for b in status["blockers"]))
            self.assertTrue(any(w["id"] == "SCORE-MISSING" for w in status["warnings"]))

    def test_state_closure_blocks_until_delta_is_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_chapter(tmp)
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertTrue(any(b["id"] == "STATE-DELTA-MISSING" for b in status["blockers"]))

            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            with open(os.path.join(tmp, "审稿", "state_delta_第01章.json"), "w", encoding="utf-8") as f:
                json.dump({"schema_version": 1, "kind": "novel_state_delta", "chapter": 1}, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertTrue(any(b["id"] == "STATE-LEDGER-MISSING" for b in status["blockers"]))

            write_state_closure(tmp)
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertFalse(any(b["id"].startswith("STATE-") for b in status["blockers"]))

    def test_state_closure_blocks_stale_ledger_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            chapter = write_chapter(tmp, "# 第1章\n旧正文\n")
            write_state_closure(tmp)
            self.assertFalse(qa_gate.collect_gate_status(tmp, require_state_closure=True)["blocking"])

            with open(chapter, "w", encoding="utf-8") as f:
                f.write("# 第1章\n新正文\n")
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertTrue(any(b["id"] == "STATE-LEDGER-STALE" for b in status["blockers"]))

    def test_ai_usage_blocks_commercial_export_until_human_contribution_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "评分"), exist_ok=True)
            chapter = write_chapter(tmp)
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"draft_mode": "商业连载", "target_platform": "红果"}, f, ensure_ascii=False)
            with open(os.path.join(tmp, "评分", "score_task.json"), "w", encoding="utf-8") as f:
                json.dump({}, f)
            with open(os.path.join(tmp, "评分", "score_report.json"), "w", encoding="utf-8") as f:
                json.dump(valid_score_report(tmp, chapter), f, ensure_ascii=False)

            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertTrue(any(b["id"] == "AI-USAGE-MISSING" for b in status["blockers"]))

            write_ai_usage(tmp, human_contribution="")
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertTrue(any(b["id"] == "AI-USAGE-SCHEMA" for b in status["blockers"]))

            write_ai_usage(tmp)
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertFalse(any(b["id"].startswith("AI-USAGE") for b in status["blockers"]))

    def test_score_baseline_freshness_blocks_unless_waived(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "评分"), exist_ok=True)
            chapter = write_chapter(tmp)
            with open(os.path.join(tmp, "评分", "score_task.json"), "w", encoding="utf-8") as f:
                json.dump({}, f)
            freshness = {
                "status": "expired",
                "blocking": True,
                "baseline_date": "2000-01-01",
                "reason": "market baseline 已过期",
            }
            score_report = valid_score_report(tmp, chapter, freshness=freshness)
            with open(os.path.join(tmp, "评分", "score_report.json"), "w", encoding="utf-8") as f:
                json.dump(score_report, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(any(b["id"] == "SCORE-BASELINE" for b in status["blockers"]))

            score_report["waivers"] = [{
                "type": "score_baseline_freshness",
                "reason": "人工豁免",
                "scope": baseline_freshness_scope(freshness),
            }]
            with open(os.path.join(tmp, "评分", "score_report.json"), "w", encoding="utf-8") as f:
                json.dump(score_report, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp)
            self.assertFalse(any(b["id"] == "SCORE-BASELINE" for b in status["blockers"]))
            self.assertTrue(any(w["id"] == "SCORE-BASELINE" for w in status["warnings"]))

    def test_review_snapshot_blocks_stale_export_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            chapter = write_chapter(tmp, "# 第1章\n旧正文\n")
            report = valid_review_report(tmp)
            with open(os.path.join(tmp, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False)
            self.assertFalse(qa_gate.collect_gate_status(tmp, require_review_report=True)["blocking"])
            with open(chapter, "w", encoding="utf-8") as f:
                f.write("# 第1章\n新正文\n")
            status = qa_gate.collect_gate_status(tmp, require_review_report=True)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "REVIEW-SNAPSHOT" for b in status["blockers"]))

    def test_missing_score_report_waiver_is_scoped_to_current_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_chapter(tmp)
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"draft_mode": "商业连载", "target_platform": "番茄"}, f, ensure_ascii=False)
            scope = qa_gate.missing_score_report_scope(tmp)
            waiver = make_waiver(
                "missing_score_report",
                reason="manual test waiver",
                affected_gate="score_report",
                source="test",
                scope=scope,
            )
            append_waiver(tmp, waiver)
            self.assertFalse(qa_gate.collect_gate_status(tmp)["blocking"])
            write_chapter(tmp, "# 第1章\n正文已变化\n")
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "SCORE-MISSING" for b in status["blockers"]))

    def test_settings_target_marks_score_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **目标用途**：漫剧\n")
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "SCORE-MISSING" for b in status["blockers"]))

    def test_setting_normalization_keeps_target_use_separate_from_novel_purpose(self):
        self.assertEqual(normalize_setting_value("小说用途", "红果漫剧源书"), "漫剧源书")
        self.assertEqual(normalize_setting_value("目标用途", "红果漫剧源书"), "红果漫剧源书")
        self.assertEqual(normalize_setting_value("目标用途", "短读"), "短读")

    def test_settings_purpose_marks_score_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **小说用途**：漫剧源书\n")
            scope = qa_gate.missing_score_report_scope(tmp)
            self.assertEqual(scope["purpose"], "漫剧源书")
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "SCORE-MISSING" for b in status["blockers"]))

    def test_settings_micro_short_drama_purpose_marks_score_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **小说用途**：微短剧源书\n")
            scope = qa_gate.missing_score_report_scope(tmp)
            self.assertEqual(scope["purpose"], "微短剧源书")
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "SCORE-MISSING" for b in status["blockers"]))

    def test_explicit_unknown_rights_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"rights_status": "unknown"}, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "RIGHTS-UNKNOWN" for b in status["blockers"]))

    def test_public_domain_without_target_region_blocks_combine_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "rights_status": "public-domain",
                    "rights_jurisdiction": "US",
                    "rights_covered_regions": ["US"],
                    "requires_region_rights_review": True,
                }, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp, export_formats=["combine"])
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "RIGHTS-PD-REGION-UNSET" for b in status["blockers"]))

    def test_public_domain_target_region_gap_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "rights_status": "public-domain",
                    "rights_jurisdiction": "US",
                    "rights_covered_regions": ["US"],
                    "target_distribution_regions": ["CN"],
                    "requires_region_rights_review": True,
                }, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "RIGHTS-PD-REGION-GAP" for b in status["blockers"]))


if __name__ == "__main__":
    unittest.main()
