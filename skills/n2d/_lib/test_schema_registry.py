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
        {
            "kind": "n2d_artifact_signoff", "version": 1, "artifact_scope": "stage2_animatic",
            "episode": "第1集", "authored_by": "automation:n2d", "input_fingerprint": {},
            "evidence_fingerprint": {}, "required_approval_groups": [], "approvals": [], "status": "pending",
        },
        {
            "kind": "n2d_autonomy_authorization", "version": 1, "status": "active",
            "policy": "only_high_risk_human", "project_root": "/tmp/work",
            "authorization_id": "AUTH_1", "authorized_by": "user:owner",
            "authorized_at": "2026-08-11T00:00:00+00:00", "source_quote": "继续制作",
            "delegated_reviewer_id": "delegate:n2d-agent",
            "allowed_signoff_profiles": ["table_read", "p2", "animatic", "p3"],
            "allowed_boundary_decisions": ["keep"],
            "human_confirmation_required": ["paid_generation_or_purchase"],
        },
        {
            "kind": "n2d_production_mode_route", "version": 1, "episode": "第1集",
            "status": "aligned", "decision": {}, "signals": {}, "inputs_fingerprint": {},
        },
        {
            "kind": "n2d_editorial_timeline", "version": 1, "episode": "第1集",
            "phase": "animatic", "status": "ready", "duration_sec": 12.0,
            "track_names": ["V1 Picture"], "media": [], "seams": [],
            "otio_path": "生产数据/timelines/第1集/editorial_timeline.otio", "otio_sha256": "abc",
        },
        {
            "kind": "n2d_voice_casting", "version": 1, "status": "casting",
            "policy": "casting_first_final_render_later",
            "roles": [{"role": "沈念", "status": "unselected"}],
            "summary": {"role_count": 1, "locked_count": 0},
        },
        {
            "kind": "n2d_timing_estimate", "version": 1, "episode": "第1集",
            "status": "provisional", "source_fingerprint": "abc", "audio_generated": False,
            "timing_basis": "text_estimate_no_audio",
            "lines": [{
                "line_index": 1, "镜头": "镜头1", "角色": "旁白", "文本": "夜色。",
                "时长": 1.0, "start": 0.0, "end": 1.0, "gap_after": 0.0,
                "timing_basis": "text_estimate_no_audio",
            }],
            "summary": {"line_count": 1, "duration_sec": 1.0},
        },
        {
            "kind": "n2d_shot_timing_basis", "version": 1, "episode": "第1集",
            "timing_basis": "text_estimate_no_audio", "provisional": True,
            "source": "合成/第1集/配音/timing_estimate.json",
            "final_voice_required_before_compose": True,
        },
    ]
    assert all(reg.validate_payload(payload) == [] for payload in payloads)


def test_blocking_bundle_rejects_unregistered_stop_reason() -> None:
    payload = {
        "kind": "n2d_blocking_bundle", "version": 1, "episode": "第1集", "stage_key": "video",
        "stop_reason": "future_silent_branch", "category": "unknown", "blocked": True, "blockers": [],
    }
    assert any("stop_reason" in str(issue.get("pointer")) for issue in reg.validate_payload(payload))


def test_new_audio_and_series_contracts_are_registered() -> None:
    payloads = [
        {"kind": "n2d_bgm_contract", "version": 1, "episode": "第1集", "status": "draft",
         "strategy": "none", "source": {}, "cues": []},
        {"kind": "n2d_series_consistency", "version": 1, "status": "draft", "subtitle_style": {},
         "canonical_names": {}, "dialogue_registers": {}, "audio_baseline": {}},
        {"kind": "n2d_voice_fit_report", "version": 1, "episode": "第1集", "language": "zh",
         "status": "planned", "applied": False, "fit_scope": [], "rows": [], "input_sha256": {}},
        {"kind": "n2d_bgm_generation_job", "version": 1, "episode": "第1集", "duration_sec": 10.0,
         "model": "Music 1", "channel": "manual", "output": "/tmp/bgm.wav", "cues": []},
        {"kind": "n2d_bgm_generation_receipt", "version": 1, "status": "pass", "episode": "第1集",
         "model": "Music 1", "channel": "manual", "output": "/tmp/bgm.wav", "output_sha256": "a",
         "contract_sha256": "b", "mode": "register_existing"},
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
    assert payload["scanned_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["skipped"][0]["classifier_reason"] == "support_json"
    assert payload["skipped"][0]["skip_reason"]["code"] == "support_json"


def test_scan_artifacts_skips_real_support_json_shapes(tmp_path: Path) -> None:
    source = tmp_path / "小说"
    source.mkdir()
    (source / "_源指纹.json").write_text('{"sha256":"abc"}', encoding="utf-8")
    (tmp_path / ".prework_cache_image_prompt.json").write_text('{"cached":true}', encoding="utf-8")
    voice = tmp_path / "合成" / "第1集" / "配音"
    voice.mkdir(parents=True)
    (voice / "时长清单.json").write_text('[{"clip":"Clip_01","duration":1.0}]', encoding="utf-8")
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "face_ep_means.json").write_text('{"第1集":[0.1,0.2]}', encoding="utf-8")
    views = tmp_path / "开发包" / "views"
    views.mkdir(parents=True)
    (views / "shot_view.json").write_text('{"rows":[]}', encoding="utf-8")
    config = tmp_path / "工具" / "config.json"
    config.parent.mkdir()
    config.write_text('{"theme":"dark"}', encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True)

    assert payload["status"] == "pass"
    assert payload["discovered_count"] == 6
    assert payload["scanned_count"] == 0
    assert payload["skipped_count"] == 6
    assert {row["classifier_reason"] for row in payload["skipped"]} == {
        "source_fingerprint",
        "prework_cache",
        "list_support",
        "embedding_support",
        "view_json",
        "config_json",
    }


def test_legacy_emotion_flow_is_explicitly_migrated_while_neighbor_list_skips(tmp_path: Path) -> None:
    voice = tmp_path / "合成" / "第1集" / "配音"
    voice.mkdir(parents=True)
    (voice / "emotion_flow.json").write_text('[{"emotion":"tense"}]', encoding="utf-8")
    (voice / "时长清单.json").write_text('[{"duration":1.0}]', encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True)

    assert payload["status"] == "warn"
    assert payload["scanned_count"] == 1
    assert payload["skipped_count"] == 1
    assert payload["scanned"][0]["classifier_reason"] == "boundary_registry_path"
    assert payload["scanned"][0]["classification"]["legacy_migration"]["from_version"] == 0
    assert payload["skipped"][0]["classifier_reason"] == "list_support"
    assert not any(item["severity"] == "block" for item in payload["issues"])
    assert any("legacy v0" in item["message"] for item in payload["issues"])


def test_malformed_legacy_emotion_flow_still_blocks(tmp_path: Path) -> None:
    voice = tmp_path / "合成" / "第1集" / "配音"
    voice.mkdir(parents=True)
    (voice / "emotion_flow.json").write_text('["not-an-emotion-row"]', encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")

    assert payload["status"] == "fail"
    assert any(item["severity"] == "block" and "expected object" in item["message"] for item in payload["issues"])


def test_manifest_does_not_promote_ordinary_json_artifact_entries(tmp_path: Path) -> None:
    script = tmp_path / "脚本" / "第1集"
    script.mkdir(parents=True)
    helper = script / "时长清单.json"
    helper.write_text('[{"duration":1.0}]', encoding="utf-8")
    (script / "manifest.json").write_text(json.dumps({
        "kind": "n2d_episode_manifest",
        "schema_version": 2,
        "episode": "第1集",
        "stage": "all",
        "artifacts": [{
            "stage": "voice",
            "path": "脚本/第1集/时长清单.json",
            "exists": True,
            "kind": "file",
        }],
    }, ensure_ascii=False), encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True)

    assert payload["status"] == "pass"
    assert payload["scanned_count"] == 1
    assert payload["skipped_count"] == 1
    assert payload["scanned"][0]["classifier_reason"] == "boundary_registry_path"
    assert payload["skipped"][0]["relative_path"] == "脚本/第1集/时长清单.json"


def test_self_declared_unknown_kind_still_fails_in_strict_scan(tmp_path: Path) -> None:
    path = tmp_path / "生产数据" / "future_output.json"
    path.parent.mkdir()
    path.write_text('{"kind":"n2d_future_output","version":1}', encoding="utf-8")

    relaxed = reg.scan_artifacts(str(tmp_path), strict_unknown=False)
    strict = reg.scan_artifacts(str(tmp_path), strict_unknown=True)

    assert relaxed["status"] == "pass"
    assert relaxed["scanned"][0]["classifier_reason"] == "declared_kind"
    assert strict["status"] == "fail"
    assert any(item["severity"] == "block" and "no schema registered" in item["message"] for item in strict["issues"])


def test_self_declared_unknown_kind_without_version_blocks_even_relaxed_scan(tmp_path: Path) -> None:
    path = tmp_path / "future_output.json"
    path.write_text('{"kind":"n2d_future_output"}', encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=False)

    assert payload["status"] == "fail"
    assert any(item["severity"] == "block" and "missing artifact version" in item["message"] for item in payload["issues"])


def test_release_scope_is_strict_only_for_boundary_and_manifest(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "batch_queue.json").write_text(
        json.dumps({"kind": "n2d_batch_queue", "version": 1, "root": str(tmp_path), "tasks": []}),
        encoding="utf-8",
    )
    (prod / "future_output.json").write_text('{"kind":"n2d_future_output","version":1}', encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")

    assert payload["status"] == "pass"
    assert payload["scanned_count"] == 1
    assert payload["skipped_count"] == 1
    assert payload["skipped"][0]["classifier_reason"] == "declared_kind"
    assert payload["skipped"][0]["skip_reason"]["code"] == "outside_release_boundary"


def test_unknown_manifest_kind_fails_in_strict_release_scan(tmp_path: Path) -> None:
    path = tmp_path / "合规" / "future_manifest.json"
    path.parent.mkdir()
    path.write_text('{"kind":"n2d_future_manifest","version":1}', encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")

    assert payload["status"] == "fail"
    assert payload["scanned"][0]["classifier_reason"] == "manifest_file"
    assert any(item["severity"] == "block" and "no schema registered" in item["message"] for item in payload["issues"])


def test_boundary_only_kind_requires_artifact_version(tmp_path: Path) -> None:
    path = tmp_path / "出图" / "共享" / "asset_registry.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"kind":"n2d_asset_reference_registry","assets":[]}', encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")

    assert payload["status"] == "fail"
    assert any("missing artifact version" in item["message"] for item in payload["issues"])


def test_release_contracts_are_in_global_boundary_registry_and_strict_schema(tmp_path: Path) -> None:
    assert reg.BOUNDARY_PRODUCT_KINDS["n2d_acceptance_receipt"]["path"] == "生产数据/acceptance_receipt_{ep}.json"
    assert reg.BOUNDARY_PRODUCT_KINDS["n2d_release_manifest"]["path"] == "合规/release_manifest_{ep}.json"
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "acceptance_receipt_第1集.json").write_text(json.dumps({
        "kind": "n2d_acceptance_receipt",
        "version": 1,
        "episode": "第1集",
        "decision": "approved",
        "reviewer": "qa",
        "accepted_at": "2026-08-20T00:00:00+00:00",
        "bindings": {},
        "evidence_digest": "abc",
        "receipt_id": "receipt-1",
    }, ensure_ascii=False), encoding="utf-8")
    compliance = tmp_path / "合规"
    compliance.mkdir()
    (compliance / "release_manifest_第1集.json").write_text(json.dumps({
        "kind": "n2d_release_manifest",
        "version": 1,
        "episode": "第1集",
        "root": str(tmp_path),
        "stage": "review",
        "asset": {},
        "compliance": {},
        "review": {},
        "provenance": {},
        "readiness": {},
    }, ensure_ascii=False), encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")

    assert payload["status"] == "pass"
    assert payload["scanned_count"] == 2
    assert {row["kind"] for row in payload["scanned"]} == {
        "n2d_acceptance_receipt",
        "n2d_release_manifest",
    }


def test_video_eval_manifest_known_schema_positive_and_negative() -> None:
    payload = {
        "kind": "n2d_video_eval_manifest",
        "version": 1,
        "root": "/tmp/work",
        "episode": "第1集",
        "generated_at": "2026-08-20T00:00:00+00:00",
        "media": ["出视频/第1集/视频/Clip_01.mp4"],
        "sidecar_targets": {"video_vlm": "生产数据/video_vlm_consistency_第1集.json"},
        "judge_schema_required": ["judge_model", "rubric_version"],
        "tasks": [{
            "clip": "Clip_01",
            "media": ["出视频/第1集/视频/Clip_01.mp4"],
            "frame_sampling": {"strategy": "start_mid_end"},
            "risk_kinds": ["subject"],
            "questions": [{"kind": "subject", "question": "identity stable?"}],
        }],
    }
    assert reg.validate_payload(payload) == []
    invalid = dict(payload)
    invalid.pop("tasks")
    assert any("tasks" in item["message"] for item in reg.validate_payload(invalid))


def test_character_asset_bundle_known_schema_positive_and_negative() -> None:
    payload = {
        "kind": "n2d_project_character_asset_bundle",
        "version": 1,
        "character_id": "CHAR_01",
        "name": "姜月初",
        "library_tier": "core_full",
        "directories": {"reference": "角色库/CHAR_01/reference"},
        "truth_sources": {"identity_registry": "出图/共享/identity_registry.json"},
        "updated_at": "2026-08-20T00:00:00+00:00",
    }
    assert reg.validate_payload(payload) == []
    invalid = dict(payload)
    invalid.pop("truth_sources")
    assert any("truth_sources" in item["message"] for item in reg.validate_payload(invalid))


def test_visual_reference_manifest_known_schema_positive_and_negative() -> None:
    payload = {
        "kind": "n2d_visual_reference_manifest",
        "version": 1,
        "status": "confirmed_for_analysis_only",
        "updated_at": "2026-08-20",
        "references": [{
            "reference_id": "USER_REF_01",
            "name": "气质参考",
            "path": "设定库/参考资料/ref.jpg",
            "sha256": "abc",
            "source": "user_provided_local_file",
            "use_policy": "identity_analysis_only",
            "rights_status": "pending_rights_review",
            "eligible_for_generation": False,
            "backend_upload_allowed": False,
        }],
        "rules": {"raw_references_are_generation_inputs": False},
    }
    assert reg.validate_payload(payload) == []
    invalid = dict(payload)
    invalid.pop("rules")
    assert any("rules" in item["message"] for item in reg.validate_payload(invalid))


def test_identity_voice_print_legacy_kind_is_explicit_boundary_alias(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "identity_voice_print_第1集.json").write_text(
        '{"kind":"n2d_identity_voice_print","version":1,"available":false}',
        encoding="utf-8",
    )

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")

    assert payload["status"] == "pass"
    row = payload["scanned"][0]
    assert row["classification"]["expected_kind"] == "n2d_identity_voice_print_report"
    assert row["classification"]["accepted_kind_aliases"] == ["n2d_identity_voice_print"]


def test_versionless_contract_inheritance_uses_exact_legacy_migration(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    path = prod / "contract_inheritance_第1集.json"
    payload = {
        "kind": "n2d_contract_inheritance",
        "episode": "第1集",
        "image_overview": "出图/第1集/prompt/00_总览.md",
        "video_overview": "出视频/第1集/prompt/00_总览.md",
        "fields": [],
        "summary": {"block": 0},
        "identity_handoff": {},
        "asset_handoff": {},
        "pixel_contract": {},
        "verdict": "pass",
        "generated_at": "2026-08-20T00:00:00Z",
        "inputs_fingerprint": {},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    migrated = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")
    assert migrated["status"] == "warn"
    assert migrated["scanned"][0]["classification"]["legacy_migration"]["rule"] == (
        "legacy_v0_n2d_contract_inheritance"
    )
    assert not any(item["severity"] == "block" for item in migrated["issues"])

    payload.pop("verdict")
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    invalid = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")
    assert invalid["status"] == "fail"
    assert any("verdict" in item["message"] for item in invalid["issues"] if item["severity"] == "block")


def test_versionless_voice_print_report_uses_exact_legacy_migration(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    path = prod / "identity_voice_print_第1集.json"
    payload = {
        "kind": "n2d_identity_voice_print_report",
        "episode": "第1集",
        "available": False,
        "mode": "no_speaker_backend",
        "precision": "insufficient_precision",
        "groups": {},
        "total_drift": 0,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    migrated = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")
    assert migrated["status"] == "warn"
    assert migrated["scanned"][0]["classification"]["legacy_migration"]["rule"] == (
        "legacy_v0_n2d_identity_voice_print_report"
    )
    assert not any(item["severity"] == "block" for item in migrated["issues"])

    payload.pop("episode")
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    invalid = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")
    assert invalid["status"] == "fail"
    assert any("episode" in item["message"] for item in invalid["issues"] if item["severity"] == "block")


def test_gate_findings_uses_registered_consistency_findings_payload_contract(tmp_path: Path) -> None:
    assert reg.BOUNDARY_PRODUCT_KINDS["n2d_gate_findings"]["accepted_kinds"] == [
        "n2d_consistency_findings"
    ]
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "gate_findings_video_preflight_第1集.json").write_text(json.dumps({
        "kind": "n2d_consistency_findings",
        "version": 1,
        "episode": "第1集",
        "findings": [],
    }, ensure_ascii=False), encoding="utf-8")

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")

    assert payload["status"] == "pass"
    assert payload["scanned_count"] == 1
    assert payload["scanned"][0]["classification"]["expected_kind"] == "n2d_gate_findings"
    assert payload["scanned"][0]["classification"]["accepted_kind_aliases"] == [
        "n2d_consistency_findings"
    ]


def test_review_ui_findings_name_is_not_misclassified_as_review_ui_boundary(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "review_ui_findings_第1集.json").write_text(
        '{"kind":"n2d_consistency_findings","version":1,"episode":"第1集","findings":[]}',
        encoding="utf-8",
    )

    payload = reg.scan_artifacts(str(tmp_path), strict_unknown=True, scope="release")

    assert payload["status"] == "pass"
    assert payload["scanned_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["skipped"][0]["classifier_reason"] == "declared_kind"
    assert payload["skipped"][0]["skip_reason"]["code"] == "outside_release_boundary"


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
