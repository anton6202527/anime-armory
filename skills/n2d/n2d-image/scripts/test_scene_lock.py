#!/usr/bin/env python3
"""cd skills/n2d/n2d-image/scripts && python3 -m pytest test_scene_lock.py

场景生成侧锁执行层——job pack / 主体库 payload / 状态回写 + 与 planner 的环闭合。"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_lock as sl
import scene_reference_planner as srp

LOC = {"id": "LOC_HALL", "core": True,
       "reference_group": {"primary": "定妆_大殿.png", "spatial_map": "布局.png"},
       "scene_atlas": {"base_views": {"reverse": "反.png"}}}


def test_scene_trigger_deterministic():
    assert sl.scene_trigger("LOC_HALL") == "loc_hall_scene_v1"


def test_build_scene_lora_job_dataset_from_refs():
    job = sl.build_scene_lora_job(LOC)
    assert job["status"] == "candidate" and job["dataset_count"] == 3  # primary+spatial_map+reverse
    slots = {d["slot"] for d in job["dataset"]}
    assert "primary" in slots and "spatial_map" in slots and "base_view:reverse" in slots


def test_build_scene_lora_job_incomplete():
    assert sl.build_scene_lora_job({"id": "LOC_X"})["status"] == "dataset_incomplete"


def test_build_subject_registration():
    s = sl.build_subject_registration(LOC, "kling")
    assert s["backend"] == "kling" and s["subject_name"] == "scene_loc_hall" and s["reference_count"] == 3


def test_apply_lock_status_and_validation():
    out = sl.apply_lock_status(LOC, "scene_lora", "ready")
    assert out["scene_lora"]["status"] == "ready"
    import pytest
    with pytest.raises(ValueError):
        sl.apply_lock_status(LOC, "bogus", "ready")


def test_registry_loop_closes_planner_tier():
    # 注册 scene_lora ready 后，planner 升档到 scene_lora 且停止重复建议
    before = srp.plan_loc(LOC, intra_shots=4, cross_eps=3, backend_supports_subject=False)
    after = srp.plan_loc(sl.apply_lock_status(LOC, "scene_lora", "ready"),
                         intra_shots=4, cross_eps=3, backend_supports_subject=False)
    assert before["scene_lock_tier"] == "reference_plate" and before["suggest_scene_lora"] is True
    assert after["scene_lock_tier"] == "scene_lora" and after["suggest_scene_lora"] is False


def test_registered_scene_lora_status_closes_planner_tier():
    after = srp.plan_loc(sl.apply_lock_status(LOC, "scene_lora", "registered"),
                         intra_shots=4, cross_eps=3, backend_supports_subject=False)
    assert after["scene_lock_tier"] == "scene_lora"


def test_register_writes_back_to_registry(tmp_path):
    root = tmp_path / "剧"
    d = root / "出图" / "共享"
    d.mkdir(parents=True)
    (d / "asset_registry.json").write_text(json.dumps({"assets": [dict(LOC)]}, ensure_ascii=False), encoding="utf-8")
    rc = sl.cmd_register(str(root), "LOC_HALL", "scene_lora", "registered")
    assert rc == 0
    data = json.loads((d / "asset_registry.json").read_text(encoding="utf-8"))
    assert data["assets"][0]["scene_lora"]["status"] == "registered"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
