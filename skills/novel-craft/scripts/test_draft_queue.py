#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draft_queue.py tests."""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT_QUEUE = os.path.join(HERE, "draft_queue.py")


def make_project(root):
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "create",
            "title": "队列测试",
            "target_chapters": 5,
            "demo_chapters": 2,
        }, f, ensure_ascii=False)
    with open(os.path.join(root, "章节", "第03章.md"), "w", encoding="utf-8") as f:
        f.write("# 第3章 已完成\n")


class DraftQueueTest(unittest.TestCase):
    def test_init_claim_done_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run(
                [sys.executable, DRAFT_QUEUE, "--json", tmp, "init"],
                capture_output=True, text=True, check=True,
            )
            qpath = os.path.join(tmp, "写作任务", "draft_queue.json")
            self.assertTrue(os.path.exists(qpath))
            self.assertTrue(os.path.exists(os.path.join(tmp, "写作任务", "draft_queue.lock")))
            with open(qpath, encoding="utf-8") as f:
                queue = json.load(f)
            self.assertEqual(queue["chapters"]["03"]["status"], "done")
            self.assertEqual(queue["chapters"]["04"]["status"], "todo")

            claimed = subprocess.run(
                [sys.executable, DRAFT_QUEUE, "--json", tmp, "claim", "--agent", "a1"],
                capture_output=True, text=True, check=True,
            )
            payload = json.loads(claimed.stdout)
            self.assertEqual(payload["claimed"]["chapter"], 4)
            self.assertEqual(payload["claimed"]["status"], "claimed")

            subprocess.run(
                [sys.executable, DRAFT_QUEUE, "--json", tmp, "done", "4", "--agent", "a1"],
                capture_output=True, text=True, check=True,
            )
            with open(qpath, encoding="utf-8") as f:
                queue = json.load(f)
            self.assertEqual(queue["chapters"]["04"]["status"], "done")

    def test_specific_claim_blocks_done_chapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run(
                [sys.executable, DRAFT_QUEUE, tmp, "init"],
                capture_output=True, text=True, check=True,
            )
            got = subprocess.run(
                [sys.executable, DRAFT_QUEUE, tmp, "claim", "--chapter", "3"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("没有可认领章节", got.stderr)


if __name__ == "__main__":
    unittest.main()

