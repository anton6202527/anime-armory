#!/usr/bin/env python3
"""Style and face-QC policy helpers for n2d.

This module is intentionally small and dependency-free so stage gates, doctor,
and QC scripts can agree on when stylized projects should use StyleID.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional


STYLIZED_STYLE_MARKERS = (
    "二次元",
    "赛璐璐",
    "国漫",
    "国风",
    "漫剧",
    "厚涂",
    "水墨",
    "国风写意",
    "q版",
    "q 版",
    "插画",
    "动漫",
    "漫画",
    "韩漫",
    "日漫",
    "卡通",
    "条漫",
    "乙女",
    "战斗番",
    "美漫",
    "低多边形",
    "低模",
    "纸片",
    "剪影",
    "定格",
    "anime",
    "cartoon",
    "cel",
    "illustration",
    "stylized",
)

STYLEID_ENCODER_VALUES = {"styleid", "styleid_clip_l", "clip_l_styleid"}
AUTO_FACE_ENCODER_VALUES = {"自动按画风", "auto", "auto_by_style", "auto-by-style"}


def is_stylized_visual_style(style: object) -> bool:
    text = str(style or "").strip().lower()
    if not text:
        return False
    return any(marker.lower() in text for marker in STYLIZED_STYLE_MARKERS)


def normalize_face_encoder(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "arcface"
    low = text.lower().replace("-", "_").replace(" ", "_")
    if low in STYLEID_ENCODER_VALUES:
        return "styleid"
    if text in AUTO_FACE_ENCODER_VALUES or low in AUTO_FACE_ENCODER_VALUES:
        return "auto"
    if low in {"arcface", "insightface", "buffalo_l"}:
        return "arcface"
    return low


def styleid_model_status(env: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    source = os.environ if env is None else env
    path = str(source.get("N2D_STYLEID_MODEL", "") or "").strip()
    if not path:
        return {"status": "missing", "path": ""}
    if os.path.exists(path):
        return {"status": "ready", "path": path}
    return {"status": "not_found", "path": path}


def face_encoder_policy(
    visual_style: object,
    encoder_setting: object = "",
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Return project-level face-QC readiness for stylized projects.

    `status`:
    - `ready`: StyleID requested and model path exists.
    - `degraded`: stylized project or StyleID requested, but StyleID is not usable.
    - `standard`: non-stylized ArcFace path.
    """
    style = str(visual_style or "").strip()
    stylized = is_stylized_visual_style(style)
    encoder = normalize_face_encoder(encoder_setting)
    model = styleid_model_status(env)
    requested_styleid = encoder == "styleid"
    if requested_styleid and model["status"] == "ready":
        status = "ready"
    elif stylized or requested_styleid or encoder == "auto":
        status = "degraded" if model["status"] != "ready" else "ready"
    else:
        status = "standard"
    return {
        "style": style,
        "stylized": stylized,
        "encoder": encoder,
        "requested_styleid": requested_styleid,
        "model_status": model["status"],
        "model_path": model["path"],
        "status": status,
    }
