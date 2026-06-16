#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draft_packets.py contract tests.

Can run without pytest:
    python3 skills/novel-craft/scripts/test_draft_packets.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT_PACKETS = os.path.join(HERE, "draft_packets.py")


def make_project(root, *, demo=True):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "create",
            "title": "测试新书",
            "rights_status": "original",
            "outputs": ["txt"],
            "scale": "medium",
            "target_chapters": 5,
            "target_words_per_chapter": [3000, 5000],
            "demo_chapters": 2,
            "person": "third-limited",
            "target_platform": "番茄",
        }, f, ensure_ascii=False)
    for name in ("创作蓝图.md", "设定圣经.md", "角色卡.md", "世界观.md"):
        with open(os.path.join(root, "设定", name), "w", encoding="utf-8") as f:
            f.write(f"# {name}\n测试内容。\n")
    with open(os.path.join(root, "设定", "读者契约.md"), "w", encoding="utf-8") as f:
        f.write("# 读者契约\n核心题旨：代价换来的力量是否值得。\n")
    with open(os.path.join(root, "设定", "章纲.md"), "w", encoding="utf-8") as f:
        f.write("# 章纲\n- 第 01 章 《开局》 — 主角登场\n- 第 03 章 《转折》 — 发现代价\n")
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("# 第1章 开局\n<!-- meta: demo=true -->\n上一章内容。\n")
    if demo:
        with open(os.path.join(root, "审稿", "demo_gate.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_demo_gate",
                "status": "passed",
                "style_anchor": {"source_chapter": "第01章", "summary": "短句强钩子"},
                "reader_promises": ["主角会付出代价"],
                "setting_constraints": ["能力不能无限用"],
                "banned_drift": ["不要流水账"],
                "reader_contract": {
                    "theme": "力量必须付出代价",
                    "dramatic_question": "主角是否愿意为守护他人承受反噬",
                    "must_answer": ["代价能否被承担"],
                    "reader_promises": ["代价会逐步升级"],
                    "aesthetic_register": "短句、有压迫感、动作细节强",
                    "delight_engine": ["每章让能力代价更尖锐"],
                    "banned_drift": ["不要写成无脑升级"],
                },
            }, f, ensure_ascii=False)


def make_kind_project(root, kind):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": kind,
            "title": "测试项目",
            "rights_status": "user-declared",
            "outputs": ["txt"],
            "scale": "short",
            "target_chapters": 3,
            "target_words_per_chapter": [1000, 1500],
            "demo_chapters": 1,
            "target_platform": "红果",
        }, f, ensure_ascii=False)
    with open(os.path.join(root, "审稿", "demo_gate.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "kind": "novel_demo_gate", "status": "passed"}, f, ensure_ascii=False)
    with open(os.path.join(root, "设定", "读者契约.md"), "w", encoding="utf-8") as f:
        f.write("# 读者契约\n核心题旨：代价换来的力量是否值得。\n")
    with open(os.path.join(root, "设定", "章纲.md"), "w", encoding="utf-8") as f:
        f.write("# 章纲\n- 第 02 章 《推进》 — 推进主线\n")
    with open(os.path.join(root, "原作.txt"), "w", encoding="utf-8") as f:
        f.write("第1章 原作\n原作内容。\n")
    for rel in (
        "设定/创作蓝图.md",
        "设定/设定圣经.md",
        "设定/角色卡.md",
        "设定/世界观.md",
        "设定/改动spec.md",
        "设定/新设定.md",
        "设定/锚点表.json",
        "设定/人物.md",
        "设定/主线骨架.json",
        "设定/末章状态.md",
        "设定/作者口吻.md",
        "设定/续写方向.md",
        "设定/事件骨架.json",
        "设定/章节映射.md",
    ):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {rel}\n")


class DraftPacketsTest(unittest.TestCase):
    def test_generates_packet_and_state_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            ledger = os.path.join(tmp, "审稿", "state_ledger.json")
            self.assertIn("[ok] 写作任务包", got.stdout)
            self.assertTrue(os.path.exists(packet))
            self.assertTrue(os.path.exists(ledger))
            self.assertTrue(os.path.exists(os.path.join(tmp, "审稿", "state_ledger.lock")))
            self.assertFalse([name for name in os.listdir(os.path.join(tmp, "审稿")) if ".tmp." in name])
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("第 03 章写作任务包", text)
            self.assertIn("发现代价", text)
            self.assertIn("题旨与读者契约", text)
            self.assertIn("力量必须付出代价", text)
            self.assertIn("代价换来的力量是否值得", text)
            self.assertIn("状态增量模板", text)
            self.assertIn("reader_contract_progress", text)

    def test_auto_uses_trio_for_commercial_serial(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 小说生成模式：商业连载\n")
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True, check=True,
            )
            task_dir = os.path.join(tmp, "写作任务")
            self.assertIn("三步迭代顺序", got.stdout)
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_architect.md")))
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_ghostwriter.md")))
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章_editor.md")))
            self.assertFalse(os.path.exists(os.path.join(task_dir, "第03章.md")))

    def test_explicit_full_overrides_trio_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as f:
                f.write("# 设置\n- 小说生成模式：漫剧源书\n")
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3", "--step", "full"],
                capture_output=True, text=True, check=True,
            )
            task_dir = os.path.join(tmp, "写作任务")
            self.assertTrue(os.path.exists(os.path.join(task_dir, "第03章.md")))
            self.assertFalse(os.path.exists(os.path.join(task_dir, "第03章_architect.md")))

    def test_blocks_without_demo_gate_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp, demo=False)
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("demo_gate.json", got.stderr)

    def test_blocks_without_reader_contract_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.remove(os.path.join(tmp, "设定", "读者契约.md"))
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("读者契约.md", got.stderr)

    def test_allow_missing_reader_contract_records_waiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.remove(os.path.join(tmp, "设定", "读者契约.md"))
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3", "--allow-missing-reader-contract"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)

    def test_allow_missing_demo_records_waiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp, demo=False)
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3", "--allow-missing-demo"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            packet = os.path.join(tmp, "写作任务", "第03章.md")
            with open(packet, encoding="utf-8") as f:
                packet_text = f.read()
            self.assertIn("显式豁免", packet_text)
            self.assertIn("missing_demo_gate", packet_text)
            waiver_log = os.path.join(tmp, "审稿", "waiver_log.jsonl")
            self.assertTrue(os.path.exists(waiver_log))
            with open(os.path.join(tmp, "审稿", "state_ledger.json"), encoding="utf-8") as f:
                ledger = json.load(f)
            self.assertEqual(ledger["waivers"][0]["type"], "missing_demo_gate")

    def test_next_skips_demo_chapters_and_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "章节", "第03章.md"), "w", encoding="utf-8") as f:
                f.write("# 第3章 转折\n正文。\n")
            subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--next"],
                capture_output=True, text=True, check=True,
            )
            self.assertTrue(os.path.exists(os.path.join(tmp, "写作任务", "第04章.md")))

    def test_source_paths_follow_project_kind(self):
        cases = {
            "rewrite": (["设定/改动spec.md", "设定/新设定.md"], ["设定/创作蓝图.md", "设定/设定圣经.md"]),
            "spinoff": (["设定/锚点表.json", "原作.txt"], ["设定/创作蓝图.md", "设定/新设定.md"]),
            "continue": (["设定/末章状态.md", "设定/作者口吻.md", "设定/续写方向.md"], ["设定/创作蓝图.md"]),
            "expand": (["设定/事件骨架.json", "设定/章节映射.md"], ["设定/创作蓝图.md", "设定/新设定.md"]),
            "condense": (["设定/主线骨架.json", "设定/章节映射.md"], ["设定/创作蓝图.md", "设定/新设定.md"]),
        }
        for kind, (must_have, must_not_have) in cases.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                make_kind_project(tmp, kind)
                got = subprocess.run(
                    [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "2", "--stdout"],
                    capture_output=True, text=True, check=True,
                )
                for path in must_have:
                    self.assertIn(f"`{path}`", got.stdout)
                self.assertIn("`设定/读者契约.md`", got.stdout)
                for path in must_not_have:
                    self.assertNotIn(f"`{path}`", got.stdout)
                self.assertIn("python3 skills/novel-review/scripts/mechanical_check.py", got.stdout)


if __name__ == "__main__":
    unittest.main()
