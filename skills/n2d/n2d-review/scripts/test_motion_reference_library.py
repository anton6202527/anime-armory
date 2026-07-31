#!/usr/bin/env python3
"""Tests for motion_reference_library.py（沉淀已过检奇观 clip 为可复用动作/运镜参考）。

cd skills/n2d/n2d-review/scripts && python -m pytest test_motion_reference_library.py
"""
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import motion_reference_library as mrl  # noqa: E402


def _seed(root: Path, *, qc_checks, clip_order=("Clip_01", "Clip_02"),
          seq_type="fight", with_media=("Clip_01",)):
    """落盘一集的 序列总账 + 视频QC + 路由 + 视频媒体，返回作品根。"""
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "spectacle_sequence_plan_第1集.json").write_text(json.dumps({
        "kind": "n2d_spectacle_sequence_plan",
        "sequences": [{
            "sequence_id": "SEQ_01",
            "sequence_type": seq_type,
            "clip_order": list(clip_order),
            "subject_slots": {"characters": ["CHAR_01"]},
            "asset_persistence": {"assets": ["WEAPON_01"]},
            "path_lock": {"screen_direction": "left_to_right"},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "spectacle_video_qc_第1集.json").write_text(
        json.dumps({"checks": qc_checks}, ensure_ascii=False), encoding="utf-8")

    pdir = root / "出视频" / "第1集" / "prompt"
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "video_model_routes.json").write_text(json.dumps({
        "routes": [{"clip_id": "Clip_01", "primary_backend": "kling", "quality_tier": "A"}],
    }, ensure_ascii=False), encoding="utf-8")

    vdir = root / "出视频" / "第1集" / "视频"
    vdir.mkdir(parents=True, exist_ok=True)
    for clip in with_media:
        (vdir / f"{clip}.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    return root


def test_build_updates_admits_measured_clip_with_media(tmp_path):
    root = _seed(tmp_path, qc_checks=[
        {"clip": "Clip_01", "evidence_status": "measured"},
        {"clip": "Clip_02", "evidence_status": "unmeasured"},
    ])

    result = mrl.build_updates(root, "第1集")

    # 仅 measured 且有媒体的 Clip_01 入库；Clip_02（unmeasured）被滤掉。
    assert len(result["updates"]) == 1
    upd = result["updates"][0]
    assert upd["reference_id"] == "第1集_Clip_01_fight"
    assert upd["clip_id"] == "Clip_01"
    assert upd["backend"] == "kling"
    assert upd["quality_tier"] == "A"
    assert upd["evidence_status"] == "measured"
    assert upd["media_path"].endswith("Clip_01.mp4")
    assert upd["constraints"]["characters"] == ["CHAR_01"]
    assert upd["constraints"]["assets"] == ["WEAPON_01"]
    assert "reference_video_motion" in upd["usage"]


def test_build_updates_accepts_all_strong_evidence_tiers(tmp_path):
    root = _seed(tmp_path, clip_order=("Clip_01",), qc_checks=[
        {"clip": "Clip_01", "evidence_status": "vlm_verified"},
    ])

    result = mrl.build_updates(root, "第1集")

    assert len(result["updates"]) == 1
    assert result["updates"][0]["evidence_status"] == "vlm_verified"


def test_build_updates_skips_measured_clip_without_media(tmp_path):
    # 实测过检但磁盘上没有对应视频 → 没有可复用的真实参考素材，不入库。
    root = _seed(tmp_path, clip_order=("Clip_01",),
                 qc_checks=[{"clip": "Clip_01", "evidence_status": "measured"}],
                 with_media=())

    result = mrl.build_updates(root, "第1集")

    assert result["updates"] == []


def test_build_updates_skips_unmeasured_evidence(tmp_path):
    root = _seed(tmp_path, clip_order=("Clip_01",), qc_checks=[
        {"clip": "Clip_01", "evidence_status": "claimed"},
    ])

    result = mrl.build_updates(root, "第1集")

    assert result["updates"] == []


def test_load_library_returns_empty_skeleton_when_absent(tmp_path):
    lib = mrl.load_library(tmp_path)

    assert lib["kind"] == mrl.MOTION_REFERENCE_LIBRARY_KIND
    assert lib["references"] == []


def test_apply_updates_writes_dedupes_and_summarizes(tmp_path):
    updates = [
        {"reference_id": "第1集_Clip_02_chase", "spectacle_type": "chase", "clip_id": "Clip_02"},
        {"reference_id": "第1集_Clip_01_fight", "spectacle_type": "fight", "clip_id": "Clip_01"},
    ]

    lib = mrl.apply_updates(tmp_path, updates)

    # 写盘 + 按 reference_id 排序 + summary 汇总。
    assert [r["reference_id"] for r in lib["references"]] == [
        "第1集_Clip_01_fight", "第1集_Clip_02_chase"]
    assert lib["summary"]["references"] == 2
    assert lib["summary"]["spectacle_types"] == ["chase", "fight"]
    on_disk = json.loads((tmp_path / "生产数据" / "motion_reference_library.json").read_text(encoding="utf-8"))
    assert on_disk["kind"] == mrl.MOTION_REFERENCE_LIBRARY_KIND
    assert len(on_disk["references"]) == 2


def test_apply_updates_overwrites_same_reference_id(tmp_path):
    mrl.apply_updates(tmp_path, [
        {"reference_id": "第1集_Clip_01_fight", "backend": "kling", "spectacle_type": "fight"}])

    lib = mrl.apply_updates(tmp_path, [
        {"reference_id": "第1集_Clip_01_fight", "backend": "veo", "spectacle_type": "fight"}])

    # 重跑同一集应原地更新，而非追加重复条目。
    assert len(lib["references"]) == 1
    assert lib["references"][0]["backend"] == "veo"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
