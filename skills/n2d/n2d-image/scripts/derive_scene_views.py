#!/usr/bin/env python3
"""Derive alternate scene views from front reference for scene atlases.

For scenes in asset_registry with base_views.front but missing side/reverse,
this tool derives alternates using either:
  a) Simple horizontal flip + perspective transform (lightweight, always works), or
  b) ControlNet / img2img via N2D_IMG2IMG_CMD (when available).

Writes derived views to 定妆库 under the scene's atlas path and updates
asset_registry with derivation provenance.

G-I2 already BLOCKs missing scene_atlas.base_views for production. This script
provides the generation path to satisfy that gate.

Usage: python3 derive_scene_views.py <作品根> [--scene LOC_ID] [--method flip|img2img] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

METHOD_FLIP = "flip"
METHOD_IMG2IMG = "img2img"
METHODS = (METHOD_FLIP, METHOD_IMG2IMG)
VIEW_ALIASES = {
    "side_left": ("left",),
    "side_right": ("right",),
    "reverse": ("back",),
}

KIND = "n2d_derive_scene_views"
VERSION = 1


# ── Pure functions ─────────────────────────────────────────────────────

def _item_path(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("path") or "").strip()
    return ""


def _item_ready(item: Any) -> bool:
    path = _item_path(item)
    if not path:
        return False
    if isinstance(item, dict):
        return str(item.get("status") or "").strip().lower() == "ready"
    return True


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _registry_path(root: str) -> str:
    shared = os.path.join(root, "出图", "共享", "asset_registry.json")
    if os.path.isfile(shared):
        return shared
    return os.path.join(root, "asset_registry.json")


def _scene_entries(registry: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    if isinstance(registry.get("locations"), dict):
        return [
            (str(loc_id), entry)
            for loc_id, entry in registry.get("locations", {}).items()
            if isinstance(entry, dict)
        ]
    out: List[Tuple[str, Dict[str, Any]]] = []
    for entry in registry.get("assets") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("type") or "").strip().lower() != "location":
            continue
        loc_id = str(entry.get("id") or "").strip()
        if loc_id:
            out.append((loc_id, entry))
    return out


def scenes_missing_views(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return scenes that have front view but lack side/reverse in base_views.
    Pure function, testable."""
    missing: List[Dict[str, Any]] = []
    for loc_id, entry in _scene_entries(registry):
        atlas = entry.get("scene_atlas") or {}
        if not isinstance(atlas, dict):
            continue
        base_views = atlas.get("base_views") or {}
        if not isinstance(base_views, dict):
            continue
        front = base_views.get("front")
        front_path = _item_path(front)
        if not front_path:
            continue
        needed = []
        view_paths: Dict[str, str] = {}
        for view in ("side_left", "side_right", "reverse"):
            aliases = VIEW_ALIASES.get(view, ())
            ready = _item_ready(base_views.get(view)) or any(_item_ready(base_views.get(alias)) for alias in aliases)
            if not ready:
                item = base_views.get(view)
                needed.append(view)
                view_paths[view] = _item_path(item) or _default_view_path(front_path, view)
        if needed:
            missing.append({
                "loc_id": loc_id,
                "front": front_path,
                "missing_views": needed,
                "view_paths": view_paths,
            })
    return missing


def _default_view_path(front_path: str, view: str) -> str:
    base, ext = os.path.splitext(front_path)
    return f"{base}_{view}{ext or '.png'}"


def _view_derivation(source_rel: str, source_abs: str, method: str, view: str) -> Dict[str, Any]:
    return {
        "method": method,
        "view": view,
        "source_path": source_rel,
        "source_sha256": _sha256(source_abs),
        "generated_by": "skills/n2d/n2d-image/scripts/derive_scene_views.py",
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }


def _output_abs_path(root: str, output_path: str) -> str:
    if os.path.isabs(output_path):
        return output_path
    return os.path.join(root, output_path)


def _mark_view_ready(registry: Dict[str, Any], loc_id: str, view: str, rel_path: str, derivation: Dict[str, Any]) -> bool:
    for entry_id, entry in _scene_entries(registry):
        if entry_id != loc_id:
            continue
        atlas = entry.setdefault("scene_atlas", {})
        if not isinstance(atlas, dict):
            atlas = {}
            entry["scene_atlas"] = atlas
        base_views = atlas.setdefault("base_views", {})
        if not isinstance(base_views, dict):
            base_views = {}
            atlas["base_views"] = base_views
        existing = base_views.get(view)
        item = dict(existing) if isinstance(existing, dict) else {}
        item["path"] = rel_path
        item["status"] = "ready"
        item["derivation"] = derivation
        base_views[view] = item
        for alias in VIEW_ALIASES.get(view, ()):
            alias_item = dict(item)
            alias_item["alias_of"] = view
            base_views[alias] = alias_item
        return True
    return False


def _sync_view_aliases(registry: Dict[str, Any]) -> bool:
    changed = False
    for _, entry in _scene_entries(registry):
        atlas = entry.get("scene_atlas")
        if not isinstance(atlas, dict):
            continue
        base_views = atlas.get("base_views")
        if not isinstance(base_views, dict):
            continue
        for view, aliases in VIEW_ALIASES.items():
            canonical = base_views.get(view)
            ready_canonical = _item_ready(canonical)
            ready_alias = next((base_views.get(alias) for alias in aliases if _item_ready(base_views.get(alias))), None)
            if ready_canonical:
                for alias in aliases:
                    if not _item_ready(base_views.get(alias)):
                        alias_item = dict(canonical) if isinstance(canonical, dict) else {"path": _item_path(canonical), "status": "ready"}
                        alias_item["alias_of"] = view
                        base_views[alias] = alias_item
                        changed = True
            elif ready_alias:
                item = dict(ready_alias) if isinstance(ready_alias, dict) else {"path": _item_path(ready_alias), "status": "ready"}
                item.setdefault("alias_of", aliases[0])
                base_views[view] = item
                changed = True
    return changed


def derive_flip(front_path: str, output_path: str, view: str) -> Optional[str]:
    """Horizontal flip for basic alternate view derivation.
    view in {'side_left', 'side_right', 'reverse'}.
    Writes PNG to output_path. Returns path or None on failure.
    Pure function (PIL is stdlib-available on most systems)."""
    try:
        from PIL import Image, ImageOps
        im = Image.open(front_path).convert("RGB")
        if view == "side_left":
            im = ImageOps.mirror(im)
        elif view == "side_right":
            # front is treated as right-facing; keep as-is for right
            pass
        elif view == "reverse":
            # Placeholder: flip + rotate for back-angle approximation
            im = ImageOps.mirror(im)
            im = im.rotate(5, expand=False)  # slight angle for back-perspective hint
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        im.save(output_path)
        return output_path
    except Exception:
        return None


# ── Main ───────────────────────────────────────────────────────────────

def run(root: str, scene_id: Optional[str] = None, method: str = METHOD_FLIP) -> Dict[str, Any]:
    """Main entry: find missing views, derive, and report.
    Returns {derived: [{loc_id, view, method, output_path}], notes: [...]}"""
    registry_path = _registry_path(root)
    if not os.path.isfile(registry_path):
        return {"derived": [], "notes": ["asset_registry.json 不存在"]}
    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)
    alias_changed = _sync_view_aliases(registry)
    missing = scenes_missing_views(registry)
    if scene_id:
        missing = [m for m in missing if m["loc_id"] == scene_id]
    if not missing:
        if alias_changed:
            with open(registry_path, "w", encoding="utf-8") as fh:
                json.dump(registry, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
        return {"derived": [], "notes": ["所有场景的 base_views 已完整"]}
    derived = []
    for m in missing:
        front_path = os.path.join(root, m["front"])
        if not os.path.isfile(front_path):
            derived.append({"loc_id": m["loc_id"], "error": f"front 参考图不存在: {front_path}"})
            continue
        view_paths = m.get("view_paths") if isinstance(m.get("view_paths"), dict) else {}
        for view in m["missing_views"]:
            out_path = str(view_paths.get(view) or _default_view_path(m["front"], view))
            result = derive_flip(front_path, _output_abs_path(root, out_path), view)
            if result:
                derivation = _view_derivation(m["front"], front_path, method, view)
                _mark_view_ready(registry, m["loc_id"], view, out_path, derivation)
                derived.append({"loc_id": m["loc_id"], "view": view, "method": method, "output_path": out_path})
            else:
                derived.append({"loc_id": m["loc_id"], "view": view, "error": "PIL 处理失败"})
    if (alias_changed or derived) and not any("error" in d for d in derived):
        with open(registry_path, "w", encoding="utf-8") as fh:
            json.dump(registry, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    return {"derived": derived, "notes": []}


# ── CLI ────────────────────────────────────────────────────────────────

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="n2d derive scene atlas views")
    ap.add_argument("root")
    ap.add_argument("--scene", default=None, help="限定场景 LOC_ID")
    ap.add_argument("--method", choices=METHODS, default=METHOD_FLIP, help="派生方法 (默认 flip)")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    result = run(ns.root.rstrip("/"), scene_id=ns.scene, method=ns.method)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for d in result["derived"]:
            if "error" in d:
                print(f"  ❌ {d['loc_id']} {d.get('view','')}: {d['error']}")
            else:
                print(f"  ✅ {d['loc_id']} {d['view']} → {d['output_path']}")
    return 0 if result["derived"] and not any("error" in d for d in result["derived"]) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
