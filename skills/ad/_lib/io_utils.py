#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tiny shared filesystem helpers — JSON / text read+write with the repo conventions.

These 4–5 helpers were copy-defined in ~27 scripts with small, diverging variants
(strict vs resilient JSON load, default args). This is the single source of truth for
*new* code and **opportunistic** migration — NOT a big-bang replacement; existing
scripts keep their local copy until touched. `write_json` fixes the repo convention
(`ensure_ascii=False, indent=2`, create parents); `load_json` exposes both error modes
via `resilient` so a delegating wrapper can byte-match its old behavior.

Note: a loader that turns a corrupt file into a *domain finding* (e.g. a QA BLOCK) is
NOT generic IO — keep those local. No business semantics live here.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any


def load_json(path: str, default: Any = None, *, resilient: bool = False) -> Any:
    """Read JSON from `path`.

    Missing file → `default`. By default a corrupt file raises (surfacing the defect);
    pass `resilient=True` to return `default` on parse/OS errors instead.
    """
    if not os.path.exists(path):
        return default
    if resilient:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_text_atomic(path: str, text: str) -> None:
    """原子写文本：同目录 temp + os.replace，写一半被打断也不会留下半个文件。

    temp 必须与目标同目录（同一文件系统）os.replace 才是原子重命名。
    """
    path = os.fspath(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent or ".", prefix=os.path.basename(path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json_atomic(path: str, payload: Any) -> None:
    """原子写 JSON（`ensure_ascii=False, indent=2` + 末尾换行），creating parents."""
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def write_json(path: str, payload: Any) -> None:
    """Write `payload` as UTF-8 JSON (`ensure_ascii=False, indent=2`), creating parents.

    自 P0 资金安全改造起为原子实现（等价 `write_json_atomic`）：job 账本这类
    「先花钱后落账」的文件绝不能被进程中断写坏。
    """
    write_json_atomic(path, payload)


def read_text(path: str, default: str = "") -> str:
    """Read a UTF-8 text file; return `default` when it does not exist."""
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path: str, text: str) -> None:
    """Write `text` to a UTF-8 file, creating parent directories."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_meta(root: str) -> dict:
    """Read `<root>/_meta.json`, returning `{}` when absent (strict on corrupt)."""
    return load_json(os.path.join(root, "_meta.json"), {})
