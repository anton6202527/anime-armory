#!/usr/bin/env python3
"""comic identity registry schema-v2 migration and deterministic validation.

This module deliberately uses only the standard library.  It owns structural
truth (IDs, references and state links), not visual/aesthetic judgement.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 2
KIND = "comic_identity_registry"
CHARACTER_TYPES = {"character", "monster"}
TIER_VALUES = {"core_full", "recurring_standard", "named_minimal", "restricted_partial"}
PREFIX_TYPES = {
    "CHAR": "character",
    "MON": "monster",
    "LOC": "location",
    "PROP": "prop",
    "OUTFIT": "outfit",
    "STYLE": "style",
    "FX": "vfx",
    "VFX": "vfx",
    "SYS": "system_asset",
}
DEFAULT_IDS = {
    "form_id": "FORM_BASE",
    "outfit_id": "OUTFIT_BASE",
    "expression_id": "EXPR_NEUTRAL",
    "state_id": "STATE_BASE",
}
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def new_registry(*, source: str = "registry_v2 init") -> dict[str, Any]:
    """Return the smallest valid, honest schema-v2 registry.

    An empty registry is a useful project bootstrap state.  It must not contain
    placeholder assets marked ready, because no identity image has been
    reviewed yet.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "assets": {},
        "schema_meta": {
            "initialized_at": now_iso(),
            "initialized_by": source,
        },
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def asset_type_for_id(asset_id: str, declared: str = "") -> str:
    prefix = str(asset_id or "").split("_", 1)[0].upper()
    return PREFIX_TYPES.get(prefix, str(declared or "asset").strip().lower() or "asset")


def _reference_images(value: Any) -> list[Any]:
    if isinstance(value, list):
        return copy.deepcopy(value)
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _view_reference(asset: Mapping[str, Any], view: str) -> list[dict[str, Any]]:
    views = asset.get("views") if isinstance(asset.get("views"), Mapping) else {}
    path = str(views.get(view) or "").strip()
    if not path:
        for item in asset.get("reference_images") or []:
            if isinstance(item, Mapping) and str(item.get("view") or "") == view:
                path = str(item.get("path") or "").strip()
                if path:
                    break
    return [{"path": path, "role": view}] if path else []


def ensure_character_contract(asset_id: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    asset = copy.deepcopy(dict(raw))
    forms = asset.get("forms") if isinstance(asset.get("forms"), Mapping) else {}
    forms = copy.deepcopy(dict(forms))
    if not forms:
        forms[DEFAULT_IDS["form_id"]] = {
            "id": DEFAULT_IDS["form_id"],
            "name": "基础形态",
            "inheritance_contract": asset.get("variant_policy") or "继承基础脸型、发际线、眼型、体型与标志物",
            "forbidden": asset.get("forbidden_inheritance") or "不得换脸、换发际线、换眼型或丢失标志物",
            "reference_images": _view_reference(asset, "front"),
            "status": "ready" if _view_reference(asset, "front") else "needs_reference",
        }
    outfits = asset.get("outfits") if isinstance(asset.get("outfits"), Mapping) else {}
    outfits = copy.deepcopy(dict(outfits))
    if not outfits:
        outfit_refs = _view_reference(asset, "front") or _view_reference(asset, "three_quarter")
        outfits[DEFAULT_IDS["outfit_id"]] = {
            "id": DEFAULT_IDS["outfit_id"],
            "name": "基础服装",
            "description": "继承角色基础定妆中的服装结构、配色与标志配饰",
            "forbidden": "不得改变领型、配饰、主色或标志纹样",
            "reference_images": outfit_refs,
            "status": "ready" if outfit_refs else "needs_reference",
        }
    expressions = asset.get("expressions") if isinstance(asset.get("expressions"), Mapping) else {}
    expressions = copy.deepcopy(dict(expressions))
    if not expressions:
        face_refs = _view_reference(asset, "face") or _view_reference(asset, "front")
        expressions[DEFAULT_IDS["expression_id"]] = {
            "id": DEFAULT_IDS["expression_id"],
            "name": "中性表情",
            "emotion": "neutral",
            "intensity": "neutral",
            "reference_images": face_refs,
            "status": "ready" if face_refs else "needs_reference",
        }
    default_binding_raw = asset.get("default_binding") if isinstance(asset.get("default_binding"), Mapping) else {}

    def _registered_default(key: str, collection: Mapping[str, Any]) -> str:
        explicit = str(default_binding_raw.get(key) or "").strip()
        if explicit:
            return explicit
        conventional = DEFAULT_IDS[key]
        if conventional in collection:
            return conventional
        return sorted(str(item) for item in collection)[0]

    default_binding = {
        "form_id": _registered_default("form_id", forms),
        "outfit_id": _registered_default("outfit_id", outfits),
        "expression_id": _registered_default("expression_id", expressions),
    }
    states = asset.get("states") if isinstance(asset.get("states"), Mapping) else {}
    states = copy.deepcopy(dict(states))
    if not states:
        state_id = str(default_binding_raw.get("state_id") or DEFAULT_IDS["state_id"]).strip()
        states[state_id] = {
            "id": state_id,
            "name": "基础状态",
            "form_id": default_binding["form_id"],
            "outfit_id": default_binding["outfit_id"],
            "expression_id": default_binding["expression_id"],
            "transient": False,
            "continuity_contract": "除非剧情状态账明确变更，否则延续此状态",
        }
    default_binding["state_id"] = _registered_default("state_id", states)
    for collection in (forms, outfits, expressions, states):
        for key, record in list(collection.items()):
            if isinstance(record, Mapping):
                item = copy.deepcopy(dict(record))
            else:
                item = {"name": str(record)}
            item.setdefault("id", str(key))
            if "reference_images" in item:
                item["reference_images"] = _reference_images(item.get("reference_images"))
            collection[str(key)] = item
            if key != str(key):
                collection.pop(key, None)
    asset.update({
        "id": asset_id,
        "type": asset_type_for_id(asset_id, str(asset.get("type") or "")),
        "display_name": str(asset.get("display_name") or asset.get("name") or asset_id).strip(),
        # 2026-07-23：MON_ 默认档位从 restricted_partial 改为与 CHAR_ 同的 core_full。
        # 旧默认让妖怪一进注册表就落进最弱档（当时还是零必需视图免检档），聊斋两话
        # 「妖怪画错生物」无人拦即源于此。档位仍可显式声明降档，但默认必须宁多不漏。
        "library_tier": str(asset.get("library_tier") or asset.get("tier") or "core_full"),
        "forms": forms,
        "outfits": outfits,
        "expressions": expressions,
        "states": states,
        "default_binding": default_binding,
    })
    asset.setdefault("reference_images", [])
    asset.setdefault("status", "needs_reference")
    if (
        asset["library_tier"] == "core_full"
        and str(asset.get("status") or "") == "ready"
        and not isinstance(asset.get("model_pack"), Mapping)
    ):
        # A legacy ready flag has no model-pack approval evidence.  Keep the
        # usable assets, but do not pretend they passed a turnaround review.
        asset["status"] = "needs_approval"
    return asset


def upsert_asset(
    registry: Mapping[str, Any],
    asset_id: str,
    *,
    display_name: str = "",
    description: str = "",
    notes: str = "",
    library_tier: str = "",
    character_dna: str = "",
    variant_policy: str = "",
    forbidden_inheritance: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create or update one registry asset without producing media.

    Prefixes remain the type authority.  Character-like assets receive a
    complete default form/outfit/expression/state binding so a panel script can
    refer to stable IDs before the model pack is generated.  The new record is
    deliberately ``needs_reference`` rather than ``ready``.
    """
    aid = str(asset_id or "").strip().upper()
    if not ID_RE.fullmatch(aid):
        raise ValueError("asset_id must be a stable uppercase underscore ID, for example CHAR_LIN or LOC_TEMPLE")
    canonical_type = asset_type_for_id(aid)
    if canonical_type == "asset":
        raise ValueError(f"unsupported asset prefix for {aid}; use one of {sorted(PREFIX_TYPES)}")
    if library_tier and library_tier not in TIER_VALUES:
        raise ValueError(f"library_tier must be one of {sorted(TIER_VALUES)}")

    migrated, _ = migrate_registry(registry)
    assets = migrated.setdefault("assets", {})
    if not isinstance(assets, dict):
        raise ValueError("registry assets must be an object")
    existed = aid in assets
    current = assets.get(aid) if isinstance(assets.get(aid), Mapping) else {}
    record = copy.deepcopy(dict(current))
    record.update({"id": aid, "type": canonical_type})
    if display_name:
        record["display_name"] = display_name.strip()
    else:
        record.setdefault("display_name", aid)
    if description:
        record["description"] = description.strip()
    if notes:
        record["notes"] = notes.strip()
    if character_dna:
        record["character_dna"] = character_dna.strip()
    if variant_policy:
        record["variant_policy"] = variant_policy.strip()
    if forbidden_inheritance:
        record["forbidden_inheritance"] = forbidden_inheritance.strip()

    if canonical_type in CHARACTER_TYPES:
        if library_tier:
            record["library_tier"] = library_tier
        record = ensure_character_contract(aid, record)
    else:
        record.setdefault("reference_images", [])
        record.setdefault("status", "needs_reference")
    record["updated_at"] = now_iso()
    assets[aid] = record
    return migrated, {
        "asset_id": aid,
        "asset_type": canonical_type,
        "created": not existed,
        "status": str(record.get("status") or ""),
        "default_binding": copy.deepcopy(record.get("default_binding") or {}),
    }


def migrate_registry(data: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    source = copy.deepcopy(data) if isinstance(data, Mapping) else {}
    previous = int(source.get("schema_version") or 1)
    assets_raw = source.get("assets") if isinstance(source.get("assets"), Mapping) else {}
    assets: dict[str, Any] = {}
    migrated_characters: list[str] = []
    normalized_types: list[str] = []
    for raw_id, raw_asset in assets_raw.items():
        asset_id = str(raw_id).strip()
        record = dict(raw_asset) if isinstance(raw_asset, Mapping) else {"notes": str(raw_asset)}
        canonical_type = asset_type_for_id(asset_id, str(record.get("type") or ""))
        if str(record.get("type") or "") != canonical_type:
            normalized_types.append(asset_id)
        if canonical_type in CHARACTER_TYPES or asset_id.startswith(("CHAR_", "MON_")):
            record = ensure_character_contract(asset_id, record)
            migrated_characters.append(asset_id)
        else:
            record = copy.deepcopy(record)
            record["id"] = asset_id
            record["type"] = canonical_type
        assets[asset_id] = record
    out = copy.deepcopy(source)
    out.update({
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "assets": assets,
    })
    meta = out.get("schema_meta") if isinstance(out.get("schema_meta"), Mapping) else {}
    meta = dict(meta)
    if previous < SCHEMA_VERSION:
        meta.update({
            "migrated_from_version": previous,
            "migrated_at": now_iso(),
            "compatibility": "legacy character assets retained; core_full requires fresh model-pack approval",
        })
    out["schema_meta"] = meta
    return out, {
        "changed": previous != SCHEMA_VERSION or out != source,
        "from_version": previous,
        "to_version": SCHEMA_VERSION,
        "migrated_characters": migrated_characters,
        "normalized_asset_types": normalized_types,
    }


def _issue(severity: str, code: str, message: str, *, asset_id: str = "", field: str = "") -> dict[str, str]:
    return {"severity": severity, "code": code, "asset_id": asset_id, "field": field, "message": message}


def validate_registry(data: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not isinstance(data, Mapping):
        issues.append(_issue("block", "registry_not_object", "identity_registry 顶层必须是 object"))
        return {"kind": "comic_identity_registry_validation", "valid": False, "issues": issues}
    if int(data.get("schema_version") or 0) != SCHEMA_VERSION:
        issues.append(_issue("block", "schema_version_not_v2", "identity_registry 必须迁移到 schema_version=2", field="schema_version"))
    if data.get("kind") != KIND:
        issues.append(_issue("block", "registry_kind_invalid", f"kind 必须为 {KIND}", field="kind"))
    assets = data.get("assets")
    if not isinstance(assets, Mapping):
        issues.append(_issue("block", "assets_not_object", "assets 必须是 object", field="assets"))
        assets = {}
    for asset_id, raw in assets.items():
        aid = str(asset_id)
        if not ID_RE.match(aid):
            issues.append(_issue("block", "asset_id_invalid", "资产 ID 必须是稳定的大写下划线 ID", asset_id=aid))
        if not isinstance(raw, Mapping):
            issues.append(_issue("block", "asset_not_object", "资产记录必须是 object", asset_id=aid))
            continue
        expected_type = asset_type_for_id(aid, str(raw.get("type") or ""))
        if str(raw.get("id") or "") != aid:
            issues.append(_issue("block", "asset_id_mismatch", "记录 id 必须与 assets key 一致", asset_id=aid, field="id"))
        if str(raw.get("type") or "") != expected_type:
            issues.append(_issue("block", "asset_type_mismatch", f"{aid} 类型必须统一为 {expected_type}", asset_id=aid, field="type"))
        if expected_type not in CHARACTER_TYPES:
            continue
        tier = str(raw.get("library_tier") or "")
        if tier not in TIER_VALUES:
            issues.append(_issue("block", "library_tier_invalid", f"library_tier 必须是 {sorted(TIER_VALUES)}", asset_id=aid, field="library_tier"))
        collections = {
            "form_id": ("forms", raw.get("forms")),
            "outfit_id": ("outfits", raw.get("outfits")),
            "expression_id": ("expressions", raw.get("expressions")),
            "state_id": ("states", raw.get("states")),
        }
        for _id_key, (field, value) in collections.items():
            if not isinstance(value, Mapping) or not value:
                issues.append(_issue("block", f"{field}_missing", f"角色必须有非空 {field}", asset_id=aid, field=field))
        default = raw.get("default_binding") if isinstance(raw.get("default_binding"), Mapping) else {}
        for id_key, (collection_name, collection) in collections.items():
            value = str(default.get(id_key) or "")
            if not value:
                issues.append(_issue("block", f"default_{id_key}_missing", f"default_binding.{id_key} 必填", asset_id=aid, field=f"default_binding.{id_key}"))
            elif not isinstance(collection, Mapping) or value not in collection:
                issues.append(_issue("block", f"default_{id_key}_unknown", f"default_binding.{id_key}={value} 未登记", asset_id=aid, field=f"default_binding.{id_key}"))
        states = raw.get("states") if isinstance(raw.get("states"), Mapping) else {}
        links = {
            "form_id": raw.get("forms"),
            "outfit_id": raw.get("outfits"),
            "expression_id": raw.get("expressions"),
        }
        for state_id, state in states.items():
            if not isinstance(state, Mapping):
                issues.append(_issue("block", "state_not_object", f"state {state_id} 必须是 object", asset_id=aid, field=f"states.{state_id}"))
                continue
            for id_key, collection in links.items():
                linked = str(state.get(id_key) or "")
                if linked and (not isinstance(collection, Mapping) or linked not in collection):
                    issues.append(_issue("block", f"state_{id_key}_unknown", f"state {state_id} 引用了未登记 {id_key}={linked}", asset_id=aid, field=f"states.{state_id}.{id_key}"))
    identity_types = [
        asset_type_for_id(str(aid), str(asset.get("type") or ""))
        for aid, asset in assets.items()
        if isinstance(asset, Mapping)
    ]
    return {
        "kind": "comic_identity_registry_validation",
        "schema_version": SCHEMA_VERSION,
        "valid": not any(item["severity"] == "block" for item in issues),
        "summary": {
            "assets": len(assets),
            "identity_assets": sum(1 for asset_type in identity_types if asset_type in CHARACTER_TYPES),
            "characters": sum(1 for asset_type in identity_types if asset_type == "character"),
            "monsters": sum(1 for asset_type in identity_types if asset_type == "monster"),
            "block": sum(1 for item in issues if item["severity"] == "block"),
            "warn": sum(1 for item in issues if item["severity"] == "warn"),
        },
        "issues": issues,
    }


def registry_path(root: Path) -> Path:
    return root / "出图" / "共享" / "identity_registry.json"


def write_registry(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="初始化、登记、迁移或校验 comic identity_registry schema v2")
    parser.add_argument("project_root")
    parser.add_argument("command", choices=("check", "init", "upsert", "migrate"))
    parser.add_argument("--write", action="store_true", help="init/upsert/migrate 时原位写回；未指定时只预览")
    parser.add_argument("--asset-id", "--id", dest="asset_id", default="", help="upsert 的稳定 ID，如 CHAR_LIN/LOC_TEMPLE")
    parser.add_argument("--name", default="", help="upsert 的人读名称")
    parser.add_argument("--description", default="", help="upsert 的资产描述")
    parser.add_argument("--notes", default="", help="upsert 的研究/制作备注")
    parser.add_argument("--tier", choices=tuple(sorted(TIER_VALUES)), default="", help="CHAR_/MON_ 生产档位")
    parser.add_argument("--character-dna", default="", help="永久脸型、五官、发型、体态和标志物；不得写临时走位/手持物")
    parser.add_argument("--variant-policy", default="", help="年龄/形态变化时必须继承的身份规则")
    parser.add_argument("--forbidden-inheritance", default="", help="禁止从风格图/临时剧情状态继承的内容")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    path = registry_path(root)

    if args.command == "init":
        created = not path.exists()
        if created:
            data = new_registry()
        else:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                print(json.dumps({"kind": "comic_identity_registry_validation", "valid": False, "error": str(exc)}, ensure_ascii=False))
                return 2
        report = validate_registry(data)
        written = bool(created and args.write and report["valid"])
        if written:
            write_registry(path, data)
        report.update({"created": created, "written": written, "path": str(path)})
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else (
            f"identity_registry v2 init: valid={report['valid']} created={created} written={written} path={path}"
        ))
        return 0 if report["valid"] else 1

    if args.command == "upsert":
        if not args.asset_id:
            parser.error("upsert requires --asset-id")
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                print(json.dumps({"kind": "comic_identity_registry_validation", "valid": False, "error": str(exc)}, ensure_ascii=False))
                return 2
        else:
            data = new_registry(source="registry_v2 upsert bootstrap")
        try:
            updated, change = upsert_asset(
                data,
                args.asset_id,
                display_name=args.name,
                description=args.description,
                notes=args.notes,
                library_tier=args.tier,
                character_dna=args.character_dna,
                variant_policy=args.variant_policy,
                forbidden_inheritance=args.forbidden_inheritance,
            )
        except ValueError as exc:
            parser.error(str(exc))
        report = validate_registry(updated)
        written = bool(args.write and report["valid"])
        if written:
            write_registry(path, updated)
        report.update({"upsert": change, "written": written, "path": str(path)})
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else (
            f"identity_registry upsert: valid={report['valid']} asset={change['asset_id']} "
            f"type={change['asset_type']} created={change['created']} written={written}"
        ))
        return 0 if report["valid"] else 1

    if not path.is_file():
        report = {
            "kind": "comic_identity_registry_validation",
            "valid": False,
            "error": f"identity_registry.json not found: {path}; run `registry_v2.py <project_root> init --write` first",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report["error"])
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"kind": "comic_identity_registry_validation", "valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    migrated, migration = migrate_registry(data)
    if args.command == "migrate" and args.write:
        write_registry(path, migrated)
    report = validate_registry(migrated if args.command == "migrate" else data)
    report["migration"] = migration
    report["written"] = bool(args.command == "migrate" and args.write)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else (
        f"identity_registry v2: valid={report['valid']} block={report.get('summary', {}).get('block', 0)} "
        f"migrated={migration['changed']} written={report['written']}"
    ))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
