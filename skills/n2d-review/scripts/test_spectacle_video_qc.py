#!/usr/bin/env python3
"""Tests for high-dynamic video QC evidence and motion reference library."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import consistency_audit  # noqa: E402
import motion_reference_library  # noqa: E402
import spectacle_video_qc  # noqa: E402


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "制漫剧" / "测试剧"
    _write_json(root / "脚本" / "第1集" / "storyboard.json", {
        "clips": [{
            "id": "Clip 1",
            "template": "fight_exchange",
            "scene": "CHAR_01 挥剑命中 WEAPON_01",
            "characters": ["CHAR_01/常态"],
            "template_contract": {
                "speed_curve": "accelerate-hit-stop",
                "spatial_path": "A left to right",
                "camera_path": "short push",
                "impact_frame": "last frame",
                "contact_points": ["blade to shield"],
            },
        }],
    })
    _write_json(root / "出视频" / "第1集" / "control" / "Clip_01" / "motion_control_manifest.json", {
        "kind": "n2d_motion_control_manifest",
        "status": "ready",
        "control_inputs": {
            "pose_sequence": {"status": "ready", "path": "pose.json"},
            "depth_map": {"status": "ready", "path": "depth.png"},
            "contact_map": {"status": "ready", "path": "contact.json"},
        },
    })
    video = root / "出视频" / "第1集" / "video" / "Clip_01.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"fake mp4")
    return root


def test_spectacle_video_qc_writes_sidecars_and_enters_consistency_audit(tmp_path: Path) -> None:
    root = _root(tmp_path)

    report = spectacle_video_qc.build_report(root, "第1集")
    paths = spectacle_video_qc.write_report(report, root, "第1集", sidecars=True)

    assert report["kind"] == "n2d_spectacle_video_qc"
    assert report["summary"]["contract_only_clips"] == 1
    assert paths["motion"].is_file()
    sections = consistency_audit.run(str(root), "第1集")["sections"]
    specv = sections["高动态成片证据(SPECV)"]
    assert specv["skipped"] is False
    assert "warn" in specv["verdicts"]


def test_motion_reference_library_registers_measured_clip_only(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write_json(root / "生产数据" / "spectacle_sequence_plan_第1集.json", {
        "kind": "n2d_spectacle_sequence_plan",
        "sequences": [{
            "sequence_id": "SEQ_001",
            "sequence_type": "fight_exchange",
            "clip_order": ["Clip_01"],
            "subject_slots": {"characters": ["CHAR_01"]},
            "asset_persistence": {"assets": ["WEAPON_01"]},
            "path_lock": {"screen_direction": "left_to_right"},
        }],
    })
    _write_json(root / "生产数据" / "spectacle_video_qc_第1集.json", {
        "kind": "n2d_spectacle_video_qc",
        "checks": [{"clip": "Clip_01", "evidence_status": "measured"}],
    })
    _write_json(root / "出视频" / "第1集" / "prompt" / "video_model_routes.json", {
        "routes": [{"clip_id": "Clip_01", "primary_backend": "kling", "quality_tier": "high"}],
    })

    updates = motion_reference_library.build_updates(root, "第1集")
    lib = motion_reference_library.apply_updates(root, updates["updates"])

    assert len(updates["updates"]) == 1
    ref = lib["references"][0]
    assert ref["media_path"].endswith("Clip_01.mp4")
    assert ref["backend"] == "kling"
    assert ref["constraints"]["characters"] == ["CHAR_01"]


def test_qc_dimensions_unverified_without_external_reports(tmp_path: Path) -> None:
    root = _root(tmp_path)
    report = spectacle_video_qc.build_report(root, "第1集")
    row = report["checks"][0]
    # 无任何 external 实测 → 八维全 unverified，且 summary 列出八维。
    assert set(row["qc_dimensions"].values()) == {"unverified"}
    assert "optical_flow_direction" in report["summary"]["qc_dimensions"]
    assert "limb_artifact" in row["qc_dimensions"]
    # 有成片但动作关键新维未测 → 提示去跑动作-artifact runner。
    assert any("动作关键维未实测" in f["message"] for f in report["findings"])
    # 采样计划带高光流加密策略。
    assert row["sampling_plan"]["strategy"] == "optical_flow_guided"


def test_qc_dimensions_verified_when_artifact_sidecar_present(tmp_path: Path) -> None:
    root = _root(tmp_path)
    # 动作-artifact runner 写入光流方向/肢体畸变/运动模糊实测 → 这几维转 verified。
    _write_json(root / "生产数据" / "spectacle_motion_artifacts_第1集.json", {
        "checks": [{
            "clip": "Clip_01",
            "optical_flow_direction": "matches camera_path",
            "limb_artifact_score": 0.02,
            "motion_blur_plausibility": 0.91,
        }],
    })
    report = spectacle_video_qc.build_report(root, "第1集")
    qc = report["checks"][0]["qc_dimensions"]
    assert qc["optical_flow_direction"] == "verified"
    assert qc["limb_artifact"] == "verified"
    assert qc["motion_blur_plausibility"] == "verified"
    # 这三维已测 → 不再提示动作关键维未实测。
    assert not any("动作关键维未实测" in f["message"] for f in report["findings"])
