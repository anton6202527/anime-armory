import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import human_signoff as hs  # noqa: E402


def _project(tmp_path):
    root = tmp_path / "ad"
    for rel in ("合成/成片_主片.mp4", "合成/delivery_plan.json", "合成/delivery_qc.json",
                "合成/accessibility_qc.json", "合成/color_preflight.json",
                "合成/rendered_text_qc.json", "合成/asr_consistency.json",
                "合规/provenance_qc.json", "合规/release_variant_manifest.json",
                "合规/locale_matrix_validation.json", "合规/compliance_manifest.json",
                "生产数据/campaign_readiness.json", "生产数据/consistency_findings.json",
                "生产数据/final_media_consistency.json", "合规/ad_review_m0.json"):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": {"block": 0}}
        if path.name == "delivery_plan.json":
            payload = {"deliverables": [{"deliverable_id": "master", "expected_path": "合成/成片_主片.mp4"}]}
        elif path.name == "final_media_consistency.json":
            sheet = root / "生产数据" / "final_media_contact_sheets" / "PROD_TEST.jpg"
            sheet.parent.mkdir(parents=True, exist_ok=True)
            sheet.write_bytes(b"contact sheet")
            payload = {"summary": {"block": 0}, "assets": {
                "PROD_TEST": {"contact_sheet": {"path": "生产数据/final_media_contact_sheets/PROD_TEST.jpg"}}
            }}
        path.write_text(json.dumps(payload) if path.suffix == ".json" else "video", encoding="utf-8")
    for rel in ("生产数据/render_profile.json", "生产数据/placement_adaptation.json"):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"kind": rel}), encoding="utf-8")
    acceptance = {
        "schema_version": 1, "kind": "ad_stage_acceptance", "stage": "compose", "mode": "formal",
        "contract_version": hs.dependency_graph.contract.CONTRACT_VERSION,
        "acceptance_version": hs.dependency_graph.contract.STAGE_ACCEPTANCE_VERSION,
        "dependency_snapshot_sha256": hs.dependency_graph.stage_snapshot_sha256(root, "compose"),
        "findings": [], "summary": {"block": 0, "warn": 0, "accepted": True},
    }
    path = root / "生产数据" / "stage_acceptance" / "compose.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(acceptance), encoding="utf-8")
    hs.dependency_graph.accept_stage(root, "compose")
    return root


def test_signoff_requires_every_human_check(tmp_path):
    root = _project(tmp_path)
    incomplete = hs.build(root, "审片人甲", ["product_identity"])
    assert incomplete["summary"]["approved"] is False

    evidence = {key: f"审片记录/{key}.md" for key in hs.EVIDENCE_REQUIRED}
    for rel in evidence.values():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("review evidence", encoding="utf-8")
    complete = hs.build(root, "审片人甲", hs.CHECKS, evidence=evidence)
    assert complete["summary"]["approved"] is True
    assert all(complete["source_sha256"].values())
    assert complete["source_sha256"]["deliverables"]["master"]
    assert complete["source_sha256"]["campaign_readiness"]
    assert complete["source_sha256"]["compliance_manifest"]
    assert all(complete["evidence_sha256"].values())


def test_high_risk_human_approval_requires_evidence_reference(tmp_path):
    root = _project(tmp_path)
    payload = hs.build(root, "审片人甲", hs.CHECKS)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "human_evidence_missing" for f in payload["findings"])
