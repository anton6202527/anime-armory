#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detect high-risk bare imports in novel runtime scripts.

The novel family keeps `skills/novel-craft/scripts/contract.py` as a compatibility
shim, but runtime code should import the unique implementation module
`novel_contract` from `skills/novel/_lib`.  Bare `import contract` can resolve to
the wrong module when another skill injects its scripts directory into sys.path.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SKILLS = REPO / "skills"
FORBIDDEN = re.compile(r"^\s*(?:from\s+contract\s+import\b|import\s+contract\b)")


def _is_novel_runtime(path: Path) -> bool:
    try:
        rel = path.relative_to(SKILLS)
    except ValueError:
        return False
    if not rel.parts:
        return False
    skill = rel.parts[0]
    if skill != "novel" and not skill.startswith("novel-"):
        return False
    if path.name == "contract.py":
        return False
    if path.name.startswith("test_") or "tests" in rel.parts:
        return False
    return path.suffix == ".py"


def check_novel_import_shadowing() -> list[str]:
    bad: list[str] = []
    for path in sorted(SKILLS.rglob("*.py")):
        if not _is_novel_runtime(path):
            continue
        for line_no, line in enumerate(path.read_text("utf-8", "ignore").splitlines(), 1):
            if FORBIDDEN.search(line):
                rel = path.relative_to(REPO)
                bad.append(
                    f"{rel}:{line_no}: runtime bare contract import shadows novel/_lib/novel_contract.py"
                )
    return bad


def main() -> int:
    violations = check_novel_import_shadowing()
    if violations:
        print("❌ novel import-shadowing: runtime bare contract imports found")
        for item in violations:
            print(f"    - {item}")
        return 1
    print("✅ novel import-shadowing: no runtime bare contract imports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
