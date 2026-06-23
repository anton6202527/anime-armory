#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reconcile_ledger safety tests. Can run without pytest."""
import importlib.util
import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "reconcile_ledger.py")

_spec = importlib.util.spec_from_file_location("reconcile_ledger", SCRIPT)
reconcile_ledger = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reconcile_ledger)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verification_hashes(root):
    return {
        "chapter_file_hash": sha256_file(os.path.join(root, "章节", "第01章.md")),
        "delta_hash": sha256_file(os.path.join(root, "审稿", "state_delta_第01章.json")),
    }


def make_project(root):
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("# 第1章 开端\n<!-- meta: demo=false -->\n王敦发现第一条线索。\n")
    with open(os.path.join(root, "审稿", "state_delta_第01章.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_state_delta",
            "chapter": 1,
            "new_facts": ["王敦发现第一条线索"],
            "character_changes": [],
            "open_threads_added": ["第一条线索"],
            "threads_resolved": [],
        }, f, ensure_ascii=False)


class WriteJsonAtomicTest(unittest.TestCase):
    def test_write_json_leaves_no_tmp_and_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "审稿", "state_ledger.json")
            reconcile_ledger.write_json(path, {"k": "值", "n": 1})
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"k": "值", "n": 1})
            # 临时文件不残留
            self.assertEqual([p for p in os.listdir(os.path.dirname(path)) if ".tmp." in p], [])

    def test_failed_write_does_not_corrupt_existing_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "审稿", "state_ledger.json")
            reconcile_ledger.write_json(path, {"good": True})
            # 不可序列化的 payload 会在 json.dump 阶段抛错——旧账本必须原样保留、无残留 tmp
            with self.assertRaises(TypeError):
                reconcile_ledger.write_json(path, {"bad": object()})
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"good": True})
            self.assertEqual([p for p in os.listdir(os.path.dirname(path)) if ".tmp." in p], [])


class ReconcileLedgerSafetyTest(unittest.TestCase):
    def test_auto_does_not_merge_without_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--auto"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("--auto 已废弃", got.stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp, "审稿", "state_ledger.json")))

    def test_merge_requires_verified_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--merge"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("--verified", got.stderr)

            generic = os.path.join(tmp, "审稿", "generic_verify.json")
            with open(generic, "w", encoding="utf-8") as f:
                json.dump({"status": "ok"}, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--merge", "--verified", generic],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("缺少 chapter", got.stderr)

            stale = os.path.join(tmp, "审稿", "stale_verify.json")
            with open(stale, "w", encoding="utf-8") as f:
                json.dump({"chapter": 1, "status": "ok", "notes": "旧核对结论"}, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--merge", "--verified", stale],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("chapter_file_hash", got.stderr)

            hashes = verification_hashes(tmp)
            mismatch = os.path.join(tmp, "审稿", "mismatch_verify.json")
            with open(mismatch, "w", encoding="utf-8") as f:
                json.dump({
                    "chapter": 1,
                    "status": "ok",
                    "chapter_file_hash": "bad",
                    "delta_hash": hashes["delta_hash"],
                }, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--merge", "--verified", mismatch],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("不匹配", got.stderr)

            verified = os.path.join(tmp, "审稿", "state_verify_第01章.json")
            with open(verified, "w", encoding="utf-8") as f:
                payload = {"chapter": 1, "status": "ok", "notes": "delta 与正文一致"}
                payload.update(hashes)
                json.dump(payload, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--merge", "--verified", verified],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            with open(os.path.join(tmp, "审稿", "state_ledger.json"), encoding="utf-8") as f:
                ledger = json.load(f)
            self.assertIn("王敦发现第一条线索", ledger["setting_facts"])
            self.assertEqual(ledger["chapter_deltas"]["chapter_01"]["verification"]["status"], "ok")


class StampHashesTest(unittest.TestCase):
    """--stamp-hashes：写后即时对账省去手抄 sha256，但不削弱完整性核心。"""

    def test_stamp_hashes_merges_conclusion_without_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            concl = os.path.join(tmp, "审稿", "state_verify_第01章.json")
            with open(concl, "w", encoding="utf-8") as f:
                json.dump({"chapter": 1, "status": "ok", "notes": "一致"}, f, ensure_ascii=False)
            # 不带 --stamp-hashes：缺 hash 仍按严格路径拒绝（完整性默认不变）
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--merge", "--verified", concl],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("chapter_file_hash", got.stderr)
            # 带 --stamp-hashes：自动盖当前文件 hash 并合并
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--merge", "--verified", concl, "--stamp-hashes"],
                capture_output=True, text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            with open(os.path.join(tmp, "审稿", "state_ledger.json"), encoding="utf-8") as f:
                ledger = json.load(f)
            v = ledger["chapter_deltas"]["chapter_01"]["verification"]
            self.assertEqual(v["status"], "ok")
            self.assertEqual(v.get("hash_source"), "script_stamped")
            self.assertEqual(set(v.get("stamped_hashes", [])), {"chapter_file_hash", "delta_hash"})

    def test_stamp_hashes_still_rejects_explicit_wrong_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            concl = os.path.join(tmp, "审稿", "state_verify_第01章.json")
            with open(concl, "w", encoding="utf-8") as f:
                # 显式写了一个错的 chapter_file_hash —— 即便 --stamp-hashes 也必须拦（防写后又改正文）
                json.dump({"chapter": 1, "status": "ok", "chapter_file_hash": "deadbeef"}, f, ensure_ascii=False)
            got = subprocess.run(
                [sys.executable, SCRIPT, tmp, "--chapter", "1", "--merge", "--verified", concl, "--stamp-hashes"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("不匹配", got.stderr)


class RollupTest(unittest.TestCase):
    def _write_ledger(self, root, ledger):
        os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
        path = os.path.join(root, "审稿", "state_ledger.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False)
        return path

    def test_rollup_compacts_old_deltas_keeps_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_ledger(tmp, {
                "schema_version": 1, "kind": "novel_state_ledger",
                "characters": {"林越": {"history": [{"chapter": 1}], "current_state": {}}},
                "setting_facts": ["铜钱线索"],
                "open_threads": [{"chapter": 1, "thread": "铜钱来历"}],
                "resolved_threads": [],
                "chapter_deltas": {
                    "chapter_01": {"merged_at": "x", "summary": {
                        "new_facts": ["a", "b"],
                        "character_changes": [{"name": "林越", "change": "觉醒"}],
                        "open_threads_added": ["铜钱来历"], "threads_resolved": []},
                        "verification": {"status": "ok", "chapter_file_hash": "h",
                                         "delta_hash": "d", "notes": "很长的核对说明" * 20}},
                    "chapter_09": {"merged_at": "y", "summary": {"new_facts": ["z"]},
                                   "verification": {"status": "ok"}},
                },
            })
            got = subprocess.run([sys.executable, SCRIPT, tmp, "--rollup", "--before", "5"],
                                 capture_output=True, text=True)
            self.assertEqual(got.returncode, 0, got.stderr)
            with open(path, encoding="utf-8") as f:
                out = json.load(f)
            # ch01 < 5 → 压缩成计数，verification 只留 status
            c01 = out["chapter_deltas"]["chapter_01"]
            self.assertTrue(c01["summary"]["rolled"])
            self.assertEqual(c01["summary"]["new_facts"], 2)
            self.assertEqual(c01["summary"]["characters_touched"], ["林越"])
            self.assertEqual(c01["verification"], {"status": "ok"})
            # ch09 >= 5 → 原样保留
            self.assertNotIn("rolled", out["chapter_deltas"]["chapter_09"]["summary"])
            # canonical 状态一律不动
            self.assertEqual(out["setting_facts"], ["铜钱线索"])
            self.assertIn("林越", out["characters"])
            self.assertEqual(out["rollups"][0]["rolled"], 1)
            # 幂等：再跑一次不再 rollup
            got2 = subprocess.run([sys.executable, SCRIPT, tmp, "--rollup", "--before", "5"],
                                  capture_output=True, text=True)
            self.assertIn("rollup 0 章", got2.stdout)

    def test_rollup_requires_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "审稿"), exist_ok=True)
            got = subprocess.run([sys.executable, SCRIPT, tmp, "--rollup"],
                                 capture_output=True, text=True)
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("--before", got.stderr)


if __name__ == "__main__":
    unittest.main()
