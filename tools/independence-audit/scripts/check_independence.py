#!/usr/bin/env python3
"""Audit skill series independence.

This is intentionally a static, conservative check. It blocks active references
to the removed shared layer and code-level coupling between skill series. It
does not block prose that describes optional file/data handoffs.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SERIES = ("ad", "mv", "n2d", "song")
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

# File-level exceptions for deliberate product handoffs. These should never be
# Python imports of another series; they are file/media/JSONL contracts only.
ALLOWED_CODE_HANDOFFS = {
    ("song", "mv", "skills/song-craft/scripts/init_project.py"),
}


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


def other_series_reference(line: str, other: str) -> bool:
    patterns = (
        rf"skills/{re.escape(other)}(?:/|-)",
        rf"\.\./{re.escape(other)}(?:/|-)",
        rf"['\"]{re.escape(other)}(?:-[A-Za-z0-9_]+)?['\"]",
        rf"\b{re.escape(other)}-[A-Za-z0-9_]+\b",
    )
    return any(re.search(pattern, line) for pattern in patterns)


def is_hard_coupling(line: str) -> bool:
    return any(marker in line for marker in HARD_COUPLING_MARKERS)


def check_file(path: Path, root: Path, strict_docs: bool) -> list[Issue]:
    issues: list[Issue] = []
    owner = series_for_path(path, root)
    relative = rel(path, root)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return issues

    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        if any(pattern.search(line) for pattern in COMMON_PATTERNS) and not is_historical_common(line):
            issues.append(
                Issue(relative, line_no, "legacy-common", "active reference to removed shared layer", stripped)
            )

        if owner and path.suffix in CODE_SUFFIXES:
            for other in SERIES:
                if other == owner:
                    continue
                if not other_series_reference(line, other):
                    continue
                allowed = (owner, other, relative) in ALLOWED_CODE_HANDOFFS
                if is_hard_coupling(line) and not allowed:
                    issues.append(
                        Issue(relative, line_no, "cross-series-code", f"{owner} code references {other}", stripped)
                    )

        if strict_docs and owner and path.suffix == ".md":
            for other in SERIES:
                if other == owner:
                    continue
                if other_series_reference(line, other):
                    issues.append(
                        Issue(relative, line_no, "cross-series-doc", f"{owner} docs reference {other}", stripped)
                    )

    return issues


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="check skill series independence")
    parser.add_argument("--strict-docs", action="store_true", help="also fail on cross-series prose references")
    args = parser.parse_args(argv)

    root = repo_root()
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
