from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("artifact_lineage.py")
spec = importlib.util.spec_from_file_location("artifact_lineage", SCRIPT)
artifact_lineage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(artifact_lineage)

from test_completion_evidence import write_test_master, write_valid_completion_receipts  # noqa: E402


def _write_test_mp4(path: Path) -> None:
    write_test_master(path)


def _write_completion_receipts(root: Path, episode: str, master: Path, contract) -> None:
    write_valid_completion_receipts(
        root, episode, master, contract, transaction_id="artifact-lineage-test"
    )


def _evidence(root: Path, episode: str) -> Path:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (root / "_进度.md").write_text("| 集 | 成片 |\n|---|---|\n| 第1集 | ✅ |\n", encoding="utf-8")
    script_dir = root / "脚本" / episode
    script_dir.mkdir(parents=True)
    (script_dir / "storyboard.json").write_text('{"clips":[]}', encoding="utf-8")
    comp = root / "合规"
    comp.mkdir()
    (comp / "compliance_manifest.json").write_text('{"kind":"n2d_compliance_manifest","version":1}', encoding="utf-8")
    prod = root / "生产数据"
    prod.mkdir()
    (prod / "production_events_audit.json").write_text('{"status":"pass","hash_chain_head":"abc"}', encoding="utf-8")
    (prod / "artifact_validation.json").write_text(
        json.dumps({"kind": "n2d_artifact_validation", "version": 1, "root": str(root), "status": "pass", "summary": {}, "checked": [], "issues": []}),
        encoding="utf-8",
    )
    (prod / f"generation_recipe_manifest_{episode}.json").write_text(
        json.dumps({"kind": "n2d_generation_recipe_manifest", "version": 1, "root": str(root), "episode": episode, "records": [], "summary": {}, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (prod / f"gate_policy_coverage_{episode}.json").write_text(
        json.dumps({"kind": "n2d_gate_policy_coverage", "version": 1, "root": str(root), "episode": episode, "matrix": {}, "groups": [], "summary": {}, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )
    asset = root / "合成" / episode / f"成片_{episode}_zh.mp4"
    _write_test_mp4(asset)
    (prod / f"score_{episode}.json").write_text('{"kind":"n2d_episode_review_score","version":1,"status":"pass","score":91}', encoding="utf-8")
    (prod / f"consistency_ledger_{episode}.json").write_text('{"kind":"n2d_consistency_ledger","version":1,"status":"pass"}', encoding="utf-8")
    (prod / f"review_ui_{episode}.json").write_text('{"kind":"n2d_review_ui","version":1,"status":"pass"}', encoding="utf-8")
    (prod / f"review_ui_findings_{episode}.json").write_text('{"kind":"n2d_consistency_findings","findings":[]}', encoding="utf-8")
    contract = artifact_lineage.acceptance_contract
    _write_completion_receipts(root, episode, asset, contract)
    (prod / "production_events.jsonl").touch(exist_ok=True)
    contract._event_ledger_module().audit(str(root), write=True, strict_trace=True)
    validation = contract.n2d_schema_registry.scan_artifacts(
        str(root), strict_unknown=True,
        scope=contract.n2d_schema_registry.SCAN_SCOPE_RELEASE,
        completion_inputs_only=True,
    )
    contract.n2d_schema_registry.write_validation(str(root), validation)
    components = [
        {"name": name, "status": "pass", "message": f"{name} passed"}
        for name in sorted(contract.REQUIRED_VERDICT_COMPONENTS)
    ]
    master_rel = asset.relative_to(root).as_posix()
    final_master = next(row for row in components if row["name"] == "final_master")
    final_master.update({
        "path": master_rel,
        "details": {
            "selected": master_rel,
            "selected_sha256": contract.sha256_file(asset),
            "duration_sec": contract.probe_master_duration(asset),
        },
    })
    (prod / f"release_verdict_{episode}.json").write_text(
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
        root, episode, reviewer="qa", decision="approved", accepted_at="2026-08-20T00:00:00+00:00"
    )
    contract.write_receipt(root, episode, receipt)
    return asset


def test_artifact_lineage_build_write_check(tmp_path: Path) -> None:
    episode = "第1集"
    _evidence(tmp_path, episode)

    payload = artifact_lineage.build_lineage(tmp_path, episode)
    path = artifact_lineage.write_lineage(tmp_path, episode, payload)

    assert payload["status"] == "pass"
    assert payload["lineage_id"]
    assert path.is_file()
    assert artifact_lineage.check_lineage(tmp_path, episode)["status"] == "pass"


def test_artifact_lineage_check_detects_hash_mismatch(tmp_path: Path) -> None:
    episode = "第1集"
    asset = _evidence(tmp_path, episode)
    payload = artifact_lineage.build_lineage(tmp_path, episode)
    artifact_lineage.write_lineage(tmp_path, episode, payload)

    asset.write_bytes(b"changed")

    result = artifact_lineage.check_lineage(tmp_path, episode)
    assert result["status"] == "fail"
    assert any("sha256 mismatch" in item for item in result["issues"])


def test_artifact_lineage_requires_canonical_acceptance_receipt(tmp_path: Path) -> None:
    episode = "第1集"
    _evidence(tmp_path, episode)
    payload = artifact_lineage.build_lineage(tmp_path, episode)
    artifact_lineage.write_lineage(tmp_path, episode, payload)
    artifact_lineage.acceptance_contract.receipt_path(tmp_path, episode).unlink()

    result = artifact_lineage.check_lineage(tmp_path, episode)
    assert result["status"] == "fail"
    assert any("acceptance_receipt" in item for item in result["issues"])


def test_artifact_lineage_rejects_stale_acceptance_receipt(tmp_path: Path) -> None:
    episode = "第1集"
    _evidence(tmp_path, episode)
    payload = artifact_lineage.build_lineage(tmp_path, episode)
    artifact_lineage.write_lineage(tmp_path, episode, payload)
    (tmp_path / "生产数据" / f"review_ui_{episode}.json").write_text(
        '{"kind":"n2d_review_ui","status":"pass","revision":2}', encoding="utf-8"
    )

    result = artifact_lineage.check_lineage(tmp_path, episode)
    assert result["status"] == "fail"
    assert any("acceptance_receipt" in item and "stale" in item for item in result["issues"])


def test_artifact_lineage_rejects_failed_required_operational_evidence(tmp_path: Path) -> None:
    episode = "第1集"
    _evidence(tmp_path, episode)
    audit = tmp_path / "生产数据" / "artifact_validation.json"
    payload = json.loads(audit.read_text(encoding="utf-8"))
    payload["status"] = "fail"
    audit.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    lineage = artifact_lineage.build_lineage(tmp_path, episode)

    assert lineage["status"] == "fail"
    assert any("artifact_validation" in issue for issue in lineage["evidence_issues"])
