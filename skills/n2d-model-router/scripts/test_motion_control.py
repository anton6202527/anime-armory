#!/usr/bin/env python3
"""motion_control 纯函数单测。从脚本自身目录跑：
    cd skills/n2d-model-router/scripts && python -m pytest test_motion_control.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion_control as mc  # noqa: E402


def test_manifest_path_and_entry():
    assert mc.manifest_rel_path("第1集", "Clip_03") == "出视频/第1集/control/Clip_03/motion_control_manifest.json"
    e = mc.new_input_entry("第1集", "Clip_03", "pose_sequence")
    assert e["type"] == "openpose_or_dwpose" and e["status"] == "missing"
    assert e["path"] == "出视频/第1集/control/Clip_03/openpose_%03d.png"


def test_build_skeleton_is_planned_and_blocks():
    sk = mc.build_skeleton("第1集", "Clip_01", ["pose_sequence", "depth_sequence", "contact_map"])
    assert sk["kind"] == mc.MOTION_CONTROL_MANIFEST_KIND
    assert sk["status"] == "planned"  # 非 ready → gate 会阻断（这是对的）
    assert set(sk["control_inputs"]) == {"pose_sequence", "depth_sequence", "contact_map"}
    assert all(v["status"] == "missing" for v in sk["control_inputs"].values())
    for f in mc.CONTACT_FIELDS:
        assert f in sk


def test_build_skeleton_preserves_filled_fields():
    existing = {
        "status": "ready",
        "control_inputs": {
            "pose_sequence": {"type": "openpose_or_dwpose", "status": "ready", "path": "real/pose.png"},
        },
        "contact_points": [{"a": "A.hand", "b": "B.wrist", "frames": "1-9"}],
    }
    sk = mc.build_skeleton("第1集", "Clip_01", ["pose_sequence", "depth_sequence"], existing)
    assert sk["status"] == "ready"                                   # 不回退
    assert sk["control_inputs"]["pose_sequence"]["path"] == "real/pose.png"  # 保留已填
    assert sk["control_inputs"]["depth_sequence"]["status"] == "missing"     # 新增缺的
    assert sk["contact_points"]                                       # 接触语义保留


def test_routes_requiring_control_filters_required_only():
    routes = [
        {"clip_id": "Clip_01", "shot_type": "fight_exchange",
         "motion_control": {"level": "required", "required_inputs": ["pose_sequence", "depth_sequence"]}},
        {"clip_id": "Clip_02", "shot_type": "dialogue",
         "motion_control": {"level": "none"}},
        {"clip_id": "Clip_03", "shot_type": "chase",
         "motion_control": {"level": "recommended", "required_inputs": ["pose_sequence"]}},
    ]
    got = mc.routes_requiring_control(routes)
    assert [t["clip_id"] for t in got] == ["Clip_01"]
    assert got[0]["required_inputs"] == ["pose_sequence", "depth_sequence"]


def test_input_is_filled():
    assert mc._input_is_filled({"status": "ready", "path": "x.png"})
    assert mc._input_is_filled({"status": "not_needed", "uri": "s3://a/b"})
    assert not mc._input_is_filled({"status": "missing", "path": "x.png"})
    assert not mc._input_is_filled({"status": "ready"})  # ready 但无 path/uri/glob
    assert not mc._input_is_filled("nope")


def test_asset_present_with_real_files(tmp_path):
    root = str(tmp_path)
    d = os.path.join(root, "出视频/第1集/control/Clip_01")
    os.makedirs(d)
    open(os.path.join(d, "openpose_001.png"), "w").close()
    # %03d 模式 → glob 命中
    assert mc._asset_present(root, {"path": "出视频/第1集/control/Clip_01/openpose_%03d.png"})
    assert not mc._asset_present(root, {"path": "出视频/第1集/control/Clip_01/depth_%03d.png"})
    assert mc._asset_present(root, {"uri": "s3://bucket/x"})        # 远端视为已指定
    assert not mc._asset_present(root, {})


def test_reconcile_flips_present_inputs_only(tmp_path):
    root = str(tmp_path)
    d = os.path.join(root, "出视频/第1集/control/Clip_01")
    os.makedirs(d)
    open(os.path.join(d, "openpose_001.png"), "w").close()
    man = mc.build_skeleton("第1集", "Clip_01", ["pose_sequence", "depth_sequence"])
    out, changed = mc.reconcile(man, root)
    assert changed == ["pose_sequence"]
    assert out["control_inputs"]["pose_sequence"]["status"] == "ready"
    assert out["control_inputs"]["depth_sequence"]["status"] == "missing"
    assert out["status"] == "planned"  # 顶层 status 不自动翻


def test_readiness_gate_pass_logic(tmp_path):
    root = str(tmp_path)
    # planned 永远不过
    man = mc.build_skeleton("第1集", "Clip_01", ["pose_sequence"])
    assert mc.readiness(man, root, ["pose_sequence"])["gate_pass"] is False
    # degrade_only + degrade_plan 过
    man2 = dict(man, status="degrade_only", degrade_plan="拆手部+反打")
    assert mc.readiness(man2, root, ["pose_sequence"])["gate_pass"] is True
    # degrade_only 无 plan 不过
    man3 = dict(man, status="degrade_only", degrade_plan="")
    assert mc.readiness(man3, root, ["pose_sequence"])["gate_pass"] is False


def test_readiness_ready_requires_inputs_and_contacts(tmp_path):
    root = str(tmp_path)
    d = os.path.join(root, "出视频/第1集/control/Clip_01")
    os.makedirs(d)
    open(os.path.join(d, "openpose_001.png"), "w").close()
    man = mc.build_skeleton("第1集", "Clip_01", ["pose_sequence"])
    man["control_inputs"]["pose_sequence"]["status"] = "ready"
    man["status"] = "ready"
    # 接触语义还没填 → 不过
    assert mc.readiness(man, root, ["pose_sequence"])["gate_pass"] is False
    for f in mc.CONTACT_FIELDS:
        man[f] = ["x"]
    assert mc.readiness(man, root, ["pose_sequence"])["gate_pass"] is True
