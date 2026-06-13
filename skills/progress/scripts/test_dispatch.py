# -*- coding: utf-8 -*-
"""Run from repo root: python3 -m pytest skills/progress/scripts/test_dispatch.py."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dispatch


def make_project(repo, line, name="某作品", nested=None):
    root = repo / dispatch.LINE_ROOTS[line] / name
    root.mkdir(parents=True)
    (root / "_进度.md").write_text("# 进度\n", encoding="utf-8")
    if nested:
        child = root.joinpath(*nested)
        child.mkdir(parents=True)
        return root, child
    return root, root


def test_nested_context_resolves_nearest_project_root(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    project, child = make_project(repo, "song", nested=("词",))
    calls = []

    monkeypatch.setattr(dispatch, "REPO", str(repo))
    monkeypatch.setattr(dispatch, "run_line", lambda line, root, limit=None: calls.append((line, root, limit)) or 0)

    assert dispatch.main([str(child)]) == 0
    assert calls == [("song", str(project), None)]


def test_file_context_resolves_parent_project_root(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    project, _ = make_project(repo, "mv", nested=("字幕",))
    progress_file = project / "_进度.md"
    calls = []

    monkeypatch.setattr(dispatch, "REPO", str(repo))
    monkeypatch.setattr(dispatch, "run_line", lambda line, root, limit=None: calls.append((line, root, limit)) or 0)

    assert dispatch.main([str(progress_file)]) == 0
    assert calls == [("mv", str(project), None)]


def test_line_root_progress_file_is_not_treated_as_project_root(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    line_root = repo / dispatch.LINE_ROOTS["n2d"]
    line_root.mkdir(parents=True)
    (line_root / "_进度.md").write_text("# wrong level\n", encoding="utf-8")

    monkeypatch.setattr(dispatch, "REPO", str(repo))

    assert dispatch.resolve_project_root(str(line_root), "n2d") is None


def test_external_context_does_not_climb_unbounded_to_unrelated_progress(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    (outside / "a" / "b" / "c" / "d").mkdir(parents=True)
    (outside / "_进度.md").write_text("# unrelated\n", encoding="utf-8")

    monkeypatch.setattr(dispatch, "REPO", str(repo))

    child = outside / "a" / "b" / "c" / "d"
    assert dispatch.resolve_project_root(str(child), "ad", max_external_ascents=2) is None
    assert dispatch.resolve_project_root(str(child), "ad", max_external_ascents=5) == str(outside)


def test_limit_is_only_converted_for_compatible_line_scripts():
    assert dispatch.line_args("novel", 2) == ["--limit", "2"]
    assert dispatch.line_args("song", 2) == ["--limit", "2"]
    assert dispatch.line_args("mv", 2) == ["--limit", "2"]
    assert dispatch.line_args("n2d", 2) == []
    assert dispatch.line_args("ad", 2) == []
    assert dispatch.line_args("song", None) == []


def test_aggregate_uses_dispatcher_limit_without_extra_child_args(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    n2d_project, _ = make_project(repo, "n2d", name="某剧")
    song_project, _ = make_project(repo, "song", name="某歌")
    calls = []

    monkeypatch.setattr(dispatch, "REPO", str(repo))
    monkeypatch.setattr(dispatch, "script_path", lambda line: __file__)
    monkeypatch.setattr(dispatch, "run_line", lambda line, root, limit=None: calls.append((line, root, limit)) or 0)

    assert dispatch.aggregate(("n2d", "song"), limit=1) == 0
    assert calls == [
        ("n2d", str(n2d_project), 1),
        ("song", str(song_project), 1),
    ]


def test_single_project_missing_script_returns_nonzero(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    project, _ = make_project(repo, "song")

    monkeypatch.setattr(dispatch, "REPO", str(repo))
    monkeypatch.setitem(dispatch.LINE_SCRIPTS, "song", "skills/missing/progress.py")

    assert dispatch.main([str(project)]) == 2


def test_aggregate_missing_script_reports_once_and_fails(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    make_project(repo, "song", name="歌A")
    make_project(repo, "song", name="歌B")

    monkeypatch.setattr(dispatch, "REPO", str(repo))
    monkeypatch.setitem(dispatch.LINE_SCRIPTS, "song", "skills/missing/progress.py")

    assert dispatch.aggregate(("song",)) == 1
    captured = capsys.readouterr()
    assert captured.err.count("尚未提供可调用的进度脚本") == 1


def test_unknown_extra_args_are_rejected(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    project, _ = make_project(repo, "novel")

    monkeypatch.setattr(dispatch, "REPO", str(repo))

    with pytest.raises(SystemExit) as exc:
        dispatch.main([str(project), "set", "draft", "done"])
    assert exc.value.code == 2
