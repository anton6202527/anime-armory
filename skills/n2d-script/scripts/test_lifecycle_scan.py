#!/usr/bin/env python3
"""Tests for lifecycle_scan.py (Gap2 character visual-lifecycle pre-scan).

Run from this script's own directory:
    cd skills/n2d-script/scripts && python -m pytest test_lifecycle_scan.py
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lifecycle_scan as L  # noqa: E402


def _mk(eps, cards=()):
    d = tempfile.mkdtemp()
    for i, body in eps:
        ep = Path(d) / "脚本" / f"第{i}集"
        ep.mkdir(parents=True)
        (ep / "raw.txt").write_text(body, encoding="utf-8")
    cdir = Path(d) / "设定库" / "characters"
    cdir.mkdir(parents=True, exist_ok=True)
    for name in cards:
        (cdir / f"{name}.md").write_text("# 角色卡 — " + name, encoding="utf-8")
    return d


def test_detects_costume_age_and_form_milestones():
    root = _mk([
        (1, "第一章\n沈念醒来，一身素衣。"),
        (3, "第三章\n大婚之日，沈念换上嫁衣，凤冠霞帔。"),
        (20, "第二十章\n十年后，沈念鬓生华发，当年的疤痕仍在。"),
    ], cards=["沈念"])
    ms, names = L.scan(root)
    assert "沈念" in names
    cats = {m["category"] for m in ms}
    assert {"换装/造型", "时间/年龄", "形态/状态"} <= cats
    # 角色归属命中
    assert any(m["unit"] == "第3集" and "沈念" in m["characters"] for m in ms)


def test_no_signal_returns_empty():
    root = _mk([(1, "第一章\n两人喝茶聊天，气氛融洽。")], cards=["甲"])
    ms, _ = L.scan(root)
    assert ms == []


def test_write_preserves_human_region():
    root = _mk([(1, "第一章\n她换上战甲。")], cards=["阿离"])
    out = Path(root) / "设定库" / "characters" / "_生命周期.md"

    def regen():
        ms, names = L.scan(root)
        L.write_md(root, L.render_md(root, ms, names))

    regen()
    # 人工在人工区写一行，并放一段假"旧自动段"
    txt = out.read_text(encoding="utf-8")
    human = txt.split(L.AUTO_MARKER)[0] + "| 第1集 | 阿离 | 换战甲 | 新建战甲变体 |\n"
    out.write_text(human + "\n" + L.AUTO_MARKER + "\n旧自动段\n", encoding="utf-8")
    # 重扫重写：人工区保留，自动段刷新
    regen()
    txt2 = out.read_text(encoding="utf-8")
    assert "新建战甲变体" in txt2          # 人工区保留
    assert "旧自动段" not in txt2          # 自动段被刷新
    assert "战甲" in txt2                  # 新自动候选重生成


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
