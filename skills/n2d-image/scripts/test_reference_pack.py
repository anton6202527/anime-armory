#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reference_pack as rp  # noqa: E402


def _write_project(root: Path) -> None:
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [
            {
                "id": "CHAR_01",
                "name": "沈念",
                "scope": "全篇主角",
                "forms": [{
                    "form": "常态",
                    "reference_group": {"front": "出图/共享/图片/定妆_CHAR_01.png"},
                }],
            },
            {
                "id": "CHAR_02",
                "name": "陆衡",
                "scope": "长线男主",
                "forms": [{
                    "form": "常态",
                    "reference_group": {"front": "出图/共享/图片/定妆_CHAR_02.png"},
                    "performance_signature": {"gaze": "垂眼"},
                }],
            },
        ]
    }, ensure_ascii=False), encoding="utf-8")
    (shared / "asset_registry.json").write_text(json.dumps({
        "assets": [{"id": "LOC_HALL", "type": "location", "reference_group": {"primary": "hall.png"}}]
    }, ensure_ascii=False), encoding="utf-8")
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "description": "CHAR_01 与 CHAR_02 在 LOC_HALL 多人同框打斗。",
            "character_ids": ["CHAR_01", "CHAR_02"],
        }]
    }, ensure_ascii=False), encoding="utf-8")


def test_reference_pack_plans_character_and_region_assets(tmp_path: Path) -> None:
    _write_project(tmp_path)

    pack = rp.build_pack(tmp_path, "第1集")

    assert pack["kind"] == rp.KIND
    slots = {(t["scope"], t["owner"], t["slot"]) for t in pack["targets"]}
    assert ("character", "CHAR_01/常态", "expression_bank") in slots
    assert ("character", "CHAR_01/常态", "performance_signature") in slots
    assert ("multi_subject", "Clip_01", "regional_construct_plate") in slots
    assert ("multi_subject", "Clip_01", "region_masks") in slots


def test_reference_pack_writes_outputs(tmp_path: Path) -> None:
    _write_project(tmp_path)
    pack = rp.build_pack(tmp_path, "第1集")
    jp, mp = rp.write_outputs(tmp_path, "第1集", pack)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == rp.KIND
