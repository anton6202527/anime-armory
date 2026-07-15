#!/usr/bin/env python3
"""Scaffold, validate and apply a comic wardrobe/accessory/prop contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REL = Path("设定库/wardrobe_prop_contract.json")
REG = Path("出图/共享/identity_registry.json")
RECEIPT = Path("生产数据/comic_wardrobe_prop_apply.json")
AXES = ["era", "polity_region", "identity_rank", "occasion_activity", "season_climate", "story_state", "production_variant"]
PRIMARY = {"excavated_object", "museum_collection", "archaeological_report"}
CORROBORATING = {"contemporary_image", "historical_text", "museum_research"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def template() -> dict[str, Any]:
    return {
        "schema_version": 1, "kind": "comic_wardrobe_prop_contract", "status": "review",
        "default_policy": {
            "mode": "recommended_unless_user_override", "setting_profile": "historical_traceable",
            "evidence_hierarchy": ["A_physical_archaeology", "B_contemporary_image", "C_historical_text", "D_museum_academic", "E_production_reference", "F_lead_only"],
            "decision_axes": AXES, "user_override": {"allowed": True, "requires_scope_and_reason": True}},
        "world_context": {"era": "", "date_range": "", "polity_region": "", "historical_confidence": "medium", "notes": ""},
        "sources": [], "wardrobe": [], "props": [], "overrides": []}


def validate(data: dict[str, Any], strict: bool = False) -> list[str]:
    errors: list[str] = []
    if data.get("kind") != "comic_wardrobe_prop_contract": errors.append("kind 必须是 comic_wardrobe_prop_contract")
    policy = data.get("default_policy", {})
    if policy.get("mode") != "recommended_unless_user_override": errors.append("默认策略必须是 recommended_unless_user_override")
    if any(x not in policy.get("decision_axes", []) for x in AXES): errors.append("decision_axes 不完整")
    profile = policy.get("setting_profile")
    sources = {x.get("id"): x for x in data.get("sources", []) if x.get("id")}
    if strict and data.get("status") != "confirmed": errors.append("strict 要求 status=confirmed")
    if strict and profile == "historical_traceable":
        world = data.get("world_context", {})
        if not world.get("era") or not world.get("polity_region"): errors.append("历史可考项目必须登记 era 与 polity_region")
        kinds = {x.get("source_type") for x in sources.values()}
        if len(sources) < 2 or not kinds.intersection(PRIMARY) or not kinds.intersection(CORROBORATING):
            errors.append("历史可考项目至少需一项实物/考古来源和一项同时代图像/文献/馆校研究")
    for row in data.get("wardrobe", []):
        tag = f"wardrobe {row.get('character_id')}/{row.get('outfit_id')}"
        for key in ("character_id", "outfit_id", "name", "silhouette", "collar_neckline", "closure", "materials", "evidence_refs", "forbidden"):
            if not row.get(key): errors.append(f"{tag} 缺 {key}")
        if any(ref not in sources for ref in row.get("evidence_refs", [])): errors.append(f"{tag} 引用未知 source")
    for row in data.get("props", []):
        tag = f"prop {row.get('prop_id')}"
        for key in ("prop_id", "name", "function", "dimensions", "construction", "materials", "interaction_grip", "production_variants", "evidence_refs", "forbidden"):
            if not row.get(key): errors.append(f"{tag} 缺 {key}")
        if any(ref not in sources for ref in row.get("evidence_refs", [])): errors.append(f"{tag} 引用未知 source")
    for row in data.get("overrides", []):
        for key in ("scope", "reason", "requested_by", "time", "facts_overridden"):
            if not row.get(key): errors.append(f"override 缺 {key}")
    return errors


def compact(row: dict[str, Any], prop: bool = False) -> str:
    if prop:
        fields = [("功能", "function"), ("尺度", "dimensions"), ("结构", "construction"), ("材料", "materials"), ("交互", "interaction_grip"), ("题字", "inscription_policy"), ("状态", "state_variants"), ("版本", "production_variants")]
    else:
        fields = [("身份场合", "identity_rank"), ("层次", "layers"), ("轮廓", "silhouette"), ("领襟", "collar_neckline"), ("开合", "closure"), ("袖摆", "sleeves"), ("腰带", "waist_belt"), ("冠帽", "headwear"), ("鞋履", "footwear"), ("材料", "materials"), ("色域", "palette"), ("佩饰", "permanent_accessories"), ("状态", "state_variants")]
    parts = []
    for label, key in fields:
        value = row.get(key)
        if value: parts.append(f"{label}:{'、'.join(map(str,value)) if isinstance(value,list) else value}")
    return "；".join(parts)


def apply(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    errors = validate(data, strict=True)
    if errors: raise SystemExit("\n".join(errors))
    registry_path = root / REG
    registry = load(registry_path)
    assets = registry.setdefault("assets", {})
    changed: list[str] = []
    for row in data.get("wardrobe", []):
        if row.get("status") != "confirmed": continue
        cid, oid = row["character_id"], row["outfit_id"]
        if cid not in assets or oid not in assets[cid].get("outfits", {}): raise SystemExit(f"registry 未登记 {cid}/{oid}")
        outfit = assets[cid]["outfits"][oid]
        outfit["description"] = compact(row)
        outfit["forbidden"] = "；".join(row["forbidden"])
        outfit["wardrobe_standard"] = row
        changed.append(f"{cid}/{oid}")
    for row in data.get("props", []):
        if row.get("status") != "confirmed": continue
        pid = row["prop_id"]
        if pid not in assets: raise SystemExit(f"registry 未登记 {pid}")
        assets[pid]["prop_contract"] = compact(row, prop=True)
        assets[pid]["forbidden_inheritance"] = "；".join(row["forbidden"])
        assets[pid]["wardrobe_prop_standard"] = row
        changed.append(pid)
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
    sha = hashlib.sha256(raw).hexdigest()
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    dump(registry_path, registry)
    receipt = {"schema_version": 1, "kind": "comic_wardrobe_prop_apply", "applied_at": datetime.now(timezone.utc).isoformat(), "contract_path": str(REL), "contract_sha256": sha, "changed_ids": changed}
    dump(root / RECEIPT, receipt)
    return receipt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path); p.add_argument("command", choices=["scaffold", "check", "apply"])
    p.add_argument("--write", action="store_true"); p.add_argument("--strict", action="store_true"); p.add_argument("--json", action="store_true")
    a = p.parse_args(); path = a.root / REL
    if a.command == "scaffold":
        result = template()
        if a.write and not path.exists(): dump(path, result)
    else:
        if not path.exists(): raise SystemExit(f"缺少 {path}")
        data = load(path)
        if a.command == "check": result = {"ok": not (errors := validate(data, a.strict)), "errors": errors}
        else:
            if not a.write: raise SystemExit("apply 必须显式传 --write")
            result = apply(a.root, data)
    print(json.dumps(result, ensure_ascii=False, indent=2) if a.json else result)
    if a.command == "check" and not result["ok"]: raise SystemExit(1)


if __name__ == "__main__": main()
