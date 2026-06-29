from __future__ import annotations

import json
import importlib.util
import shutil
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
LIB = REPO / "skills" / "n2d" / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_contract import stage_for_progress_column  # noqa: E402
from n2d_route import parse_progress, stage_of  # noqa: E402


FIXTURES = REPO / "tests" / "fixtures" / "n2d_golden_projects"
READINESS_SCRIPT = Path(__file__).with_name("production_readiness.py")
spec = importlib.util.spec_from_file_location("production_readiness_for_golden", READINESS_SCRIPT)
production_readiness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(production_readiness)


def _stage_key(route: dict) -> str:
    if route.get("label") == "补真实配音" or route.get("skill") == "n2d-voice":
        return "voice"
    spec = stage_for_progress_column(str(route.get("col") or ""))
    return str((spec or {}).get("key") or "")


def test_n2d_golden_project_routes_are_stable() -> None:
    cases = sorted(path for path in FIXTURES.iterdir() if path.is_dir())
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

    _write_json(root / "出视频" / episode / "prompt" / "video_model_routes.json", {"kind": "n2d_video_model_routes", "version": 1, "routes": []})
    _write_json(root / "出图" / "共享" / "identity_registry.json", {"kind": "n2d_identity_registry", "version": 1, "characters": []})
    _write_json(root / "出图" / "共享" / "asset_registry.json", {"kind": "n2d_asset_reference_registry", "version": 1, "assets": []})

    prod = root / "生产数据"
    prod.mkdir(exist_ok=True)
    _write_json(prod / f"budget_{episode}.json", {"kind": "n2d_budget_evidence", "version": 1, "status": "pass"})
    _write_json(prod / "image_backend_capabilities" / "fixture.json", {"kind": "n2d_backend_capability_evidence", "version": 1, "status": "fresh"})
    _write_json(prod / "image_qc" / episode / f"image_qc_{episode}.json", {"kind": "n2d_image_qc", "version": 1, "status": "pass"})
    _write_json(prod / f"contract_inheritance_{episode}.json", {"kind": "n2d_contract_inheritance", "version": 1, "status": "pass"})
    _write_json(prod / f"score_{episode}.json", {"kind": "n2d_episode_review_score", "version": 1, "status": "pass", "score": 91})
    _write_json(prod / f"consistency_ledger_{episode}.json", {"kind": "n2d_consistency_ledger", "version": 1, "status": "pass", "delivery_surface": {"status": "pass"}, "counts": {"block": 0, "high": 0}})
    _write_json(prod / f"review_ui_{episode}.json", {"kind": "n2d_review_ui", "version": 1, "status": "pass"})
    _write_json(prod / f"review_ui_findings_{episode}.json", {"kind": "n2d_consistency_findings", "version": 1, "episode": episode, "findings": []})
    _write_json(prod / f"review_signoff_{episode}.json", {"kind": "n2d_review_signoff", "version": 1, "status": "approved", "reviewer": "qa"})
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


def test_n2d_golden_project_release_gates_are_stable(tmp_path: Path) -> None:
    cases = sorted(path for path in FIXTURES.iterdir() if path.is_dir())
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
