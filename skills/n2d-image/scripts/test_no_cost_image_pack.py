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
    assert pack["summary"]["reference_generation_tasks"] == 2
    assert pack["summary"]["keyshot_candidate_tasks"] == 1
    assert pack["summary"]["regional_construct_manifests"] == 1
    assert pack["shot_packages"][0]["keyshot_candidate_task"]["selection_status"] == "selected"
    assert pack["regional_construct_manifests"][0]["mode"] == "regional_construct_required"


def test_no_cost_image_pack_writes_outputs(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    pack = ncip.build_pack(tmp_path, "第1集")
    jp, mp = ncip.write_outputs(tmp_path, "第1集", pack)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == ncip.KIND
