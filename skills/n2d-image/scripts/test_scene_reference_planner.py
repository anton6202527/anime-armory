#!/usr/bin/env python3
"""cd skills/n2d-image/scripts && python3 -m pytest test_scene_reference_planner.py

场景生成侧锚定规划器——纯逻辑（tier / master / lora / refs 含 spatial_map+base_views）。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_reference_planner as srp


def test_scene_lock_tier_ladder():
    assert srp.scene_lock_tier(backend_supports_subject=False) == "reference_plate"
    assert srp.scene_lock_tier(backend_supports_subject=True) == "backend_subject"
    assert srp.scene_lock_tier(backend_supports_subject=True, scene_lora_status="ready") == "scene_lora"
    assert srp.scene_lock_tier(backend_supports_subject=False, scene_lora_status="training") == "scene_lora"


def test_master_anchor_threshold():
    assert srp.plan_master_anchor("LOC_X", 3) == "LOC_X_MASTER"
    assert srp.plan_master_anchor("LOC_X", 5) == "LOC_X_MASTER"
    assert srp.plan_master_anchor("LOC_X", 2) is None


def test_scene_lora_suggestion_proactive():
    # 核心 × 跨≥3集 × 无后端主体锁 → 建议
    assert srp.should_suggest_scene_lora(is_core=True, cross_eps=3, backend_supports_subject=False) is True
    # 后端有主体库 → 不建议（后端自己锁）
    assert srp.should_suggest_scene_lora(is_core=True, cross_eps=9, backend_supports_subject=True) is False
    # 非核心 → 不建议
    assert srp.should_suggest_scene_lora(is_core=False, cross_eps=9, backend_supports_subject=False) is False
    # 已上 LoRA → 不再建议
    assert srp.should_suggest_scene_lora(is_core=True, cross_eps=9, backend_supports_subject=False,
                                         scene_lora_status="ready") is False
    # 跨集不足 → 不建议
    assert srp.should_suggest_scene_lora(is_core=True, cross_eps=2, backend_supports_subject=False) is False


def test_plan_scene_refs_includes_spatial_map_and_base_views():
    loc = {"id": "LOC_HALL",
           "reference_group": {"primary": "p.png", "spatial_map": "布局.png", "lighting_plate": "光.png"},
           "scene_atlas": {"base_views": {"reverse": "反.png", "side": "侧.png"}}}
    refs = srp.plan_scene_refs(loc, master_anchor="LOC_HALL_MASTER")
    slots = [r["slot"] for r in refs]
    assert "master_plate" in slots                        # #3
    assert "spatial_map" in slots                         # #1 布局图（死字段救活）
    assert "base_view:reverse" in slots and "base_view:side" in slots  # #1 多视角
    assert "primary" in slots and "lighting_plate" in slots


def test_plan_scene_refs_degrades_when_fields_absent():
    # 只有 primary：不报错，只出能出的槽（master 计划槽仍可加）
    refs = srp.plan_scene_refs({"id": "LOC_X", "reference_group": {"primary": "p.png"}})
    slots = [r["slot"] for r in refs]
    assert slots == ["primary"]
    assert "spatial_map" not in slots and "master_plate" not in slots


def test_plan_loc_full():
    loc = {"id": "LOC_HALL", "core": True,
           "reference_group": {"primary": "p.png", "spatial_map": "b.png"},
           "scene_atlas": {"base_views": {"reverse": "r.png"}}}
    plan = srp.plan_loc(loc, intra_shots=4, cross_eps=3, backend_supports_subject=False)
    assert plan["scene_lock_tier"] == "reference_plate"
    assert plan["master_anchor"] == "LOC_HALL_MASTER"
    assert plan["suggest_scene_lora"] is True
    assert plan["is_core"] is True


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
