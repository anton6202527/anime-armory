#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strict zero-coupling audit for the novel and n2d skill families."""
from __future__ import annotations

import os
import re
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
    "drama_source_handoff",
    "write_drama_handoff",
    "formats handoff",
    "改编源书交付包",
    "下游改编结构化交付包",
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
    "drama_source_handoff",
    "_novel_handoff",
    "check_novel_handoff",
    "parse_novel_ledger",
    "novel export",
    "novel 交付包",
    "novel 侧",
    "source\": \"novel",
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
    "drama_source_handoff",
    "_novel_handoff",
    "formats handoff",
    "改编源书交付包",
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
        hits = []
        for token in forbidden:
            # `n2d-adapt` 曾是耦合交接名；不要把合法的 adapter/adaptation
            # 文档或实现按子串误判成它。
            if token == "n2d-adapt":
                matched = re.search(r"(?<![\w-])n2d-adapt(?![\w-])", line) is not None
            else:
                matched = token in line
            if matched:
                hits.append(token)
        if hits:
            yield lineno, hits, line.strip()


_SYS_PATH_RE = re.compile(r"sys\.path\.(?:insert|append)\s*\(")


def check_no_cross_line_coload(repo: Path) -> list[str]:
    """Runtime-namespace guard: no single file may put BOTH the novel and the
    n2d line on ``sys.path`` in one interpreter.

    The two families deliberately vendor independent copies of same-named
    helpers (``settings``/``score``/``progress``/``scan``/``self_audit``/
    ``mechanical_check``/``consistency_audit``/``markdown_parser``/``text_utils``).
    Each is bare-imported (``import settings``), so resolution depends on
    ``sys.path[0]`` — safe under the one-process-per-skill invocation model.
    The ONLY way they could cross-shadow (``sys.modules['settings']`` cached
    from line A served to line B) is a single process that loads both lines.
    Within either family that can't happen — the forbidden-token groups above
    already ban a novel file from naming ``n2d`` and an n2d file from naming
    ``skills/novel``. This locks the remaining vector: a *neutral* file (tools/
    or a future top-level orchestrator) that sys.path-inserts both lines.
    Today 0 files do this; the guard keeps it that way.
    """
    failures: list[str] = []
    scan_roots = [repo / "skills", repo / "tools"]
    audit_dir = SELF.parent.parent  # tools/independence-audit/ — the auditor names both lines as subjects
    for path in iter_text_files(scan_roots):
        if path.suffix != ".py" or path == SELF:
            continue
        if audit_dir in path.parents:  # skip the independence-audit tool's own scripts/tests/probes
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        sys_path_lines = [ln for ln in text.splitlines() if _SYS_PATH_RE.search(ln)]
        if not sys_path_lines:
            continue
        blob = "\n".join(sys_path_lines)
        adds_n2d = bool(re.search(r"\bn2d\b|n2d[-_/]", blob))
        adds_novel = bool(re.search(r"\bnovel\b|novel[-_/]", blob))
        if adds_n2d and adds_novel:
            failures.append(
                f"cross-line co-load risk: {path.relative_to(repo)} puts both novel and "
                f"n2d dirs on sys.path — same-named vendored modules can cross-shadow via sys.modules")
    return failures


def roots_for(prefix: str) -> list[Path]:
    skills = REPO / "skills"
    line_root = skills / prefix
    roots = [line_root]
    # line_root 会递归覆盖当前嵌套子技能；保留旧扁平发现仅用于迁移期审计，
    # 避免尚未迁完的目录逃过零耦合检查。
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

    # Runtime-namespace guard: no neutral file may co-load both lines (shared
    # vendored basenames would cross-shadow via sys.modules in one interpreter).
    failures.extend(check_no_cross_line_coload(REPO))

    if failures:
        print("novel/n2d zero-coupling audit failed:", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("novel/n2d zero-coupling audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
