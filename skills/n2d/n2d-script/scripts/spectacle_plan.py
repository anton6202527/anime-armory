#!/usr/bin/env python3
"""Build production plans for high-dynamic and large-scale n2d shots."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import (  # noqa: E402
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    MOTION_CONTROL_MANIFEST_KIND,
    SPECTACLE_PLAN_KIND,
    default_degrade_plan,
    edit_cues_for_spectacle,
    infer_spectacle_type,
    missing_fields,
    motion_control_inputs_for_spectacle,
    premium_spectacle_passes,
    spectacle_recommendations,
    spectacle_required_fields,
)


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def storyboard_path(root: Path, ep: str) -> Path:
    return root / "脚本" / ep / "storyboard.json"


def output_json_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"spectacle_plan_{ep}.json"


def output_md_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"spectacle_plan_{ep}.md"


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
    path = storyboard_path(root, ep)
    if not path.is_file():
        raise FileNotFoundError(f"storyboard not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("storyboard.json top-level must be an object")
    return data


def spectacle_contract(clip: Mapping[str, Any], kind: str) -> Dict[str, Any]:
    if kind == "large_establishing":
        for key in ("large_scene_contract", "spectacle_contract", "template_contract"):
            value = clip.get(key)
            if isinstance(value, dict):
                return dict(value)
        return {}
    value = clip.get("template_contract")
    return dict(value) if isinstance(value, dict) else {}


def manifest_rel_path(ep: str, clip_id: str) -> str:
    return f"出视频/{ep}/control/{clip_id}/motion_control_manifest.json"


def control_dir_rel(ep: str, clip_id: str) -> str:
    return f"出视频/{ep}/control/{clip_id}"


INPUT_SPEC: Dict[str, Tuple[str, str]] = {
    "pose_sequence": ("openpose_or_dwpose", "openpose_%03d.png"),
    "depth_sequence": ("depth", "depth_%03d.png"),
    "instance_masks": ("instance_mask", "seg_%03d.png"),
    "contact_map": ("contact_map", "contact_map.json"),
    "camera_path": ("camera_path", "camera_path.json"),
    "spatial_path": ("spatial_path", "spatial_path.json"),
    "parallax_layers": ("parallax_layers", "parallax_layers.json"),
    "vfx_layers": ("vfx_layers", "vfx_layers.json"),
}
HIGH_ACTION_KINDS = set(ACTION_CHOREOGRAPHY_SHOT_TYPES)


def input_entry(ep: str, clip_id: str, key: str) -> Dict[str, str]:
    typ, fname = INPUT_SPEC[key]
    return {"type": typ, "status": "missing", "path": f"{control_dir_rel(ep, clip_id)}/{fname}"}


def build_motion_manifest(ep: str, clip_id: str, kind: str, existing: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    existing = existing or {}
    status = str(existing.get("status") or "").strip()
    if status not in {"ready", "degrade_only", "planned"}:
        status = "planned"
    old_inputs = existing.get("control_inputs") if isinstance(existing.get("control_inputs"), dict) else {}
    inputs: Dict[str, Any] = {}
    for key in motion_control_inputs_for_spectacle(kind):
        prior = old_inputs.get(key)
        inputs[key] = prior if isinstance(prior, dict) and str(prior.get("status") or "") in {"ready", "not_needed"} else input_entry(ep, clip_id, key)
    out = {
        "kind": MOTION_CONTROL_MANIFEST_KIND,
        "version": 1,
        "clip_id": clip_id,
        "spectacle_type": kind,
        "status": status,
        "control_inputs": inputs,
        "degrade_plan": existing.get("degrade_plan") or default_degrade_plan(kind),
        "notes": spectacle_recommendations(kind),
    }
    if kind == "fight_exchange":
        for field in ("contact_points", "occlusion_order", "body_part_ownership"):
            out[field] = existing.get(field) if existing.get(field) else []
    return out


def write_motion_manifest(root: Path, ep: str, clip_id: str, kind: str) -> Path:
    rel = manifest_rel_path(ep, clip_id)
    path = root / rel
    existing: Optional[Dict[str, Any]] = None
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            existing = data if isinstance(data, dict) else None
        except Exception:
            existing = None
    manifest = build_motion_manifest(ep, clip_id, kind, existing)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    storyboard = load_storyboard(root, ep)
    clips = storyboard.get("clips") or []
    if not isinstance(clips, list):
        raise ValueError("storyboard.json clips must be a list")
    rows: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        kind = infer_spectacle_type(clip)
        if not kind:
            continue
        clip_id = make_clip_id(clip, idx)
        contract = spectacle_contract(clip, kind)
        required = list(spectacle_required_fields(kind))
        missing = missing_fields(contract, required) if contract else required
        controls = list(motion_control_inputs_for_spectacle(kind))
        premium = premium_spectacle_passes(kind)
        rows.append({
            "clip_id": clip_id,
            "source_id": str(clip.get("id") or clip.get("clip_id") or clip.get("label") or clip_id),
            "spectacle_type": kind,
            "required_contract_fields": required,
            "missing_contract_fields": missing,
            "motion_control_manifest_path": manifest_rel_path(ep, clip_id) if controls else "",
            "control_inputs_required": controls,
            "keyframes_required": {
                "start_frame": True,
                "end_frame": kind in HIGH_ACTION_KINDS or bool(premium),
                "mid_anchors": kind in HIGH_ACTION_KINDS or bool(premium),
                "premium_policy": premium.get("keyframe_policy") if premium else {},
            },
            "edit_cue_profile": kind,
            "edit_cues": edit_cues_for_spectacle(kind, contract),
            "premium_passes": premium,
            "degrade_plan": str(contract.get("degrade_plan") or default_degrade_plan(kind)),
            "recommendations": spectacle_recommendations(kind),
        })
    return {
        "kind": SPECTACLE_PLAN_KIND,
        "version": 1,
        "root": str(root),
        "episode": ep,
        "clips": rows,
        "summary": {
            "spectacle_clips": len(rows),
            "contract_missing_clips": sum(1 for row in rows if row["missing_contract_fields"]),
            "motion_control_required_clips": sum(1 for row in rows if row["control_inputs_required"]),
        },
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 高动态/大场景制作计划",
        "",
        f"- episode: {plan.get('episode')}",
        f"- spectacle_clips: {(plan.get('summary') or {}).get('spectacle_clips', 0)}",
        "",
        "| Clip | 类型 | 缺契约字段 | 控制输入 | 回退/保真实现方案 |",
        "|---|---|---|---|---|",
    ]
    for row in plan.get("clips") or []:
        lines.append(
            "| {clip} | {kind} | {missing} | {inputs} | {degrade} |".format(
                clip=row.get("clip_id", ""),
                kind=row.get("spectacle_type", ""),
                missing=", ".join(row.get("missing_contract_fields") or []) or "-",
                inputs=", ".join(row.get("control_inputs_required") or []) or "-",
                degrade=str(row.get("degrade_plan") or "").replace("|", "/"),
            )
        )
    return "\n".join(lines)


def write_plan(plan: Mapping[str, Any], root: Path, ep: str) -> Dict[str, Path]:
    out_json = output_json_path(root, ep)
    out_md = output_md_path(root, ep)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    return {"json": out_json, "markdown": out_md}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build n2d spectacle/action production plan")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--write-manifests", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    plan = build_plan(root, ep)
    manifest_paths: List[str] = []
    if ns.write_manifests:
        for row in plan.get("clips") or []:
            inputs = row.get("control_inputs_required") or []
            if inputs:
                p = write_motion_manifest(root, ep, str(row["clip_id"]), str(row["spectacle_type"]))
                manifest_paths.append(str(p))
        plan["written_motion_control_manifests"] = manifest_paths
    if ns.write:
        paths = write_plan(plan, root, ep)
        plan["written"] = {k: str(v) for k, v in paths.items()}
    if ns.markdown:
        print(render_markdown(plan))
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
