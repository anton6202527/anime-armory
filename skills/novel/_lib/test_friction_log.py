#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for friction_log.py — production-friction 埋点 for novel-*.

Run from this directory:
    cd skills/novel/_lib && python3 -m pytest test_friction_log.py
"""
import os
import tempfile
import unittest

import friction_log as fl


class TestFrictionLog(unittest.TestCase):
    def test_append_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            sig = fl.log_friction(
                tmp, "score_coverage_gap", skill="novel-score", severity="warn",
                title="t", detail="d", suggested_fix="fix", key="2026-06-27",
            )
            self.assertEqual(sig["status"], "open")
            self.assertEqual(sig["kind"], "score_coverage_gap")
            signals = fl.load_signals(tmp)
            self.assertEqual(len(signals), 1)
            self.assertTrue(fl.signal_log_path(tmp).endswith(
                os.path.join("生产数据", "优化信号.jsonl")))

    def test_idempotent_per_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            for _ in range(3):
                fl.log_friction(tmp, "k", skill="s", severity="warn",
                                title="t", detail="d", key="same")
            self.assertEqual(len(fl.load_signals(tmp)), 1)

    def test_different_key_distinct_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            fl.log_friction(tmp, "k", skill="s", severity="warn", title="t", detail="d", key="a")
            fl.log_friction(tmp, "k", skill="s", severity="warn", title="t", detail="d", key="b")
            self.assertEqual(len(fl.open_signatures(tmp)), 2)

    def test_invalid_severity_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            sig = fl.log_friction(tmp, "k", skill="s", severity="boom",
                                  title="t", detail="d", key="x")
            self.assertEqual(sig["severity"], "advice")

    def test_resolve_signals_stops_resurfacing(self):
        with tempfile.TemporaryDirectory() as tmp:
            sig = fl.log_friction(tmp, "k", skill="s", severity="warn",
                                  title="t", detail="d", key="x")
            n = fl.resolve_signals(tmp, [sig["signature"]])
            self.assertEqual(n, 1)
            self.assertEqual(len(fl.open_signatures(tmp)), 0)
            # resolved entry is retained, just not open
            self.assertEqual(len(fl.load_signals(tmp)), 1)

    def test_falsy_root_is_noop(self):
        self.assertIsNone(fl.log_friction("", "k", skill="s", severity="warn",
                                          title="t", detail="d"))


if __name__ == "__main__":
    unittest.main()
