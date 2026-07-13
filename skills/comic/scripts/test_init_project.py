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


def test_scaffold_writes_independent_bootstrap_catalog(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "comic"
    monkeypatch.setattr(sys, "argv", ["init_project.py", str(root), "--title", "测试漫画"])
    assert init_project.main() == 0
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    catalog = json.loads((root / "生产数据" / "artifact_catalog.json").read_text(encoding="utf-8"))
    assert meta["line"] == "comic" and meta["project_id"].startswith("comic_")
    assert catalog["status"] == "bootstrap"
    assert catalog["project"]["project_id"] == meta["project_id"]
