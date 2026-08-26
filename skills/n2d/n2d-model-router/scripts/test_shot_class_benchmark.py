from __future__ import annotations

import hashlib
import json
from pathlib import Path

import shot_class_benchmark as bench


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_root(tmp_path: Path) -> Path:
    story = tmp_path / "脚本" / "第1集"
    story.mkdir(parents=True)
    (story / "storyboard.json").write_text(json.dumps({"clips": [
        {"clip_id": "Clip_01", "shot_type": "CU", "characters": ["CHAR_A"], "dialogue": "你来了"},
        {"clip_id": "Clip_02", "characters": ["CHAR_A", "CHAR_B"], "action": "近身打斗交手碰撞", "risk": "critical"},
    ]}, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_plan_is_stratified_and_hash_bound(tmp_path):
    plan = bench.build_plan(_fixture_root(tmp_path), "1")
    classes = {row["shot_class"] for row in plan["selections"]}
    assert {"dialogue_closeup", "action_contact"} <= classes
    assert len(plan["plan_digest"]) == 64
    assert bench.digest_value({k: v for k, v in plan.items() if k != "plan_digest"}) == plan["plan_digest"]


def _result(root: Path, planned, suffix: str, accepted: bool):
    artifact = root / f"artifact-{suffix}.mp4"
    qc = root / f"qc-{suffix}.json"
    inspect = root / f"inspect-{suffix}.json"
    artifact.write_bytes(b"decoded-video-" + suffix.encode())
    artifact_sha = _sha(artifact)
    qc.write_text(json.dumps({
        "kind": "n2d_video_qc_receipt", "artifact_sha256": artifact_sha,
        "verdict": "pass" if accepted else "fail",
    }), encoding="utf-8")
    inspect.write_text(json.dumps({
        "kind": "n2d_clip_actual_watch", "artifact_sha256": artifact_sha,
        "verdict": "pass", "reviewer_kind": "executor_visual_audio",
        "final_user_acceptance": False,
    }), encoding="utf-8")
    return {
        **{key: planned[key] for key in ("trial_id", "shot_class", "clip_id", "backend", "clip_contract_sha256")},
        "status": "completed",
        "attempt_kind": "initial",
        "artifact_path": str(artifact), "artifact_sha256": artifact_sha,
        "qc_receipt_path": str(qc), "qc_receipt_sha256": _sha(qc),
        "inspection_receipt_path": str(inspect), "inspection_receipt_sha256": _sha(inspect),
        "qc_verdict": "pass" if accepted else "fail",
        "cost": 1.0, "latency_seconds": 12.0, "accepted_seconds": 5.0 if accepted else 0.0,
    }


def test_summary_refuses_thin_evidence_then_recommends_with_real_receipts(tmp_path):
    root = _fixture_root(tmp_path)
    plan = bench.build_plan(root, "1")
    action = [row for row in plan["trials"] if row["shot_class"] == "action_contact"]
    thin = {"kind": bench.RESULTS_KIND, "plan_digest": plan["plan_digest"], "trials": [
        _result(root, action[0], "thin", True),
    ]}
    assert bench.summarize(root, plan, thin, min_samples=2)["status"] == "insufficient_evidence"

    by_backend = {}
    for row in action:
        by_backend.setdefault(row["backend"], []).append(row)
    chosen = list(by_backend.items())[:2]
    trials = []
    for backend_index, (_, planned_rows) in enumerate(chosen):
        for sample, planned in enumerate(planned_rows[:2]):
            trials.append(_result(root, planned, f"{backend_index}-{sample}", accepted=backend_index == 0 or sample == 0))
    payload = {"kind": bench.RESULTS_KIND, "plan_digest": plan["plan_digest"], "trials": trials}
    summary = bench.summarize(root, plan, payload, min_samples=2)
    assert summary["status"] == "ready"
    assert summary["recommendations"]["action_contact"]["primary_backend"] == chosen[0][0]


def test_summary_rejects_hash_drift(tmp_path):
    root = _fixture_root(tmp_path)
    plan = bench.build_plan(root, "1")
    trial = plan["trials"][0]
    result = _result(root, trial, "drift", True)
    Path(result["artifact_path"]).write_bytes(b"changed")
    summary = bench.summarize(root, plan, {
        "kind": bench.RESULTS_KIND,
        "plan_digest": plan["plan_digest"],
        "trials": [result],
    }, min_samples=1)
    assert summary["status"] == "insufficient_evidence"
    assert any("sha256 mismatch" in issue for issue in summary["invalid_results"])
