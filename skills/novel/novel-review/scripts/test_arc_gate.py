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

    def test_local_resolution_signal_warns_without_blocking_core_arc(self):
        with tempfile.TemporaryDirectory() as root:
            make_project(root)
            write_json(os.path.join(root, "_meta.json"), {"target_chapters": 100})
            write(os.path.join(root, "设定", "读者契约.md"),
                  "核心戏剧问题：主角能否夺回王座？\n- 终局必须回答：他是否成为新王？\n")
            delta_path = os.path.join(root, "审稿", "state_delta_第02章.json")
            with open(delta_path, encoding="utf-8") as f:
                delta = json.load(f)
            delta["reader_contract_progress"] = ["局部旧案真相大白，支线谜底揭晓。"]
            delta["theme_alignment"] = "局部支线收口，但主线仍推进。"
            write_json(delta_path, delta)

            got = subprocess.run(
                [sys.executable, ARC_GATE, root, "--arc", "1-3"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            report_path = os.path.join(root, "审稿", "arc_gate_第01-03章.json")
            with open(report_path, encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report["blocking"], 0)
            self.assertTrue(any(f["type"] == "resolution_signal_needs_review" for f in report["findings"]))

    def test_core_resolution_keyword_signal_is_advisory_per_b10(self):
        # 关键词命中收束信号属脆弱启发式（B10）：只提醒人审，不硬阻断。
        with tempfile.TemporaryDirectory() as root:
            make_project(root)
            write_json(os.path.join(root, "_meta.json"), {"target_chapters": 100})
            write(os.path.join(root, "设定", "读者契约.md"),
                  "核心戏剧问题：主角能否夺回王座？\n- 终局必须回答：他是否成为新王？\n")
            delta_path = os.path.join(root, "审稿", "state_delta_第02章.json")
            with open(delta_path, encoding="utf-8") as f:
                delta = json.load(f)
            delta["reader_contract_progress"] = ["主线完结：他是否成为新王？答案已经揭晓。"]
            delta["theme_alignment"] = "核心问题解决。"
            write_json(delta_path, delta)

            got = subprocess.run(
                [sys.executable, ARC_GATE, root, "--arc", "1-3"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            report_path = os.path.join(root, "审稿", "arc_gate_第01-03章.json")
            with open(report_path, encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report["blocking"], 0)
            hits = [f for f in report["findings"] if f["type"] == "premature_resolution_signal"]
            self.assertTrue(hits)
            self.assertEqual(hits[0]["severity"], "建议级")

    def test_declared_core_resolution_blocks_before_finale(self):
        # state_delta 显式结构化声明 core_conflict_resolved=true → 确定性硬阻断。
        with tempfile.TemporaryDirectory() as root:
            make_project(root)
            write_json(os.path.join(root, "_meta.json"), {"target_chapters": 100})
            write(os.path.join(root, "设定", "读者契约.md"),
                  "核心戏剧问题：主角能否夺回王座？\n- 终局必须回答：他是否成为新王？\n")
            delta_path = os.path.join(root, "审稿", "state_delta_第02章.json")
            with open(delta_path, encoding="utf-8") as f:
                delta = json.load(f)
            delta["core_conflict_resolved"] = True
            write_json(delta_path, delta)

            got = subprocess.run(
                [sys.executable, ARC_GATE, root, "--arc", "1-3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("premature_core_resolution_declared", got.stdout)


if __name__ == "__main__":
    unittest.main()
