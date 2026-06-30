#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
SENTRY = os.path.join(HERE, "reader_contract_sentry.py")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def make_project(root, *, progress=True, theme=True):
    write(os.path.join(root, "章节", "第03章.md"), "# 第3章 转折\n主角第一次承认力量的代价。\n")
    write(os.path.join(root, "设定", "读者契约.md"), "# 读者契约\n核心题旨：力量必须付出代价。\n")
    write_json(os.path.join(root, "审稿", "demo_gate.json"), {
        "schema_version": 1,
        "kind": "novel_demo_gate",
        "status": "passed",
        "reader_contract": {
            "theme": "力量必须付出代价",
            "reader_promises": ["代价会逐步升级"],
            "banned_drift": ["无脑升级"],
        },
    })
    delta = {
        "schema_version": 1,
        "kind": "novel_state_delta",
        "chapter": 3,
        "new_facts": [],
    }
    if progress:
        delta["reader_contract_progress"] = ["主角用痛觉换来胜利，代价第一次升级。"]
    if theme:
        delta["theme_alignment"] = "本章把力量与代价绑定，回应核心题旨。"
    write_json(os.path.join(root, "审稿", "state_delta_第03章.json"), delta)


class ReaderContractSentryTest(unittest.TestCase):
    def test_passes_when_delta_tracks_reader_contract(self):
        with tempfile.TemporaryDirectory() as root:
            make_project(root)
            got = subprocess.run(
                [sys.executable, SENTRY, root, "--chapter", "第03章"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            self.assertIn("读者契约检查通过", got.stdout)
            report_path = os.path.join(root, "审稿", "reader_contract_sentry_第03章.json")
            with open(report_path, encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report["status"], "clean")

    def test_blocks_missing_reader_contract_progress(self):
        with tempfile.TemporaryDirectory() as root:
            make_project(root, progress=False)
            got = subprocess.run(
                [sys.executable, SENTRY, root, "--chapter", "3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("reader_contract_progress", got.stdout)

    def test_blocks_missing_theme_alignment(self):
        with tempfile.TemporaryDirectory() as root:
            make_project(root, theme=False)
            got = subprocess.run(
                [sys.executable, SENTRY, root, "--chapter", "3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("theme_alignment", got.stdout)


if __name__ == "__main__":
    unittest.main()
