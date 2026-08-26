from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

import acceptance_contract
from test_completion_evidence import write_test_master, write_valid_completion_receipts


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_test_mp4(path: Path, *, color: str = "black") -> None:
    write_test_master(path, color=color)


def _refresh_operational_evidence(root: Path) -> None:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    ledger = prod / "production_events.jsonl"
    ledger.touch(exist_ok=True)
    acceptance_contract._event_ledger_module().audit(
        str(root), write=True, strict_trace=True
    )
    report = acceptance_contract.n2d_schema_registry.scan_artifacts(
        str(root), strict_unknown=True,
        scope=acceptance_contract.n2d_schema_registry.SCAN_SCOPE_RELEASE,
        completion_inputs_only=True,
    )
    _write_json(prod / "artifact_validation.json", report)


def _canonical_evidence(root: Path, episode: str = "第1集") -> Path:
    master = root / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(master)
    prod = root / "生产数据"
    master_rel = master.relative_to(root).as_posix()
    evidence = write_valid_completion_receipts(
        root, episode, master, acceptance_contract, transaction_id="acceptance-contract-test"
    )
    master_sha = evidence["master_sha256"]
    duration = evidence["duration_sec"]
    _write_json(prod / f"score_{episode}.json", {"kind": "n2d_episode_review_score", "version": 1, "status": "pass", "score": 91})
    _write_json(prod / f"consistency_ledger_{episode}.json", {"kind": "n2d_consistency_ledger", "version": 1, "status": "pass"})
    _write_json(prod / f"review_ui_{episode}.json", {"kind": "n2d_review_ui", "version": 1, "status": "pass"})
    _write_json(prod / f"review_ui_findings_{episode}.json", {"kind": "n2d_consistency_findings", "version": 1, "episode": episode, "findings": []})
    _refresh_operational_evidence(root)
    bindings = acceptance_contract.current_evidence_bindings(root, episode)
    components = [
        {"name": name, "status": "pass", "message": f"{name} passed"}
        for name in sorted(acceptance_contract.REQUIRED_VERDICT_COMPONENTS)
    ]
    final_master = next(row for row in components if row["name"] == "final_master")
    final_master["path"] = master_rel
    final_master["details"] = {
        "selected": master_rel,
        "selected_sha256": master_sha,
        "duration_sec": duration,
    }
    _write_json(
        prod / f"release_verdict_{episode}.json",
        {
            "kind": "n2d_release_verdict",
            "version": 2,
            "episode": episode,
            "profile": "internal",
            "generated_at": "2026-08-20T00:00:00+00:00",
            "status": "internal-only",
            "summary": {"block": 0, "warn": 0, "pass": len(components)},
            "components": components,
            "blocking_reasons": [],
            "warnings": [],
            "evidence_bindings": bindings,
            "content_fingerprint": acceptance_contract.release_content_fingerprint(root, episode, "internal"),
        },
    )
    return master


def _approve(root: Path, episode: str = "第1集") -> dict:
    payload = acceptance_contract.build_receipt(
        root,
        episode,
        reviewer="human-qc",
        decision="approved",
        accepted_at="2026-08-20T00:00:00+00:00",
    )
    acceptance_contract.write_receipt(root, episode, payload)
    return payload


def test_canonical_acceptance_receipt_binds_all_release_evidence(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    payload = _approve(tmp_path)

    assert set(acceptance_contract.REQUIRED_EVIDENCE_ROLES) <= set(payload["bindings"])
    assert payload["bindings"]["release_verdict"]["sha256"]
    assert payload["bindings"]["master_asset"]["sha256"]
    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "pass"


def test_rough_cut_cannot_diverge_machine_verdict_from_accepted_master(tmp_path: Path) -> None:
    rough = tmp_path / "合成" / "第1集" / "rough_cut.mp4"
    rough.parent.mkdir(parents=True, exist_ok=True)
    rough.write_bytes(b"newer-but-not-a-master")
    future = time.time() + 10
    os.utime(rough, (future, future))
    master = _canonical_evidence(tmp_path)

    assert acceptance_contract.resolve_final_master(tmp_path, "第1集") == master.resolve()
    assert (
        acceptance_contract.current_evidence_bindings(tmp_path, "第1集")["records"]["master_asset"]["path"]
        == master.relative_to(tmp_path).as_posix()
    )
    _approve(tmp_path)
    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "pass"


def test_random_bytes_cannot_be_promoted_by_a_handwritten_green_verdict(tmp_path: Path) -> None:
    episode = "第1集"
    master = _canonical_evidence(tmp_path, episode)
    master.write_bytes(b"not-a-playable-mp4")
    verdict_path = acceptance_contract.verdict_path(tmp_path, episode)
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    final_master = next(row for row in verdict["components"] if row["name"] == "final_master")
    final_master["details"]["selected_sha256"] = acceptance_contract.sha256_file(master)
    final_master["details"]["duration_sec"] = 1.0
    verdict["evidence_bindings"] = acceptance_contract.current_evidence_bindings(tmp_path, episode)
    verdict["content_fingerprint"] = acceptance_contract.release_content_fingerprint(
        tmp_path, episode, "internal"
    )
    _write_json(verdict_path, verdict)

    with pytest.raises(
        acceptance_contract.AcceptanceContractError,
        match="not currently ffprobe-decodable",
    ):
        _approve(tmp_path, episode)


def test_rejected_decision_can_never_issue_or_validate_receipt(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    with pytest.raises(acceptance_contract.AcceptanceContractError, match="approved or accepted"):
        acceptance_contract.build_receipt(tmp_path, "第1集", reviewer="human-qc", decision="rejected")

    payload = _approve(tmp_path)
    payload["decision"] = "rejected"
    acceptance_contract.write_receipt(tmp_path, "第1集", payload)
    result = acceptance_contract.check_acceptance(tmp_path, "第1集")
    assert result["status"] == "fail"
    assert any("approved or accepted" in item for item in result["issues"])


def test_automated_identity_cannot_issue_or_validate_acceptance(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    for reviewer in ("Codex", "AI", "delegate:review", "system/reviewer", "制作代理:审片"):
        with pytest.raises(acceptance_contract.AcceptanceContractError, match="reviewer is required explicitly"):
            acceptance_contract.build_receipt(
                tmp_path, "第1集", reviewer=reviewer, decision="approved"
            )

    payload = _approve(tmp_path)
    payload["reviewer"] = "Codex"
    acceptance_contract.write_receipt(tmp_path, "第1集", payload)
    result = acceptance_contract.check_acceptance(tmp_path, "第1集")
    assert result["status"] == "fail"
    assert any("reviewer missing or placeholder" in item for item in result["issues"])


def test_deleted_acceptance_receipt_fails_closed(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    _approve(tmp_path)
    acceptance_contract.receipt_path(tmp_path, "第1集").unlink()

    result = acceptance_contract.check_acceptance(tmp_path, "第1集")
    assert result["status"] == "fail"
    assert result["available"] is False


def test_receipt_becomes_stale_when_bound_evidence_changes(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    _approve(tmp_path)
    _write_json(
        tmp_path / "生产数据" / "score_第1集.json",
        {"kind": "n2d_episode_review_score", "status": "pass", "score": 99},
    )

    result = acceptance_contract.check_acceptance(tmp_path, "第1集")
    assert result["status"] == "fail"
    assert any("score" in item and "sha256 mismatch" in item for item in result["issues"])
    assert any("stale" in item for item in result["issues"])


@pytest.mark.parametrize(
    ("receipt_name", "expected_issue"),
    [
        ("media_artifact_receipt_第1集.json", "media_artifact_receipt"),
        ("creative_watchdown_第1集.json", "creative_watchdown"),
    ],
)
def test_completion_receipt_change_revokes_acceptance(
    tmp_path: Path, receipt_name: str, expected_issue: str
) -> None:
    _canonical_evidence(tmp_path)
    _approve(tmp_path)
    path = tmp_path / "生产数据" / receipt_name
    data = json.loads(path.read_text(encoding="utf-8"))
    data["tampered"] = True
    _write_json(path, data)

    result = acceptance_contract.check_acceptance(tmp_path, "第1集")

    assert result["status"] == "fail"
    assert any(expected_issue in item for item in result["issues"])


def test_deleted_watchdown_revokes_acceptance(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    _approve(tmp_path)
    (tmp_path / "生产数据" / "creative_watchdown_第1集.json").unlink()

    result = acceptance_contract.check_acceptance(tmp_path, "第1集")

    assert result["status"] == "fail"
    assert any("creative_watchdown" in item for item in result["issues"])


def test_hand_edited_green_summary_cannot_bypass_current_receipt_validation(tmp_path: Path) -> None:
    episode = "第1集"
    _canonical_evidence(tmp_path, episode)
    media_path = tmp_path / "生产数据" / f"media_artifact_receipt_{episode}.json"
    media = json.loads(media_path.read_text(encoding="utf-8"))
    media["validation"]["status"] = "block"
    _write_json(media_path, media)
    _refresh_operational_evidence(tmp_path)

    # Simulate an attacker making the verdict's summaries and hashes look
    # current without actually obtaining a fresh, passing media receipt.
    verdict_path = acceptance_contract.verdict_path(tmp_path, episode)
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    for row in verdict["components"]:
        row["status"] = "pass"
    verdict["status"] = "internal-only"
    verdict["summary"] = {"block": 0, "warn": 0, "pass": len(verdict["components"])}
    verdict["blocking_reasons"] = []
    verdict["warnings"] = []
    verdict["evidence_bindings"] = acceptance_contract.current_evidence_bindings(tmp_path, episode)
    verdict["content_fingerprint"] = acceptance_contract.release_content_fingerprint(
        tmp_path, episode, "internal"
    )
    _write_json(verdict_path, verdict)

    with pytest.raises(
        acceptance_contract.AcceptanceContractError,
        match="current media_artifact_receipt invalid",
    ):
        _approve(tmp_path, episode)


def test_legacy_signoff_is_migration_only_and_advisory_never_counts(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    prod = tmp_path / "生产数据"
    _write_json(prod / "review_signoff_第1集.json", {"reviewer": "qa", "status": "rejected"})
    _write_json(prod / "consistency_advisory_signoff_第1集.json", {"reviewer": "qa", "status": "approved"})

    legacy = acceptance_contract.read_legacy_signoff(tmp_path, "第1集")
    assert legacy["available"] is True
    assert legacy["valid"] is False
    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "fail"


def test_legacy_approved_signoff_cannot_authorize_a_new_receipt(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    _write_json(
        tmp_path / "生产数据" / "review_signoff_第1集.json",
        {"reviewer": "old-reviewer", "status": "approved"},
    )

    with pytest.raises(acceptance_contract.AcceptanceContractError, match="required explicitly"):
        acceptance_contract.build_receipt(tmp_path, "第1集")


def test_verdict_cannot_hide_blocking_component_under_acceptable_status(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    path = acceptance_contract.verdict_path(tmp_path, "第1集")
    verdict = json.loads(path.read_text(encoding="utf-8"))
    verdict["components"][0]["status"] = "block"
    verdict["summary"] = {"block": 1, "warn": 0, "pass": len(verdict["components"]) - 1}
    verdict["blocking_reasons"] = [verdict["components"][0]]
    path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(acceptance_contract.AcceptanceContractError, match="contradicts blocking components"):
        _approve(tmp_path)


def test_progress_acceptance_writeback_does_not_invalidate_receipt(tmp_path: Path) -> None:
    progress = tmp_path / "_进度.md"
    progress.write_text("| 集 | 成片 | 验收 |\n|---|---|---|\n| 第1集 | ✅ | ⬜ |\n", encoding="utf-8")
    _canonical_evidence(tmp_path)
    _approve(tmp_path)

    progress.write_text("| 集 | 成片 | 验收 |\n|---|---|---|\n| 第1集 | ✅ | ✅ |\n", encoding="utf-8")

    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "pass"


def test_other_episode_progress_does_not_revoke_acceptance(tmp_path: Path) -> None:
    progress = tmp_path / "_进度.md"
    progress.write_text(
        "| 集 | 视频 | 成片 | 验收 |\n|---|---|---|---|\n| 第1集 | ✅ | ✅ | ⬜ |\n| 第2集 | ⬜ | ⬜ | ⬜ |\n",
        encoding="utf-8",
    )
    _canonical_evidence(tmp_path)
    _approve(tmp_path)

    progress.write_text(
        "| 集 | 视频 | 成片 | 验收 |\n|---|---|---|---|\n| 第1集 | ✅ | ✅ | ⬜ |\n| 第2集 | ✅ | ⬜ | ⬜ |\n",
        encoding="utf-8",
    )
    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "pass"

    progress.write_text(
        "| 集 | 视频 | 成片 | 验收 |\n|---|---|---|---|\n| 第1集 | ✅ | ⬜ | ⬜ |\n| 第2集 | ✅ | ⬜ | ⬜ |\n",
        encoding="utf-8",
    )
    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "fail"


def test_ep2_only_shared_asset_does_not_revoke_ep1_acceptance(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    _approve(tmp_path)
    ep2_asset = tmp_path / "出图" / "共享" / "图片" / "CHAR_EP2_only.png"
    ep2_asset.parent.mkdir(parents=True, exist_ok=True)
    ep2_asset.write_bytes(b"ep2")
    ep2_card = tmp_path / "设定库" / "characters" / "ep2.md"
    ep2_card.parent.mkdir(parents=True, exist_ok=True)
    ep2_card.write_text("# CHAR_EP2_ONLY 第二集角色\n", encoding="utf-8")

    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "pass"


def test_ep1_referenced_shared_asset_change_revokes_acceptance(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True, exist_ok=True)
    storyboard.write_text(
        '{"clips":[{"id":"Clip_01","reference":"出图/共享/图片/CHAR_EP1.png"}]}',
        encoding="utf-8",
    )
    shared = tmp_path / "出图" / "共享" / "图片" / "CHAR_EP1.png"
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_bytes(b"ep1-v1")
    _canonical_evidence(tmp_path)
    _approve(tmp_path)

    shared.write_bytes(b"ep1-v2")

    result = acceptance_contract.check_acceptance(tmp_path, "第1集")
    assert result["status"] == "fail"
    assert any("content_fingerprint" in issue for issue in result["issues"])


def test_other_episode_event_does_not_revoke_ep1_but_ep1_event_does(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    _approve(tmp_path)
    ledger = tmp_path / "生产数据" / "production_events.jsonl"
    ledger.write_text(json.dumps({
        "kind": "n2d_production_event", "version": 1,
        "ts": "2026-08-20T01:00:00+00:00", "episode": "第2集",
        "stage": "image", "event": "status", "source": "unit",
        "trace": {"trace_id": "ep2-event"},
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    _refresh_operational_evidence(tmp_path)
    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "pass"

    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "kind": "n2d_production_event", "version": 1,
            "ts": "2026-08-20T02:00:00+00:00", "episode": "第1集",
            "stage": "image", "event": "status", "source": "unit",
            "trace": {"trace_id": "ep1-event"},
        }, ensure_ascii=False) + "\n")
    _refresh_operational_evidence(tmp_path)
    assert acceptance_contract.check_acceptance(tmp_path, "第1集")["status"] == "fail"


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("production_events_audit.json", {"status": "pass"}),
        ("artifact_validation.json", {"status": "pass"}),
    ],
)
def test_status_only_operational_report_cannot_issue_acceptance(
    tmp_path: Path, filename: str, payload: dict
) -> None:
    _canonical_evidence(tmp_path)
    _write_json(tmp_path / "生产数据" / filename, payload)

    with pytest.raises(acceptance_contract.AcceptanceContractError, match="invalid|incomplete"):
        _approve(tmp_path)


def test_episode_owned_operational_projection_stales_on_internal_ep1_change(tmp_path: Path) -> None:
    _canonical_evidence(tmp_path)
    receipt = _approve(tmp_path)
    before = receipt["bindings"]["event_ledger_audit"]["sha256"]
    ledger = tmp_path / "生产数据" / "production_events.jsonl"
    ledger.write_text(json.dumps({
        "kind": "n2d_production_event", "version": 1,
        "ts": "2026-08-20T03:00:00+00:00", "episode": "第1集",
        "stage": "compose", "event": "status", "source": "unit",
        "trace": {"trace_id": "ep1-content-change"},
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    _refresh_operational_evidence(tmp_path)

    current = acceptance_contract.current_evidence_bindings(tmp_path, "第1集")
    assert current["records"]["event_ledger_audit"]["sha256"] != before
    result = acceptance_contract.check_acceptance(tmp_path, "第1集")
    assert result["status"] == "fail"
    assert any("event_ledger_audit" in item or "stale" in item for item in result["issues"])


def test_artifact_projection_stales_when_scanned_evidence_content_changes(tmp_path: Path) -> None:
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    _write_json(registry, {
        "kind": "n2d_identity_registry", "version": 1, "characters": [],
    })
    _canonical_evidence(tmp_path)
    receipt = _approve(tmp_path)
    before = receipt["bindings"]["artifact_validation"]["sha256"]

    _write_json(registry, {
        "kind": "n2d_identity_registry", "version": 1,
        "characters": [{"id": "CHAR_001"}],
    })
    _refresh_operational_evidence(tmp_path)

    current = acceptance_contract.current_evidence_bindings(tmp_path, "第1集")
    assert current["records"]["artifact_validation"]["sha256"] != before
    result = acceptance_contract.check_acceptance(tmp_path, "第1集")
    assert result["status"] == "fail"
    assert any("artifact_validation" in item or "stale" in item for item in result["issues"])


@pytest.mark.parametrize(
    "filename",
    ["production_events_audit.json", "artifact_validation.json"],
)
def test_operational_evidence_failure_revokes_acceptance(
    tmp_path: Path, filename: str
) -> None:
    _canonical_evidence(tmp_path)
    _approve(tmp_path)

    path = tmp_path / "生产数据" / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "fail"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = acceptance_contract.check_acceptance(tmp_path, "第1集")
    assert result["status"] == "fail"
    assert any(filename in issue or "component" in issue for issue in result["issues"])
