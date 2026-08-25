from __future__ import annotations

import json
from pathlib import Path

import dynamic_outline as d


def _project(root: Path, chapters: int = 5) -> None:
    (root / "章节").mkdir()
    (root / "设定").mkdir()
    (root / "设定/章纲.md").write_text("# 章纲\n旧", encoding="utf-8")
    (root / "设定/scene_cards.json").write_text("{}", encoding="utf-8")
    for number in range(1, chapters + 1):
        (root / f"章节/第{number:02d}章.md").write_text(f"# 第{number}章\n", encoding="utf-8")


def test_future_only_delta_auto_applies_with_hash_receipt(tmp_path: Path) -> None:
    _project(tmp_path)
    payload = d.scaffold(tmp_path, delta_id="d1")
    payload["affected_chapters"] = [6, 7]
    payload["reason"] = "前五章节奏证据要求提早支线回收"
    payload["evidence"] = [{"path": "审稿/review_report.json", "finding": "pacing"}]
    payload["proposed_files"] = [{"path": "设定/章纲.md", "content": "# 章纲\n新"}]
    d.atomic_write_json(d.delta_path(tmp_path, "d1"), payload)
    assert d.evaluate(tmp_path, payload)["verdict"] == "auto_apply"
    receipt = d.apply_delta(tmp_path, d.delta_path(tmp_path, "d1"))
    assert (tmp_path / "设定/章纲.md").read_text(encoding="utf-8").endswith("新")
    assert len(receipt["outputs"][0]["sha256"]) == 64


def test_written_chapter_or_author_contract_requires_human(tmp_path: Path) -> None:
    _project(tmp_path)
    payload = d.scaffold(tmp_path, delta_id="d2")
    payload["affected_chapters"] = [4]
    payload["touches_author_intent"] = True
    payload["proposed_files"] = [{"path": "设定/章纲.md", "content": "# changed"}]
    d.atomic_write_json(d.delta_path(tmp_path, "d2"), payload)
    assert d.evaluate(tmp_path, payload)["verdict"] == "needs_human"
    try:
        d.apply_delta(tmp_path, d.delta_path(tmp_path, "d2"))
    except ValueError as exc:
        assert "human approval" in str(exc)
    else:
        raise AssertionError("expected human boundary")


def test_workflow_requests_checkpoint_and_then_specialist_content(tmp_path: Path) -> None:
    _project(tmp_path)
    assert d.workflow_status(tmp_path)["phase"] == "create_delta"
    d.scaffold(tmp_path, delta_id="d3")
    assert d.workflow_status(tmp_path)["phase"] == "needs_specialist"
