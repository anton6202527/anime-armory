#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

import validate_skills


def write_skill(root: Path, name: str, description: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def test_valid_skill_tree_passes(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    write_skill(skills, "demo", '"Demo skill."')
    (skills / "README.md").write_text("## Skills\n\n- `demo`\n", encoding="utf-8")

    findings = validate_skills.validate_tree(skills)

    assert [f for f in findings if f.severity == "error"] == []


def test_description_with_plain_colon_is_rejected(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    write_skill(skills, "bad", "Bad frontmatter: unquoted colon")
    (skills / "README.md").write_text("## Skills\n\n- `bad`\n", encoding="utf-8")

    findings = validate_skills.validate_tree(skills)

    assert any("frontmatter" in f.message or "YAML" in f.message for f in findings)


def test_readme_must_index_existing_skill(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    write_skill(skills, "missing", '"Missing from README."')
    (skills / "README.md").write_text("## Skills\n", encoding="utf-8")

    findings = validate_skills.validate_tree(skills)

    assert any("missing index entry for `missing`" == f.message for f in findings)
