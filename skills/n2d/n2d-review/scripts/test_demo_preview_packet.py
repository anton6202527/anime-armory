#!/usr/bin/env python3
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import demo_preview_packet as dpp  # noqa: E402


def test_sample_points_scale_clip_midpoints_to_master_duration() -> None:
    clips = [
        {"clip": "Clip_01", "story_mid_sec": 10.0},
        {"clip": "Clip_02", "story_mid_sec": 40.0},
        {"clip": "Clip_03", "story_mid_sec": 90.0},
    ]

    points = dpp.sample_points_from_storyboard(
        clips,
        storyboard_total_sec=100.0,
        master_duration_sec=50.0,
        max_samples=8,
    )

    by_label = {row["label"]: row for row in points}
    assert by_label["Clip_01_mid"]["time_sec"] == 5.0
    assert by_label["Clip_02_mid"]["time_sec"] == 20.0
    assert by_label["Clip_03_mid"]["time_sec"] == 45.0
    assert by_label["tail"]["time_sec"] == 49.4
    assert by_label["Clip_01_mid"]["storyboard_to_master_scale"] == 0.5


def test_sample_points_keeps_opening_and_tail_when_limited() -> None:
    clips = [{"clip": f"Clip_{i:02d}", "story_mid_sec": float(i * 10)} for i in range(1, 10)]

    points = dpp.sample_points_from_storyboard(
        clips,
        storyboard_total_sec=100.0,
        master_duration_sec=100.0,
        max_samples=5,
    )

    assert len(points) == 5
    assert points[0]["label"] == "opening"
    assert points[-1]["label"] == "tail"


def test_packet_status_ready_for_internal_demo() -> None:
    status = dpp.packet_status(
        {"exists": True},
        {"合规用途": "internal_only", "一致性严格度": "demo"},
        {
            "distribution_intent": "internal_only",
            "intended_use": {"public_release": False, "paid_distribution": False},
        },
    )

    assert status == "ready_for_human_demo_preview"


def test_packet_status_blocks_missing_master() -> None:
    status = dpp.packet_status(
        {"exists": False},
        {"合规用途": "internal_only", "一致性严格度": "demo"},
        {"distribution_intent": "internal_only", "intended_use": {}},
    )

    assert status == "needs_final_master"


def test_render_markdown_declares_non_acceptance() -> None:
    md = dpp.render_markdown({
        "episode": "第1集",
        "status": "ready_for_human_demo_preview",
        "asset": {"path": "合成/第1集/成片_第1集_zh.mp4"},
        "source_reports": {},
        "artifacts": {},
        "checklist": [],
        "sample_points": [],
        "production_debt_notes": ["本包不是 n2d-review 正式验收，不回写验收通过。"],
    })

    assert "不是正式验收" in md
    assert "不回写验收通过" in md


def test_human_checklist_requires_frame_face_drift_watch() -> None:
    checks = {row["id"]: row["check"] for row in dpp.human_checklist()}

    assert "frame_face_drift" in checks
    assert "video_face_drift_watch.py" in checks["frame_face_drift"]
    assert "逐 Clip 中点抽样" in checks["frame_face_drift"]
