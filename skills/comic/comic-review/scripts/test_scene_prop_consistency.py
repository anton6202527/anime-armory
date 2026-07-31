#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import scene_prop_consistency


def test_outfit_child_reference_is_resolved(tmp_path: Path) -> None:
    root = tmp_path / "project"
    anchor = root / "出图" / "共享" / "图片" / "CHAR_A__OUTFIT_TRAVEL.png"
    anchor.parent.mkdir(parents=True)
    anchor.write_bytes(b"reviewed-outfit-anchor")
    registry = {
        "assets": {
            "CHAR_A": {
                "type": "character",
                "outfits": {
                    "OUTFIT_TRAVEL": {
                        "reference_images": [
                            {"path": "出图/共享/图片/CHAR_A__OUTFIT_TRAVEL.png"}
                        ]
                    }
                },
            }
        }
    }

    assert scene_prop_consistency.asset_anchor_paths(root, registry, "OUTFIT_TRAVEL") == [
        "出图/共享/图片/CHAR_A__OUTFIT_TRAVEL.png"
    ]
