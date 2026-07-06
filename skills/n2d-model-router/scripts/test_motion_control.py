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


def test_build_skeleton_can_mark_degrade_only_without_faking_inputs():
    sk = mc.build_skeleton("第1集", "Clip_01", ["pose_sequence"], degrade_only=True)
    assert sk["status"] == "degrade_only"
    assert sk["control_inputs"]["pose_sequence"]["status"] == "missing"


def test_apply_degrade_plan_preserves_ready_manifest():
    ready = mc.build_skeleton("第1集", "Clip_01", ["pose_sequence"], {"status": "ready"})
    out = mc.apply_degrade_plan(ready, "拆手部+反打")
    assert out["status"] == "ready"
    assert out["degrade_plan"] == "拆手部+反打"


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
         "motion_control": {"level": "required", "required_inputs": ["pose_sequence", "camera_path"]}},
    ]
    got = mc.routes_requiring_control(routes)
    assert [t["clip_id"] for t in got] == ["Clip_01", "Clip_03"]
    assert got[0]["required_inputs"] == ["pose_sequence", "depth_sequence"]
    assert got[0]["contact_fields_required"] is True
    assert got[1]["required_inputs"] == ["pose_sequence", "camera_path"]
    assert got[1]["contact_fields_required"] is False


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


def test_readiness_for_chase_control_does_not_require_contact_fields(tmp_path):
    root = str(tmp_path)
    d = os.path.join(root, "出视频/第1集/control/Clip_03")
    os.makedirs(d)
    open(os.path.join(d, "openpose_001.png"), "w").close()
    open(os.path.join(d, "camera_path.json"), "w").write("{}")
    man = mc.build_skeleton("第1集", "Clip_03", ["pose_sequence", "camera_path"])
    man["control_inputs"]["pose_sequence"]["status"] = "ready"
    man["control_inputs"]["camera_path"]["status"] = "ready"
    man["status"] = "ready"

    result = mc.readiness(man, root, ["pose_sequence", "camera_path"], contact_fields_required=False)

    assert result["gate_pass"] is True
    assert result["missing_contacts"] == []


# ---- 步内中间产物指纹缓存（G11）----

def _seed_frame(root, rel, content=b"px"):
    """写一张假源首/尾帧 PNG（内容指纹只看字节，不需真 PNG）。"""
    full = os.path.join(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as fh:
        fh.write(content)
    return rel


def _seed_output(root, ep, clip, key):
    """写该输入键的产物文件（让 _asset_present 命中）。返回 out_rel。"""
    out_rel = f"{mc.control_dir_rel(ep, clip)}/{mc.input_filename(key)}"
    # 产物是 %03d glob 模式 → 落一个具体帧
    full = os.path.join(root, out_rel.replace("%03d", "000"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "wb").close()
    return out_rel


def test_cache_fingerprint_folds_frames_and_params(tmp_path):
    root = str(tmp_path)
    rel = _seed_frame(root, "出图/第1集/图片/镜头01.png", b"aaa")
    fp = mc.cache_fingerprint(root, [rel], "pose_sequence")
    assert fp["sha"] and rel in fp["files"]
    assert fp["params"] == mc._params_for("pose_sequence")
    # 改源帧像素 → base sha 变
    _seed_frame(root, rel, b"bbb")
    assert mc.cache_fingerprint(root, [rel], "pose_sequence")["sha"] != fp["sha"]
    # 同源帧不同输入键 → base sha 同（params 单独存），但 params 不同 → 缓存判定会失配
    _seed_frame(root, rel, b"aaa")
    depth_fp = mc.cache_fingerprint(root, [rel], "depth_sequence")
    assert depth_fp["sha"] == fp["sha"]
    assert depth_fp["params"] != fp["params"]


def test_cache_is_fresh_tracks_frames_and_params(tmp_path):
    root = str(tmp_path)
    rel = _seed_frame(root, "出图/第1集/图片/镜头01.png", b"aaa")
    rec = mc.cache_fingerprint(root, [rel], "pose_sequence")
    assert mc.cache_is_fresh(rec, root, [rel], "pose_sequence") is True
    # 源帧变 → 不新鲜
    _seed_frame(root, rel, b"ccc")
    assert mc.cache_is_fresh(rec, root, [rel], "pose_sequence") is False
    # 记录缺失/形状不对 → False（诚实）
    assert mc.cache_is_fresh(None, root, [rel], "pose_sequence") is False
    assert mc.cache_is_fresh({"sha": "x"}, root, [rel], "pose_sequence") is False
    # 参数版本变了（模拟 bump）→ 不新鲜
    _seed_frame(root, rel, b"aaa")
    stale_params = dict(rec, params={**rec["params"], "_version": 999})
    assert mc.cache_is_fresh(stale_params, root, [rel], "pose_sequence") is False


def test_cache_decision_skip_when_fresh(tmp_path):
    root, ep, clip, key = str(tmp_path), "第1集", "Clip_01", "pose_sequence"
    rel = _seed_frame(root, "出图/第1集/图片/镜头01.png", b"aaa")
    out_rel = _seed_output(root, ep, clip, key)
    man = mc.record_cache_fingerprint(mc.build_skeleton(ep, clip, [key]), root, key, [rel])
    d = mc.cache_decision(man, root, key, [rel], out_rel)
    assert d["action"] == "skip" and d["reason"] == "fresh"


def test_cache_decision_extract_when_frames_changed(tmp_path):
    root, ep, clip, key = str(tmp_path), "第1集", "Clip_01", "pose_sequence"
    rel = _seed_frame(root, "出图/第1集/图片/镜头01.png", b"aaa")
    out_rel = _seed_output(root, ep, clip, key)
    man = mc.record_cache_fingerprint(mc.build_skeleton(ep, clip, [key]), root, key, [rel])
    _seed_frame(root, rel, b"DIFFERENT")  # 源帧改了
    d = mc.cache_decision(man, root, key, [rel], out_rel)
    assert d["action"] == "extract" and d["reason"] == "stale"


def test_cache_decision_extract_when_output_missing(tmp_path):
    root, ep, clip, key = str(tmp_path), "第1集", "Clip_01", "pose_sequence"
    rel = _seed_frame(root, "出图/第1集/图片/镜头01.png", b"aaa")
    out_rel = f"{mc.control_dir_rel(ep, clip)}/{mc.input_filename(key)}"  # 不落产物
    man = mc.record_cache_fingerprint(mc.build_skeleton(ep, clip, [key]), root, key, [rel])
    d = mc.cache_decision(man, root, key, [rel], out_rel)
    # 指纹新鲜但产物不在 → 不臆造跳过
    assert d["action"] == "extract" and d["reason"] == "missing_output"


def test_cache_decision_extract_when_no_fingerprint(tmp_path):
    root, ep, clip, key = str(tmp_path), "第1集", "Clip_01", "pose_sequence"
    rel = _seed_frame(root, "出图/第1集/图片/镜头01.png", b"aaa")
    out_rel = _seed_output(root, ep, clip, key)
    man = mc.build_skeleton(ep, clip, [key])  # 无 generate_cache
    d = mc.cache_decision(man, root, key, [rel], out_rel)
    assert d["action"] == "extract" and d["reason"] == "no_fingerprint"


def test_cache_decision_force_overrides_fresh(tmp_path):
    root, ep, clip, key = str(tmp_path), "第1集", "Clip_01", "pose_sequence"
    rel = _seed_frame(root, "出图/第1集/图片/镜头01.png", b"aaa")
    out_rel = _seed_output(root, ep, clip, key)
    man = mc.record_cache_fingerprint(mc.build_skeleton(ep, clip, [key]), root, key, [rel])
    # 不 force → skip
    assert mc.cache_decision(man, root, key, [rel], out_rel)["action"] == "skip"
    # --no-cache → 强制重抽，留痕 forced
    d = mc.cache_decision(man, root, key, [rel], out_rel, force=True)
    assert d["action"] == "extract" and d["reason"] == "forced"


def test_env_truthy():
    assert mc._env_truthy("1") and mc._env_truthy("true") and mc._env_truthy("ON")
    assert not mc._env_truthy("") and not mc._env_truthy(None) and not mc._env_truthy("0")


def test_record_cache_fingerprint_is_pure(tmp_path):
    root = str(tmp_path)
    rel = _seed_frame(root, "出图/第1集/图片/镜头01.png", b"aaa")
    man = mc.build_skeleton("第1集", "Clip_01", ["pose_sequence"])
    out = mc.record_cache_fingerprint(man, root, "pose_sequence", [rel])
    assert "generate_cache" not in man  # 入参未被就地改
    assert "pose_sequence" in out["generate_cache"]
