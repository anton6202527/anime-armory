#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_name_board


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_name_board_records_page_flow_and_finishing_preview(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 漫画形态：页漫\n- 阅读方向：从右到左\n- 页面尺寸：1440xauto\n- 原稿规格：B5商漫\n- 出图稿层：网点完成稿\n- 网点策略：显式tone_plan\n- 效果线策略：剧情驱动\n- 基础视觉风格：黑白日漫页漫\n",
        encoding="utf-8",
    )
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {
            "panels": [
                {
                    "panel_id": "P001",
                    "story_function": "opening_hook",
                    "description": "主角推门。",
                    "dialogue": [{"text": "来了。"}],
                    "layout_weight": "heavy",
                },
                {"panel_id": "P002", "story_function": "reaction", "description": "对手回头。"},
            ]
        },
    )

    board = build_name_board.build_name_board(root, chapter)

    assert board["kind"] == "comic_name_board"
    assert board["manuscript"]["bleed"] > 0
    assert board["pages"][0]["page_side"] == "right"
    assert board["pages"][0]["eye_flow_path"] == ["P001", "P002"]
    assert board["pages"][0]["panels"][0]["layout_weight"] == "heavy"
    assert board["pages"][0]["panels"][0]["bubble_first"] == "right_top"
    assert "screentone" in board["finishing_preview"]["tone_plan"]


def test_explicit_page_hints_override_fixed_page_capacity(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 漫画形态：页漫\n- 阅读方向：从左到右\n- 页面尺寸：1440xauto\n- 原稿规格：B5商漫\n",
        encoding="utf-8",
    )
    panels = [
        {"panel_id": f"P{index:03d}", "story_function": "beat", "page_hint": 1 if index <= 3 else 2}
        for index in range(1, 7)
    ]
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})

    board = build_name_board.build_name_board(root, chapter)

    assert len(board["pages"]) == 2
    assert board["pages"][0]["eye_flow_path"] == ["P001", "P002", "P003"]
    assert board["pages"][1]["eye_flow_path"] == ["P004", "P005", "P006"]
