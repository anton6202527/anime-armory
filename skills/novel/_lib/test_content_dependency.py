from __future__ import annotations

from pathlib import Path

from content_dependency import build_graph, invalidation_plan


def _project(root: Path) -> None:
    for folder in ("章节", "审稿", "评分", "修订", "导出", "设定"):
        (root / folder).mkdir()
    for number in (1, 2, 3):
        (root / f"章节/第{number:02d}章.md").write_text(f"# 第{number}章", encoding="utf-8")
        (root / f"审稿/state_delta_第{number:02d}章.json").write_text("{}", encoding="utf-8")
    for path in ("审稿/review_report.json", "评分/score_report.json", "修订/revision_plan.json"):
        (root / path).write_text("{}", encoding="utf-8")
    (root / "导出/book.txt").write_text("book", encoding="utf-8")


def test_semantic_chapter_change_reaches_later_chapters_and_release(tmp_path: Path) -> None:
    _project(tmp_path)
    graph = build_graph(tmp_path)
    plan = invalidation_plan(graph, ["章节/第01章.md"], change_kind="semantic")
    assert "章节/第02章.md" in plan["affected"]
    assert "审稿/review_report.json" in plan["affected"]
    assert "导出/release_manifest.json" in plan["affected"]


def test_prose_only_change_does_not_invalidate_state_or_later_chapters(tmp_path: Path) -> None:
    _project(tmp_path)
    graph = build_graph(tmp_path)
    plan = invalidation_plan(graph, ["章节/第01章.md"], change_kind="prose_only")
    assert "章节/第02章.md" not in plan["affected"]
    assert "审稿/state_delta_第01章.json" not in plan["affected"]
    assert "导出/book.txt" in plan["affected"]
