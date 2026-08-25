from pathlib import Path

from completion_contract import (
    accept_final,
    build_completion_verdict,
    canonical_release_digest,
)


def report(tmp_path: Path, verdict: str = "pass") -> dict:
    artifact = tmp_path / "out.png"
    artifact.write_bytes(b"png")
    return {
        "chapter": "第1话", "medium": "web_images", "usage": "internal",
        "target_platform": "generic", "verdict": verdict,
        "artifacts": [{"path": "out.png", "sha256": "a" * 64}],
        "review_gate_summary": {"receipt_id": "r1"},
        "issues": [] if verdict == "pass" else [
            {"code": "broken", "reason": "broken", "blocks_active_delivery": True}
        ],
    }


def test_digest_changes_with_active_contract(tmp_path: Path):
    first = report(tmp_path)
    second = dict(first, usage="public")
    assert canonical_release_digest(first) != canonical_release_digest(second)


def test_machine_ready_then_named_acceptance(tmp_path: Path):
    release = report(tmp_path)
    before = build_completion_verdict(tmp_path, release)
    assert before["status"] == "machine_ready"
    accept_final(tmp_path, release, accepted_by="Wesley", note="final pixels reviewed")
    assert build_completion_verdict(tmp_path, release)["status"] == "accepted"


def test_acceptance_invalidates_on_artifact_hash_change(tmp_path: Path):
    release = report(tmp_path)
    accept_final(tmp_path, release, accepted_by="Wesley", note="ok")
    changed = dict(release, artifacts=[{"path": "out.png", "sha256": "b" * 64}])
    assert build_completion_verdict(tmp_path, changed)["status"] == "machine_ready"


def test_delegate_cannot_final_accept(tmp_path: Path):
    try:
        accept_final(tmp_path, report(tmp_path), accepted_by="delegate:agent", note="")
    except ValueError as exc:
        assert "non-delegate" in str(exc)
    else:
        raise AssertionError("delegate final acceptance must fail")
