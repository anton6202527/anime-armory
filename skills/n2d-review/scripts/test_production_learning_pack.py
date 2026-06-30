#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import production_learning_pack as plp  # noqa: E402


def _write_project(root: Path) -> None:
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [
            {
                "id": "Clip_01",
                "description": "CHAR_01 在 LOC_HALL 发现 PROP_RING，作为开场封面候选。",
                "character_ids": ["CHAR_01"],
            },
            {
                "id": "Clip_02",
                "description": "CHAR_01 与 CHAR_02 在 LOC_HALL 对峙。",
                "character_ids": ["CHAR_01", "CHAR_02"],
            },
        ]
    }, ensure_ascii=False), encoding="utf-8")

    prod = root / "生产数据"
    prod.mkdir()
    (prod / "keyshot_candidate_plan_第1集.json").write_text(json.dumps({
        "keyshots": [
            {"clip": "Clip_01", "tags": ["opening", "cover"]},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "review_ui_findings_第1集.json").write_text(json.dumps({
        "findings": [
            {"severity": "warn", "dimension": "角色一致性", "message": "近景脸型轻微漂移", "clip": "Clip_02"},
            {"severity": "high", "dimension": "角色一致性", "message": "反打镜发型不一致", "clip": "Clip_02"},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "gate_findings_image_第1集.json").write_text(json.dumps({
        "findings": [
            {"sev": "block", "dim": "资产一致性", "msg": "PROP_RING 未继承资产 id", "loc": "Clip_01"},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    image_qc = prod / "image_qc" / "第1集"
    image_qc.mkdir(parents=True)
    (image_qc / "image_qc_第1集.json").write_text(json.dumps({
        "recipe_hash": "abc",
        "prompt_sha256": "def",
    }, ensure_ascii=False), encoding="utf-8")

    bible = root / "设定库"
    bible.mkdir()
    (bible / "series_bible.json").write_text(json.dumps({
        "truth_sources": {
            "series_packaging": "设定库/packaging.json",
        }
    }, ensure_ascii=False), encoding="utf-8")


def test_production_learning_pack_builds_p2_sections(tmp_path: Path) -> None:
    _write_project(tmp_path)

    pack = plp.build_pack(tmp_path, "第1集")

    assert pack["kind"] == plp.KIND
    assert pack["summary"]["findings"] == 3
    assert pack["active_learning"]["patterns"][0]["dimension"] == "角色一致性"
    assert pack["active_learning"]["patterns"][0]["count"] == 2
    assert len(pack["packaging_ab_plan"]["variants"]) == 4
    assert pack["packaging_ab_plan"]["variants"][0]["source_clip"] == "Clip_01"
    assert pack["finished_video_vlm_qa"]["clip_questions"][0]["clip"] == "Clip_01"
    assert "PROP_RING" in pack["finished_video_vlm_qa"]["clip_questions"][0]["questions"][1]
    missing = pack["recipe_ledger"]["missing"][0]["missing_top_level_or_meta"]
    assert "backend_version" in missing
    assert "leitmotif_registry" in pack["series_bible_supplement"]["missing_truth_layers"]
    assert "series_packaging" not in pack["series_bible_supplement"]["missing_truth_layers"]


def test_production_learning_pack_writes_outputs(tmp_path: Path) -> None:
    _write_project(tmp_path)
    pack = plp.build_pack(tmp_path, "第1集")
    jp, mp = plp.write_outputs(tmp_path, "第1集", pack)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == plp.KIND
