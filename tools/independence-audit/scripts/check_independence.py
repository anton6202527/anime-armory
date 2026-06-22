#!/usr/bin/env python3
"""Audit skill series independence.

This is a static check. It blocks active references to the removed shared layer
and code-level coupling between skill series, and — by default — also blocks
cross-series prose inside per-series docs (strict-docs). Pass --lenient-docs to
drop the prose gate and only enforce code-level independence.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SERIES = ("ad", "mv", "n2d", "novel", "song")
SERIES_ROOT_LABELS = {
    "ad": ("拍广告",),
    "mv": ("制MV",),
    "n2d": ("制漫剧",),
    "novel": ("写小说",),
    "song": ("写歌",),
}
TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".txt"}
CODE_SUFFIXES = {".py", ".sh"}

COMMON_PATTERNS = (
    re.compile(r"skills/common(?:/|\b)"),
    re.compile(r"\bcommon/[A-Za-z0-9_-]+\.py\b"),
    re.compile(r"\bcommon/(?:n2d|voice|subtitle)[A-Za-z0-9_/-]*\b"),
    re.compile(r"\bcommon/settings\.py\b"),
)
HISTORICAL_COMMON_MARKERS = (
    "deleted",
    "removed",
    "former",
    "legacy",
    "forbidden",
    "forbid",
    "已删除",
    "删除",
    "拆除",
    "不存在",
    "不依赖",
    "阻断",
    "禁止",
    "原 `skills/common",
)

HARD_COUPLING_MARKERS = (
    "sys.path",
    "importlib",
    "load_script",
    "subprocess",
    "python3 skills/",
    "bash skills/",
    "os.path.join",
    "shutil.copy",
)

SERIES_SKILL_NAMES: dict[str, tuple[str, ...]] = {}


@dataclass(frozen=True)
class Issue:
    path: str
    line_no: int
    kind: str
    message: str
    text: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def series_for_path(path: Path, root: Path) -> str | None:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return None
    if len(parts) < 2 or parts[0] != "skills":
        return None
    top = parts[1]
    for series in SERIES:
        if top == series or top.startswith(series + "-"):
            return series
    return None


def iter_text_files(root: Path) -> Iterable[Path]:
    roots = [root / "AGENTS.md", root / "README.md", root / "skills"]
    for start in roots:
        if start.is_file():
            yield start
            continue
        for path in start.rglob("*"):
            if "__pycache__" in path.parts:
                continue
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                yield path


def is_historical_common(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered or marker in line for marker in HISTORICAL_COMMON_MARKERS)


def discover_series_skill_names(root: Path) -> dict[str, tuple[str, ...]]:
    names: dict[str, list[str]] = {series: [] for series in SERIES}
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return {series: () for series in SERIES}
    for path in skills_dir.iterdir():
        if not path.is_dir():
            continue
        top = path.name
        for series in SERIES:
            if top == series or top.startswith(series + "-"):
                # Bare "song"/"novel"/"ad"/"mv" are also domain nouns, file
                # fields, variable names, or shell commands. Treat the bare
                # dispatcher name as a cross-series token only for n2d, whose
                # spelling is not a normal production noun in this repo.
                if top != series or series == "n2d":
                    names[series].append(top)
                break
    return {series: tuple(sorted(items, key=len, reverse=True)) for series, items in names.items()}


def other_series_reference(line: str, other: str) -> bool:
    skill_names = SERIES_SKILL_NAMES.get(other, ())
    patterns = (
        rf"skills/{re.escape(other)}(?:/|-)",
        rf"\.\./{re.escape(other)}(?:/|-)",
        rf"\b{re.escape(other)}-\*(?![A-Za-z0-9_])",
        rf"\b{re.escape(other)}\s*(?:线|系列|家族)",
        rf"(?:交|给|转|推给|调用|跑|进入)\s*(?:[*_`]*\s*){re.escape(other)}(?:\s*[*_`]*)(?:\s|做|产|审|质检|$)",
    )
    if any(re.search(pattern, line) for pattern in patterns):
        return True
    return any(
        re.search(rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])", line)
        for name in skill_names
    )


def other_root_reference(line: str, other: str) -> bool:
    return any(label in line for label in SERIES_ROOT_LABELS[other])


def is_hard_coupling(line: str) -> bool:
    return any(marker in line for marker in HARD_COUPLING_MARKERS)


def check_file(path: Path, root: Path, strict_docs: bool) -> list[Issue]:
    issues: list[Issue] = []
    if not SERIES_SKILL_NAMES:
        SERIES_SKILL_NAMES.update(discover_series_skill_names(root))
    owner = series_for_path(path, root)
    relative = rel(path, root)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return issues

    in_block_comment = False
    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        code_prose = False
        if path.suffix in CODE_SUFFIXES:
            code_prose = in_block_comment or stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''")

        if any(pattern.search(line) for pattern in COMMON_PATTERNS) and not is_historical_common(line):
            issues.append(
                Issue(relative, line_no, "legacy-common", "active reference to removed shared layer", stripped)
            )

        if owner and path.suffix in CODE_SUFFIXES:
            for other in SERIES:
                if other == owner:
                    continue
                has_series_ref = other_series_reference(line, other)
                has_root_ref = other_root_reference(line, other)
                if not has_series_ref and not has_root_ref:
                    continue
                if is_hard_coupling(line) or has_root_ref or code_prose or has_series_ref:
                    issues.append(
                        Issue(relative, line_no, "cross-series-code", f"{owner} code references {other}", stripped)
                    )

        if strict_docs and owner and path.suffix == ".md":
            for other in SERIES:
                if other == owner:
                    continue
                if other_series_reference(line, other) or other_root_reference(line, other):
                    issues.append(
                        Issue(relative, line_no, "cross-series-doc", f"{owner} docs reference {other}", stripped)
                    )

        if path.suffix in CODE_SUFFIXES:
            quote_count = stripped.count('"""') + stripped.count("'''")
            if quote_count % 2 == 1:
                in_block_comment = not in_block_comment

    return issues


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="check skill series independence")
    # strict-docs is the enforced default; cross-series prose in per-series docs fails.
    parser.add_argument(
        "--lenient-docs",
        dest="strict_docs",
        action="store_false",
        help="only enforce code-level independence; allow cross-series prose in docs",
    )
    # Accepted for backward compatibility — strict-docs is already the default.
    parser.add_argument("--strict-docs", dest="strict_docs", action="store_true", help=argparse.SUPPRESS)
    parser.set_defaults(strict_docs=True)
    args = parser.parse_args(argv)

    root = repo_root()
    SERIES_SKILL_NAMES.update(discover_series_skill_names(root))
    all_issues: list[Issue] = []
    files_checked = 0
    for path in iter_text_files(root):
        files_checked += 1
        all_issues.extend(check_file(path, root, strict_docs=args.strict_docs))

    if all_issues:
        for issue in all_issues:
            print(f"{issue.path}:{issue.line_no}: {issue.kind}: {issue.message}", file=sys.stderr)
            print(f"  {issue.text}", file=sys.stderr)
        print(f"\nindependence audit failed: {len(all_issues)} issue(s)", file=sys.stderr)
        return 1

    print(f"independence audit passed: {files_checked} files checked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
