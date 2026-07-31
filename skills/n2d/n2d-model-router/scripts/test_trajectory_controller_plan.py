#!/usr/bin/env python3
"""Tests for optional trajectory controller planning."""
from __future__ import annotations

import json
from pathlib import Path

import trajectory_controller_plan as tcp


def test_trajectory_controller_plan_marks_env_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MOTIONCTRL_HOME", raising=False)
    monkeypatch.delenv("CAMERACTRL_HOME", raising=False)
    monkeypatch.delenv("DRAGNUWA_HOME", raising=False)
    root = tmp_path / "制漫剧" / "测试剧"
    path = root / "出视频" / "第1集" / "prompt" / "video_model_routes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "routes": [{
            "clip_id": "Clip_01",
            "shot_type": "flight",
            "primary_backend": "seedance",
            "execution_recipe": {
                "execution_backend": "seedance",
                "control_inputs": {
                    "required_inputs": ["camera_path", "spatial_path", "parallax_layers"],
                    "manifest_path": "出视频/第1集/control/Clip_01/motion_control_manifest.json",
                },
            },
        }],
    }, ensure_ascii=False), encoding="utf-8")

    plan = tcp.build_plan(root, "第1集")

    assert plan["kind"] == "n2d_trajectory_controller_plan"
    assert plan["summary"]["controller_candidate_clips"] == 1
    clip = plan["clips"][0]
    assert clip["controller"] == "motionctrl"
    assert clip["status"] == "planned_env_missing"
    assert "camera_path" in clip["required_inputs"]
