#!/usr/bin/env python3
"""Canonical content fingerprints for n2d production contracts.

Callers decide which inputs belong to a contract.  This module is the single
definition of how that input set becomes a reusable hash: canonical JSON,
project-relative content hashes, explicit missing inputs, and glob membership.
"""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


KIND = "n2d_content_fingerprint"
VERSION = 1


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(root: Path, path: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"fingerprint input escapes project root: {path}") from exc


def _expand_pattern(root: Path, raw: str) -> list[Path]:
    pattern = str(raw or "").strip()
    if not pattern:
        return []
    candidate = Path(pattern)
    if candidate.is_absolute():
        _safe_relative(root, candidate)
        absolute_pattern = str(candidate)
    else:
        absolute_pattern = str(root / candidate)
    if any(token in absolute_pattern for token in ("*", "?", "[")):
        matches = [Path(item) for item in glob.glob(absolute_pattern, recursive=True)]
        return sorted((item for item in matches if item.is_file()), key=lambda item: item.as_posix())
    return [Path(absolute_pattern)]


def build_content_fingerprint(
    root: str | Path,
    *,
    source_patterns: Sequence[str | Path],
    values: Mapping[str, Any] | None = None,
    scope: str = "production_input",
) -> Dict[str, Any]:
    """Return a self-describing and recomputable content fingerprint."""
    project_root = Path(root).expanduser().resolve()
    patterns = [str(item) for item in source_patterns]
    files: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for raw in patterns:
        expanded = _expand_pattern(project_root, raw)
        if not expanded:
            files.append({"pattern": raw, "path": "", "exists": False, "sha256": "", "size": 0})
            continue
        for path in expanded:
            rel = _safe_relative(project_root, path)
            if rel in seen:
                continue
            seen.add(rel)
            exists = path.is_file()
            files.append({
                "pattern": raw,
                "path": rel,
                "exists": exists,
                "sha256": file_sha256(path) if exists else "",
                "size": path.stat().st_size if exists else 0,
            })
    normalized_values = dict(values or {})
    body = {
        "scope": str(scope or "production_input"),
        "source_patterns": patterns,
        "values": normalized_values,
        "files": files,
    }
    return {
        "kind": KIND,
        "version": VERSION,
        **body,
        "sha256": canonical_sha256(body),
    }


def recompute_content_fingerprint(root: str | Path, recorded: Mapping[str, Any]) -> Dict[str, Any]:
    return build_content_fingerprint(
        root,
        source_patterns=[str(item) for item in recorded.get("source_patterns") or []],
        values=recorded.get("values") if isinstance(recorded.get("values"), Mapping) else {},
        scope=str(recorded.get("scope") or "production_input"),
    )


def fingerprint_issues(root: str | Path, recorded: Any) -> list[str]:
    if not isinstance(recorded, Mapping):
        return ["input_fingerprint_missing"]
    if recorded.get("kind") != KIND or int(recorded.get("version") or 0) != VERSION:
        return ["input_fingerprint_contract_unsupported"]
    expected = recompute_content_fingerprint(root, recorded)
    if str(recorded.get("sha256") or "") != expected["sha256"]:
        return ["input_fingerprint_stale"]
    return []
