from __future__ import annotations

from pathlib import Path

import pytest

import signoff_contract as sc


def test_two_role_signoff_is_hash_bound_and_same_solo_owner_can_wear_two_roles(tmp_path: Path) -> None:
    (tmp_path / "input.txt").write_text("source", encoding="utf-8")
    (tmp_path / "artifact.json").write_text("{}", encoding="utf-8")
    groups = (("creative", ("director",)), ("production", ("producer",)))
    payload = sc.new_manifest(
        tmp_path,
        artifact_scope="p2_director_blocking",
        author_id="automation:n2d",
        input_paths=["input.txt"],
        evidence_paths=["artifact.json"],
        required_role_groups=groups,
    )
    payload = sc.record_approval(
        payload, tmp_path, reviewer_id="user:owner", reviewer_role="director",
        evidence_paths=["artifact.json"], note="creative approved",
    )
    assert sc.derived_status(payload) == "pending"
    payload = sc.record_approval(
        payload, tmp_path, reviewer_id="user:owner", reviewer_role="producer",
        evidence_paths=["artifact.json"], note="production approved",
    )
    assert sc.validate_manifest(
        payload, tmp_path, artifact_scope="p2_director_blocking",
        input_paths=["input.txt"], evidence_paths=["artifact.json"],
        required_role_groups=groups,
    ) == []

    (tmp_path / "artifact.json").write_text('{"changed":true}', encoding="utf-8")
    issues = sc.validate_manifest(
        payload, tmp_path, artifact_scope="p2_director_blocking",
        input_paths=["input.txt"], evidence_paths=["artifact.json"],
        required_role_groups=groups,
    )
    assert any("过期" in issue for issue in issues)


def test_author_cannot_approve_own_artifact(tmp_path: Path) -> None:
    (tmp_path / "artifact").write_text("x", encoding="utf-8")
    payload = sc.new_manifest(
        tmp_path, artifact_scope="x", author_id="user:author",
        evidence_paths=["artifact"], required_role_groups=(("review", ("director",)),),
    )
    with pytest.raises(ValueError, match="不能审批自己的产物"):
        sc.record_approval(
            payload, tmp_path, reviewer_id="user:author", reviewer_role="director",
            evidence_paths=["artifact"],
        )


def test_approval_is_bound_to_inputs_and_must_cover_every_artifact(tmp_path: Path) -> None:
    (tmp_path / "input.txt").write_text("v1", encoding="utf-8")
    (tmp_path / "a.json").write_text("a", encoding="utf-8")
    (tmp_path / "b.json").write_text("b", encoding="utf-8")
    payload = sc.new_manifest(
        tmp_path,
        artifact_scope="x",
        input_paths=["input.txt"],
        evidence_paths=["a.json", "b.json"],
        required_role_groups=(("review", ("director",)),),
    )
    with pytest.raises(ValueError, match="未覆盖完整待签产物"):
        sc.record_approval(
            payload, tmp_path, reviewer_id="user:reviewer", reviewer_role="director",
            evidence_paths=["a.json"],
        )

    signed = sc.record_approval(
        payload, tmp_path, reviewer_id="user:reviewer", reviewer_role="director",
        evidence_paths=["a.json", "b.json"],
    )
    assert signed["approvals"][0]["signed_input_fingerprint_sha"] == payload["input_fingerprint"]["sha"]
    (tmp_path / "input.txt").write_text("v2", encoding="utf-8")
    issues = sc.validate_manifest(
        signed, tmp_path, artifact_scope="x", input_paths=["input.txt"],
        evidence_paths=["a.json", "b.json"],
        required_role_groups=(("review", ("director",)),),
    )
    assert any("input_fingerprint" in issue for issue in issues)


def test_profile_dependencies_exclude_progress_and_bind_animatic_otio(tmp_path: Path) -> None:
    (tmp_path / "小说").mkdir()
    (tmp_path / "小说" / "source.txt").write_text("novel", encoding="utf-8")
    (tmp_path / "_进度.md").write_text("volatile", encoding="utf-8")
    (tmp_path / "_设置.md").write_text("制作模式: 配音先行", encoding="utf-8")

    p1 = sc.profile_spec(tmp_path, "p1")
    animatic = sc.profile_spec(tmp_path, "animatic", "第1集")
    p3 = sc.profile_spec(tmp_path, "p3", "第1集")

    assert "_进度.md" not in p1["input_paths"]
    assert "_设置.md" in p1["input_paths"]
    assert "合成/第1集/_work/animatic_timeline.otio" in animatic["evidence_paths"]
    assert "脚本/第1集/animatic_signoff.json" in p3["input_paths"]


def test_missing_upstream_signoff_cannot_be_approved(tmp_path: Path) -> None:
    (tmp_path / "artifact.json").write_text("{}", encoding="utf-8")
    payload = sc.new_manifest(
        tmp_path, artifact_scope="handoff",
        input_paths=["upstream_signoff.json"], evidence_paths=["artifact.json"],
        required_role_groups=(("handoff", ("producer",)),),
    )
    with pytest.raises(ValueError, match="缺上游签收"):
        sc.record_approval(
            payload, tmp_path, reviewer_id="user:producer", reviewer_role="producer",
            evidence_paths=["artifact.json"],
        )
