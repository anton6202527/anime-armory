#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("library.py")
    spec = importlib.util.spec_from_file_location("comic_identity_library_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


library = load_module()


def test_builds_comic_local_character_and_asset_manifests(tmp_path: Path) -> None:
    root = tmp_path / "漫画"
    registry = root / "出图" / "共享" / "identity_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "kind": "comic_identity_registry",
                "assets": {
                    "CHAR_A": {
                        "id": "CHAR_A",
                        "type": "character",
                        "display_name": "阿甲",
                        "core": True,
                        "status": "planned",
                        "views": {
                            "front": "出图/共享/图片/CHAR_A__front.png",
                            "side": "出图/共享/图片/CHAR_A__side.png",
                        },
                        "reference_images": [
                            {
                                "view": "front",
                                "path": "出图/共享/图片/CHAR_A__front.png",
                                "source": {
                                    "style_reference_path": "出图/共享/图片/STYLE_A__anchor.png",
                                    "style_reference_role": "style_only",
                                },
                            }
                        ],
                    },
                    "LOC_GARDEN": {
                        "id": "LOC_GARDEN",
                        "type": "scene",
                        "display_name": "庭院",
                        "anchor_path": "出图/共享/图片/LOC_GARDEN__anchor.png",
                    },
                    "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "display_name": "淡彩",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "设定库").mkdir(parents=True)
    shared = root / "出图" / "共享" / "图片"
    shared.mkdir(parents=True)
    (shared / "CHAR_A__front.png").write_bytes(b"front")
    (shared / "STYLE_A__anchor.png").write_bytes(b"style")

    summary = library.build_library(root, write=True)
    assert summary["character_count"] == 1
    assert summary["asset_count"] == 2
    assert summary["cross_line_dependency"] is False

    character_manifest = root / summary["characters"][0]["manifest"]
    character = json.loads(character_manifest.read_text(encoding="utf-8"))
    assert character["kind"] == "comic_project_character_asset_bundle"
    assert character["library_tier"] == "core_full"
    assert character["reference_count"] == 1
    assert character["planned_reference_count"] == 1
    assert character["planned_reference_files"] == ["出图/共享/图片/CHAR_A__side.png"]
    assert character["generation_dependency_files"] == ["出图/共享/图片/STYLE_A__anchor.png"]
    assert character["reference_readiness"] == {
        "declared_count": 2,
        "ready_count": 1,
        "planned_count": 1,
        "all_declared_ready": False,
    }
    assert character["derivation"]["cross_line_dependency"] is False

    assert (root / "角色库" / "00_索引.json").is_file()
    assert (root / "资产库" / "00_索引.json").is_file()
    assert any("资产库/场景" in item["manifest"] for item in summary["assets"])
