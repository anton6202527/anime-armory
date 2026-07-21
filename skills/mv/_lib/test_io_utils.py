#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""io_utils tests（幂等写盘 write_json_stable）。

Can run without pytest:
    python3 skills/mv/_lib/test_io_utils.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io_utils  # noqa: E402


class WriteJsonStableTest(unittest.TestCase):
    def test_skips_write_when_only_generated_at_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "clip_plan.json")
            io_utils.write_json(path, {"generated_at": "2026-07-19", "clips": [1, 2]})
            before = open(path, "rb").read()
            wrote = io_utils.write_json_stable(path, {"generated_at": "2026-07-20", "clips": [1, 2]})
            self.assertFalse(wrote)
            self.assertEqual(open(path, "rb").read(), before)  # 字节稳定 → 下游 hash 链不失效

    def test_writes_when_substantive_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "clip_plan.json")
            io_utils.write_json(path, {"generated_at": "2026-07-19", "clips": [1, 2]})
            wrote = io_utils.write_json_stable(path, {"generated_at": "2026-07-20", "clips": [1, 2, 3]})
            self.assertTrue(wrote)
            self.assertIn("3", open(path, encoding="utf-8").read())

    def test_writes_when_file_missing_or_not_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "new.json")
            self.assertTrue(io_utils.write_json_stable(path, {"generated_at": "x", "a": 1}))
            io_utils.write_json(path, [1, 2])
            self.assertTrue(io_utils.write_json_stable(path, {"generated_at": "x", "a": 1}))


if __name__ == "__main__":
    unittest.main()
