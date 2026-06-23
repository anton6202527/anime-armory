#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel-craft export contract tests.

Can run without pytest:
    python3 skills/novel-craft/scripts/test_export.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import hashlib

from report_snapshot import snapshot_chapters


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXPORT = os.path.join(HERE, "export.py")
EXPAND_INIT = os.path.join(REPO, "skills", "novel-expand", "scripts", "init_project.py")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_chapter(project_root):
    chap_dir = os.path.join(project_root, "章节")
    os.makedirs(chap_dir, exist_ok=True)
    with open(os.path.join(chap_dir, "第01章.md"), "w", encoding="utf-8") as f:
        f.write("# 第1章 《扩写开端》\n<!-- meta: demo=false -->\n扩写正文内容。\n")


def write_review_pass(project_root):
    os.makedirs(os.path.join(project_root, "审稿"), exist_ok=True)
    with open(os.path.join(project_root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_review_report",
            "project_root": os.path.abspath(project_root),
            "generated_at": "2026-06-09",
            "scope": {"mode": "full"},
            "summary": {"blocking_count": 0, "suggestion_count": 0, "polish_count": 0, "waiver_count": 0, "verdict": "pass"},
            "source_snapshot": snapshot_chapters(project_root, mode="review:full"),
            "mechanical_findings_path": "审稿/mechanical_findings.json",
            "waivers": [],
            "findings": [],
                "next_actions": [],
        }, f, ensure_ascii=False)
    delta_path = os.path.join(project_root, "审稿", "state_delta_第01章.json")
    with open(delta_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_state_delta",
            "chapter": 1,
        }, f, ensure_ascii=False)
    chapter_path = os.path.join(project_root, "章节", "第01章.md")
    with open(os.path.join(project_root, "审稿", "state_ledger.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_state_ledger",
            "chapter_deltas": {"chapter_01": {
                "merged": True,
                "verification": {
                    "chapter_file_hash": sha256_file(chapter_path),
                    "delta_hash": sha256_file(delta_path),
                },
            }},
        }, f, ensure_ascii=False)
    os.makedirs(os.path.join(project_root, "合规"), exist_ok=True)
    with open(os.path.join(project_root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_ai_usage",
            "generated_at": "2026-06-09",
            "project_root": os.path.abspath(project_root),
            "title": "源书",
            "publish_target": "导出测试",
            "human_contribution": "测试夹具模拟人工审稿与导出确认。",
            "rights_status": "public-domain",
            "text_mode": "AI-assisted",
            "image_mode": "未使用AI图片",
            "disclosure_detail": {
                "text_directness": "revision_only",
                "human_steering": "测试夹具固定输入，人工确认导出。",
                "replaceability": "assistive_non_replaceable",
                "direct_incorporation": "none",
                "review_steps": ["review_report_passed", "state_ledger_verified"],
            },
        }, f, ensure_ascii=False)


class ExportContractTest(unittest.TestCase):
    def test_expand_init_default_export_uses_meta_outputs_and_kind_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "源书.txt")
            with open(src, "w", encoding="utf-8") as f:
                f.write("# copyright: public-domain\n\n第1章 开端\n\n原文内容。\n")
            project = os.path.join(tmp, "expand")
            subprocess.run(
                [sys.executable, EXPAND_INIT, src, "--out", project, "--outputs", "txt"],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            with open(os.path.join(project, "_meta.json"), encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["schema_version"], 1)
            self.assertEqual(meta["kind"], "expand")
            with open(os.path.join(project, "_进度.md"), encoding="utf-8") as f:
                progress_md = f.read()
            self.assertIn("novel-derived-stage-table: 1; kind: expand", progress_md)
            self.assertIn("<!-- stage:source_model -->", progress_md)
            write_chapter(project)
            write_review_pass(project)
            subprocess.run(
                [sys.executable, EXPORT, project],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(os.path.exists(os.path.join(project, "导出", "源书-扩写.txt")))

    def test_missing_formats_is_hard_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "proj")
            os.makedirs(project, exist_ok=True)
            with open(os.path.join(project, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"source_title": "源书", "kind": "expand"}, f, ensure_ascii=False)
            write_chapter(project)
            write_review_pass(project)
            got = subprocess.run(
                [sys.executable, EXPORT, project],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("outputs", got.stderr)

    def test_export_blocks_when_qa_gate_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "proj")
            os.makedirs(project, exist_ok=True)
            with open(os.path.join(project, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"source_title": "源书", "kind": "expand", "outputs": ["txt"]}, f, ensure_ascii=False)
            write_chapter(project)
            os.makedirs(os.path.join(project, "审稿"), exist_ok=True)
            with open(os.path.join(project, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
                json.dump({"findings": [{
                    "id": "REV-001",
                    "blocking": True,
                    "return_to_stage": "outline",
                    "recommended_skill": "novel-expand",
                    "problem": "事件骨架变了",
                }]}, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, EXPORT, project],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("QA gate", got.stderr)
            self.assertFalse(os.path.exists(os.path.join(project, "导出", "源书-扩写.txt")))

    def test_export_blocks_when_review_report_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "proj")
            os.makedirs(project, exist_ok=True)
            with open(os.path.join(project, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"source_title": "源书", "kind": "expand", "outputs": ["txt"]}, f, ensure_ascii=False)
            write_chapter(project)
            got = subprocess.run(
                [sys.executable, EXPORT, project],
                cwd=REPO,
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("REVIEW-MISSING", got.stderr)

    def test_legacy_cross_line_format_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "proj")
            os.makedirs(project, exist_ok=True)
            with open(os.path.join(project, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"source_title": "源书", "kind": "expand", "outputs": ["txt"]}, f, ensure_ascii=False)
            write_chapter(project)
            legacy_format = "hand" + "off"
            got = subprocess.run(
                [sys.executable, EXPORT, project, "--formats", legacy_format, "--ignore-qa-gate"],
                cwd=REPO,
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("未知导出格式", got.stderr)

    def test_ignore_qa_gate_logs_waiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "proj")
            os.makedirs(project, exist_ok=True)
            with open(os.path.join(project, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"source_title": "源书", "kind": "expand", "outputs": ["txt"]}, f, ensure_ascii=False)
            write_chapter(project)
            got = subprocess.run(
                [sys.executable, EXPORT, project, "--ignore-qa-gate"],
                cwd=REPO,
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            waiver_log = os.path.join(project, "审稿", "waiver_log.jsonl")
            self.assertTrue(os.path.exists(waiver_log))
            with open(waiver_log, encoding="utf-8") as f:
                waiver = json.loads(f.readline())
            self.assertEqual(waiver["type"], "ignore_qa_gate")
            self.assertEqual(waiver["scope"]["chapter_count"], 1)
            self.assertIn("source_aggregate_hash", waiver["scope"])
            self.assertEqual(waiver["scope"]["blocker_ids"], ["REVIEW-MISSING", "STATE-DELTA-MISSING"])
            self.assertTrue(os.path.exists(os.path.join(project, "导出", "源书-扩写.txt")))


if __name__ == "__main__":
    unittest.main()
