#!/usr/bin/env python3
"""Tests for n2d spectacle/action helper scripts."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import action_edit_cues  # noqa: E402
import spectacle_contract_audit  # noqa: E402
import spectacle_plan  # noqa: E402
import spectacle_probe_pack  # noqa: E402
import spectacle_sequence_plan  # noqa: E402
import scene_layer_pack  # noqa: E402


def _mk_storyboard(clips):
    d = tempfile.mkdtemp()
    ep = Path(d) / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({"clips": clips}, ensure_ascii=False), encoding="utf-8")
    return Path(d)


def _fight_contract():
    return {
        "template_id": "fight_exchange",
        "beats": ["setup", "attack", "impact", "reaction", "recovery"],
        "blocking": "A left, B right",
        "camera_rule": "stable medium",
        "continuity_must": ["same sword"],
        "negative": ["extra hit"],
        "attack_path": "left to right slash",
        "impact_frame": "end frame",
        "action_scope": "one hit",
        "contact_points": ["sword edge to shield"],
        "force_direction": "screen right",
        "speed_curve": "fast then stop",
        "spatial_path": "A advances one step",
        "camera_path": "small push",
        "readability_beats": ["hit silhouette clear"],
        "recovery_beat": "B staggers",
        "degrade_plan": "split setup/impact/reaction",
    }


def test_spectacle_contract_audit_blocks_missing_fight_contract():
    root = _mk_storyboard([{"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中追兵"}])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert not result["ok"]
    assert any(f["code"] == "missing_template_contract" for f in result["findings"])
    assert any(f.get("field") == "impact_frame" for f in result["findings"])


def test_spectacle_contract_audit_passes_complete_fight_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "fight_exchange",
        "scene": "挥剑命中追兵",
        "template_contract": _fight_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_plan_writes_motion_manifest(tmp_path):
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "fight_exchange",
        "scene": "挥剑命中追兵",
        "template_contract": _fight_contract(),
    }])

    plan = spectacle_plan.build_plan(root, "第1集")
    manifest = spectacle_plan.write_motion_manifest(root, "第1集", "Clip_01", "fight_exchange")

    assert plan["clips"][0]["motion_control_manifest_path"].endswith("Clip_01/motion_control_manifest.json")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_motion_control_manifest"
    assert "contact_map" in data["control_inputs"]


def test_spectacle_sequence_plan_groups_contiguous_action_clips():
    root = _mk_storyboard([
        {"id": "Clip 1", "template": "fight_exchange", "scene": "CHAR_01 挥剑命中", "template_contract": _fight_contract()},
        {"id": "Clip 2", "template": "chase", "scene": "CHAR_01 沿屋脊追逐", "template_contract": {
            "template_id": "chase",
            "screen_direction": "left_to_right",
            "distance_curve": "closing",
            "spatial_path": "roofline",
            "camera_path": "tracking",
            "parallax_layers": ["roof", "moon"],
        }},
    ])

    plan = spectacle_sequence_plan.build_plan(root, "第1集")

    assert plan["kind"] == "n2d_spectacle_sequence_plan"
    assert plan["summary"]["sequences"] == 1
    seq = plan["sequences"][0]
    assert seq["sequence_type"] == "mixed_action"
    assert seq["clip_order"] == ["Clip_01", "Clip_02"]
    assert "CHAR_01" in seq["subject_slots"]["characters"]


def test_sequence_plan_embeds_beat_decomposition_for_action_clips():
    root = _mk_storyboard([
        {"id": "Clip 1", "template": "fight_exchange",
         "scene": "CHAR_01 出拳，对方格挡后反击命中", "template_contract": _fight_contract()},
    ])

    plan = spectacle_sequence_plan.build_plan(root, "第1集")
    row = plan["clips"][0]

    # 动作行带逐拍拆镜推荐 + 检测到的节拍类别（一镜塞了完整攻防回合）。
    assert [b["beat"] for b in row["beat_decomposition"]] == ["setup_attack", "impact", "react_recover"]
    assert set(row["beat_categories"]) >= {"attack", "block", "counter", "impact"}


def test_sequence_plan_injects_identity_lock_and_same_frame_cap():
    root = _mk_storyboard([
        {"id": "Clip 1", "template": "fight_exchange",
         "scene": "CHAR_01 与 CHAR_02 缠斗，CHAR_03 在旁观战 命中",
         "template_contract": _fight_contract()},
    ])

    plan = spectacle_sequence_plan.build_plan(root, "第1集")
    seq = plan["sequences"][0]

    # 负向身份锁词注入序列契约。
    assert "shifting jawline" in seq["negative_identity_lock"]
    # 三具名角色同框 > 2 → 进 over_cap_clips，建议拆镜。
    assert seq["same_frame_policy"]["cap"] == 2
    assert "Clip_01" in seq["same_frame_policy"]["over_cap_clips"]
    # 运动强度连续档 + 3-4 角度建议。
    assert plan["clips"][0]["motion_intensity"] == 3
    assert "3" in seq["identity_reference_advice"] or "3–4" in seq["identity_reference_advice"]


def test_scene_layer_pack_scaffolds_large_scene_pack():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "large_establishing",
        "scene": "LOC_01 宗门大殿全貌，万人广场",
        "large_scene_contract": {
            "reuse_asset_id": "LOC_01",
            "landmark_anchor": "山门巨匾",
            "scale_reference": "人群像米粒，殿门十丈高",
            "parallax_planes": ["云雾", "殿门", "远山"],
        },
    }])

    plan = scene_layer_pack.build_plan(root, "第1集")

    assert plan["summary"]["scene_layer_packs"] == 1
    pack = plan["packs"][0]["pack"]
    assert pack["kind"] == "n2d_scene_layer_pack"
    assert pack["loc_id"] == "LOC_01"
    assert pack["landmark_anchor"] == "山门巨匾"


def test_spectacle_probe_pack_selects_representative_types():
    root = _mk_storyboard([
        {"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中追兵", "template_contract": _fight_contract()},
        {"id": "Clip 2", "template": "chase", "scene": "屋脊追逐，左到右紧追"},
        {"id": "Clip 3", "template": "flight", "scene": "腾云驾雾穿过云海"},
        {"id": "Clip 4", "scene": "宗门大殿全貌，万人广场，大场景航拍"},
    ])

    pack = spectacle_probe_pack.build_probe_pack(root, "第1集")
    types = {p["spectacle_type"] for p in pack["probe_clips"]}

    assert {"fight_exchange", "chase", "flight", "large_establishing"}.issubset(types)
    assert pack["benchmark_schema"]["kind"] == "n2d_spectacle_backend_benchmark"


def test_action_edit_cues_contains_hit_stop():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "fight_exchange",
        "scene": "挥剑命中追兵",
        "template_contract": _fight_contract(),
    }])

    cues = action_edit_cues.build_cues(root, "第1集")

    assert cues["kind"] == "n2d_action_edit_cues"
    assert cues["clips"][0]["cues"][0]["cue"] == "hit_stop"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
