#!/usr/bin/env python3
"""Tests for split_novel project scaffolding."""
import os
import subprocess
import sys


def test_split_novel_scaffold_includes_base_visual_style_contract(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text("第一章\n她推门而入。\n第二章\n风声忽起。\n", encoding="utf-8")
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [sys.executable, script, str(novel), "--out", str(out), "--limit", "1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    style = (out / "设定库" / "global_style.md").read_text(encoding="utf-8")
    assert "## 基础视觉风格" in style
    assert "## 基础视觉风格契约（style_contract 源头）" in style
    assert "风格名" in style
    assert "风格禁忌" in style


def test_split_novel_scaffold_uses_project_base_visual_style(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text("第一章\n她推门而入。\n第二章\n风声忽起。\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "_设置.md").write_text("- 基础视觉风格: 二次元赛璐璐\n", encoding="utf-8")
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [sys.executable, script, str(novel), "--out", str(out), "--limit", "1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    style = (out / "设定库" / "global_style.md").read_text(encoding="utf-8")
    assert "二次元赛璐璐" in style
    assert "风格名：二次元赛璐璐" in style
    assert "赛璐璐块面上色" in style
