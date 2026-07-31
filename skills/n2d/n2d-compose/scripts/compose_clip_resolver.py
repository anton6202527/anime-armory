#!/usr/bin/env python3
"""Resolve the video version that compose must place on V1.

Hybrid routing can deliberately create a neutral-mouth base plate first.  Once
the route requires a post lipsync pass, compose must use the derived lipsync
asset and must not silently fall back to the base plate.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def route_index(root: Path, episode: str) -> Dict[str, Dict[str, Any]]:
    path = root / "出视频" / episode / "prompt" / "video_model_routes.json"
    payload = _load_json(path)
    routes = payload.get("routes") if isinstance(payload, Mapping) else []
    return {
        str(row.get("clip_id") or row.get("id") or ""): dict(row)
        for row in routes or []
        if isinstance(row, Mapping) and str(row.get("clip_id") or row.get("id") or "").strip()
    }


def requires_post_lipsync(route: Mapping[str, Any]) -> bool:
    return bool(
        route.get("post_lipsync_required") is True
        or str(route.get("audio_strategy") or "").strip() == "base_video_then_post_lipsync"
    )


def expected_lipsync_path(root: Path, episode: str, clip_id: str, route: Mapping[str, Any]) -> Path:
    declared = str(route.get("post_lipsync_output") or "").strip()
    if declared:
        path = Path(declared)
        return path if path.is_absolute() else root / path
    return root / "出视频" / episode / "视频_lipsync" / f"{clip_id}_lipsync.mp4"


def resolve_clip_video(
    root: Path,
    episode: str,
    clip_id: str,
    base_video: str | Path | None,
    routes: Mapping[str, Mapping[str, Any]],
    *,
    allow_base_preview: bool = False,
) -> Tuple[Path | None, str]:
    """Return `(path, source_kind)` or raise when a required pass is missing."""
    route = routes.get(str(clip_id)) or {}
    base = Path(base_video) if base_video else None
    if not requires_post_lipsync(route):
        return base, "base_or_final"
    lipsync = expected_lipsync_path(root, episode, str(clip_id), route)
    if lipsync.is_file():
        return lipsync, "post_lipsync"
    if allow_base_preview:
        return base, "base_preview_waiver"
    raise FileNotFoundError(
        f"{clip_id} 仍是 neutral-mouth base plate，缺后期口型成片：{lipsync}"
    )

