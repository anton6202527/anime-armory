#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA gate tests. Can run without pytest."""
import json
import os
import tempfile
import unittest
import hashlib
from datetime import date

import qa_gate
from report_snapshot import snapshot_chapters, snapshot_files
from settings import normalize_setting_value
from waivers import baseline_freshness_scope, make_waiver, append_waiver


def _write_meta(root, **fields):
    meta = {"schema_version": 1, "kind": "create", "rights_status": "original"}
    meta.update(fields)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)


def _write_arc_report(root, name, blocking):
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "审稿", name), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "kind": "novel_arc_gate", "blocking": blocking,
                   "status": "blocked" if blocking else "clean", "findings": []}, f, ensure_ascii=False)


class ArcGateTest(unittest.TestCase):
    def _ids(self, items):
        return {i.get("id") for i in items}

    def test_blocking_arc_report_blocks_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, scale="medium", target_chapters=8)
            _write_arc_report(tmp, "arc_gate_第01-05章.json", blocking=2)
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertIn("ARC-BLOCK", self._ids(status["blockers"]))
            self.assertTrue(status["blocking"])

    def test_long_project_without_arc_report_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, scale="long", target_chapters=120)
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertIn("ARC-MISSING", self._ids(status["warnings"]))
            self.assertNotIn("ARC-BLOCK", self._ids(status["blockers"]))

    def test_short_project_without_arc_report_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, scale="short", target_chapters=6)
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertNotIn("ARC-MISSING", self._ids(status["warnings"]))
            self.assertNotIn("ARC-BLOCK", self._ids(status["blockers"]))

    def test_clean_arc_report_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, scale="long", target_chapters=120)
            _write_arc_report(tmp, "arc_gate_第01-05章.json", blocking=0)
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertNotIn("ARC-BLOCK", self._ids(status["blockers"]))
            self.assertNotIn("ARC-MISSING", self._ids(status["warnings"]))

    def test_commercial_short_project_now_warns_arc_missing(self):
        """长弧判定单一真值源：商业连载即便 20 章（<30）也按长弧处理——此前 qa_gate
        漏了 mode/purpose 与 flow 漂移，商业连载短项目在导出闸收不到 ARC-MISSING。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, scale="medium", target_chapters=20, draft_mode="商业连载")
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertIn("ARC-MISSING", self._ids(status["warnings"]))

    def test_long_arc_predicate_agrees_across_flow_and_gate(self):
        """flow.long_arc_mode 与 qa_gate._arc_long_project 必须基于同一谓词。"""
        import novel_contract
        # 商业连载 20 章：两侧都应判长弧。
        meta = {"scale": "medium", "target_chapters": 20}
        settings = {"小说生成模式": "商业连载"}
        self.assertTrue(novel_contract.is_long_arc_project(meta, settings))
        # 纯短篇、无商业/源书模式：两侧都应判否。
        self.assertFalse(novel_contract.is_long_arc_project(
            {"scale": "short", "target_chapters": 6}, {}))


def write_chapter(root, text="# 第1章\n正文\n"):
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    chapter = os.path.join(root, "章节", "第01章.md")
    with open(chapter, "w", encoding="utf-8") as f:
        f.write(text)
    return chapter


def write_chapters(root, count, text_fn=None):
    """创建 count 章正文（第01章~第N章），返回路径列表。"""
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    paths = []
    for n in range(1, count + 1):
        path = os.path.join(root, "章节", f"第{n:02d}章.md")
        text = text_fn(n) if text_fn else f"# 第{n}章\n正文内容\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        paths.append(path)
    return paths


def _write_demo_gate(root, status="passed"):
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "审稿", "demo_gate.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "kind": "novel_demo_gate", "status": status}, f, ensure_ascii=False)


class DemoGateTest(unittest.TestCase):
    def _ids(self, items):
        return {i.get("id") for i in items}

    def test_no_demo_chapters_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, demo_chapters=0)
            write_chapters(tmp, 3)
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertNotIn("DEMO-GATE-NOT-PASSED", self._ids(status["blockers"]))
            self.assertNotIn("DEMO-GATE-PENDING", self._ids(status["warnings"]))

    def test_mass_production_without_passed_demo_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, demo_chapters=2)
            write_chapters(tmp, 5)  # 写到 demo 之后 → 批量生产已发生
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertIn("DEMO-GATE-NOT-PASSED", self._ids(status["blockers"]))
            self.assertTrue(status["blocking"])

    def test_passed_demo_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, demo_chapters=2)
            write_chapters(tmp, 5)
            _write_demo_gate(tmp, status="passed")
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertNotIn("DEMO-GATE-NOT-PASSED", self._ids(status["blockers"]))

    def test_within_demo_phase_warns_not_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, demo_chapters=3)
            write_chapters(tmp, 2)  # 仍在 demo 阶段，未越界
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertIn("DEMO-GATE-PENDING", self._ids(status["warnings"]))
            self.assertNotIn("DEMO-GATE-NOT-PASSED", self._ids(status["blockers"]))


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


def write_full_state_closure(root, chapter_nums):
    """为多个章节创建 delta 并写入单一 state_ledger（不互相覆盖）。"""
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    chapter_deltas = {}
    for ch in chapter_nums:
        delta_path = os.path.join(root, "审稿", f"state_delta_第{ch:02d}章.json")
        with open(delta_path, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 1, "kind": "novel_state_delta", "chapter": ch}, f, ensure_ascii=False)
        chapter_path = os.path.join(root, "章节", f"第{ch:02d}章.md")
        chapter_deltas[f"chapter_{ch:02d}"] = {
            "merged": True,
            "verification": {
                "chapter": ch,
                "status": "passed",
                "chapter_file_hash": file_sha256(chapter_path),
                "delta_hash": file_sha256(delta_path),
            },
        }
    with open(os.path.join(root, "审稿", "state_ledger.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_state_ledger",
            "chapter_deltas": chapter_deltas,
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

    def test_stale_high_risk_research_pack_blocks_export_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_chapter(tmp, "# 第1章\n医生在医院急诊进行抢救和用药。\n")
            os.makedirs(os.path.join(tmp, "资料"), exist_ok=True)
            with open(os.path.join(tmp, "资料", "专业资料包_急诊抢救.md"), "w", encoding="utf-8") as f:
                f.write("# 专业资料包：急诊抢救\n")
            with open(os.path.join(tmp, "资料", "research_sources.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 1,
                    "kind": "novel_research_sources",
                    "packs": [{
                        "topic": "急诊抢救",
                        "topic_slug": "急诊抢救",
                        "domain": "medical",
                        "risk_level": "high",
                        "status": "ready",
                        "pack_path": "资料/专业资料包_急诊抢救.md",
                        "applicable_chapters": ["all"],
                        "keywords": ["急诊", "抢救"],
                        "updated_at": "2025-01-01",
                        "freshness_days": 30,
                        "sources": [{
                            "id": "SRC-001",
                            "title": "急诊指南",
                            "published_date": "2025-01-01",
                            "accessed_date": "2025-01-02",
                            "reliability": "high",
                        }],
                        "claims": [{
                            "id": "FACT-001",
                            "claim": "急诊分诊先评估生命体征",
                            "source_ids": ["SRC-001"],
                            "confidence": "high",
                            "applicable_chapters": ["all"],
                        }],
                    }],
                }, f, ensure_ascii=False)

            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "RESEARCH-PACK-STALE" for b in status["blockers"]))

    def test_required_research_domain_blocks_export_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"research_required_domains": ["legal"]}, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertTrue(any(b["id"] == "RESEARCH-MISSING-REQUIRED-RESEARCH-PACK" for b in status["blockers"]))

    def test_simulate_signal_only_warns_but_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "评分"), exist_ok=True)
            with open(os.path.join(tmp, "评分", "reader_panel_signals.json"), "w", encoding="utf-8") as f:
                json.dump({"analysis_mode": "signal_only", "signal_only": True, "qualitative_completed": False}, f)
            status = qa_gate.collect_gate_status(tmp)
            self.assertFalse(status["blocking"])
            self.assertTrue(any(w["id"] == "SIMULATE-SIGNAL-ONLY" for w in status["warnings"]))

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
        """5 章以上项目，state_closure 缺失 delta/未合并应阻断；全合并后不应阻断。"""
        with tempfile.TemporaryDirectory() as tmp:
            write_chapters(tmp, 5)
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertTrue(any(b["id"] == "STATE-DELTA-MISSING" for b in status["blockers"]),
                            "缺 state_delta 应阻断")

            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            with open(os.path.join(tmp, "审稿", "state_delta_第01章.json"), "w", encoding="utf-8") as f:
                json.dump({"schema_version": 1, "kind": "novel_state_delta", "chapter": 1}, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertTrue(any(b["id"] == "STATE-LEDGER-MISSING" for b in status["blockers"]),
                            "有 delta 但未合并进 ledger 应阻断")

            write_full_state_closure(tmp, range(1, 6))
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertFalse(any(b["id"].startswith("STATE-") for b in status["blockers"]),
                             "全部合并后不应有阻断")

    def test_state_closure_blocks_stale_ledger_hash(self):
        """5 章以上项目，正文修改后 ledger hash 过期应阻断。"""
        with tempfile.TemporaryDirectory() as tmp:
            chapters = write_chapters(tmp, 5)
            write_full_state_closure(tmp, range(1, 6))
            self.assertFalse(qa_gate.collect_gate_status(tmp, require_state_closure=True)["blocking"],
                             "初始全对账不应阻断")

            # 修改第 1 章正文，hash 过期
            with open(chapters[0], "w", encoding="utf-8") as f:
                f.write("# 第1章\n修改后的正文\n")
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertTrue(any(b["id"] == "STATE-LEDGER-STALE" for b in status["blockers"]),
                            "正文修改后 ledger hash 过期应阻断")

    def test_state_closure_short_project_waiver(self):
        """短篇（<5 章）：require_state_closure=True 也仅出提醒，不阻断。"""
        with tempfile.TemporaryDirectory() as tmp:
            write_chapters(tmp, 3)
            status = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertTrue(any(w["id"] == "STATE-SHORT-WAIVER" for w in status["warnings"]),
                            "短篇应出豁免提醒")
            self.assertFalse(any(b["id"].startswith("STATE-") for b in status["blockers"]),
                             "短篇缺 state_delta 不应阻断")

    def test_short_project_waiver_does_not_apply_to_explicit_per_chapter_check(self):
        """掣肘回归：短篇豁免只放过"全项目闭环扫描"（state_chapter=None）。
        当显式逐章检查（novel-gate review --chapter，state_chapter 指定）时，该章的
        state_delta 是硬作业——短篇也必须阻断，否则 review 闸对短篇整条空转。"""
        with tempfile.TemporaryDirectory() as tmp:
            write_chapters(tmp, 2)  # <5 章短篇
            # 全项目扫描（无 state_chapter）→ 仅提醒（保留 P0-1 豁免）。
            sweep = qa_gate.collect_gate_status(tmp, require_state_closure=True)
            self.assertFalse(any(b["id"].startswith("STATE-") for b in sweep["blockers"]))
            # 逐章检查第 2 章（state_chapter=2）→ 缺 state_delta 必须阻断。
            per_ch = qa_gate.collect_gate_status(tmp, require_state_closure=True, state_chapter=2)
            self.assertTrue(any(b["id"] == "STATE-DELTA-MISSING" for b in per_ch["blockers"]),
                            [b["id"] for b in per_ch["blockers"]])

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

    def test_ai_generated_text_blocks_strict_chinese_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, target_platform="晋江")
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **目标平台**：晋江\n- **文本主创模式**：AI生成\n")
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(status["blocking"])
            self.assertTrue(any(b["id"] == "AI-GENERATED-TEXT-PLATFORM-RISK" for b in status["blockers"]))

    def test_ai_generated_text_exception_requires_evidence_and_scoped_waiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, target_platform="晋江")
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **目标平台**：晋江\n- **文本主创模式**：AI生成\n")
            evidence_dir = os.path.join(tmp, "合规")
            os.makedirs(evidence_dir, exist_ok=True)
            with open(os.path.join(evidence_dir, "platform_ai_evidence.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 1,
                    "kind": "novel_platform_ai_evidence",
                    "target_platform": "晋江",
                    "evidence_date": date.today().isoformat(),
                    "source_url": "https://example.com/platform-rule",
                    "summary": "平台正式接受 AI生成 正文投稿的当日规则证据。",
                    "accepted_text_authorship_modes": ["AI生成"],
                }, f, ensure_ascii=False)

            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(any(b["id"] == "AI-GENERATED-TEXT-PLATFORM-RISK" for b in status["blockers"]))

            scope = qa_gate.platform_ai_exception_scope(tmp, "晋江", "AI生成")
            waiver = make_waiver(
                "ai_generated_text_platform_exception",
                reason="official platform evidence",
                affected_gate="platform_ai_text",
                source="test",
                scope=scope,
            )
            append_waiver(tmp, waiver)
            status = qa_gate.collect_gate_status(tmp)
            self.assertFalse(any(b["id"] == "AI-GENERATED-TEXT-PLATFORM-RISK" for b in status["blockers"]))
            self.assertTrue(any(w["id"] == "AI-GENERATED-TEXT-PLATFORM-WAIVED" for w in status["warnings"]))

    def test_ai_assisted_text_warns_for_strict_chinese_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, target_platform="晋江")
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **目标平台**：晋江\n- **文本主创模式**：AI辅助\n")
            status = qa_gate.collect_gate_status(tmp)
            self.assertFalse(any(b["id"].startswith("AI-") for b in status["blockers"]))
            self.assertTrue(any(w["id"] == "AI-ASSISTED-TEXT-PLATFORM-REVIEW" for w in status["warnings"]))

    def test_target_language_alone_does_not_trip_chinese_platform_strict_gate(self):
        """🟡C：目标语言是语言、不是投放渠道。AI生成 + 仅出海语言（无中文平台）不应触发
        中文平台严格闸 AI-GENERATED-TEXT-PLATFORM-RISK（旧实现把 目标语言 拼进 blob 子串匹配）。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **目标语言**：English\n- **文本主创模式**：AI生成\n")
            status = qa_gate.collect_gate_status(tmp)
            self.assertFalse(any(b["id"] == "AI-GENERATED-TEXT-PLATFORM-RISK" for b in status["blockers"]))

    def test_overseas_target_requires_ai_usage_via_field_not_substring(self):
        """🟡C：出海（出海目标平台 / 非中文目标语言）→ AI 文本披露必需，
        但走显式字段判定（_targets_overseas），不再靠把语言串塞进关键词 blob。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **出海目标平台**：KDP\n")
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertTrue(any(b["id"].startswith("AI-USAGE") for b in status["blockers"]),
                            [b["id"] for b in status["blockers"]])

    def test_domestic_chinese_language_does_not_force_ai_usage(self):
        """🟡C：纯国内（目标语言=中文、无商业平台）不应被出海逻辑误判为需 AI 披露。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n\n- **目标语言**：中文\n")
            status = qa_gate.collect_gate_status(tmp, export_formats=["txt"])
            self.assertFalse(any(b["id"].startswith("AI-USAGE") for b in status["blockers"]))

    def test_scene_card_missing_key_fields_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp)
            os.makedirs(os.path.join(tmp, "设定"), exist_ok=True)
            with open(os.path.join(tmp, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 1,
                    "kind": "novel_scene_cards",
                    "scenes": [{"id": "SC001-01", "chapter": 1, "scene_no": 1, "pov": "林越"}],
                }, f, ensure_ascii=False)
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(any(b["id"] == "SCENE-CARD-MISSING-FIELDS" for b in status["blockers"]))

    def test_missing_scene_cards_warn_for_long_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_meta(tmp, scale="long", target_chapters=80)
            status = qa_gate.collect_gate_status(tmp)
            self.assertTrue(any(w["id"] == "SCENE-CARDS-MISSING" for w in status["warnings"]))

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
