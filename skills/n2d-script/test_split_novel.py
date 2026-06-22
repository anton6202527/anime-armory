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
    assert "国漫写实角色审美 + 电影级布光与镜头语言" in style
    assert "## 基础视觉风格契约（style_contract 源头）" in style
    assert "风格名" in style
    assert "电影级动机光" in style
    assert "风格禁忌" in style
    assert (out / "小说" / "novel.txt").exists()
    assert not (out / "脚本" / "第1集" / "字幕_英文.srt").exists()
    progress = (out / "_进度.md").read_text(encoding="utf-8")
    row = next(line for line in progress.splitlines() if line.startswith("| 第1集"))
    cells = [c.strip() for c in row.split("|")[1:-1]]
    header = [c.strip() for c in next(line for line in progress.splitlines() if line.startswith("| 集")).split("|")[1:-1]]
    assert cells[header.index("字幕英")] == "—"


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


def test_split_novel_keeps_english_subtitle_column_open_when_requested(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text("第一章\n她推门而入。\n第二章\n风声忽起。\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "_设置.md").write_text("- 字幕语言: 中英双语\n", encoding="utf-8")
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [sys.executable, script, str(novel), "--out", str(out), "--limit", "1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    progress = (out / "_进度.md").read_text(encoding="utf-8")
    row = next(line for line in progress.splitlines() if line.startswith("| 第1集"))
    cells = [c.strip() for c in row.split("|")[1:-1]]
    header = [c.strip() for c in next(line for line in progress.splitlines() if line.startswith("| 集")).split("|")[1:-1]]
    assert cells[header.index("字幕英")] == "⬜"


def test_split_novel_does_not_hard_cut_before_strong_hook(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text(
        "第一章\n"
        + "\n".join(["她在冷宫里忍着。"] * 30)
        + "\n门外突然传来脚步声！\n"
        + "第二章\n她抬头。\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [
            sys.executable,
            script,
            str(novel),
            "--out",
            str(out),
            "--by-chapter",
            "--target",
            "20",
            "--max",
            "25",
            "--limit",
            "1",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    raw = (out / "脚本" / "第1集" / "raw.txt").read_text(encoding="utf-8")
    assert raw.count("她在冷宫里忍着。") == 30
    assert "门外突然传来脚步声！" in raw


def test_split_novel_default_splits_short_complete_hook_units_without_target(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text(
        "第一章\n"
        "柳娘子逼她交出凤印。\n"
        "沈念反手夺回凤印，众人当场跪倒！\n"
        "第二章\n"
        "太监拔刀逼近小禾。\n"
        "沈念冷笑抬头，殿门突然被撞开！\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [
            sys.executable,
            script,
            str(novel),
            "--out",
            str(out),
            "--by-chapter",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    raw1 = (out / "脚本" / "第1集" / "raw.txt").read_text(encoding="utf-8")
    raw2 = (out / "脚本" / "第2集" / "raw.txt").read_text(encoding="utf-8")
    assert "第一章" in raw1 and "第二章" not in raw1
    assert "第二章" in raw2


def test_split_novel_default_uses_scene_break_as_closed_loop_candidate(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text(
        "【冷宫夜】\n"
        "柳娘子逼她交出凤印。\n"
        "沈念反手夺回凤印，众人当场跪倒。\n"
        "【内殿】\n"
        "太监拔刀逼近小禾。\n"
        "沈念冷笑抬头，殿门突然被撞开！\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [
            sys.executable,
            script,
            str(novel),
            "--out",
            str(out),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    raw1 = (out / "脚本" / "第1集" / "raw.txt").read_text(encoding="utf-8")
    raw2 = (out / "脚本" / "第2集" / "raw.txt").read_text(encoding="utf-8")
    assert "柳娘子逼她交出凤印" in raw1 and "【内殿】" not in raw1
    assert "【内殿】" in raw2
