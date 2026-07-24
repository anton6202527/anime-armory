#!/usr/bin/env python3
"""Shared platform/backend profiles for n2d video generation.

This is the machine-readable source for fields that otherwise drift between
`n2d-video/references/platforms.md`, `n2d-image/references/platforms.md`, and
the model router.  Human docs may explain tradeoffs, but scripts should read
these constants for routing/gate decisions.
"""
from __future__ import annotations

import math

from typing import Any, Dict, Mapping, Optional, Sequence


# 候选快照新鲜度戳记（本线 _lib/freshness.py 据此判过期）。
# 这是「生视频模型/渠道」选择点的能力档快照；max_clip_seconds/native_av/frame_control、以及
# 下方 MOTION_CONTROL_PROFILES（运镜/运动控制能力）和 lipsync_audio_ref（音频参考口型）都随后端迭代变，
# 同属本快照、同一个戳记覆盖（freshness 注册 id=n2d-video-backends）。
# 采集日期：2026-07-24  来源：Google Gemini API video/Omni/Veo docs + ByteDance Seedance 2.0/2.5 official launch（即梦体验中心 07-06 上线·API 随后）+ Kling VIDEO 3.0 official guide + PixVerse C1 official launch + cli_snapshots/
CATALOG_VERIFIED = {
    "date": "2026-07-11",
    "source": (
        "Google Gemini API video overview/Omni Flash/Veo docs (last updated 2026-06-30) + "
        "ByteDance Seedance 2.0 official launch + Kling VIDEO 3.0 official guide + "
        "PixVerse C1 official launch (2026-04-07) + Dreamina CLI snapshots + Luma Ray docs + "
        "OpenAI Sora discontinuation notice; other entries are conservative fallbacks"
    ),
}


VIDEO_BACKEND_PROFILES: Dict[str, Dict[str, object]] = {
    "dreamina": {
        # 即梦官方 CLI 是字节 Seedance 的访问面：frames2video/image2video 用 seedance2.0 模型
        # 单镜 4–15s，multimodal2video 是 Seedance 2.0 旗舰「全能参考」，multiframe2video 是
        # 「智能多帧」原生多关键帧。能力以 references/cli_snapshots/dreamina/ 的 --help 快照为准
        # （probe_cli.py 抓取/校验）。native_av 仍保守置 False：本线 voice-first，默认不开原生人声，
        # 即梦默认 image2video/multiframe 路径也不生成台词；要原生音轨须显式走 multimodal2video。
        "label": "Dreamina/即梦",
        "capability_confidence": "evidence",
        "aliases": ("即梦", "dreamina", "即梦/Dreamina", "Dreamina/即梦", "jimeng"),
        "max_clip_seconds": 15,
        "default_mode": "image2video",
        "default_model_version": "seedance2.0fast",
        # Seedance 家族有 fast/pro 质量档（fast≈$0.022/s，量产默认；pro 留给吃重镜）。这里只登记
        # 「支持质量档 + 默认档」能力，不写死具体 pro 版本字串（防过期：版本名以 cli_snapshots 为准）。
        "supports_quality_tier": True,
        "default_quality_tier": "fast",
        "identity_mechanism": "first_last_frame_or_reference_group",
        "native_av": False,
        "duration_control": {
            "kind": "integer_range",
            "min_seconds": 4,
            "max_seconds": 15,
            "step_seconds": 1,
            "default_seconds": 5,
            "model_ranges": {
                "3.0": (3, 10),
                "3.0fast": (3, 10),
                "3.0pro": (3, 10),
                "3.5pro": (4, 12),
                "seedance2.0": (4, 15),
                "seedance2.0fast": (4, 15),
                "seedance2.0_vip": (4, 15),
                "seedance2.0fast_vip": (4, 15),
            },
            "native_multiframe": {
                "kind": "continuous_range",
                "min_seconds": 2,
                "max_seconds": 15,
                "step_seconds": 0.1,
            },
            "verified": "2026-06-22 local official Dreamina CLI --help snapshots",
        },
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
        "capability_confidence": "conservative",
        "aliases": ("可灵", "kling", "可灵/Kling", "Kling/可灵", "Kling 3.0", "kling3.0", "kling 3.0"),
        "max_clip_seconds": 10,
        "default_mode": "frames2video",
        "identity_mechanism": "character_id",
        "native_av": False,
        "duration_control": {
            "kind": "allowed_values",
            "values": (5, 10),
            "verified": "conservative profile; re-verify current Kling model before paid submit",
        },
        "consistency_face_floor_delta": 0.05,  # multishot + character_id → tighter identity floor
        "lipsync_audio_ref": True,  # 可灵 Omni 原生口型：可吃音频参考做口型驱动
        "multilingual_lipsync": True,  # 可灵 3.0 Omni 多语言/方言/口音原生口型（出海次选，Seedance 优先）
        # Kling 3.0（2026 市场报告）：单次生成可出**最多 6 个连续镜头 + 共享音轨时间线**的多镜叙事，
        # 字符一致性显著增强——同 Seedance 一样属「多镜单次生成」能力，对连续接力镜组可一次 co-generate
        # 整段消缝。判定走能力字段，由 MULTISHOT_NATIVE_BACKENDS 自动收录 → router 标 multishot_candidate。
        # 保守起见：付费批量前仍按 verified 复核当前 Kling API 是否暴露该多镜接口。
        "multishot_native": True,
        "frame_control": {
            "mode": "first_last",
            "max_timeline_frames": 2,
            "supports_first_frame": True,
            "supports_last_frame": True,
            "supports_native_mid_anchors": False,
            "fallback": "Use first+last frame control. Extra mid anchors require split relay/concat or reroute to a native multi-keyframe backend.",
            "verified": "conservative n2d profile; re-verify against current Kling API before paid batch (incl. 6-shot multi-shot + shared audio timeline)",
        },
    },
    "seedance": {
        "label": "Seedance",
        "capability_confidence": "conservative",
        "aliases": ("seedance", "Seedance 2.0", "seedance2.0", "seedance 2.0",
                    "Seedance 2.5", "seedance2.5", "seedance 2.5"),
        # 2026 新鲜度（2026-07-24 实搜复核）：Seedance 2.5 已正式上线——即梦体验中心 ~2026-07-06、
        # API 随后开放；官方发布口径为单段原生 30s + 最多 50 个全模态参考 + 音视频同 latent 联合生成
        # （「原生 4K」多篇报道实际归属同场升级的 Seedance 2.0，2.5 是否 4K 仍存疑）。对 n2d 的意义：
        # 30s 单段直接抬高 single_take_multishot 接力组的合并上限（更少 clip）。能力仍按
        # multishot_native + 当前 max_clip_seconds 保守登记：执行渠道 per-run cli_snapshots 验到 2.5
        # 且时长档确认前，家族上限不升到 30（防把未验数字写死进预算）。
        "max_clip_seconds": 15,
        "default_mode": "image2video",
        "identity_mechanism": "face_lock",
        "native_av": True,
        "duration_control": {
            "kind": "integer_range",
            "min_seconds": 4,
            "max_seconds": 15,
            "step_seconds": 1,
            "verified": "2026-07-01 Seedance 2.0 official duration range",
        },
        "lipsync_audio_ref": True,  # Seedance 2.0 音素级口型：可吃音频参考做口型驱动
        "multilingual_lipsync": True,  # 2026 多语言唇同步 best-in-class（出海非中文台词口型/口音匹配）
        # Seedance 2.0 一次生成可出「多镜头叙事 + 跨镜人物一致 + 无缝转场」（multi-shot single-gen），
        # 也能收视频片段作运动/风格参考（reference_video_motion 已在 MOTION_CONTROL_PROFILES 登记）。
        "multishot_native": True,
        "supports_quality_tier": True,  # fast/pro 质量档；fast 量产默认，pro 留吃重镜
        "default_quality_tier": "fast",
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
        "capability_confidence": "evidence",
        "aliases": ("veo", "Veo 3.1", "veo3.1", "veo 3.1", "Veo 3"),
        "max_clip_seconds": 8,
        "default_mode": "image2video",
        "identity_mechanism": "reference_controls",
        "native_av": True,
        "duration_control": {
            "kind": "allowed_values",
            "values": (4, 6, 8),
            "verified": "2026-07-10 Google Veo 3.1 first/last-frame API docs",
        },
        "availability": {
            "status": "preview",
            "current_model": "Veo 3.1",
            "legacy_models_shutdown_at": "2026-06-30",
            "legacy_models": ("Veo 3", "Veo 2"),
            "source": "Google Vertex AI / Gemini API Veo 3.1 docs and model lifecycle notes",
            "note": "route only to current Veo 3.1 capability; do not treat older Veo 3/Veo 2 pricing or limits as current.",
        },
        "frame_control": {
            "mode": "first_last_plus_references",
            "max_timeline_frames": 2,
            "max_reference_images": 3,
            "supports_first_frame": True,
            "supports_last_frame": True,
            "supports_native_mid_anchors": False,
            "fallback": "Use first+last frames and up to 3 reference images; extra timeline anchors require split relay/extend, not one native multi-keyframe request.",
            "verified": "2026-06-25 Google Gemini API / Vertex AI Veo 3.1 docs",
        },
    },
    "gemini_omni": {
        "label": "Gemini Omni Flash",
        "capability_confidence": "evidence",
        "aliases": (
            "gemini_omni",
            "Gemini Omni Flash",
            "gemini omni flash",
            "Gemini Omni",
            "gemini-omni-flash-preview",
            "omni flash",
            "Google Omni",
        ),
        # Google calls Omni Flash the Gemini API default for video generation, but the public docs only
        # say "short videos"; keep n2d's per-Clip cap conservative until duration controls are exposed
        # in the API adapter or project smoke evidence.
        "max_clip_seconds": 8,
        "default_mode": "interactions_video",
        "default_model_version": "gemini-omni-flash-preview",
        "identity_mechanism": "multi_input_reference",
        "native_av": True,
        "duration_control": {
            "kind": "manual_confirm",
            "min_seconds": 1,
            "max_seconds": 8,
            "verified": "public duration controls not exposed in the current adapter",
        },
        "multishot_native": True,
        "availability": {
            "status": "preview",
            "current_model": "gemini-omni-flash-preview",
            "source": "Google Gemini API Omni Flash docs and video overview",
            "note": "Google recommends Omni Flash as the default Gemini API video model; n2d still requires first/last-frame contract evidence and backend smoke before paid batch routing.",
        },
        "frame_control": {
            "mode": "multi_input_reference_edit",
            "max_timeline_frames": 1,
            "max_reference_images": 3,
            "supports_first_frame": False,
            "supports_last_frame": False,
            "supports_native_mid_anchors": False,
            "fallback": "Use as multimodal reference-to-video / conversational editing candidate. Do not assume n2d first-frame or last-frame exactness until adapter smoke verifies the contract.",
            "verified": "2026-07-01 Google Gemini API video overview + Gemini Omni Flash docs (last updated 2026-06-30)",
        },
    },
    "sora": {
        "label": "Sora",
        "capability_confidence": "deprecated",
        "aliases": ("sora",),
        "max_clip_seconds": 20,
        "default_mode": "image2video",
        "identity_mechanism": "reference_media",
        # 2026-06-25：Sora Web/App 已停服，API 处于明确日落窗口。保留档案只为读旧项目/人工补单；
        # 自动路由、原生音画候选、批量付费提交不得再把 Sora 当 primary/fallback。
        "native_av": False,
        "duration_control": {
            "kind": "manual_confirm",
            "min_seconds": 1,
            "max_seconds": 20,
            "verified": "legacy/manual-only profile",
        },
        "auto_routing": False,
        "availability": {
            "status": "legacy_manual_only",
            "web_app_discontinued_at": "2026-04-26",
            "api_shutdown_at": "2026-09-24",
            "source": "OpenAI Help Center: What to know about the Sora discontinuation",
        },
        "frame_control": {
            "mode": "reference_media",
            "max_timeline_frames": 1,
            "supports_first_frame": True,
            "supports_last_frame": False,
            "supports_native_mid_anchors": False,
            "fallback": "Treat as reference/first-frame guided unless current API explicitly exposes first+last or multi-keyframe timeline control.",
            "verified": "legacy/manual-only profile; do not auto-route paid batches to Sora",
        },
    },
    "luma": {
        "label": "Luma/Ray",
        "capability_confidence": "evidence",
        "aliases": ("luma", "Luma", "Luma Ray", "Luma Ray3.2", "Ray", "Ray 2", "ray-2"),
        "max_clip_seconds": 5,
        "default_mode": "frames2video",
        "identity_mechanism": "first_last_frame",
        "native_av": False,
        "duration_control": {
            "kind": "allowed_values",
            "values": (5,),
            "verified": "2026-07-10 Luma Ray 2 API docs",
        },
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
        "capability_confidence": "conservative",
        "aliases": ("runway", "Runway", "Runway Gen-4", "Gen-4", "gen4"),
        "max_clip_seconds": 10,
        "default_mode": "image2video",
        "identity_mechanism": "reference_image",
        "native_av": False,
        "duration_control": {
            "kind": "allowed_values",
            "values": (5, 10),
            "verified": "conservative Gen-4/Gen-4.5 profile; re-verify selected model before paid submit",
        },
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
        "capability_confidence": "conservative",
        "aliases": ("pika", "Pika", "Pika 2.5"),
        "max_clip_seconds": 10,
        "default_mode": "image2video",
        "identity_mechanism": "reference_image",
        "native_av": False,
        "duration_control": {
            "kind": "allowed_values",
            "values": (5, 10),
            "verified": "conservative profile; official API not verified in this audit",
        },
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
    "pixverse_c1": {
        "label": "PixVerse C1",
        "capability_confidence": "evidence",
        "aliases": ("pixverse_c1", "PixVerse C1", "pixverse c1", "C1"),
        "max_clip_seconds": 15,
        "default_mode": "reference_to_video",
        "identity_mechanism": "reference_guided",
        "native_av": True,
        # 官方能力已核验；尚无 n2d 正式 submit adapter，因此不进入自动付费 roster。
        "auto_routing": False,
        "multishot_native": True,
        "reference_to_video_native": True,
        "duration_control": {
            "kind": "integer_range", "min_seconds": 1, "max_seconds": 15, "step_seconds": 1,
            "verified": "2026-04-07 PixVerse official C1 launch: up to 15s/1080p with audio",
        },
        "frame_control": {
            "mode": "storyboard_or_reference_bundle",
            "max_timeline_frames": 9,
            "max_reference_images": 9,
            "supports_first_frame": True,
            "supports_last_frame": True,
            "supports_native_mid_anchors": True,
            "fallback": "Use a 3-9 panel storyboard/reference bundle; n2d emits a job package until a verified C1 adapter is registered.",
            "verified": "2026-04-07 PixVerse official C1 storyboard-to-video/reference-guided announcement",
        },
    },
    "wan": {
        "label": "Wan/万相",
        "capability_confidence": "conservative",
        "aliases": ("wan", "Wan", "万相", "通义万相", "Wan 2.2", "wan2.2", "Wan 2.6", "wan2.6",
                    "Wan 2.7", "wan2.7", "WanX"),
        "max_clip_seconds": 10,
        "default_mode": "image2video",
        "identity_mechanism": "first_last_frame_or_reference",
        "native_av": False,
        "duration_control": {
            "kind": "allowed_values",
            "values": (5, 10),
            "verified": "conservative self-hosted profile; re-verify the local checkpoint",
        },
        "consistency_face_floor_delta": -0.03,  # open-source self-host; identity less stable than cloud APIs
        # 开源/可自托管的「多镜单次生成」后端（Wan 2.6/2.7）：native-multishot 里唯一不绑付费云 API、
        # 可在本地 ComfyUI/自建管线跑的选项——契合「主流程不硬绑后端、缺依赖优雅降级」（设计宪法 C4）。
        # 能力走字段判定，由 MULTISHOT_NATIVE_BACKENDS 自动收录；开源权重无官方 SLA，批量前按 verified
        # 复核当前本地 checkpoint 版本与多镜接口。
        "multishot_native": True,
        "frame_control": {
            "mode": "first_last",
            "max_timeline_frames": 2,
            "supports_first_frame": True,
            "supports_last_frame": True,
            "supports_native_mid_anchors": False,
            "fallback": "Use first+last frame control on the self-hosted Wan pipeline; extra mid anchors require split relay/concat. Open weights: no managed API SLA, re-verify the local checkpoint version before batch.",
            "verified": "conservative n2d profile (open-source self-host); re-verify local Wan checkpoint before batch",
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


def backend_face_floor_delta(backend_key: str) -> float:
    """Per-backend identity floor adjustment for consistency_audit face scoring.

    Backends with native multishot + strong identity mechanisms (Kling character_id,
    Seedance reference_group) get a tighter floor (positive delta → harder to pass);
    open-source / single-shot backends get a looser floor (negative delta → easier to
    pass, acknowledging inherent identity instability).

    Returns 0.0 for unknown backends (no adjustment).
    """
    spec = VIDEO_BACKEND_PROFILES.get(backend_key, {})
    return float(spec.get("consistency_face_floor_delta", 0.0))


VIDEO_BACKEND_ALIASES = video_backend_aliases()
VIDEO_BACKEND_LABELS = {
    key: str(spec["label"]) for key, spec in VIDEO_BACKEND_PROFILES.items()
}
VIDEO_BACKEND_MAX_SECONDS = {
    key: int(spec["max_clip_seconds"]) for key, spec in VIDEO_BACKEND_PROFILES.items()
}
AUTO_ROUTABLE_VIDEO_BACKENDS = tuple(
    key for key, spec in VIDEO_BACKEND_PROFILES.items() if spec.get("auto_routing", True) is not False
)
NATIVE_AV_BACKENDS = tuple(
    key for key, spec in VIDEO_BACKEND_PROFILES.items()
    if bool(spec.get("native_av")) and spec.get("auto_routing", True) is not False
)

# 支持「音频参考 / 口型驱动」的后端（能把一段配音当口型条件喂进去、同帧出对口型画面）。
# 从档案 lipsync_audio_ref 字段派生，供 router 的 voice_conditioned_lipsync 路由用——
# 候选事实集中在本档（带 CATALOG_VERIFIED 戳记 + freshness 注册），不再散落在 router 里。
LIPSYNC_AUDIO_REF_BACKENDS = frozenset(
    key for key, spec in VIDEO_BACKEND_PROFILES.items() if bool(spec.get("lipsync_audio_ref"))
)

# 多语言唇同步后端（非中文台词口型/口音匹配）——出海(目标语言≠中文)说话镜优先。从 multilingual_lipsync
# 字段派生；偏好序列 seedance(2026 best-in-class)→kling(Omni)→veo，用于 overseas 路由 primary 抢占。
MULTILINGUAL_LIPSYNC_BACKENDS = frozenset(
    key for key, spec in VIDEO_BACKEND_PROFILES.items() if bool(spec.get("multilingual_lipsync"))
)
_MULTILINGUAL_LIPSYNC_PREFERENCE = ("seedance", "kling", "veo")


def video_backend_supports_multilingual_lipsync(backend: Optional[str]) -> bool:
    """该后端是否支持多语言唇同步（出海非中文台词口型）。纯函数·可测。"""
    return normalize_video_backend(backend or "", default="") in MULTILINGUAL_LIPSYNC_BACKENDS


def preferred_multilingual_lipsync_backend() -> str:
    """出海说话镜首选的多语言唇同步后端（按偏好序列取首个可自动路由者）；无则空串。纯函数·可测。"""
    for key in _MULTILINGUAL_LIPSYNC_PREFERENCE:
        if key in MULTILINGUAL_LIPSYNC_BACKENDS and video_backend_auto_routable(key):
            return key
    for key in sorted(MULTILINGUAL_LIPSYNC_BACKENDS):
        if video_backend_auto_routable(key):
            return key
    return ""


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
    "gemini_omni": {
        "level": "medium",
        "capabilities": ["multimodal_reference", "conversational_edit", "native_audio"],
    },
    "pixverse_c1": {
        "level": "medium",
        "capabilities": ["multimodal_reference", "reference_video_motion", "storyboard_reference", "native_audio"],
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


# ── 奇观镜「冷启动后端先验」（CATALOG_VERIFIED 戳记覆盖，同属 n2d-video-backends 快照）──────────
# 背景：spectacle_backend_benchmark.json 是项目级 probe 实测回灌，没填则高动态镜按物理表现路由「名存实亡」。
# 本表是 benchmark 为空时的默认排序先验——按动作类型把候选后端排个序，给冷启动项目一个有依据的起点。
# ⚠️ 这是「选择点的候选快照」性质（C1/C2）：只在「自动路由 + 无 benchmark + 非 fixed_default」时生效；
# benchmark 一旦填了就覆盖本表，_设置.md 锁了 fixed_default 也不动。不是把某家后端硬绑进主流程。
# 依据（2026-06 横评，详见 n2d-model-router/references/）：
#   physical_combat   打斗物理(拳脚/碰撞/重量感)：Kling 物理写实最强；Seedance 2.0 快速拳踢翻滚平滑次之。
#   continuity_transition 连续追逐/无缝转场/多镜叙事：Seedance 原生多镜+稳定转场最强。
#   identity_lock     身份吃紧近景：带 reference 的 Kling 3.0 element binding / Runway Gen-4 References。
#   stylized          二次元/风格化动作(漫剧主力)：Seedance stylized 项 + 即梦中文语义/运镜调度。
# 每个 spectacle_type 给一条按优先级排好的 auto-routable 后端序列；裸名以 VIDEO_BACKEND_ALIASES 归一后为准。
SPECTACLE_BACKEND_PRIOR: Dict[str, Dict[str, Any]] = {
    "fight_exchange": {
        "ranking": ("kling", "seedance", "dreamina", "veo"),
        "basis": "physical_combat: Kling 物理写实最强, Seedance 2.0 动作平滑次之",
    },
    "chase": {
        "ranking": ("seedance", "kling", "dreamina", "veo"),
        "basis": "continuity_transition: Seedance 原生多镜+稳定转场最适合连续追逐",
    },
    "flight": {
        "ranking": ("veo", "seedance", "kling", "dreamina"),
        "basis": "flight 兼顾物理(云海/坠落重量)与运镜语言: Veo 写实物理+运镜强, Seedance 多镜次之",
    },
    "mount_ride": {
        "ranking": ("seedance", "kling", "dreamina", "veo"),
        "basis": "mount_ride 吃连续步态和背景视差: Seedance 长连续运动强, Kling 适合主体/接触约束",
    },
    "vehicle_ride": {
        "ranking": ("seedance", "kling", "dreamina", "veo"),
        "basis": "vehicle_ride 吃轮转、牵引连接和侧向跟拍: Seedance 连续运动强, Kling 适合局部运动控制",
    },
    "vessel_flight": {
        "ranking": ("seedance", "veo", "kling", "dreamina"),
        "basis": "vessel_flight 吃载具剪影、云层视差和运镜: Seedance 连续飞行强, Veo 电影运镜强",
    },
    "road_vehicle": {
        "ranking": ("seedance", "kling", "dreamina", "veo"),
        "basis": "road_vehicle 吃车流连续、车道保持、轮转和视差: Seedance 连续运动强, Kling 适合局部运动控制",
    },
    "stealth_stalk": {
        "ranking": ("seedance", "kling", "veo", "dreamina"),
        "basis": "stealth_stalk 吃慢速跟拍、遮挡层和低光连续性: Seedance 连续运动强, Kling 适合遮挡/主体约束",
    },
    "large_establishing": {
        "ranking": ("veo", "seedance", "kling", "dreamina"),
        "basis": "large_establishing 吃运镜语言与尺度: Veo cinematography 强, Seedance 转场次之",
    },
}


def spectacle_backend_prior_ranking(spectacle_type: Optional[str]) -> tuple:
    """该奇观类型的冷启动后端先验排序（已按 auto_routable 过滤）。纯函数·可测。

    返回归一化后、且 auto_routing 未关闭的后端键序列；类型不识别或全不可路由→空 tuple。
    调用方应只把它当「无 benchmark 时的默认排序」，benchmark/fixed_default 优先级更高。
    """
    spec = SPECTACLE_BACKEND_PRIOR.get(str(spectacle_type or "").strip())
    if not spec:
        return ()
    seen: list = []
    for raw in spec.get("ranking", ()):  # type: ignore[union-attr]
        key = normalize_video_backend(str(raw), default="")
        if key and key not in seen and video_backend_auto_routable(key):
            seen.append(key)
    return tuple(seen)


# ── 多镜单次生成 / 视频运动参考 / 质量档 能力派生（CATALOG_VERIFIED 戳记覆盖）──────────
# 三者都从档案字段派生，集中在本档（不散落在 router）。判定走能力字段，不 hardcode 厂商名。
MULTISHOT_CAPABLE_BACKENDS = frozenset(
    key for key, spec in VIDEO_BACKEND_PROFILES.items() if bool(spec.get("multishot_native"))
)
MULTISHOT_NATIVE_BACKENDS = frozenset(
    key for key, spec in VIDEO_BACKEND_PROFILES.items()
    if bool(spec.get("multishot_native")) and spec.get("auto_routing", True) is not False
)
QUALITY_TIER_BACKENDS = frozenset(
    key for key, spec in VIDEO_BACKEND_PROFILES.items() if bool(spec.get("supports_quality_tier"))
)
# 视频运动参考（把一段已通过的 clip 当运动/风格参考喂进去）= 运动控制档里的 reference_video_motion 能力。
MOTION_REFERENCE_BACKENDS = frozenset(
    key for key, spec in MOTION_CONTROL_PROFILES.items()
    if "reference_video_motion" in (spec.get("capabilities") or [])
)
REFERENCE_TO_VIDEO_BACKENDS = frozenset(
    key for key, spec in VIDEO_BACKEND_PROFILES.items() if bool(spec.get("reference_to_video_native"))
)


def video_backend_supports_multishot(backend: Optional[str]) -> bool:
    """该后端是否支持「多镜单次生成」（一次出多镜头叙事、跨镜一致、无缝转场）。纯函数·可测。"""
    return normalize_video_backend(backend or "", default="") in MULTISHOT_CAPABLE_BACKENDS


def video_backend_supports_reference_to_video(backend: Optional[str]) -> bool:
    """Whether a backend can generate from a storyboard/reference bundle without a per-shot hero frame."""
    return normalize_video_backend(backend or "", default="") in REFERENCE_TO_VIDEO_BACKENDS


def video_backend_supports_quality_tier(backend: Optional[str]) -> bool:
    """该后端是否有 fast/pro 质量档（成本×质量路由轴）。纯函数·可测。"""
    return normalize_video_backend(backend or "", default="") in QUALITY_TIER_BACKENDS


def video_backend_default_quality_tier(backend: Optional[str]) -> str:
    """该后端默认质量档（无档位能力→空串）。纯函数·可测。"""
    key = normalize_video_backend(backend or "", default="")
    spec = VIDEO_BACKEND_PROFILES.get(key, {})
    return str(spec.get("default_quality_tier") or "") if spec.get("supports_quality_tier") else ""


def video_backend_supports_motion_reference(backend: Optional[str]) -> bool:
    """该后端能否吃「视频片段运动/风格参考」（reference_video_motion）。纯函数·可测。"""
    return normalize_video_backend(backend or "", default="") in MOTION_REFERENCE_BACKENDS


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


def single_take_merge_ceiling_seconds(backend: Optional[str], *, floor: float = 15.0) -> float:
    """编辑侧「单拍多镜」合并上限（秒）：后端能力感知的前向接线。

    返回 max(floor, 已验后端单段生成上限)。设计意图：
      - 后端未定（自动路由）/未知 → floor（历史 15s 行为，绝不倒退合并机会）；
      - 后端单段上限经 per-run 证据升高（如 Seedance 2.5 验到 30s 后更新
        VIDEO_BACKEND_MAX_SECONDS）→ 脚本层合并上限自动跟进，不需再改代码；
      - 上限较小的后端（如 8s 档）不把编辑侧合并压得比历史更碎——最终能不能一次
        生成仍由 select_video_frame_strategy / 时长闸兜底回落，编辑侧只管合并意图。
    消费方：n2d-script shot_split_decision.single_take_policy_verdict 与
    n2d-video prompt_pack 的 auto_single_take（同口径）。
    """
    backend_max = float(video_backend_max_seconds(backend, default=0))
    return max(float(floor), backend_max)


def video_backend_duration_control(
    backend: Optional[str],
    channel: Optional[str] = None,
    *,
    model_version: Optional[str] = None,
    mode: Optional[str] = None,
) -> Dict[str, object]:
    """Return the executable backend's duration contract.

    Duration is a request-field capability, not a storytelling decision.  The
    returned profile describes only what the selected backend can submit; the
    compiler separately keeps the narrative span and edit target.
    """
    key = effective_frame_backend(backend, channel)
    spec = VIDEO_BACKEND_PROFILES.get(key, {})
    raw = spec.get("duration_control")
    if not isinstance(raw, Mapping):
        return {
            "kind": "manual_confirm",
            "min_seconds": 0.1,
            "max_seconds": float(spec.get("max_clip_seconds") or 8),
            "verified": "unknown duration control; confirm the selected model before paid submit",
            "execution_backend": key,
        }
    control: Dict[str, object] = dict(raw)
    low_mode = str(mode or "").strip().lower()
    native_duration_mode = key == "dreamina" and low_mode in {"multiframe2video", "native_multiframe"}
    if native_duration_mode:
        native = raw.get("native_multiframe")
        if isinstance(native, Mapping):
            control.update(dict(native))
    model = str(model_version or spec.get("default_model_version") or "").strip()
    ranges = raw.get("model_ranges")
    if model and isinstance(ranges, Mapping) and not native_duration_mode:
        pair = ranges.get(model)
        if isinstance(pair, Sequence) and not isinstance(pair, (str, bytes)) and len(pair) >= 2:
            control["min_seconds"] = float(pair[0])
            control["max_seconds"] = float(pair[1])
    control["execution_backend"] = key
    control["model_version"] = model
    return control


def quantize_video_duration(
    target_seconds: Optional[float],
    backend: Optional[str],
    channel: Optional[str] = None,
    *,
    model_version: Optional[str] = None,
    mode: Optional[str] = None,
) -> Dict[str, object]:
    """Map an edit target to a backend request duration without changing edit intent."""
    try:
        target = float(target_seconds) if target_seconds is not None else 0.0
    except (TypeError, ValueError):
        target = 0.0
    control = video_backend_duration_control(
        backend, channel, model_version=model_version, mode=mode
    )
    kind = str(control.get("kind") or "manual_confirm")
    request = target
    requires_manual = kind == "manual_confirm"
    requires_split = False
    reason = kind
    values = control.get("values")
    if kind == "allowed_values" and isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        allowed = sorted({float(v) for v in values if isinstance(v, (int, float)) and float(v) > 0})
        if allowed:
            request = next((v for v in allowed if v + 1e-9 >= target), allowed[-1])
            requires_split = target > allowed[-1] + 1e-9
            reason = "allowed_values:" + ",".join(f"{v:g}" for v in allowed)
    elif kind in {"integer_range", "continuous_range"}:
        minimum = float(control.get("min_seconds") or 0.1)
        maximum = float(control.get("max_seconds") or max(minimum, target))
        step = float(control.get("step_seconds") or (1.0 if kind == "integer_range" else 0.1))
        if target > maximum + 1e-9:
            request = maximum
            requires_split = True
        else:
            base = max(minimum, target)
            request = math.ceil((base - minimum) / step - 1e-9) * step + minimum
            request = min(maximum, max(minimum, request))
        reason = f"{kind}:{minimum:g}-{maximum:g}/step={step:g}"
    else:
        minimum = float(control.get("min_seconds") or 0.1)
        maximum = float(control.get("max_seconds") or max(minimum, target))
        request = min(maximum, max(minimum, target))
        requires_split = target > maximum + 1e-9
        reason = "manual_confirm"
    request = round(float(request), 3)
    target = round(max(0.0, target), 3)
    surplus = round(max(0.0, request - target), 3)
    return {
        "execution_backend": control.get("execution_backend") or "",
        "model_version": control.get("model_version") or "",
        "duration_control_kind": kind,
        "edit_target_sec": target,
        "backend_request_sec": request,
        "backend_surplus_sec": surplus,
        "usable_window": [0.0, min(target, request)],
        "trim_mode": "trim_tail" if surplus > 0.05 else "none",
        "requires_split": requires_split,
        "requires_manual_confirmation": requires_manual,
        "quantization_reason": reason,
        "verified": control.get("verified") or "",
    }


def video_backend_profile(backend: str) -> Optional[Dict[str, object]]:
    key = normalize_video_backend(backend, default="")
    if not key:
        return None
    spec = VIDEO_BACKEND_PROFILES.get(key)
    return dict(spec) if spec else None


def video_backend_capability_confidence(backend: Optional[str], channel: Optional[str] = None) -> Dict[str, object]:
    """Return evidence-quality metadata for paid backend routing.

    Freshness answers "when was this catalog checked"; confidence answers whether
    the checked facts are strong enough for automated paid routing.
    """
    execution = effective_frame_backend(backend, channel)
    profile = VIDEO_BACKEND_PROFILES.get(execution)
    if not profile:
        return {
            "backend": normalize_video_backend(backend or "", default="") or (backend or ""),
            "channel": normalize_video_backend(channel or "", default="") or (channel or ""),
            "execution_backend": execution,
            "confidence": "manual_required",
            "paid_routing_allowed": False,
            "reason": "unknown backend profile",
        }
    confidence = str(profile.get("capability_confidence") or "conservative")
    availability = profile.get("availability") if isinstance(profile.get("availability"), dict) else {}
    if availability.get("status") in {"legacy_manual_only", "deprecated", "shutdown"}:
        confidence = "deprecated"
    paid_allowed = confidence == "evidence"
    return {
        "backend": normalize_video_backend(backend or "", default="") or (backend or ""),
        "channel": normalize_video_backend(channel or "", default="") or (channel or ""),
        "execution_backend": execution,
        "confidence": confidence,
        "paid_routing_allowed": paid_allowed,
        "reason": availability.get("status") or profile.get("frame_control", {}).get("verified") or "",
    }


def video_backend_auto_routable(backend: Optional[str]) -> bool:
    """Whether a backend may be selected by automatic routing for new paid work."""
    key = normalize_video_backend(backend or "", default="")
    if not key:
        return True
    spec = VIDEO_BACKEND_PROFILES.get(key)
    if not spec:
        return True
    return spec.get("auto_routing", True) is not False


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
    """Whether one native request can consume 3+ timeline anchors.

    A first+last backend is deliberately False: two paid first/last requests
    joined at a middle image are split relay, not native three-frame control.
    """
    key = effective_frame_backend(backend, channel)
    spec = VIDEO_BACKEND_PROFILES.get(key)
    if not spec:                       # 未知/未选后端：先要能力证据，不默认强制三帧
        return False
    fc = spec.get("frame_control") or {}
    if fc.get("supports_native_mid_anchors"):
        return True
    try:
        return int(fc.get("max_timeline_frames") or 1) >= 3
    except (TypeError, ValueError):
        return False


VIDEO_FRAME_STRATEGIES = frozenset({
    "first_only",
    "first_last",
    "native_multiframe",
    "split_relay",
    "edit_cut",
    "edit_cut_pending_assets",
    "reference_qc",
    "reroute_required",
    "single_take_multishot",
})


def single_take_multishot_supported(
    backend: Optional[str],
    duration_sec: Optional[float] = None,
) -> bool:
    """storyboard `take_policy=single_take_multishot` 能否在该后端一次生成整个多镜位 Clip。

    条件：后端 multishot_native（一次出多镜头叙事、跨镜一致）且 Clip 叙事跨度不超过该后端
    单次生成上限（`max_clip_seconds`）。纯函数·可测；不满足时调用方必须回落 edit_cut 拆 take，
    不得静默按单镜直提。"""
    if not video_backend_supports_multishot(backend):
        return False
    if duration_sec is None:
        return True
    try:
        return float(duration_sec) <= float(video_backend_max_seconds(backend, 8)) + 1e-9
    except (TypeError, ValueError):
        return False


def select_video_frame_strategy(
    backend: Optional[str],
    channel: Optional[str] = None,
    *,
    shot_count: int = 1,
    anchor_count: int = 0,
    need_end: bool = False,
    requires_mid_anchors: bool = False,
    explicit: Optional[str] = None,
    take_policy: Optional[str] = None,
    duration_sec: Optional[float] = None,
) -> Dict[str, object]:
    """Choose 1/2/N-frame execution from story grammar and native capability.

    `shot_count>1` means editorial coverage changes, not a continuous keyframe
    interpolation.  Such clips use separate edit-cut takes when boundary images
    exist — unless storyboard declares `take_policy=single_take_multishot` and
    the backend can natively carry a multi-shot narrative inside one generation
    (capability + duration gated; otherwise fall back to edit-cut takes).  A
    middle anchor is otherwise required only for an explicitly risky continuous
    shot.
    """
    control = video_backend_frame_control(backend, channel)
    supports_last = bool(control.get("supports_last_frame"))
    supports_native_mid = bool(control.get("supports_native_mid_anchors"))
    requested = str(explicit or "").strip().lower()
    policy = str(take_policy or "").strip().lower()
    if requested in VIDEO_FRAME_STRATEGIES:
        strategy = requested
        reason = "explicit_storyboard_strategy"
    elif int(shot_count or 0) > 1 and policy == "single_take_multishot":
        if single_take_multishot_supported(backend, duration_sec):
            strategy = "single_take_multishot"
            reason = "storyboard_take_policy_single_take_and_backend_multishot_native"
        else:
            required_boundaries = max(1, int(shot_count) - 1)
            strategy = "edit_cut" if int(anchor_count or 0) >= required_boundaries and need_end else "edit_cut_pending_assets"
            reason = "single_take_multishot_fallback_backend_unsupported_or_span_exceeds_window"
    elif int(shot_count or 0) > 1:
        required_boundaries = max(1, int(shot_count) - 1)
        strategy = "edit_cut" if int(anchor_count or 0) >= required_boundaries and need_end else "edit_cut_pending_assets"
        reason = "multiple_editorial_shots_require_hard_cut_coverage"
    elif requires_mid_anchors:
        if supports_native_mid:
            strategy = "native_multiframe"
            reason = "high_risk_continuous_shot_with_native_mid_control"
        elif supports_last:
            strategy = "split_relay"
            reason = "high_risk_continuous_shot_requires_explicit_relay"
        else:
            strategy = "reroute_required"
            reason = "high_risk_continuous_shot_backend_cannot_consume_mid_anchors"
    elif need_end and supports_last:
        strategy = "first_last"
        reason = "single_beat_with_required_end_state"
    else:
        strategy = "first_only"
        reason = "low_risk_single_beat_or_backend_first_frame_only"
    return {
        "strategy": strategy,
        "reason": reason,
        "shot_count": max(1, int(shot_count or 1)),
        "anchor_count": max(0, int(anchor_count or 0)),
        "need_end": bool(need_end),
        "take_policy": policy,
        "supports_last_frame": supports_last,
        "supports_native_mid_anchors": supports_native_mid,
        "frame_control_mode": control.get("mode") or "unknown",
    }


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


def anchor_consumption_plan(
    backend: Optional[str],
    channel: Optional[str] = None,
    *,
    anchor_count: int = 0,
    need_end: bool = False,
    frame_strategy: Optional[str] = None,
) -> Dict[str, Any]:
    """Describe how first/mid/end keyframes can actually be consumed by the backend.

    `backend_supports_three_plus_frames()` answers the video capability question.
    Image-stage policy is stricter: declared first/mid/end image assets are still
    produced by default. This function answers the execution question: whether
    declared mid anchors become native timeline keyframes, require split relay,
    or are only available for QC/manual reference.
    """
    key = effective_frame_backend(backend, channel)
    spec = VIDEO_BACKEND_PROFILES.get(key)
    control = video_backend_frame_control(backend, channel)
    supports_native_mid = bool(control.get("supports_native_mid_anchors"))
    supports_last = bool(control.get("supports_last_frame"))
    max_reference_images = int(control.get("max_reference_images") or 0)
    known = spec is not None
    requested_strategy = str(frame_strategy or "").strip().lower()
    mode = "first_frame"
    if requested_strategy == "edit_cut":
        mode = "edit_cut"
    elif requested_strategy == "edit_cut_pending_assets":
        mode = "edit_cut_pending_assets"
    elif requested_strategy == "reference_qc":
        mode = "reference_only_qc"
    elif requested_strategy == "reroute_required":
        mode = "unsupported_mid_anchor"
    elif requested_strategy == "first_only":
        mode = "first_frame"
    elif requested_strategy == "first_last":
        mode = "first_last" if supports_last else "unsupported_endframe"
    elif requested_strategy == "native_multiframe":
        mode = "native_multiframe" if supports_native_mid else "unsupported_mid_anchor"
    elif requested_strategy == "split_relay":
        mode = "split_relay" if supports_last else "unsupported_mid_anchor"
    elif requested_strategy == "single_take_multishot":
        # 多镜位一次生成：镜位切换由 multishot-native 后端在一条 take 内部完成，
        # 不消费 edit_cut 边界锚为时间轴；首帧（+可选尾帧）仍按后端能力喂入。
        mode = "single_take_multishot" if video_backend_supports_multishot(backend) else "unsupported_multishot_take"
    elif anchor_count > 0:
        if supports_native_mid:
            mode = "native_multiframe"
        elif supports_last:
            mode = "split_relay"
        elif max_reference_images > 0:
            mode = "reference_only_qc"
        elif known:
            mode = "unsupported_mid_anchor"
        else:
            mode = "unknown_manual_confirm"
    elif need_end:
        if supports_last:
            mode = "first_last"
        elif known:
            mode = "unsupported_endframe"
        else:
            mode = "unknown_manual_confirm"
    consumes_endframe = bool(need_end and (
        mode in {"native_multiframe", "split_relay", "first_last", "edit_cut"}
        or (mode == "single_take_multishot" and supports_last)
    ))
    plan: Dict[str, Any] = {
        "backend": normalize_video_backend(backend or "", default="") or (backend or ""),
        "execution_backend": key,
        "frame_control_mode": control.get("mode", "unknown"),
        "anchor_count": int(anchor_count or 0),
        "need_end": bool(need_end),
        "consumption_mode": mode,
        "frame_strategy": requested_strategy or "legacy_auto",
        "consumes_mid_anchors_natively": mode == "native_multiframe",
        "consumes_endframe": consumes_endframe,
        "requires_split_relay": mode == "split_relay",
        "reference_only": mode == "reference_only_qc",
        "known_profile": known,
        "supports_native_mid_anchors": supports_native_mid,
        "supports_last_frame": supports_last,
        "auto_routable": video_backend_auto_routable(backend),
    }
    if mode == "edit_cut":
        plan["action"] = "generate separate physical takes for storyboard shots and join them with editorial cuts"
    elif mode == "edit_cut_pending_assets":
        plan["action"] = "create missing shot-boundary images before paid generation"
    elif mode == "native_multiframe":
        if need_end:
            plan["action"] = "submit first/mid/end frames in one native multi-keyframe request"
        else:
            plan["action"] = "submit first/mid frames in one native multi-keyframe request; no storyboard endframe is submitted"
    elif mode == "split_relay":
        if need_end:
            plan["action"] = "split clip into first-last relay parts; mid anchors are segment boundary frames"
        else:
            plan["action"] = "split clip through mid anchors only; no storyboard endframe is submitted"
    elif mode == "first_last":
        plan["action"] = "submit first+last frames as timeline endpoints"
    elif mode == "reference_only_qc":
        plan["action"] = "do not assume timeline consumption; use anchors as references/QC or reroute"
    elif mode.startswith("unsupported"):
        plan["action"] = "keep image anchors for QC/reference; reroute to native multiframe/first-last backend or split manually before paid video"
    else:
        plan["action"] = "manual confirmation required before paid generation"
    return plan
