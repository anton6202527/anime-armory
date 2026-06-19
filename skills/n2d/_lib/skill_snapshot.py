#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared file snapshot and diffing library for Anime Armory skills.

Provides stable, unified methods to track skill file changes, compute hashes,
and compare states against a baseline to determine if a rebuild is needed.

交付铁律：本库**不依赖任何版本控制**。变更检测完全基于文件内容快照（SHA256），
用户端无需 git/任何 VCS——直接读文件内容算 hash 比对即可，中文路径天然无障碍。
"""

import datetime as dt
import hashlib
import json
import os
from typing import Any, Dict, Iterable, List, Optional

TEXT_EXTS = {
    ".md", ".py", ".json", ".yaml", ".yml", ".txt", ".sh", ".js", ".ts",
    ".toml", ".cfg", ".ini", ".csv",
}
# 点开头目录（含任何 VCS 元数据目录）已被 os.walk 里的 `d.startswith(".")` 跳过。
SKIP_DIRS = {"__pycache__", "node_modules", "tests"}


def is_test_path(path: str) -> bool:
    """测试文件不影响 skill 运行时行为，不计入重制指纹。"""
    name = os.path.basename(path)
    return name == "conftest.py" or (name.startswith("test_") and name.endswith(".py"))

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
            if is_test_path(name):
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


def artifact_fingerprint(base_dir: str, rel_paths: Iterable[str]) -> Dict[str, Any]:
    """Content fingerprint over a set of production input files, for report freshness.

    A QC/contract report stamps this over the inputs it actually read; a later
    consumer (n2d-update) re-hashes the same file list to tell whether the report
    still describes the current artifacts. Missing files hash as None so a later
    add/delete flips the combined sha. Same git-free SHA256 ethos as the skill
    snapshot — works on the user's machine with no VCS and Chinese paths.

    Returns {"files": {rel: sha|None}, "sha": <combined>}; rel paths are relative
    to base_dir (typically 作品根), normalized to forward slashes.
    """
    files: Dict[str, Optional[str]] = {}
    h = hashlib.sha256()
    for rel in sorted({str(r).replace(os.sep, "/") for r in rel_paths}):
        path = os.path.join(base_dir, rel)
        digest = file_sha256(path) if os.path.isfile(path) else None
        files[rel] = digest
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update((digest or "-").encode("ascii"))
        h.update(b"\n")
    return {"files": files, "sha": h.hexdigest()}


def fingerprint_is_fresh(recorded: Optional[Dict[str, Any]], base_dir: str) -> Optional[bool]:
    """Recompute over a recorded fingerprint's own file list and compare its sha.

    True = fresh (inputs unchanged since the report), False = stale (inputs changed),
    None = unknown (the report carried no usable `inputs_fingerprint`). Decoupled by
    design: the consumer trusts the producer's declared input list and only re-verifies
    that those files still hash to the same combined sha.
    """
    if not isinstance(recorded, dict):
        return None
    files = recorded.get("files")
    sha = recorded.get("sha")
    if not isinstance(files, dict) or not isinstance(sha, str) or not sha:
        return None
    return artifact_fingerprint(base_dir, list(files.keys()))["sha"] == sha
