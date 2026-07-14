from __future__ import annotations

import json
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[3]
LIB = REPO / "skills" / "n2d" / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_contract import stage_for_progress_column  # noqa: E402
from n2d_route import parse_progress, stage_of  # noqa: E402
from skill_snapshot import artifact_fingerprint  # noqa: E402


FIXTURES = REPO / "tests" / "fixtures" / "n2d_golden_projects"
READINESS_SCRIPT = Path(__file__).with_name("production_readiness.py")
spec = importlib.util.spec_from_file_location("production_readiness_for_golden", READINESS_SCRIPT)
production_readiness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(production_readiness)


def _golden_cases() -> list[Path]:
    """The fixture pack is optional in distributable/trimmed checkouts."""
    if not FIXTURES.is_dir():
        pytest.skip(f"optional n2d golden fixture pack is not installed: {FIXTURES}")
    return sorted(path for path in FIXTURES.iterdir() if path.is_dir())


@pytest.fixture(autouse=True)
def _stable_ffprobe(monkeypatch):
    monkeypatch.setattr(production_readiness.script_supervisor_log, "ffprobe_duration", lambda path: 1.0 if Path(path).is_file() else None)
    # Golden release fixtures exercise project evidence, not the wall-clock age of
    # repository-wide backend candidate snapshots. Keep that orthogonal audit in
    # freshness.py's own tests so this suite stays deterministic over time.
    monkeypatch.setattr(production_readiness, "run_freshness_checks", lambda root: [])


def _stage_key(route: dict) -> str:
    if route.get("label") == "补真实配音" or route.get("skill") == "n2d-voice":
        return "voice"
    spec = stage_for_progress_column(str(route.get("col") or ""))
    return str((spec or {}).get("key") or "")


def test_n2d_golden_project_routes_are_stable() -> None:
    cases = _golden_cases()
    assert len(cases) == 6
    for root in cases:
        expected = json.loads((root / "生产数据" / "golden_expected.json").read_text(encoding="utf-8"))
        header, rows = parse_progress(str(root))
        assert rows, root
        route = stage_of(str(root), rows[0], header)
        assert _stage_key(route) == expected["expected_stage_key"], (root.name, route, expected)
        assert route.get("skill") == expected["expected_owner"], (root.name, route, expected)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _generation_event(episode: str, stage: str, asset: str) -> dict:
    return {
        "kind": "n2d_production_event",
        "version": 1,
        "ts": "2026-06-26T00:00:00+00:00",
        "episode": episode,
        "stage": stage,
        "event": "generation",
        "source": "golden_fixture",
        "trace": {"trace_id": f"golden-{stage}", "span_id": "span", "idempotency_key": asset},
        "generation": {
            "asset": asset,
            "status": "pass",
            "provider": "fixture",
            "model": f"fixture-{stage}",
            "channel": "fixture-channel",
            "route_hash": "route-sha",
            "capability_evidence_id": "fixture-capability",
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


def _enrich_release_evidence(root: Path, episode: str) -> None:
    script = root / "脚本" / episode
    script.mkdir(parents=True, exist_ok=True)
    _write_json(script / "storyboard.json", {"kind": "storyboard", "clips": []})
    _write_json(root / "设定库" / "source_comprehension.json", {"kind": "n2d_source_comprehension", "status": "confirmed"})
    (root / "设定库" / "global_style.md").write_text("status: confirmed\n", encoding="utf-8")
    (script / "voiceover.txt").write_text("对白\n", encoding="utf-8")
    (script / "bgm.txt").write_text("fixture music bed\n", encoding="utf-8")
    _write_json(script / "镜头时长.json", {})
    _write_json(script / "director_blocking_pack.json", {"kind": "n2d_director_blocking_pack", "status": "confirmed"})
    _write_json(script / "preventive_contracts.json", {"kind": "n2d_preventive_contracts", "status": "confirmed"})
    (script / "字幕_中文.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n对白\n", encoding="utf-8")

    compliance = production_readiness.release_manifest.compliance
    data = compliance.default_manifest(root, episode)
    data["distribution_intent"] = "internal_only"
    path = compliance.manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    image = root / "出图" / episode / "图片" / "Clip_01.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"png")
    video = root / "出视频" / episode / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"clip")
    master = root / "合成" / episode / f"成片_{episode}_zh.mp4"
    master.parent.mkdir(parents=True, exist_ok=True)
    master.write_bytes(b"master")
    _write_json(root / "合成" / episode / "_work" / "timeline.json", {"kind": "n2d_rough_cut_timeline", "version": 1, "segments": []})
    (root / "合成" / episode / "rough_cut_preview.html").write_text("<html>rough</html>", encoding="utf-8")

    _write_json(root / "出视频" / episode / "prompt" / "video_model_routes.json", {"kind": "n2d_video_model_routes", "version": 1, "routes": []})
    _write_json(root / "出图" / "共享" / "identity_registry.json", {"kind": "n2d_identity_registry", "version": 1, "characters": []})
    _write_json(root / "出图" / "共享" / "asset_registry.json", {"kind": "n2d_asset_reference_registry", "version": 1, "assets": []})

    prod = root / "生产数据"
    prod.mkdir(exist_ok=True)
    _write_json(prod / f"script_quality_contract_{episode}.json", {"kind": "n2d_script_quality_contract", "status": "pass"})
    _write_json(prod / f"story_economy_audit_{episode}.json", {"kind": "n2d_story_economy_audit", "version": 1, "ok": True, "status": "pass", "summary": {"blocks": 0}})
    for name, kind, extra in (
        ("production_breakdown.json", "n2d_production_breakdown", {"scene_breakdowns": []}),
        ("continuity_breakdown.json", "n2d_continuity_breakdown", {"rows": []}),
        ("continuity_chain.json", "n2d_continuity_chain", {"clips": [], "seams": [], "summary": {"block": 0}}),
        ("continuity_bible.json", "n2d_continuity_bible", {"clips": []}),
        ("ai_shooting_schedule.json", "n2d_ai_shooting_schedule", {"tasks": []}),
    ):
        _write_json(script / name, {"kind": kind, "version": 1, "episode": episode, "status": "confirmed", **extra})
    (script / "ai_call_sheet.md").write_text("status: confirmed\n# fixture call sheet\n", encoding="utf-8")
    handoff_inputs = [
        "设定库/source_comprehension.json",
        f"脚本/{episode}/voiceover.txt",
        f"脚本/{episode}/storyboard.json",
        f"脚本/{episode}/镜头时长.json",
        f"脚本/{episode}/director_blocking_pack.json",
        f"脚本/{episode}/preventive_contracts.json",
        f"生产数据/script_quality_contract_{episode}.json",
    ]
    _write_json(script / "production_handoff_pack.json", {
        "kind": "n2d_production_handoff_pack",
        "version": 1,
        "episode": episode,
        "status": "confirmed",
        "inputs_fingerprint": artifact_fingerprint(str(root), handoff_inputs),
    })
    _write_json(prod / f"ai_shooting_schedule_batch_seed_{episode}.json", {
        "kind": "n2d_ai_shooting_schedule_batch_seed",
        "version": 1,
        "status": "ready",
        "batch_tasks": [{"task_id": "fixture", "stage": "image"}],
    })
    (prod / f"ai_shooting_schedule_batch_seed_{episode}.md").write_text("# fixture batch seed\n", encoding="utf-8")
    _write_json(prod / f"budget_{episode}.json", {"kind": "n2d_budget_evidence", "version": 1, "status": "pass"})
    _write_json(prod / f"final_timeline_probe_{episode}.json", {"kind": "n2d_final_timeline_probe", "version": 1, "status": "pass", "segments": []})
    _write_json(prod / f"video_qc_{episode}.json", {"kind": "n2d_video_qc", "version": 1, "status": "pass"})
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
    _write_json(prod / "image_backend_capabilities" / "fixture.json", {"kind": "n2d_backend_capability_evidence", "version": 1, "status": "fresh"})
    _write_json(prod / "image_qc" / episode / f"image_qc_{episode}.json", {"kind": "n2d_image_qc", "version": 1, "status": "pass"})
    _write_json(prod / f"contract_inheritance_{episode}.json", {"kind": "n2d_contract_inheritance", "version": 1, "status": "pass"})
    _write_json(prod / f"score_{episode}.json", {"kind": "n2d_episode_review_score", "version": 1, "status": "pass", "score": 91})
    _write_json(prod / f"consistency_ledger_{episode}.json", {"kind": "n2d_consistency_ledger", "version": 1, "status": "pass", "delivery_surface": {"status": "pass"}, "counts": {"block": 0, "high": 0}})
    _write_json(prod / f"review_ui_{episode}.json", {"kind": "n2d_review_ui", "version": 1, "status": "pass"})
    _write_json(prod / f"review_ui_findings_{episode}.json", {"kind": "n2d_consistency_findings", "version": 1, "episode": episode, "findings": []})
    _write_json(prod / f"review_signoff_{episode}.json", {"kind": "n2d_review_signoff", "version": 1, "status": "approved", "reviewer": "qa"})
    _write_json(prod / f"identity_voice_print_{episode}.json", {"kind": "n2d_identity_voice_print", "version": 1, "available": False, "mode": "no_audio"})
    _write_json(prod / f"release_verdict_{episode}.json", {"kind": "n2d_release_verdict", "version": 1, "status": "internal-only"})
    _write_json(prod / "identity_adapter_matrix.json", {"kind": "n2d_identity_adapter_matrix", "version": 1, "forms": []})
    events = [
        _generation_event(episode, "image", f"出图/{episode}/图片/Clip_01.png"),
        _generation_event(episode, "video", f"出视频/{episode}/视频/Clip_01.mp4"),
        {
            "kind": "n2d_production_event",
            "version": 1,
            "ts": "2026-06-26T00:00:02+00:00",
            "episode": episode,
            "stage": "release",
            "event": "release",
            "source": "golden_fixture",
            "trace": {"trace_id": "golden-release", "span_id": "span", "idempotency_key": "release"},
        },
    ]
    (prod / "production_events.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in events),
        encoding="utf-8",
    )
    production_readiness.production_locks.scaffold(root, episode, confirmed=True, reviewer="golden", force=True)
    decision = {
        "kind": "n2d_creative_decision",
        "version": 1,
        "decision_type": "release_lock",
        "owner": "producer",
        "scope": "golden_project_release_readiness",
        "accepted_choice": "使用当前 enrich 后证据作为 release readiness 黄金样例",
        "reason": "golden fixture 需要稳定覆盖生产治理硬闸。",
        "affected_artifacts": [f"生产数据/production_locks_{episode}.json"],
        "affected_stages": ["review"],
        "follow_up_batch_scope": "none",
    }
    (prod / "creative_decisions.jsonl").write_text(
        json.dumps(decision, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_n2d_golden_project_release_gates_are_stable(tmp_path: Path) -> None:
    cases = _golden_cases()
    assert len(cases) == 6
    for src in cases:
        root = tmp_path / src.name
        shutil.copytree(src, root)
        expected = json.loads((root / "生产数据" / "golden_expected.json").read_text(encoding="utf-8"))
        _enrich_release_evidence(root, "第1集")

        payload = production_readiness.build_readiness(root, "第1集", write=True, skip_next_action=True)

        assert payload["status"] == expected["expected_release_readiness_after_enrichment"], (src.name, payload["checks"])
        assert production_readiness.artifact_lineage.check_lineage(root, "第1集")["status"] == "pass"
        assert production_readiness.release_manifest.check_manifest(root, "第1集")["status"] == "pass"
