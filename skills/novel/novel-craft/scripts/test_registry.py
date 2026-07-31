#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Novel skill registry sync tests.

Can run without pytest:
    python3 skills/novel/novel-craft/scripts/test_registry.py
"""
import os
import re
import unittest

import registry


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SKILLS = os.path.join(REPO, "skills")


def read(relpath):
    with open(os.path.join(REPO, relpath), encoding="utf-8") as f:
        return f.read()


def actual_novel_skills():
    line_root = os.path.join(SKILLS, "novel")
    names = {"novel"} if os.path.isfile(os.path.join(line_root, "SKILL.md")) else set()
    names.update(
        name for name in os.listdir(line_root)
        if name.startswith("novel-")
        and os.path.isfile(os.path.join(line_root, name, "SKILL.md"))
    )
    return names


def referenced_novel_skills(text):
    return set(re.findall(r"`(novel(?:-[a-z-]+)?)(?:/[^`]*)?`", text))


class NovelRegistryTest(unittest.TestCase):
    def test_author_and_readme_match_actual_novel_skills(self):
        actual = actual_novel_skills()
        expected = set(registry.skill_names())
        author = referenced_novel_skills(read("skills/novel/SKILL.md"))
        readme = referenced_novel_skills(read("skills/README.md"))
        self.assertEqual(expected, actual)
        self.assertEqual(author, expected)
        self.assertEqual(readme, expected)


if __name__ == "__main__":
    unittest.main()
