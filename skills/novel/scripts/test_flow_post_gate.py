#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for novel orchestration entrypoints."""
import importlib.util
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FLOW = os.path.join(HERE, "flow.py")
POST_WRITE = os.path.join(HERE, "post_write.py")
NOVEL_GATE = os.path.join(REPO, "skills", "novel", "novel-gate.py")
NOVEL_LIB = os.path.join(REPO, "skills", "novel", "_lib")
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)

import novel_route  # noqa: E402
from report_snapshot import snapshot_chapters  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


post_write = load_module("post_write_under_test", POST_WRITE)
novel_gate = load_module("novel_gate_under_test", NOVEL_GATE)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_matrix_project(root):
    write_json(os.path.join(root, "_meta.json"), {
        "schema_version": 1,
        "kind": "create",
        "title": "测试书",
        "rights_status": "original",
        "demo_chapters": 2,
        "draft_mode": "稳妥初稿",
        "target_platform": "跨平台",
    })
    write(os.path.join(root, "_进度.md"), """# 进度

| 章节 | 标题 | 字数 | 大纲 | 细纲 | 正文初稿 | 机检 | 审稿 | 评分 | 改写 | 导出 |
|---|---|---|---|---|---|---|---|---|---|---|
| 第03章 | 转折 | 0 | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
""")
    write(os.path.join(root, "设定", "章纲.md"), "# 章纲\n- 第 03 章 《转折》 — 推进主线\n")
    write(os.path.join(root, "设定", "读者契约.md"), "# 读者契约\n核心题旨：代价换来的力量是否值得。\n")
    write_json(os.path.join(root, "审稿", "demo_gate.json"), {"status": "passed"})


class PostWriteTest(unittest.TestCase):
    def test_marks_progress_only_after_hard_checks_and_ledger_merge(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            write(os.path.join(root, "章节", "第03章.md"), "# 第3章\n正文\n")
            write_json(os.path.join(root, "审稿", "state_delta_第03章.json"), {
                "schema_version": 1,
                "kind": "novel_state_delta",
                "chapter": 3,
            })
            conclusion = os.path.join(root, "审稿", "state_verify_第03章.json")
            write_json(conclusion, {"chapter": 3, "status": "ok", "notes": "一致"})
            calls = []

            def fake_run(cmd, check=False, **_kwargs):
                calls.append(cmd)
                return subprocess.CompletedProcess(cmd, 0)

            with mock.patch.object(post_write.subprocess, "run", side_effect=fake_run):
                with mock.patch.object(sys, "argv", ["post_write.py", root, "--chapter", "第03章", "--conclusion", conclusion]):
                    post_write.main()

            script_names = [os.path.basename(cmd[1]) for cmd in calls]
            self.assertEqual(script_names, [
                "reader_contract_sentry.py",
                "reconcile_ledger.py",
                "wiki_builder.py",
                "tone_check.py",           # 情绪/张力实测回填（advisory·哨兵前跑，激活张力塌陷检测）
                "logic_sentry.py",
                "power_system.py",
                "antagonist_scaling.py",  # 反派战力 scaling 自检（advisory）
                "timeline_check.py",       # 时间线/事件顺序（建议级倒流 + 台账乱序阻断级）
                "reconcile_ledger.py",
                "progress.py",
            ])

    def test_does_not_mark_progress_without_conclusion(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            write(os.path.join(root, "章节", "第03章.md"), "# 第3章\n正文\n")
            write_json(os.path.join(root, "审稿", "state_delta_第03章.json"), {
                "schema_version": 1,
                "kind": "novel_state_delta",
                "chapter": 3,
            })
            calls = []

            def fake_run(cmd, check=False, **_kwargs):
                calls.append(cmd)
                return subprocess.CompletedProcess(cmd, 0)

            with mock.patch.object(post_write.subprocess, "run", side_effect=fake_run):
                with mock.patch.object(sys, "argv", ["post_write.py", root, "--chapter", "第03章"]):
                    with self.assertRaises(SystemExit) as raised:
                        post_write.main()

            self.assertEqual(raised.exception.code, 2)
            script_names = [os.path.basename(cmd[1]) for cmd in calls]
            self.assertNotIn("progress.py", script_names)

    def test_missing_state_delta_exits_before_side_effects(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            write(os.path.join(root, "章节", "第03章.md"), "# 第3章\n正文\n")
            with mock.patch.object(post_write.subprocess, "run") as run_mock:
                with mock.patch.object(sys, "argv", ["post_write.py", root, "--chapter", "第03章"]):
                    with self.assertRaises(SystemExit):
                        post_write.main()
            run_mock.assert_not_called()


class FlowSchemaTest(unittest.TestCase):
    def test_flow_handles_import_progress(self):
        with tempfile.TemporaryDirectory() as root:
            write_json(os.path.join(root, "_meta.json"), {
                "kind": "import",
                "title": "导入源书",
                "rights_status": "user-declared",
            })
            write(os.path.join(root, "_进度.md"), """# 进度

<!-- novel-progress-schema: 1; kind: import -->

## 源书纳管阶段（机器读）
<!-- novel-import-stage-table: 1; kind: import -->
- [x] 项目骨架 <!-- stage:setup -->
- [x] 原作导入 <!-- stage:source_import -->
- [x] 权利复核（当前：user-declared） <!-- stage:rights_review -->
- [ ] 选择下一步：评分 / 审稿 / 改写 / 精简 / 续写 / 转制就绪检查 <!-- stage:next_action -->
""")
            got = subprocess.run(
                [sys.executable, FLOW, root],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            self.assertIn("同构阶段清单", got.stdout)
            self.assertIn("选择下一步", got.stdout)

    def test_flow_handles_stage_checklist_progress(self):
        with tempfile.TemporaryDirectory() as root:
            write_json(os.path.join(root, "_meta.json"), {
                "kind": "expand",
                "title": "扩写项目",
                "rights_status": "original",
            })
            write(os.path.join(root, "_进度.md"), """# 进度

<!-- novel-progress-schema: 1; kind: expand -->

## 同构阶段（机器读）
<!-- novel-derived-stage-table: 1; kind: expand -->
- [x] 项目骨架 <!-- stage:setup -->
- [ ] 事件骨架精筛 <!-- stage:source_model -->
""")
            got = subprocess.run(
                [sys.executable, FLOW, root],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            self.assertIn("同构阶段清单", got.stdout)
            self.assertIn("[next]", got.stdout)

    def test_flow_surfaces_live_check_workflow_command(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            write(os.path.join(root, "_设置.md"), "# 设置\n- 小说生成工作流：边写边自检\n- 小批回扫间隔：3章\n")
            write(os.path.join(root, "写作任务", "第03章.md"), "# 第03章写作任务包\n")
            got = subprocess.run(
                [sys.executable, FLOW, root],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            self.assertIn("小说生成工作流：边写边自检", got.stdout)
            self.assertIn("post_write.py", got.stdout)
            self.assertIn("--conclusion", got.stdout)
            self.assertIn("state_verify_第03章.json", got.stdout)
            self.assertIn("小批回扫", got.stdout)
            self.assertIn("--range 1-3", got.stdout)

    def test_flow_prompts_revision_plan_when_reports_exist(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            write(os.path.join(root, "写作任务", "第03章.md"), "# 第03章写作任务包\n")
            write_json(os.path.join(root, "评分", "score_report.json"), {
                "verdict": "小改",
                "next_actions": [],
            })
            got = subprocess.run(
                [sys.executable, FLOW, root],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            self.assertIn("revision_planner.py", got.stdout)
            self.assertIn("统一修订计划", got.stdout)


class NovelRouteProgressCellTest(unittest.TestCase):
    def test_done_notes_and_yellow_review_notes_do_not_block_route(self):
        with tempfile.TemporaryDirectory() as root:
            write(os.path.join(root, "_进度.md"), """# 进度

| 章节 | 标题 | 字数 | 大纲 | 细纲 | 正文初稿 | 机检 | 审稿 | 评分 | 改写 | 导出 |
|---|---|---|---|---|---|---|---|---|---|---|
| 第01章 | 开局 | 1000 | ✅ | ✅ | ✅(demo) | ✅ | 🟡偏长 | ✅ | ⬜ | ⬜ |
""")
            summary = novel_route.summarize(root)
            self.assertNotIn("error", summary)
            # 改写是 optional 支路列：⬜ = 未启用，路由越过它直达导出，不再卡死。
            self.assertEqual(summary["first"]["label"], "导出")
            self.assertEqual(summary["bottleneck"], {"导出": 1})
            # 🟡 不回炉路由，但不能被静默吞进 done——必须单列出来。
            flagged = summary["flagged"]
            self.assertEqual(len(flagged), 1)
            self.assertEqual(flagged[0]["col"], "审稿")
            self.assertEqual(flagged[0]["value"], "🟡偏长")
            self.assertTrue(flagged[0]["ch"].startswith("第01章"))

    def test_optional_rewrite_column_routes_only_when_engaged(self):
        # 显式标 ⏳ = 启用改写支路，照常路由；—（na）与 ⬜ 都不路由到改写。
        with tempfile.TemporaryDirectory() as root:
            write(os.path.join(root, "_进度.md"), """# 进度

| 章节 | 标题 | 字数 | 大纲 | 细纲 | 正文初稿 | 机检 | 审稿 | 评分 | 改写 | 导出 |
|---|---|---|---|---|---|---|---|---|---|---|
| 第01章 | 开局 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳返工中 | ⬜ |
""")
            summary = novel_route.summarize(root)
            self.assertNotIn("error", summary)
            self.assertEqual(summary["first"]["label"], "改写")

    def test_yellow_cell_is_flagged_state_but_counts_as_done_for_routing(self):
        # cell_state 单元语义：🟡 → flagged；is_done 仍 True（路由不回炉）。
        self.assertEqual(novel_route.cell_state("🟡偏长"), "flagged")
        self.assertTrue(novel_route.is_done("🟡偏长"))
        self.assertEqual(novel_route.cell_state("✅"), "done")
        self.assertEqual(novel_route.cell_state("⬜"), "todo")


class NovelGateTest(unittest.TestCase):
    def test_drafting_gate_blocks_missing_bulk_task_packet(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            blockers, warnings = novel_gate.check_drafting_ready(root, "第03章")
            self.assertTrue(any("写作任务包" in item for item in blockers), blockers)
            self.assertFalse(any("检测到写作任务包" in item for item in warnings))

    def test_drafting_gate_passes_with_required_artifacts(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            write(os.path.join(root, "写作任务", "第03章.md"), "# 第03章写作任务包\n")
            blockers, warnings = novel_gate.check_drafting_ready(root, "第03章")
            self.assertEqual(blockers, [])
            self.assertTrue(any("第03章.md" in item for item in warnings))

    def test_drafting_gate_does_not_require_score_before_text_exists(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            write_json(os.path.join(root, "_meta.json"), {
                "schema_version": 1,
                "kind": "create",
                "title": "商业测试",
                "rights_status": "original",
                "demo_chapters": 2,
                "draft_mode": "商业连载",
                "target_platform": "红果",
            })
            blockers, warnings = novel_gate.check_qa_blockers(root, "drafting", "第03章")
            self.assertFalse(any("SCORE-MISSING" in item for item in blockers), blockers)
            self.assertTrue(any("SCORE-MISSING" in item for item in warnings), warnings)

    def test_review_gate_requires_state_delta_merged(self):
        with tempfile.TemporaryDirectory() as root:
            make_matrix_project(root)
            write(os.path.join(root, "章节", "第03章.md"), "# 第3章\n正文\n")
            blockers, _warnings = novel_gate.check_qa_blockers(root, "review", "第03章")
            self.assertTrue(any("STATE-DELTA-MISSING" in item for item in blockers), blockers)

            write_json(os.path.join(root, "审稿", "state_delta_第03章.json"), {
                "schema_version": 1,
                "kind": "novel_state_delta",
                "chapter": 3,
            })
            blockers, _warnings = novel_gate.check_qa_blockers(root, "review", "第03章")
            self.assertTrue(any("STATE-LEDGER-MISSING" in item for item in blockers), blockers)

            write_json(os.path.join(root, "审稿", "state_ledger.json"), {
                "schema_version": 1,
                "kind": "novel_state_ledger",
                "chapter_deltas": {"chapter_03": {
                    "merged": True,
                    "verification": {
                        "chapter_file_hash": sha256_file(os.path.join(root, "章节", "第03章.md")),
                        "delta_hash": sha256_file(os.path.join(root, "审稿", "state_delta_第03章.json")),
                    },
                }},
            })
            blockers, _warnings = novel_gate.check_qa_blockers(root, "review", "第03章")
            self.assertFalse(any("STATE-" in item for item in blockers), blockers)

    def test_wiki_freshness_uses_chapter_file_mtime(self):
        with tempfile.TemporaryDirectory() as root:
            wiki = os.path.join(root, "设定", "动态百科.json")
            chapter = os.path.join(root, "章节", "第01章.md")
            write_json(wiki, {"角色": {}})
            write(chapter, "# 第1章\n新正文\n")
            os.utime(wiki, (1000, 1000))
            os.utime(chapter, (2000, 2000))

            status = novel_gate.check_wiki_freshness(root)
            self.assertEqual(status["status"], "stale")

    def test_wiki_freshness_prefers_source_snapshot_hash(self):
        with tempfile.TemporaryDirectory() as root:
            wiki = os.path.join(root, "设定", "动态百科.json")
            chapter = os.path.join(root, "章节", "第01章.md")
            write(chapter, "# 第1章\n旧正文\n")
            write_json(wiki, {"角色": {}})
            write_json(os.path.join(root, "设定", "动态百科.source_snapshot.json"),
                       snapshot_chapters(root, mode="wiki:dynamic"))
            status = novel_gate.check_wiki_freshness(root)
            self.assertEqual(status["status"], "ok")

            write(chapter, "# 第1章\n新正文\n")
            status = novel_gate.check_wiki_freshness(root)
            self.assertEqual(status["status"], "stale")
            self.assertIn("source_snapshot", status["reason"])

    def test_wiki_freshness_reports_lag_chapters(self):
        # 分级判据：snapshot 覆盖后新增/改动的章节数 = lag_chapters（≥3 章达 review/score 阻断阈值）。
        with tempfile.TemporaryDirectory() as root:
            wiki = os.path.join(root, "设定", "动态百科.json")
            write(os.path.join(root, "章节", "第01章.md"), "# 第1章\n旧正文\n")
            write_json(wiki, {"角色": {}})
            write_json(os.path.join(root, "设定", "动态百科.source_snapshot.json"),
                       snapshot_chapters(root, mode="wiki:dynamic"))
            for i in (2, 3, 4):
                write(os.path.join(root, "章节", f"第{i:02d}章.md"), f"# 第{i}章\n新正文\n")

            status = novel_gate.check_wiki_freshness(root)
            self.assertEqual(status["status"], "stale")
            self.assertEqual(status["lag_chapters"], 3)
            self.assertGreaterEqual(status["lag_chapters"], novel_gate.WIKI_LAG_BLOCK_THRESHOLD)

    def test_wiki_freshness_rejects_partial_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            wiki = os.path.join(root, "设定", "动态百科.json")
            chapter = os.path.join(root, "章节", "第01章.md")
            write(chapter, "# 第1章\n正文\n")
            write_json(wiki, {"角色": {}})
            snapshot = snapshot_chapters(root, mode="wiki:partial")
            write_json(os.path.join(root, "设定", "动态百科.source_snapshot.json"), snapshot)

            status = novel_gate.check_wiki_freshness(root)
            self.assertEqual(status["status"], "stale")
            self.assertIn("不是全量", status["reason"])


if __name__ == "__main__":
    unittest.main()
