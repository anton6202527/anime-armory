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
            }, f, ensure_ascii=False)


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
            with open(packet, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("第 03 章写作任务包", text)
            self.assertIn("发现代价", text)
            self.assertIn("状态增量模板", text)

    def test_blocks_without_demo_gate_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp, demo=False)
            got = subprocess.run(
                [sys.executable, DRAFT_PACKETS, tmp, "--chapter", "3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("demo_gate.json", got.stderr)

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


if __name__ == "__main__":
    unittest.main()
