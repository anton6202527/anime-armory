#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_finishing_plan


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_finishing_plan_adds_tone_effects_and_no_bake_contract(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 基础视觉风格：黑白日漫页漫\n- 出图稿层：网点完成稿\n- 网点策略：显式tone_plan\n- 效果线策略：剧情驱动\n",
        encoding="utf-8",
    )
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {
            "panels": [
                {"panel_id": "P001", "story_function": "action_peak", "description": "一拳命中。", "sfx": ["砰"]},
                {"panel_id": "P002", "story_function": "reaction", "description": "旁观者倒吸气。"},
            ]
        },
    )
    write_json(root / "排版" / chapter / "layout.json", {"segments": [{"panels": [{"panel_id": "P001", "w": 1200, "h": 900}, {"panel_id": "P002", "w": 900, "h": 420}]}]})

    plan = build_finishing_plan.build_finishing_plan(root, chapter)
    first = plan["panels"][0]

    assert plan["render_stage"] == "网点完成稿"
    assert "tone" in first["art_stage_sequence"]
    assert "screentone" in first["tone_plan"]
    assert "speed/action lines" in first["effects_plan"]
    assert first["lettering_sfx_plan"]["mode"] == "drawn_sfx"
    assert "dialogue and narration stay out" in first["no_bake_text_contract"]
