#!/usr/bin/env python3
"""Route n2d video clips to suitable model backends.

This is deliberately rule based.  The route table is a production contract, not
a creative guess: it should be stable enough for gate checks and batch reruns.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Dict, List, Optional

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  与 gate 共用的单一真值源
    MOTION_CONTROL_REQUIRED_SHOT_TYPES,  # 高危接触镜头集
    VIDEO_MODEL_ROUTES_KIND,             # 路由产物 kind
    is_native_av_mode,                   # 原生音画判定（与 n2d_settings/gate 同源）
)
from n2d_platform_profiles import (  # noqa: E402  视频后端档案单一真值源
    NATIVE_AV_BACKENDS,
    VIDEO_BACKEND_LABELS,
    VIDEO_BACKEND_MAX_SECONDS,
    normalize_video_backend,
    video_backend_max_seconds,
)
from n2d_settings import load_settings as _load_settings_md  # noqa: E402  _设置.md 解析单一真值源


BACKEND_LABELS = VIDEO_BACKEND_LABELS
BACKEND_MAX_SECONDS = VIDEO_BACKEND_MAX_SECONDS

# 本表描述「运镜/运动控制」能力（level + 运动类 capabilities：motion_brush/pose_sequence/depth…），
# 与 n2d_contract.IDENTITY_VIDEO_ADAPTERS（描述「身份绑定」mode：character_id/face_lock/reference_controls）
# 是两个不同关注点，刻意不合并。⚠️ 但其中身份类能力词（character_id/face_lock/reference_controls）与契约重叠：
# 若某后端身份 mode 名在契约里改了，这里的同名 capability 字串也要同步，避免两表对身份能力各说各话。
BACKEND_MOTION_CONTROL = {
    "dreamina": {
        "level": "weak",
        "capabilities": ["first_frame", "end_frame_text"],
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

SPEECH_SHOT_TYPES = {"dialogue_shot_reverse", "dialogue_closeup"}

# 支持「音频参考 / 口型驱动」的后端：能把一段配音当口型条件喂进去、同帧出对口型画面。
# Seedance 2.0 音素级口型（可吃音频参考）、可灵 Omni 原生口型。用于 voice_first + 对口型 opt-in
# 的 voice_conditioned_lipsync 路由（音轨仍是 voice-first 克隆音，模型音频仅作口型条件）。
LIPSYNC_AUDIO_REF_BACKENDS = {"seedance", "kling"}

# 关闭对口型的 _设置.md 值；其余值（开启/配音对齐/原生口型/on…）视为 opt-in。
LIPSYNC_OFF_VALUES = {"", "关闭", "否", "off", "no", "none", "disable", "disabled"}

COMPLEX_TEMPLATES = {
    "fight_exchange",
    "chase",
    "dialogue_shot_reverse",
    "magic_burst",
    "flight",
    "intimate_interaction",
    "hug_or_pull",
    "multi_character_same_frame",
    "ensemble_blocking",
    "multi_person_blocking",
}

# 高危物理接触镜头集（接触/形变风险）——与 gate 的 Motion Control 硬闸判定同源，见 n2d_contract。
CONTACT_SHOT_TYPES = set(MOTION_CONTROL_REQUIRED_SHOT_TYPES)

PHYSICAL_INTERACTION_SHOT_TYPES = {
    *CONTACT_SHOT_TYPES,
}

MULTI_PERSON_SHOT_TYPES = {
    "multi_character_same_frame",
    "ensemble_blocking",
    "multi_person_blocking",
}


def normalize_backend(value: str, default: str = "dreamina") -> str:
    return normalize_video_backend(value, default=default)


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def load_settings(root: Path) -> Dict[str, str]:
    # 解析单一真值源在 n2d_settings.load_settings；保留薄包装兼容 Path 入参与既有调用。
    return _load_settings_md(str(root))


def routing_mode_from_settings(settings: Mapping[str, str]) -> str:
    value = settings.get("视频模型路由", "").strip()
    if "固定" in value:
        return "fixed_default"
    return "auto"


def av_mode_from_settings(settings: Mapping[str, str]) -> str:
    """生产模式 → 音画路线。`制作模式=原生音画` → native_av；否则 voice_first（默认）。
    判定走 n2d_contract.is_native_av_mode（与 n2d_settings.is_native_av / gate 同源）。"""
    return "native_av" if is_native_av_mode(settings.get("制作模式", "")) else "voice_first"


def load_storyboard(root: Path, episode: str, storyboard: Optional[Path] = None) -> Dict[str, Any]:
    path = storyboard or root / "脚本" / episode / "storyboard.json"
    if not path.is_file():
        raise FileNotFoundError(f"storyboard not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return " ".join(_flatten_text(v) for v in value)
    return str(value)


def _clip_text(clip: Mapping[str, Any]) -> str:
    keys = (
        "id",
        "label",
        "scene",
        "description",
        "summary",
        "action",
        "camera",
        "visual",
        "dialogue",
        "template",
        "template_contract",
        "continuity",
        "audio",
        "notes",
    )
    return " ".join(_flatten_text(clip.get(k)) for k in keys)


def _has_any(text: str, words: Iterable[str]) -> bool:
    lower = text.lower()
    return any(w.lower() in lower for w in words)


def infer_shot_type(clip: Mapping[str, Any]) -> str:
    template = str(clip.get("template") or "").strip()
    if template in COMPLEX_TEMPLATES:
        return template

    text = _clip_text(clip)
    if _has_any(text, ("打斗", "交手", "出拳", "挥剑", "命中", "撞击", "fight", "combat", "hit")):
        return "fight_exchange"
    if _has_any(text, ("追逐", "追赶", "奔逃", "逃跑", "chase", "running away")):
        return "chase"
    if _has_any(text, ("御剑", "飞行", "凌空", "掠过云", "飞掠", "flight", "flying")):
        return "flight"
    if _has_any(text, ("对话反打", "反打", "过肩", "对视", "台词", "dialogue", "shot reverse", "ots")):
        return "dialogue_shot_reverse"
    if _has_any(text, ("说话特写", "口型", "嘴部", "近景说话", "lip-sync", "mouth", "close-up dialogue")):
        return "dialogue_closeup"
    if _has_any(text, ("法术", "符阵", "灵光", "爆发", "雷劫", "光束", "magic", "burst", "spell")):
        return "magic_burst"
    if _has_any(text, ("拥抱", "抱住", "拉扯", "拉住", "抓腕", "拽住", "推开", "扯住", "拉袖", "tug", "pull", "grab wrist", "hug")):
        return "hug_or_pull"
    if _has_any(text, ("牵手", "靠近", "亲密", "搀扶", "扶住", "抚脸", "扶肩", "疗伤", "intimate", "touch")):
        return "intimate_interaction"
    if _has_any(text, ("多人同框", "双人同框", "两人同框", "三人同框", "同框", "同画面", "two-shot", "group shot")):
        return "multi_character_same_frame"
    if _has_any(text, ("群像", "群戏", "群臣", "门徒", "人群", "围观", "队列", "站位", "多人站位", "ensemble", "crowd")):
        return "ensemble_blocking"
    if _has_any(text, ("多人", "围住", "multi-person", "blocking")):
        return "multi_person_blocking"
    if _has_any(text, ("空镜", "转场", "远景", "氛围", "环境", "establishing", "ambience", "empty")):
        return "empty_establishing"
    return "general_motion"


def clip_duration_seconds(clip: Mapping[str, Any]) -> float:
    for key in ("duration", "duration_sec", "seconds", "时长"):
        raw = clip.get(key)
        if raw is None:
            continue
        m = re.search(r"\d+(?:\.\d+)?", str(raw))
        if m:
            return float(m.group(0))
    return 0.0


def clip_has_named_characters(clip: Mapping[str, Any]) -> bool:
    text = _clip_text(clip)
    if _has_any(text, ("无人物", "空镜", "empty shot", "no character")):
        return False
    return _has_any(text, ("角色", "人物", "主角", "脸", "发型", "服装", "character", "face"))


def clip_has_mouth_visible(clip: Mapping[str, Any]) -> bool:
    text = _clip_text(clip)
    return _has_any(text, ("口型", "嘴", "说话", "台词", "正脸", "mouth", "lip-sync", "speaking", "dialogue"))


def clip_multi_person(clip: Mapping[str, Any]) -> bool:
    template = str(clip.get("template") or "").strip()
    if template in MULTI_PERSON_SHOT_TYPES:
        return True
    text = _clip_text(clip)
    if _has_any(text, ("多人", "群像", "众人", "围住", "多人同框", "multi-person", "crowd")):
        return True
    chars = clip.get("characters") or clip.get("角色")
    if isinstance(chars, list) and len(chars) >= 2:
        return True
    return False


def _route_fixed(clip: Mapping[str, Any], shot_type: str, default_backend: str) -> Dict[str, Any]:
    fallback = [b for b in ("seedance", "kling", "dreamina") if b != default_backend]
    return {
        "primary_backend": default_backend,
        "fallback_backends": fallback[:2],
        "mode": "image2video" if shot_type != "empty_establishing" else "text2video",
        "native_audio_policy": "none",
        "identity_requirement": "reference_group" if clip_has_named_characters(clip) else "none",
        "rationale": [f"routing_mode=fixed_default, use project 生视频AI={default_backend} for this clip"],
        "prompt_requirements": ["write model routing field even in fixed mode", "keep fallback/degrade plan explicit"],
        "degrade_plan": "If the fixed backend fails twice, switch 视频模型路由 to auto and reroute the affected clip.",
    }


def _is_speech_shot(clip: Mapping[str, Any], shot_type: str) -> bool:
    """说话/对白镜：对话反打、说话特写，或 mouth_visible 的镜头。"""
    return shot_type in SPEECH_SHOT_TYPES or clip_has_mouth_visible(clip)


def _lipsync_enabled(lip_sync_setting: str) -> bool:
    """`_设置.md 对口型` 是否 opt-in（非「关闭」即视为启用）。"""
    return str(lip_sync_setting).strip().lower() not in LIPSYNC_OFF_VALUES


def _route_voice_conditioned_lipsync(
    clip: Mapping[str, Any], shot_type: str, default_backend: str
) -> Dict[str, Any]:
    """voice_first + 对口型 opt-in 的说话镜路由：把克隆配音 line_NN.wav 当口型条件喂进
    支持音频参考的后端（Seedance 2.0 音素级 / 可灵 Omni），同帧出对口型画面。

    与 native_av 的根本区别：音轨仍是 voice-first 的克隆音色（compose 用配音轨），模型音频
    只作 lip 条件、不接管声音——既不双人声，又省一道后期 MuseTalk/Wav2Lip 对口型 pass。
    """
    primary = default_backend if default_backend in LIPSYNC_AUDIO_REF_BACKENDS else "seedance"
    fallback = [b for b in ("kling", "seedance", "veo") if b != primary]
    return {
        "primary_backend": primary,
        "fallback_backends": fallback,
        "mode": "voice_conditioned_lipsync",
        "native_audio_policy": "lipsync_condition_only",
        "identity_requirement": "character_id_or_reference_group",
        "rationale": [
            "voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面",
            "音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass",
        ],
        "prompt_requirements": [
            "把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声",
            "speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）",
            "成片仍须 AI 标识水印（compliance 闸门）",
        ],
        "degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。",
    }


def _route_native_av_speech(clip: Mapping[str, Any], shot_type: str, default_backend: str) -> Dict[str, Any]:
    """原生音画模式下的说话镜路由：一次出同步音画（台词+口型+环境声），绕过配音先行。

    用原生音画能力最强的后端做 primary（Seedance 2.0 / Veo 3 / Sora），台词文本与情绪由
    脚本提供、镜头时长由脚本规划驱动（不读配音先行的时长清单）。失败回退配音先行链路。
    """
    native_primary = default_backend if default_backend in NATIVE_AV_BACKENDS else "seedance"
    fallback = [b for b in ("veo", "sora", "seedance") if b != native_primary]
    return {
        "primary_backend": native_primary,
        "fallback_backends": fallback,
        "mode": "native_av",
        "native_audio_policy": "native_speech",
        "identity_requirement": "character_id_or_reference_group" if clip_has_named_characters(clip) else "none",
        "rationale": [
            "制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工",
            "台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音",
        ],
        "prompt_requirements": [
            "提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声",
            "speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）",
            "成片须带 AI 标识水印（compliance 闸门），native_speech 不豁免合规",
        ],
        "degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。",
    }


def choose_route(
    clip: Mapping[str, Any],
    shot_type: str,
    *,
    default_backend: str = "dreamina",
    routing_mode: str = "auto",
    native_audio_setting: str = "丢弃",
    lip_sync_setting: str = "关闭",
    av_mode: str = "voice_first",
) -> Dict[str, Any]:
    if routing_mode == "fixed_default":
        route = _route_fixed(clip, shot_type, default_backend)
        if av_mode == "native_av" and _is_speech_shot(clip, shot_type):
            route["rationale"].append("制作模式=原生音画，但视频模型路由=固定生视频AI；固定选择优先，不自动切 native_speech 后端")
            route["prompt_requirements"].append("speech_policy=no_native_speech unless the fixed backend is explicitly configured downstream for native AV")
        return route

    # 原生音画模式：说话镜优先走原生同步音画路由（绕过配音先行）。其余镜头走常规路由。
    if av_mode == "native_av" and _is_speech_shot(clip, shot_type):
        route = _route_native_av_speech(clip, shot_type, default_backend)
        fallbacks: List[str] = []
        for backend in route["fallback_backends"] + [default_backend]:
            backend = normalize_backend(backend)
            if backend != route["primary_backend"] and backend not in fallbacks:
                fallbacks.append(backend)
        route["fallback_backends"] = fallbacks[:3]
        return route
    # voice_first + 对口型 opt-in 的说话镜：克隆配音作口型条件喂进支持音频参考的后端，
    # 同帧出对口型画面（不双人声、省后期对口型 pass）。固定后端模式不抢路由。
    if (
        av_mode == "voice_first"
        and routing_mode != "fixed_default"
        and _is_speech_shot(clip, shot_type)
        and _lipsync_enabled(lip_sync_setting)
    ):
        route = _route_voice_conditioned_lipsync(clip, shot_type, default_backend)
        fallbacks = []
        for backend in route["fallback_backends"] + [default_backend]:
            backend = normalize_backend(backend)
            if backend != route["primary_backend"] and backend not in fallbacks:
                fallbacks.append(backend)
        route["fallback_backends"] = fallbacks[:3]
        return route
    if shot_type == "fight_exchange":
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "frames2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group",
            "rationale": [
                "fight/contact motion benefits from first/last frame control and motion brush",
                "impact beats need short controllable motion rather than free choreography",
            ],
            "prompt_requirements": [
                "write first frame and end frame as hard constraints",
                "one contact action per clip; avoid multi-hit choreography",
            ],
            "degrade_plan": "Split into setup and impact clips; keep the hit frame as the end frame.",
        }
    elif shot_type in ("chase", "flight"):
        route = {
            "primary_backend": "seedance",
            "fallback_backends": ["kling", default_backend],
            "mode": "image2video",
            "native_audio_policy": "none",
            "identity_requirement": "face_lock_or_reference_group" if clip_has_named_characters(clip) else "none",
            "rationale": [
                "long continuous motion and moving backgrounds benefit from longer single-shot generation",
                "flight/chase should lock character pose and move background layers",
            ],
            "prompt_requirements": [
                "keep body pose stable; put speed into background, foreground occluders, cloth and camera tracking",
                "avoid large limb changes unless there is an end frame",
            ],
            "degrade_plan": "Cut to front/back reaction shots or split into approach, pass-by, and exit clips.",
        }
    elif shot_type in ("dialogue_shot_reverse", "dialogue_closeup"):
        primary = "kling"
        fallback = ["veo", "seedance"] if _lipsync_enabled(lip_sync_setting) or "保留" in native_audio_setting else ["seedance", default_backend]
        route = {
            "primary_backend": primary,
            "fallback_backends": [b for b in fallback if b != primary],
            "mode": "image2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group",
            "rationale": [
                "dialogue shots are identity-sensitive and often need lip-sync or strong reference controls",
                "default n2d audio remains voiceover-first; do not let the video backend generate speech",
            ],
            "prompt_requirements": [
                "mark mouth_visible and speech_policy=no_native_speech",
                "prefer side/back/OTS if lip-sync is disabled",
            ],
            "degrade_plan": "Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.",
        }
    elif shot_type == "magic_burst":
        route = {
            "primary_backend": "seedance",
            "fallback_backends": ["kling", default_backend],
            "mode": "image2video",
            "native_audio_policy": "native_sfx" if "低音量" in native_audio_setting else "none",
            "identity_requirement": "face_lock_or_reference_group" if clip_has_named_characters(clip) else "none",
            "rationale": [
                "energy buildup, release, and aftermath benefit from continuous VFX motion",
                "native SFX can be opt-in only when no speech risk exists",
            ],
            "prompt_requirements": [
                "lock effect color/shape from template_contract",
                "describe charge, release, and aftermath beats; no new spell colors",
            ],
            "degrade_plan": "Split into charge frame, release frame, and aftermath; use VFX overlays in compose if needed.",
        }
    elif shot_type in ("intimate_interaction", "hug_or_pull"):
        if shot_type == "hug_or_pull":
            prompt_requirements = [
                "write exact contact point, force direction, and release/end pose",
                "use first/end frames; avoid full-body tangled motion when a hand insert or OTS can carry the beat",
            ]
            degrade_plan = "Replace the tug/hug with hand close-up, reaction reverse shot, or split into approach, contact, and release clips."
        else:
            prompt_requirements = [
                "write exact blocking and contact point; avoid ambiguous full-body interaction",
                "use end frame for the final pose",
            ]
            degrade_plan = "Replace full contact with reaction close-up, hand insert, or shot/reverse-shot."
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "frames2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group",
            "rationale": [
                "close contact and occlusion need precise motion and identity control",
                "hands/faces are high-risk and should be constrained by first/last frames",
            ],
            "prompt_requirements": prompt_requirements,
            "degrade_plan": degrade_plan,
        }
    elif shot_type in MULTI_PERSON_SHOT_TYPES:
        if shot_type == "multi_character_same_frame":
            prompt_requirements = [
                "freeze character slots, left/right positions, and face priority",
                "keep two to three named faces maximum; lower-priority faces may be side/back/soft focus",
            ]
            degrade_plan = "If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip."
        elif shot_type == "ensemble_blocking":
            prompt_requirements = [
                "write screen positions and focus hierarchy; background crowd must be silhouette, back view, or soft focus",
                "one speaking/action focus per clip; do not ask every crowd member to have a clear face",
            ]
            degrade_plan = "Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways."
        else:
            prompt_requirements = [
                "freeze left/right positions and eyelines",
                "if more than three named characters share frame, split into groups or reaction shots",
            ]
            degrade_plan = "Split crowd blocking into two-character OTS pairs plus establishing shot."
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "frames2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group",
            "rationale": [
                "multi-person staging needs reference controls and stable screen direction",
                "single-backend generic generation often swaps faces or screen positions",
            ],
            "prompt_requirements": prompt_requirements,
            "degrade_plan": degrade_plan,
        }
    elif shot_type == "empty_establishing":
        native = "ambience" if "丢弃" not in native_audio_setting else "none"
        route = {
            "primary_backend": "veo" if native != "none" else "seedance",
            "fallback_backends": ["dreamina", "seedance" if native != "none" else "veo"],
            "mode": "text2video",
            "native_audio_policy": native,
            "identity_requirement": "none",
            "rationale": [
                "empty/ambience shots have low identity risk and can use native ambience when opted in",
                "text2video is acceptable when no character identity must be preserved",
            ],
            "prompt_requirements": [
                "confirm mouth_visible=no and speech_policy=no_native_speech",
                "keep ambience sound low-risk; no voices, no narration, no humming",
            ],
            "degrade_plan": "Use Dreamina/Seedance silent clip and add SFX/BGM in compose.",
        }
    else:
        route = {
            "primary_backend": default_backend,
            "fallback_backends": [b for b in ("seedance", "kling") if b != default_backend],
            "mode": "image2video",
            "native_audio_policy": "none",
            "identity_requirement": "reference_group" if clip_has_named_characters(clip) else "none",
            "rationale": ["general motion can use the project default backend for cost and speed"],
            "prompt_requirements": ["keep character/camera/dynamic detail three-part prompt explicit"],
            "degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.",
        }

    # Avoid duplicate fallbacks and make sure default is available as last resort.
    fallbacks: List[str] = []
    for backend in route["fallback_backends"] + [default_backend]:
        backend = normalize_backend(backend)
        if backend != route["primary_backend"] and backend not in fallbacks:
            fallbacks.append(backend)
    route["fallback_backends"] = fallbacks[:3]
    return route


def make_clip_id(clip: Mapping[str, Any], index: int) -> str:
    raw = clip.get("clip_id") or clip.get("id") or clip.get("label") or ""
    text = str(raw).strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", text, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", text)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{index:02d}"


def risk_flags_for_clip(clip: Mapping[str, Any], shot_type: str, primary_backend: str) -> List[str]:
    flags: List[str] = []
    duration = clip_duration_seconds(clip)
    if duration and duration > video_backend_max_seconds(primary_backend):
        flags.append("long_duration")
    if clip_multi_person(clip) or shot_type in MULTI_PERSON_SHOT_TYPES:
        flags.append("multi_person")
    if clip_has_mouth_visible(clip):
        flags.append("mouth_visible")
    if shot_type in CONTACT_SHOT_TYPES:
        flags.append("contact_motion")
        flags.append("feature_melting_risk")
        flags.append("physical_interaction")
    if clip_has_named_characters(clip) and shot_type in {"fight_exchange", "flight", *CONTACT_SHOT_TYPES, *MULTI_PERSON_SHOT_TYPES}:
        flags.append("identity_drift_risk")
    if shot_type == "empty_establishing":
        flags.append("low_identity_risk")
    return sorted(set(flags))


def motion_control_contract(
    clip: Mapping[str, Any],
    clip_id: str,
    shot_type: str,
    primary_backend: str,
    episode: str,
) -> Dict[str, Any]:
    """Return the route-level Motion Control contract.

    The router only declares the control requirement.  Control assets live in a
    per-clip manifest and are validated by n2d-review gate before paid video
    generation.
    """
    manifest_path = f"出视频/{episode}/control/{clip_id}/motion_control_manifest.json"
    backend_caps = BACKEND_MOTION_CONTROL.get(primary_backend, BACKEND_MOTION_CONTROL["dreamina"])

    if shot_type in PHYSICAL_INTERACTION_SHOT_TYPES:
        if shot_type == "fight_exchange":
            required_inputs = ["pose_sequence", "depth_sequence", "instance_masks", "contact_map"]
            failure_modes = ["feature_melting", "limb_fusion", "weapon_contact_drift", "body_interpenetration"]
            control_notes = [
                "impact/contact beats must be constrained by pose/depth/instance ownership or degraded into setup+impact cuts",
                "OpenPose/DWPose alone is not enough for weapon/body contact; add depth + instance masks where possible",
            ]
        elif shot_type == "hug_or_pull":
            required_inputs = ["pose_sequence", "depth_sequence", "instance_masks", "contact_map"]
            failure_modes = ["feature_melting", "hand_fusion", "limb_ownership_swap", "body_overlap_collapse"]
            control_notes = [
                "hug/pull/grab shots need explicit contact point, occlusion order, and body-part ownership",
                "without ready control assets, degrade to hand insert + OTS/reaction + release frame",
            ]
        else:
            required_inputs = ["pose_sequence", "depth_sequence", "instance_masks"]
            failure_modes = ["feature_melting", "hand_fusion", "face_occlusion_drift"]
            control_notes = [
                "near contact needs pose/depth plus ownership constraints; text prompt is insufficient",
                "without ready control assets, degrade to close-up contact/reaction/shot-reverse-shot",
            ]
        return {
            "level": "required",
            "required": True,
            "manifest_required": True,
            "manifest_path": manifest_path,
            "required_inputs": required_inputs,
            "backend_control_level": backend_caps["level"],
            "backend_capabilities": backend_caps["capabilities"],
            "recommended_control_backends": ["comfyui_ltx", "kling_motion_control", "seedance_reference_video"],
            "failure_modes": failure_modes,
            "gate_policy": "block_without_ready_manifest_or_degrade_only_manifest",
            "degrade_allowed": True,
            "notes": control_notes,
        }

    if shot_type in MULTI_PERSON_SHOT_TYPES or shot_type in {"flight", "chase"}:
        return {
            "level": "recommended",
            "required": False,
            "manifest_required": False,
            "manifest_path": manifest_path,
            "required_inputs": ["pose_sequence", "depth_sequence"],
            "backend_control_level": backend_caps["level"],
            "backend_capabilities": backend_caps["capabilities"],
            "recommended_control_backends": ["comfyui_ltx", "kling_motion_control", "seedance_reference_video"],
            "failure_modes": ["slot_drift", "pose_drift", "identity_drift"],
            "gate_policy": "warn_or_degrade_if_repeated_failure",
            "degrade_allowed": True,
            "notes": ["use control manifest only if this shot has failed before or is a recurring high-risk template"],
        }

    return {
        "level": "none",
        "required": False,
        "manifest_required": False,
        "manifest_path": "",
        "required_inputs": [],
        "backend_control_level": backend_caps["level"],
        "backend_capabilities": backend_caps["capabilities"],
        "recommended_control_backends": [],
        "failure_modes": [],
        "gate_policy": "not_required",
        "degrade_allowed": False,
        "notes": [],
    }


def route_clip(
    clip: Mapping[str, Any],
    index: int,
    *,
    episode: str,
    default_backend: str,
    routing_mode: str,
    native_audio_setting: str,
    lip_sync_setting: str,
    av_mode: str = "voice_first",
) -> Dict[str, Any]:
    shot_type = infer_shot_type(clip)
    route = choose_route(
        clip,
        shot_type,
        default_backend=default_backend,
        routing_mode=routing_mode,
        native_audio_setting=native_audio_setting,
        lip_sync_setting=lip_sync_setting,
        av_mode=av_mode,
    )
    primary = normalize_backend(route["primary_backend"], default_backend)
    clip_id = make_clip_id(clip, index)
    risk_flags = risk_flags_for_clip(clip, shot_type, primary)
    if route.get("native_audio_policy") == "native_speech":
        risk_flags = sorted(set(risk_flags) | {"native_speech"})
    return {
        "clip_id": clip_id,
        "shot_type": shot_type,
        "template": str(clip.get("template") or "none"),
        "primary_backend": primary,
        "fallback_backends": route["fallback_backends"],
        "mode": route["mode"],
        "native_audio_policy": route["native_audio_policy"],
        "identity_requirement": route["identity_requirement"],
        "max_clip_seconds": video_backend_max_seconds(primary),
        "risk_flags": risk_flags,
        "motion_control": motion_control_contract(clip, clip_id, shot_type, primary, episode),
        "rationale": route["rationale"],
        "prompt_requirements": route["prompt_requirements"],
        "degrade_plan": route["degrade_plan"],
    }


def route_episode(
    root: Path,
    episode: str,
    *,
    storyboard_path: Optional[Path] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    settings = load_settings(root)
    default_backend = normalize_backend(settings.get("生视频AI", "即梦"))
    routing_mode = routing_mode_from_settings(settings)
    av_mode = av_mode_from_settings(settings)
    native_audio_setting = settings.get("视频原生音轨", "丢弃")
    lip_sync_setting = settings.get("对口型", "关闭")
    storyboard = load_storyboard(root, episode, storyboard_path)
    clips = storyboard.get("clips") or []
    if not isinstance(clips, list):
        raise ValueError("storyboard.json clips must be a list")
    return {
        "kind": VIDEO_MODEL_ROUTES_KIND,
        "version": 1,
        "root": str(root),
        "episode": episode,
        "routing_mode": routing_mode,
        "production_mode": settings.get("制作模式", "配音先行") or "配音先行",
        "av_mode": av_mode,
        "default_backend": default_backend,
        "generated_at": generated_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "routes": [
            route_clip(
                clip,
                i,
                episode=episode,
                default_backend=default_backend,
                routing_mode=routing_mode,
                native_audio_setting=native_audio_setting,
                lip_sync_setting=lip_sync_setting,
                av_mode=av_mode,
            )
            for i, clip in enumerate(clips, 1)
        ],
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 视频模型路由",
        "",
        f"- episode: {plan.get('episode')}",
        f"- routing_mode: {plan.get('routing_mode')}",
        f"- production_mode: {plan.get('production_mode')} (av_mode={plan.get('av_mode')})",
        f"- default_backend: {plan.get('default_backend')}",
        f"- generated_at: {plan.get('generated_at')}",
        "",
        "## 本集模型路由表",
        "",
        "| Clip | shot_type | primary | fallback | mode | native_audio | identity | motion_control | 风险 | 降级 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for route in plan.get("routes", []):
        fallback = ", ".join(route.get("fallback_backends", []))
        flags = ", ".join(route.get("risk_flags", [])) or "-"
        motion = route.get("motion_control") or {}
        motion_level = motion.get("level", "-") if isinstance(motion, Mapping) else "-"
        lines.append(
            "| {clip} | {shot} | {primary} | {fallback} | {mode} | {audio} | {identity} | {motion} | {flags} | {degrade} |".format(
                clip=route.get("clip_id", ""),
                shot=route.get("shot_type", ""),
                primary=route.get("primary_backend", ""),
                fallback=fallback,
                mode=route.get("mode", ""),
                audio=route.get("native_audio_policy", ""),
                identity=route.get("identity_requirement", ""),
                motion=motion_level,
                flags=flags,
                degrade=str(route.get("degrade_plan", "")).replace("|", "/"),
            )
        )
    lines.extend(["", "## 逐 Clip 路由理由", ""])
    for route in plan.get("routes", []):
        lines.append(f"### {route.get('clip_id')} — {route.get('shot_type')}")
        lines.append(f"- primary: {route.get('primary_backend')}")
        lines.append(f"- fallback: {', '.join(route.get('fallback_backends', []))}")
        lines.append(f"- mode: {route.get('mode')}")
        lines.append(f"- identity: {route.get('identity_requirement')}")
        motion = route.get("motion_control") or {}
        if isinstance(motion, Mapping):
            lines.append(f"- motion_control: {motion.get('level')} (manifest={motion.get('manifest_path') or '-'})")
            if motion.get("required_inputs"):
                lines.append(f"- motion_control_required_inputs: {', '.join(motion.get('required_inputs', []))}")
        lines.append("- rationale:")
        for item in route.get("rationale", []):
            lines.append(f"  - {item}")
        lines.append("- prompt_requirements:")
        for item in route.get("prompt_requirements", []):
            lines.append(f"  - {item}")
        lines.append(f"- degrade_plan: {route.get('degrade_plan')}")
        lines.append("")
    return "\n".join(lines)


def write_plan(plan: Mapping[str, Any], root: Path, episode: str) -> Dict[str, Path]:
    out_dir = root / "出视频" / episode / "prompt"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "video_model_routes.json"
    md_path = out_dir / "video_model_routes.md"
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def main() -> int:
    parser = argparse.ArgumentParser(description="Route n2d video clips to suitable model backends.")
    parser.add_argument("root", help="作品根, e.g. 制漫剧/剧名")
    parser.add_argument("episode", help="第N集")
    parser.add_argument("--storyboard", help="override storyboard.json path")
    parser.add_argument("--write", action="store_true", help="write video_model_routes.json/md under 出视频/第N集/prompt")
    parser.add_argument("--markdown", action="store_true", help="print markdown instead of JSON")
    ns = parser.parse_args()

    root = Path(ns.root)
    storyboard = Path(ns.storyboard) if ns.storyboard else None
    plan = route_episode(root, ns.episode, storyboard_path=storyboard)
    if ns.write:
        paths = write_plan(plan, root, ns.episode)
        print(f"wrote {paths['json']}")
        print(f"wrote {paths['markdown']}")
    else:
        if ns.markdown:
            print(render_markdown(plan))
        else:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
