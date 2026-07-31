#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
ARC_PACKETS = os.path.join(HERE, "arc_packets.py")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def make_project(root):
    write_json(os.path.join(root, "_meta.json"), {
        "schema_version": 1,
        "kind": "create",
        "title": "长篇测试",
        "scale": "long",
        "target_platform": "番茄",
    })
    write(os.path.join(root, "设定", "章纲.md"), "\n".join([
        "# 章纲",
        "- 第 01 章 《开局》 — 立下代价规则",
        "- 第 02 章 《代价》 — 代价首次伤人",
        "- 第 03 章 《选择》 — 主角主动承担代价",
    ]))
    write(os.path.join(root, "设定", "读者契约.md"), "# 读者契约\n核心题旨：力量必须付出代价。\n")
    write_json(os.path.join(root, "审稿", "demo_gate.json"), {
        "status": "passed",
        "reader_contract": {
            "theme": "力量必须付出代价",
            "dramatic_question": "主角是否愿意为守护他人承受反噬",
            "reader_promises": ["代价会逐步升级"],
            "delight_engine": ["每章让能力代价更尖锐"],
            "banned_drift": ["无脑升级"],
        },
    })
    write_json(os.path.join(root, "审稿", "state_ledger.json"), {
        "open_threads": [{"id": "hook_1", "status": "high", "question": "代价是否会反噬主角"}],
    })


class ArcPacketsTest(unittest.TestCase):
    def test_writes_arc_packet_and_plan(self):
        with tempfile.TemporaryDirectory() as root:
            make_project(root)
            got = subprocess.run(
                [sys.executable, ARC_PACKETS, root, "--arc", "1-3"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            packet_path = os.path.join(root, "写作任务", "弧段_第01-03章.md")
            plan_path = os.path.join(root, "审稿", "arc_plan_第01-03章.json")
            self.assertTrue(os.path.exists(packet_path))
            self.assertTrue(os.path.exists(plan_path))
            with open(packet_path, encoding="utf-8") as f:
                packet = f.read()
            self.assertIn("弧段写作任务包", packet)
            self.assertIn("力量必须付出代价", packet)
            self.assertIn("不得连续 3 章缺少", packet)
            self.assertIn("arc_gate.py", packet)
            with open(plan_path, encoding="utf-8") as f:
                plan = json.load(f)
            self.assertEqual(plan["chapters"], [1, 2, 3])
            self.assertEqual(plan["required_contract"]["theme"], "力量必须付出代价")


if __name__ == "__main__":
    unittest.main()
