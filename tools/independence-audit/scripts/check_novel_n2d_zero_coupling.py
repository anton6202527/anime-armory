#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strict zero-coupling audit for the novel and n2d skill families."""
from __future__ import annotations

import os
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SELF = Path(__file__).resolve()

NOVEL_FORBIDDEN = (
    "n2d",
    "N2D",
    "_n2d",
    "asset_registry_preflight",
    "n2d_ready",
    "n2d-ready",
    "n2d-readiness",
    "n2d-asset",
    "n2d-adapt",
    "N2D_GENRE_LEDGER",
    "n2d-feedback",
)

N2D_FORBIDDEN = (
    "写小说",
    "skills/novel",
    "novel-craft",
    "novel-review",
    "novel-score",
    "novel-progress-schema",
    "_n2d_handoff",
    "novel→n2d",
)

ROOT_FORBIDDEN = (
    "novel 导出 n2d",
    "导出 n2d",
    "n2d handoff",
    "n2d-ready",
    "n2d-adapt",
    "asset_registry_preflight",
    "novel→n2d",
    "写小说导出",
    "n2d 源书",
    "n2d-feedback genre ledger read by novel-score",
)

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
}


def iter_text_files(paths: list[Path]):
    for root in paths:
        if root.is_file():
            candidates = [root]
        elif root.is_dir():
            candidates = [p for p in root.rglob("*") if p.is_file()]
        else:
            continue
        for path in candidates:
            if path == SELF:
                continue
            if any(part in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"} for part in path.parts):
                continue
            if path.suffix not in TEXT_SUFFIXES:
                continue
            yield path


def line_hits(path: Path, forbidden: tuple[str, ...]):
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for lineno, line in enumerate(text.splitlines(), 1):
        hits = [token for token in forbidden if token in line]
        if hits:
            yield lineno, hits, line.strip()


def roots_for(prefix: str) -> list[Path]:
    roots: list[Path] = []
    skills = REPO / "skills"
    roots.append(skills / prefix)
    roots.extend(sorted(p for p in skills.glob(f"{prefix}-*") if p.is_dir()))
    return roots


def main() -> int:
    failures: list[str] = []

    groups = [
        ("novel family must not reference n2d handoff terms", roots_for("novel"), NOVEL_FORBIDDEN),
        ("n2d family must not reference novel implementation or source handoff terms", roots_for("n2d"), N2D_FORBIDDEN),
        (
            "entry docs must not describe novel/n2d handoffs",
            [
                REPO / "AGENTS.md",
                REPO / "skills" / "README.md",
                REPO / "docs" / "skill-design-principles.md",
                REPO / "tools" / "independence-audit" / "SKILL.md",
            ],
            ROOT_FORBIDDEN,
        ),
    ]

    for label, paths, forbidden in groups:
        for path in iter_text_files(paths):
            rel = path.relative_to(REPO)
            for lineno, hits, line in line_hits(path, forbidden):
                failures.append(f"{label}: {rel}:{lineno}: {', '.join(hits)} :: {line}")

    if failures:
        print("novel/n2d zero-coupling audit failed:", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("novel/n2d zero-coupling audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
