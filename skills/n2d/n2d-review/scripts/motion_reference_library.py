#!/usr/bin/env python3
"""Maintain reusable motion references from passed spectacle clips."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import MOTION_REFERENCE_LIBRARY_KIND  # noqa: E402
from video_consistency_common import existing_media, load_json  # noqa: E402


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def library_path(root: Path) -> Path:
    return root / "生产数据" / "motion_reference_library.json"


def load_library(root: Path) -> Dict[str, Any]:
    data = load_json(str(library_path(root)))
    if isinstance(data, dict) and data.get("kind") == MOTION_REFERENCE_LIBRARY_KIND:
        return data
    return {"kind": MOTION_REFERENCE_LIBRARY_KIND, "version": 1, "references": []}


def _clip_media(media: Sequence[str], clip_id: str, root: Path) -> str:
    token = clip_id.lower().replace("_", "")
    for path in media:
        if token in os.path.basename(path).lower().replace("_", ""):
            return os.path.relpath(path, root)
    return ""


def build_updates(root: Path, ep: str) -> Dict[str, Any]:
    seq = load_json(str(root / "生产数据" / f"spectacle_sequence_plan_{ep}.json"))
    qc = load_json(str(root / "生产数据" / f"spectacle_video_qc_{ep}.json"))
    routes = load_json(str(root / "出视频" / ep / "prompt" / "video_model_routes.json"))
    media = existing_media(str(root), ep)
    if not isinstance(seq, dict):
        seq = {"sequences": []}
    if not isinstance(qc, dict):
        qc = {"checks": []}
    if not isinstance(routes, dict):
        routes = {"routes": []}
    checks = {str(row.get("clip")): row for row in qc.get("checks") or [] if isinstance(row, Mapping)}
    route_by_clip = {str(row.get("clip_id")): row for row in routes.get("routes") or [] if isinstance(row, Mapping)}
    updates: List[Dict[str, Any]] = []
    for sequence in seq.get("sequences") or []:
        if not isinstance(sequence, Mapping):
            continue
        for clip_id in sequence.get("clip_order") or []:
            clip_id = str(clip_id)
            check = checks.get(clip_id, {})
            evidence = str(check.get("evidence_status") or "")
            if evidence not in {"measured", "external_report", "vlm_verified", "tracked"}:
                continue
            route = route_by_clip.get(clip_id, {})
            ref_path = _clip_media(media, clip_id, root)
            if not ref_path:
                continue
            updates.append({
                "reference_id": f"{ep}_{clip_id}_{sequence.get('sequence_type')}",
                "episode": ep,
                "clip_id": clip_id,
                "sequence_id": sequence.get("sequence_id"),
                "spectacle_type": sequence.get("sequence_type"),
                "media_path": ref_path,
                "backend": route.get("primary_backend"),
                "quality_tier": route.get("quality_tier"),
                "evidence_status": evidence,
                "usage": ["reference_video_motion", "camera_motion_reference", "style_motion_reference"],
                "constraints": {
                    "characters": (sequence.get("subject_slots") or {}).get("characters") or [],
                    "assets": (sequence.get("asset_persistence") or {}).get("assets") or [],
                    "path_lock": sequence.get("path_lock") or {},
                },
            })
    return {"updates": updates, "skipped_unmeasured": len((qc.get("checks") or [])) - len(updates)}


def apply_updates(root: Path, updates: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    lib = load_library(root)
    refs = [r for r in lib.get("references") or [] if isinstance(r, dict)]
    by_id = {str(r.get("reference_id")): r for r in refs}
    for update in updates:
        rid = str(update.get("reference_id") or "")
        if not rid:
            continue
        by_id[rid] = dict(update)
    lib["references"] = sorted(by_id.values(), key=lambda r: str(r.get("reference_id") or ""))
    lib["summary"] = {
        "references": len(lib["references"]),
        "spectacle_types": sorted(set(str(r.get("spectacle_type") or "") for r in lib["references"] if r.get("spectacle_type"))),
    }
    path = library_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lib


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="register measured spectacle clips into motion_reference_library")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    result = build_updates(root, ep)
    if ns.write:
        lib = apply_updates(root, result["updates"])
        result["library_path"] = str(library_path(root))
        result["summary"] = lib.get("summary")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
