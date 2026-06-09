#!/usr/bin/env python3
"""Shared platform/backend profiles for n2d video generation.

This is the machine-readable source for fields that otherwise drift between
`n2d-video/references/platforms.md`, `n2d-image/references/platforms.md`, and
the model router.  Human docs may explain tradeoffs, but scripts should read
these constants for routing/gate decisions.
"""
from __future__ import annotations

from typing import Dict, Optional


VIDEO_BACKEND_PROFILES: Dict[str, Dict[str, object]] = {
    "dreamina": {
        "label": "Dreamina/即梦",
        "aliases": ("即梦", "dreamina", "jimeng"),
        "max_clip_seconds": 8,
        "default_mode": "image2video",
        "identity_mechanism": "first_last_frame_or_reference_group",
        "native_av": False,
    },
    "kling": {
        "label": "Kling/可灵",
        "aliases": ("可灵", "kling"),
        "max_clip_seconds": 10,
        "default_mode": "frames2video",
        "identity_mechanism": "character_id",
        "native_av": False,
    },
    "seedance": {
        "label": "Seedance",
        "aliases": ("seedance",),
        "max_clip_seconds": 15,
        "default_mode": "image2video",
        "identity_mechanism": "face_lock",
        "native_av": True,
    },
    "veo": {
        "label": "Veo",
        "aliases": ("veo",),
        "max_clip_seconds": 8,
        "default_mode": "image2video",
        "identity_mechanism": "reference_controls",
        "native_av": True,
    },
    "sora": {
        "label": "Sora",
        "aliases": ("sora",),
        "max_clip_seconds": 20,
        "default_mode": "image2video",
        "identity_mechanism": "reference_media",
        "native_av": True,
    },
}


def video_backend_aliases() -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for key, spec in VIDEO_BACKEND_PROFILES.items():
        aliases[key] = key
        for alias in spec.get("aliases", ()):
            aliases[str(alias)] = key
            aliases[str(alias).lower()] = key
    return aliases


VIDEO_BACKEND_ALIASES = video_backend_aliases()
VIDEO_BACKEND_LABELS = {
    key: str(spec["label"]) for key, spec in VIDEO_BACKEND_PROFILES.items()
}
VIDEO_BACKEND_MAX_SECONDS = {
    key: int(spec["max_clip_seconds"]) for key, spec in VIDEO_BACKEND_PROFILES.items()
}
NATIVE_AV_BACKENDS = tuple(
    key for key, spec in VIDEO_BACKEND_PROFILES.items() if bool(spec.get("native_av"))
)


def normalize_video_backend(value: Optional[str], default: str = "dreamina") -> str:
    text = (value or "").strip()
    if not text:
        return default
    return VIDEO_BACKEND_ALIASES.get(text, VIDEO_BACKEND_ALIASES.get(text.lower(), default))


def video_backend_max_seconds(backend: Optional[str], default: int = 8) -> int:
    key = normalize_video_backend(backend or "", default="")
    if not key:
        return default
    return VIDEO_BACKEND_MAX_SECONDS.get(key, default)


def video_backend_profile(backend: str) -> Optional[Dict[str, object]]:
    key = normalize_video_backend(backend, default="")
    if not key:
        return None
    spec = VIDEO_BACKEND_PROFILES.get(key)
    return dict(spec) if spec else None
