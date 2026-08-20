from pathlib import Path

import pytest

import content_fingerprint as cf


def test_fingerprint_changes_for_content_and_glob_membership(tmp_path: Path) -> None:
    (tmp_path / "inputs").mkdir()
    first = tmp_path / "inputs" / "a.json"
    first.write_text('{"a":1}', encoding="utf-8")
    one = cf.build_content_fingerprint(
        tmp_path, source_patterns=["inputs/*.json"], values={"backend": "v1"}, scope="video",
    )
    first.write_text('{"a":2}', encoding="utf-8")
    two = cf.build_content_fingerprint(
        tmp_path, source_patterns=["inputs/*.json"], values={"backend": "v1"}, scope="video",
    )
    assert one["sha256"] != two["sha256"]
    (tmp_path / "inputs" / "b.json").write_text("{}", encoding="utf-8")
    three = cf.build_content_fingerprint(
        tmp_path, source_patterns=["inputs/*.json"], values={"backend": "v1"}, scope="video",
    )
    assert two["sha256"] != three["sha256"]


def test_fingerprint_is_recomputable_and_value_sensitive(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("same", encoding="utf-8")
    recorded = cf.build_content_fingerprint(
        tmp_path, source_patterns=["a.txt", "missing.json"], values={"model": "m1"}, scope="image",
    )
    assert cf.fingerprint_issues(tmp_path, recorded) == []
    changed = dict(recorded)
    changed["values"] = {"model": "m2"}
    assert cf.fingerprint_issues(tmp_path, changed) == ["input_fingerprint_stale"]


def test_fingerprint_rejects_paths_outside_project(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes project root"):
        cf.build_content_fingerprint(tmp_path, source_patterns=[outside])
