#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build one compact, human-readable index for the comic identity registry.

`出图/共享/identity_registry.json` remains the only machine truth.  The compact
index lives in `设定库/共享资产索引.md`; it replaces the old per-asset manifest
trees under `角色库/` and `资产库/`.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import shutil
from typing import Any


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".avif"}
TYPE_BY_PREFIX = {
    "CHAR_": "character",
    "MON_": "character",
    "BEAST_": "character",
    "ANIMAL_": "character",
    "GROUP_": "character_group",
    "LOC_": "scene",
    "PROP_": "prop",
    "WEAPON_": "prop",
    "OUTFIT_": "outfit",
    "STYLE_": "style",
    "FX_": "effect",
    "SYS_": "effect",
}
TYPE_LABELS = {
    "character": "角色",
    "character_group": "群像",
    "scene": "场景",
    "location": "场景",
    "prop": "道具",
    "outfit": "服装",
    "costume": "服装",
    "effect": "特效",
    "vfx": "特效",
    "style": "风格",
    "other": "其他",
}
LEGACY_VIEW_DIRS = ("角色库", "资产库")
LEGACY_GENERATED_FILENAMES = {"00_索引.json", "manifest.json"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_text_if_changed(path: Path, text: str) -> None:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
        _add_image_path(paths, item.get("path") if isinstance(item, dict) else item)
    outfits = asset.get("outfits")
    if isinstance(outfits, dict):
        for outfit in outfits.values():
            if not isinstance(outfit, dict):
                continue
            for key in ("anchor_path", "primary_path", "path"):
                _add_image_path(paths, outfit.get(key))
            for item in outfit.get("reference_images") or []:
                _add_image_path(paths, item.get("path") if isinstance(item, dict) else item)
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


def default_tier(kind: str, asset: dict[str, Any]) -> str:
    explicit = str(asset.get("library_tier") or asset.get("tier") or "").strip()
    if explicit:
        return explicit
    if kind == "character":
        return "core_full" if asset.get("core") else "recurring_standard"
    return "registered_asset"


def entry_for(root: Path, asset_id: str, asset: dict[str, Any]) -> dict[str, Any]:
    kind = normalized_type(asset_id, asset)
    declared = declared_reference_paths(asset)
    ready = [path for path in declared if reference_exists(root, path)]
    planned = [path for path in declared if path not in ready]
    preferred = ""
    for candidate in (
        asset.get("primary_path"),
        asset.get("anchor_path"),
        (asset.get("views") or {}).get("front") if isinstance(asset.get("views"), dict) else None,
        ready[0] if ready else None,
    ):
        if isinstance(candidate, str) and candidate in ready:
            preferred = candidate
            break
    return {
        "asset_id": asset_id,
        "asset_type": kind,
        "display_name": display_name(asset_id, asset),
        "library_tier": default_tier(kind, asset),
        "status": str(asset.get("status") or "planned"),
        "reference_count": len(ready),
        "planned_reference_count": len(planned),
        "primary_reference": preferred,
        "reference_files": ready,
        "planned_reference_files": planned,
        "generation_dependency_files": generation_dependency_paths(asset),
    }


def render_compact_index(summary: dict[str, Any]) -> str:
    lines = [
        "# 共享资产索引",
        "",
        "> 自动生成的人读视图；不要手工维护。机器真值：`出图/共享/identity_registry.json`，真实图片：`出图/共享/图片/`。",
        "",
        f"- 生成日期：{summary['generated_on']}",
        f"- 角色：{summary['character_count']}",
        f"- 其它资产：{summary['asset_count']}",
        "",
        "## 角色",
        "",
        "| ID | 名称 | 档位 | 状态 | 已有/计划参考 | 主参考 |",
        "|---|---|---|---|---:|---|",
    ]
    for item in summary["characters"]:
        lines.append(
            f"| `{item['asset_id']}` | {item['display_name']} | `{item['library_tier']}` | "
            f"{item['status']} | {item['reference_count']}/{item['planned_reference_count']} | "
            f"`{item['primary_reference'] or '—'}` |"
        )
    lines += [
        "",
        "## 场景、道具、服装、特效与风格",
        "",
        "| 类型 | ID | 名称 | 档位 | 状态 | 已有/计划参考 | 主参考 |",
        "|---|---|---|---|---|---:|---|",
    ]
    for item in summary["assets"]:
        label = TYPE_LABELS.get(item["asset_type"], item["asset_type"] or "其他")
        lines.append(
            f"| {label} | `{item['asset_id']}` | {item['display_name']} | `{item['library_tier']}` | "
            f"{item['status']} | {item['reference_count']}/{item['planned_reference_count']} | "
            f"`{item['primary_reference'] or '—'}` |"
        )
    lines += [
        "",
        "## 职责边界",
        "",
        "- 改故事、人物、世界观或视觉规则：编辑 `设定库/story_bible.md` / `style_guide.md`。",
        "- 改机器身份、DNA、档位、状态或引用关系：编辑/刷新 `出图/共享/identity_registry.json`。",
        "- 改真实定妆、场景锚和道具锚：使用 `出图/共享/图片/`，不要复制到本索引旁边。",
        "- 跨作品复用的独立资产包：放在漫画线根目录 `_资产库/`，项目导入后复制进自身 registry，不能长期回指。",
        "",
    ]
    return "\n".join(lines)


def legacy_views_safe_to_remove(root: Path) -> tuple[bool, list[str]]:
    unexpected: list[str] = []
    for rel in LEGACY_VIEW_DIRS:
        base = root / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.name not in LEGACY_GENERATED_FILENAMES:
                unexpected.append(str(path.relative_to(root)))
    return not unexpected, unexpected


def remove_legacy_views(root: Path) -> list[str]:
    safe, unexpected = legacy_views_safe_to_remove(root)
    if not safe:
        raise ValueError("legacy views contain non-generated files; refusing removal: " + ", ".join(unexpected[:8]))
    removed: list[str] = []
    for rel in LEGACY_VIEW_DIRS:
        path = root / rel
        if path.exists():
            shutil.rmtree(path)
            removed.append(rel)
    return removed


def build_library(root: Path, *, write: bool, remove_legacy: bool = False) -> dict[str, Any]:
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry = load_json(registry_path)
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    if not assets:
        raise ValueError(f"identity registry has no assets: {registry_path}")
    entries = [entry_for(root, asset_id, asset) for asset_id, asset in sorted(assets.items()) if isinstance(asset, dict)]
    characters = [entry for entry in entries if entry["asset_type"] == "character"]
    project_assets = [entry for entry in entries if entry["asset_type"] != "character"]
    summary = {
        "schema_version": 2,
        "kind": "comic_project_compact_asset_index",
        "identity_registry": str(registry_path.relative_to(root)),
        "compact_index": "设定库/共享资产索引.md",
        "character_count": len(characters),
        "asset_count": len(project_assets),
        "characters": characters,
        "assets": project_assets,
        "cross_line_dependency": False,
        "generated_on": date.today().isoformat(),
        "legacy_views_removed": [],
    }
    if write and remove_legacy:
        safe, unexpected = legacy_views_safe_to_remove(root)
        if not safe:
            raise ValueError("legacy views contain non-generated files; refusing removal: " + ", ".join(unexpected[:8]))
    if write:
        write_text_if_changed(root / summary["compact_index"], render_compact_index(summary))
        if remove_legacy:
            summary["legacy_views_removed"] = remove_legacy_views(root)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="从 comic identity_registry 生成单一共享资产索引")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true", help="写入 设定库/共享资产索引.md；默认只打印计划")
    parser.add_argument(
        "--remove-legacy-views",
        action="store_true",
        help="安全移除仅含旧派生 manifest 的 角色库/资产库；发现人工文件即拒绝",
    )
    args = parser.parse_args()
    if args.remove_legacy_views and not args.write:
        parser.error("--remove-legacy-views requires --write")
    root = Path(args.project_root).expanduser().resolve()
    try:
        summary = build_library(root, write=args.write, remove_legacy=args.remove_legacy_views)
    except ValueError as exc:
        print(json.dumps({"verdict": "block", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
