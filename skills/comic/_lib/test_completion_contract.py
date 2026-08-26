from pathlib import Path

from completion_contract import (
    accept_final,
    atomic_json,
    build_completion_verdict,
    canonical_release_digest,
    sha256_file,
    verify_stored_completion,
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


def test_automated_identity_cannot_final_accept(tmp_path: Path):
    for actor in ("delegate:agent", "Codex", "AI", "system/reviewer", "制作代理:审片"):
        try:
            accept_final(tmp_path, report(tmp_path), accepted_by=actor, note="")
        except ValueError as exc:
            assert "named human" in str(exc)
        else:
            raise AssertionError(f"automated final acceptance must fail: {actor}")


def test_stored_completion_revalidates_active_bundle_and_current_bytes(tmp_path: Path):
    settings = tmp_path / "_设置.md"
    settings.write_text("- 交付介质: web_images\n- 交付用途: internal\n- 目标平台: 通用\n", encoding="utf-8")
    artifact = tmp_path / "out.png"
    artifact.write_bytes(b"current-pixels")
    release = {
        "chapter": "第1话", "medium": "web_images", "usage": "internal",
        "target_platform": "通用", "verdict": "pass", "issues": [],
        "settings_binding": {"path": "_设置.md", "sha256": sha256_file(settings)},
        "artifacts": [{"path": "out.png", "sha256": sha256_file(artifact)}],
    }
    release["release_digest"] = canonical_release_digest(release)
    digest = release["release_digest"]
    bundle = tmp_path / "生产数据" / "releases" / "第1话" / digest / "release_verdict.json"
    atomic_json(bundle, release)
    atomic_json(tmp_path / "生产数据" / "release_contract_第1话.json", {
        "kind": "comic_active_release_contract", "chapter": "第1话",
        "release_digest": digest, "bundle_path": str(bundle.relative_to(tmp_path)),
        "bundle_sha256": sha256_file(bundle),
    })
    verdict = build_completion_verdict(tmp_path, release)
    atomic_json(tmp_path / "生产数据" / "completion_verdict_第1话.json", verdict)
    assert verify_stored_completion(tmp_path, "第1话")["current"] is True
    artifact.write_bytes(b"changed-pixels")
    stale = verify_stored_completion(tmp_path, "第1话")
    assert stale["current"] is False
    assert stale["status"] == "stale"
    assert any("artifact" in issue for issue in stale["issues"])
