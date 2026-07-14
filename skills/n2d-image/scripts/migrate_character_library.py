#!/usr/bin/env python3
"""Move one n2d work from 设定库/character_assets to the work-root 角色库.

Dry-run is the default.  `--apply` performs one directory move, rewrites textual
project references, and records the tiered character-library policy in registry
and manifests.  It never leaves two live directory trees behind.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_const import character_library_tier_for_record  # noqa: E402


OLD_REL = "设定库/character_assets"
NEW_REL = "角色库"
TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".toml"}
CORE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派|贯穿")
RECURRING_RE = re.compile(r"常驻|多集|中长线|反复|复现|主要配角|男二|女二")
PARTIAL_RE = re.compile(r"局部|群像|群演|剪影|不正脸|no_full_face|restricted_partial", re.I)

README = """# 角色库

本目录存放本作品可迁移的角色生产资产包；`设定库/` 仍是人物语义、世界观和角色圣经真值层。

- `core_full`：主角、核心长线、或预计出场 10 集及以上。
- `recurring_standard`：多集复现角色，先建正面、45°、服装与脸锚，侧背按镜头补。
- `named_minimal`：具名短线角色，先建正面、服装与脸锚，复用增加时升档。
- `restricted_partial`：群像或局部角色，只建真实需要的剪影/手部/服装局部。

跨作品复用时显式导出一个自包含 asset pack 到本系列 `_资产库/`；其它作品不得直接依赖本目录路径。
"""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, data: Any) -> None:
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def planned_count(char: Mapping[str, Any]) -> int:
    for key in ("planned_episode_count", "预计出场集数", "计划出场集数"):
        try:
            value = char.get(key)
            if value not in (None, ""):
                return max(0, int(value))
        except (TypeError, ValueError):
            pass
    return 0


def infer_tier(char: Mapping[str, Any]) -> str:
    record = dict(char)
    cid = str(char.get("id") or "")
    scope = " ".join(str(char.get(k) or "") for k in ("scope", "tier", "role", "name"))
    forms = char.get("forms") if isinstance(char.get("forms"), list) else []
    form_blob = json.dumps(forms, ensure_ascii=False)
    if cid.startswith(("GROUP_", "CROWD_")) or PARTIAL_RE.search(f"{scope} {form_blob}"):
        record["restricted_partial"] = True
    if not record.get("planned_episode_count"):
        record["planned_episode_count"] = planned_count(char)
    return character_library_tier_for_record(record)


def registry_paths(root: Path) -> Iterable[Path]:
    for rel in (
        "出图/共享/identity_registry.json",
        "出图/common/identity_registry.json",
        "生产数据/identity_registry.json",
    ):
        path = root / rel
        if path.is_file():
            yield path


def annotate_registries(root: Path, apply: bool) -> Dict[str, str]:
    tiers: Dict[str, str] = {}
    for path in registry_paths(root):
        data = load_json(path)
        if not isinstance(data, dict) or not isinstance(data.get("characters"), list):
            continue
        changed = False
        for char in data["characters"]:
            if not isinstance(char, dict):
                continue
            cid = str(char.get("id") or "").strip()
            if not cid:
                continue
            tier = infer_tier(char)
            tiers[cid] = tier
            count = planned_count(char)
            if char.get("library_tier") != tier:
                char["library_tier"] = tier
                changed = True
            if char.get("planned_episode_count") != count:
                char["planned_episode_count"] = count
                changed = True
            bundle = char.get("asset_bundle")
            if isinstance(bundle, dict) and bundle.get("tier") != tier:
                bundle["tier"] = tier
                changed = True
            for form in char.get("forms") or []:
                if not isinstance(form, dict):
                    continue
                atlas = form.get("reference_atlas")
                if isinstance(atlas, dict) and atlas.get("build_tier") != tier:
                    atlas["build_tier"] = tier
                    changed = True
        if changed and apply:
            write_json(path, data)
    return tiers


def annotate_manifests(root: Path, tiers: Mapping[str, str], apply: bool) -> int:
    changed_count = 0
    for path in sorted((root / NEW_REL).glob("*/manifest.json")):
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        cid = str(data.get("character_id") or path.parent.name.split("__", 1)[0]).strip()
        tier = tiers.get(cid)
        if not tier:
            tier = "restricted_partial" if cid.startswith(("GROUP_", "CROWD_")) else "named_minimal"
        changed = False
        if data.get("library_tier") != tier:
            data["library_tier"] = tier
            changed = True
        if changed:
            changed_count += 1
            if apply:
                write_json(path, data)
    return changed_count


def text_replacements(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            if OLD_REL in path.read_text(encoding="utf-8"):
                out.append(path)
        except (OSError, UnicodeDecodeError):
            continue
    return out


def migrate(root: Path, apply: bool = False) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    old = root / OLD_REL
    new = root / NEW_REL
    if old.exists() and new.exists():
        return {
            "ok": False,
            "status": "conflict",
            "message": "旧、新角色库同时存在；为避免合并覆盖，未做任何修改。请先人工确认唯一真值。",
            "old": str(old),
            "new": str(new),
        }

    refs_before = text_replacements(root)
    registries = list(registry_paths(root))
    report: Dict[str, Any] = {
        "ok": True,
        "status": "planned" if not apply else "applied",
        "root": str(root),
        "move": bool(old.exists()),
        "old": str(old),
        "new": str(new),
        "reference_files": [str(p.relative_to(root)) for p in refs_before],
        "registry_files": [str(p.relative_to(root)) for p in registries],
    }
    if not apply:
        return report

    if old.exists():
        old.rename(new)
    elif registries:
        new.mkdir(parents=True, exist_ok=True)

    for path in text_replacements(root):
        atomic_write(path, path.read_text(encoding="utf-8").replace(OLD_REL, NEW_REL))

    tiers = annotate_registries(root, apply=True)
    report["tiers"] = dict(sorted(tiers.items()))
    report["manifests_annotated"] = annotate_manifests(root, tiers, apply=True)
    if new.exists() and not (new / "README.md").exists():
        atomic_write(new / "README.md", README)
    report["legacy_directory_remaining"] = old.exists()
    report["new_directory_exists"] = new.exists()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root")
    parser.add_argument("--apply", action="store_true", help="perform migration; default is dry-run")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = migrate(Path(args.project_root), apply=args.apply)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result.get("message") or json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
