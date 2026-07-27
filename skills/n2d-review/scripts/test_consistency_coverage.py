#!/usr/bin/env python3
"""cd skills/n2d-review/scripts && python3 -m pytest test_consistency_coverage.py

一致性现实覆盖账本——纯逻辑（适用性 / 真跑过 / 覆盖率汇总）。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import consistency_coverage as cc


LOCS = [{"id": "LOC_A", "scene_dna": {"resident_assets": ["残匾"]},
         "constraints": {"doors_windows": "门在画左"}}]


def test_applies_by_declared_data():
    assert cc.applies("has_loc", LOCS) is True
    assert cc.applies("has_resident_assets", LOCS) is True
    assert cc.applies("has_doors_windows", LOCS) is True
    # 没登记数据 → 不适用（不强求无关项目装重型后端）
    assert cc.applies("has_resident_assets", [{"id": "LOC_B"}]) is False
    assert cc.applies("has_doors_windows", [{"id": "LOC_B", "constraints": {}}]) is False
    assert cc.applies("has_loc", [{"id": "CHAR_A"}]) is False


def test_ran_fresh_detector_ran():
    assert cc.ran_fresh("detector_ran", {"detector_ran": True}) is True
    assert cc.ran_fresh("detector_ran", {"detector_ran": False}) is False
    assert cc.ran_fresh("detector_ran", None) is False
    assert cc.ran_fresh("detector_ran", {}) is False


def test_ran_fresh_embed_filled():
    assert cc.ran_fresh("embed_filled", {"probes": [{"embedding": [0.1, 0.2]}]}) is True
    assert cc.ran_fresh("embed_filled", {"probes": [{"embedding": None}]}) is False
    assert cc.ran_fresh("embed_filled", {"probes": []}) is False


def test_coverage_summary():
    rows = [{"applicable": True, "ran_fresh": True}, {"applicable": True, "ran_fresh": False},
            {"applicable": False, "ran_fresh": False}]
    assert cc.coverage_summary(rows) == {"applicable": 2, "ran_fresh": 1, "dormant": 1, "total": 3}


def test_scene_coverage_rows_dormant(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "出图", "共享"))
    import json
    json.dump({"assets": LOCS}, open(os.path.join(root, "出图", "共享", "asset_registry.json"), "w"))
    # no sidecars → all applicable verifiers dormant
    rows = cc.scene_coverage_rows(root, "第1集")
    by = {r["key"]: r for r in rows}
    assert by["resident_presence"]["applicable"] and by["resident_presence"]["dormant"]
    assert by["scene_geometry"]["applicable"] and by["scene_geometry"]["dormant"]
    assert by["scene_embedding"]["applicable"] and by["scene_embedding"]["dormant"]


# ── 2026-07-26 扩容：O3V / VAP / COST 纳入覆盖账本 ────────────────────────────

def test_applies_persistent_objects_and_char():
    assert cc.applies("has_persistent_objects", [{"id": "WEAPON_横刀"}]) is True
    assert cc.applies("has_persistent_objects", [{"id": "PROP_酒壶"}]) is True
    assert cc.applies("has_persistent_objects", [{"id": "LOC_A"}, {"id": "VFX_烟"}]) is False
    assert cc.applies("has_char", [{"id": "CHAR_01"}]) is True
    assert cc.applies("has_char", [{"id": "LOC_A"}]) is False


def test_ran_fresh_adjudicated_and_available():
    # manifest 天生带 findings:[] 占位——键存在≠裁决过；要 detector/judge/adjudicated 戳或非空 findings
    assert cc.ran_fresh("adjudicated", {"probes": [1], "findings": []}) is False       # 占位≠裁决
    assert cc.ran_fresh("adjudicated", {"probes": [1], "findings": [], "detector": "owl"}) is True
    assert cc.ran_fresh("adjudicated", {"pairs": [1], "findings": [], "judge": "vlm"}) is True
    assert cc.ran_fresh("adjudicated", {"pairs": [1], "findings": [], "adjudicated": True}) is True
    assert cc.ran_fresh("adjudicated", {"pairs": [1], "findings": [{"shot": "x"}]}) is True  # 有发现=裁过
    assert cc.ran_fresh("adjudicated", {"pairs": [], "findings": []}) is True          # 无待判对象≠休眠
    assert cc.ran_fresh("available_true", {"available": True}) is True
    assert cc.ran_fresh("available_true", {"available": False}) is False


def test_object_appearance_costume_dormancy_detected(tmp_path):
    """实证回归（那妖魔ep1）：insightface 在场时 O3V/VAP/COST 无声休眠——现在必须被账本点名。"""
    import json
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "出图", "共享"))
    json.dump({"assets": [{"id": "WEAPON_横刀"}]},
              open(os.path.join(root, "出图", "共享", "asset_registry.json"), "w"))
    json.dump({"characters": [{"id": "CHAR_01", "name": "姜月初"}]},
              open(os.path.join(root, "出图", "共享", "identity_registry.json"), "w"))
    rows = cc.scene_coverage_rows(root, "第1集")
    by = {r["key"]: r for r in rows}
    assert by["object_presence"]["applicable"] and by["object_presence"]["dormant"]
    assert by["appearance_judge"]["applicable"] and by["appearance_judge"]["dormant"]
    assert by["costume_independent"]["applicable"] and by["costume_independent"]["dormant"]
    # 裁决/真跑后转 fresh
    os.makedirs(os.path.join(root, "生产数据"))
    json.dump({"pairs": [], "findings": []},
              open(os.path.join(root, "生产数据", "appearance_judge_第1集.json"), "w"))
    json.dump({"probes": [], "findings": [], "detector": "owl"},
              open(os.path.join(root, "生产数据", "object_presence_第1集.json"), "w"))
    json.dump({"available": True, "shots": []},
              open(os.path.join(root, "生产数据", "costume_consistency_第1集.json"), "w"))
    rows = cc.scene_coverage_rows(root, "第1集")
    by = {r["key"]: r for r in rows}
    assert not by["object_presence"]["dormant"]
    assert not by["appearance_judge"]["dormant"]
    assert not by["costume_independent"]["dormant"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
