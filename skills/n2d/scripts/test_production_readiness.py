from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("production_readiness.py")
spec = importlib.util.spec_from_file_location("production_readiness", SCRIPT)
production_readiness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(production_readiness)


@pytest.fixture(autouse=True)
def _stable_ffprobe(monkeypatch):
    monkeypatch.setattr(production_readiness.script_supervisor_log, "ffprobe_duration", lambda path: 1.0 if Path(path).is_file() else None)


def _write_test_mp4(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                "color=c=black:s=16x16:d=0.2", "-an", "-c:v", "mpeg4", str(path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except FileNotFoundError:
        pytest.skip("ffmpeg unavailable")
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")


def _release_ready_project(root: Path, episode: str) -> None:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n- 一致性严格度: production\n", encoding="utf-8")
    (root / "_进度.md").write_text("| 集 | 成片 | 验收 |\n|---|---|---|\n| 第1集 | ✅ | ✅ |\n", encoding="utf-8")
    script_dir = root / "脚本" / episode
    script_dir.mkdir(parents=True)
    (script_dir / "storyboard.json").write_text('{"kind":"storyboard","clips":[]}', encoding="utf-8")
    (script_dir / "字幕_中文.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n对白\n", encoding="utf-8")
    (script_dir / "production_handoff_pack.json").write_text('{"kind":"n2d_production_handoff_pack","version":1,"status":"confirmed"}', encoding="utf-8")
    (script_dir / "continuity_chain.json").write_text('{"kind":"n2d_continuity_chain","version":1,"status":"confirmed","summary":{"block":0}}', encoding="utf-8")
    (script_dir / "continuity_bible.json").write_text('{"kind":"n2d_continuity_bible","version":1,"status":"confirmed"}', encoding="utf-8")
    (script_dir / "ai_shooting_schedule.json").write_text('{"kind":"n2d_ai_shooting_schedule","version":1,"status":"confirmed"}', encoding="utf-8")
    (script_dir / "ai_call_sheet.md").write_text("status: confirmed\n# call sheet\n", encoding="utf-8")
    style = root / "设定库" / "global_style.md"
    style.parent.mkdir(parents=True, exist_ok=True)
    style.write_text("status: confirmed\n", encoding="utf-8")

    compliance = production_readiness.release_manifest.compliance
    data = compliance.default_manifest(root, episode)
    data["distribution_intent"] = "internal_only"
    path = compliance.manifest_path(root)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    asset = root / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)

    prod = root / "生产数据"
    prod.mkdir()
    image = root / "出图" / episode / "图片" / "Clip_01.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png")
    video = root / "出视频" / episode / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"clip")
    timeline = root / "合成" / episode / "_work" / "timeline.json"
    timeline.parent.mkdir(parents=True)
    timeline.write_text('{"kind":"n2d_rough_cut_timeline","version":1,"segments":[]}', encoding="utf-8")
    (root / "合成" / episode / "rough_cut_preview.html").write_text("<html>rough</html>", encoding="utf-8")
    route_dir = root / "出视频" / episode / "prompt"
    route_dir.mkdir(parents=True)
    (route_dir / "video_model_routes.json").write_text('{"kind":"n2d_video_model_routes","version":1,"routes":[]}', encoding="utf-8")
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text('{"kind":"n2d_identity_registry","version":1,"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text('{"kind":"n2d_asset_reference_registry","version":1,"assets":[]}', encoding="utf-8")
    (prod / f"budget_{episode}.json").write_text('{"kind":"n2d_budget_evidence","version":1,"status":"pass"}', encoding="utf-8")
    (prod / f"final_timeline_probe_{episode}.json").write_text('{"kind":"n2d_final_timeline_probe","version":1,"status":"pass","segments":[]}', encoding="utf-8")
    (prod / f"video_qc_{episode}.json").write_text('{"kind":"n2d_video_qc","version":1,"status":"pass"}', encoding="utf-8")
    (prod / f"story_economy_audit_{episode}.json").write_text('{"kind":"n2d_story_economy_audit","version":1,"status":"pass","summary":{"blocks":0}}', encoding="utf-8")
    (prod / f"script_supervisor_log_{episode}.jsonl").write_text(
        json.dumps({
            "kind": "n2d_script_supervisor_log",
            "version": 1,
            "episode": episode,
            "clip_id": "Clip_01",
            "take_id": "Clip_01",
            "asset": f"出视频/{episode}/视频/Clip_01.mp4",
            "accepted_take": True,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (prod / "identity_adapter_matrix.json").write_text('{"kind":"n2d_identity_adapter_matrix","version":1,"forms":[]}', encoding="utf-8")
    cap = prod / "image_backend_capabilities"
    cap.mkdir()
    (cap / "codex.json").write_text('{"kind":"n2d_backend_capability_evidence","version":1,"status":"fresh"}', encoding="utf-8")
    qc = prod / "image_qc" / episode
    qc.mkdir(parents=True)
    (qc / f"image_qc_{episode}.json").write_text('{"kind":"n2d_image_qc","version":1,"status":"pass"}', encoding="utf-8")
    (prod / f"contract_inheritance_{episode}.json").write_text('{"kind":"n2d_contract_inheritance","version":1,"status":"pass"}', encoding="utf-8")
    (prod / f"consistency_ledger_{episode}.json").write_text('{"kind":"n2d_consistency_ledger","version":1,"status":"pass","delivery_surface":{"status":"pass"},"counts":{"block":0,"high":0}}', encoding="utf-8")
    (prod / "identity_drift_report.json").write_text(json.dumps({
        "kind": "n2d_identity_drift_report",
        "version": 1,
        "characters": {
            "CHAR_01": {"episodes": {
                "第1集": {"block": 0, "worst_score": 0.82},
                "第2集": {"block": 1, "worst_score": 0.31},
            }}
        }
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "review_calibration.json").write_text(json.dumps({
        "kind": "n2d_review_calibration",
        "version": 1,
        "status": "pass",
        "case_count": 2,
        "vote_count": 4,
        "reviewers": [{"reviewer": "qa", "total": 2, "accuracy": 1.0}],
        "dimensions": [],
        "disagreements": [],
        "unknown_cases": [],
    }, ensure_ascii=False), encoding="utf-8")
    (prod / f"review_ui_{episode}.json").write_text('{"kind":"n2d_review_ui","version":1,"status":"pass"}', encoding="utf-8")
    (prod / f"review_ui_findings_{episode}.json").write_text(json.dumps({"kind": "n2d_consistency_findings", "version": 1, "episode": episode, "findings": []}, ensure_ascii=False), encoding="utf-8")
    def event(stage: str, asset_rel: str) -> dict:
        return {
            "kind": "n2d_production_event",
            "version": 1,
            "ts": "2026-06-26T00:00:00+00:00",
            "episode": episode,
            "stage": stage,
            "event": "generation",
            "source": "test",
            "trace": {"trace_id": f"t-{stage}", "span_id": f"s-{stage}", "idempotency_key": asset_rel},
            "generation": {
                "asset": asset_rel,
                "status": "pass",
                "provider": "test-provider",
                "model": f"test-{stage}",
                "channel": "test-channel",
                "route_hash": "route-sha",
                "capability_evidence_id": "capability-id",
                "recipe_hash": f"recipe-{stage}",
                "prompt_sha256": f"prompt-{stage}",
                "reference_bundle_sha256": f"reference-{stage}",
                "backend_version": "2026-06-26",
                "quality_tier": "final",
                "actual_image_inputs": ["出图/共享/identity_registry.json"],
                "seed_effective": False,
                "seed_support": "unsupported",
            },
        }

    release_event = {
        "kind": "n2d_production_event",
        "version": 1,
        "ts": "2026-06-26T00:00:00+00:00",
        "episode": episode,
        "stage": "release",
        "event": "release",
        "source": "test",
        "trace": {"trace_id": "t1", "span_id": "s1", "idempotency_key": "i1"},
    }
    events = [
        event("image", f"出图/{episode}/图片/Clip_01.png"),
        event("video", f"出视频/{episode}/视频/Clip_01.mp4"),
        release_event,
    ]
    (prod / "production_events.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in events), encoding="utf-8")
    (prod / f"review_signoff_{episode}.json").write_text('{"kind":"n2d_review_signoff","version":1,"status":"approved","reviewer":"qa"}', encoding="utf-8")
    (prod / f"identity_voice_print_{episode}.json").write_text('{"kind":"n2d_identity_voice_print","version":1,"available":false,"mode":"no_audio"}', encoding="utf-8")
    (prod / f"score_{episode}.json").write_text('{"kind":"n2d_episode_review_score","version":1,"status":"pass","score":91}', encoding="utf-8")
    production_readiness.production_locks.scaffold(root, episode, confirmed=True, reviewer="qa", force=True)
    decision = {
        "kind": "n2d_creative_decision",
        "version": 1,
        "decision_type": "release_lock",
        "owner": "producer",
        "scope": "production_readiness",
        "accepted_choice": "按当前锁版账进入 release readiness",
        "reason": "测试夹具已补齐交付证据，允许统一交付门聚合。",
        "affected_artifacts": [f"生产数据/production_locks_{episode}.json"],
        "affected_stages": ["review"],
        "follow_up_batch_scope": "none",
    }
    (prod / "creative_decisions.jsonl").write_text(json.dumps(decision, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    # Producer-owned release evidence exists before the immutable verdict is
    # issued.  A later readiness audit may recompute it, but must not introduce
    # the first version after human acceptance.
    production_readiness.run_event_ledger(root, write=True, strict_trace=True)
    production_readiness.run_generation_recipe(root, episode, write=True)
    production_readiness.run_gate_policy_coverage(root, episode, write=True)
    production_readiness.run_genre_packs(root, episode, write=True)
    production_readiness.run_artifact_validation(root, write=True)

    # Completion is proved by one canonical, hash-bound verdict/acceptance
    # pair.  The legacy review_signoff above remains migration input only.
    acceptance = production_readiness.release_manifest.acceptance_contract
    components = [
        {"name": name, "status": "pass", "message": f"{name} passed"}
        for name in sorted(acceptance.REQUIRED_VERDICT_COMPONENTS)
    ]
    master = acceptance.resolve_final_master(root, episode)
    assert master is not None
    master_rel = master.relative_to(root).as_posix()
    final_master = next(row for row in components if row["name"] == "final_master")
    final_master.update({
        "path": master_rel,
        "details": {
            "selected": master_rel,
            "selected_sha256": acceptance.sha256_file(master),
            "duration_sec": acceptance.probe_master_duration(master),
        },
    })
    verdict = {
        "kind": "n2d_release_verdict",
        "version": 2,
        "episode": episode,
        "profile": "internal",
        "generated_at": "2026-06-26T00:00:00+00:00",
        "status": "internal-only",
        "summary": {"block": 0, "warn": 0, "pass": len(components)},
        "components": components,
        "blocking_reasons": [],
        "warnings": [],
        "evidence_bindings": acceptance.current_evidence_bindings(root, episode),
        "content_fingerprint": acceptance.release_content_fingerprint(root, episode, "internal"),
    }
    (prod / f"release_verdict_{episode}.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = acceptance.build_receipt(
        root,
        episode,
        reviewer="qa",
        decision="approved",
        accepted_at="2026-06-26T00:00:00+00:00",
    )
    acceptance.write_receipt(root, episode, receipt)


def test_production_readiness_writes_unified_gate(monkeypatch, tmp_path: Path) -> None:
    episode = "第1集"
    _release_ready_project(tmp_path, episode)
    monkeypatch.setattr(production_readiness.freshness, "check_all", lambda: [])

    payload = production_readiness.build_readiness(tmp_path, episode, write=True, skip_next_action=True)

    assert payload["status"] == "pass"
    names = {item["name"] for item in payload["checks"]}
    assert {
        "artifact_validation",
        "event_ledger_audit",
        "generation_recipe_manifest",
        "gate_policy_coverage",
        "artifact_lineage",
        "release_manifest",
        "candidate_freshness",
        "golden_set_calibration",
        "reviewer_calibration",
        "genre_packs",
    } <= names
    assert (tmp_path / "生产数据" / f"production_readiness_{episode}.json").is_file()
    assert (tmp_path / "生产数据" / f"generation_recipe_manifest_{episode}.json").is_file()
    assert (tmp_path / "生产数据" / f"gate_policy_coverage_{episode}.json").is_file()
    assert (tmp_path / "合规" / f"release_manifest_{episode}.json").is_file()


def test_readiness_artifact_validation_skips_support_json_but_reports_counts(tmp_path: Path) -> None:
    source = tmp_path / "小说"
    source.mkdir()
    (source / "_源指纹.json").write_text('{"sha256":"abc"}', encoding="utf-8")
    (tmp_path / ".prework_cache_image_prompt.json").write_text('{"cached":true}', encoding="utf-8")

    row = production_readiness.run_artifact_validation(tmp_path, write=False)

    assert row["status"] == "pass"
    assert row["scanned_count"] == 0
    assert row["skipped_count"] == 2
    assert "scanned=0 skipped=2 block=0 warn=0" == row["message"]


def test_readiness_artifact_validation_strictly_rejects_unknown_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "合规" / "future_manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"kind":"n2d_future_manifest","version":1}', encoding="utf-8")

    row = production_readiness.run_artifact_validation(tmp_path, write=False)

    assert row["status"] == "fail"
    assert row["scanned_count"] == 1
    assert row["skipped_count"] == 0
    assert "block=1" in row["message"]


def test_reviewer_calibration_missing_fails_for_scale_up(tmp_path: Path) -> None:
    episode = "第1集"
    _release_ready_project(tmp_path, episode)
    (tmp_path / "生产数据" / "review_calibration.json").unlink()

    payload = production_readiness.build_readiness(
        tmp_path,
        episode,
        write=False,
        skip_next_action=True,
        scale_up=True,
    )

    row = next(item for item in payload["checks"] if item["name"] == "reviewer_calibration")
    assert payload["scale_up"] is True
    assert row["status"] == "fail"
    assert payload["status"] == "fail"


def _write_judge_report(root: Path, episode: str, judge_model: str) -> None:
    pdir = root / "生产数据"
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / f"video_vlm_consistency_{episode}.json").write_text(
        json.dumps({"judge_model": judge_model, "rows": []}, ensure_ascii=False), encoding="utf-8"
    )


def _write_generation_events(root: Path, episode: str, model: str) -> None:
    pdir = root / "生产数据"
    pdir.mkdir(parents=True, exist_ok=True)
    rows = [
        {"event": "generation", "stage": "image", "episode": episode, "asset": "出图/x.png",
         "provider": "codex", "model": model},
    ]
    (pdir / "production_events.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )


def test_judge_independence_info_when_no_judge_report(tmp_path: Path) -> None:
    row = production_readiness.judge_generator_independence(tmp_path, "第1集")
    assert row["status"] == "info"


def test_judge_independence_flags_same_family(tmp_path: Path) -> None:
    episode = "第1集"
    _write_judge_report(tmp_path, episode, "gpt-4o")
    _write_generation_events(tmp_path, episode, "GPT Image 2")
    warn = production_readiness.judge_generator_independence(tmp_path, episode, scale_up=False)
    assert warn["status"] == "warn"
    fail = production_readiness.judge_generator_independence(tmp_path, episode, scale_up=True)
    assert fail["status"] == "fail"


def test_judge_independence_pass_for_distinct_families(tmp_path: Path) -> None:
    episode = "第1集"
    _write_judge_report(tmp_path, episode, "gemini-2.5-pro")
    _write_generation_events(tmp_path, episode, "GPT Image 2")
    row = production_readiness.judge_generator_independence(tmp_path, episode, scale_up=True)
    assert row["status"] == "pass"


def test_model_family_classifier() -> None:
    assert production_readiness._model_family("GPT Image 2") == "openai"
    assert production_readiness._model_family("gemini-2.5-pro") == "google"
    assert production_readiness._model_family("Kling 3.0") == "kuaishou"
    assert production_readiness._model_family("Seedance 2.0") == "bytedance"
    assert production_readiness._model_family("某不知名模型") == ""
