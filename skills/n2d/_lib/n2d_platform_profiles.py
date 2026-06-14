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
# 这是「生视频模型/渠道」选择点的能力档快照；max_clip_seconds/native_av/frame_control、以及
# 下方 MOTION_CONTROL_PROFILES（运镜/运动控制能力）和 lipsync_audio_ref（音频参考口型）都随后端迭代变，
# 同属本快照、同一个戳记覆盖（freshness 注册 id=n2d-video-backends）。
# 采集日期：2026-06-13  来源：各后端官方文档 + cli_snapshots/（待逐条复核）
CATALOG_VERIFIED = {
    "date": "2026-06-13",
    "source": "Dreamina CLI snapshots + Google Veo docs + Luma Ray docs; other entries are conservative fallbacks",
}


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
        "frame_control": {
            "mode": "multi_keyframe",
            "max_timeline_frames": 20,
            "supports_first_frame": True,
            "supports_last_frame": True,
            "supports_native_mid_anchors": True,
            "segment_seconds_range": (0.5, 8.0),
            "fallback": "Use multiframe2video for first/mid/end anchors; if invalid, fall back to first+last frames2video or single first frame.",
            "verified": "2026-06-12 local official dreamina CLI --help snapshot",
        },
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
        "lipsync_audio_ref": True,  # 可灵 Omni 原生口型：可吃音频参考做口型驱动
        "frame_control": {
            "mode": "first_last",
            "max_timeline_frames": 2,
            "supports_first_frame": True,
            "supports_last_frame": True,
            "supports_native_mid_anchors": False,
            "fallback": "Use first+last frame control. Extra mid anchors require split relay/concat or reroute to a native multi-keyframe backend.",
            "verified": "conservative n2d profile; re-verify against current Kling API before paid batch",
        },
    },
    "seedance": {
        "label": "Seedance",
        "aliases": ("seedance", "Seedance 2.0", "seedance2.0", "seedance 2.0"),
        "max_clip_seconds": 15,
        "default_mode": "image2video",
        "identity_mechanism": "face_lock",
        "native_av": True,
        "lipsync_audio_ref": True,  # Seedance 2.0 音素级口型：可吃音频参考做口型驱动
        "frame_control": {
            "mode": "first_frame_or_channel",
            "max_timeline_frames": 1,
            "supports_first_frame": True,
            "supports_last_frame": False,
            "supports_native_mid_anchors": False,
            "fallback": "Direct Seedance profile is treated as first-frame only unless the execution channel is Dreamina; use Dreamina multiframe for native anchors or split relay.",
            "verified": "conservative n2d profile; Dreamina channel has separate verified multiframe capability",
        },
    },
    "veo": {
        "label": "Veo",
        "aliases": ("veo", "Veo 3.1", "veo3.1", "veo 3.1", "Veo 3"),
        "max_clip_seconds": 8,
        "default_mode": "image2video",
        "identity_mechanism": "reference_controls",
        "native_av": True,
        "frame_control": {
            "mode": "first_last_plus_references",
            "max_timeline_frames": 2,
            "max_reference_images": 3,
            "supports_first_frame": True,
            "supports_last_frame": True,
            "supports_native_mid_anchors": False,
            "fallback": "Use first+last frames and up to 3 reference images; extra timeline anchors require split relay/extend, not one native multi-keyframe request.",
            "verified": "2026-06-13 Google Gemini API Veo 3.1 docs",
        },
    },
    "sora": {
        "label": "Sora",
        "aliases": ("sora",),
        "max_clip_seconds": 20,
        "default_mode": "image2video",
        "identity_mechanism": "reference_media",
        "native_av": True,
        "frame_control": {
            "mode": "reference_media",
            "max_timeline_frames": 1,
            "supports_first_frame": True,
            "supports_last_frame": False,
            "supports_native_mid_anchors": False,
            "fallback": "Treat as reference/first-frame guided unless current API explicitly exposes first+last or multi-keyframe timeline control.",
            "verified": "conservative n2d profile; re-verify current Sora API before paid batch",
        },
    },
    "luma": {
        "label": "Luma/Ray",
        "aliases": ("luma", "Luma", "Luma Ray", "Luma Ray3.2", "Ray", "Ray 2", "ray-2"),
        "max_clip_seconds": 5,
        "default_mode": "frames2video",
        "identity_mechanism": "first_last_frame",
        "native_av": False,
        "frame_control": {
            "mode": "first_last",
            "max_timeline_frames": 2,
            "supports_first_frame": True,
            "supports_last_frame": True,
            "supports_native_mid_anchors": False,
            "fallback": "Use keyframes.frame0/frame1. Extra mid anchors require split relay/interpolate between generated clips.",
            "verified": "2026-06-13 Luma Ray 2 API docs",
        },
    },
    "runway": {
        "label": "Runway",
        "aliases": ("runway", "Runway", "Runway Gen-4", "Gen-4", "gen4"),
        "max_clip_seconds": 10,
        "default_mode": "image2video",
        "identity_mechanism": "reference_image",
        "native_av": False,
        "frame_control": {
            "mode": "first_frame",
            "max_timeline_frames": 1,
            "supports_first_frame": True,
            "supports_last_frame": False,
            "supports_native_mid_anchors": False,
            "fallback": "Treat as first-frame/reference guided unless current Runway API exposes last-frame or keyframe timeline control; use split relay/manual workflow for anchors.",
            "verified": "conservative n2d profile; official page must be rechecked before paid batch",
        },
    },
    "pika": {
        "label": "Pika",
        "aliases": ("pika", "Pika", "Pika 2.5"),
        "max_clip_seconds": 10,
        "default_mode": "image2video",
        "identity_mechanism": "reference_image",
        "native_av": False,
        "frame_control": {
            "mode": "first_frame",
            "max_timeline_frames": 1,
            "supports_first_frame": True,
            "supports_last_frame": False,
            "supports_native_mid_anchors": False,
            "fallback": "Treat as first-frame guided unless current Pika API documents first+last or multi-keyframe control; use split relay/manual workflow for anchors.",
            "verified": "conservative n2d profile; official API not verified in this audit",
        },
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

# 支持「音频参考 / 口型驱动」的后端（能把一段配音当口型条件喂进去、同帧出对口型画面）。
# 从档案 lipsync_audio_ref 字段派生，供 router 的 voice_conditioned_lipsync 路由用——
# 候选事实集中在本档（带 CATALOG_VERIFIED 戳记 + freshness 注册），不再散落在 router 里。
LIPSYNC_AUDIO_REF_BACKENDS = frozenset(
    key for key, spec in VIDEO_BACKEND_PROFILES.items() if bool(spec.get("lipsync_audio_ref"))
)


# ── 运镜/运动控制能力档（与 frame_control 同属本快照，CATALOG_VERIFIED 戳记覆盖）──────────
# 本表描述「运镜/运动控制」能力（level + 运动类 capabilities：motion_brush/pose_sequence/depth…），
# 与 n2d_contract.IDENTITY_VIDEO_ADAPTERS（描述「身份绑定」mode：character_id/face_lock/reference_controls）
# 是两个不同关注点，刻意不合并。⚠️ 但其中身份类能力词（character_id/face_lock/reference_controls）与契约重叠：
# 若某后端身份 mode 名在契约里改了，这里的同名 capability 字串也要同步，避免两表对身份能力各说各话。
# comfyui_ltx 是本地控制网后端（非出片后端，不在 VIDEO_BACKEND_PROFILES），仅作运动控制能力登记。
MOTION_CONTROL_PROFILES: Dict[str, Dict[str, object]] = {
    "dreamina": {
        "level": "medium",
        "capabilities": ["first_frame", "first_last_frame", "native_multiframe", "multimodal_reference"],
    },
    "kling": {
        "level": "medium",
        "capabilities": ["first_last_frame", "motion_brush", "reference_video_motion", "character_id"],
    },
    "seedance": {
        "level": "medium",
        "capabilities": ["multimodal_reference", "reference_video_motion", "face_lock"],
    },
    "veo": {
        "level": "medium",
        "capabilities": ["reference_controls", "multimodal_reference"],
    },
    "sora": {
        "level": "medium",
        "capabilities": ["reference_media", "multimodal_reference"],
    },
    "comfyui_ltx": {
        "level": "strong",
        "capabilities": ["pose_sequence", "depth_sequence", "edge_sequence", "instance_mask", "ic_lora"],
    },
}


def video_backend_motion_control(backend: Optional[str], default: str = "dreamina") -> Dict[str, object]:
    """该后端的运镜/运动控制能力档（level + capabilities）。

    先按通用别名归一查（dreamina/kling/…），再容纳控制网后端裸名（comfyui_ltx 不在 VIDEO_BACKEND_PROFILES
    别名表里）；都查不到回退到 default 后端档。返回副本，调用方改不了源表。"""
    key = normalize_video_backend(backend or "", default="")
    if key in MOTION_CONTROL_PROFILES:
        return dict(MOTION_CONTROL_PROFILES[key])
    raw = (backend or "").strip().lower()
    if raw in MOTION_CONTROL_PROFILES:
        return dict(MOTION_CONTROL_PROFILES[raw])
    return dict(MOTION_CONTROL_PROFILES.get(default, {}))


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


def effective_frame_backend(backend: Optional[str], channel: Optional[str] = None) -> str:
    """Return the backend whose frame-control contract will actually execute.

    `生视频模型=Seedance 2.0` often runs through `生视频渠道=即梦/Dreamina`.
    In that case the executable frame API is Dreamina's CLI, not a hypothetical
    direct Seedance API, so native multi-keyframe support comes from Dreamina.
    """
    primary = normalize_video_backend(backend or "", default="")
    execution = normalize_video_backend(channel or "", default="")
    if execution == "dreamina" and primary in {"", "dreamina", "seedance"}:
        return "dreamina"
    return primary or execution


def backend_supports_three_plus_frames(backend: Optional[str], channel: Optional[str] = None) -> bool:
    """三帧契约能力门控：路由视频后端能否表达 ≥3 个关键帧（首+中+尾）。

    True = 必须走三帧契约（默认强制·不因 cost/风格豁免）。判定（向前看·宁强制勿放过）：
      · 后端不在档案里（未知/新后端）→ True（默认假定支持；后端在普遍支持化）。
      · 原生多帧（supports_native_mid_anchors，如即梦 multiframe2video）→ True。
      · max_timeline_frames ≥ 3 → True。
      · 支持尾帧（supports_last_frame，如可灵/Veo/Luma 首尾档）→ True：可首尾拆段接力凑 ≥3 帧。
    False = **唯一豁免**：后端明确为 first-frame-only（无尾帧、无原生多帧、max<3，如
      seedance/sora/runway/pika），连拆段接力都钉不住第 3 个关键帧。
    """
    key = effective_frame_backend(backend, channel)
    spec = VIDEO_BACKEND_PROFILES.get(key)
    if not spec:                       # 未知/新后端：保守按支持（强制三帧）
        return True
    fc = spec.get("frame_control") or {}
    if fc.get("supports_native_mid_anchors") or fc.get("supports_last_frame"):
        return True
    try:
        return int(fc.get("max_timeline_frames") or 1) >= 3
    except (TypeError, ValueError):
        return True


def video_backend_frame_control(backend: Optional[str], channel: Optional[str] = None) -> Dict[str, object]:
    key = effective_frame_backend(backend, channel)
    spec = VIDEO_BACKEND_PROFILES.get(key, {})
    control = spec.get("frame_control")
    if isinstance(control, dict):
        return dict(control)
    return {
        "mode": "unknown",
        "max_timeline_frames": 1,
        "supports_first_frame": True,
        "supports_last_frame": False,
        "supports_native_mid_anchors": False,
        "fallback": "Unknown frame-control capability; assume first-frame only and require manual confirmation before paid generation.",
        "verified": "unknown",
    }
