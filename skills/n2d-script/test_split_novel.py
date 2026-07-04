#!/usr/bin/env python3
"""Tests for split_novel project scaffolding."""
import json
import os
import subprocess
import sys


def test_split_novel_builds_local_source_analysis(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text(
        "第一章\n"
        "灵气复苏的现代都市里，林越说自己觉醒了系统面板。\n"
        "林越来到青云宗大殿，发现神秘玉佩暗藏真相。\n"
        "第二章\n"
        "苏眠问林越为何受伤，林越低声说这是觉醒代价。林越握紧玉佩，林越必须继续查。\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [sys.executable, script, str(novel), "--out", str(out), "--limit", "1"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )

    analysis_path = out / "设定库" / "source_analysis.json"
    assert analysis_path.exists()
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert analysis["kind"] == "n2d_source_analysis"
    assert analysis["source"] == "n2d_source_text"
    assert "系统" in analysis["power_system"]["system_terms"]
    assert any("神秘玉佩" in s["description"] for s in analysis["foreshadowing_candidates"])
    roster = (out / "设定库" / "characters" / "_角色总表.md").read_text(encoding="utf-8")
    assert "n2d 源书分析预填候选" in roster
    assert (out / "开发包" / "series_bible.md").exists()
    assert (out / "开发包" / "adaptation_strategy.json").exists()
    legacy_cross_line_file = "_novel" + "_handoff.json"
    assert not (out / "设定库" / legacy_cross_line_file).exists()


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
    assert "冷灰写实3D国风漫剧" in style
    assert "## 基础视觉风格契约（style_contract 源头）" in style
    assert "风格名" in style
    assert "冷灰写实 3D 国风漫剧质感" in style
    assert "真实3D人物质感 + 电影叙事镜头感" in style
    assert "风格禁忌" in style
    assert "style_anchor" in style
    assert "出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png" in style
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


def test_split_novel_scaffold_uses_new_visual_style_preset(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text("第一章\n她推门而入。\n第二章\n风声忽起。\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "_设置.md").write_text("- 基础视觉风格: 韩漫精致清透\n", encoding="utf-8")
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [sys.executable, script, str(novel), "--out", str(out), "--limit", "1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    style = (out / "设定库" / "global_style.md").read_text(encoding="utf-8")
    assert "韩漫精致清透" in style
    assert "风格名：韩漫精致清透" in style
    assert "韩漫条漫式精致清透" in style
    assert "风格禁忌" in style


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
    split_plan = json.loads((out / "脚本" / "split_plan.json").read_text(encoding="utf-8"))
    assert split_plan["kind"] == "n2d_machine_split_plan"
    assert split_plan["scope"] == "full"
    assert split_plan["target_episode_count"] == 2
    assert split_plan["episodes"][0]["raw_rel"] == "脚本/第1集/raw.txt"
    assert (out / "脚本" / "_拆集复核.md").exists()


def test_split_novel_default_limits_first_scaffold_to_ten_episodes(tmp_path):
    parts = []
    for i in range(1, 13):
        parts.extend([
            f"第{i}章",
            f"长老逼第{i}房交出玉牌。",
            f"少年反手亮出真相，众人当场跪倒！",
        ])
    novel = tmp_path / "novel.txt"
    novel.write_text("\n".join(parts) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [sys.executable, script, str(novel), "--out", str(out), "--by-chapter"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert (out / "脚本" / "第10集" / "raw.txt").exists()
    assert not (out / "脚本" / "第11集" / "raw.txt").exists()
    split_plan = json.loads((out / "脚本" / "split_plan.json").read_text(encoding="utf-8"))
    assert split_plan["scope"] == "partial"
    assert split_plan["target_episode_count"] == 10
    assert split_plan["estimated_total_episode_count"] == 12
    progress = (out / "_进度.md").read_text(encoding="utf-8")
    assert "已粗切 **10** 集" in progress


def test_split_novel_all_opt_in_writes_full_scaffold(tmp_path):
    parts = []
    for i in range(1, 13):
        parts.extend([
            f"第{i}章",
            f"长老逼第{i}房交出玉牌。",
            f"少年反手亮出真相，众人当场跪倒！",
        ])
    novel = tmp_path / "novel.txt"
    novel.write_text("\n".join(parts) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [sys.executable, script, str(novel), "--out", str(out), "--by-chapter", "--all"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert (out / "脚本" / "第12集" / "raw.txt").exists()
    split_plan = json.loads((out / "脚本" / "split_plan.json").read_text(encoding="utf-8"))
    assert split_plan["scope"] == "full"
    assert split_plan["target_episode_count"] == 12


def test_split_novel_full_rerun_updates_existing_progress_without_overwriting_done(tmp_path):
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
    out.mkdir()
    (out / "_进度.md").write_text(
        "\n".join(
            [
                "# old",
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 999 | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | — | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
                "",
                "## 旧状态",
                "- 保留这段人工生产记录。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    subprocess.run(
        [sys.executable, script, str(novel), "--out", str(out), "--by-chapter"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    progress = (out / "_进度.md").read_text(encoding="utf-8")
    assert "全篇粗切索引已落地 **2** 集" in progress
    assert "| 第1集 | 999 | ✅ | ✅ | ✅ | ✅ |" in progress
    assert "| 第2集 |" in progress
    assert "## 旧状态" in progress
    assert "保留这段人工生产记录" in progress


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


def test_split_novel_start_chapter_filters_window_and_keeps_source_snapshot(tmp_path):
    novel = tmp_path / "novel.txt"
    novel.write_text(
        "第一章\n"
        "柳娘子逼她交出凤印。\n"
        "沈念反手夺回凤印，众人当场跪倒！\n"
        "第二章\n"
        "太监拔刀逼近小禾。\n"
        "沈念冷笑抬头，殿门突然被撞开！\n"
        "第三章\n"
        "黑衣人逼她交出玉佩。\n"
        "沈念反手亮出真相，众人当场跪倒！\n"
        "第四章\n"
        "长老拔刀逼近沈念。\n"
        "她冷笑抬头，殿门突然被撞开！\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    script = os.path.join(os.path.dirname(__file__), "scripts", "split_novel.py")

    result = subprocess.run(
        [
            sys.executable,
            script,
            str(novel),
            "--out",
            str(out),
            "--by-chapter",
            "--start-chapter",
            "第三章",
            "--limit",
            "2",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    raw1 = (out / "脚本" / "第1集" / "raw.txt").read_text(encoding="utf-8")
    raw2 = (out / "脚本" / "第2集" / "raw.txt").read_text(encoding="utf-8")
    source = (out / "小说" / "novel.txt").read_text(encoding="utf-8")
    progress = (out / "_进度.md").read_text(encoding="utf-8")
    assert "第三章" in raw1 and "第一章" not in raw1 and "第二章" not in raw1
    assert "第四章" in raw2
    assert "第一章" in source
    assert "起始章节：请求第3章，实际从第3章开始" in result.stdout
    assert "全篇粗切索引已落地 **2** 集（从第3章起）" in progress
