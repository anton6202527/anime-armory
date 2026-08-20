from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("release_manifest.py")
spec = importlib.util.spec_from_file_location("release_manifest", SCRIPT)
release_manifest = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(release_manifest)

compliance = release_manifest.compliance


def _write_test_mp4(path: Path, *, color: str = "black") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                f"color=c={color}:s=16x16:d=0.2", "-an", "-c:v", "mpeg4", str(path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except FileNotFoundError:
        pytest.skip("ffmpeg unavailable")
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")


def _write_internal_compliance(root: Path, episode: str) -> None:
    data = compliance.default_manifest(root, episode)
    data["distribution_intent"] = "internal_only"
    path = compliance.manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_release_evidence(root: Path, episode: str) -> None:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (root / "_进度.md").write_text("| 集 | 成片 | 验收 |\n|---|---|---|\n| 第1集 | ✅ | ✅ |\n", encoding="utf-8")
    script_dir = root / "脚本" / episode
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "storyboard.json").write_text('{"kind":"storyboard","clips":[]}', encoding="utf-8")
    pdir = root / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / "production_events_audit.json").write_text(
        json.dumps({"status": "pass", "event_count": 1, "hash_chain_head": "abc", "strict_trace": True}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / "artifact_validation.json").write_text(
        json.dumps({"kind": "n2d_artifact_validation", "version": 1, "root": str(root), "status": "pass", "summary": {}, "checked": [], "issues": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"generation_recipe_manifest_{episode}.json").write_text(
        json.dumps({"kind": "n2d_generation_recipe_manifest", "version": 1, "root": str(root), "episode": episode, "records": [], "summary": {}, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"gate_policy_coverage_{episode}.json").write_text(
        json.dumps({"kind": "n2d_gate_policy_coverage", "version": 1, "root": str(root), "episode": episode, "matrix": {}, "groups": [], "summary": {}, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"score_{episode}.json").write_text(
        json.dumps({"kind": "n2d_episode_review_score", "version": 1, "status": "pass", "score": 91, "threshold": 85}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"consistency_ledger_{episode}.json").write_text(
        json.dumps({"kind": "n2d_consistency_ledger", "version": 1, "status": "pass", "counts": {"block": 0, "high": 0}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"review_ui_{episode}.json").write_text(
        json.dumps({"kind": "n2d_review_ui", "version": 1, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (pdir / f"review_ui_findings_{episode}.json").write_text(
        json.dumps({"kind": "n2d_consistency_findings", "version": 1, "findings": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    ledger = pdir / "production_events.jsonl"
    ledger.touch(exist_ok=True)
    contract = release_manifest.acceptance_contract
    contract._event_ledger_module().audit(str(root), write=True, strict_trace=True)
    validation = contract.n2d_schema_registry.scan_artifacts(
        str(root), strict_unknown=True,
        scope=contract.n2d_schema_registry.SCAN_SCOPE_RELEASE,
        completion_inputs_only=True,
    )
    contract.n2d_schema_registry.write_validation(str(root), validation)


def _write_canonical_acceptance(root: Path, episode: str, *, decision: str = "approved") -> None:
    contract = release_manifest.acceptance_contract
    verdict_path = contract.verdict_path(root, episode)
    verdict_path.parent.mkdir(parents=True, exist_ok=True)
    components = [
        {"name": name, "status": "pass", "message": f"{name} passed"}
        for name in sorted(contract.REQUIRED_VERDICT_COMPONENTS)
    ]
    master = contract.resolve_final_master(root, episode)
    assert master is not None
    master_rel = master.relative_to(root).as_posix()
    final_master = next(row for row in components if row["name"] == "final_master")
    final_master.update({
        "path": master_rel,
        "details": {
            "selected": master_rel,
            "selected_sha256": contract.sha256_file(master),
            "duration_sec": contract.probe_master_duration(master),
        },
    })
    verdict_path.write_text(
        json.dumps({
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
            "evidence_bindings": contract.current_evidence_bindings(root, episode),
            "content_fingerprint": contract.release_content_fingerprint(root, episode, "internal"),
        }, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    receipt = contract.build_receipt(
        root,
        episode,
        reviewer="human",
        decision=decision,
        accepted_at="2026-08-20T00:00:00+00:00",
    )
    contract.write_receipt(root, episode, receipt)


def test_build_release_manifest_ready_with_asset_and_signoff(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    _write_canonical_acceptance(tmp_path, episode)

    payload = release_manifest.build_manifest(tmp_path, episode)
    path = release_manifest.write_manifest(tmp_path, episode, payload)

    assert payload["readiness"]["status"] == "ready"
    assert payload["asset"]["sha256"]
    assert payload["review"]["signoff"]["available"] is True
    assert payload["review"]["acceptance_receipt"]["valid"] is True
    assert payload["review"]["release_verdict"]["status"] == "internal-only"
    assert payload["provenance"]["artifact_lineage"]["path"]
    assert payload["transparency"]["strict"] is False
    assert payload["transparency"]["machine_readable_present"] is False
    assert payload["readiness"]["status"] == "ready"  # internal_only: transparency gaps are publish todos
    assert path.is_file()
    assert (tmp_path / "生产数据" / f"artifact_lineage_{episode}.json").is_file()
    assert release_manifest.check_manifest(tmp_path, episode)["status"] == "pass"


def test_release_manifest_check_detects_asset_hash_mismatch(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    _write_canonical_acceptance(tmp_path, episode)
    payload = release_manifest.build_manifest(tmp_path, episode)
    release_manifest.write_manifest(tmp_path, episode, payload)

    asset.write_bytes(b"v2")
    result = release_manifest.check_manifest(tmp_path, episode)

    assert result["status"] == "fail"
    assert "asset sha256 mismatch" in result["issues"]


def test_release_manifest_cannot_swap_to_unreviewed_master(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    unreviewed = tmp_path / "合成" / episode / f"成片_{episode}_bilingual.mp4"
    _write_test_mp4(unreviewed, color="red")
    accepted = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(accepted, color="blue")
    _write_canonical_acceptance(tmp_path, episode)

    payload = release_manifest.build_manifest(
        tmp_path,
        episode,
        asset=str(unreviewed.relative_to(tmp_path)),
    )
    release_manifest.write_manifest(tmp_path, episode, payload)
    result = release_manifest.check_manifest(tmp_path, episode)

    assert payload["readiness"]["status"] == "blocked"
    assert any("acceptance master binding" in item for item in payload["readiness"]["blocks"])
    assert result["status"] == "fail"
    assert any("acceptance master binding" in item for item in result["issues"])


def test_release_manifest_blocks_missing_canonical_acceptance_and_only_surfaces_gate_diagnostic(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / f"gate_findings_review_{episode}.json").write_text(
        json.dumps({
            "kind": "n2d_consistency_findings",
            "findings": [{"severity": "block", "dimension": "角色一致性", "message": "脸漂"}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    payload = release_manifest.build_manifest(tmp_path, episode)

    assert payload["readiness"]["status"] == "blocked"
    assert any("canonical acceptance receipt" in item for item in payload["readiness"]["blocks"])
    assert not any("gate block" in item for item in payload["readiness"]["blocks"])
    assert payload["review"]["gate_blocks"] == 1


def test_transparency_blocks_paid_release_without_labels(tmp_path: Path) -> None:
    episode = "第1集"
    data = compliance.default_manifest(tmp_path, episode)
    data["distribution_intent"] = "paid_distribution"

    summary = release_manifest.transparency_summary(tmp_path, episode, data, stage="release")

    assert summary["strict"] is True
    assert any("显式标识" in item for item in summary["blocks"])
    assert any("机器可读" in item for item in summary["blocks"])


def test_transparency_accepts_label_and_c2pa_manifest(tmp_path: Path) -> None:
    episode = "第1集"
    data = compliance.default_manifest(tmp_path, episode)
    data["distribution_intent"] = "paid_distribution"
    data["ai_labeling"]["explicit_label"]["status"] = "done"
    data["ai_labeling"]["implicit_metadata"]["applied"] = False
    c2pa = tmp_path / "合规" / "c2pa_manifest.json"
    c2pa.parent.mkdir(parents=True)
    c2pa.write_text('{"kind":"c2pa"}', encoding="utf-8")
    data["ai_labeling"]["implicit_metadata"]["c2pa_manifest"] = "合规/c2pa_manifest.json"

    summary = release_manifest.transparency_summary(tmp_path, episode, data, stage="release")

    assert summary["machine_readable_present"] is True
    assert summary["content_credentials"]["status"] == "present"
    assert summary["blocks"] == []


def test_platform_checklist_blocks_paid_target_missing_delivery_assets(tmp_path: Path) -> None:
    episode = "第1集"
    data = compliance.default_manifest(tmp_path, episode)
    data["distribution_intent"] = "paid_distribution"
    data["platform_review"]["targets"] = [{"platform": "TikTok", "region": "US", "language": "en"}]
    data["ai_labeling"]["explicit_label"]["status"] = "done"
    data["ai_labeling"]["implicit_metadata"]["applied"] = True
    data["ai_labeling"]["platform_disclosure"] = {"status": "done"}
    transparency = release_manifest.transparency_summary(tmp_path, episode, data, stage="release")

    checklist = release_manifest.platform_release_checklist(
        tmp_path,
        episode,
        data,
        transparency,
        [],
        stage="release",
    )

    assert checklist["strict"] is True
    assert checklist["targets"][0]["platform"] == "tiktok"
    assert {"subtitle", "cover"} <= set(checklist["targets"][0]["missing"])
    assert any("platform checklist tiktok missing" in item for item in checklist["blocks"])


def test_platform_checklist_accepts_required_delivery_evidence(tmp_path: Path) -> None:
    episode = "第1集"
    (tmp_path / "脚本" / episode).mkdir(parents=True)
    (tmp_path / "脚本" / episode / "字幕_中文.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n字幕\n", encoding="utf-8")
    (tmp_path / "合成" / episode).mkdir(parents=True)
    (tmp_path / "合成" / episode / "cover.jpg").write_bytes(b"jpg")
    data = compliance.default_manifest(tmp_path, episode)
    data["distribution_intent"] = "paid_distribution"
    data["platform_review"]["targets"] = [{"platform": "YouTube", "region": "US", "language": "en"}]
    data["ai_labeling"]["explicit_label"]["status"] = "done"
    data["ai_labeling"]["implicit_metadata"]["applied"] = True
    data["ai_labeling"]["platform_disclosure"] = {"status": "done"}
    transparency = release_manifest.transparency_summary(tmp_path, episode, data, stage="release")

    checklist = release_manifest.platform_release_checklist(
        tmp_path,
        episode,
        data,
        transparency,
        [],
        stage="release",
    )

    assert checklist["targets"][0]["platform"] == "youtube"
    assert checklist["targets"][0]["missing"] == []
    assert checklist["blocks"] == []


def test_release_manifest_rejects_legacy_rubber_stamp_signoff(tmp_path: Path) -> None:
    """旧文件即使存在，也不能替代 canonical acceptance receipt。"""
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    # 文件存在但缺 reviewer + 缺真实结论
    (pdir / f"review_signoff_{episode}.json").write_text("{}", encoding="utf-8")

    payload = release_manifest.build_manifest(tmp_path, episode)

    assert payload["readiness"]["status"] == "blocked"
    assert payload["review"]["signoff"]["available"] is False
    assert payload["review"]["signoff"]["valid"] is False
    assert any("canonical acceptance receipt" in item for item in payload["readiness"]["blocks"])


def test_release_manifest_accepts_canonical_receipt_with_reviewer_and_decision(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    _write_canonical_acceptance(tmp_path, episode)

    signoff = release_manifest.review_signoff(tmp_path, episode)
    assert signoff["valid"] is True
    assert signoff["reviewer"] == "human"
    assert signoff["canonical"] is True


def test_release_manifest_blocks_stale_acceptance_receipt(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    _write_canonical_acceptance(tmp_path, episode)
    (tmp_path / "生产数据" / f"score_{episode}.json").write_text(
        '{"kind":"n2d_episode_review_score","status":"pass","score":99}', encoding="utf-8"
    )

    payload = release_manifest.build_manifest(tmp_path, episode)
    assert payload["readiness"]["status"] == "blocked"
    assert any("acceptance receipt" in item and "stale" in item for item in payload["readiness"]["blocks"])


def test_release_manifest_blocks_when_compliance_changes_after_acceptance(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    _write_canonical_acceptance(tmp_path, episode)

    compliance_path = tmp_path / "合规" / "compliance_manifest.json"
    data = json.loads(compliance_path.read_text(encoding="utf-8"))
    data["distribution_intent"] = "paid_distribution"
    compliance_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    assert release_manifest.acceptance_contract.check_acceptance(tmp_path, episode)["status"] == "fail"
    payload = release_manifest.build_manifest(tmp_path, episode)
    assert payload["readiness"]["status"] == "blocked"
    assert any("content_fingerprint" in item for item in payload["readiness"]["blocks"])


def test_release_manifest_check_fails_after_acceptance_receipt_deleted(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    _write_canonical_acceptance(tmp_path, episode)
    payload = release_manifest.build_manifest(tmp_path, episode)
    release_manifest.write_manifest(tmp_path, episode, payload)
    release_manifest.acceptance_contract.receipt_path(tmp_path, episode).unlink()

    result = release_manifest.check_manifest(tmp_path, episode)
    assert result["status"] == "fail"
    assert any("acceptance receipt" in item for item in result["issues"])


def test_rejected_legacy_and_approved_advisory_never_make_manifest_ready(tmp_path: Path) -> None:
    episode = "第1集"
    _write_internal_compliance(tmp_path, episode)
    _write_release_evidence(tmp_path, episode)
    asset = tmp_path / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    prod = tmp_path / "生产数据"
    (prod / f"review_signoff_{episode}.json").write_text(
        '{"reviewer":"qa","decision":"rejected"}', encoding="utf-8"
    )
    (prod / f"consistency_advisory_signoff_{episode}.json").write_text(
        '{"reviewer":"qa","decision":"approved"}', encoding="utf-8"
    )

    payload = release_manifest.build_manifest(tmp_path, episode)
    assert payload["readiness"]["status"] == "blocked"
    assert payload["review"]["signoff"]["available"] is False
