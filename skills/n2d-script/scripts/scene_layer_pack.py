#!/usr/bin/env python3
"""Scaffold reusable scene layer packs for large/flight spectacle scenes."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import SCENE_LAYER_PACK_KIND, infer_spectacle_type  # noqa: E402


LOC_RE = re.compile(r"\bLOC_[A-Za-z0-9_]+\b")


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def make_clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("clip_id") or clip.get("id") or clip.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{idx:02d}"


def load_storyboard(root: Path, ep: str) -> Dict[str, Any]:
    path = root / "脚本" / ep / "storyboard.json"
    if not path.is_file():
        raise FileNotFoundError(f"storyboard not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("storyboard.json top-level must be an object")
    return data


def _flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return " ".join(_flatten(v) for v in value)
    return str(value)


def contract_for(clip: Mapping[str, Any]) -> Dict[str, Any]:
    for key in ("large_scene_contract", "spectacle_contract", "template_contract"):
        value = clip.get(key)
        if isinstance(value, dict):
            return dict(value)
    return {}


def loc_id_for(clip: Mapping[str, Any], contract: Mapping[str, Any], idx: int) -> str:
    for key in ("reuse_asset_id", "loc", "location_id", "scene_id"):
        value = str(contract.get(key) or clip.get(key) or "").strip()
        if value.startswith("LOC_"):
            return value
    found = LOC_RE.findall(json.dumps(clip, ensure_ascii=False))
    if found:
        return found[0]
    return f"LOC_UNASSIGNED_{idx:02d}"


def pack_path(root: Path, loc_id: str) -> Path:
    return root / "设定库" / "scene_layers" / loc_id / "scene_layer_pack.json"


def build_pack(root: Path, ep: str, loc_id: str, clips: List[Mapping[str, Any]]) -> Dict[str, Any]:
    first = clips[0] if clips else {}
    contract = first.get("contract") if isinstance(first.get("contract"), Mapping) else contract_for(first)
    return {
        "kind": SCENE_LAYER_PACK_KIND,
        "version": 1,
        "loc_id": loc_id,
        "source_episode": ep,
        "source_clips": [item.get("clip_id") for item in clips],
        "floorplan": {
            "status": "planned",
            "path": f"设定库/scene_layers/{loc_id}/floorplan.png",
            "notes": "标出主轴线、入口、地标、角色默认动线；无图时至少在 notes 写文字平面。",
        },
        "landmark_anchor": contract.get("landmark_anchor") or "待补：本 LOC 可跨镜识别的地标锚点",
        "scale_reference": contract.get("scale_reference") or "待补：人物/建筑/山体/云层比例尺",
        "depth_planes": contract.get("depth_planes") or ["foreground", "midground", "background"],
        "parallax_planes": contract.get("parallax_planes") or contract.get("parallax_layers") or [
            {"plane": "foreground", "motion": "fast lateral pass"},
            {"plane": "midground", "motion": "medium drift"},
            {"plane": "background", "motion": "slow drift"},
        ],
        "crowd_strategy": contract.get("crowd_strategy") or "复杂人群默认剪影/背身/雾化/分层合成，避免清晰逐人生成。",
        "atmosphere_lut": contract.get("atmosphere_lut") or "待补：本 LOC 统一色温/雾气/对比度/LUT。",
        "reusable_bg_keyframes": contract.get("reusable_bg_keyframes") or [
            f"设定库/scene_layers/{loc_id}/keyframes/wide.png",
            f"设定库/scene_layers/{loc_id}/keyframes/mid.png",
            f"设定库/scene_layers/{loc_id}/keyframes/detail.png",
        ],
        "consistency_rules": [
            "reuse this pack for all large_establishing/flight/chase shots in the same LOC",
            "do not change landmark_anchor or scale_reference without forking a new loc_id",
            "video prompts should move parallax/depth layers instead of regenerating the whole place",
        ],
    }


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    storyboard = load_storyboard(root, ep)
    clips = storyboard.get("clips") or []
    if not isinstance(clips, list):
        raise ValueError("storyboard.json clips must be a list")
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        kind = infer_spectacle_type(clip)
        if kind not in {"large_establishing", "flight"}:
            continue
        contract = contract_for(clip)
        loc_id = loc_id_for(clip, contract, idx)
        grouped.setdefault(loc_id, []).append({
            "clip_id": make_clip_id(clip, idx),
            "spectacle_type": kind,
            "source_text": _flatten(clip)[:240],
            **({"contract": contract} if contract else {}),
        })
    packs = []
    for loc_id, loc_clips in sorted(grouped.items()):
        pack = build_pack(root, ep, loc_id, loc_clips)
        packs.append({
            "loc_id": loc_id,
            "path": os.path.relpath(pack_path(root, loc_id), root),
            "source_clips": [c["clip_id"] for c in loc_clips],
            "pack": pack,
        })
    return {
        "kind": "n2d_scene_layer_pack_plan",
        "version": 1,
        "root": str(root),
        "episode": ep,
        "packs": packs,
        "summary": {"scene_layer_packs": len(packs), "source_clips": sum(len(p["source_clips"]) for p in packs)},
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 场景分层资产包计划",
        "",
        f"- episode: {plan.get('episode')}",
        f"- scene_layer_packs: {(plan.get('summary') or {}).get('scene_layer_packs', 0)}",
        "",
        "| LOC | Clips | Pack |",
        "|---|---|---|",
    ]
    for item in plan.get("packs") or []:
        lines.append(f"| {item.get('loc_id')} | {', '.join(item.get('source_clips') or [])} | {item.get('path')} |")
    return "\n".join(lines)


def write_plan(plan: Mapping[str, Any], root: Path, ep: str, *, write_packs: bool = True) -> Dict[str, Path]:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    out_json = prod / f"scene_layer_pack_plan_{ep}.json"
    out_md = prod / f"scene_layer_pack_plan_{ep}.md"
    out_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    paths: Dict[str, Path] = {"json": out_json, "markdown": out_md}
    if write_packs:
        for item in plan.get("packs") or []:
            if not isinstance(item, Mapping) or not isinstance(item.get("pack"), Mapping):
                continue
            path = root / str(item.get("path"))
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file():
                existing = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    merged = dict(item["pack"])
                    merged.update(existing)
                    item = {**item, "pack": merged}
            path.write_text(json.dumps(item["pack"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            paths[str(item.get("loc_id"))] = path
    return paths


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="scaffold scene layer packs for large/flight spectacle clips")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--no-packs", action="store_true", help="write only plan, not scene_layer_pack.json files")
    ap.add_argument("--markdown", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    plan = build_plan(root, ep)
    if ns.write:
        paths = write_plan(plan, root, ep, write_packs=not ns.no_packs)
        plan["written"] = {k: str(v) for k, v in paths.items()}
    print(render_markdown(plan) if ns.markdown else json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
