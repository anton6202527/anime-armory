#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漂移护栏：novel/_lib/qa_gate.py 与 novel-craft/scripts/qa_gate.py 是同一份 gate 逻辑
的两份 vendored 拷贝，**只允许 contract 的 import 行不同**（一个绑 novel_contract，
一个绑 contract）。其余任何一行不一致即判失败，防止改一处忘另一处导致 gate 行为分叉。

从脚本自身目录跑：
    cd skills/novel-craft/scripts && python3 -m pytest test_qa_gate_sync.py
"""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CRAFT = os.path.join(REPO, "skills", "novel-craft", "scripts", "qa_gate.py")
LIB = os.path.join(REPO, "skills", "novel", "_lib", "qa_gate.py")

# 允许差异的行：contract 模块来源（vendoring 必然不同）
ALLOWED_DIFF = {
    "from novel_contract import normalize_rights_status, parse_regions",
    "from contract import normalize_rights_status, parse_regions",
}


class QaGateSyncTest(unittest.TestCase):
    def test_two_copies_identical_except_contract_import(self):
        craft = open(CRAFT, encoding="utf-8").read().splitlines()
        lib = open(LIB, encoding="utf-8").read().splitlines()
        self.assertEqual(len(craft), len(lib),
                         "两份 qa_gate 行数不同——已发生结构性漂移，请同步")
        for i, (a, b) in enumerate(zip(craft, lib), 1):
            if a == b:
                continue
            self.assertTrue(
                a.strip() in ALLOWED_DIFF and b.strip() in ALLOWED_DIFF,
                f"qa_gate 第 {i} 行非法漂移：\n  craft: {a!r}\n  lib:   {b!r}\n"
                f"两份拷贝只允许 contract import 行不同；其余必须逐字同步。",
            )


if __name__ == "__main__":
    unittest.main()
