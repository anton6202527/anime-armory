from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import n2d_schema_registry as reg


def test_validate_known_payload_passes() -> None:
    payload = {
        "kind": "n2d_context_pack",
        "version": 1,
        "root": "/tmp/work",
        "episode": "第1集",
        "stage_key": "image_prompt",
        "action_contract": {},
        "files": [{"relpath": "_设置.md", "exists": True}],
    }
    assert reg.validate_payload(payload) == []


def test_validate_runtime_v2_artifact_kinds_pass() -> None:
    payloads = [
        {
            "kind": "n2d_episode_graph", "version": 1, "root": "/tmp/work", "episode": "第1集",
            "nodes": [{"id": "episode:第1集", "type": "episode"}], "edges": [], "source_files": [],
            "graph_hash": "abc", "summary": {}, "status": "pass",
        },
        {
            "kind": "n2d_blocking_bundle", "version": 1, "episode": "第1集", "stage_key": "video",
            "stop_reason": "needs_payment_confirm", "category": "paid_confirmation", "blocked": True,
            "blockers": [],
        },
        {
            "kind": "n2d_video_execution_adapter_registry", "version": 2, "adapters": {},
        },
        {
            "kind": "n2d_post_video_proxy", "version": 1, "episode": "第1集", "status": "ready",
            "timeline": [], "output": "合成/第1集/_proxy/actual_rough_cut.mp4",
        },
        {
            "kind": "n2d_multishot_batch", "version": 1, "episode": "第1集", "group_id": "MSG_01",
            "backend": "seedance", "members": ["Clip_01", "Clip_02"], "status": "prepared", "shots": [],
        },
    ]
    assert all(reg.validate_payload(payload) == [] for payload in payloads)


def test_validate_payload_blocks_missing_required() -> None:
    issues = reg.validate_payload({"kind": "n2d_batch_queue", "version": 1})
    messages = [item["message"] for item in issues]
    assert any("root" in msg for msg in messages)
    assert any("tasks" in msg for msg in messages)


def test_validate_episode_manifest_payload_passes() -> None:
    payload = {
        "kind": "n2d_episode_manifest",
        "schema_version": 2,
        "episode": "第1集",
        "stage": "all",
        "production_mode": "原生音画",
        "artifacts": [
            {
                "stage": "source",
                "path": "脚本/第1集/raw.txt",
                "exists": True,
                "kind": "file",
                "sha256": "abc",
            }
        ],
    }
    assert reg.validate_payload(payload) == []


def test_validate_leitmotif_registry_payload_passes() -> None:
    payload = {
        "kind": "n2d_leitmotif_registry",
        "version": 1,
        "motifs": [
            {"id": "MOTIF_hero", "subject": ["CHAR_hero"], "desc": "two-note cold string motif"}
        ],
    }
    assert reg.validate_payload(payload) == []


def test_validate_script_planning_payloads_pass() -> None:
    assert reg.validate_payload({
        "kind": "n2d_anchor_plan",
        "schema_version": 1,
        "episode": "第1集",
        "planned": [{
            "clip_index": 1,
            "clip_id": "EP01_CLIP01",
            "duration": 7,
            "rule": "D0 三帧契约默认中锚",
            "anchors": [{
                "anchor_png": "出图/第1集/图片/EP01_CLIP01_first_mid.png",
                "at_sec": 3.5,
                "use": "qc",
                "reason": "default",
            }],
            "added_cost": {"images": 1, "video_segments": 0},
        }],
    }) == []
    assert reg.validate_payload({
        "kind": "n2d_motif_plan",
        "schema_version": 1,
        "episode": "第1集",
        "genre": {"genre": "系统流"},
        "motif_clips": [{
            "clip_index": 8,
            "clip_id": "EP01_CLIP08",
            "motif_type": "system_panel",
            "motif_id": "MOTIF_系统面板",
            "template": "system_panel",
            "hits": 3,
            "matched": ["光幕", "系统面板"],
            "rule": "命中 system_panel",
            "growth_suggestion": {"level": 2, "panel_tier": "v2"},
        }],
        "summary": {"motif_clips": 1},
    }) == []
    assert reg.validate_payload({
        "kind": "n2d_motif_registry",
        "version": 1,
        "motifs": [{
            "motif_id": "MOTIF_系统面板",
            "motif_type": "system_panel",
            "scope": "复用",
            "growth_state_machine": {
                "bound_vfx": "VFX_系统面板",
                "monotonic_fields": ["level", "panel_tier"],
                "progression": [{
                    "at_clip": "EP01_CLIP08",
                    "level": 2,
                    "panel_tier": "first_reward",
                    "title": "噬妖夺能",
                    "attrs": {"获得": "伪人皮、潜行"},
                    "overlay_lines": ["得到：伪人皮"],
                }],
            },
            "shot_template_id": "system_panel",
            "overlay_spec": {"anchor": "panel_center"},
        }],
    }) == []


def test_validate_motif_registry_blocks_missing_progression_identity() -> None:
    issues = reg.validate_payload({
        "kind": "n2d_motif_registry",
        "version": 1,
        "motifs": [{
            "motif_id": "MOTIF_系统面板",
            "motif_type": "system_panel",
            "growth_state_machine": {
                "progression": [{
                    "at_clip": "EP01_CLIP08",
                    "level": 2,
                    "title": "噬妖夺能",
                }],
            },
        }],
    })

    assert any("panel_tier" in item["message"] for item in issues)


def test_validate_story_integrity_payloads_pass() -> None:
    assert reg.validate_payload({
        "kind": "n2d_story_integrity_ledger",
        "version": 1,
        "episodes": [{"episode": "第1集", "choices": [], "consequences": []}],
    }) == []
    assert reg.validate_payload({
        "kind": "n2d_thread_scheduler",
        "version": 1,
        "threads": [{
            "thread_id": "T001",
            "status": "candidate",
            "opened_ep": "第1集",
            "next_due_ep": "第2集",
            "open_question": "真正供的是谁？",
        }],
    }) == []
    assert reg.validate_payload({
        "kind": "n2d_pilot_arc_contract",
        "version": 1,
        "episode_window": ["第1集", "第2集"],
        "series_promise": "吞妖夺能破宫局",
        "protagonist_desire": "活下去并查清幕后黑手",
        "repeatable_pleasure_loop": "遇妖、识破、夺能、打脸、抬钩",
        "long_question": "皇宫真正供养的是谁？",
    }) == []


def test_validate_production_dashboard_payloads_pass() -> None:
    assert reg.validate_payload({
        "kind": "n2d_production_dashboard",
        "version": 1,
        "root": "/tmp/work",
        "episodes": [{"episode": "第1集", "event_count": 1, "stages": {}}],
        "totals": {"event_count": 1},
    }) == []
    assert reg.validate_payload({
        "kind": "n2d_production_alerts",
        "version": 1,
        "root": "/tmp/work",
        "generated_at": "2026-06-26T00:00:00+00:00",
        "thresholds": {},
        "counts": {"critical": 0, "warn": 0},
        "alerts": [],
    }) == []


def test_validate_storyboard_payload_passes() -> None:
    payload = {
        "kind": "n2d_storyboard",
        "version": 1,
        "episode": "第1集",
        "visual_contract": {"色调基线": "冷青"},
        "style_contract": {"风格名": "冷灰写实3D国风漫剧"},
        "clips": [
            {
                "id": "EP01_CLIP01",
                "duration": 7.0,
                "continuity": {"start_state": "a", "end_state": "b"},
            }
        ],
    }
    assert reg.validate_payload(payload) == []


def test_scan_artifacts_skips_kindless_shot_duration_map(tmp_path: Path) -> None:
    script = tmp_path / "脚本" / "第1集"
    script.mkdir(parents=True)
    (script / "镜头时长.json").write_text(json.dumps({"EP01_CLIP01": 7.0}, ensure_ascii=False), encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path))

    assert payload["status"] == "pass"
    assert payload["checked_count"] == 1
    assert payload["checked"][0]["kind"] == "non_routable_json"


def test_scan_artifacts_validates_json_and_jsonl(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    event = {
        "kind": "n2d_production_event",
        "version": 1,
        "ts": "2026-06-26T00:00:00+00:00",
        "episode": "第1集",
        "stage": "image",
        "event": "generation",
        "source": "unit",
        "trace": {"trace_id": "tr_1"},
    }
    (prod / "production_events.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")
    (prod / "flow_events.jsonl").write_text(json.dumps({
        "kind": "n2d_flow_event", "version": 1, "at": "2026-07-10T00:00:00+0800",
        "event_type": "next_action", "episode": "第1集", "stage": "video",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    (prod / "batch_queue.json").write_text(
        json.dumps({"kind": "n2d_batch_queue", "version": 1, "root": str(tmp_path), "tasks": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    payload = reg.scan_artifacts(str(tmp_path))

    assert payload["status"] == "pass"
    assert payload["checked_count"] == 3
