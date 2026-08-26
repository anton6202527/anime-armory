import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import provenance_qc as pq


def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project(tmp_path: Path):
    root = tmp_path / "ad"
    master = root / "合成" / "成片_主片.mp4"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"final encoded bytes")
    (root / "合成" / "delivery_plan.json").write_text(json.dumps({"deliverables": [{
        "deliverable_id": "master", "expected_path": "合成/成片_主片.mp4", "status": "rendered"
    }]}), encoding="utf-8")
    (root / "合规").mkdir()
    (root / "合规" / "ai_usage.json").write_text(json.dumps({
        "visual_mode": "AI-generated", "video_mode": "AI-generated"
    }), encoding="utf-8")
    (root / "合规" / "probe.json").write_text("actual external c2pa/metadata probe", encoding="utf-8")
    (root / "需求").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps({
        "release_regions": ["中国大陆"],
        "provenance_receipts": [{
            "deliverable_id": "master", "status": "verified", "asset_sha256": _sha(master),
            "tool": "c2patool 0.22 + provider metadata API", "checked_at": "2026-07-11",
            "approved_by": "发布甲", "evidence_file": "合规/probe.json",
            "metadata_assertions": {"ai_generated": True, "provider_or_platform": "OpenAI",
                                    "content_id": "asset-001"},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return root


def test_external_actual_probe_receipt_must_bind_current_file_sha(tmp_path, monkeypatch):
    root = _project(tmp_path)
    monkeypatch.setattr(pq, "c2pa_probe", lambda path: None)
    monkeypatch.setattr(pq, "ffprobe_metadata", lambda path: None)
    report = pq.build(root)
    assert report["summary"]["verified"] is True
    assert report["items"][0]["external_receipt"]["valid"] is True
    assert report["items"][0]["origin_label_compliant"] is True
    assert report["items"][0]["cryptographic_provenance_valid"] is False

    (root / "合成" / "成片_主片.mp4").write_bytes(b"re-encoded")
    stale = pq.build(root)
    assert any(row["code"] == "provenance_not_verified" for row in stale["findings"])


def test_bare_metadata_status_is_not_an_input_or_proof(tmp_path, monkeypatch):
    root = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["provenance_receipts"] = []
    brief["metadata_status"] = "preserve"
    brief_path.write_text(json.dumps(brief), encoding="utf-8")
    monkeypatch.setattr(pq, "c2pa_probe", lambda path: {"verified": False})
    monkeypatch.setattr(pq, "ffprobe_metadata", lambda path: {"payload": {}, "ai_markers": []})
    report = pq.build(root)
    assert any(row["code"] == "provenance_not_verified" for row in report["findings"])


def test_c2pa_probe_requires_active_manifest_and_no_validation_failure(tmp_path, monkeypatch):
    media = tmp_path / "asset.mp4"
    media.write_bytes(b"media")
    monkeypatch.setattr(pq.shutil, "which", lambda name: "/usr/local/bin/c2patool")
    valid = {
        "active_manifest": "urn:c2pa:1",
        "manifests": {"urn:c2pa:1": {
            "assertions": [{"digitalSourceType":
                            "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"}]
        }},
        "validation_status": [{"code": "claimSignature.validated"}],
    }
    monkeypatch.setattr(pq.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout=json.dumps(valid), stderr=""))
    assert pq.c2pa_probe(media)["verified"] is True
    assert pq.c2pa_probe(media)["ai_assertion"] is True

    invalid = {**valid, "validation_status": [{"code": "assertion.dataHash.mismatch"}]}
    monkeypatch.setattr(pq.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout=json.dumps(invalid), stderr=""))
    result = pq.c2pa_probe(media)
    assert result["verified"] is False and result["validation_errors"]


def test_plain_metadata_never_claims_cryptographic_provenance(tmp_path, monkeypatch):
    root = _project(tmp_path)
    monkeypatch.setattr(pq, "c2pa_probe", lambda path: None)
    monkeypatch.setattr(pq, "ffprobe_metadata", lambda path: {
        "payload": {}, "ai_markers": ["ai-generated"],
        "china_assertions": {"ai_generated": True, "provider_or_platform": True,
                             "content_id": True, "complete": True},
    })
    report = pq.build(root)
    item = report["items"][0]
    assert item["origin_label_compliant"] is True
    assert item["cryptographic_provenance_valid"] is False
    assert item["cryptographic_provenance_trusted"] is False
