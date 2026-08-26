from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


MODULE = Path(__file__).with_name("completion_contract.py")
SPEC = importlib.util.spec_from_file_location("novel_completion_contract_tested", MODULE)
assert SPEC and SPEC.loader
cc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cc)


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    else:
        path.write_text(str(value), encoding="utf-8")


def _manifest(root: Path) -> dict:
    _write(root / "章节/第01章.md", "# 第1章\n正文")
    _write(root / "导出/book.txt", "正文")
    chapters = [{"path": "章节/第01章.md", "sha256": cc.sha256_file(root / "章节/第01章.md")}]
    exports = [{"path": "导出/book.txt", "sha256": cc.sha256_file(root / "导出/book.txt")}]
    manifest = {
        "release_profile": "platform_publish", "release_name": "book", "release_ready": True,
        "chapters": chapters, "exports": exports, "evidence": {}, "meta": {}, "settings": {},
        "readiness_contract_version": cc.READINESS_CONTRACT_VERSION,
        "release_readiness": {
            "release_profile": "platform_publish", "profile_label": "Platform publish",
            "passed": True, "blocker_count": 0, "warning_count": 0,
            "blockers": [], "warnings": [], "checks": [],
            "qa_gate": {"blocking": False, "blocker_count": 0, "warning_count": 0, "profile_skipped": False},
        },
    }
    manifest["release_digest"] = cc.canonical_release_digest(manifest)
    _write(root / "导出/release_manifest.json", manifest)
    return manifest


def test_machine_ready_requires_hash_bound_named_acceptance(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    verdict = cc.build_completion_verdict(tmp_path)
    assert verdict["status"] == "machine_ready"
    assert verdict["release_digest"] == manifest["release_digest"]

    receipt = cc.accept_release(tmp_path, accepted_by="主编", note="终稿确认")
    assert receipt["release_digest"] == manifest["release_digest"]
    assert cc.build_completion_verdict(tmp_path)["status"] == "accepted"


def test_content_change_invalidates_acceptance_and_stale_manifest(tmp_path: Path) -> None:
    _manifest(tmp_path)
    cc.accept_release(tmp_path, accepted_by="作者")
    (tmp_path / "导出/book.txt").write_text("改过的正文", encoding="utf-8")
    stale = cc.build_completion_verdict(tmp_path)
    assert stale["status"] == "blocked"
    assert "hash changed" in " ".join(stale["blockers"])
    # Rebuild the manifest and prove the old receipt cannot follow the new digest.
    manifest = json.loads((tmp_path / "导出/release_manifest.json").read_text(encoding="utf-8"))
    manifest["exports"][0]["sha256"] = cc.sha256_file(tmp_path / "导出/book.txt")
    manifest["release_digest"] = cc.canonical_release_digest(manifest)
    _write(tmp_path / "导出/release_manifest.json", manifest)
    verdict = cc.build_completion_verdict(tmp_path)
    assert verdict["status"] == "machine_ready"
    assert "stale" in " ".join(verdict["acceptance"]["issues"])


def test_release_ready_boolean_cannot_override_bound_blockers(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["release_ready"] = True
    manifest["release_readiness"].update({
        "passed": False,
        "blocker_count": 1,
        "blockers": [{"id": "RELEASE-TEST-BLOCK", "message": "current gate blocks", "path": "审稿/review_report.json"}],
    })
    # Even if a caller recomputes the digest after changing the summary boolean,
    # the verdict derives readiness from the bound gate details.
    manifest["release_digest"] = cc.canonical_release_digest(manifest)
    _write(tmp_path / "导出/release_manifest.json", manifest)

    verdict = cc.build_completion_verdict(tmp_path)
    assert verdict["status"] == "blocked"
    assert verdict["machine_ready"] is False
    assert "disagrees" in " ".join(verdict["blockers"])
    assert "did not pass" in " ".join(verdict["blockers"])


def test_readiness_gate_details_are_part_of_release_digest(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    original = manifest["release_digest"]
    manifest["release_readiness"]["warnings"].append({
        "id": "RELEASE-ADVISORY", "message": "review this exact warning", "path": "审稿/review_report.json",
    })
    manifest["release_readiness"]["warning_count"] = 1
    assert cc.canonical_release_digest(manifest) != original


def test_legacy_unbound_readiness_fails_closed_until_manifest_rebuild(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest.pop("readiness_contract_version")
    manifest.pop("release_readiness")
    manifest["release_digest"] = cc.canonical_release_digest(manifest)
    _write(tmp_path / "导出/release_manifest.json", manifest)
    verdict = cc.build_completion_verdict(tmp_path)
    assert verdict["status"] == "blocked"
    assert "rebuild release_manifest.json" in " ".join(verdict["blockers"])


@pytest.mark.parametrize(
    "actor",
    ["agent", "delegate:visual-qc-agent", "system", "automation-bot", "Codex", "代理：视觉质检"],
)
def test_final_acceptance_rejects_automated_identity(tmp_path: Path, actor: str) -> None:
    _manifest(tmp_path)
    with pytest.raises(ValueError, match="named human"):
        cc.accept_release(tmp_path, accepted_by=actor)


def test_stored_automated_acceptance_receipt_is_not_accepted(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    _write(tmp_path / "导出/final_acceptance.json", {
        "kind": cc.ACCEPTANCE_KIND,
        "decision": "accepted",
        "accepted_by": "delegate:editorial-agent",
        "release_digest": manifest["release_digest"],
    })
    verdict = cc.build_completion_verdict(tmp_path)
    assert verdict["status"] == "machine_ready"
    assert "named human" in " ".join(verdict["acceptance"]["issues"])
