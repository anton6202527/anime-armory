#!/usr/bin/env python3
"""Shared platform/backend profiles for n2d video generation.

This is the machine-readable source for fields that otherwise drift between
`n2d-video/references/platforms.md`, `n2d-image/references/platforms.md`, and
the model router.  Human docs may explain tradeoffs, but scripts should read
these constants for routing/gate decisions.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# 候选快照新鲜度戳记（本线 _lib/freshness.py 据此判过期）。
# 这是「生视频模型/渠道」选择点的能力档快照；max_clip_seconds/native_av/frame_control、以及
# 下方 MOTION_CONTROL_PROFILES（运镜/运动控制能力）和 lipsync_audio_ref（音频参考口型）都随后端迭代变，
# 同属本快照、同一个戳记覆盖（freshness 注册 id=n2d-video-backends）。
# 采集日期：2026-06-19  来源：各后端官方文档 + cli_snapshots/（待逐条复核）
CATALOG_VERIFIED = {
    "date": "2026-06-19",
    "source": (
        "Dreamina CLI snapshots + Google Veo docs + Luma Ray docs + OpenAI Sora discontinuation notice; "
        "other entries are conservative fallbacks"
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
        "aliases": ("seedance", "Seedance 2.0", "seedance2.0", "seedance 2.0"),
        "max_clip_seconds": 15,
        "default_mode": "image2video",
        "identity_mechanism": "face_lock",
        "native_av": True,
        "lipsync_audio_ref": True,  # Seedance 2.0 音素级口型：可吃音频参考做口型驱动
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
        # 2026-06：Sora Web/App 已公告停服，API 也处于终止窗口。保留档案只为读旧项目/人工补单；
        # 自动路由、原生音画候选、批量付费提交不得再把 Sora 当 primary/fallback。
        "native_av": False,
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


def video_backend_supports_multishot(backend: Optional[str]) -> bool:
    """该后端是否支持「多镜单次生成」（一次出多镜头叙事、跨镜一致、无缝转场）。纯函数·可测。"""
    return normalize_video_backend(backend or "", default="") in MULTISHOT_NATIVE_BACKENDS


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


def video_backend_profile(backend: str) -> Optional[Dict[str, object]]:
    key = normalize_video_backend(backend, default="")
    if not key:
        return None
    spec = VIDEO_BACKEND_PROFILES.get(key)
    return dict(spec) if spec else None


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


def anchor_consumption_plan(
    backend: Optional[str],
    channel: Optional[str] = None,
    *,
    anchor_count: int = 0,
    need_end: bool = False,
) -> Dict[str, Any]:
    """Describe how first/mid/end keyframes can actually be consumed by the backend.

    `backend_supports_three_plus_frames()` answers the policy question ("do we still
    require a 3-frame contract?").  This function answers the execution question:
    whether declared mid anchors become native timeline keyframes, require split
    relay, or are only available for QC/manual reference.
    """
    key = effective_frame_backend(backend, channel)
    spec = VIDEO_BACKEND_PROFILES.get(key)
    control = video_backend_frame_control(backend, channel)
    supports_native_mid = bool(control.get("supports_native_mid_anchors"))
    supports_last = bool(control.get("supports_last_frame"))
    max_reference_images = int(control.get("max_reference_images") or 0)
    known = spec is not None
    mode = "first_frame"
    if anchor_count > 0:
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
    plan: Dict[str, Any] = {
        "backend": normalize_video_backend(backend or "", default="") or (backend or ""),
        "execution_backend": key,
        "frame_control_mode": control.get("mode", "unknown"),
        "anchor_count": int(anchor_count or 0),
        "need_end": bool(need_end),
        "consumption_mode": mode,
        "consumes_mid_anchors_natively": mode == "native_multiframe",
        "consumes_endframe": bool(supports_last or mode == "native_multiframe"),
        "requires_split_relay": mode == "split_relay",
        "reference_only": mode == "reference_only_qc",
        "known_profile": known,
        "supports_native_mid_anchors": supports_native_mid,
        "supports_last_frame": supports_last,
        "auto_routable": video_backend_auto_routable(backend),
    }
    if mode == "native_multiframe":
        plan["action"] = "submit first/mid/end frames in one native multi-keyframe request"
    elif mode == "split_relay":
        plan["action"] = "split clip into first-last relay parts; mid anchors are segment boundary frames"
    elif mode == "first_last":
        plan["action"] = "submit first+last frames as timeline endpoints"
    elif mode == "reference_only_qc":
        plan["action"] = "do not assume timeline consumption; use anchors as references/QC or reroute"
    elif mode.startswith("unsupported"):
        plan["action"] = "reroute to native multiframe/first-last backend or rewrite storyboard frame contract"
    else:
        plan["action"] = "manual confirmation required before paid generation"
    return plan
