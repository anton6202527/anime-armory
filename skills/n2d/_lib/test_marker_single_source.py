#!/usr/bin/env python3
"""一致性 lint 共享词表单一真值源守护（P0-1）。

历史 bug 家族「const 漂离消费端」：image_qc / gate / face_drift_risk / shot_risk_audit 各存一份
多主体/强情绪近义词表，成员逐渐漂移 → 同一镜「出图放行 / 质检阻断」口径分裂。词表已上提
n2d_const 单一真值源，本测试钉死两件事：
  1) 放行集 = 分层 + 原生 + 执行策略三类并集（结构不变量）；
  2) 四个消费端**不得再用字面量元组重定义**这些 canonical 名字（只能 import / alias），
     否则 block ⊆ review block 的口径一致性会再次靠人手维护而漂移。

跑：cd skills/n2d/_lib && python3 -m pytest test_marker_single_source.py
"""
from __future__ import annotations

import os
import re

import n2d_const as C

# 收口到 _lib 的 canonical 词表名字。消费端可 `from n2d_const import X` 或 `Y = X` 别名，
# 但不得出现 `X = (...)` 字面量元组重定义。
CANONICAL_NAMES = (
    "STRONG_EMOTION_MARKERS",
    "EXPRESSION_LIB_MARKERS",
    "SPLIT_COMPOSITE_MARKERS",
    "NATIVE_MULTI_SUBJECT_STRATEGY_MARKERS",
    "MULTI_SUBJECT_EXECUTION_STRATEGY_MARKERS",
    "MULTI_SUBJECT_SLOT_MARKERS",
    "MULTI_SUBJECT_POSITION_MARKERS",
    "MULTI_SUBJECT_ACCEPTING_MARKERS",
)

# skills/ 根（本文件在 skills/n2d/_lib/）
_SKILLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONSUMER_FILES = (
    os.path.join(_SKILLS_ROOT, "n2d-image", "scripts", "image_qc.py"),
    os.path.join(_SKILLS_ROOT, "n2d-image", "scripts", "face_drift_risk.py"),
    os.path.join(_SKILLS_ROOT, "n2d-script", "scripts", "shot_risk_audit.py"),
    os.path.join(_SKILLS_ROOT, "n2d-review", "scripts", "gate.py"),
)


def test_canonical_sets_exist_and_nonempty():
    for name in CANONICAL_NAMES:
        assert hasattr(C, name), f"n2d_const 缺 canonical 词表 {name}"
        assert len(getattr(C, name)) > 0, f"{name} 不应为空"


def test_accepting_union_invariant():
    """放行集 = 分层 + 原生 + 执行策略三类并集（image_qc 放宽 / gate 判定 / shot_risk 判定同源）。"""
    expected = (
        C.SPLIT_COMPOSITE_MARKERS
        + C.NATIVE_MULTI_SUBJECT_STRATEGY_MARKERS
        + C.MULTI_SUBJECT_EXECUTION_STRATEGY_MARKERS
    )
    assert C.MULTI_SUBJECT_ACCEPTING_MARKERS == expected


def test_no_consumer_redefines_canonical_literal():
    """四个消费端不得用 `NAME = (` 字面量元组重定义 canonical 词表（只能 import / 别名）。"""
    offenders = []
    for path in CONSUMER_FILES:
        assert os.path.exists(path), f"消费端文件不存在：{path}"
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        for name in CANONICAL_NAMES:
            # 行首（允许缩进）NAME = ( …  → 字面量元组重定义。别名 NAME = OTHER 不匹配 `= (`。
            if re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\(", src):
                offenders.append(f"{os.path.relpath(path, _SKILLS_ROOT)}::{name}")
    assert not offenders, (
        "以下消费端仍用字面量元组重定义了 canonical 词表（应改 import / 别名，"
        f"否则会再次漂离 n2d_const 单一真值源）：{offenders}"
    )


def test_strong_emotion_has_no_dup():
    """单一真值源不应含重复项（历史 image_qc 副本有重复『狂怒』）。"""
    s = C.STRONG_EMOTION_MARKERS
    assert len(s) == len(set(s)), f"STRONG_EMOTION_MARKERS 有重复项：{[x for x in s if s.count(x) > 1]}"


if __name__ == "__main__":
    test_canonical_sets_exist_and_nonempty()
    test_accepting_union_invariant()
    test_no_consumer_redefines_canonical_literal()
    test_strong_emotion_has_no_dup()
    print("ok")
