#!/usr/bin/env python3
"""Scan and clean generated junk under the repository.

The cleaner is intentionally conservative: it auto-removes only allowlisted
generated files/directories. Possible-but-risky cleanup targets are reported for
review and never deleted by default.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Sequence, Set


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_SKILLS_ROOT = DEFAULT_REPO_ROOT / "skills"

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
    ".next",
    ".turbo",
    ".cache",
    "coverage",
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
)

SKILLS_ONLY_AUTO_FILE_PATTERNS = (
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


def git_tracked_paths(root: Path) -> Set[str]:
    """Return git-tracked files under root, relative to root.

    Cleanup may run against arbitrary temporary directories in tests or against
    folders outside a Git worktree. In those cases, tracked-file protection is
    simply disabled.
    """
    root = root.resolve()
    try:
        repo_root_raw = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return set()

    repo_root = Path(repo_root_raw).resolve()
    try:
        scan_rel = root.relative_to(repo_root)
    except ValueError:
        return set()

    pathspec = "." if scan_rel == Path(".") else scan_rel.as_posix()
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(repo_root), "ls-files", "-z", "--", pathspec],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()

    tracked: Set[str] = set()
    for item in raw.decode("utf-8", errors="surrogateescape").split("\0"):
        if not item:
            continue
        path = (repo_root / item).resolve()
        try:
            tracked.add(path.relative_to(root).as_posix())
        except ValueError:
            continue
    return tracked


def is_tracked_path(rel_path: str, tracked_paths: Set[str]) -> bool:
    return rel_path in tracked_paths


def contains_tracked_path(rel_path: str, tracked_paths: Set[str]) -> bool:
    prefix = rel_path.rstrip("/") + "/"
    return any(path == rel_path or path.startswith(prefix) for path in tracked_paths)


def is_auto_file(path: Path, *, repo_mode: bool = False) -> bool:
    name = path.name
    if name in AUTO_FILE_NAMES or any(fnmatch.fnmatch(name, pat) for pat in AUTO_FILE_PATTERNS):
        return True
    if not repo_mode and any(fnmatch.fnmatch(name, pat) for pat in SKILLS_ONLY_AUTO_FILE_PATTERNS):
        return True
    return False


def is_repo_review_file(path: Path, *, repo_mode: bool = False) -> bool:
    return repo_mode and any(fnmatch.fnmatch(path.name, pat) for pat in SKILLS_ONLY_AUTO_FILE_PATTERNS)


def has_placeholder_skill_text(path: Path) -> bool:
    if path.name != "SKILL.md":
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def scan(
    root: Path,
    *,
    include_empty_dirs: bool = False,
    repo_mode: bool = False,
    tracked_paths: Set[str] | None = None,
) -> List[Candidate]:
    root = root.resolve()
    candidates: List[Candidate] = []
    seen: Set[Path] = set()
    tracked_paths = git_tracked_paths(root) if tracked_paths is None else tracked_paths

    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: List[str] = []
        for dirname in dirs:
            path = current_path / dirname
            if dirname in AUTO_DIR_NAMES:
                rel_path = relative(path, root)
                has_tracked = contains_tracked_path(rel_path, tracked_paths)
                candidates.append(
                    Candidate(
                        path=rel_path,
                        kind="tracked-generated-dir" if has_tracked else "generated-dir",
                        reason=(
                            f"generated cache directory `{dirname}` contains tracked files; review before deleting"
                            if has_tracked
                            else f"generated cache directory `{dirname}`"
                        ),
                        bytes=disk_usage(path),
                        auto_clean=not has_tracked,
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
            if is_auto_file(path, repo_mode=repo_mode):
                rel_path = relative(path, root)
                is_tracked = is_tracked_path(rel_path, tracked_paths)
                candidates.append(
                    Candidate(
                        path=rel_path,
                        kind="tracked-generated-file" if is_tracked else "generated-file",
                        reason=(
                            "generated/temp/backup file is tracked by git; review before deleting"
                            if is_tracked
                            else "generated/temp/backup file matched cleanup allowlist"
                        ),
                        bytes=disk_usage(path),
                        auto_clean=not is_tracked,
                    )
                )
                seen.add(path.resolve())
            elif is_repo_review_file(path, repo_mode=repo_mode):
                candidates.append(
                    Candidate(
                        path=relative(path, root),
                        kind="review-log-file",
                        reason="log file in repository scan; review before deleting because logs can be production evidence",
                        bytes=disk_usage(path),
                        auto_clean=False,
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


def summary_for(candidates: Sequence[Candidate], *, cleaned: int = 0, saved_bytes: int = 0) -> dict:
    auto = [c for c in candidates if c.auto_clean]
    review = [c for c in candidates if not c.auto_clean]
    total = sum(c.bytes for c in candidates)
    auto_total = sum(c.bytes for c in auto)
    review_total = sum(c.bytes for c in review)
    return {
        "candidates": len(candidates),
        "auto_clean": len(auto),
        "review": len(review),
        "bytes": total,
        "auto_bytes": auto_total,
        "review_bytes": review_total,
        "cleaned": cleaned,
        "saved_bytes": saved_bytes,
    }


def print_human(candidates: Sequence[Candidate], *, cleaned: int = 0, saved_bytes: int = 0) -> None:
    summary = summary_for(candidates, cleaned=cleaned, saved_bytes=saved_bytes)
    print(
        f"candidates={summary['candidates']} "
        f"auto_clean={summary['auto_clean']} "
        f"review={summary['review']} "
        f"bytes={human_size(summary['bytes'])} "
        f"auto_bytes={human_size(summary['auto_bytes'])} "
        f"review_bytes={human_size(summary['review_bytes'])}"
    )
    if cleaned:
        print(f"cleaned={cleaned} saved={human_size(saved_bytes)}")
    for c in candidates:
        flag = "AUTO" if c.auto_clean else "REVIEW"
        print(f"{flag:6} {human_size(c.bytes):>8} {c.kind:24} {c.path} - {c.reason}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan/clean generated junk under skills/ or the whole repository.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("scan", "clean"):
        p = sub.add_parser(name)
        p.add_argument("root", nargs="?", help="root to scan; default: repository skills/ unless --repo is set")
        p.add_argument("--repo", action="store_true", help="scan the whole repository root instead of only skills/")
        p.add_argument("--include-empty-dirs", action="store_true", help="include empty directories as auto-clean candidates")
        p.add_argument("--json", action="store_true", help="emit JSON")

    return parser


def resolve_root(ns: argparse.Namespace) -> Path:
    if ns.root:
        return Path(ns.root).resolve()
    return (DEFAULT_REPO_ROOT if ns.repo else DEFAULT_SKILLS_ROOT).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    root = resolve_root(ns)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    candidates = scan(root, include_empty_dirs=ns.include_empty_dirs, repo_mode=ns.repo)
    cleaned = 0
    saved_bytes = 0
    if ns.command == "clean":
        for candidate in candidates:
            if candidate.auto_clean:
                saved_bytes += candidate.bytes
                remove_candidate(root, candidate)
                cleaned += 1
        if ns.include_empty_dirs:
            existing = {c.path for c in candidates}
            for candidate in scan(root, include_empty_dirs=True, repo_mode=ns.repo):
                if candidate.kind == "empty-dir" and candidate.path not in existing:
                    saved_bytes += candidate.bytes
                    remove_candidate(root, candidate)
                    candidates.append(candidate)
                    existing.add(candidate.path)
                    cleaned += 1

    if ns.json:
        payload = {
            "root": str(root),
            "command": ns.command,
            "cleaned": cleaned,
            "saved_bytes": saved_bytes,
            "summary": summary_for(candidates, cleaned=cleaned, saved_bytes=saved_bytes),
            "candidates": [asdict(c) for c in candidates],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(candidates, cleaned=cleaned, saved_bytes=saved_bytes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
