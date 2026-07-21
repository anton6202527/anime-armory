#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Charter 守护测试：load-bearing 闸不得被静默降级（宪法 B11 漫画线落地）。"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from consistency_charter import ALLOW_UNREGISTERED, CHARTER

GATE_SRC = (SCRIPT_DIR / "gate.py").read_text(encoding="utf-8")
GATE_TREE = ast.parse(GATE_SRC)
TOP_FUNCS = {node.name: node for node in GATE_TREE.body if isinstance(node, ast.FunctionDef)}


def func_source(name: str) -> str:
    node = TOP_FUNCS[name]
    return ast.get_source_segment(GATE_SRC, node) or ""


def test_charter_keys_are_real_gate_functions() -> None:
    missing = [name for name in CHARTER if name not in TOP_FUNCS]
    assert not missing, f"charter 登记了 gate.py 不存在的函数：{missing}——闸被删除/改名必须先改 charter"


def test_locked_gates_still_emit_block() -> None:
    for name, spec in CHARTER.items():
        if spec["required_severity"] != "block":
            continue
        src = func_source(name)
        assert '"block"' in src or "'block'" in src, (
            f"{name} 已不再产出 block——降级 load-bearing 闸必须先改 consistency_charter.py 并留痕"
        )


def test_unconditional_gates_do_not_condition_severity() -> None:
    """may_be_setting_gated=False 的闸不得写条件严重度（`"block" if …` 模式）。

    读 read_setting 取输入（风格锚来源、后端名）是合法的；被禁止的是把
    severity 本身放进条件表达式——那正是"静默降级"的手术入口。
    """
    for name, spec in CHARTER.items():
        if spec.get("may_be_setting_gated"):
            continue
        src = func_source(name)
        has_conditional_severity = '"block" if' in src or "'block' if" in src
        assert not (has_conditional_severity and "read_setting" in src), (
            f"{name} 同时出现 read_setting 与条件严重度（\"block\" if …）——设置门控 severity "
            "必须先把 charter 里 may_be_setting_gated 改为 True 并写明理由/日期"
        )


def test_every_block_capable_function_is_registered() -> None:
    """gate.py 新增能产 block 的顶层函数必须登记 enforcement 或加入豁免名单。"""
    unregistered = []
    for name in TOP_FUNCS:
        src = func_source(name)
        if ('"block"' in src or "'block'" in src) and name not in CHARTER and name not in ALLOW_UNREGISTERED:
            unregistered.append(name)
    assert not unregistered, (
        f"以下 gate 函数能产 block 但未在 consistency_charter.py 登记 enforcement：{unregistered}。"
        "强制力是一等公民——在 CHARTER 登记（或明确列入 ALLOW_UNREGISTERED 并说明为什么）。"
    )


def test_charter_entries_have_rationale_and_date() -> None:
    for name, spec in CHARTER.items():
        assert str(spec.get("rationale") or "").strip(), f"{name} 缺 rationale"
        assert str(spec.get("decided") or "").strip(), f"{name} 缺 decided 日期"
