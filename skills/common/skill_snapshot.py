#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared file snapshot and diffing library for Anime Armory skills.

Provides stable, unified methods to track skill file changes, compute hashes,
and compare states against a baseline to determine if a rebuild is needed.
"""

import datetime as dt
import hashlib
import json
import os
import subprocess
from typing import Any, Dict, Iterable, List, Optional

TEXT_EXTS = {
    ".md", ".py", ".json", ".yaml", ".yml", ".txt", ".sh", ".js", ".ts",
    ".toml", ".cfg", ".ini", ".csv",
}
SKIP_DIRS = {"__pycache__", "node_modules", ".git"}

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def iter_skill_files(skills_dir: str, skill: str) -> Iterable[str]:
    """Iterate through all trackable text files in a specific skill directory."""
    base = os.path.join(skills_dir, skill)
    if not os.path.isdir(base):
        return []
    files: List[str] = []
    for root, dirs, names in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in names:
            if name.startswith(".") or name.endswith(".pyc") or name.endswith(".vsix"):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext and ext not in TEXT_EXTS:
                continue
            path = os.path.join(root, name)
            if os.path.isfile(path):
                files.append(path)
    return sorted(files)

def snapshot_for_skills(repo_root: str, skills_dir: str, skills: Iterable[str]) -> Dict[str, Any]:
    """Take a SHA256 snapshot of all files across the given skills."""
    files: Dict[str, str] = {}
    for skill in sorted(set(skills)):
        for path in iter_skill_files(skills_dir, skill):
            rel_path = os.path.relpath(path, repo_root).replace(os.sep, "/")
            files[rel_path] = file_sha256(path)
    return {
        "created_at": now_iso(),
        "skills": sorted(set(skills)),
        "files": files,
    }

def changed_files_since(old: Optional[Dict[str, Any]], new: Dict[str, Any]) -> List[str]:
    """Compare an old snapshot with a new one and return changed file paths."""
    if not old:
        return []
    before = old.get("files") if isinstance(old.get("files"), dict) else {}
    after = new.get("files") if isinstance(new.get("files"), dict) else {}
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))

def git_changed_files(repo_root: str) -> List[str]:
    """Query git status for uncommitted changes in the skills directory."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo_root, "status", "--short", "--untracked-files=all"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    out: List[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path.startswith("skills/"):
            out.append(path)
    return sorted(set(out))
