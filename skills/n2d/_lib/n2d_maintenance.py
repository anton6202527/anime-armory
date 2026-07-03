#!/usr/bin/env python3
"""Migration and maintenance logic for the n2d pipeline."""

from __future__ import annotations
import json
import os
import re
from typing import Dict, List, Any, Optional

try:
    from n2d_const import *
    from n2d_schema import *
    from n2d_registry import *
except ImportError:
    from .n2d_const import *
    from .n2d_schema import *
    from .n2d_registry import *

def migrate_legacy_shared_assets(root: str, *, apply: bool = True) -> Dict[str, object]:
    """Migrate legacy `common/` assets to `共享/`."""
    base = root.rstrip("/")
    current = os.path.join(base, "出图", SHARED_ASSET_DIR)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR)
    result: Dict[str, object] = {"moved": [], "conflicts": [], "removed_legacy": False}
    if not os.path.isdir(legacy):
        return result
    if not os.path.exists(current):
        if apply:
            os.rename(legacy, current)
        result["moved"] = [LEGACY_SHARED_ASSET_DIR]
        result["removed_legacy"] = True
        return result
    moved: List[str] = []
    conflicts: List[str] = []
    for dirpath, _, files in os.walk(legacy):
        rel_dir = os.path.relpath(dirpath, legacy)
        for name in files:
            rel = name if rel_dir == "." else os.path.join(rel_dir, name)
            src = os.path.join(legacy, rel)
            dst = os.path.join(current, rel)
            if os.path.exists(dst):
                conflicts.append(rel)
                continue
            if apply:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.rename(src, dst)
            moved.append(rel)
    result["moved"] = moved
    result["conflicts"] = conflicts
    if apply and not conflicts:
        for dirpath, _, _ in os.walk(legacy, topdown=False):
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
        result["removed_legacy"] = not os.path.exists(legacy)
    return result

def contract_version_report(root: str) -> Dict[str, object]:
    """Inspect per-episode manifests against CONTRACT_VERSION."""
    def _episode_names(r):
        s = os.path.join(r.rstrip("/"), "脚本")
        if not os.path.isdir(s): return []
        n = [d for d in os.listdir(s) if os.path.isdir(os.path.join(s, d)) and d.startswith("第") and d.endswith("集")]
        return sorted(n, key=lambda x: int(re.search(r"\d+", x).group(0)) if re.search(r"\d+", x) else 10**9)
    
    def _ver(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
            return int(d.get("schema_version"))
        except: return None

    episodes = []
    for ep in _episode_names(root):
        path = episode_manifest_path(root, ep)
        v = _ver(path) if os.path.isfile(path) else None
        status = "missing" if v is None else "current" if v == CONTRACT_VERSION else "stale" if v < CONTRACT_VERSION else "future"
        episodes.append({"episode": ep, "path": path, "schema_version": v, "status": status})
    stale = [e for e in episodes if e["status"] in {"missing", "stale"}]
    future = [e for e in episodes if e["status"] == "future"]
    return {
        "kind": "n2d_contract_version_report",
        "contract_version": CONTRACT_VERSION,
        "root": root,
        "episodes": episodes,
        "stale_or_missing": len(stale),
        "future": len(future),
        "status": "blocked_future" if future else "migration_needed" if stale else "current",
    }

def migrate_v1_to_v2(root: str, *, apply: bool = True) -> Dict[str, object]:
    actions: List[Dict[str, str]] = []
    def _episode_names(r):
        s = os.path.join(r.rstrip("/"), "脚本")
        if not os.path.isdir(s): return []
        return [d for d in os.listdir(s) if os.path.isdir(os.path.join(s, d)) and d.startswith("第") and d.endswith("集")]

    for ep in _episode_names(root):
        path = episode_manifest_path(root, ep)
        try:
            d = json.load(open(path, encoding="utf-8"))
            v = int(d.get("schema_version"))
        except: v = None
        if v == CONTRACT_VERSION:
            continue
        actions.append({"episode": ep, "action": "refresh_episode_manifest", "path": path})
        if apply:
            write_episode_manifest(root, ep, extra={"migration_note": "migrated v1->v2 by refreshing manifest"})
    return {"from": 1, "to": 2, "actions": actions, "applied": apply}

def migrate_contract(root: str, *, target_version: int = CONTRACT_VERSION, apply: bool = True) -> Dict[str, object]:
    before = contract_version_report(root)
    if before["status"] == "blocked_future":
        raise ValueError("project has manifests newer than this code contract")
    steps = []
    if before["status"] == "migration_needed":
        if apply:
            migrate_v1_to_v2(root, apply=True)
            steps.append({"v1_to_v2": "applied"})
    after = contract_version_report(root) if apply else before
    report = {
        "kind": "n2d_contract_migration_report",
        "contract_version": CONTRACT_VERSION,
        "root": root,
        "applied": apply,
        "before": before,
        "steps": steps,
        "after": after,
    }
    if apply:
        path = os.path.join(production_dir(root), "contract_migration_report.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return report
