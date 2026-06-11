#!/usr/bin/env python3
"""Scan and clean generated junk under the repository skills/ tree.

The cleaner is intentionally conservative: it auto-removes only allowlisted
generated files/directories. Possible-but-risky cleanup targets are reported for
review and never deleted by default.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Sequence, Set


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SKILLS_ROOT = SCRIPT_DIR.parents[1]

AUTO_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
}

REVIEW_DIR_NAMES = {
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
}

AUTO_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".coverage",
}

AUTO_FILE_PATTERNS = (
    "*.pyc",
    "*.pyo",
    "*~",
    "*.bak",
    "*.orig",
    "*.tmp",
    "*.swp",
    "*.swo",
    "*.log",
)

PLACEHOLDER_MARKERS = (
    "[TODO:",
    "TODO: Complete and informative explanation",
    "Delete this entire \"Structuring This Skill\" section",
    "## [TODO: Replace with the first main section",
)


@dataclass(frozen=True)
class Candidate:
    path: str
    kind: str
    reason: str
    bytes: int
    auto_clean: bool


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def disk_usage(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for current, dirs, files in os.walk(path, topdown=True, followlinks=False):
        dirs[:] = [d for d in dirs if not Path(current, d).is_symlink()]
        for name in files:
            item = Path(current, name)
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def is_auto_file(path: Path) -> bool:
    name = path.name
    return name in AUTO_FILE_NAMES or any(fnmatch.fnmatch(name, pat) for pat in AUTO_FILE_PATTERNS)


def has_placeholder_skill_text(path: Path) -> bool:
    if path.name != "SKILL.md":
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def scan(root: Path, *, include_empty_dirs: bool = False) -> List[Candidate]:
    root = root.resolve()
    candidates: List[Candidate] = []
    seen: Set[Path] = set()

    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: List[str] = []
        for dirname in dirs:
            path = current_path / dirname
            if dirname in AUTO_DIR_NAMES:
                candidates.append(
                    Candidate(
                        path=relative(path, root),
                        kind="generated-dir",
                        reason=f"generated cache directory `{dirname}`",
                        bytes=disk_usage(path),
                        auto_clean=True,
                    )
                )
                seen.add(path.resolve())
                continue
            if dirname in REVIEW_DIR_NAMES:
                candidates.append(
                    Candidate(
                        path=relative(path, root),
                        kind="review-dir",
                        reason=f"large/local dependency or build directory `{dirname}`; review before deleting",
                        bytes=disk_usage(path),
                        auto_clean=False,
                    )
                )
                seen.add(path.resolve())
                continue
            if dirname.startswith(".git"):
                continue
            kept_dirs.append(dirname)
        dirs[:] = kept_dirs

        for filename in files:
            path = current_path / filename
            if path.is_symlink():
                continue
            if is_auto_file(path):
                candidates.append(
                    Candidate(
                        path=relative(path, root),
                        kind="generated-file",
                        reason="generated/temp/backup file matched cleanup allowlist",
                        bytes=disk_usage(path),
                        auto_clean=True,
                    )
                )
                seen.add(path.resolve())
            elif has_placeholder_skill_text(path):
                skill_dir = path.parent
                resolved = skill_dir.resolve()
                if resolved not in seen:
                    candidates.append(
                        Candidate(
                            path=relative(skill_dir, root),
                            kind="review-placeholder-skill",
                            reason="SKILL.md still contains scaffold TODO text; decide keep/finish/delete manually",
                            bytes=disk_usage(skill_dir),
                            auto_clean=False,
                        )
                    )
                    seen.add(resolved)

    if include_empty_dirs:
        for current, dirs, files in os.walk(root, topdown=False, followlinks=False):
            path = Path(current)
            if path == root:
                continue
            if path.resolve() in seen:
                continue
            try:
                is_empty = not any(path.iterdir())
            except OSError:
                is_empty = False
            if is_empty:
                candidates.append(
                    Candidate(
                        path=relative(path, root),
                        kind="empty-dir",
                        reason="empty directory",
                        bytes=0,
                        auto_clean=True,
                    )
                )
                seen.add(path.resolve())

    return sorted(candidates, key=lambda c: (not c.auto_clean, c.kind, c.path))


def remove_candidate(root: Path, candidate: Candidate) -> None:
    path = root / candidate.path
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def human_size(num: int) -> str:
    value = float(num)
    for unit in ("B", "K", "M", "G"):
        if value < 1024 or unit == "G":
            if unit == "B":
                return f"{int(value)}B"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}G"


def print_human(candidates: Sequence[Candidate], *, cleaned: int = 0) -> None:
    auto = [c for c in candidates if c.auto_clean]
    review = [c for c in candidates if not c.auto_clean]
    total = sum(c.bytes for c in candidates)
    auto_total = sum(c.bytes for c in auto)
    print(f"candidates={len(candidates)} auto_clean={len(auto)} review={len(review)} bytes={human_size(total)} auto_bytes={human_size(auto_total)}")
    if cleaned:
        print(f"cleaned={cleaned}")
    for c in candidates:
        flag = "AUTO" if c.auto_clean else "REVIEW"
        print(f"{flag:6} {human_size(c.bytes):>8} {c.kind:24} {c.path} - {c.reason}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan/clean generated junk under skills/.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("scan", "clean"):
        p = sub.add_parser(name)
        p.add_argument("root", nargs="?", default=str(DEFAULT_SKILLS_ROOT), help="skills root; default: repository skills/")
        p.add_argument("--include-empty-dirs", action="store_true", help="include empty directories as auto-clean candidates")
        p.add_argument("--json", action="store_true", help="emit JSON")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    root = Path(ns.root).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    candidates = scan(root, include_empty_dirs=ns.include_empty_dirs)
    cleaned = 0
    if ns.command == "clean":
        for candidate in candidates:
            if candidate.auto_clean:
                remove_candidate(root, candidate)
                cleaned += 1
        if ns.include_empty_dirs:
            existing = {c.path for c in candidates}
            for candidate in scan(root, include_empty_dirs=True):
                if candidate.kind == "empty-dir" and candidate.path not in existing:
                    remove_candidate(root, candidate)
                    candidates.append(candidate)
                    existing.add(candidate.path)
                    cleaned += 1

    if ns.json:
        payload = {
            "root": str(root),
            "command": ns.command,
            "cleaned": cleaned,
            "candidates": [asdict(c) for c in candidates],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(candidates, cleaned=cleaned)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
