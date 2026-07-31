#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_finishing_plan


def load_stage_module(name: str, relative: str):
    path = Path(__file__).resolve().parents[2] / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


name_stage = load_stage_module("comic_name_for_finishing_test", "comic-name/scripts/build_name_board.py")
layout_stage = load_stage_module("comic_layout_for_finishing_test", "comic-layout/scripts/build_layout.py")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_approved_inputs(root: Path, chapter: str, panels: list[dict]) -> None:
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})
    name_path = root / "排版" / chapter / "name_board.json"
    write_json(name_path, name_stage.build_name_board(root, chapter))
    name_stage.transition_existing(root, chapter, "review")
    name_stage.transition_existing(root, chapter, "approved", reviewed_by="editor")
    layout_path = root / "排版" / chapter / "layout.json"
    write_json(layout_path, layout_stage.build_layout(root, chapter, 0, 28))
    layout_stage.transition_existing(root, chapter, "review")
    layout_stage.transition_existing(root, chapter, "approved", reviewed_by="layout-editor")


def test_finishing_plan_adds_tone_effects_and_no_bake_contract(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 基础视觉风格：黑白日漫页漫\n- 出图稿层：网点完成稿\n- 网点策略：显式tone_plan\n- 效果线策略：剧情驱动\n",
        encoding="utf-8",
    )
    panels = [
        {"panel_id": "P001", "story_function": "action_peak", "description": "一拳命中。", "sfx": ["砰"]},
        {"panel_id": "P002", "story_function": "reaction", "description": "旁观者倒吸气。"},
    ]
    build_approved_inputs(
        root,
        chapter,
        panels,
    )

    plan = build_finishing_plan.build_finishing_plan(root, chapter)
    first = plan["panels"][0]

    assert plan["render_stage"] == "网点完成稿"
    assert plan["schema_version"] == 2
    assert plan["workflow_status"] == "validated"
    assert plan["delivery_mode"] == "monochrome_print"
    assert plan["layer_contract"]["ordered_layers"]
    assert plan["page_value_plans"]
    assert plan["validation"]["status"] == "pass"
    assert "tone" in first["art_stage_sequence"]
    assert first["layer_items"]
    assert first["tone_items"]
    assert "screentone" in first["tone_plan"]
    assert "speed/action lines" in first["effects_plan"]
    assert first["lettering_sfx_plan"]["mode"] == "drawn_sfx"
    assert first["sfx_items"][0]["content_ref"] == "panel:P001.sfx:1"
    assert "dialogue and narration stay out" in first["no_bake_text_contract"]


def test_finishing_blocks_missing_or_empty_inputs(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    root.mkdir()
    with pytest.raises(build_finishing_plan.FinishingError):
        build_finishing_plan.build_finishing_plan(root, "第1话")


def test_finishing_stale_receipt_detects_upstream_change(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    settings = root / "_设置.md"
    settings.write_text(
        "- 漫画形态：条漫\n- 阅读方向：从上到下\n- 基础视觉风格：彩色国漫条漫\n- 出图稿层：彩色完成稿\n",
        encoding="utf-8",
    )
    panels = [{"panel_id": "P001", "story_function": "opening_hook", "dialogue": [{"speaker": "甲", "text": "走。"}]}]
    build_approved_inputs(root, chapter, panels)
    plan = build_finishing_plan.build_finishing_plan(root, chapter)
    assert build_finishing_plan.stale_errors(root, chapter, plan) == []

    settings.write_text(settings.read_text(encoding="utf-8") + "- 网点策略：关闭\n", encoding="utf-8")
    assert any("settings_sha256" in item for item in build_finishing_plan.stale_errors(root, chapter, plan))
    with pytest.raises(build_finishing_plan.FinishingError):
        build_finishing_plan.build_finishing_plan(root, chapter)


def test_finishing_blocks_panel_coverage_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    panels = [{"panel_id": "P001"}, {"panel_id": "P002"}]
    build_approved_inputs(root, chapter, panels)
    layout_path = root / "排版" / chapter / "layout.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    layout["segments"][0]["panels"].pop()
    layout_path.write_text(json.dumps(layout, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(build_finishing_plan.FinishingError):
        build_finishing_plan.build_finishing_plan(root, chapter)


@pytest.mark.parametrize(
    ("artifact", "field"),
    (("name_board.json", "reviewed_by"), ("layout.json", "reviewed_at")),
)
def test_finishing_requires_accountable_upstream_approvals(
    tmp_path: Path,
    artifact: str,
    field: str,
) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    build_approved_inputs(root, chapter, [{"panel_id": "P001"}])
    path = root / "排版" / chapter / artifact
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["approval"].pop(field)
    write_json(path, payload)

    with pytest.raises(build_finishing_plan.FinishingError, match=field):
        build_finishing_plan.build_finishing_plan(root, chapter)
