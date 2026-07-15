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


def test_reference_pack_does_not_extend_structured_ids_into_chinese_prose(tmp_path: Path) -> None:
    _write_project(tmp_path)
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.write_text(json.dumps({"clips": [{
        "id": "Clip_01",
        "description": "CHAR_01与CHAR_02连线，VFX_01退出清晰画面。",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "object_ids": ["VFX_01"],
        "location_id": "LOC_HALL",
    }]}, ensure_ascii=False), encoding="utf-8")

    pack = rp.build_pack(tmp_path, "第1集")

    assert pack["used_characters"] == ["CHAR_01", "CHAR_02"]
    assert pack["used_assets"] == ["LOC_HALL", "VFX_01"]


def test_reference_pack_does_not_report_planned_registry_paths_as_ready(tmp_path: Path) -> None:
    _write_project(tmp_path)
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["characters"][0]["forms"][0]["reference_group"] = {
        "front": {"path": "出图/共享/图片/定妆_CHAR_01.png", "status": "planned"},
        "half_body": {"path": "出图/共享/图片/定妆_CHAR_01_半身.png", "status": "planned"},
        "face_anchor_refs": [
            {"path": "出图/共享/图片/定妆_CHAR_01_脸部特写.png", "status": "planned"}
        ],
    }
    registry.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pack = rp.build_pack(tmp_path, "第1集")
    char_targets = [t for t in pack["targets"] if t["owner"] == "CHAR_01/常态"]

    assert char_targets
    assert all(t["status"] == "planned" for t in char_targets)
    by_slot = {t["slot"]: t for t in char_targets}
    assert by_slot["front"]["path"] == "出图/共享/图片/定妆_CHAR_01.png"
    assert by_slot["half_body_or_full_body"]["path"] == "出图/共享/图片/定妆_CHAR_01_半身.png"
    assert by_slot["face_anchor_refs"]["path"] == "出图/共享/图片/定妆_CHAR_01_脸部特写.png"


def test_reference_pack_includes_registered_core_turnaround_path(tmp_path: Path) -> None:
    _write_project(tmp_path)
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    form = data["characters"][0]["forms"][0]
    form["library_tier"] = "core_full"
    form["reference_group"]["turnaround"] = {
        "path": "出图/共享/图片/定妆_CHAR_01__常态_三视图.png",
        "status": "planned",
        "layout": "five_angle_v1",
    }
    registry.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pack = rp.build_pack(tmp_path, "第1集")
    turnaround = next(
        t for t in pack["targets"]
        if t["owner"] == "CHAR_01/常态" and t["slot"] == "turnaround"
    )

    assert turnaround["status"] == "planned"
    assert turnaround["path"] == "出图/共享/图片/定妆_CHAR_01__常态_三视图.png"


def test_reference_pack_counts_ready_six_expression_sheet_as_six_slots(tmp_path: Path) -> None:
    _write_project(tmp_path)
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    expression_path = "出图/共享/图片/定妆_CHAR_01__常态_表情_六联表.png"
    data["characters"][0]["forms"][0]["reference_group"]["expressions"] = [{
        "path": expression_path,
        "status": "ready",
        "emotion": "六联表（冷静/警觉/震惊/隐忍/将哭/决绝）",
        "layout": "two_by_three_expression_sheet_v1",
    }]
    registry.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pack = rp.build_pack(tmp_path, "第1集")
    expression = next(
        t for t in pack["targets"]
        if t["owner"] == "CHAR_01/常态" and t["slot"] == "expression_bank"
    )

    assert expression["status"] == "ready"
    assert expression["path"] == expression_path


def test_reference_pack_does_not_reuse_one_scene_primary_for_all_plates(tmp_path: Path) -> None:
    _write_project(tmp_path)
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(storyboard.read_text(encoding="utf-8"))
    data["clips"][0]["location_id"] = "LOC_HALL"
    storyboard.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    pack = rp.build_pack(tmp_path, "第1集")
    scene = {
        t["slot"]: t for t in pack["targets"]
        if t["owner"] == "LOC_HALL"
    }

    assert scene["wide_plate"]["path"] == "hall.png"
    assert scene["wide_plate"]["status"] == "ready"
    assert scene["reverse_angle"]["status"] == "planned"
    assert scene["empty_plate"]["status"] == "planned"
    assert scene["lighting_plate"]["status"] == "planned"
    assert len({scene[key]["path"] for key in scene}) == 4
