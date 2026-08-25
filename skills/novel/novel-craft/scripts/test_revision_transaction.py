from __future__ import annotations

import json
from pathlib import Path

import revision_transaction as rt
import story_vcs


def _project(root: Path) -> None:
    (root / "章节").mkdir()
    (root / "设定").mkdir()
    (root / "修订").mkdir()
    (root / "章节/第01章.md").write_text("# 第1章 起点\n<!-- meta -->\n" + "正文" * 500, encoding="utf-8")
    (root / "_进度.md").write_text("# 进度", encoding="utf-8")
    (root / "设定/动态百科.json").write_text("{}", encoding="utf-8")
    (root / "修订/revision_plan.json").write_text(json.dumps({"tasks": [{
        "id": "REV-001", "chapter": 1, "tier": "scene", "status": "open",
        "title": "强化场景", "recommended_skill": "novel-rewrite", "return_to_stage": "rewrite",
    }]}), encoding="utf-8")


def test_transaction_branches_chapter_verifies_and_promotes(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path)
    tx = rt.start(tmp_path, "REV-001")
    manifest = story_vcs.load_manifest(str(tmp_path), tx["branch"])
    chapter = next(row for row in manifest["files"] if row["main_path"] == "章节/第01章.md")
    candidate = tmp_path / chapter["branch_path"]
    candidate.write_text(candidate.read_text(encoding="utf-8") + "\n强化后的结尾。", encoding="utf-8")
    checked = rt.verify(tmp_path, "REV-001", verified_by="specialist_reviewer:test")
    assert checked["status"] == "verified"
    monkeypatch.setattr(rt, "_mechanical_check", lambda *a, **k: {"returncode": 0, "red_findings": [], "report": "x"})
    promoted = rt.promote(tmp_path, "REV-001")
    assert promoted["status"] == "promoted"
    assert "强化后的结尾" in (tmp_path / "章节/第01章.md").read_text(encoding="utf-8")


def test_failed_post_merge_gate_rolls_back(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path)
    original = (tmp_path / "章节/第01章.md").read_text(encoding="utf-8")
    tx = rt.start(tmp_path, "REV-001")
    manifest = story_vcs.load_manifest(str(tmp_path), tx["branch"])
    chapter = next(row for row in manifest["files"] if row["main_path"] == "章节/第01章.md")
    (tmp_path / chapter["branch_path"]).write_text("坏稿", encoding="utf-8")
    rt.verify(tmp_path, "REV-001", verified_by="specialist_reviewer:test")
    monkeypatch.setattr(rt, "_mechanical_check", lambda *a, **k: {"returncode": 0, "red_findings": [{"severity": "🔴"}], "report": "x"})
    promoted = rt.promote(tmp_path, "REV-001")
    assert promoted["status"] == "rolled_back"
    assert (tmp_path / "章节/第01章.md").read_text(encoding="utf-8") == original
