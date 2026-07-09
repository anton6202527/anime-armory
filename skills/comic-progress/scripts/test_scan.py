#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import scan


def write_progress(root: Path, finishing_label: str) -> None:
    (root / "_进度.md").write_text(
        f"""# 进度

| 话 | 源本/企划 | 漫画脚本 | 缩略分镜 | 页面排版 | {finishing_label} | 出图包 | 出图 | 嵌字合成 | 审查 |
|---|---|---|---|---|---|---|---|---|---|
| 第1话 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
""",
        encoding="utf-8",
    )


def test_summarize_project_accepts_canonical_finishing_column(tmp_path: Path) -> None:
    write_progress(tmp_path, "原稿收尾")

    summary = scan.summarize_project(tmp_path)

    assert summary["fronts"][0]["complete"] is True
    assert summary["fronts"][0]["next_stage"] == "完成"


def test_summarize_project_accepts_legacy_finishing_column(tmp_path: Path) -> None:
    write_progress(tmp_path, "传统收尾")

    summary = scan.summarize_project(tmp_path)

    assert summary["fronts"][0]["complete"] is True
    assert summary["fronts"][0]["next_stage"] == "完成"
