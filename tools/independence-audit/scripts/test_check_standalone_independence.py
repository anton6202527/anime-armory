from __future__ import annotations

from pathlib import Path

from check_independence import check_file, owner_for_path


def make_standalone(tmp_path: Path, name: str = "n2d-solo") -> Path:
    root = tmp_path
    skill = root / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n", encoding="utf-8")
    return skill


def test_top_level_prefixed_skill_is_standalone(tmp_path: Path) -> None:
    skill = make_standalone(tmp_path)
    script = skill / "scripts" / "run.py"
    script.parent.mkdir()
    script.write_text("print('standalone')\n", encoding="utf-8")
    assert owner_for_path(script, tmp_path) == "standalone:n2d-solo"
    assert check_file(script, tmp_path, strict_docs=True) == []


def test_standalone_executable_cannot_call_series(tmp_path: Path) -> None:
    skill = make_standalone(tmp_path)
    script = skill / "scripts" / "run.py"
    script.parent.mkdir()
    script.write_text("# python3 skills/n2d/run.py next\n", encoding="utf-8")
    issues = check_file(script, tmp_path, strict_docs=True)
    assert any(issue.kind == "cross-series-code" for issue in issues)


def test_standalone_docs_may_name_reference_series(tmp_path: Path) -> None:
    skill = make_standalone(tmp_path)
    doc = skill / "SKILL.md"
    doc.write_text(
        "---\nname: n2d-solo\ndescription: test\n---\nCan learn concepts from n2d but stays independent.\n",
        encoding="utf-8",
    )
    assert check_file(doc, tmp_path, strict_docs=True) == []
