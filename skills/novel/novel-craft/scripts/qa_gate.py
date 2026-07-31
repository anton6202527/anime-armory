#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qa_gate（novel-craft 侧入口）—— 单一真值源在 `novel/_lib/qa_gate.py`。

历史上这里是 `novel/_lib/qa_gate.py` 的整份 vendored 拷贝，靠 `test_qa_gate_sync.py`
防漂移。但 novel-craft/scripts 本就依赖 novel/_lib（project_io / report_snapshot /
waivers / novel_contract 都从那里 import），再单独 vendoring 一份 849 行 gate 逻辑纯属
维护负担（每改一条 gate 规则都要双改）。故收敛为**薄转发**：直接复用 _lib 的实现并把其
全部公共符号原样再导出，调用方 `import qa_gate` 的行为完全不变，但 gate 逻辑只剩一处。

注：_lib 实现里 `normalize_rights_status / parse_regions` 取自 `novel_contract`，与本线
`contract.py` 的同名函数已验证逐字一致，故转发不改变 rights 判定行为。
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

_spec = importlib.util.spec_from_file_location(
    "_novel_lib_qa_gate", os.path.join(_LIB, "qa_gate.py")
)
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)

# 把实现模块的全部公共符号原样转发到本模块命名空间。
globals().update({k: v for k, v in vars(_impl).items() if not k.startswith("_")})

# 供需要时定位真正实现（测试/调试用）。
_IMPL_FILE = os.path.join(_LIB, "qa_gate.py")
