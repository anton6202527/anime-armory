#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile

import style_sheet_check


def test_style_sheet_check_blocks_missing_sheet():
    with tempfile.TemporaryDirectory() as root:
        report = style_sheet_check.build_check(root)
        assert report["blocking"] == 1
        assert report["findings"][0]["id"] == "STYLE-SHEET-MISSING"


def test_style_sheet_check_warns_on_todo_and_missing_sections():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "修订"), exist_ok=True)
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("# 第1章\n")
        with open(os.path.join(root, "修订", "style_sheet.md"), "w", encoding="utf-8") as f:
            f.write("# Style Sheet\n## 术语\n- 待补\n")

        report = style_sheet_check.build_check(root)
        assert report["blocking"] == 0
        assert report["warnings"] >= 1
        ids = {item["id"] for item in report["findings"]}
        assert "STYLE-SHEET-TODO" in ids
