#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import no_cost_image_pack as ncip  # noqa: E402


def _write_inputs(root: Path) -> None:
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "description": "CHAR_01 和 CHAR_02 在 LOC_HALL 多人同框。",
            "character_ids": ["CHAR_01", "CHAR_02"],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    prod = root / "生产数据"
    prod.mkdir()
    (prod / "no_cost_reference_pack_第1集.json").write_text(json.dumps({
        "targets": [
            {"scope": "character", "owner": "CHAR_01/常态", "slot": "turnaround", "status": "planned", "path": "出图/共享/图片/turnaround.png", "reason": "核心五角总览"},
            {"scope": "character", "owner": "CHAR_01/常态", "slot": "expression_bank", "status": "planned", "path": "出图/共享/图片/expr.png", "reason": "核心表情库"},
            {"scope": "multi_subject", "owner": "Clip_01", "slot": "region_masks", "status": "planned", "path": "出图/第1集/区域构建/Clip_01/masks.json", "reason": "多人分区"},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "keyshot_candidate_plan_第1集.json").write_text(json.dumps({
        "keyshots": [{
            "clip": "Clip_01",
            "tags": ["opening", "multi_subject"],
            "candidate_count": 6,
            "candidate_dir": "出图/第1集/候选/Clip_01/",
            "expected_candidates": ["出图/第1集/候选/Clip_01/candidate_01.png"],
            "selection_manifest": "出图/第1集/候选/Clip_01/selection.json",
            "selection_criteria": ["角色 DNA 一致"],
            "existing_scores": [{"candidate": "candidate_01", "score": 4.2}],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "reference_plan_第1集.json").write_text(json.dumps({
        "clips": [{
            "clip_id": "Clip_01",
            "multi_subject_strategy": {
                "mode": "regional_construct_required",
                "slots": [{"slot": "LEFT_SLOT", "char_id": "CHAR_01"}, {"slot": "RIGHT_SLOT", "char_id": "CHAR_02"}],
            },
        }]
    }, ensure_ascii=False), encoding="utf-8")


def test_no_cost_image_pack_builds_all_p0_sections(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    pack = ncip.build_pack(tmp_path, "第1集")

    assert pack["kind"] == ncip.KIND
    assert pack["summary"]["reference_generation_tasks"] == 3
    turnaround = next(task for task in pack["reference_generation_queue"] if task["slot"] == "turnaround")
    assert turnaround["priority"] == "P0"
    assert pack["summary"]["keyshot_candidate_tasks"] == 1
    assert pack["summary"]["regional_construct_manifests"] == 1
    assert pack["shot_packages"][0]["keyshot_candidate_task"]["selection_status"] == "selected"
    assert pack["regional_construct_manifests"][0]["mode"] == "regional_construct_required"


def test_reference_queue_deduplicates_same_physical_output_and_keeps_requirements(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    ref = tmp_path / "生产数据" / "no_cost_reference_pack_第1集.json"
    data = json.loads(ref.read_text(encoding="utf-8"))
    data["targets"].extend([
        {"scope": "character", "owner": "CHAR_02/常态", "slot": "front", "status": "planned", "path": "出图/共享/图片/char02.png", "reason": "正面锚"},
        {"scope": "character", "owner": "CHAR_02/常态", "slot": "expression_bank", "status": "planned", "path": "出图/共享/图片/char02.png", "reason": "基础表情可复用正面锚"},
    ])
    ref.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pack = ncip.build_pack(tmp_path, "第1集")
    rows = [task for task in pack["reference_generation_queue"] if task["output_path"].endswith("char02.png")]

    assert len(rows) == 1
    assert {item["slot"] for item in rows[0]["satisfies"]} == {"front", "expression_bank"}
    assert rows[0]["priority"] == "P0"


def test_no_cost_image_pack_writes_outputs(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    pack = ncip.build_pack(tmp_path, "第1集")
    jp, mp = ncip.write_outputs(tmp_path, "第1集", pack)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == ncip.KIND


def test_shot_packages_use_structured_ids_not_prose_suffixes(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.write_text(json.dumps({"clips": [{
        "id": "Clip_01",
        "description": "CHAR_01与CHAR_02连线，VFX_01退出清晰画面。",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "object_ids": ["VFX_01"],
        "location_id": "LOC_HALL",
    }]}, ensure_ascii=False), encoding="utf-8")

    pack = ncip.build_pack(tmp_path, "第1集")
    shot = pack["shot_packages"][0]

    assert shot["characters"] == ["CHAR_01", "CHAR_02"]
    assert shot["assets"] == ["VFX_01", "LOC_HALL"]


def test_shot_packages_exclude_offscreen_characters_from_regional_construct(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.write_text(json.dumps({"clips": [{
        "id": "Clip_01",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "entity_schedule": {
            "characters": ["CHAR_01"],
            "offscreen_presence": ["CHAR_02"],
            "forbidden_presence": [],
        },
    }]}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "生产数据" / "reference_plan_第1集.json").write_text(
        json.dumps({"clips": []}, ensure_ascii=False), encoding="utf-8")

    pack = ncip.build_pack(tmp_path, "第1集")

    assert pack["shot_packages"][0]["characters"] == ["CHAR_01"]
    assert pack["regional_construct_manifests"] == []


def test_form_specific_character_and_required_base_are_one_subject(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.write_text(json.dumps({"clips": [{
        "id": "Clip_01",
        "entity_schedule": {
            "characters": ["CHAR_01/反噬跪地态"],
            "required_presence": ["CHAR_01", "VFX_系统面板"],
        },
    }]}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "生产数据" / "reference_plan_第1集.json").write_text(
        json.dumps({"clips": []}, ensure_ascii=False), encoding="utf-8")

    pack = ncip.build_pack(tmp_path, "第1集")

    assert pack["shot_packages"][0]["characters"] == ["CHAR_01/反噬跪地态"]
    assert pack["regional_construct_manifests"] == []


def test_offscreen_base_suppresses_form_specific_character(tmp_path: Path) -> None:
    clip = {
        "entity_schedule": {
            "characters": ["CHAR_01/常态", "CHAR_02/死亡态"],
            "offscreen_presence": ["CHAR_02"],
            "required_presence": ["CHAR_01"],
        }
    }

    chars, _assets = ncip.structured_entities(clip)

    assert chars == ["CHAR_01/常态"]
