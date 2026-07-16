#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


def load_module():
    path = Path(__file__).with_name("init_project.py")
    spec = importlib.util.spec_from_file_location("comic_init_project_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


init_project = load_module()


def test_project_skeleton_uses_registry_plus_compact_index_not_manifest_trees() -> None:
    assert "设定库" in init_project.SUBDIRS
    assert "出图/共享/图片" in init_project.SUBDIRS
    assert not any(path == "角色库" or path.startswith("资产库/") for path in init_project.SUBDIRS)


def test_resolve_named_paper_sizes() -> None:
    assert init_project.resolve_page_dimensions("B5", "页漫") == (2079, 2953)
    assert init_project.resolve_page_dimensions("A4", "页漫") == (2480, 3508)


def test_page_layout_placeholder_accepts_b5_and_marks_manual_work() -> None:
    layout = init_project.layout_json(
        SimpleNamespace(
            page_size="B5",
            format="页漫",
            reading_direction="从左到右",
            manuscript_spec="B5商漫",
        )
    )
    assert layout["canvas"] == {"width": 2079, "height": 2953}
    assert layout["manual_layout_required"] is True
    assert layout["format_supported_by_script"] is False
    assert layout["manuscript"]["bleed"] > 0


def test_numeric_auto_keeps_longstrip_compatibility() -> None:
    assert init_project.resolve_page_dimensions("1440xauto", "条漫") == (1440, 1800)


def test_name_stage_remains_when_traditional_finishing_is_disabled() -> None:
    progress = init_project.progress_markdown(
        "测试漫画",
        SimpleNamespace(
            mode="原创漫画",
            format="页漫",
            reading_direction="从右到左",
            traditional_workflow="关闭",
        ),
        source_ready=False,
    )
    assert "缩略分镜" in progress
    assert "原稿收尾" not in progress


def test_scaffold_writes_independent_bootstrap_catalog(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "comic"
    monkeypatch.setattr(sys, "argv", ["init_project.py", str(root), "--title", "测试漫画"])
    assert init_project.main() == 0
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    catalog = json.loads((root / "生产数据" / "artifact_catalog.json").read_text(encoding="utf-8"))
    assert meta["line"] == "comic" and meta["project_id"].startswith("comic_")
    assert catalog["status"] == "bootstrap"
    assert catalog["project"]["project_id"] == meta["project_id"]
    assert not (root / "排版" / "第1话" / "layout.json").exists()
    panel_script = json.loads((root / "脚本" / "第1话" / "panel_script.json").read_text(encoding="utf-8"))
    assert panel_script["schema_version"] == 2
    assert panel_script["chapter_contract"]["status"] == "draft"
    assert panel_script["panels"][0]["character_bindings"] == []
    progress = (root / "_进度.md").read_text(encoding="utf-8")
    assert "| 第1话 | ✅" not in progress
    registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    assert registry["schema_version"] == 2
    assert registry["kind"] == "comic_identity_registry"
    assert registry["assets"] == {}
    bible = (root / "设定库" / "story_bible.md").read_text(encoding="utf-8")
    assert "### 待定主角 CHAR_TBD_PROTAGONIST" in bible
    assert "### 待定对手 CHAR_TBD_ANTAGONIST" in bible
    # 作品卡片字段：立项时 synopsis 空、cover 为 null，不硬阻断。
    assert meta["synopsis"] == ""
    assert meta["cover"] is None
    assert "出图/封面/prompt" in init_project.SUBDIRS
    progress_text = (root / "_进度.md").read_text(encoding="utf-8")
    assert "## 作品封面" in progress_text


def test_extract_synopsis_from_story_bible_core_line() -> None:
    bible = (
        "# 故事圣经\n\n## 一句话核心\n- 少女被迫变身，踏上斩妖除魔之路\n\n"
        "## 角色\n- 不该被采集的正文\n"
    )
    assert init_project.extract_synopsis(bible) == "少女被迫变身，踏上斩妖除魔之路"


def test_extract_synopsis_empty_when_core_is_placeholder() -> None:
    bible = "# 故事圣经\n\n## 一句话核心\n- \n\n## 角色\n- x\n"
    assert init_project.extract_synopsis(bible) == ""
