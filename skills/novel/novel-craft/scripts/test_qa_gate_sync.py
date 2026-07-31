#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单一真值源护栏：gate 逻辑只允许有一份实现（novel/_lib/qa_gate.py）；
novel-craft/scripts/qa_gate.py 必须是薄转发 shim，把 _lib 的公共符号原样再导出，
不得自己再 fork 一份 gate 逻辑（历史上是 849 行 vendored 拷贝，已收敛）。

从脚本自身目录跑：
    cd skills/novel/novel-craft/scripts && python3 -m pytest test_qa_gate_sync.py
"""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CRAFT = os.path.join(REPO, "skills", "novel", "novel-craft", "scripts", "qa_gate.py")
LIB = os.path.join(REPO, "skills", "novel", "_lib", "qa_gate.py")

# 消费方真正用到的公共 API；shim 必须把这些原样转发过来。
PUBLIC_API = (
    "collect_gate_status",
    "format_gate_status",
    "validate_review_report_schema",
    "validate_score_report_schema",
    "missing_score_report_scope",
)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class QaGateSingleSourceTest(unittest.TestCase):
    def test_craft_is_thin_shim(self):
        text = open(CRAFT, encoding="utf-8").read()
        # 真正的 gate 逻辑（数百行）只能在 _lib；craft 侧必须是小转发文件。
        self.assertLess(len(text.splitlines()), 60,
                        "novel-craft/scripts/qa_gate.py 又变胖了——gate 逻辑应只在 _lib，这里只转发")
        # 不得自己重新定义 gate 函数（应来自转发）。
        self.assertNotIn("def collect_gate_status", text,
                         "shim 不应自行定义 gate 逻辑；应从 novel/_lib/qa_gate.py 转发")

    def test_lib_is_real_source(self):
        lib_text = open(LIB, encoding="utf-8").read()
        self.assertIn("def collect_gate_status", lib_text,
                      "单一真值源 novel/_lib/qa_gate.py 必须含真正的 gate 实现")

    def test_shim_reexports_public_api(self):
        craft = _load("craft_qa_gate", CRAFT)
        for name in PUBLIC_API:
            self.assertTrue(hasattr(craft, name),
                            f"shim 缺转发公共符号：{name}")
            self.assertTrue(callable(getattr(craft, name)),
                            f"转发的 {name} 不可调用")


if __name__ == "__main__":
    unittest.main()
