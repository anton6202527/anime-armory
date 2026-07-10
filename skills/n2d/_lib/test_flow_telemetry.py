from __future__ import annotations

import json
from pathlib import Path

import flow_telemetry as ft


def test_next_action_and_milestone_are_append_only_and_aggregated(tmp_path: Path) -> None:
    payload = {
        "frontier": {"ep": "第1集", "stage_key": "video", "label": "出视频"},
        "stop_reason": "needs_payment_confirm",
        "prework": [
            {"step": "router", "status": "pass", "_cached": True},
            {"step": "gate", "status": "pass"},
        ],
        "gate": {"stage": "video_preflight", "blocked": False},
        "trace": {"trace_id": "trace-1", "span_id": "span-1"},
    }

    ft.record_next_action(tmp_path, payload, 12.5)
    ft.record_milestone(tmp_path, "video_submitted", episode="第1集", stage="video", extra={
        "clip": "Clip_01", "provider": "test", "returncode": 0,
        "secret": "must-not-be-recorded",
    })
    report = ft.report(tmp_path)

    lines = ft.event_path(tmp_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert report["event_count"] == 2
    assert report["stop_reasons"] == {"needs_payment_confirm": 1}
    assert report["prework"]["cache_hit_rate"] == 0.5
    assert report["milestones"] == {"video_submitted": 1}
    milestone = json.loads(lines[1])
    assert "secret" not in milestone["extra"]


def test_stage_transitions_and_latency_percentiles(tmp_path: Path) -> None:
    for stage, elapsed in (("script_stage1", 10), ("image_prompt", 20), ("video", 30)):
        ft.record_next_action(tmp_path, {
            "frontier": {"ep": "第1集", "stage_key": stage},
            "stop_reason": "needs_agent_gen",
            "prework": [],
        }, elapsed)

    report = ft.report(tmp_path)

    assert report["stage_transitions"] == {
        "image_prompt->video": 1,
        "script_stage1->image_prompt": 1,
    }
    assert report["orchestrator_latency_ms"]["p50"] == 20.0
    assert report["orchestrator_latency_ms"]["p95"] == 29.0
