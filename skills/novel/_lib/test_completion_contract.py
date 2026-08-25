from __future__ import annotations

import json
from pathlib import Path

import completion_contract as cc


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
