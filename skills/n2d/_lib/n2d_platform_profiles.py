#!/usr/bin/env python3
"""Shared platform/backend profiles for n2d video generation.

This is the machine-readable source for fields that otherwise drift between
`n2d-video/references/platforms.md`, `n2d-image/references/platforms.md`, and
the model router.  Human docs may explain tradeoffs, but scripts should read
these constants for routing/gate decisions.
"""
from __future__ import annotations

from typing import Dict, Optional


# 候选快照新鲜度戳记（本线 _lib/freshness.py 据此判过期）。
# 这是「生视频模型/渠道」选择点的能力档快照；max_clip_seconds/native_av 等会随后端迭代变。
# 采集日期：2026-06-13  来源：各后端官方文档 + cli_snapshots/（待逐条复核）
CATALOG_VERIFIED = {"date": "2026-06-13", "source": "各后端官方文档 + cli_snapshots/(待复核)"}


VIDEO_BACKEND_PROFILES: Dict[str, Dict[str, object]] = {
    "dreamina": {
        # 即梦官方 CLI 是字节 Seedance 的访问面：frames2video/image2video 用 seedance2.0 模型
        # 单镜 4–15s，multimodal2video 是 Seedance 2.0 旗舰「全能参考」，multiframe2video 是
        # 「智能多帧」原生多关键帧。能力以 references/cli_snapshots/dreamina/ 的 --help 快照为准
        # （probe_cli.py 抓取/校验）。native_av 仍保守置 False：本线 voice-first，默认不开原生人声，
        # 即梦默认 image2video/multiframe 路径也不生成台词；要原生音轨须显式走 multimodal2video。
        "label": "Dreamina/即梦",
        "aliases": ("即梦", "dreamina", "即梦/Dreamina", "Dreamina/即梦", "jimeng"),
        "max_clip_seconds": 15,
        "default_mode": "image2video",
        "default_model_version": "seedance2.0fast",
        "identity_mechanism": "first_last_frame_or_reference_group",
        "native_av": False,
        "multiframe": {
            # 智能多帧 multiframe2video：N 张关键帧 → 一条连续长镜（原生消除拼接"刹车感"）
            "command": "multiframe2video",
            "max_images": 20,
            "segment_seconds_range": (0.5, 8.0),
            "total_seconds_min": 2.0,
            "supports_resolution_override": False,  # CLI: model_version/video_resolution 不支持
        },
    },
    "kling": {
        "label": "Kling/可灵",
        "aliases": ("可灵", "kling", "可灵/Kling", "Kling/可灵", "Kling 3.0", "kling3.0", "kling 3.0"),
        "max_clip_seconds": 10,
        "default_mode": "frames2video",
        "identity_mechanism": "character_id",
        "native_av": False,
    },
    "seedance": {
        "label": "Seedance",
        "aliases": ("seedance", "Seedance 2.0", "seedance2.0", "seedance 2.0"),
        "max_clip_seconds": 15,
        "default_mode": "image2video",
        "identity_mechanism": "face_lock",
        "native_av": True,
    },
    "veo": {
        "label": "Veo",
        "aliases": ("veo", "Veo 3.1", "veo3.1", "veo 3.1", "Veo 3"),
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
