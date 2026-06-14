#!/usr/bin/env python3
"""Registry management and filesystem helpers for the n2d pipeline."""

from __future__ import annotations
import hashlib
import json
import os
import re
from typing import Dict, List, Any, Optional

try:
    from n2d_const import *
    from n2d_schema import *
except ImportError:
    from .n2d_const import *
    from .n2d_schema import *

def file_lock(lock_path: str, timeout: float = 30.0, poll: float = 0.1):
    """Simple file-based lock context manager."""
    import time
    import contextlib

    @contextlib.contextmanager
    def _lock():
        start = time.time()
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                break
            except FileExistsError:
                if time.time() - start > timeout:
                    raise TimeoutError(f"Lock wait timeout: {lock_path}")
                time.sleep(poll)
        try:
            yield fd
        finally:
            os.close(fd)
            try:
                os.unlink(lock_path)
            except OSError:
                pass
    return _lock()

def registry_lock_path(root: str) -> str:
    """Return the path to the registry lock file for a project."""
    return os.path.join(root.rstrip("/"), ".registry.lock")

def production_dir(root: str) -> str:
    """Absolute path to the production data directory."""
    return os.path.join(os.fspath(root).rstrip("/"), PRODUCTION_DIR)

def shared_asset_dir(root: str, *, prefer_existing: bool = True) -> str:
    """Path to the shared asset directory (with legacy fallback)."""
    base = root.rstrip("/")
    current = os.path.join(base, "出图", SHARED_ASSET_DIR)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR)
    if prefer_existing and not os.path.exists(current) and os.path.exists(legacy):
        return legacy
    return current

def shared_asset_path(root: str, *parts: str, prefer_existing: bool = True) -> str:
    """Path to a file within the shared asset directory."""
    base = root.rstrip("/")
    current = os.path.join(base, "出图", SHARED_ASSET_DIR, *parts)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR, *parts)
    if prefer_existing and not os.path.exists(current) and os.path.exists(legacy):
        return legacy
    return current

def shared_asset_relpath(*parts: str) -> str:
    """Repository-project relative path inside the current shared asset dir."""
    return os.path.join("出图", SHARED_ASSET_DIR, *parts)

def identity_registry_path(root: str) -> str:
    return shared_asset_path(root, "identity_registry.json")

def asset_registry_path(root: str) -> str:
    return shared_asset_path(root, "asset_registry.json")

def voicemap_path(root: str) -> str:
    """Path to the voicemap.json: `<作品根>/合成/voicemap.json`."""
    return os.path.join(os.fspath(root).rstrip("/"), "合成", "voicemap.json")

def load_json_registry(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}

def load_identity_registry(root: str) -> Dict[str, Any]:
    return load_json_registry(identity_registry_path(root))

def load_asset_registry(root: str) -> Dict[str, Any]:
    return load_json_registry(asset_registry_path(root))

def _sha256(path: str) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _dir_count(path: str) -> Optional[int]:
    if not os.path.isdir(path):
        return None
    total = 0
    for _, _, files in os.walk(path):
        total += len(files)
    return total

def artifact_snapshot(root: str, ep: str, rel_path: str, stage_key: str) -> Dict[str, Any]:
    rel = rel_path.format(ep=ep)
    full = os.path.join(root.rstrip("/"), rel)
    exists = os.path.exists(full)
    item: Dict[str, Any] = {
        "stage": stage_key,
        "path": rel,
        "exists": exists,
        "kind": "dir" if os.path.isdir(full) else "file" if os.path.isfile(full) else "missing",
    }
    digest = _sha256(full)
    if digest:
        item["sha256"] = digest
    count = _dir_count(full)
    if count is not None:
        item["file_count"] = count
    return item

def collect_episode_artifacts(root: str, ep: str, stage: Optional[str] = None) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for spec in STAGE_GRAPH:
        key = str(spec["key"])
        if stage and key != stage:
            continue
        for rel in spec.get("outputs", ()):
            items.append(artifact_snapshot(root, ep, str(rel), key))
    return items

def build_episode_manifest(root: str, ep: str, stage: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from n2d_settings import production_mode
    data: Dict[str, Any] = {
        "kind": MANIFEST_KIND,
        "schema_version": CONTRACT_VERSION,
        "episode": ep,
        "stage": stage or "all",
        "production_mode": production_mode(root),
        "artifacts": collect_episode_artifacts(root, ep, stage=stage),
    }
    if extra:
        data.update(extra)
    return data

def episode_manifest_path(root: str, ep: str) -> str:
    """Absolute path to a per-episode boundary manifest (脚本/<ep>/manifest.json).

    Location is resolved from the BOUNDARY_PRODUCT_KINDS registry so it stays a
    single source of truth with the schema rather than a second hardcoded copy."""
    rel = BOUNDARY_PRODUCT_KINDS[MANIFEST_KIND]["path"].format(ep=ep)
    return os.path.join(os.fspath(root).rstrip("/"), rel)

def write_episode_manifest(root: str, ep: str, stage: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> str:
    path = episode_manifest_path(root, ep)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = build_episode_manifest(root, ep, stage=stage, extra=extra)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path
