#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""contract（novel-craft 侧入口）—— 单一真值源在 `novel/_lib/novel_contract.py`。

历史上这里是 novel 家族契约的另一份 vendored 模块，与 _lib 的 novel_contract.py 平行维护，
靠 test_contract_sync.py 守护「共享表 + 纯权利计算」逐值一致——但 base_meta/derive_title/parse_outputs
仍各自漂过。2026-06 统一：把本模块独有的阶段表/进度清单 + 富版 derive_title 并入 novel_contract.py，
本文件收敛为**薄转发**：复用 _lib 实现并把全部公共符号原样再导出，调用方 `from contract import X`
行为不变，但契约逻辑只剩一处（base_meta 沿用 _lib 简版＝各 init 现网行为；derive_title 取富版＝export 实际取用版）。

注：novel-craft/scripts 本就依赖 novel/_lib（qa_gate/store/waivers/project_io 等都从那里来），
转发 novel_contract 与既有架构一致；不影响其它创作线各自的 contract.py（各线独立）。
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "novel", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

_spec = importlib.util.spec_from_file_location(
    "_novel_lib_contract", os.path.join(_LIB, "novel_contract.py")
)
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)

# 把实现模块全部公共符号原样转发到本模块命名空间。
globals().update({k: v for k, v in vars(_impl).items() if not k.startswith("_")})

_IMPL_FILE = os.path.join(_LIB, "novel_contract.py")
