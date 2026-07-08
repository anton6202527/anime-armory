#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build MV identity / asset registries and per-clip reference plan.

This is the MV line's own lightweight consistency layer. It uses stable IDs and
reference groups while staying fully self-contained.
"""
import argparse
import glob
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


PALETTE_NAMES = ("白", "月白", "墨", "青", "冷蓝", "暖灯", "金", "霓虹", "红", "绿")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
REFERENCE_SEARCH_DIRS = (
    "设定/reference_images",
    "出图/共享/图片",
    "出图/段落/图片",
)
TARGET_ALIASES = {
    "CHAR_LEAD_YOUNG": ("仗剑少年", "少年", "主角", "定妆_少年", "定妆_主角"),
    "CHAR_LEAD_ADULT": ("成年", "多年后", "剑客", "鬓染霜"),
    "PROP_QINGFENG_SWORD": ("青锋", "长剑", "剑", "拔剑", "仗剑"),
    "LOC_MOUNTAIN_GATE": ("山门", "石阶", "下山", "立山门"),
    "LOC_CLOUD_SEA": ("云海", "山巅", "崖", "仗剑"),
    "LOC_INN": ("客栈", "灯火", "酒"),
    "LOC_BAMBOO_FOREST": ("竹林", "多年后"),
    "LOC_SNOWFIELD": ("雪原", "月下", "荒野", "残碑"),
    "VFX_SWORD_LIGHT": ("剑光", "刀光", "青白冷光", "冷光"),
}


def read_all(pattern):
    rows = []
    for path in sorted(glob.glob(pattern)):
        rows.append((path, mv_utils.read_text(path)))
    return rows


def extract_anchor(character_text):
    m = re.search(r"锚点句[^\n]*\n[「\"]?([^」\"\n]+)", character_text)
    if m:
        return m.group(1).strip(" 「」\"")
    m = re.search(r"白衣束发[^。\n]+", character_text)
    return m.group(0).strip() if m else "主角身份锚点待补"


def extract_palette(blueprint):
    rows = []
    for name in PALETTE_NAMES:
        if name in blueprint and name not in rows:
            rows.append(name)
    return rows or ["主色待补"]


def first_existing(root, rels):
    for rel in rels:
        if os.path.exists(os.path.join(root, rel)):
            return rel
    return ""


def normalize_match_key(value):
    return re.sub(r"[\s_\-./（）()]+", "", str(value or "").lower())


def unique_existing(root, paths):
    seen = set()
    out = []
    for rel in paths:
        if not rel:
            continue
        rel = rel.replace(os.sep, "/")
        if rel in seen:
            continue
        if os.path.exists(os.path.join(root, rel)):
            out.append(rel)
            seen.add(rel)
    return out


def existing_reference_paths(root, target_id, names=(), seed_paths=()):
    keys = [target_id, *(TARGET_ALIASES.get(target_id) or ()), *names]
    keys = [normalize_match_key(k) for k in keys if normalize_match_key(k)]
    rels = list(seed_paths or [])
    for base in REFERENCE_SEARCH_DIRS:
        abs_base = os.path.join(root, base)
        if not os.path.isdir(abs_base):
            continue
        for path in sorted(glob.glob(os.path.join(abs_base, "**", "*"), recursive=True)):
            if not os.path.isfile(path) or not path.lower().endswith(IMAGE_EXTS):
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            haystack = normalize_match_key(rel)
            if any(key and key in haystack for key in keys):
                rels.append(rel)
    return unique_existing(root, rels)


def requirement_status(existing_paths, required_views, text_card_ready=False):
    existing_count = len(existing_paths or [])
    required_count = len(required_views or [])
    image_reference_ready = required_count > 0 and existing_count >= required_count
    if image_reference_ready:
        status = "ready"
    elif existing_count:
        status = "partial"
    elif text_card_ready:
        status = "text_only"
    else:
        status = "planned"
    return {
        "status": status,
        "text_card_ready": bool(text_card_ready),
        "image_reference_ready": image_reference_ready,
        "coverage": {
            "existing_count": existing_count,
            "required_count": required_count,
            "missing_count": max(0, required_count - existing_count),
        },
        "missing_views": list((required_views or [])[existing_count:]),
    }


def build_identity_registry(root):
    char_docs = read_all(os.path.join(root, "设定", "characters", "*.md"))
    blueprint = mv_utils.read_text(os.path.join(root, "视觉蓝图.md"))
    char_text = "\n".join(text for _path, text in char_docs)
    anchor = extract_anchor(char_text or blueprint)
    makeup = first_existing(root, [
        "出图/共享/图片/定妆_少年_常态.png",
        "出图/共享/图片/定妆_主角.png",
    ])
    return {
        "schema_version": 1,
        "kind": "mv_identity_registry",
        "generated_at": date.today().isoformat(),
        "title": (mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}).get("title") or os.path.basename(root),
        "lead_id": "CHAR_LEAD_YOUNG",
        "identities": [
            {
                "id": "CHAR_LEAD_YOUNG",
                "role": "lead_performer",
                "display_name": "仗剑少年",
                "anchor": anchor,
                "reference_group": "REF_LEAD_YOUNG",
                "reference_images": [makeup] if makeup else [],
                "allowed_variants": ["少年态", "风雪/战斗尘土", "表演特写"],
                "forbidden_drift": ["换脸", "换发型", "换主服装", "新增无关人物", "现代服饰", "文字/logo/水印"],
            },
            {
                "id": "CHAR_LEAD_ADULT",
                "role": "bridge_variant",
                "display_name": "多年后剑客",
                "anchor": "鬓染霜、白袍泛旧、眼神沉静，仍背同一柄青锋长剑",
                "reference_group": "REF_LEAD_ADULT",
                "reference_images": [],
                "allowed_variants": ["bridge/多年后"],
                "forbidden_drift": ["改成不同人物", "丢失青锋长剑", "现代服饰"],
            },
        ],
        "global_style": "国风武侠 · 水墨意境 + 电影级光影",
        "palette_anchor": extract_palette(blueprint),
        "reference_groups": [
            {
                "id": "REF_LEAD_YOUNG",
                "status": "partial" if makeup else "planned",
                "purpose": "主角脸、服装、长剑、整体比例",
                "paths": [makeup] if makeup else [],
                "coverage_note": "正式包需多角度定妆；单张 demo 定妆只算 partial。",
            },
            {
                "id": "REF_LEAD_ADULT",
                "status": "planned",
                "purpose": "bridge 成年态，只在多年后段落使用",
                "paths": [],
            },
        ],
    }


def build_asset_registry(root):
    locations = mv_utils.read_text(os.path.join(root, "设定", "locations", "场景集.md"))
    return {
        "schema_version": 1,
        "kind": "mv_asset_registry",
        "generated_at": date.today().isoformat(),
        "assets": [
            {"id": "PROP_QINGFENG_SWORD", "type": "prop", "name": "青锋长剑", "anchor": "墨色剑鞘缠青绳，青锋寒光", "status": "planned"},
            {"id": "LOC_MOUNTAIN_GATE", "type": "location", "name": "山门石阶", "anchor": "青灰石阶、晨雾、古朴山门、松柏挂霜", "status": "ready" if "山门" in locations else "planned"},
            {"id": "LOC_CLOUD_SEA", "type": "location", "name": "云海崖边", "anchor": "云海翻涌、逆光、崖边剪影", "status": "ready" if "云海" in locations else "planned"},
            {"id": "LOC_INN", "type": "location", "name": "江湖客栈", "anchor": "昏黄油灯、木质客栈、江湖客、烟火气", "status": "ready" if "客栈" in locations else "planned"},
            {"id": "LOC_BAMBOO_FOREST", "type": "location", "name": "竹林", "anchor": "青翠竹林、光斑、薄雾", "status": "ready" if "竹林" in locations else "planned"},
            {"id": "LOC_SNOWFIELD", "type": "location", "name": "雪原/月下荒野", "anchor": "苍茫雪原、冷月、孤树残碑、冷蓝调", "status": "ready" if "雪原" in locations else "planned"},
            {"id": "VFX_SWORD_LIGHT", "type": "vfx", "name": "剑光/刀光", "anchor": "青白冷光，形状干净，不生成文字", "status": "planned"},
        ],
    }


def infer_location_id(clip):
    blob = " ".join(str(clip.get(k, "")) for k in ("section", "lyric_hint", "visual_motif"))
    cont = clip.get("continuity") or {}
    blob += " " + " ".join(str(cont.get(k, "")) for k in ("start_state", "action", "end_state"))
    if any(k in blob for k in ("山门", "石阶", "下山")):
        return "LOC_MOUNTAIN_GATE"
    if any(k in blob for k in ("云海", "山巅", "崖")):
        return "LOC_CLOUD_SEA"
    if any(k in blob for k in ("客栈", "灯火", "酒")):
        return "LOC_INN"
    if any(k in blob for k in ("竹林", "多年后")):
        return "LOC_BAMBOO_FOREST"
    if any(k in blob for k in ("雪", "月光", "荒野", "伤")):
        return "LOC_SNOWFIELD"
    return "LOC_MOUNTAIN_GATE"


def build_reference_plan(root, identity_registry, asset_registry):
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    clips = []
    lead_ref = identity_registry["reference_groups"][0]["paths"]
    for clip in plan.get("clips", []):
        location_id = infer_location_id(clip)
        refs = []
        for path in lead_ref:
            refs.append({"path": path, "use": "lead_identity"})
        refs.append({"asset_id": location_id, "use": "scene_anchor"})
        if "剑" in json.dumps(clip, ensure_ascii=False) or clip.get("section"):
            refs.append({"asset_id": "PROP_QINGFENG_SWORD", "use": "prop_anchor"})
        clips.append({
            "clip_id": clip.get("clip_id"),
            "identity_ids": ["CHAR_LEAD_ADULT"] if "bridge" in str(clip.get("section", "")).lower() else ["CHAR_LEAD_YOUNG"],
            "asset_ids": [location_id, "PROP_QINGFENG_SWORD"],
            "reference_inputs": refs,
            "status": "ready" if all(not r.get("path") or os.path.exists(os.path.join(root, r["path"])) for r in refs) else "planned",
        })
    return {
        "schema_version": 1,
        "kind": "mv_reference_plan",
        "generated_at": date.today().isoformat(),
        "identity_registry": "设定/identity_registry.json",
        "asset_registry": "设定/asset_registry.json",
        "clips": clips,
    }


def build_reference_requirements(root, identity_registry, asset_registry, reference_plan):
    requirements = []
    groups = {g.get("id"): g for g in identity_registry.get("reference_groups", [])}
    for ident in identity_registry.get("identities", []):
        group = groups.get(ident.get("reference_group"), {})
        paths = group.get("paths") or []
        if ident.get("id") == "CHAR_LEAD_YOUNG":
            needed = [
                "正面中性定妆",
                "半身情绪特写",
                "侧脸/三分之二脸",
                "全身含服装比例",
                "手握青锋长剑近景",
            ]
        elif ident.get("id") == "CHAR_LEAD_ADULT":
            needed = [
                "成年态正面定妆",
                "成年态半身情绪特写",
                "成年态全身含旧白袍和同一柄剑",
            ]
        else:
            needed = ["正面定妆", "半身", "全身"]
        existing = existing_reference_paths(
            root,
            ident.get("id"),
            names=(ident.get("display_name"), ident.get("anchor")),
            seed_paths=paths,
        )
        status_info = requirement_status(existing, needed, text_card_ready=bool(ident.get("anchor")))
        requirements.append({
            "target_id": ident.get("id"),
            "type": "identity",
            **status_info,
            "existing_paths": existing,
            "required_views": needed,
            "why": "锁脸、服装、年龄变体和图生视频首帧继承。",
        })

    for asset in asset_registry.get("assets", []):
        if asset.get("type") == "location":
            views = ["空镜远景", "人物入场中景", "同场景光线参考"]
        elif asset.get("type") == "prop":
            views = ["道具正侧视", "手持近景", "高光/反光参考"]
        else:
            views = ["形状参考", "颜色参考", "转场中遮挡参考"]
        existing = existing_reference_paths(
            root,
            asset.get("id"),
            names=(asset.get("name"), asset.get("anchor")),
        )
        status_info = requirement_status(
            existing,
            views,
            text_card_ready=asset.get("status") == "ready" or bool(asset.get("anchor")),
        )
        requirements.append({
            "target_id": asset.get("id"),
            "type": asset.get("type"),
            **status_info,
            "existing_paths": existing,
            "required_views": views,
            "why": "锁场景、道具和 VFX 形状，降低跨 clip 漂移。",
        })

    key_clips = []
    for row in reference_plan.get("clips", []):
        cid = row.get("clip_id")
        ids = set(row.get("asset_ids") or [])
        if "PROP_QINGFENG_SWORD" in ids or any("ADULT" in x for x in row.get("identity_ids") or []):
            key_clips.append(cid)
    return {
        "schema_version": 1,
        "kind": "mv_reference_requirements",
        "generated_at": date.today().isoformat(),
        "requirements": requirements,
        "key_clip_reference_priorities": key_clips,
        "notes": [
            "正式整首 MV 出图前先补 planned/关键参考，尤其成年态、手部/剑和副歌高光镜。",
            "已有 demo 可用作创意方向，不等于正式 reference pack 完整。",
        ],
    }


def write_reference_requirements(root, payload):
    mv_utils.write_json(os.path.join(root, "设定", "reference_requirements.json"), payload)
    lines = [
        "# reference requirements",
        "",
        "| Target | Type | Status | Image refs | Missing Views | Why |",
        "|---|---|---|---:|---|---|",
    ]
    for row in payload.get("requirements", []):
        coverage = row.get("coverage") or {}
        image_refs = f"{coverage.get('existing_count', len(row.get('existing_paths') or []))}/{coverage.get('required_count', len(row.get('required_views') or []))}"
        missing = "; ".join(row.get("missing_views") or []) or "none"
        lines.append(
            f"| {row.get('target_id')} | {row.get('type')} | {row.get('status')} | "
            f"{image_refs} | {missing} | {row.get('why')} |"
        )
    lines.extend(["", "## Existing Paths"])
    for row in payload.get("requirements", []):
        lines.append(f"- {row.get('target_id')}:")
        paths = row.get("existing_paths") or []
        if paths:
            lines.extend(f"  - {p}" for p in paths)
        else:
            lines.append("  - none")
    lines.extend(["", "## Key Clip Priorities"])
    for cid in payload.get("key_clip_reference_priorities", []):
        lines.append(f"- {cid}")
    mv_utils.write_text(os.path.join(root, "设定", "reference_requirements.md"), "\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Generate MV identity/asset registries and reference plan")
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
    mv_utils.write_json(os.path.join(root, "设定", "identity_registry.json"), identity)
    mv_utils.write_json(os.path.join(root, "设定", "asset_registry.json"), assets)
    mv_utils.write_json(os.path.join(root, "分镜", "reference_plan.json"), refs)
    write_reference_requirements(root, requirements)
    print("[ok] identity registry → 设定/identity_registry.json")
    print("[ok] asset registry → 设定/asset_registry.json")
    print("[ok] reference plan → 分镜/reference_plan.json")
    print("[ok] reference requirements → 设定/reference_requirements.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
