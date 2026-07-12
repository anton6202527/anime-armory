#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build project-local comic character and asset bundle views.

The unified comic identity registry remains the machine truth.  This command
creates human-friendly, self-contained manifests under 角色库/ and 资产库/
without importing another production line or copying its project memory.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from typing import Any


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".avif"}
TYPE_BY_PREFIX = {
    "CHAR_": "character",
    "MON_": "character",
    "GROUP_": "character_group",
    "LOC_": "scene",
    "PROP_": "prop",
    "OUTFIT_": "outfit",
    "STYLE_": "style",
    "FX_": "effect",
    "SYS_": "effect",
}
ASSET_FOLDERS = {
    "scene": "场景",
    "location": "场景",
    "prop": "道具",
    "outfit": "服装",
    "costume": "服装",
    "effect": "特效",
    "vfx": "特效",
    "style": "风格",
    "character_group": "群像",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json_if_changed(path: Path, data: dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "_", str(value or "").strip()).strip("._")
    return cleaned or "未命名"


def normalized_type(asset_id: str, asset: dict[str, Any]) -> str:
    raw = str(asset.get("type") or asset.get("asset_type") or "").strip().lower()
    if raw:
        return raw
    upper = asset_id.upper()
    for prefix, kind in TYPE_BY_PREFIX.items():
        if upper.startswith(prefix):
            return kind
    return "other"


def display_name(asset_id: str, asset: dict[str, Any]) -> str:
    return str(asset.get("display_name") or asset.get("name") or asset.get("title") or asset_id).strip()


def _add_image_path(paths: list[str], value: Any) -> None:
    if not isinstance(value, str):
        return
    candidate = value.strip()
    if Path(candidate).suffix.lower() in IMAGE_SUFFIXES and candidate not in paths:
        paths.append(candidate)


def declared_reference_paths(asset: dict[str, Any]) -> list[str]:
    """Collect identity references without recursively swallowing source metadata."""
    paths: list[str] = []
    for key in ("anchor_path", "primary_path", "path", "style_anchor_path"):
        _add_image_path(paths, asset.get(key))
    views = asset.get("views")
    if isinstance(views, dict):
        for value in views.values():
            _add_image_path(paths, value)
    for item in asset.get("reference_images") or []:
        if isinstance(item, dict):
            _add_image_path(paths, item.get("path"))
        else:
            _add_image_path(paths, item)
    outfits = asset.get("outfits")
    if isinstance(outfits, dict):
        for outfit in outfits.values():
            if not isinstance(outfit, dict):
                continue
            for key in ("anchor_path", "primary_path", "path"):
                _add_image_path(paths, outfit.get(key))
            for item in outfit.get("reference_images") or []:
                if isinstance(item, dict):
                    _add_image_path(paths, item.get("path"))
                else:
                    _add_image_path(paths, item)
    return sorted(paths)


def generation_dependency_paths(asset: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for item in asset.get("reference_images") or []:
        if not isinstance(item, dict) or not isinstance(item.get("source"), dict):
            continue
        source = item["source"]
        for key in ("style_reference_path", "anchor_path", "source_path"):
            _add_image_path(paths, source.get(key))
    return sorted(paths)


def reference_exists(root: Path, raw: str) -> bool:
    path = Path(raw)
    return (path if path.is_absolute() else root / path).is_file()


def bundle_path(root: Path, asset_id: str, asset: dict[str, Any], kind: str) -> Path:
    label = f"{safe_name(asset_id)}__{safe_name(display_name(asset_id, asset))}"
    if kind == "character":
        return root / "角色库" / label
    category = ASSET_FOLDERS.get(kind, "其他")
    return root / "资产库" / category / label


def default_tier(kind: str, asset: dict[str, Any]) -> str:
    explicit = str(asset.get("library_tier") or asset.get("tier") or "").strip()
    if explicit:
        return explicit
    if kind == "character":
        return "core_full" if asset.get("core") else "recurring_standard"
    return "registered_asset"


def manifest_for(root: Path, registry_rel: str, asset_id: str, asset: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    kind = normalized_type(asset_id, asset)
    target = bundle_path(root, asset_id, asset, kind)
    declared_references = declared_reference_paths(asset)
    references = [path for path in declared_references if reference_exists(root, path)]
    planned_references = [path for path in declared_references if path not in references]
    generation_dependencies = generation_dependency_paths(asset)
    rel_target = str(target.relative_to(root))
    if kind == "character":
        directories = {
            "reference": f"{rel_target}/reference",
            "forms": f"{rel_target}/forms",
            "prompts": f"{rel_target}/prompts",
            "qc": f"{rel_target}/qc",
        }
        manifest_kind = "comic_project_character_asset_bundle"
    else:
        directories = {
            "reference": f"{rel_target}/reference",
            "prompts": f"{rel_target}/prompts",
            "qc": f"{rel_target}/qc",
        }
        manifest_kind = "comic_project_asset_bundle"
    manifest = {
        "schema_version": 1,
        "kind": manifest_kind,
        "asset_id": asset_id,
        "asset_type": kind,
        "display_name": display_name(asset_id, asset),
        "library_tier": default_tier(kind, asset),
        "status": str(asset.get("status") or "planned"),
        "truth_sources": {
            "identity_registry": registry_rel,
            "story_bible": "设定库/story_bible.md",
            "style_guide": "设定库/style_guide.md",
        },
        "directories": directories,
        "reference_files": references,
        "reference_count": len(references),
        "planned_reference_files": planned_references,
        "planned_reference_count": len(planned_references),
        "generation_dependency_files": generation_dependencies,
        "reference_readiness": {
            "declared_count": len(declared_references),
            "ready_count": len(references),
            "planned_count": len(planned_references),
            "all_declared_ready": bool(declared_references) and not planned_references,
        },
        "derivation": {
            "mode": "registry_view",
            "owner": "comic-identity",
            "cross_line_dependency": False,
            "note": "manifest is a project-local view; edit identity_registry as machine truth",
        },
        "generated_on": date.today().isoformat(),
    }
    return target, manifest


def build_library(root: Path, *, write: bool) -> dict[str, Any]:
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry = load_json(registry_path)
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    if not assets:
        raise ValueError(f"identity registry has no assets: {registry_path}")
    registry_rel = str(registry_path.relative_to(root))
    characters: list[dict[str, Any]] = []
    project_assets: list[dict[str, Any]] = []
    for asset_id in sorted(assets):
        asset = assets[asset_id]
        if not isinstance(asset, dict):
            continue
        target, manifest = manifest_for(root, registry_rel, asset_id, asset)
        entry = {
            "asset_id": asset_id,
            "asset_type": manifest["asset_type"],
            "display_name": manifest["display_name"],
            "library_tier": manifest["library_tier"],
            "manifest": str((target / "manifest.json").relative_to(root)),
            "reference_count": manifest["reference_count"],
            "planned_reference_count": manifest["planned_reference_count"],
        }
        if manifest["asset_type"] == "character":
            characters.append(entry)
        else:
            project_assets.append(entry)
        if write:
            for rel_dir in manifest["directories"].values():
                (root / rel_dir).mkdir(parents=True, exist_ok=True)
            write_json_if_changed(target / "manifest.json", manifest)

    summary = {
        "schema_version": 1,
        "kind": "comic_project_asset_library_index",
        "identity_registry": registry_rel,
        "character_count": len(characters),
        "asset_count": len(project_assets),
        "characters": characters,
        "assets": project_assets,
        "cross_line_dependency": False,
        "generated_on": date.today().isoformat(),
    }
    if write:
        write_json_if_changed(root / "角色库" / "00_索引.json", {**summary, "assets": []})
        write_json_if_changed(root / "资产库" / "00_索引.json", {**summary, "characters": []})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="从 comic identity_registry 派生项目角色库/资产库 manifests")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true", help="写入 角色库/ 和 资产库/；默认只打印计划")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    try:
        summary = build_library(root, write=args.write)
    except ValueError as exc:
        print(json.dumps({"verdict": "block", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
