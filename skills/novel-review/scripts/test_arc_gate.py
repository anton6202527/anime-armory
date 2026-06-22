#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
ARC_GATE = os.path.join(HERE, "arc_gate.py")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def make_project(root, *, with_progress=True, with_theme=True):
    write_json(os.path.join(root, "审稿", "demo_gate.json"), {
        "status": "passed",
        "reader_contract": {
            "theme": "力量必须付出代价",
            "reader_promises": ["代价会逐步升级"],
            "banned_drift": ["无脑升级"],
        },
    })
    for chapter in range(1, 4):
        write(os.path.join(root, "章节", f"第{chapter:02d}章.md"), f"# 第{chapter}章\n正文推进代价。\n")
        delta = {"schema_version": 1, "kind": "novel_state_delta", "chapter": chapter}
        if with_progress:
            delta["reader_contract_progress"] = [f"第{chapter}章让代价更具体。"]
        if with_theme:
            delta["theme_alignment"] = "力量必须付出代价。"
        write_json(os.path.join(root, "审稿", f"state_delta_第{chapter:02d}章.json"), delta)


class ArcGateTest(unittest.TestCase):
    def test_passes_when_arc_has_contract_progress(self):
        with tempfile.TemporaryDirectory() as root:
            make_project(root)
            got = subprocess.run(
                [sys.executable, ARC_GATE, root, "--arc", "1-3"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            report_path = os.path.join(root, "审稿", "arc_gate_第01-03章.json")
            with open(report_path, encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report["blocking"], 0)

    def test_blocks_three_chapter_reader_contract_stall(self):
        with tempfile.TemporaryDirectory() as root:
            make_project(root, with_progress=False)
            got = subprocess.run(
                [sys.executable, ARC_GATE, root, "--arc", "1-3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("reader_contract_stall", got.stdout)

    def test_blocks_arc_without_theme_alignment(self):
        with tempfile.TemporaryDirectory() as root:
            make_project(root, with_theme=False)
            got = subprocess.run(
                [sys.executable, ARC_GATE, root, "--arc", "1-3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("arc_without_theme_alignment", got.stdout)


if __name__ == "__main__":
    unittest.main()
