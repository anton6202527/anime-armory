#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build project-derived MV identity, asset, state, and reference registries."""
import argparse
import glob
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
MV_UTILS_PATH = os.path.join(HERE, "mv_utils.py")


def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv_utils = load_mv_utils()
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
REFERENCE_SEARCH_DIRS = ("设定/reference_images", "出图/共享/图片", "出图/段落/图片")
FIELD_RE = re.compile(r"^\s*[-*]\s*([^:：]+)[:：]\s*(.+?)\s*$")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")


def read_all(pattern):
    return [(path, mv_utils.read_text(path)) for path in sorted(glob.glob(pattern))]


def clean_name(value):
    value = re.sub(r"[`*_「」『』]", "", str(value or "")).strip()
    value = re.sub(r"（.*?）|\(.*?\)", "", value).strip()
    return value


def stable_id(prefix, name):
    ascii_slug = re.sub(r"[^A-Z0-9]+", "_", str(name).upper()).strip("_")
    if not ascii_slug or len(ascii_slug) < 2:
        ascii_slug = hashlib.sha1(str(name).encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}_{ascii_slug[:48]}"


def markdown_fields(text):
    out = {}
    for raw in str(text or "").splitlines():
        match = FIELD_RE.match(raw)
        if match:
            out[clean_name(match.group(1)).lower()] = match.group(2).strip()
    return out


def field_value(fields, *names):
    for name in names:
        key = name.lower()
        if fields.get(key):
            return fields[key]
    return ""


def split_values(value):
    value = re.sub(r"^[①②③④⑤⑥⑦⑧⑨]+", "", str(value or ""))
    rows = [clean_name(x) for x in re.split(r"[；;、]|\s+[|/]\s+|[①②③④⑤⑥⑦⑧⑨]", value)]
    return [x for x in rows if x]


def machine_value(blueprint, key):
    match = re.search(rf"^\s*[-*]\s*{re.escape(key)}\s*[:：]\s*(.+)$", blueprint, re.M | re.I)
    return match.group(1).strip() if match else ""


def extract_palette(blueprint):
    value = machine_value(blueprint, "palette_anchor")
    if value:
        return split_values(value.replace(",", "、"))
    return []


def extract_global_style(blueprint):
    value = machine_value(blueprint, "global_style")
    if value:
        return value
    match = re.search(r"画风[^:：\n]*[:：]\s*\*{0,2}(.+?)\*{0,2}\s*$", blueprint, re.M)
    return match.group(1).strip() if match else "待从视觉蓝图确认"


def extract_anchor(text, fields):
    value = field_value(fields, "锚点句", "身份锚点", "lead_identity_anchor")
    if value:
        return clean_name(value)
    match = re.search(r"锚点句[^\n]*\n[「\"]?([^」\"\n]+)", text)
    if match:
        return match.group(1).strip(" 「」\"")
    parts = [field_value(fields, "固定外貌", "外貌"), field_value(fields, "固定服装", "服装")]
    return "；".join(x for x in parts if x) or "身份锚点待补"


def existing_reference_paths(root, target_id, names=(), seed_paths=()):
    keys = [re.sub(r"\W+", "", str(x).lower()) for x in (target_id, *names) if x]
    paths = list(seed_paths or [])
    for base in REFERENCE_SEARCH_DIRS:
        abs_base = os.path.join(root, base)
        if not os.path.isdir(abs_base):
            continue
        for path in glob.glob(os.path.join(abs_base, "**", "*"), recursive=True):
            if not os.path.isfile(path) or not path.lower().endswith(IMAGE_EXTS):
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            haystack = re.sub(r"\W+", "", rel.lower())
            if any(key and key in haystack for key in keys):
                paths.append(rel)
    seen = set()
    return [p for p in paths if p and not (p in seen or seen.add(p)) and os.path.exists(os.path.join(root, p))]


def requirement_status(existing, views, text_ready=False):
    count = len(existing)
    required = len(views)
    status = "ready" if required and count >= required else ("partial" if count else ("text_only" if text_ready else "planned"))
    return {
        "status": status,
        "text_card_ready": bool(text_ready),
        "image_reference_ready": status == "ready",
        "coverage": {"existing_count": count, "required_count": required, "missing_count": max(0, required - count)},
        "missing_views": views[count:],
    }


def build_identity_registry(root):
    blueprint = mv_utils.read_text(os.path.join(root, "视觉蓝图.md"))
    docs = read_all(os.path.join(root, "设定", "characters", "*.md"))
    identities = []
    groups = []
    states = []
    for index, (path, text) in enumerate(docs):
        fields = markdown_fields(text)
        heading = next((clean_name(m.group(1)) for line in text.splitlines() if (m := HEADING_RE.match(line))), "")
        name = clean_name(os.path.splitext(os.path.basename(path))[0]) or heading or f"角色{index + 1}"
        char_id = stable_id("CHAR", name)
        group_id = stable_id("REF", name)
        anchor = extract_anchor(text, fields)
        refs = existing_reference_paths(root, char_id, (name, heading, anchor))
        variants = split_values(field_value(fields, "形态变体", "状态变体", "allowed_variants")) or ["默认态"]
        forbidden = split_values(field_value(fields, "禁止漂移", "forbidden_drift")) or ["换脸", "换发型", "无依据换服装", "新增无关人物", "文字/logo/水印"]
        role = "lead_performer" if index == 0 else "supporting_performer"
        identities.append({
            "id": char_id, "role": role, "display_name": name, "anchor": anchor,
            "reference_group": group_id, "reference_images": refs,
            "allowed_variants": variants, "forbidden_drift": forbidden,
            "source": os.path.relpath(path, root).replace(os.sep, "/"),
        })
        groups.append({
            "id": group_id, "identity_id": char_id, "status": "ready" if len(refs) >= 3 else ("partial" if refs else "planned"),
            "purpose": f"锁定{name}的脸、发型、服装轮廓、体态和标志配饰", "paths": refs,
            "coverage_note": "正式包建议正面、侧面/三分之二脸、全身和关键状态参考。",
        })
        for variant in variants:
            states.append({"state_id": stable_id("STATE", f"{name}_{variant}"), "identity_id": char_id, "name": variant, "anchor": anchor})

    if not identities:
        fields = markdown_fields(blueprint)
        name = field_value(fields, "主角", "主唱", "lead") or "主角"
        char_id = stable_id("CHAR", name)
        group_id = stable_id("REF", name)
        anchor = machine_value(blueprint, "lead_identity_anchor") or name
        refs = existing_reference_paths(root, char_id, (name, anchor))
        identities.append({"id": char_id, "role": "lead_performer", "display_name": name, "anchor": anchor,
                           "reference_group": group_id, "reference_images": refs, "allowed_variants": ["默认态"],
                           "forbidden_drift": ["换脸", "换发型", "无依据换服装", "新增无关人物", "文字/logo/水印"],
                           "source": "视觉蓝图.md"})
        groups.append({"id": group_id, "identity_id": char_id, "status": "partial" if refs else "planned",
                       "purpose": f"锁定{name}身份", "paths": refs, "coverage_note": "需补多角度正式定妆。"})
        states.append({"state_id": stable_id("STATE", f"{name}_默认态"), "identity_id": char_id, "name": "默认态", "anchor": anchor})

    return {
        "schema_version": 2, "kind": "mv_identity_registry", "generated_at": date.today().isoformat(),
        "title": (mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}).get("title") or os.path.basename(root),
        "lead_id": identities[0]["id"], "identities": identities, "identity_states": states,
        "global_style": extract_global_style(blueprint), "palette_anchor": extract_palette(blueprint),
        "reference_groups": groups,
    }


def parse_location_assets(root):
    assets = []
    for path, text in read_all(os.path.join(root, "设定", "locations", "*.md")):
        headings = list(re.finditer(r"^##+\s+(.+?)\s*$", text, re.M))
        for index, match in enumerate(headings):
            name = clean_name(match.group(1))
            body_end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            body = text[match.end():body_end].strip()
            if name:
                assets.append({"id": stable_id("LOC", name), "type": "location", "name": name,
                               "anchor": next((x.strip() for x in body.splitlines() if x.strip()), body[:240]),
                               "status": "ready", "source": os.path.relpath(path, root).replace(os.sep, "/")})
    return assets


def build_asset_registry(root):
    assets = parse_location_assets(root)
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    by_id = {a["id"]: a for a in assets}
    for clip in plan.get("clips", []):
        shot = clip.get("shot_design") or {}
        loc_name = shot.get("location_name")
        loc_id = shot.get("location_id") or (stable_id("LOC", loc_name) if loc_name else "")
        if loc_id and loc_id not in by_id:
            by_id[loc_id] = {"id": loc_id, "type": "location", "name": loc_name or loc_id,
                             "anchor": shot.get("production_design") or shot.get("lighting") or "场景锚点待补", "status": "text_only"}
        for asset_id in clip.get("asset_ids") or []:
            if asset_id and asset_id not in by_id:
                prefix = str(asset_id).split("_", 1)[0].upper()
                kind = {"LOC": "location", "PROP": "prop", "VFX": "vfx"}.get(prefix, "asset")
                by_id[asset_id] = {"id": asset_id, "type": kind, "name": asset_id,
                                   "anchor": "资产锚点待补", "status": "planned"}
    return {"schema_version": 2, "kind": "mv_asset_registry", "generated_at": date.today().isoformat(), "assets": list(by_id.values())}


def build_reference_plan(root, identity_registry, asset_registry):
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    lead_id = identity_registry.get("lead_id")
    lead = next((x for x in identity_registry.get("identities", []) if x.get("id") == lead_id), {})
    lead_refs = lead.get("reference_images") or []
    known_assets = {a.get("id") for a in asset_registry.get("assets", [])}
    rows = []
    for clip in plan.get("clips", []):
        contract = clip.get("identity_contract") or {}
        identity_ids = clip.get("identity_ids") or ([contract.get("lead_id") or lead_id] if lead_id else [])
        asset_ids = [x for x in (clip.get("asset_ids") or []) if x in known_assets]
        refs = list(clip.get("reference_inputs") or [])
        for path in lead_refs:
            if not any(r.get("path") == path for r in refs):
                refs.append({"path": path, "use": "lead_identity"})
        for asset_id in asset_ids:
            if not any(r.get("asset_id") == asset_id for r in refs):
                refs.append({"asset_id": asset_id, "use": "asset_anchor"})
        file_refs = [r.get("path") for r in refs if r.get("path")]
        rows.append({"clip_id": clip.get("clip_id"), "identity_ids": [x for x in identity_ids if x],
                     "asset_ids": asset_ids, "reference_inputs": refs,
                     "status": "ready" if file_refs and all(os.path.exists(os.path.join(root, p)) for p in file_refs) else "planned"})
    return {"schema_version": 2, "kind": "mv_reference_plan", "generated_at": date.today().isoformat(),
            "identity_registry": "设定/identity_registry.json", "asset_registry": "设定/asset_registry.json", "clips": rows}


def build_reference_requirements(root, identity_registry, asset_registry, reference_plan):
    requirements = []
    for ident in identity_registry.get("identities", []):
        views = ["正面中性定妆", "侧脸/三分之二脸", "全身含服装比例", "主要表演情绪特写"]
        if len(ident.get("allowed_variants") or []) > 1:
            views.append("每个关键状态变体定妆")
        existing = existing_reference_paths(root, ident.get("id"), (ident.get("display_name"), ident.get("anchor")), ident.get("reference_images"))
        requirements.append({"target_id": ident.get("id"), "type": "identity",
                             **requirement_status(existing, views, bool(ident.get("anchor"))),
                             "existing_paths": existing, "required_views": views,
                             "why": "锁脸、发型、服装、体态和状态变体。"})
    for asset in asset_registry.get("assets", []):
        kind = asset.get("type")
        views = (["空镜远景", "人物入场中景", "同场景光线/空间参考"] if kind == "location"
                 else ["正侧视", "交互/手持近景", "材质和高光参考"] if kind == "prop"
                 else ["形状参考", "颜色/材质参考", "运动/转场状态参考"])
        existing = existing_reference_paths(root, asset.get("id"), (asset.get("name"), asset.get("anchor")))
        requirements.append({"target_id": asset.get("id"), "type": kind,
                             **requirement_status(existing, views, bool(asset.get("anchor"))),
                             "existing_paths": existing, "required_views": views,
                             "why": "锁场景空间、道具形状/材质或 VFX 运动形态。"})
    priority = [r.get("clip_id") for r in reference_plan.get("clips", []) if r.get("identity_ids") or r.get("asset_ids")]
    return {"schema_version": 2, "kind": "mv_reference_requirements", "generated_at": date.today().isoformat(),
            "requirements": requirements, "key_clip_reference_priorities": priority,
            "notes": ["正式批量生成前补齐关键身份、状态变体、交互道具和复用场景参考。"]}


def write_reference_requirements(root, payload):
    mv_utils.write_json_stable(os.path.join(root, "设定", "reference_requirements.json"), payload)
    lines = ["# reference requirements", "", "| Target | Type | Status | Image refs | Missing Views | Why |", "|---|---|---|---:|---|---|"]
    for row in payload.get("requirements", []):
        coverage = row.get("coverage") or {}
        image_refs = f"{coverage.get('existing_count', 0)}/{coverage.get('required_count', 0)}"
        lines.append(f"| {row.get('target_id')} | {row.get('type')} | {row.get('status')} | {image_refs} | {'; '.join(row.get('missing_views') or []) or 'none'} | {row.get('why')} |")
    mv_utils.write_text(os.path.join(root, "设定", "reference_requirements.md"), "\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="生成项目驱动的 MV 身份/资产/状态/参考注册表")
    ap.add_argument("project_root")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    identity = build_identity_registry(root)
    assets = build_asset_registry(root)
    refs = build_reference_plan(root, identity, assets)
    requirements = build_reference_requirements(root, identity, assets, refs)
    # 幂等写盘：注册表被 inherit_contract 的 inputs_sha256 绑定，纯 generated_at 变化不得换 hash。
    mv_utils.write_json_stable(os.path.join(root, "设定", "identity_registry.json"), identity)
    mv_utils.write_json_stable(os.path.join(root, "设定", "asset_registry.json"), assets)
    mv_utils.write_json_stable(os.path.join(root, "分镜", "reference_plan.json"), refs)
    write_reference_requirements(root, requirements)
    print(f"[ok] identity/assets/reference registry → {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
