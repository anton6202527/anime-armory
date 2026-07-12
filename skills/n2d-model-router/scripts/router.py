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
from typing import Any, Dict, List, Optional, Sequence

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  与 gate 共用的单一真值源
    ACTION_CHOREOGRAPHY_COMMON_FIELDS,
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS,
    MOTION_CONTROL_RISK_FLAGS,
    MOTION_CONTROL_REQUIRED_SHOT_TYPES,  # Motion Control required 镜头集
    PRODUCTION_MODE_DEFAULT,             # 制作模式默认值单一真值源
    SHOT_TYPE_KEYWORDS,                  # 镜头类型判定关键词（与 gate 专项模板检测同源）
    SPECTACLE_BACKEND_BENCHMARK_KIND,
    VIDEO_MODEL_ROUTES_KIND,             # 路由产物 kind
    infer_spectacle_type,
    is_native_av_mode,                   # 原生音画判定（与 n2d_settings/gate 同源）
    motion_control_inputs_for_spectacle,
    policy_lattice_document,
    route_policy_resolution,
)
from n2d_platform_profiles import (  # noqa: E402  视频后端档案单一真值源
    LIPSYNC_AUDIO_REF_BACKENDS,
    MOTION_CONTROL_PROFILES,
    MULTILINGUAL_LIPSYNC_BACKENDS,
    NATIVE_AV_BACKENDS,
    SPECTACLE_BACKEND_PRIOR,
    VIDEO_BACKEND_LABELS,
    VIDEO_BACKEND_MAX_SECONDS,
    anchor_consumption_plan,
    effective_frame_backend,
    normalize_video_backend,
    spectacle_backend_prior_ranking,
    video_backend_auto_routable,
    video_backend_capability_confidence,
    video_backend_default_quality_tier,
    video_backend_frame_control,
    video_backend_max_seconds,
    video_backend_supports_motion_reference,
    video_backend_supports_multilingual_lipsync,
    video_backend_supports_multishot,
    video_backend_supports_quality_tier,
    video_backend_supports_reference_to_video,
    preferred_multilingual_lipsync_backend,
)
from n2d_const import (  # noqa: E402  打斗镜判定 + 风格自适应视觉盛宴（与出图 runner 同源单一真值源）
    is_combat_spectacle_shot,
    combat_spectacle_guidance_for_style,
)
from n2d_settings import load_settings as _load_settings_md  # noqa: E402  _设置.md 解析单一真值源
from production_mode_router import build_route as build_production_mode_route  # noqa: E402
from seam_contract import needs_end_anchor, normalize_seam_mode, requires_boundary_frame  # noqa: E402
from video_execution_adapter import execution_status as video_execution_status  # noqa: E402
try:  # ③ 一角一后端亲和（advisory）：读 identity_registry 找已注册原生视频主体的角色
    from n2d_registry import load_identity_registry as _load_identity_registry  # noqa: E402
except Exception:  # pragma: no cover - 布局兜底
    _load_identity_registry = None  # type: ignore


BACKEND_LABELS = VIDEO_BACKEND_LABELS
BACKEND_MAX_SECONDS = VIDEO_BACKEND_MAX_SECONDS

# 运镜/运动控制能力档与「音频参考口型」后端集的单一真值源已上移到 n2d_platform_profiles
# （与 frame_control 同属 CATALOG_VERIFIED 带日期快照 + freshness 注册，C2 易变候选清单要求）。
# 这里保留本地别名以兼容既有 .get() 调用点；运动控制 vs 身份绑定（n2d_contract.IDENTITY_VIDEO_ADAPTERS）
# 仍是两个刻意不合并的关注点，身份类能力词若在契约改名，platform_profiles 里的同名字串要同步。
BACKEND_MOTION_CONTROL = MOTION_CONTROL_PROFILES

SPEECH_SHOT_TYPES = {"dialogue_shot_reverse", "dialogue_closeup", "reveal_reaction_chain", "public_confrontation", "relationship_turn"}
NARRATIVE_STATE_SHOT_TYPES = {"reveal_reaction_chain", "public_confrontation", "relationship_turn"}

# 关闭对口型的 _设置.md 值；其余值（开启/配音对齐/原生口型/on…）视为 opt-in。
LIPSYNC_OFF_VALUES = {"", "关闭", "否", "off", "no", "none", "disable", "disabled"}
# 「对话近景」保留为显式兼容档：仅对话近景说话镜走配音对齐口型，其余说话镜不进口型路由。
# 2026-07 起非原生音画默认改为 `视频生成音频策略=无声视频流`，不再默认启用此档。
LIPSYNC_DIALOGUE_CLOSEUP_DEFAULT_VALUES = {
    v.lower() for v in ("对话近景", "对话近景默认", "dialogue_closeup", "dialogue_closeup_default")
}
SILENT_VIDEO_FLOW_VALUES = {"", "无声视频流", "静音视频流", "无声", "静音", "video_only", "silent_video", "no_audio"}
LIPSYNC_VIDEO_FLOW_VALUES = {"配音对齐口型", "音频参考口型", "voice_conditioned_lipsync", "lipsync", "lip_sync"}
AMBIENCE_VIDEO_FLOW_VALUES = {"低风险环境声", "低风险环境声/音效", "ambience", "native_sfx"}
FALLBACK_OFF_VALUES = {"", "无", "不使用", "关闭", "否", "off", "no", "none", "disable", "disabled"}

# 跨后端英雄镜多版（2026-06-26）：英雄镜=名场面/开场钩/高潮（IP 改编初始流量来源）。开启后这些镜
# 同时跑 primary + secondary 两个后端各出一版，pooled 进候选，video_qc 选优，避免单后端在高价值镜翻车。
# costly 选择点：默认关闭、花钱前确认（见 选择点与偏好.md「英雄镜多版」）。
HERO_MULTI_OFF_VALUES = {"", "关闭", "否", "off", "no", "none", "disable", "disabled"}
# 英雄镜高潮/关系转折/真相揭示/对质 shot_type（复用 NARRATIVE_STATE_SHOT_TYPES + 动作/奇观高潮）。
HERO_SHOT_TYPES = NARRATIVE_STATE_SHOT_TYPES | {
    "fight_exchange", "magic_burst", "tribulation_breakthrough",
    "alchemy_forging", "dual_cultivation", "kiss_or_near_kiss",
}
# 名场面/爽点兑现词表（与 n2d-image keyshot_candidates 的 signature_scene 同义；两线各自持有、不跨线 import）。
HERO_SIGNATURE_RE = re.compile(
    r"(名场面|高光时刻|打脸|逆袭|反杀|反败为胜|翻盘|绝地反击|封神|破境|突破境界|觉醒时刻|"
    r"重逢|相认|认亲|告白|表白|复仇|报仇|雪耻|揭穿|揭露身份|真相大白|身世揭晓|夺权|登基|加冕|"
    r"碾压|力压全场|扮猪吃虎|一鸣惊人|决战|对决|决斗|生死决|诀别|牺牲|英雄救美|全场震惊|众人震惊|"
    r"当众打脸|封印|救场|封面|首图|系列总钩)")

COMPLEX_TEMPLATES = {
    "fight_exchange",
    "chase",
    "mount_ride",
    "vehicle_ride",
    "vessel_flight",
    "road_vehicle",
    "stealth_stalk",
    "screen_insert",
    "evidence_search",
    "tribulation_breakthrough",
    "meditation_cultivation",
    "alchemy_forging",
    "dual_cultivation",
    "kiss_or_near_kiss",
    "array_ritual",
    "soul_manifestation",
    "realm_portal",
    "contract_summon",
    "talent_test",
    "dialogue_shot_reverse",
    "reveal_reaction_chain",
    "public_confrontation",
    "magic_burst",
    "flight",
    "intimate_interaction",
    "hug_or_pull",
    "relationship_turn",
    "multi_character_same_frame",
    "ensemble_blocking",
    "multi_person_blocking",
}

# 高危物理接触镜头集（接触/形变风险）——只表示真实接触语义；Motion Control required 集合
# 还包含追逐/飞行/多人调度等高动量或复杂空间镜，不能混成 "contact_motion"。
CONTACT_SHOT_TYPES = {"fight_exchange", "kiss_or_near_kiss", "hug_or_pull", "intimate_interaction", "dual_cultivation"}

PHYSICAL_INTERACTION_SHOT_TYPES = {
    *MOTION_CONTROL_REQUIRED_SHOT_TYPES,
}

MULTI_PERSON_SHOT_TYPES = {
    "multi_character_same_frame",
    "ensemble_blocking",
    "multi_person_blocking",
}


def normalize_backend(value: str, default: str = "dreamina") -> str:
    return normalize_video_backend(value, default=default)


def project_default_backend(settings: Mapping[str, str]) -> str:
    """Return the route-level default backend from split model/channel settings.

    `生视频模型` is preferred because routing is capability/model driven. Old
    projects with only `生视频AI` continue to work, and `生视频渠道` is a final
    fallback when the model name is absent or unsupported by this router.
    """
    for value in (
        settings.get("生视频模型", ""),
        settings.get("生视频AI", ""),
        settings.get("生视频渠道", ""),
        "Seedance 2.0",
    ):
        backend = normalize_backend(value, default="")
        if backend:
            return backend
    return normalize_backend("即梦")


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


def fixed_fallback_backends_from_settings(settings: Mapping[str, str], default_backend: str) -> Optional[List[str]]:
    """Project-level fixed-mode fallback override.

    Empty/missing keeps the historical router fallback list.  Explicit off
    values allow a machine that only has the default backend CLI installed to
    avoid advertising unavailable local backends in generated route tables.
    """
    raw = settings.get("视频备用后端", "").strip()
    if not raw:
        return None
    if raw.lower() in FALLBACK_OFF_VALUES or raw in FALLBACK_OFF_VALUES:
        return []
    parts = [p.strip() for p in re.split(r"[,，、/\s]+", raw) if p.strip()]
    out: List[str] = []
    for part in parts:
        backend = normalize_backend(part, default="")
        if backend and backend != default_backend and backend not in out:
            out.append(backend)
    return out


_OVERSEAS_REGIONS = {"北美", "东南亚", "全球", "north_america", "southeast_asia", "global", "overseas"}


def is_overseas_target(settings: Mapping[str, str]) -> bool:
    """出海(目标说话语言≠中文)判定：发行地区/变现模式/字幕语言任一指向海外非中文台词。纯函数·可测。

    用于说话镜路由：出海时优先多语言唇同步最强后端，避免非中文台词口型/口音错配。
    港澳台/中英双语仍以中文为主语音，不算（唇同步对的是被说出来的那种语言）。"""
    region = str(settings.get("发行地区", "") or "").strip().lower()
    monet = str(settings.get("变现模式", "") or "").strip()
    subs = str(settings.get("字幕语言", "") or "").strip()
    if region in _OVERSEAS_REGIONS:
        return True
    if "海外" in monet or "overseas" in monet.lower():
        return True
    if subs in {"仅英文", "english_only", "en"}:
        return True
    return False


def av_mode_from_settings(settings: Mapping[str, str]) -> str:
    """生产模式 → 音画路线。默认制作模式来自 n2d_contract.PRODUCTION_MODE_DEFAULT。
    判定走 n2d_contract.is_native_av_mode（与 n2d_settings.is_native_av / gate 同源）。"""
    mode = settings.get("制作模式", "") or PRODUCTION_MODE_DEFAULT
    normalized = str(mode or "").strip().lower()
    if is_native_av_mode(mode):
        return "native_av"
    if "混合自动路由" in str(mode) or "hybrid" in normalized or "mixed" in normalized:
        return "hybrid"
    return "voice_first"


# ── 时效档（成本轴·与质量档正交·G8）────────────────────────────────────────────
# 2026 视频生成 API 首现「batch/隔夜半价」（Sora2 Batch 24h SLA -50%、Seedance flex -50% 预告）。
# 非赶投放窗口的量产放量集，可路由 batch_24h 档省成本；首集打样/赶投放走 realtime。
# **诚实边界**：实际 async batch endpoint 由后端能力决定，属执行适配层 follow-up（视频后端 batch
# 通道接入后才真省）；本函数只产**路由意图**，供 dashboard 拆 realtime vs batch 成本账与执行侧消费。
URGENCY_REALTIME = "realtime"
URGENCY_BATCH = "batch_24h"


def urgency_tier_from_settings(settings: Mapping[str, str]) -> str:
    """项目级时效档路由意图。纯函数·可测。读 `投放时效`（实时/隔夜批量），默认 realtime（安全·绝不静默延迟）。"""
    raw = str(settings.get("投放时效", "") or "").strip().lower()
    if raw in ("隔夜批量", "批量", "隔夜", "batch", "batch_24h", "flex", "非紧急"):
        return URGENCY_BATCH
    return URGENCY_REALTIME


def video_generation_audio_policy_from_settings(settings: Mapping[str, str]) -> str:
    """Return the paid video-generation audio policy.

    `视频原生音轨` only tells compose what to do with an audio stream after the
    backend returns an MP4.  This setting controls which generation path the
    router is allowed to choose.  Non-native AV defaults to video-only.
    """
    return str(settings.get("视频生成音频策略", "") or "无声视频流").strip() or "无声视频流"


def _audio_policy_norm(value: str) -> str:
    return str(value or "").strip().lower()


def _is_silent_video_flow(value: str) -> bool:
    raw = str(value or "").strip()
    return raw in SILENT_VIDEO_FLOW_VALUES or _audio_policy_norm(raw) in SILENT_VIDEO_FLOW_VALUES


def _is_lipsync_video_flow(value: str) -> bool:
    raw = str(value or "").strip()
    return raw in LIPSYNC_VIDEO_FLOW_VALUES or _audio_policy_norm(raw) in LIPSYNC_VIDEO_FLOW_VALUES


def _is_ambience_video_flow(value: str) -> bool:
    raw = str(value or "").strip()
    return raw in AMBIENCE_VIDEO_FLOW_VALUES or _audio_policy_norm(raw) in AMBIENCE_VIDEO_FLOW_VALUES


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
        "title",
        "name",
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
        "visual_contract",
        "characters",
        "角色",
        "character_ids",
        "cast",
        "roles",
        "subjects",
        "人物",
        "audio",
        "notes",
    )
    return " ".join(_flatten_text(clip.get(k)) for k in keys)


def _style_text_from_storyboard(storyboard: Mapping[str, Any]) -> str:
    """本剧风格名/视觉基调（取 storyboard.style_contract）。供打斗镜 motion 侧视觉盛宴按风格族分流。

    读不到 → 空串（combat_spectacle_guidance_for_style 回 cinematic 默认·向后兼容）。"""
    sc = storyboard.get("style_contract") if isinstance(storyboard, Mapping) else None
    if not isinstance(sc, Mapping):
        return ""
    for k in ("风格名", "style_name", "视觉基调"):
        v = sc.get(k)
        if isinstance(v, (list, tuple)):
            v = "、".join(str(x) for x in v if str(x).strip())
        if str(v or "").strip():
            return str(v).strip()
    return ""


def apply_motion_spectacle_guidance(routes: Sequence[Mapping[str, Any]], clips: Sequence[Mapping[str, Any]], style_text: str) -> int:
    """打斗/法术/动作镜：把风格自适应「经费在燃烧」指导挂进 route 机器字段（motion 侧·与出图 runner 同源）。

    出图 runner 已按风格族注入四层视觉盛宴；视频 prompt 由 LLM 撰写、此前拿不到这份指导——
    于是首帧是盛宴、运动段可能平淡。这里把同一份风格自适应文案挂进 route，供出视频 prompt 作者落实 +
    spectacle QC 对账。纯函数式 in-place 标注，返回标注镜数。非打斗镜不碰（避免稀释）。"""
    guidance = combat_spectacle_guidance_for_style(style_text or "")
    applied = 0
    for route, clip in zip(routes, clips):
        if not isinstance(route, dict) or not is_combat_spectacle_shot(_clip_text(clip)):
            continue
        route["motion_spectacle_guidance"] = guidance
        reqs = route.setdefault("prompt_requirements", [])
        hint = "motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）"
        if isinstance(reqs, list) and hint not in reqs:
            reqs.append(hint)
        applied += 1
    return applied


def _has_any(text: str, words: Iterable[str]) -> bool:
    lower = text.lower()
    for word in words:
        needle = str(word or "").strip().lower()
        if not needle:
            continue
        # English route keywords such as "car" must not match substrings like
        # "water-carrying"; CJK keywords intentionally keep substring matching.
        if re.search(r"[a-z0-9]", needle) and not re.search(r"[\u4e00-\u9fff]", needle):
            if re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", lower):
                return True
        elif needle in lower:
            return True
    return False


CHARACTER_FIELD_KEYS = (
    "characters",
    "角色",
    "character_ids",
    "角色ID",
    "角色id",
    "cast",
    "roles",
    "subjects",
    "人物",
    "人物列表",
    "character_refs",
)
NO_CHARACTER_VALUES = {"", "无", "none", "null", "[]", "无人物", "空镜", "no character", "empty shot"}
CHARACTER_REF_RE = re.compile(r"\b(CHAR_[A-Za-z0-9_]+)(?:/([^\s，；、`,|]+))?\b")
ASSET_REF_RE = re.compile(r"\b((?:LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_]+)\b")
CHARACTER_ID_KEYS = ("id", "character_id", "characterId", "角色ID", "角色id", "角色编号")
CHARACTER_FORM_KEYS = ("form", "形态", "状态", "costume_form", "variant")


def _value_has_named_character(value: Any) -> bool:
    """Return true when a structured storyboard field explicitly names characters.

    Fixed routing must not infer identity requirements only from prose keywords:
    generated storyboards often store the actual cast in `characters[]`, while
    the scene/continuity text may only describe the action.  This keeps empty
    shots explicitly empty without dropping identity refs for dialogue/reaction
    shots that have structured cast data.
    """
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in NO_CHARACTER_VALUES or text in NO_CHARACTER_VALUES:
            return False
        if _has_any(text, ("无人物", "空镜", "no character", "empty shot")):
            return False
        return True
    if isinstance(value, Mapping):
        if not value:
            return False
        return any(_value_has_named_character(v) for v in value.values())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_value_has_named_character(v) for v in value)
    return False


def _collect_character_refs(value: Any, *, allow_raw: bool = True) -> List[Dict[str, str]]:
    refs: List[Dict[str, str]] = []
    if value is None:
        return refs
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in NO_CHARACTER_VALUES or text in NO_CHARACTER_VALUES:
            return refs
        for match in CHARACTER_REF_RE.finditer(text):
            ref = {"character_id": match.group(1)}
            if match.group(2):
                ref["form"] = match.group(2).strip()
            refs.append(ref)
        if allow_raw and not refs and _value_has_named_character(text):
            refs.append({"raw": text})
        return refs
    if isinstance(value, Mapping):
        cid = ""
        form = ""
        for key in CHARACTER_ID_KEYS:
            if str(value.get(key) or "").strip():
                cid = str(value.get(key) or "").strip()
                break
        for key in CHARACTER_FORM_KEYS:
            if str(value.get(key) or "").strip():
                form = str(value.get(key) or "").strip()
                break
        if cid:
            ref = {"character_id": cid}
            if form:
                ref["form"] = form
            refs.append(ref)
        for child in value.values():
            refs.extend(_collect_character_refs(child, allow_raw=allow_raw))
        return refs
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            refs.extend(_collect_character_refs(item, allow_raw=allow_raw))
    return refs


def clip_character_refs(clip: Mapping[str, Any]) -> List[Dict[str, str]]:
    refs: List[Dict[str, str]] = []
    for key in CHARACTER_FIELD_KEYS:
        refs.extend(_collect_character_refs(clip.get(key)))
    # Structured cast fields are the visible-character truth when present.
    # Prose fields often mention offscreen/forbidden characters in continuity,
    # degrade plans, or negative prompts; treating those mentions as references
    # can make the video backend render exactly the face we meant to avoid.
    if not any(ref.get("character_id") for ref in refs):
        refs.extend(_collect_character_refs(_clip_text(clip), allow_raw=False))
    out: List[Dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in refs:
        cid = str(ref.get("character_id") or "").strip()
        form = str(ref.get("form") or "").strip()
        raw = str(ref.get("raw") or "").strip()
        if not (cid or raw):
            continue
        key = (cid, form, raw)
        if key in seen:
            continue
        seen.add(key)
        item: Dict[str, str] = {}
        if cid:
            item["character_id"] = cid
        if form:
            item["form"] = form
        if raw and not cid:
            item["raw"] = raw
        out.append(item)
    return out


def clip_asset_refs(clip: Mapping[str, Any]) -> List[str]:
    """Structured asset ids referenced by this clip, preserving deterministic order."""
    seen: set[str] = set()
    out: List[str] = []
    for match in ASSET_REF_RE.finditer(_clip_text(clip)):
        asset_id = match.group(1)
        if asset_id not in seen:
            seen.add(asset_id)
            out.append(asset_id)
    return out


def infer_shot_type(clip: Mapping[str, Any]) -> str:
    template = str(clip.get("template") or "").strip()
    if template in COMPLEX_TEMPLATES:
        return template

    text = _clip_text(clip)
    # 关键词表单一真值源在 common（与 gate 专项镜头模板检测同源，避免判型口径漂移）；保留本地小写匹配器。
    for shot_type, keywords in SHOT_TYPE_KEYWORDS:
        if _has_any(text, keywords):
            return shot_type
    return "general_motion"


def clip_loc(clip: Mapping[str, Any]) -> str:
    """镜头场景 LOC（同场景多镜单次生成分组用）。优先结构化字段，再回退 LOC_ token。"""
    for key in ("loc", "location", "scene_id", "scene", "场景", "地点"):
        raw = str(clip.get(key) or "").strip()
        if raw:
            return raw.split("/")[0].strip()
    m = re.search(r"\bLOC_[\w\-一-鿿]+\b", _clip_text(clip))
    return m.group(0) if m else ""


def clip_duration_seconds(clip: Mapping[str, Any]) -> float:
    for key in ("duration", "duration_sec", "seconds", "时长"):
        raw = clip.get(key)
        if raw is None:
            continue
        m = re.search(r"\d+(?:\.\d+)?", str(raw))
        if m:
            return float(m.group(0))
    return 0.0


def _timeline_frame_requirements(clip: Mapping[str, Any]) -> Dict[str, int | bool]:
    """Storyboard timeline frame demand for route-time backend capability checks.

    `gate.py` later enforces the same concern before paid generation.  The
    router should avoid producing an obviously doomed primary when the current
    execution channel already has a stronger multi-keyframe path.
    """
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    anchor_count = 0
    if isinstance(cont.get("midframe"), Mapping):
        anchor_count = 1
    elif isinstance(cont.get("anchors"), list):
        anchor_count = len([a for a in cont.get("anchors") if isinstance(a, Mapping)])
    need_end = needs_end_anchor(clip)
    return {
        "anchor_count": anchor_count,
        "need_end": need_end,
        "total_frames": 1 + anchor_count + (1 if need_end else 0),
    }


def _timeline_anchor_seconds(clip: Mapping[str, Any], duration: float, anchor_count: int) -> List[float]:
    """Return usable mid-anchor timestamps for duration relay planning."""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    anchors = cont.get("anchors") if isinstance(cont.get("anchors"), list) else []
    times: List[float] = []
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            continue
        raw = anchor.get("at_sec") or anchor.get("time_sec") or anchor.get("seconds")
        try:
            sec = float(raw)
        except (TypeError, ValueError):
            continue
        if 0.0 < sec < duration and sec not in times:
            times.append(sec)
    if isinstance(cont.get("midframe"), Mapping):
        raw = cont.get("midframe", {}).get("at_sec") or cont.get("midframe", {}).get("time_sec")
        try:
            sec = float(raw)
        except (TypeError, ValueError):
            sec = 0.0
        if 0.0 < sec < duration and sec not in times:
            times.append(sec)
    times = sorted(times)
    if len(times) >= anchor_count:
        return times[:anchor_count]
    # Missing explicit times should not make a valid first/mid/end contract unusable.
    # Use even boundaries as an execution hint; the real frame paths still come from
    # storyboard continuity / landed image assets.
    missing = anchor_count - len(times)
    slots = anchor_count + 1
    for idx in range(1, slots):
        sec = round(duration * idx / slots, 3)
        if 0.0 < sec < duration and sec not in times:
            times.append(sec)
            missing -= 1
            if missing <= 0:
                break
    return sorted(times)[:anchor_count]


def duration_segment_relay_plan(
    clip: Mapping[str, Any],
    primary: str,
    anchor_plan: Mapping[str, Any],
    *,
    clip_id: str = "",
) -> Dict[str, Any]:
    """Plan deterministic first→mid→end submits when one storyboard clip exceeds cap.

    This does not change story semantics or invent frames. It only declares that
    the video execution layer must submit multiple paid jobs using already-landed
    timeline anchors as segment boundaries, so every paid request stays under the
    backend's documented max duration.
    """
    duration = clip_duration_seconds(clip)
    max_sec = video_backend_max_seconds(primary)
    out: Dict[str, Any] = {
        "required": bool(duration and max_sec and duration > max_sec),
        "supported": False,
        "max_clip_seconds": max_sec,
        "clip_seconds": duration,
        "segments": [],
    }
    if not out["required"]:
        return out

    anchor_count = int(anchor_plan.get("anchor_count") or 0)
    need_end = bool(anchor_plan.get("need_end"))
    if anchor_count <= 0 or not need_end:
        out["reason"] = "clip exceeds backend cap but lacks mid+end timeline anchors for deterministic relay"
        return out
    if not (anchor_plan.get("consumes_endframe") or anchor_plan.get("supports_last_frame")):
        out["reason"] = "clip exceeds backend cap but primary cannot consume a hard end-frame boundary"
        return out

    times = _timeline_anchor_seconds(clip, duration, anchor_count)
    if len(times) < anchor_count:
        out["reason"] = "clip exceeds backend cap but has no usable mid-anchor timestamps"
        return out

    boundaries = [0.0, *times, duration]
    segments: List[Dict[str, Any]] = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        seg_duration = round(max(0.0, end - start), 3)
        from_frame = "first_frame" if idx == 0 else f"mid_anchor_{idx}"
        to_frame = f"mid_anchor_{idx + 1}" if idx < len(boundaries) - 2 else "end_frame"
        segments.append({
            "segment_id": f"{clip_id or 'Clip'}_seg{idx + 1:02d}",
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": seg_duration,
            "from_frame": from_frame,
            "to_frame": to_frame,
            "submit_mode": "first_last_relay",
        })

    out["segments"] = segments
    max_segment = max((float(seg.get("duration_sec") or 0.0) for seg in segments), default=0.0)
    out["max_segment_seconds"] = round(max_segment, 3)
    out["supported"] = bool(max_segment and max_segment <= max_sec)
    if out["supported"]:
        out["reason"] = "split paid generation into first/mid/end relay segments under backend cap"
    else:
        out["reason"] = f"longest relay segment {max_segment:g}s still exceeds backend cap {max_sec:g}s"
    return out


def duration_for_backend_selection(entry: Mapping[str, Any]) -> float:
    plan = entry.get("duration_segment_relay") if isinstance(entry.get("duration_segment_relay"), Mapping) else {}
    if plan.get("supported") and plan.get("max_segment_seconds"):
        return float(plan.get("max_segment_seconds") or 0.0)
    return float(entry.get("clip_seconds") or 0.0)


def _primary_frame_capability_mismatch(clip: Mapping[str, Any], primary: str, video_channel: str) -> List[str]:
    req = _timeline_frame_requirements(clip)
    control = video_backend_frame_control(primary, video_channel)
    reasons: List[str] = []
    duration = clip_duration_seconds(clip)
    max_sec = video_backend_max_seconds(primary)
    if duration and max_sec and duration > max_sec:
        reasons.append(f"duration {duration:g}s exceeds {primary} max {max_sec}s")
    if req["need_end"] and not control.get("supports_last_frame"):
        reasons.append("storyboard needs endframe but primary lacks last-frame control")
    if req["anchor_count"] and not control.get("supports_native_mid_anchors"):
        reasons.append("storyboard has mid anchors but primary lacks native mid-anchor control")
    return reasons


def _backend_paid_routing_allowed(backend: str, video_channel: str) -> bool:
    """Whether automatic paid routing may select this backend for the configured channel."""
    channel = normalize_backend(str(video_channel or ""), default="")
    if not channel:
        return True
    if effective_frame_backend(backend, video_channel) != channel:
        return False
    conf = video_backend_capability_confidence(backend, video_channel)
    return bool(conf.get("paid_routing_allowed"))


def _backend_covers_clip_contract(clip: Mapping[str, Any], backend: str, video_channel: str) -> bool:
    req = _timeline_frame_requirements(clip)
    anchor_plan = anchor_consumption_plan(
        backend,
        video_channel,
        anchor_count=int(req.get("anchor_count") or 0),
        need_end=bool(req.get("need_end")),
    )
    if req["need_end"] and not anchor_plan.get("consumes_endframe"):
        return False
    if req["anchor_count"] and str(anchor_plan.get("consumption_mode") or "") in {
        "unsupported_mid_anchor",
        "unknown_manual_confirm",
        "reference_only_qc",
    }:
        return False
    duration = clip_duration_seconds(clip)
    max_sec = video_backend_max_seconds(backend)
    if duration and max_sec and duration > max_sec:
        relay = duration_segment_relay_plan(clip, backend, anchor_plan)
        if not relay.get("supported"):
            return False
    return True


def _first_paid_executable_backend(
    clip: Mapping[str, Any],
    candidates: Iterable[str],
    *,
    primary: str,
    video_channel: str,
) -> str:
    for candidate in candidates:
        backend = normalize_backend(str(candidate or ""), default="")
        if not backend or backend == primary:
            continue
        if not video_backend_auto_routable(backend):
            continue
        if not _backend_paid_routing_allowed(backend, video_channel):
            continue
        if not _backend_covers_clip_contract(clip, backend, video_channel):
            continue
        return backend
    return ""


def prefer_execution_multiframe_backend(
    clip: Mapping[str, Any],
    route: Dict[str, Any],
    *,
    default_backend: str,
    video_channel: str,
) -> Dict[str, Any]:
    """Use the project execution channel when it is the stronger frame contract.

    Example: `生视频模型=Seedance 2.0` through `生视频渠道=即梦/Dreamina`
    executes on Dreamina's verified multiframe API.  For high-risk clips that
    have end/mid anchors or exceed a fallback backend's duration limit, a Sora
    or Kling primary can make `video_preflight` fail even though the configured
    execution channel can satisfy the storyboard frame contract.
    """
    primary = normalize_backend(str(route.get("primary_backend") or ""), default_backend)
    default = normalize_backend(default_backend, default="")
    if not default or primary == default:
        return route
    mismatch = _primary_frame_capability_mismatch(clip, primary, video_channel)
    paid_allowed = _backend_paid_routing_allowed(primary, video_channel)
    if not mismatch and paid_allowed:
        return route
    candidates = [*list(route.get("fallback_backends") or []), default, "seedance", "dreamina"]
    replacement = _first_paid_executable_backend(
        clip,
        candidates,
        primary=primary,
        video_channel=video_channel,
    )
    if not replacement:
        return route

    updated = dict(route)
    old_fallbacks = [normalize_backend(b, default="") for b in route.get("fallback_backends", [])]
    fallback = [primary] + [b for b in old_fallbacks if b and b not in {primary, replacement}]
    updated["primary_backend"] = replacement
    updated["fallback_backends"] = fallback[:3]
    rationale = list(route.get("rationale", []))
    reasons = []
    if mismatch:
        reasons.append(f"storyboard 帧/时长契约不匹配（{'; '.join(mismatch)}）")
    if not paid_allowed:
        conf = video_backend_capability_confidence(primary, video_channel)
        reasons.append(
            f"当前渠道不可自动付费路由（confidence={conf.get('confidence')}; "
            f"execution_backend={conf.get('execution_backend')}）"
        )
    rationale.append(
        f"执行渠道「{video_channel or replacement}」下改用可执行后端「{replacement}」；"
        f"原 primary「{primary}」{'；'.join(reasons)}，降为 fallback。"
    )
    updated["rationale"] = rationale
    return updated


def clip_has_named_characters(clip: Mapping[str, Any]) -> bool:
    text = _clip_text(clip)
    if _has_any(text, ("无人物", "空镜", "empty shot", "no character")):
        return False
    if any(_value_has_named_character(clip.get(k)) for k in CHARACTER_FIELD_KEYS):
        return True
    template = str(clip.get("template") or "").strip()
    if template in COMPLEX_TEMPLATES:
        return True
    if re.search(r"\bCHAR_[A-Za-z0-9_]+(?:/[^\s，；、`]+)?\b", text):
        return True
    return _has_any(text, ("角色", "人物", "主角", "脸", "发型", "服装", "character", "face"))


def t2v_action_experimental_enabled(raw: object) -> bool:
    """T2V action channel is an experimental opt-in, not the old broad `开启` switch."""
    value = str(raw or "").strip().lower()
    return value in {"实验开启", "experimental", "experiment", "experimental_on", "t2v_experimental"}


def clip_t2v_identity_reference_plan(clip: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """Return the explicit reference/identity fallback plan for named-character T2V."""
    for key in ("t2v_identity_reference_plan", "t2v_reference_plan"):
        plan = clip.get(key)
        if isinstance(plan, Mapping) and plan:
            return plan
    tc = clip.get("template_contract")
    if isinstance(tc, Mapping):
        for key in ("t2v_identity_reference_plan", "t2v_reference_plan"):
            plan = tc.get(key)
            if isinstance(plan, Mapping) and plan:
                return plan
    return None


def clip_has_t2v_identity_reference_plan(clip: Mapping[str, Any]) -> bool:
    """A named-character T2V clip needs an explicit reference/identity fallback plan."""
    return clip_t2v_identity_reference_plan(clip) is not None


def clip_has_mouth_visible(clip: Mapping[str, Any]) -> bool:
    text = _clip_text(clip)
    return _has_any(text, ("口型", "嘴", "说话", "台词", "正脸", "mouth", "lip-sync", "speaking", "dialogue"))


def clip_named_character_count(clip: Mapping[str, Any]) -> int:
    """同框具名角色数（从 template_contract.character_slots / face_priority 取）。
    ≥5 时仍按多人高风险处理，但不再自动路由到 legacy/manual-only 后端。"""
    tc = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    slots = tc.get("character_slots")
    if isinstance(slots, Mapping):
        return len(slots)
    for key in ("face_priority", "character_slots"):
        val = tc.get(key)
        if isinstance(val, (list, tuple)):
            return len(val)
    return 0


# ── ③ 一角一后端亲和（核心硬钉，无法同时满足才告警）────────────────────────────
# 治"同一核心角色跨集/跨镜被路由到不同视频后端 → 脸质感漂移"。只对**已注册原生视频主体**
# （Character ID / face_lock，status registered|ready）的角色生效：注册了原生主体 = 这角色的脸被
# 该后端锁住了，再被路由到别的后端就是跨集一致性风险。没注册原生主体的角色不产任何告警（零噪音）。
_NATIVE_VIDEO_NONNATIVE_MODES = {"reference_group", "fallback_reference_group"}


def _native_video_backend(form: Mapping[str, Any]) -> str:
    """form 已注册原生主体的视频后端（mode 非 reference_group 兜底 + status registered/ready）；无则 ''。纯函数。"""
    adapters = form.get("identity_adapters") if isinstance(form.get("identity_adapters"), Mapping) else {}
    video = adapters.get("video") if isinstance(adapters.get("video"), Mapping) else {}
    for backend, cfg in video.items():
        if not isinstance(cfg, Mapping):
            continue
        mode = str(cfg.get("mode") or "").strip()
        status = str(cfg.get("status") or "").strip()
        if mode and mode not in _NATIVE_VIDEO_NONNATIVE_MODES and status in ("registered", "ready"):
            return normalize_video_backend(backend) or str(backend)
    return ""


def build_backend_affinity(registry: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """角色 → 其跨集应锁定的视频后端（仅取已注册原生主体的角色）。返回 [{id, name, aliases, backend}]。
    纯函数·可测。核心/主演角色进入亲和后会在 route_clip 中硬钉 primary，避免跨镜换后端漂脸。"""
    out: List[Dict[str, Any]] = []
    if not isinstance(registry, Mapping):
        return out
    for ch in registry.get("characters") or []:
        if not isinstance(ch, Mapping):
            continue
        backend = ""
        for f in ch.get("forms") or []:
            if isinstance(f, Mapping):
                backend = _native_video_backend(f)
                if backend:
                    break
        if not backend:
            continue  # 无原生视频主体 = 无后端可锁 → 不产冲突噪音
        name = str(ch.get("name") or "").strip()
        aliases = {p.strip() for p in re.split(r"[/／、,，|\s]+", name) if len(p.strip()) >= 2}
        # 进 affinity = 已注册原生视频主体 = 核心/主演（脸被该后端锁死）。core 角色的 backend 即其
        # locked_backend：跨镜不得漂到别的后端（脸质感漂移）→ route_clip 对 core 冲突硬钉，非 core 仅 warn。
        out.append({"id": str(ch.get("id") or "").strip(), "name": name, "aliases": aliases,
                    "backend": backend, "core": True})
    return out


def character_backend_conflicts(clip: Mapping[str, Any], primary: str,
                                affinity: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """本镜命中的原生主体角色里，亲和后端 != 本镜 primary 的冲突明细。纯函数·可测。

    核心/主演角色（core，已注册原生视频主体=脸被该后端锁死）的冲突标 enforce=True，
    `locked_backend` 即其应被强制路由的后端；非 core 角色 enforce=False（仅 warn）。
    route_clip 据 enforce 决定是硬钉 primary 还是仅告警。"""
    if not affinity:
        return []
    text = _clip_text(clip)
    ids = set(re.findall(r"CHAR_[A-Za-z0-9_]+", text))
    primary_n = normalize_video_backend(primary) or str(primary or "")
    out: List[Dict[str, Any]] = []
    for a in affinity:
        present = (a.get("id") and a["id"] in ids) or any(al in text for al in a.get("aliases") or ())
        if present and a.get("backend") and a["backend"] != primary_n:
            core = bool(a.get("core"))
            out.append({"character": a.get("name") or a.get("id") or "?",
                        "character_id": a.get("id") or "",
                        "prefers_backend": a["backend"], "routed_backend": primary_n,
                        "locked_backend": a["backend"], "core": core, "enforce": core})
    return out


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


# ── 接力镜 → 双关键帧（首尾硬约束）路由（C1）─────────────────────────────────
# 2026 起 Kling O1/O3、即梦 multiframe2video 等支持**同时把首帧+尾帧当硬约束**插值出中间运动
# （非自由外推）。对「接力/无缝转场」镜，把上一镜尾帧 PNG 作本镜首帧硬约束喂进去时，接缝在
# 结构上被保证（边界帧就是你授权的那张图）——既稳一致性，又能让边界帧两镜复用、省一次出图。
# 这里只做**预防侧**路由/指引；落档侧 temporal_consistency 的接缝机检照常 block（双关键帧镜若
# 接缝仍漂=后端没真消费尾帧约束/被拆段了，是真故障，不能因为「声明了双关键帧」就放过=假通过）。
DUAL_KEYFRAME_CAPS = {"first_last_frame", "native_multiframe"}  # 首尾硬约束插值能力（≠ 单纯多参考图）
# 与 temporal_consistency.RELAY_TRANSITIONS / video_qc 同义，三处保持同步。
RELAY_TRANSITIONS = ("接力", "relay", "seamless", "continuous", "无缝")


def backend_supports_dual_keyframe(backend: str, video_channel: str = "") -> bool:
    """该后端在当前执行渠道下是否支持双关键帧（首尾硬约束插值）。纯函数·可测。"""
    plan = anchor_consumption_plan(backend, video_channel, anchor_count=0, need_end=True)
    if plan.get("consumes_endframe"):
        return True
    caps = BACKEND_MOTION_CONTROL.get(normalize_backend(backend), {}).get("capabilities", [])
    return bool(DUAL_KEYFRAME_CAPS.intersection(caps))


def is_relay_clip(clip: Mapping[str, Any]) -> bool:
    """Only continuous_take_relay receives the dual-keyframe relay route."""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    explicit_mode = clip.get("seam_mode") or cont.get("seam_mode")
    trans = str(clip.get("transition") or cont.get("transition") or "").strip().lower()
    need_end = any(clip.get(k) or cont.get(k) for k in ("need_endframe", "need_end_frame"))
    mode = normalize_seam_mode(
        explicit_mode,
        trans,
        need_endframe=False if str(explicit_mode or "").strip() else bool(need_end),
    ).get("mode")
    if str(explicit_mode or "").strip():
        return requires_boundary_frame(mode)
    if clip.get("relay") or cont.get("relay"):
        return True
    return requires_boundary_frame(mode)


def seam_relay_plan(clip: Mapping[str, Any], primary: str,
                    fallback_backends: List[str], video_channel: str = "") -> Dict[str, Any]:
    """接力镜的双关键帧路由计划。纯函数·可测：返回 seam_relay 子表（非接力镜也返回 is_relay=False）。

    primary 已支持双关键帧 → seam_guaranteed=True（接缝结构保证）；不支持 → 从 fallback 里挑一个
    支持的当 dual_keyframe_fallback，提示改用它把尾帧作硬约束。"""
    relay = is_relay_clip(clip)
    prim_ok = backend_supports_dual_keyframe(primary, video_channel)
    plan: Dict[str, Any] = {"is_relay": relay, "primary_supports_dual_keyframe": prim_ok}
    if not relay:
        return plan
    plan["boundary_frame_shared"] = True  # 上一镜尾帧 = 本镜首帧（同一张授权图），两镜复用省一次出图
    plan["seam_guaranteed"] = prim_ok
    if not prim_ok:
        plan["dual_keyframe_fallback"] = next(
            (b for b in fallback_backends if backend_supports_dual_keyframe(b, video_channel)), None)
    return plan


# ── 质量档（fast/high）路由（成本×质量轴·2026-06-19 流程自审落地）─────────────────
# Seedance 家族有 fast/pro 档（fast≈$0.022/s 量产默认，pro 留吃重镜）。这里只给**路由意图**
# （fast | high），不写死具体模型版本字串（版本以 cli_snapshots 为准·防过期）。落档侧出片脚本/
# CLI 把 high→pro、fast→fast 解析成实际 model_version；后端无档位能力时本字段为 n/a（不浪费意图）。
# 判据：身份吃重/高风险镜值 pro（脸/接触/多人/原生台词/已升锁）；空镜/无人物通用镜走 fast 省钱。
HIGH_TIER_SHOT_TYPES = {
    "fight_exchange", "chase", "flight", "mount_ride", "vehicle_ride", "vessel_flight",
    "road_vehicle", "stealth_stalk", "screen_insert", "evidence_search",
    "tribulation_breakthrough", "meditation_cultivation", "alchemy_forging", "dual_cultivation", "kiss_or_near_kiss", "array_ritual", "soul_manifestation",
    "realm_portal", "contract_summon", "talent_test",
    "magic_burst",
    "hug_or_pull", "intimate_interaction", "dialogue_closeup",
    "dialogue_shot_reverse", "reveal_reaction_chain", "public_confrontation", "relationship_turn",
    "multi_character_same_frame", "ensemble_blocking",
    "multi_person_blocking",
}
HIGH_TIER_RISK_FLAGS = {
    "identity_drift_risk", "contact_motion", "feature_melting_risk", "physical_interaction",
    "high_speed_motion", "spatial_path_risk", "action_choreography_required",
    "multi_person", "native_speech", "identity_escalated", "character_backend_conflict",
}


def quality_tier_for_clip(shot_type: str, risk_flags: Iterable[str], primary: str) -> str:
    """本镜质量档路由意图。纯函数·可测。后端无 fast/pro 档 → 'n/a'。

    high = 身份吃重/高风险镜（脸/接触/多人/原生台词/升锁），值得 pro 档把脸和物理钉稳；
    fast = 空镜/通用镜，量产默认省成本。判据走 shot_type + risk_flags，不 hardcode 厂商。"""
    if not video_backend_supports_quality_tier(primary):
        return "n/a"
    flags = set(risk_flags or [])
    if shot_type in HIGH_TIER_SHOT_TYPES or (flags & HIGH_TIER_RISK_FLAGS):
        return "high"
    return "fast"


# ── 视频运动参考（把已通过 clip 当运动/风格参考·reference_video_motion）─────────────
# Seedance/Kling 等可吃「视频片段参考」锁运动节奏/风格——与图身份锁正交的**跨镜运动连续性**轴。
# 对长连续运动镜（追逐/飞行/御兽/马车/飞舟/现代车辆/尾随潜入/打斗），把前一条已通过的同段 clip 作 motion/style ref 喂进去，运镜节奏
# 更连贯。只做预防侧指引（prompt_requirement + hint），不强制——首条镜无前序参考时自然跳过。
MOTION_REFERENCE_SHOT_TYPES = {
    "chase", "flight", "mount_ride", "vehicle_ride", "vessel_flight",
    "road_vehicle", "stealth_stalk", "fight_exchange", "magic_burst",
}


def motion_reference_plan(shot_type: str, primary: str) -> Dict[str, Any]:
    """长连续运动镜的视频运动参考计划。纯函数·可测。非适用镜返回 applicable=False。"""
    applicable = (
        shot_type in MOTION_REFERENCE_SHOT_TYPES
        and video_backend_supports_motion_reference(primary)
    )
    plan: Dict[str, Any] = {"applicable": applicable}
    if applicable:
        plan["use"] = "prior_approved_clip_as_video_reference"
        plan["note"] = (
            f"{primary} 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作"
            "运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。"
        )
    return plan


def execution_recipe_for_route(
    entry: Mapping[str, Any],
    clip: Mapping[str, Any],
    *,
    video_channel: str,
) -> Dict[str, Any]:
    """Normalize a route into concrete execution inputs for the video stage.

    The route chooses a backend; this recipe tells the caller what to actually
    provide to that backend: frames, reference images/videos, control manifests,
    audio policy, and fallback/degrade contract.  It is intentionally capability
    based so execution code does not parse backend prose.
    """
    backend = normalize_backend(str(entry.get("primary_backend") or ""), default="")
    frame_control = entry.get("frame_control") if isinstance(entry.get("frame_control"), Mapping) else video_backend_frame_control(backend, video_channel)
    anchor = entry.get("anchor_consumption") if isinstance(entry.get("anchor_consumption"), Mapping) else {}
    motion = entry.get("motion_control") if isinstance(entry.get("motion_control"), Mapping) else {}
    chars = entry.get("clip_characters") if isinstance(entry.get("clip_characters"), list) else []
    character_refs = [
        {
            "character_id": str(c.get("character_id") or ""),
            "form": str(c.get("form") or ""),
            "binding": entry.get("identity_requirement") or "none",
        }
        for c in chars if isinstance(c, Mapping) and (c.get("character_id") or c.get("raw"))
    ]
    motion_ref = entry.get("motion_reference") if isinstance(entry.get("motion_reference"), Mapping) else {}
    max_reference_images = int(frame_control.get("max_reference_images") or 0)
    mode = str(entry.get("mode") or "").strip().lower()
    consumes_timeline_frames = mode not in {"text2video", "t2v"}
    anchor_count = int(anchor.get("anchor_count") or 0) if consumes_timeline_frames else 0
    uses_last_frame = bool(
        consumes_timeline_frames
        and anchor.get("need_end")
        and (anchor.get("consumes_endframe") or frame_control.get("supports_last_frame"))
    )
    timeline_frame_count = (1 + anchor_count + (1 if uses_last_frame else 0)) if consumes_timeline_frames else 0
    recipe = {
        "backend": backend,
        "execution_backend": anchor.get("execution_backend") or backend,
        "mode": entry.get("mode"),
        "quality_tier": entry.get("quality_tier"),
        "urgency_tier": entry.get("urgency_tier"),
        "frame_inputs": {
            "first_frame": bool(consumes_timeline_frames),
            "last_frame": uses_last_frame,
            "mid_anchors": anchor_count,
            "consumption_mode": (anchor.get("consumption_mode") or "first_frame") if consumes_timeline_frames else "text_prompt_with_references",
            "native_timeline_frames": timeline_frame_count or int(frame_control.get("max_timeline_frames") or 1),
            "requires_split_relay": bool(anchor.get("requires_split_relay")),
            "reference_only": bool(anchor.get("reference_only")),
        },
        "reference_inputs": {
            "characters": character_refs,
            "assets": clip_asset_refs(clip),
            "max_reference_images": max_reference_images,
            "motion_reference": {
                "allowed": bool(motion_ref.get("applicable")),
                "library_path": "生产数据/motion_reference_library.json",
                "policy": "use same sequence/shot_type approved reference when available" if motion_ref.get("applicable") else "not_supported_or_not_needed",
            },
        },
        "control_inputs": {
            "manifest_path": motion.get("manifest_path") or "",
            "required": bool(motion.get("required")),
            "required_inputs": list(motion.get("required_inputs") or []),
            "gate_policy": motion.get("gate_policy") or "not_required",
        },
        "audio_inputs": {
            "video_generation_audio_policy": entry.get("video_generation_audio_policy") or "无声视频流",
            "native_audio_policy": entry.get("native_audio_policy"),
            "speech_policy": "native_speech" if entry.get("native_audio_policy") == "native_speech" else "no_native_speech",
            "requires_voice_track": bool(entry.get("requires_voice_fallback")),
            "fallback_production_mode": entry.get("fallback_production_mode") or "",
            "audio_strategy": entry.get("audio_strategy") or "",
            "timing_basis": entry.get("timing_basis") or "",
            "performance_track_status": entry.get("performance_track_status") or "",
            "performance_audio_paths": list(entry.get("performance_audio_paths") or []),
            "requires_performance_audio_before_final": bool(entry.get("requires_performance_audio_before_final")),
            "post_lipsync_required": bool(entry.get("post_lipsync_required")),
            "base_video_only": bool(entry.get("base_video_only")),
            "base_video_mouth_policy": entry.get("base_video_mouth_policy") or "route_default",
        },
        "fallback": {
            "fallback_backends": list(entry.get("fallback_backends") or []),
            "degrade_plan": entry.get("degrade_plan"),
        },
        "capability_match": {
            "frame_contract_supported": "frame_contract_unsupported" not in set(entry.get("risk_flags") or []),
            "motion_reference_supported": bool(motion_ref.get("applicable")),
            "motion_control_level": motion.get("backend_control_level") or "unknown",
        },
    }
    segment_relay = entry.get("duration_segment_relay")
    if isinstance(segment_relay, Mapping) and segment_relay.get("supported"):
        recipe["video_segments"] = {
            "required": True,
            "mode": "first_last_relay",
            "reason": segment_relay.get("reason"),
            "max_clip_seconds": segment_relay.get("max_clip_seconds"),
            "max_segment_seconds": segment_relay.get("max_segment_seconds"),
            "segments": list(segment_relay.get("segments") or []),
        }
    plan = entry.get("identity_preservation_plan")
    if isinstance(plan, Mapping) and plan:
        recipe["reference_inputs"]["identity_preservation_plan"] = dict(plan)
    recipe["post_video_qc"] = post_video_qc_plan(entry, clip)
    return recipe


def _identity_qc_required(entry: Mapping[str, Any]) -> bool:
    identity = str(entry.get("identity_requirement") or "").strip().lower()
    if identity in {"", "none", "not_needed", "not_required", "no", "无"}:
        return False
    chars = entry.get("clip_characters")
    return isinstance(chars, list) and any(isinstance(c, Mapping) and (c.get("character_id") or c.get("raw")) for c in chars)


def _clip_identity_risk_text(entry: Mapping[str, Any], clip: Mapping[str, Any]) -> str:
    parts: List[str] = [
        str(entry.get("shot_type") or ""),
        str(entry.get("template") or ""),
        str(clip.get("template") or ""),
        str(clip.get("scene") or ""),
        str(clip.get("label") or ""),
        str(clip.get("desc") or ""),
    ]
    for shot in clip.get("shots") or []:
        if not isinstance(shot, Mapping):
            continue
        parts.extend(str(shot.get(k) or "") for k in ("lens", "desc", "action", "camera", "shot_size"))
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    parts.extend(str(cont.get(k) or "") for k in ("expression_span", "start_state", "end_state", "action"))
    return " ".join(parts).lower()


def _dense_face_watch_required(entry: Mapping[str, Any], clip: Mapping[str, Any]) -> bool:
    if not _identity_qc_required(entry):
        return False
    flags = {str(x).strip() for x in (entry.get("risk_flags") or []) if str(x).strip()}
    shot_type = str(entry.get("shot_type") or "").strip()
    text = _clip_identity_risk_text(entry, clip)
    closeup_tokens = (
        "cu", "mcu", "closeup", "close-up", "dialogue_closeup", "dialogue_shot_reverse",
        "shot_reverse", "近景", "特写", "反打", "脸", "表情", "五官", "正脸", "说话",
    )
    return (
        shot_type in {"dialogue_closeup", "dialogue_shot_reverse", "reveal_reaction_chain", "relationship_turn", "public_confrontation"}
        or bool(flags & {"identity_drift_risk", "mouth_visible", "face_contact_risk", "multi_person", "character_backend_conflict", "identity_escalated"})
        or any(token in text for token in closeup_tokens)
    )


def post_video_qc_plan(entry: Mapping[str, Any], clip: Mapping[str, Any]) -> Dict[str, Any]:
    """Machine-readable post-generation identity QC contract.

    Route-level consistency work is only useful if the accept/review layers know
    which clips require dense identity evidence.  This block is consumed by the
    prompt pack, gate and video runner; it is deliberately policy-based, not a
    backend-specific instruction string.
    """
    identity_required = _identity_qc_required(entry)
    dense = _dense_face_watch_required(entry, clip)
    reports = ["video_qc"]
    if identity_required:
        reports.append("temporal_consistency")
    if dense:
        reports.append("video_face_drift_watch")
    return {
        "identity_qc_required": identity_required,
        "dense_face_watch_required": dense,
        "required_reports": reports,
        "sample_policy": (
            "start/mid/end machine QC plus dense human frame review on clear-face windows"
            if dense else "standard start/mid/end machine QC; escalate to dense frame review if reviewer sees face drift"
        ),
        "acceptance_policy": (
            "block_clear_wrong_closeup_face; block_dense_warn_until_human_review; "
            "no VLM/signoff override for true face drift"
        ),
        "return_to_stage": "video_or_image_then_compose",
    }


def action_choreography_contract(shot_type: str) -> Dict[str, Any]:
    """高动量镜头的动作编排契约。纯函数·可测；普通镜返回 required=False。"""
    if shot_type not in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        return {"required": False}

    specific = ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS[shot_type]
    required_fields = ACTION_CHOREOGRAPHY_COMMON_FIELDS + specific
    if shot_type == "fight_exchange":
        notes = [
            "one attack intention per clip; write setup -> attack -> impact -> reaction -> recovery",
            "impact/contact must have contact point, force direction, readable hit frame, and recovery beat",
            "premium fields keyframe_plan/post_cue_points/physics_guard must map hit-stop, SFX peak, and limb/weapon ownership",
        ]
        failure_modes = ["unclear_hit", "wrong_force_direction", "limb_fusion", "weapon_contact_drift", "extra_unplanned_hits"]
        beat_model = "setup_attack_impact_reaction_recovery"
    elif shot_type == "magic_burst":
        notes = [
            "lock effect_asset/vfx_asset shape, color, source point, energy_path, and collision/apex frame",
            "write charge -> release -> collision/apex -> aftermath; one power result per clip",
            "premium fields keyframe_plan/post_cue_points/physics_guard must map flash, impact boom, aftershock, and VFX shape guard",
        ]
        failure_modes = ["vfx_shape_drift", "energy_path_flip", "collision_point_lost", "unreadable_apex", "new_unplanned_spell"]
        beat_model = "charge_release_collision_aftermath"
    elif shot_type == "chase":
        notes = [
            "keep one screen direction; distance curve may close OR open, not both in one clip",
            "sell speed with parallax layers, foreground occluders, cloth, hair, and camera tracking",
        ]
        failure_modes = ["screen_direction_flip", "distance_curve_reset", "pose_drift", "background_stickiness", "teleporting"]
        beat_model = "direction_distance_obstacle_result"
    elif shot_type == "flight":
        notes = [
            "lock rider/body pose and move cloud/mountain/parallax layers; only maneuver shots may change pose",
            "write altitude curve and mount/cloud lock so sword/cloud shape does not morph",
        ]
        failure_modes = ["pose_drift", "altitude_curve_drift", "mount_shape_drift", "background_stickiness", "camera_float"]
        beat_model = "takeoff_cruise_maneuver_arrival"
    elif shot_type == "mount_ride":
        notes = [
            "lock rider/mount contact points, saddle or harness shape, and one gait cycle",
            "sell speed with dust, grass, mane, cloth, foreground occlusion, and side-tracking camera",
        ]
        failure_modes = ["rider_mount_contact_drift", "gait_cycle_reset", "pose_drift", "harness_morph", "background_stickiness"]
        beat_model = "mount_establish_gait_turn_arrival"
    elif shot_type == "vehicle_ride":
        notes = [
            "lock carriage or vehicle silhouette, wheel count/position, and harness connection",
            "sell motion with wheel rotation, hoof/road feedback, dust, curtains, and parallax layers",
        ]
        failure_modes = ["vehicle_shape_drift", "wheel_count_or_rotation_error", "harness_morph", "direction_flip", "background_stickiness"]
        beat_model = "vehicle_establish_rolling_stop"
    elif shot_type == "vessel_flight":
        notes = [
            "lock flying vessel silhouette, flight path, altitude curve, and screen direction",
            "keep vessel pose stable; use clouds, mountains, light trails, and parallax layers for speed",
        ]
        failure_modes = ["vessel_shape_drift", "altitude_curve_drift", "direction_flip", "scale_jump", "background_stickiness"]
        beat_model = "vessel_enter_cruise_maneuver_arrival"
    elif shot_type == "road_vehicle":
        notes = [
            "lock car/bus/motorcycle shape, wheel rotation, driver controls, lane position, and traffic flow",
            "sell speed with road markings, street lights, traffic parallax, tire motion, and restrained camera tracking",
        ]
        failure_modes = ["vehicle_shape_drift", "wheel_rotation_error", "lane_drift", "traffic_flow_reset", "direction_flip"]
        beat_model = "vehicle_establish_traffic_brake"
    elif shot_type == "stealth_stalk":
        notes = [
            "lock screen direction, distance curve, occlusion layers, light/shadow source, and a single reveal-or-hide beat",
            "suspense comes from controlled partial visibility; avoid turning stealth into a freeform chase inside one clip",
        ]
        failure_modes = ["screen_direction_flip", "distance_curve_reset", "occlusion_layer_jump", "light_shadow_flicker", "target_teleport"]
        beat_model = "hide_establish_shadow_approach_reveal_or_hide"
    else:
        notes = ["write beats, path, camera movement, readability holds, and a concrete degrade plan"]
        failure_modes = ["path_drift", "pose_drift", "readability_loss"]
        beat_model = "structured_action_beats"

    return {
        "required": True,
        "shot_type": shot_type,
        "beat_model": beat_model,
        "required_fields": required_fields,
        "gate_policy": "block_prompt_without_action_choreography_contract",
        "failure_modes": failure_modes,
        "notes": notes,
    }


BACKEND_CONSISTENCY_SCOPE = {
    "image_generation": "single_model_channel_per_project",
    "video_generation": "per_clip_allowed_with_baseline",
    "required_guards": [
        "model_routes_baseline",
        "identity_handoff",
        "execution_recipe",
        "post_video_qc",
    ],
}


def backend_consistency_scope() -> Dict[str, Any]:
    return {
        "image_generation": BACKEND_CONSISTENCY_SCOPE["image_generation"],
        "video_generation": BACKEND_CONSISTENCY_SCOPE["video_generation"],
        "required_guards": list(BACKEND_CONSISTENCY_SCOPE["required_guards"]),
    }


def duration_safe_fallbacks(
    primary: str,
    fallbacks: Iterable[str],
    clip_seconds: float,
    *,
    native_audio_policy: str = "",
    anchor_contract: Optional[Mapping[str, Any]] = None,
    video_channel: str = "",
) -> List[str]:
    """Keep only automatic fallbacks that can cover this clip duration."""
    needs_native_av = str(native_audio_policy or "").strip().lower() == "native_speech"
    preferred = NATIVE_AV_BACKENDS if needs_native_av else ("seedance", "dreamina", "kling", "veo")
    out: List[str] = []
    for candidate in [*list(fallbacks or []), *preferred]:
        backend = normalize_backend(str(candidate or ""), default="")
        if not backend or backend == primary or backend in out:
            continue
        if not video_backend_auto_routable(backend):
            continue
        if not _backend_paid_routing_allowed(backend, video_channel):
            continue
        if needs_native_av and backend not in NATIVE_AV_BACKENDS:
            continue
        if clip_seconds > 0 and video_backend_max_seconds(backend) < clip_seconds:
            continue
        if not fallback_frame_contract_ok(backend, video_channel, anchor_contract):
            continue
        out.append(backend)
        if len(out) >= 3:
            break
    if not out:
        primary_norm = normalize_backend(str(primary or ""), default="")
        if (
            video_backend_auto_routable(primary_norm)
            and _backend_paid_routing_allowed(primary_norm, video_channel)
            and (not needs_native_av or primary_norm in NATIVE_AV_BACKENDS)
            and (clip_seconds <= 0 or video_backend_max_seconds(primary_norm) >= clip_seconds)
            and fallback_frame_contract_ok(primary_norm, video_channel, anchor_contract)
        ):
            out.append(primary_norm)
    return out


def fallback_frame_contract_ok(
    backend: str,
    video_channel: str,
    anchor_contract: Optional[Mapping[str, Any]],
) -> bool:
    if not isinstance(anchor_contract, Mapping):
        return True
    anchor_count = int(anchor_contract.get("anchor_count") or 0)
    need_end = bool(anchor_contract.get("need_end") or anchor_contract.get("consumes_endframe"))
    if not anchor_count and not need_end:
        return True
    frame = video_backend_frame_control(backend, video_channel)
    if need_end and not frame.get("supports_last_frame"):
        return False
    if str(anchor_contract.get("consumption_mode") or "") == "native_multiframe":
        if anchor_count and not frame.get("supports_native_mid_anchors"):
            return False
        needed_frames = 1 + anchor_count + (1 if need_end else 0)
        if int(frame.get("max_timeline_frames") or 1) < needed_frames:
            return False
    return True


def needs_identity_preservation_plan(entry: Mapping[str, Any]) -> bool:
    identity = str(entry.get("identity_requirement") or "").strip().lower()
    if identity in {"", "none", "not_needed"}:
        return False
    shot_type = str(entry.get("shot_type") or "").strip()
    flags = {str(x).strip() for x in (entry.get("risk_flags") or []) if str(x).strip()}
    motion = entry.get("motion_control") if isinstance(entry.get("motion_control"), Mapping) else {}
    return (
        shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES
        or shot_type in MOTION_CONTROL_REQUIRED_SHOT_TYPES
        or bool(flags & set(MOTION_CONTROL_RISK_FLAGS))
        or bool(flags & {"high_action", "spectacle", "contact_motion", "fast_motion", "physics"})
        or motion.get("required") is True
    )


def identity_preservation_plan(entry: Mapping[str, Any]) -> Dict[str, Any]:
    shot_type = str(entry.get("shot_type") or "general_motion")
    anchor = entry.get("anchor_consumption") if isinstance(entry.get("anchor_consumption"), Mapping) else {}
    frame_truth = (
        "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"
        if anchor.get("need_end")
        else "keep first frame and registered reference group as identity truth when motion control needs simpler movement"
    )
    return {
        "required_identity_anchors": [
            "face_shape",
            "hairstyle",
            "age_read",
            "outfit_palette",
            "named_character_screen_slot",
        ],
        "reference_strategy": str(entry.get("identity_requirement") or "reference_group"),
        "motion_readability_allowances": [
            "prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups",
            "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot",
            frame_truth,
        ],
        "fallback_plan": (
            "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; "
            "do not silently swap backend or drop the story beat."
        ),
        "applies_to": shot_type,
    }


# ── QC 失败 → 路由自动升锁（E4·闭环）────────────────────────────────────────
# 静态路由的盲点：某镜 identity 反复崩脸/错脸，下次重跑还路由到同一个没原生身份锁的后端，白烧。
# 这里把「该镜 identity 已失败 N 次」回灌进路由：≥阈值就升锁——要求原生身份锁、把 primary 换成
# 有 Character ID/Face Lock 的后端（固定后端模式只收紧 requirement+提示，不擅自换厂）。失败计数来源
# 是 production_events.jsonl 的 redraw/qa_gate 事件（见 load_identity_failure_counts），按 clip 聚合。
IDENTITY_LOCK_CAPS = {"character_id", "face_lock"}
IDENTITY_FAILURE_THRESHOLD = 2


def backend_has_native_identity(backend: str) -> bool:
    """该后端是否有原生身份锁（Character ID / Face Lock）。纯函数·可测。"""
    caps = BACKEND_MOTION_CONTROL.get(normalize_backend(backend), {}).get("capabilities", [])
    return bool(IDENTITY_LOCK_CAPS.intersection(caps))


def escalate_identity_for_failures(route_entry: Dict[str, Any], failure_count: int, *,
                                   fixed_mode: bool = False,
                                   threshold: int = IDENTITY_FAILURE_THRESHOLD) -> Dict[str, Any]:
    """E4：本镜 identity 反复失败 → 自动升锁。纯函数·可测。failure_count<threshold 原样返回。

    升锁：identity_requirement=native_identity_lock_required + risk_flag `identity_escalated`；
    primary 无原生身份锁时换成有的后端（固定后端模式不换厂，只收紧 requirement + 提示补 ref/拆镜）。"""
    if failure_count < threshold:
        return route_entry
    entry = dict(route_entry)
    primary = entry.get("primary_backend")
    entry["identity_requirement"] = "native_identity_lock_required"
    entry["risk_flags"] = sorted(set(entry.get("risk_flags", [])) | {"identity_escalated"})
    rationale = list(entry.get("rationale", []))
    if backend_has_native_identity(primary):
        rationale.append(
            f"⚠️本镜 identity 已失败 {failure_count} 次：primary「{primary}」已具原生身份锁，"
            "强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。")
    elif fixed_mode:
        rationale.append(
            f"⚠️本镜 identity 已失败 {failure_count} 次，但视频模型路由=固定后端「{primary}」(无原生身份锁)："
            "不擅自换厂，强烈建议手动改用 Kling(Character ID)/Seedance(Face Lock) 或补 reference_group / 上 LoRA / 拆镜。")
    else:
        better = next((b for b in (entry.get("fallback_backends") or []) + ["kling", "seedance"]
                       if backend_has_native_identity(b)), None)
        if better and better != primary:
            fbs = [primary] + [b for b in entry.get("fallback_backends", []) if b != better]
            entry["primary_backend"] = better
            entry["fallback_backends"] = fbs[:3]
            entry["max_clip_seconds"] = video_backend_max_seconds(better)
            rationale.append(
                f"⚠️本镜 identity 已失败 {failure_count} 次：primary「{primary}」无原生身份锁，"
                f"升锁改用「{better}」(Character ID/Face Lock) 把脸钉死后再生成。")
        else:
            rationale.append(
                f"⚠️本镜 identity 已失败 {failure_count} 次且无原生身份锁后端可用：补 reference_group 角度 / 上 LoRA / 拆镜降难度。")
    # 升锁后把最终 primary 钉成 locked_backend：重试/重跑须复用它，不得再轮换 fallback 后端
    # （否则换脸-换后端-再换脸永不收敛）。固定后端模式不换厂时 locked_backend 即原 primary。
    entry["locked_backend"] = entry.get("primary_backend")
    entry["rationale"] = rationale
    return entry


IDENTITY_FAIL_MARKERS = ("脸", "崩脸", "身份", "identity", "face", "角色一致", "character_consistency", "错脸", "换脸")
_CLIP_ID_RE = re.compile(r"(?:Clip[_]?|镜头)(\d+)", re.I)


def _clip_id_from_text(text: str) -> Optional[str]:
    m = _CLIP_ID_RE.search(str(text or ""))
    return f"Clip_{int(m.group(1)):02d}" if m else None


def _is_identity_failure(text: str) -> bool:
    low = str(text or "").lower()
    return any(m.lower() in low for m in IDENTITY_FAIL_MARKERS)


def load_identity_failure_counts(root: Path, episode: str) -> Dict[str, int]:
    """读 production_events.jsonl，按 clip 聚合**本集 identity 失败次数**（E4 升锁输入）。

    失败信号：① redraw 事件 status=fail 且原因/资产命中身份关键词；② qa_gate 事件 severity=block
    且 dim/维度命中身份关键词。只统计能解析出 Clip 号的（定妆共享库等无 clip 的略过）。缺文件→{}。"""
    path = Path(root) / "生产数据" / "production_events.jsonl"
    counts: Dict[str, int] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return counts
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if str(ev.get("episode") or "") not in ("", episode):
            continue
        clip_id = reason = None
        if ev.get("event") == "redraw":
            gen = ev.get("generation") or {}
            if str(gen.get("status") or "") != "fail":
                continue
            reason = f"{gen.get('redraw_reason','')} {gen.get('asset','')}"
            clip_id = _clip_id_from_text(gen.get("asset", "")) or _clip_id_from_text(gen.get("redraw_reason", ""))
        elif ev.get("event") in ("qa_gate", "qa_gate_run"):
            qa = ev.get("qa") or ev.get("qa_gate") or {}
            if str(qa.get("severity") or "") != "block":
                continue
            reason = f"{qa.get('dim','')} {qa.get('dimension','')} {qa.get('msg','')} {qa.get('loc','')}"
            clip_id = _clip_id_from_text(qa.get("loc", "")) or _clip_id_from_text(qa.get("msg", ""))
        if clip_id and reason and _is_identity_failure(reason):
            counts[clip_id] = counts.get(clip_id, 0) + 1
    return counts


def _route_fixed(
    clip: Mapping[str, Any],
    shot_type: str,
    default_backend: str,
    fallback_backends: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if fallback_backends is None:
        fallback = [b for b in ("seedance", "kling", "dreamina") if b != default_backend]
    else:
        fallback = [b for b in fallback_backends if b != default_backend]
    degrade_plan = (
        "If the fixed backend fails twice, switch 视频模型路由 to auto and reroute the affected clip."
        if fallback
        else "If the fixed backend fails twice, pause and ask before enabling another video backend or manually rerouting this clip."
    )
    return {
        "primary_backend": default_backend,
        "fallback_backends": fallback[:2],
        "mode": "image2video" if shot_type != "empty_establishing" else "text2video",
        "native_audio_policy": "none",
        "identity_requirement": "reference_group" if clip_has_named_characters(clip) else "none",
        "rationale": [f"routing_mode=fixed_default, use project 生视频模型={default_backend} for this clip"],
        "prompt_requirements": ["write model routing field even in fixed mode", "keep fallback/degrade plan explicit"],
        "degrade_plan": degrade_plan,
    }


def _is_speech_shot(clip: Mapping[str, Any], shot_type: str) -> bool:
    """说话/对白镜：对话反打、说话特写，或 mouth_visible 的镜头。"""
    return shot_type in SPEECH_SHOT_TYPES or clip_has_mouth_visible(clip)


def _clip_has_character_dialogue(clip: Mapping[str, Any]) -> bool:
    """Storyboard-level machine truth for visible character dialogue.

    `voiceover_indices` may include narration; native_speech must only be
    selected when the clip has character dialogue that the video backend may
    actually generate.
    """
    for key in ("dialogue_indices", "allowed_character_dialogue_indices"):
        raw = clip.get(key)
        if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes, bytearray)):
            if any(str(item).strip() for item in raw):
                return True
    raw_dialogue = clip.get("allowed_character_dialogue")
    if isinstance(raw_dialogue, Iterable) and not isinstance(raw_dialogue, (str, bytes, bytearray)):
        if any(bool(item) for item in raw_dialogue):
            return True
    raw_text = clip.get("dialogue")
    return isinstance(raw_text, str) and bool(raw_text.strip())


def _lipsync_enabled(lip_sync_setting: str) -> bool:
    """`_设置.md 对口型` 是否 opt-in（非「关闭」即视为启用）。"""
    return str(lip_sync_setting).strip().lower() not in LIPSYNC_OFF_VALUES


def _lipsync_dialogue_closeup_default(lip_sync_setting: str) -> bool:
    """是否为「对话近景」兼容档（仅对话近景说话镜启用口型）。"""
    return str(lip_sync_setting or "").strip().lower() in LIPSYNC_DIALOGUE_CLOSEUP_DEFAULT_VALUES


def _is_dialogue_closeup(clip: Mapping[str, Any], shot_type: str) -> bool:
    """对话近景说话镜：对话反打/说话特写 shot_type，或 mouth_visible（口型可见）。
    比 _is_speech_shot 窄——不含 reveal_reaction_chain/public_confrontation/relationship_turn 等
    非近景说话镜，使「对话近景」兼容档的口型成本有界。"""
    return shot_type in ("dialogue_shot_reverse", "dialogue_closeup") or clip_has_mouth_visible(clip)


def _lipsync_active(lip_sync_setting: str, clip: Mapping[str, Any], shot_type: str) -> bool:
    """该镜是否启用「配音对齐」口型路由（统一三档语义，供 voice_conditioned 路由闸用）：
    - 显式关闭/空 → 否。
    - 对话近景兼容档 → 仅对话近景说话镜启用，其余说话镜不进口型路由。
    - 显式开启（配音对齐/后期pass/平台原生…）→ 所有说话镜启用（旧 opt-in 行为）。"""
    if str(lip_sync_setting or "").strip().lower() in LIPSYNC_OFF_VALUES:
        return False
    if _lipsync_dialogue_closeup_default(lip_sync_setting):
        return _is_dialogue_closeup(clip, shot_type)
    return _is_speech_shot(clip, shot_type)


def _route_voice_conditioned_lipsync(
    clip: Mapping[str, Any], shot_type: str, default_backend: str, *, overseas: bool = False
) -> Dict[str, Any]:
    """voice_first + 对口型 opt-in 的说话镜路由：把克隆配音 line_NN.wav 当口型条件喂进
    支持音频参考的后端（Seedance 2.0 音素级 / 可灵 Omni），同帧出对口型画面。

    与 native_av 的根本区别：音轨仍是 voice-first 的克隆音色（compose 用配音轨），模型音频
    只作 lip 条件、不接管声音——既不双人声，又省一道后期 MuseTalk/Wav2Lip 对口型 pass。
    """
    primary = default_backend if default_backend in LIPSYNC_AUDIO_REF_BACKENDS else "seedance"
    rationale = [
        "voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面",
        "音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass",
    ]
    if overseas and not video_backend_supports_multilingual_lipsync(primary):
        ml = preferred_multilingual_lipsync_backend()
        if ml:
            primary = ml
            rationale.append(
                "出海(目标语言≠中文)：抢占多语言唇同步最强后端做对口型，避免非中文台词口型/口音错配（2026 出海增量）")
    fallback = [b for b in ("kling", "seedance", "veo") if b != primary]
    return {
        "primary_backend": primary,
        "fallback_backends": fallback,
        "mode": "voice_conditioned_lipsync",
        "native_audio_policy": "lipsync_condition_only",
        "identity_requirement": "character_id_or_reference_group" if clip_has_named_characters(clip) else "none",
        "rationale": rationale,
        "prompt_requirements": [
            "把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声",
            "speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）",
        ],
        "degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。",
    }


def _route_native_av_speech(clip: Mapping[str, Any], shot_type: str, default_backend: str,
                            *, overseas: bool = False) -> Dict[str, Any]:
    """原生音画模式下的说话镜路由：一次出同步音画（台词+口型+环境声），绕过配音先行。

    用原生音画能力最强的当前后端做 primary（Seedance 2.0 / Veo 3.1；Sora 仅旧项目/manual），台词文本与情绪由
    脚本提供、镜头时长由脚本规划驱动（不读配音先行的时长清单）。失败回退配音先行链路。
    """
    native_primary = default_backend if default_backend in NATIVE_AV_BACKENDS else "seedance"
    rationale = [
        "制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工",
        "台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音",
    ]
    # 出海(目标语言≠中文)：原生说话镜须由多语言唇同步最强后端出非中文台词，否则口型/口音错配。
    if overseas and not video_backend_supports_multilingual_lipsync(native_primary):
        ml = preferred_multilingual_lipsync_backend()
        if ml and ml in NATIVE_AV_BACKENDS:
            native_primary = ml
            rationale.append("出海(目标语言≠中文)：抢占多语言原生唇同步最强后端出非中文台词（2026 出海增量）")
    fallback = [b for b in ("veo", "seedance") if b != native_primary]
    return {
        "primary_backend": native_primary,
        "fallback_backends": fallback,
        "mode": "native_av",
        "native_audio_policy": "native_speech",
        "identity_requirement": "character_id_or_reference_group" if clip_has_named_characters(clip) else "none",
        "rationale": rationale,
        "prompt_requirements": [
            "提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声",
            "speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）",
        ],
        "degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。",
    }


def _route_narrative_state_scene(
    clip: Mapping[str, Any],
    shot_type: str,
    default_backend: str,
    *,
    native_audio_setting: str,
    lip_sync_setting: str,
    av_mode: str,
) -> Dict[str, Any]:
    """真相/对质/关系转折镜头：优先身份、表情和叙事状态一致性，而非普通说话镜快捷路由。"""
    primary = "kling"
    fallback = ["veo", "seedance"] if _lipsync_enabled(lip_sync_setting) or "保留" in native_audio_setting else ["seedance", default_backend]
    template_notes = {
        "reveal_reaction_chain": (
            "reveal scenes are identity- and reaction-chain-sensitive",
            "lock reveal_object, knowledge_order, reaction_beats, and cut_point from template_contract",
            "Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.",
        ),
        "public_confrontation": (
            "confrontations need stable speaker focus, evidence ladder, and crowd hierarchy",
            "lock stakes, evidence_ladder, power_shift, and crowd_reaction_order from template_contract",
            "Split into evidence insert, speaker OTS, judge/witness reaction, and crowd cutaway if staging drifts.",
        ),
        "relationship_turn": (
            "relationship turns depend on micro-expression, eyeline, and precise before/after state",
            "lock relationship_state_before, turning_action, subtext, and relationship_state_after from template_contract",
            "Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.",
        ),
    }[shot_type]
    rationale = [
        template_notes[0],
        "these shots carry irreversible story state changes, so visual identity, eyeline, and reaction order outrank generic speech routing",
    ]
    prompt_requirements = [
        "mark mouth_visible when faces speak; speech_policy=no_native_speech unless this clip is explicitly rerouted to a native AV backend",
        template_notes[1],
    ]
    if av_mode == "native_av":
        rationale.append("制作模式=原生音画，但本专项模板优先锁身份/表情/反应链；若必须原生人声，拆成说话特写或手动改用 native AV fallback。")
        rationale.append("本镜未声明 native_speech 时必须补 voice-first 配音轨；不能让原生音画项目出现无声对白/反应链。")
        prompt_requirements.append("native_av_project_note=visual_consistency_first_for_narrative_state_scene")
        prompt_requirements.append("requires_voice_fallback=true；若本镜有台词/画内说话，先补 n2d-voice，再以 no_native_speech 出视频")
    out = {
        "primary_backend": primary,
        "fallback_backends": [b for b in fallback if b != primary],
        "mode": "image2video",
        "native_audio_policy": "none",
        "identity_requirement": "character_id_or_reference_group",
        "rationale": rationale,
        "prompt_requirements": prompt_requirements,
        "degrade_plan": template_notes[2],
    }
    if av_mode == "native_av":
        out["requires_voice_fallback"] = True
        out["fallback_production_mode"] = "voice_first"
        out["native_av_override_reason"] = "narrative_state_identity_priority"
        out["degrade_plan"] = (
            template_notes[2]
            + "；若本镜含对白/画内发声，必须走 voice-first 配音补偿链路，或拆出 native_speech 说话特写后重跑路由。"
        )
    return out


def choose_route(
    clip: Mapping[str, Any],
    shot_type: str,
    *,
    default_backend: str = "dreamina",
    routing_mode: str = "auto",
    native_audio_setting: str = "丢弃",
    lip_sync_setting: str = "关闭",
    av_mode: str = "voice_first",
    fixed_fallback_backends: Optional[List[str]] = None,
    t2v_action: bool = False,
    overseas: bool = False,
) -> Dict[str, Any]:
    if routing_mode == "fixed_default":
        route = _route_fixed(clip, shot_type, default_backend, fixed_fallback_backends)
        if av_mode == "native_av" and _is_speech_shot(clip, shot_type):
            route["rationale"].append("制作模式=原生音画，但视频模型路由=固定生视频模型；固定选择优先，不自动切 native_speech 后端")
            route["rationale"].append("本镜已降级为配音先行补偿链路：必须先补 n2d-voice 真配音，再生成静音/无原生人声视频，避免无声对白镜。")
            route["prompt_requirements"].append("speech_policy=no_native_speech；requires_voice_fallback=true；先补本镜 voice-first 配音轨，再出视频")
            route["requires_voice_fallback"] = True
            route["fallback_production_mode"] = "voice_first"
            route["native_av_override_reason"] = "fixed_default_backend_without_native_speech"
            route["degrade_plan"] = (
                "制作模式=原生音画但固定后端未走 native_speech：本镜必须回退配音先行，"
                "先由 n2d-voice 产出真实配音/时长清单，再以 no_native_speech 生成视频；"
                "若要保持原生音画，请关闭固定模式或改用支持 native_speech 的固定后端。"
            )
        return route

    # 原生音画模式：说话镜优先走原生同步音画路由（绕过配音先行）。其余镜头走常规路由。
    if av_mode == "native_av" and _is_speech_shot(clip, shot_type) and (
        shot_type not in NARRATIVE_STATE_SHOT_TYPES or _clip_has_character_dialogue(clip)
    ):
        route = _route_native_av_speech(clip, shot_type, default_backend, overseas=overseas)
        fallbacks: List[str] = []
        for backend in route["fallback_backends"] + [default_backend]:
            backend = normalize_backend(backend)
            if backend != route["primary_backend"] and backend not in fallbacks:
                fallbacks.append(backend)
        route["fallback_backends"] = fallbacks[:3]
        return route

    if shot_type in NARRATIVE_STATE_SHOT_TYPES:
        return _route_narrative_state_scene(
            clip,
            shot_type,
            default_backend,
            native_audio_setting=native_audio_setting,
            lip_sync_setting=lip_sync_setting,
            av_mode=av_mode,
        )
    # voice_first + 对口型 opt-in 的说话镜：克隆配音作口型条件喂进支持音频参考的后端，
    # 同帧出对口型画面（不双人声、省后期对口型 pass）。固定后端模式不抢路由。
    if (
        av_mode == "voice_first"
        and routing_mode != "fixed_default"
        and _lipsync_active(lip_sync_setting, clip, shot_type)
    ):
        route = _route_voice_conditioned_lipsync(clip, shot_type, default_backend, overseas=overseas)
        fallbacks = []
        for backend in route["fallback_backends"] + [default_backend]:
            backend = normalize_backend(backend)
            if backend != route["primary_backend"] and backend not in fallbacks:
                fallbacks.append(backend)
        route["fallback_backends"] = fallbacks[:3]
        return route
    t2v_plan = clip_t2v_identity_reference_plan(clip)
    has_named_characters = clip_has_named_characters(clip)
    t2v_allowed = bool(t2v_action and (not has_named_characters or t2v_plan))
    if shot_type == "fight_exchange":
        mode = "text2video" if t2v_allowed else "frames2video"
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": mode,
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group" if has_named_characters else "none",
            "rationale": [
                f"fight/contact motion benefits from {'experimental T2V physics engine' if t2v_allowed else 'first/last frame control'}",
                "impact beats need short controllable motion rather than free choreography",
            ],
            "prompt_requirements": [
                "write detailed action kinetics with reference_inputs and identity anchors" if t2v_allowed else "write first frame and end frame as hard constraints",
                "one contact action per clip; avoid multi-hit choreography",
                "fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, attack_path, impact_frame, contact_points, force_direction, recovery_beat",
            ],
            "degrade_plan": "Split into setup and impact clips; keep the hit frame as the end frame.",
        }
    elif shot_type in ("chase", "flight", "mount_ride", "vehicle_ride", "vessel_flight", "road_vehicle", "stealth_stalk"):
        mode = "text2video" if t2v_allowed else "image2video"
        route = {
            "primary_backend": "seedance",
            "fallback_backends": ["kling", default_backend],
            "mode": mode,
            "native_audio_policy": "none",
            "identity_requirement": "face_lock_or_reference_group" if has_named_characters else "none",
            "rationale": [
                f"long continuous motion and moving backgrounds benefit from {'experimental T2V unconstrained physics' if t2v_allowed else 'longer single-shot generation'}",
                "flight/chase/mount/vehicle/vessel/road/stealth shots should lock subject shape and put speed or suspense into background, parallax, gait, wheels, traffic, light, or occlusion layers",
            ],
            "prompt_requirements": [
                "keep body pose stable; put speed into background, foreground occluders, cloth and camera tracking",
                "avoid large limb changes unless there is an end frame",
                "fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, parallax_layers and route-specific chase/flight/mount/vehicle/vessel/road/stealth fields",
            ],
            "degrade_plan": "Cut to front/back reaction shots or split into approach, pass-by, and exit clips.",
        }
    elif shot_type == "screen_insert":
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "image2video",
            "native_audio_policy": "none",
            "identity_requirement": "reference_group" if has_named_characters else "none",
            "rationale": [
                "screen inserts are text/readability sensitive; keep device and hand motion low and move readable content to overlay",
                "image2video preserves a designed phone/computer/CCTV plate better than free text generation",
            ],
            "prompt_requirements": [
                "use text_layer=overlay; video model must not render readable UI text, numbers, chat logs, codes, or timestamps",
                "lock device_lock, screen_content_ref, reflection_policy, and hand_pose_lock; only allow small finger, glare, notification, or camera drift",
            ],
            "degrade_plan": "Use a static screen keyframe plus compose overlay; cut to hand/reaction if device motion or text legibility fails.",
        }
    elif shot_type == "evidence_search":
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "image2video",
            "native_audio_policy": "none",
            "identity_requirement": "face_lock_or_reference_group" if has_named_characters else "none",
            "rationale": [
                "evidence search is object-continuity sensitive and benefits from first/end frame constraints",
                "one clue reveal per clip keeps the evidence chain readable and prevents the model inventing new props",
            ],
            "prompt_requirements": [
                "lock clue_object, search_path, reveal_frame, evidence_chain, hand_pose_lock, occlusion_order, and contamination_guard",
                "one clue reveal per clip; avoid combining search, reveal, chase, and fight in the same generation",
            ],
            "degrade_plan": "Split into search hand insert, clue reveal close-up, and evidence-chain reaction or bagging shot.",
        }
    elif shot_type in ("tribulation_breakthrough", "array_ritual", "realm_portal", "contract_summon"):
        route = {
            "primary_backend": "seedance",
            "fallback_backends": ["kling", "veo", default_backend],
            "mode": "image2video",
            "native_audio_policy": "native_sfx" if "低音量" in native_audio_setting else "none",
            "identity_requirement": "face_lock_or_reference_group" if has_named_characters else "none",
            "rationale": [
                "high-energy genre spectacle needs stable VFX/asset locks and controlled progression rather than freeform effects",
                "image2video preserves the keyed lightning/array/portal/summon plate while letting light, particles, and camera move",
            ],
            "prompt_requirements": [
                "lock all VFX/asset ids from template_contract; do not invent new lightning, array geometry, portal shape, summon silhouette, or contract mark",
                "one spectacle result per clip; split omen/setup, activation/entry, and reveal/result if the beat chain is longer than three steps",
                "write readability_beats and degrade_plan from the template_contract; text/numbers/talent labels go to overlay when present",
            ],
            "degrade_plan": "Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.",
        }
    elif shot_type == "meditation_cultivation":
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "image2video",
            "native_audio_policy": "native_sfx" if "低音量" in native_audio_setting else "none",
            "identity_requirement": "face_lock_or_reference_group" if has_named_characters else "reference_group",
            "rationale": [
                "meditation/cultivation shots are low-motion but detail-sensitive: posture, breath rhythm, aura path, and inner-state cue must stay readable",
                "image2video preserves the designed seated pose while allowing controlled aura particles, cloth, hair, dust, and environment response",
            ],
            "prompt_requirements": [
                "lock posture_lock, breath_cycle, energy_flow, aura_vfx_lock, environment_stillness, and micro_motion from template_contract",
                "one inner result per clip: inner vision, dantian/meridian pulse, heart-demon pressure, cultivation breakthrough hint, or calm return",
                "avoid sudden standing, martial movement, new hand seals, or uncontrolled camera rotation; make stillness feel expensive through layered VFX and sound cues",
            ],
            "degrade_plan": "Use a static seated keyframe plus aura/VFX overlay; split posture, breath-energy cycle, inner-state response, and return/hold if the body or hand seal drifts.",
        }
    elif shot_type in ("alchemy_forging", "talent_test"):
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "image2video",
            "native_audio_policy": "native_sfx" if "低音量" in native_audio_setting else "none",
            "identity_requirement": "reference_group" if has_named_characters else "none",
            "rationale": [
                "craft/test shots are object-readability sensitive: the furnace, artifact, material sequence, and result must not morph",
                "first-frame preservation plus low-to-medium process motion keeps product/talent result legible",
            ],
            "prompt_requirements": [
                "lock furnace_or_forge/test_artifact, material/result sequence, process_stage_ladder, heat_curve, material_state_ladder, hand pose, flame/light color, and product/result state",
                "use overlay_policy for numbers, rankings, talent names, attribute text, or panel-like readouts",
                "one result reveal per clip; split preparation, process stage, state transformation, and result if needed",
            ],
            "degrade_plan": "Use static product/test-result keyframe plus flame/light overlay; cut to hand/detail/reaction if the object morphs or the process stage jumps.",
        }
    elif shot_type == "soul_manifestation":
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", "veo", default_backend],
            "mode": "frames2video",
            "native_audio_policy": "native_sfx" if "低音量" in native_audio_setting else "none",
            "identity_requirement": "character_id_or_reference_group" if has_named_characters else "reference_group",
            "rationale": [
                "soul/spirit shots are identity-sensitive: body and soul must read as the same character or the scene becomes confusing",
                "first/end frame control is safer for body-anchor to soul-emergence transitions",
            ],
            "prompt_requirements": [
                "lock body_soul_identity_lock, soul_form_lock, host_body_lock, opacity_curve, and emergence_path",
                "body remains anchored; only translucent soul opacity, glow, and air flow move unless end frame says otherwise",
                "avoid freeform two-soul wrestling; split possession/probe/conflict into clear result frames",
            ],
            "degrade_plan": "Split into body anchor, translucent soul emergence, and probe/conflict result; derive soul form from the character reference.",
        }
    elif shot_type in ("dialogue_shot_reverse", "dialogue_closeup"):
        primary = "kling"
        fallback = ["veo", "seedance"] if _lipsync_enabled(lip_sync_setting) or "保留" in native_audio_setting else ["seedance", default_backend]
        route = {
            "primary_backend": primary,
            "fallback_backends": [b for b in fallback if b != primary],
            "mode": "image2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group" if clip_has_named_characters(clip) else "none",
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
                "describe charge, release, collision/apex, and aftermath beats; no new spell colors",
                "fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, keyframe_plan, post_cue_points, physics_guard, charge_frame, release_frame, effect_asset, energy_path, collision_or_apex_frame, power_shift",
            ],
            "degrade_plan": "Split into charge frame, release frame, collision/apex frame, and aftermath; use VFX overlays in compose if needed.",
        }
    elif shot_type == "dual_cultivation":
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "frames2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group",
            "rationale": [
                "dual cultivation is a consent-bound two-person energy scene: contact, distance, identity, and non-explicit boundaries must be constrained",
                "first/end frames reduce hand/body overlap collapse while letting aura circulation carry the spectacle",
            ],
            "prompt_requirements": [
                "adult characters only; write adult_consent_lock and non_explicit_boundary explicitly; no nudity, no sexual action, no underage implication",
                "lock paired_posture_lock, distance_boundary, contact_points, breath_sync, energy_circulation, aura_vfx_lock, and relationship_state",
                "keep physical motion restrained; use hands/back-to-back silhouettes, meridian light, aura loops, reaction inserts, or fade-to-light for the result",
            ],
            "degrade_plan": "If contact or boundary drifts, replace with hand seal close-up, back-view energy loop, reaction reverse shot, light-fog fade, or split consent/posture, breath sync, energy circulation, and result hold.",
        }
    elif shot_type == "kiss_or_near_kiss":
        route = {
            "primary_backend": "kling",
            "fallback_backends": ["seedance", default_backend],
            "mode": "frames2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group",
            "rationale": [
                "kiss/near-kiss shots are face-angle and contact sensitive: identity, consent, micro-expression, hand placement, and body overlap need first/end frame control",
                "frames2video is safer than free motion for close faces and hands because it constrains the approach and the contact/near-contact frame",
            ],
            "prompt_requirements": [
                "write age_context_lock, consent_lock, and non_explicit_boundary; no nudity, no sexual action, no explicit tongue detail, no underage sexualization",
                "lock approach_path, face_angle_lock, contact_or_near_contact_frame, hand_position_lock, body_overlap_limit, breath_pause, and micro_expression_beats",
                "prefer closed-mouth gentle kiss, forehead/cheek kiss, near-kiss pause, OTS, hand insert, or reaction close-up when the boundary or face contact is unstable",
            ],
            "degrade_plan": "If faces merge, hands drift, or boundary is unclear, split into approach, eye/breath pause, hand/forehead/cheek insert, and separate/reaction clips; use near-kiss or cutaway instead of forcing mouth contact.",
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
        # 5+ 同框/群像不再自动切 Sora：Sora 已是 legacy/manual-only；自动路由优先 Kling 槽位绑定，
        # 再用 Seedance/项目默认拆组。2-3 具名脸的常见同框仍走 Kling（Character ID/主体库 + 运动笔刷锁站位）。
        big_ensemble = shot_type == "ensemble_blocking" or clip_named_character_count(clip) >= 5
        mp_primary = "kling"
        mp_fallback = [b for b in (["seedance", default_backend] if big_ensemble
                                   else ["seedance", default_backend]) if b != mp_primary]
        mp_rationale = [
            "multi-person staging needs reference controls and stable screen direction",
            "single-backend generic generation often swaps faces or screen positions",
        ]
        if big_ensemble:
            mp_rationale.append(
                "5+ 同框/群像：Sora 已从自动路由移除；Kling 负责槽位/主体约束，仍不稳按 degrade_plan 拆组，"
                "不要把 5+ 清晰正脸压在同一镜。"
            )
        # 空间绑定硬约束（与 gate 多人同框槽位 block 同源）：同框必须逐主体绑定到画面槽位+各自参考，
        # 决不能用一张共享参考喂整帧——单参考会让模型把多张脸平均成同一张/混位（脸漂真凶）。
        prompt_requirements = list(prompt_requirements) + [
            "bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)",
        ]
        route = {
            "primary_backend": mp_primary,
            "fallback_backends": mp_fallback,
            "mode": "frames2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group",
            "spatial_binding_required": True,
            "rationale": mp_rationale,
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

    if shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES and t2v_action and not t2v_allowed:
        route["rationale"].append(
            "T2V动作通道=实验开启，但本镜含具名角色且缺 t2v_identity_reference_plan；按主线回退到首帧/首尾帧路径，避免文生视频绕过身份链。"
        )
        route["prompt_requirements"].append(
            "若确需 T2V 实验，先在 storyboard/template_contract 写 t2v_identity_reference_plan(reference_inputs, identity anchors, degrade_plan)。"
        )
    if shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES and t2v_allowed and route.get("mode") == "text2video":
        route["experimental_t2v"] = True
        if t2v_plan:
            route["t2v_identity_reference_plan"] = dict(t2v_plan)
        route["degrade_plan"] = (
            str(route.get("degrade_plan") or "")
            + " If experimental T2V loses identity, immediately reroute to image2video_or_frames2video with first/end frames."
        ).strip()
        route["prompt_requirements"].append(
            "T2V实验镜必须保留 reference_inputs / identity anchors / motion contract，并在失败时回退 image2video_or_frames2video。"
        )
    if t2v_allowed and video_backend_supports_reference_to_video(route.get("primary_backend")):
        route["mode"] = "reference_to_video"
        route["reference_to_video_contract"] = dict(t2v_plan or {})
        route["reference_bundle_status"] = "ready" if t2v_plan else "missing"
        route["prompt_requirements"].append(
            "reference-to-video：必须提交真实 storyboard/reference bundle；逐镜 hero frame 可选，但身份/场景/动作参考不得为空。"
        )
        route["degrade_plan"] = (
            str(route.get("degrade_plan") or "")
            + " If the reference-to-video adapter or bundle fails, return to image2video with landed first/end frames."
        ).strip()

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
    if shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        flags.append("action_choreography_required")
    if shot_type in {"chase", "flight", "mount_ride", "vehicle_ride", "vessel_flight", "road_vehicle", "stealth_stalk"}:
        flags.append("high_speed_motion")
        flags.append("spatial_path_risk")
        flags.append("pose_drift_risk")
    if shot_type == "screen_insert":
        flags.append("text_overlay_required")
        flags.append("screen_readability_risk")
    if shot_type == "evidence_search":
        flags.append("object_continuity_risk")
        flags.append("evidence_chain_required")
    if shot_type in {"tribulation_breakthrough", "array_ritual", "realm_portal", "contract_summon"}:
        flags.append("vfx_consistency_risk")
        flags.append("readability_hold_required")
    if shot_type == "meditation_cultivation":
        flags.append("vfx_consistency_risk")
        flags.append("readability_hold_required")
        flags.append("micro_motion_readability_risk")
    if shot_type == "magic_burst":
        flags.append("vfx_consistency_risk")
        flags.append("readability_hold_required")
        flags.append("high_speed_motion")
        flags.append("spatial_path_risk")
    if shot_type == "dual_cultivation":
        flags.append("consent_non_explicit_required")
        flags.append("energy_circulation_required")
        flags.append("readability_hold_required")
        flags.append("vfx_consistency_risk")
    if shot_type == "kiss_or_near_kiss":
        flags.append("consent_non_explicit_required")
        flags.append("face_contact_risk")
        flags.append("micro_expression_required")
        flags.append("readability_hold_required")
    if shot_type in {"alchemy_forging", "talent_test"}:
        flags.append("object_continuity_risk")
        flags.append("readability_hold_required")
    if shot_type == "alchemy_forging":
        flags.append("vfx_consistency_risk")
    if shot_type == "talent_test":
        flags.append("text_overlay_required")
    if shot_type == "soul_manifestation":
        flags.append("identity_drift_risk")
        flags.append("body_soul_consistency_risk")
        flags.append("readability_hold_required")
    if clip_has_named_characters(clip) and shot_type in {
        "fight_exchange", "chase", "flight", "mount_ride", "vehicle_ride", "vessel_flight",
        "road_vehicle", "stealth_stalk", "screen_insert", "evidence_search",
        "tribulation_breakthrough", "meditation_cultivation", "alchemy_forging", "array_ritual", "soul_manifestation",
        "realm_portal", "contract_summon", "talent_test", "magic_burst",
        "reveal_reaction_chain", "public_confrontation", "relationship_turn",
        *CONTACT_SHOT_TYPES, *MULTI_PERSON_SHOT_TYPES,
    }:
        flags.append("identity_drift_risk")
    if shot_type == "empty_establishing":
        flags.append("low_identity_risk")
    return sorted(set(flags))


def _frame_risk_flags(plan: Mapping[str, Any]) -> List[str]:
    mode = str(plan.get("consumption_mode") or "")
    flags: List[str] = []
    if not plan.get("auto_routable", True):
        flags.append("legacy_manual_backend")
    if int(plan.get("anchor_count") or 0) > 0:
        if mode == "native_multiframe":
            flags.append("native_multiframe")
        elif mode == "split_relay":
            flags.append("split_relay_required")
        else:
            flags.append("mid_anchor_not_consumed_natively")
    if mode.startswith("unsupported") or mode == "unknown_manual_confirm":
        flags.append("frame_contract_unsupported")
    return flags


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
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
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
        elif shot_type == "kiss_or_near_kiss":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = [
                "face_melting",
                "mouth_contact_drift",
                "hand_fusion",
                "body_overlap_collapse",
                "identity_drift",
                "consent_boundary_violation",
                "explicit_content_drift",
            ]
            control_notes = [
                "kiss/near-kiss shots need age context, consent, face angle, contact-or-near-contact frame, hand placement, and body overlap locked",
                "without ready control assets, degrade to near-kiss pause, forehead/cheek kiss, hand insert, OTS/reaction, or separate/hold clips",
            ]
        elif shot_type == "dual_cultivation":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = [
                "body_overlap_collapse",
                "hand_fusion",
                "limb_ownership_swap",
                "consent_boundary_violation",
                "explicit_content_drift",
                "energy_path_drift",
            ]
            control_notes = [
                "dual-cultivation shots need adult consent, non-explicit boundary, paired posture, distance boundary, contact points, and energy circulation locked before generation",
                "without ready control assets, degrade to hand seal close-up, back-view aura loop, reaction reverse shot, or fade-to-light result hold",
            ]
        elif shot_type == "chase":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = ["screen_direction_flip", "distance_curve_reset", "pose_drift", "background_stickiness"]
            control_notes = [
                "chase shots must lock screen direction, distance curve, and camera path; text-only prompts often flip direction or reset distance",
                "if ready motion controls are not available, degrade to alternating pursuer/runner shots with a clear obstacle or turn beat",
            ]
        elif shot_type == "flight":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = ["pose_drift", "altitude_curve_drift", "mount_shape_drift", "background_stickiness"]
            control_notes = [
                "flight/cloud-riding shots must lock rider pose, altitude curve, mount/cloud shape, and parallax layers",
                "if ready controls are not available, keep a cruise pose and move background/cloud layers, or split takeoff/cruise/maneuver/arrival",
            ]
        elif shot_type == "magic_burst":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = ["vfx_shape_drift", "energy_path_flip", "collision_point_lost", "unreadable_apex", "new_unplanned_spell"]
            control_notes = [
                "magic/martial-skill bursts must lock effect asset, energy path, collision/apex frame, and aftershock layers",
                "if ready controls are not available, split charge/release/collision/aftermath or move the VFX into compose overlay layers",
            ]
        elif shot_type == "mount_ride":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = ["rider_mount_contact_drift", "gait_cycle_reset", "pose_drift", "harness_morph", "background_stickiness"]
            control_notes = [
                "mount-riding shots must lock rider saddle/contact points, gait cycle, screen direction, and parallax layers",
                "if ready controls are not available, degrade to beast detail, rider reaction, side-run, and stop/arrival inserts",
            ]
        elif shot_type == "vehicle_ride":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = ["vehicle_shape_drift", "wheel_count_or_rotation_error", "harness_morph", "direction_flip", "background_stickiness"]
            control_notes = [
                "vehicle shots must lock carriage/vehicle shape, wheel count and rotation, harness connection, screen direction, and parallax layers",
                "if ready controls are not available, degrade to wheel/hoof/driver hand/interior reaction inserts plus short side-tracking shots",
            ]
        elif shot_type == "vessel_flight":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = ["vessel_shape_drift", "altitude_curve_drift", "direction_flip", "scale_jump", "background_stickiness"]
            control_notes = [
                "flying-vessel shots must lock vehicle silhouette, flight path, altitude curve, screen direction, and parallax layers",
                "if ready controls are not available, keep the vessel pose stable and split launch/cruise/maneuver/arrival",
            ]
        elif shot_type == "road_vehicle":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = ["vehicle_shape_drift", "wheel_rotation_error", "lane_drift", "traffic_flow_reset", "direction_flip"]
            control_notes = [
                "road-vehicle shots must lock vehicle shape, wheel rotation, driver controls, lane position, traffic flow, screen direction, and parallax layers",
                "if ready controls are not available, degrade to tire/side-mirror/driver-hand/interior reaction inserts plus short side-tracking or braking shots",
            ]
        elif shot_type == "stealth_stalk":
            required_inputs = list(motion_control_inputs_for_spectacle(shot_type))
            failure_modes = ["screen_direction_flip", "distance_curve_reset", "occlusion_layer_jump", "light_shadow_flicker", "target_teleport"]
            control_notes = [
                "stealth/stalking shots must lock screen direction, distance curve, occlusion layers, light/shadow source, and the single reveal-or-hide beat",
                "if ready controls are not available, degrade to peephole/doorframe/footstep/reaction inserts with one controlled reveal",
            ]
        else:
            required_inputs = ["pose_sequence", "depth_sequence", "instance_masks"]
            failure_modes = ["slot_drift", "pose_drift", "identity_drift"]
            control_notes = [
                "complex blocking needs pose/depth plus instance ownership; text prompt is insufficient for stable screen slots",
                "without ready control assets, degrade to smaller groups, OTS pairs, or reaction inserts",
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

    if shot_type in MULTI_PERSON_SHOT_TYPES:
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
    video_generation_audio_policy: str,
    video_channel: str,
    av_mode: str = "voice_first",
    fixed_fallback_backends: Optional[List[str]] = None,
    failure_counts: Optional[Dict[str, int]] = None,
    backend_affinity: Optional[List[Dict[str, Any]]] = None,
    t2v_action: bool = False,
    overseas: bool = False,
    sound_route: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    shot_type = infer_shot_type(clip)
    sound = dict(sound_route or {})
    sound_strategy = str(sound.get("audio_strategy") or "").strip()
    effective_av_mode = av_mode
    effective_lip_sync = lip_sync_setting
    if av_mode == "hybrid":
        effective_av_mode = "native_av" if sound_strategy == "native_av" else "voice_first"
        if sound_strategy == "performance_audio_first" and str(sound.get("performance_track_status") or "") in {"guide_ready", "final_ready"}:
            effective_lip_sync = "配音对齐"
        else:
            effective_lip_sync = "关闭"
    route = choose_route(
        clip,
        shot_type,
        default_backend=default_backend,
        routing_mode=routing_mode,
        native_audio_setting=native_audio_setting,
        lip_sync_setting=effective_lip_sync,
        av_mode=effective_av_mode,
        fixed_fallback_backends=fixed_fallback_backends,
        t2v_action=t2v_action,
        overseas=overseas,
    )
    if av_mode == "hybrid" and sound_strategy == "base_video_then_post_lipsync":
        # This is intentionally a base-performance plate, not a finished talking
        # shot.  The later lipsync/Act-Two-like channel owns visible articulation.
        route = dict(route)
        route["mode"] = "image2video"
        route["native_audio_policy"] = "none"
        route["rationale"] = list(route.get("rationale") or []) + [
            "混合路由：当前无已签收表演音轨，只生成中性嘴型的基础视频；音轨就绪后走独立后期表演/口型驱动。"
        ]
        route["prompt_requirements"] = list(route.get("prompt_requirements") or []) + [
            "base_video_only=true；嘴唇保持自然闭合/静息，不做可辨识发音动作，不让模型即兴说话；为后期表演驱动保留稳定正脸与表情空间。"
        ]
        route["degrade_plan"] = (
            "先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。"
            "基础视频未经该 pass 不得作为最终说话镜进入 compose。"
        )
    route = prefer_execution_multiframe_backend(
        clip,
        route,
        default_backend=default_backend,
        video_channel=video_channel,
    )
    primary = normalize_backend(route["primary_backend"], default_backend)
    clip_id = make_clip_id(clip, index)
    # ③ 一角一后端亲和：核心/主演角色（已注册原生视频主体=脸被锁死）冲突=硬钉其 locked_backend，
    #   把脸锁后端强加为 primary（原 primary 降为 fallback 首项），防核心角色跨镜漂后端→脸质感漂移；
    #   非 core 角色仍仅 warn（advisory，不改路由）。
    backend_conflicts = character_backend_conflicts(clip, primary, backend_affinity)
    pin_notes: List[str] = []
    enforced = [c for c in backend_conflicts if c.get("enforce") and c.get("locked_backend")]
    if enforced:
        locked = normalize_backend(enforced[0]["locked_backend"], primary)
        if locked and locked != primary:
            fbs = [primary] + [b for b in route["fallback_backends"] if b != locked]
            route["fallback_backends"] = fbs[:3]
            pin_notes.append(
                f"核心角色「{enforced[0]['character']}」原生主体锁在「{locked}」：硬钉 primary=「{locked}」"
                f"（原「{primary}」降为 fallback），防核心角色跨镜换后端致脸质感漂移。")
            primary = locked
        # 重算冲突（primary 已被钉到 locked_backend，核心角色此时应无冲突，仅余其它 core 不可同时满足者）
        backend_conflicts = character_backend_conflicts(clip, primary, backend_affinity)
    risk_flags = risk_flags_for_clip(clip, shot_type, primary)
    if backend_conflicts:
        risk_flags = sorted(set(risk_flags) | {"character_backend_conflict"})
    if route.get("native_audio_policy") == "native_speech":
        risk_flags = sorted(set(risk_flags) | {"native_speech"})
    seam_relay = seam_relay_plan(clip, primary, route["fallback_backends"], video_channel=video_channel)
    rationale = list(route["rationale"]) + pin_notes
    prompt_requirements = list(route["prompt_requirements"])
    choreography = action_choreography_contract(shot_type)
    if choreography.get("required"):
        prompt_requirements.append(
            "必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 "
            + ", ".join(choreography.get("required_fields", []))
            + "；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。"
        )
    clip_characters = clip_character_refs(clip)
    if clip_characters and str(route.get("identity_requirement") or "").strip().lower() == "none":
        route = dict(route)
        route["identity_requirement"] = "reference_group"
        route["rationale"] = list(route.get("rationale") or []) + [
            "含结构化角色 ID，最终保护层将 identity_requirement 从 none 升为 reference_group，避免执行端少传身份参考。"
        ]
        route["prompt_requirements"] = list(route.get("prompt_requirements") or []) + [
            "本镜含结构化角色 ID，必须传首帧/角色 reference_group 或等效身份参考；不得按纯空镜处理。"
        ]
        if str(route.get("mode") or "").strip().lower() in {"text2video", "t2v"} and not route.get("experimental_t2v"):
            route["mode"] = "image2video"
            route["rationale"].append(
                "非实验 T2V 不可承载具名角色身份链，改为 image2video 以继承首帧/尾帧/锚帧。"
            )
    if seam_relay.get("is_relay"):
        risk_flags = sorted(set(risk_flags) | {"seam_relay"})
        if seam_relay.get("seam_guaranteed"):
            rationale.append(
                f"接力镜：primary「{primary}」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。")
        else:
            fb = seam_relay.get("dual_keyframe_fallback")
            rationale.append(
                f"接力镜：primary「{primary}」无首尾硬约束能力——优先改用 "
                f"{fb or '可灵O3/即梦多帧等首尾帧后端'} 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。")
        prompt_requirements.append(
            "接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。")
    entry = {
        "clip_id": clip_id,
        "shot_type": shot_type,
        "template": str(clip.get("template") or "none"),
        "primary_backend": primary,
        "fallback_backends": route["fallback_backends"],
        "mode": route["mode"],
        "video_generation_audio_policy": video_generation_audio_policy,
        "native_audio_policy": route["native_audio_policy"],
        "identity_requirement": route["identity_requirement"],
        "clip_characters": clip_characters,
        "loc": clip_loc(clip),
        "max_clip_seconds": video_backend_max_seconds(primary),
        "clip_seconds": clip_duration_seconds(clip),
        "risk_flags": risk_flags,
        "seam_relay": seam_relay,
        "motion_control": motion_control_contract(clip, clip_id, shot_type, primary, episode),
        "action_choreography": choreography,
        "rationale": rationale,
        "prompt_requirements": prompt_requirements,
        "degrade_plan": route["degrade_plan"],
        "character_backend_conflicts": backend_conflicts,
    }
    if sound:
        entry["sound_route"] = sound
        for key in (
            "audio_strategy", "timing_basis", "performance_track_status",
            "performance_audio_paths", "voice_lock_status", "final_voice_required",
            "requires_voice_lock_before_final_render", "requires_performance_audio_before_final",
            "post_lipsync_required", "base_video_only", "base_video_mouth_policy",
            "post_lipsync_output",
            "can_generate_base_video", "can_generate_final_performance", "final_voice_stage", "route_commitment",
        ):
            if key in sound:
                entry[key] = sound[key]
        if sound.get("post_lipsync_required"):
            entry["risk_flags"] = sorted(set(entry.get("risk_flags") or []) | {"post_lipsync_required", "base_video_only"})
            entry["post_video_qc"] = {
                "required": True,
                "checks": ["base_plate_identity_stable", "neutral_rest_mouth", "post_lipsync_output_required_before_compose"],
            }
    for key in (
        "experimental_t2v",
        "t2v_identity_reference_plan",
        "requires_voice_fallback",
        "fallback_production_mode",
        "native_av_override_reason",
    ):
        if key in route:
            entry[key] = route[key]
    frame_req = _timeline_frame_requirements(clip)
    frame_control = video_backend_frame_control(primary, video_channel)
    anchor_plan = anchor_consumption_plan(
        primary,
        video_channel,
        anchor_count=int(frame_req.get("anchor_count") or 0),
        need_end=bool(frame_req.get("need_end")),
    )
    entry["frame_control"] = frame_control
    entry["anchor_consumption"] = anchor_plan
    segment_relay = duration_segment_relay_plan(clip, str(primary), anchor_plan, clip_id=clip_id)
    if segment_relay.get("required"):
        entry["duration_segment_relay"] = segment_relay
        if segment_relay.get("supported"):
            entry["risk_flags"] = sorted((set(entry["risk_flags"]) - {"long_duration"}) | {"duration_segment_relay"})
            entry["rationale"].append(
                f"本镜 {segment_relay.get('clip_seconds')}s 超过 {primary} 单次上限 "
                f"{segment_relay.get('max_clip_seconds')}s；执行侧必须按现有首/中/尾帧拆成 "
                f"{len(segment_relay.get('segments') or [])} 段 first_last_relay 付费提交，"
                "每段不超过上限，再在后续合成阶段接回。"
            )
            entry["prompt_requirements"].append(
                "长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。"
            )
        else:
            entry["rationale"].append(
                f"本镜超过 {primary} 单次上限，且无法用现有锚帧形成安全分段：{segment_relay.get('reason')}"
            )
    if not (routing_mode == "fixed_default" and not (entry.get("fallback_backends") or [])):
        entry["fallback_backends"] = duration_safe_fallbacks(
            str(primary),
            entry.get("fallback_backends") or [],
            duration_for_backend_selection(entry),
            native_audio_policy=str(entry.get("native_audio_policy") or ""),
            anchor_contract=anchor_plan,
            video_channel=video_channel,
        )
    extra_frame_flags = _frame_risk_flags(anchor_plan)
    if extra_frame_flags:
        entry["risk_flags"] = sorted(set(entry["risk_flags"]) | set(extra_frame_flags))
    if frame_req.get("anchor_count"):
        if anchor_plan["consumption_mode"] == "native_multiframe":
            entry["rationale"].append("本镜中段锚帧会被后端作为原生时间轴关键帧消费。")
        elif anchor_plan["consumption_mode"] == "split_relay":
            entry["rationale"].append("本镜中段锚帧不能被 primary 原生消费，执行侧必须拆段接力，锚帧作为段边界首尾帧。")
        else:
            entry["rationale"].append(
                f"本镜声明中段锚帧，但 primary 的消费模式为 {anchor_plan['consumption_mode']}；"
                "出视频前需 reroute 到原生多帧/首尾帧后端或改 storyboard 帧契约。"
            )
    fc = (failure_counts or {}).get(clip_id, 0)
    if fc:  # E4：本镜 identity 反复失败 → 升锁（含固定后端模式只收紧不换厂）
        entry = escalate_identity_for_failures(entry, fc, fixed_mode=(routing_mode == "fixed_default"))
    # 质量档（成本×质量）+ 视频运动参考：用升锁/钉锁后的最终 primary 与 risk_flags 计算（增量字段）。
    final_primary = entry["primary_backend"]
    if not (routing_mode == "fixed_default" and not (entry.get("fallback_backends") or [])):
        entry["fallback_backends"] = duration_safe_fallbacks(
            str(final_primary),
            entry.get("fallback_backends") or [],
            duration_for_backend_selection(entry),
            native_audio_policy=str(entry.get("native_audio_policy") or ""),
            anchor_contract=entry.get("anchor_consumption") if isinstance(entry.get("anchor_consumption"), Mapping) else None,
            video_channel=video_channel,
        )
    entry["quality_tier"] = quality_tier_for_clip(entry["shot_type"], entry["risk_flags"], final_primary)
    if entry["quality_tier"] == "high":
        entry["rationale"].append(
            "质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。")
    elif entry["quality_tier"] == "fast":
        entry["rationale"].append(
            "质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。")
    mref = motion_reference_plan(entry["shot_type"], final_primary)
    entry["motion_reference"] = mref
    if mref.get("applicable"):
        entry["risk_flags"] = sorted(set(entry["risk_flags"]) | {"motion_reference_candidate"})
        entry["rationale"].append(mref["note"])
        entry["prompt_requirements"].append(
            "若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。")
    if needs_identity_preservation_plan(entry):
        entry["identity_preservation_plan"] = identity_preservation_plan(entry)
    entry["execution_recipe"] = execution_recipe_for_route(entry, clip, video_channel=video_channel)
    return entry


# 多镜组成员上限（次级护栏，防 0/缺时长时无限聚集）。主护栏是累计时长 ≤ 后端单次输出上限。
MULTISHOT_MAX_MEMBERS = 4


def annotate_multishot_groups(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标注「多镜单次生成」候选组（2026-06-19 流程自审落地·advisory）。纯函数·可测。

    Seedance 2.0 等可一次出多镜头叙事且跨镜一致、无缝转场。对**连续接力镜 + 同一支持多镜的
    primary**，这段最适合一次 co-generate 消灭接缝。**但 n2d 立身之本是逐 Clip 可追踪可重跑**
    （模型矩阵 line 17），所以只标 `multishot_candidate` 提示 + 返回组清单，**不合并 Clip、不改
    primary/mode**——逐镜仍是独立可重跑单元；是否真的一次出由出片侧/用户按接缝风险决定。

    **组大小受物理约束封顶**：单次多镜生成的总输出长度 ≤ 后端 `max_clip_seconds`（如 Seedance ~15s），
    所以按**累计时长**切组——加入会超上限就断新组（缺/0 时长时退到 `MULTISHOT_MAX_MEMBERS` 成员护栏），
    避免出「11 镜一次出」这种物理上不可能、误导操作者的巨组。返回 [{group_id, members, backend}]。"""
    groups: List[Dict[str, Any]] = []
    run: List[Dict[str, Any]] = []

    def _flush() -> None:
        if len(run) >= 2:
            backend = run[0]["primary_backend"]
            gid = f"MSG_{len(groups)+1:02d}"
            members = [r["clip_id"] for r in run]
            total = round(sum(float(r.get("clip_seconds") or 0) for r in run), 2)
            for r in run:
                r["multishot_candidate"] = {
                    "group_id": gid,
                    "members": members,
                    "note": (
                        f"接力镜组 {members}（≈{total}s）：primary「{backend}」支持多镜单次生成，可一次 co-generate "
                        "这段消灭接缝/最稳跨镜一致；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定是否合并。"
                    ),
                }
                r["risk_flags"] = sorted(set(r.get("risk_flags", [])) | {"multishot_candidate"})
            groups.append({"group_id": gid, "members": members, "backend": backend,
                           "approx_seconds": total})
        run.clear()

    def _eligible(r: Mapping[str, Any]) -> bool:
        relay = isinstance(r.get("seam_relay"), Mapping) and r["seam_relay"].get("is_relay")
        return bool(relay and video_backend_supports_multishot(r.get("primary_backend")))

    for r in routes:
        if not _eligible(r):
            _flush()
            continue
        backend = r.get("primary_backend")
        if run and run[-1]["primary_backend"] != backend:
            _flush()
        # 累计时长护栏：加入本镜后超后端单次输出上限 → 先断组（已有成员先成组）。
        cap = video_backend_max_seconds(backend)
        cur_total = sum(float(x.get("clip_seconds") or 0) for x in run)
        add = float(r.get("clip_seconds") or 0)
        would_exceed_seconds = add and cur_total and cap and (cur_total + add) > cap
        would_exceed_members = len(run) >= MULTISHOT_MAX_MEMBERS
        if run and (would_exceed_seconds or would_exceed_members):
            _flush()
        run.append(r)
    _flush()
    return groups


def _route_char_set(route: Mapping[str, Any]) -> frozenset:
    chars = route.get("clip_characters")
    out = set()
    if isinstance(chars, (list, tuple)):
        for c in chars:
            if isinstance(c, Mapping):
                cid = str(c.get("character_id") or c.get("id") or "").strip()
            else:
                cid = str(c or "").strip()
            if cid:
                out.add(cid)
    return frozenset(out)


def recommend_multishot_reroute(
    routes: List[Dict[str, Any]],
    available_multishot_backends: Sequence[str],
) -> List[Dict[str, Any]]:
    """同场景/同角色连续镜 → 推荐改走原生多镜后端（2026-06 一致性加固·advisory）。纯函数·可测。

    `annotate_multishot_groups` 只在 **primary 本身已支持多镜** 且为接力镜时标候选；它不会在
    primary 不支持多镜时**主动建议换后端**。但 2026 的 SOTA（Kling 3.0 Element Binding / Director
    Memory 物体恒存、Veo 3.1 ingredients、Seedance 多镜叙事）把一大块跨镜身份/场景/对象持久性塞进
    **单次多镜生成**——对一段「同场景」或「同角色集」的连续镜，改走原生多镜后端能让 Element Binding
    直接扛掉本来要靠 inherit_contract 硬拦的漂移。

    本函数扫这种连续镜段：primary 不支持多镜时给出**换后端建议**（advisory，不改 primary、不合并
    Clip——逐 Clip 仍可追踪可重跑）。优先建议项目 roster 内已有的多镜后端；roster 内没有时，给规范候选
    并标 `roster_switch_required`，提醒换后端须**整项目统一、勿混用**（anti-mixing），由出片侧/用户定夺。"""
    in_roster = next((b for b in available_multishot_backends if video_backend_supports_multishot(b)), "")
    suggest = in_roster or "seedance"  # 规范多镜候选（保守默认；kling 亦可，按项目接口可用性复核）
    roster_switch_required = not in_roster
    recs: List[Dict[str, Any]] = []
    run: List[Dict[str, Any]] = []

    def _flush() -> None:
        if len(run) >= 2:
            gid = f"MRR_{len(recs)+1:02d}"
            members = [r["clip_id"] for r in run]
            same_loc = len({r.get("loc") or "" for r in run}) == 1 and (run[0].get("loc"))
            basis = "同场景" if same_loc else "同角色集"
            note = (
                f"{basis}连续镜组 {members}：primary「{run[0].get('primary_backend')}」非原生多镜，"
                f"建议这段改走多镜后端「{suggest}」一次 co-generate——Element Binding/Director Memory 直接稳跨镜"
                f"身份/场景/对象持久性，省 inherit_contract 硬拦。advisory：不改 primary、不合并 Clip，"
                f"换后端须整项目统一（勿混用），由出片侧/用户定夺。"
            )
            for r in run:
                r["multishot_reroute_suggestion"] = {
                    "group_id": gid, "members": members, "suggested_backend": suggest, "basis": basis,
                    "roster_switch_required": roster_switch_required,
                }
                r["risk_flags"] = sorted(set(r.get("risk_flags", [])) | {"multishot_reroute_candidate"})
            recs.append({"group_id": gid, "members": members, "suggested_backend": suggest,
                         "basis": basis, "roster_switch_required": roster_switch_required, "note": note})
        run.clear()

    def _continuous(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> bool:
        # 已支持多镜的 primary 由 annotate_multishot_groups 管，这里只盯「漏网」的非多镜 primary。
        if video_backend_supports_multishot(cur.get("primary_backend")):
            return False
        same_loc = bool(cur.get("loc")) and prev.get("loc") == cur.get("loc")
        chars = _route_char_set(cur)
        same_char = bool(chars) and _route_char_set(prev) == chars
        return same_loc or same_char

    for r in routes:
        if video_backend_supports_multishot(r.get("primary_backend")):
            _flush()
            continue
        if run and not _continuous(run[-1], r):
            _flush()
        run.append(r)
    _flush()
    return recs


def spectacle_backend_benchmark_path(root: Path) -> Path:
    return Path(root) / "生产数据" / "spectacle_backend_benchmark.json"


# ── 跨后端英雄镜多版（hero shot cross-backend multi-version） ──────────────────────────
def _hero_multi_enabled(setting: Any) -> bool:
    """`英雄镜多版` 是否开启（非「关闭」即视为开启）。costly 选择点，默认关闭。"""
    return str(setting or "").strip().lower() not in HERO_MULTI_OFF_VALUES


def is_hero_shot(clip: Mapping[str, Any], shot_type: str, idx: int) -> bool:
    """是否英雄镜（名场面/开场钩/高潮）——高价值、值得跨后端多版兜底的镜。纯函数·可测。"""
    if shot_type in HERO_SHOT_TYPES:
        return True
    if idx == 1:                                  # 第1镜=开场钩
        return True
    return bool(HERO_SIGNATURE_RE.search(_clip_text(clip)))


def _hero_secondary_backend(route: Mapping[str, Any]) -> Optional[str]:
    """选一个与 primary 不同的次后端做多版兜底：取 fallback_backends 里第一个异于 primary 的后端。"""
    primary = normalize_backend(route.get("primary_backend") or "")
    for backend in route.get("fallback_backends") or []:
        nb = normalize_backend(backend)
        if nb and nb != primary:
            return nb
    return None


def apply_hero_multi_version(routes: Sequence[Dict[str, Any]], clips: Sequence[Mapping[str, Any]],
                             *, setting: Any, episode: str, routing_mode: str = "") -> Dict[str, Any]:
    """英雄镜跨后端多版规划（post-pass，原地标注 route['hero_multi_version']）。

    开启时：对每个英雄镜，若能选出异于 primary 的 secondary 后端，就写 hero_multi_version 契约，
    指示执行端 primary + secondary 各出一版、pooled 进候选、video_qc 选优。固定后端模式不抢
    （routing_mode=fixed_default 时整条线只用单后端，不做跨后端多版）。纯函数·可测。"""
    summary: Dict[str, Any] = {"enabled": _hero_multi_enabled(setting), "hero_clips": [], "skipped_no_secondary": []}
    if not summary["enabled"] or routing_mode == "fixed_default":
        summary["enabled"] = summary["enabled"] and routing_mode != "fixed_default"
        return summary
    for idx, (route, clip) in enumerate(zip(routes, clips), 1):
        if not isinstance(route, dict):
            continue
        shot_type = str(route.get("shot_type") or "")
        if not is_hero_shot(clip, shot_type, idx):
            continue
        clip_id = str(route.get("clip_id") or route.get("id") or f"Clip_{idx:02d}")
        secondary = _hero_secondary_backend(route)
        if not secondary:
            summary["skipped_no_secondary"].append(clip_id)
            continue
        route["hero_multi_version"] = {
            "enabled": True,
            "primary_backend": normalize_backend(route.get("primary_backend") or ""),
            "secondary_backend": secondary,
            "candidate_pool": f"出视频/{episode}/候选/{clip_id}/",
            "select_by": "video_qc",
            "reason": ("英雄镜（名场面/开场钩/高潮）跨后端多版兜底：primary+secondary 各出一版 pooled 进候选，"
                       "video_qc 选优；高价值镜不赌单后端发挥，初始流量都冲这些高光而来。"),
        }
        summary["hero_clips"].append(clip_id)
    return summary


def load_spectacle_backend_benchmark(root: Path) -> Dict[str, Any]:
    """Read optional probe-backed backend recommendations.

    Shape accepted:
      {"kind": "n2d_spectacle_backend_benchmark",
       "recommendations": {"fight_exchange": {"primary_backend": "seedance", ...}}}
    """
    path = spectacle_backend_benchmark_path(root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, Mapping):
        return {}
    kind = str(data.get("kind") or "").strip()
    if kind and kind != SPECTACLE_BACKEND_BENCHMARK_KIND:
        return {}
    recs = data.get("recommendations")
    if not isinstance(recs, Mapping):
        return {}
    out = dict(data)
    # 新鲜度护栏（2026-07 标准审计）：旧逻辑对 probe 结果零时效校验——任意久远的 benchmark
    # 会永久覆盖高动态镜路由。probed_at/generated_at 超龄（默认 45 天·对齐 freshness 候选表
    # 上限·env N2D_SPECTACLE_BENCHMARK_MAX_AGE_DAYS 可调）即标 stale：仍返回数据供审计，
    # 但 apply 端只留 advisory 不改 primary。缺时间戳按 stale 处理（诚实：没证据日期=不可信）。
    max_age_days = float(os.environ.get("N2D_SPECTACLE_BENCHMARK_MAX_AGE_DAYS", "45"))
    stamp = str(data.get("probed_at") or data.get("generated_at") or data.get("checked_at") or "").strip()
    stale = True
    if stamp:
        try:
            probed = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if probed.tzinfo is None:
                probed = probed.replace(tzinfo=dt.timezone.utc)
            age = (dt.datetime.now(dt.timezone.utc) - probed).days
            stale = age > max_age_days
            out["benchmark_age_days"] = age
        except ValueError:
            stale = True
    out["benchmark_stale"] = stale
    if stale:
        out["stale_reason"] = (f"probe 时间戳缺失" if not stamp
                               else f"probe 已 {out.get('benchmark_age_days')} 天 > {max_age_days:g} 天上限")
    return out


def _benchmark_recommendation(benchmark: Mapping[str, Any], spectacle_type: str) -> Dict[str, Any]:
    recs = benchmark.get("recommendations") if isinstance(benchmark.get("recommendations"), Mapping) else {}
    raw = recs.get(spectacle_type) if isinstance(recs, Mapping) else {}
    if isinstance(raw, str):
        return {"primary_backend": raw}
    return dict(raw) if isinstance(raw, Mapping) else {}


def apply_spectacle_backend_benchmark(
    routes: List[Dict[str, Any]],
    clips: Sequence[Any],
    *,
    benchmark: Mapping[str, Any],
    episode: str,
    default_backend: str,
    video_channel: str,
    routing_mode: str,
) -> List[Dict[str, Any]]:
    """Apply optional probe-backed backend recommendations to high-dynamic routes.

    Fixed-default mode is intentionally left untouched.  This is a production
    feedback loop from small probe clips, not an authority to override a user
    who explicitly locked the project to one backend.
    """
    if routing_mode == "fixed_default" or not benchmark:
        return []
    if benchmark.get("benchmark_stale"):
        # 过期 probe 不改 primary：逐 route 打 advisory 风险旗留痕，提示重跑 probe 刷新。
        for route in routes:
            flags = set(route.get("risk_flags") or [])
            flags.add("spectacle_benchmark_stale")
            route["risk_flags"] = sorted(flags)
        return [{"skipped": "benchmark_stale", "reason": str(benchmark.get("stale_reason") or "")}]
    applied: List[Dict[str, Any]] = []
    for idx, route in enumerate(routes):
        clip = clips[idx] if idx < len(clips) and isinstance(clips[idx], Mapping) else {}
        spectacle_type = infer_spectacle_type(clip) or str(route.get("shot_type") or "")
        if spectacle_type not in set(ACTION_CHOREOGRAPHY_SHOT_TYPES) | {"large_establishing"}:
            continue
        rec = _benchmark_recommendation(benchmark, spectacle_type)
        backend = normalize_backend(str(rec.get("primary_backend") or rec.get("backend") or ""), default="")
        if not backend or not video_backend_auto_routable(backend):
            continue
        old = normalize_backend(str(route.get("primary_backend") or ""), default_backend)
        if not old or backend == old:
            continue
        if route.get("locked_backend") and not bool(rec.get("override_identity_lock")):
            route["spectacle_benchmark_deferred"] = {
                "spectacle_type": spectacle_type,
                "recommended_backend": backend,
                "current_primary": old,
                "reason": "identity_affinity_locked_backend",
                "evidence": rec.get("evidence"),
            }
            route["risk_flags"] = sorted(set(route.get("risk_flags", [])) | {"spectacle_benchmark_deferred_by_identity"})
            route.setdefault("rationale", []).append(
                f"spectacle benchmark recommends {backend} for {spectacle_type}, but identity backend lock keeps {old}; "
                "set override_identity_lock=true in benchmark only after identity QC signoff."
            )
            continue
        if route.get("baseline_anchored") and not bool(rec.get("override_baseline")):
            route["spectacle_benchmark_deferred"] = {
                "spectacle_type": spectacle_type,
                "recommended_backend": backend,
                "current_primary": old,
                "reason": "cross_episode_baseline",
                "evidence": rec.get("evidence"),
            }
            route["risk_flags"] = sorted(set(route.get("risk_flags", [])) | {"spectacle_benchmark_deferred_by_baseline"})
            route.setdefault("rationale", []).append(
                f"spectacle benchmark recommends {backend} for {spectacle_type}, but cross-episode baseline keeps {old}; "
                "set override_baseline=true only after series-style QC signoff."
            )
            continue
        fallback = [old] + [normalize_backend(b, default="") for b in route.get("fallback_backends", [])]
        route["primary_backend"] = backend
        route["fallback_backends"] = [b for b in fallback if b and b != backend][:3]
        route["max_clip_seconds"] = video_backend_max_seconds(backend)
        route["motion_control"] = motion_control_contract(
            clip,
            str(route.get("clip_id") or make_clip_id(clip, idx + 1)),
            str(route.get("shot_type") or ""),
            backend,
            episode,
        )
        frame_req = _timeline_frame_requirements(clip)
        route["frame_control"] = video_backend_frame_control(backend, video_channel)
        route["anchor_consumption"] = anchor_consumption_plan(
            backend,
            video_channel,
            anchor_count=int(frame_req.get("anchor_count") or 0),
            need_end=bool(frame_req.get("need_end")),
        )
        route["risk_flags"] = sorted(set(route.get("risk_flags", [])) | {"spectacle_benchmark_routed"})
        route["quality_tier"] = quality_tier_for_clip(
            str(route.get("shot_type") or ""),
            route.get("risk_flags", []),
            backend,
        )
        route.setdefault("rationale", []).append(
            f"spectacle probe benchmark recommends {backend} for {spectacle_type}; "
            f"primary changed from {old} and old primary kept as fallback."
        )
        route["spectacle_benchmark"] = {
            "spectacle_type": spectacle_type,
            "recommended_backend": backend,
            "previous_primary": old,
            "score": rec.get("score"),
            "evidence": rec.get("evidence"),
        }
        applied.append({
            "clip_id": route.get("clip_id"),
            "spectacle_type": spectacle_type,
            "was": old,
            "now": backend,
            "score": rec.get("score"),
        })
    return applied


def apply_spectacle_backend_prior(
    routes: List[Dict[str, Any]],
    clips: Sequence[Any],
    *,
    benchmark: Mapping[str, Any],
    default_backend: str,
    routing_mode: str,
) -> List[Dict[str, Any]]:
    """冷启动后端先验：补「关键词识别为奇观、但 shot_type 通用、路由落到 default」那批镜。

    这是 benchmark 为空/未覆盖时的兜底，让没跑过 probe 的项目也有按动作类型选后端的依据。
    刻意只动「通用 default 兜底」的镜，不碰 route_clip 已显式给过 spectacle 后端的镜
    (fight→kling / chase·flight→seedance)，也不碰 baseline 锚定、benchmark 已覆盖、fixed_default。
    benchmark > prior：某 spectacle_type 已有 benchmark 推荐则本函数跳过该类型。
    执行契约(frame/anchor/motion_control/quality)统一交给随后的 refresh_execution_contracts 重建。
    """
    if routing_mode == "fixed_default":
        return []
    default_norm = normalize_backend(default_backend, default_backend)
    covered_types = set()
    recs = benchmark.get("recommendations") if isinstance(benchmark, Mapping) else None
    if isinstance(recs, Mapping):
        covered_types = {str(k) for k in recs.keys()}
    applied: List[Dict[str, Any]] = []
    for idx, route in enumerate(routes):
        clip = clips[idx] if idx < len(clips) and isinstance(clips[idx], Mapping) else {}
        spectacle_type = infer_spectacle_type(clip)
        if not spectacle_type or spectacle_type in covered_types:
            continue
        # route_clip 已显式 spectacle 路由的镜不动；baseline 锁定的镜不动（跨集一致优先）。
        if str(route.get("shot_type") or "") in set(ACTION_CHOREOGRAPHY_SHOT_TYPES):
            continue
        if route.get("baseline_anchored") or route.get("locked_backend"):
            continue
        ranking = spectacle_backend_prior_ranking(spectacle_type)
        if not ranking:
            continue
        target = ranking[0]
        current = normalize_backend(str(route.get("primary_backend") or ""), default_backend)
        # 只补「通用兜底落到 default」这一冷启动缺口；已是 target 或被别的逻辑选过非 default 的不动。
        if current == target or current != default_norm:
            continue
        fallback = [current] + [normalize_backend(b, default="") for b in ranking[1:]]
        route["primary_backend"] = target
        route["fallback_backends"] = [b for b in fallback if b and b != target][:3]
        route["risk_flags"] = sorted(set(route.get("risk_flags", [])) | {"spectacle_prior_routed"})
        route.setdefault("rationale", []).append(
            f"spectacle cold-start prior: {spectacle_type} 默认排序首选 {target}"
            f"（{SPECTACLE_BACKEND_PRIOR.get(spectacle_type, {}).get('basis', '')}）；"
            f"通用兜底 {current} 改为 prior 首选，原后端保留为 fallback。跑 probe 后由 benchmark 覆盖。"
        )
        route["spectacle_prior"] = {
            "spectacle_type": spectacle_type,
            "prior_backend": target,
            "previous_primary": current,
            "ranking": list(ranking),
        }
        applied.append({
            "clip_id": route.get("clip_id"),
            "spectacle_type": spectacle_type,
            "was": current,
            "now": target,
        })
    return applied


def native_multiframe_candidate(
    route: Mapping[str, Any],
    *,
    video_channel: str,
    anchor_count: int,
    need_end: bool,
) -> str:
    """Pick an auto-routable backend that can consume declared mid anchors natively."""
    if anchor_count <= 0:
        return ""
    current = normalize_backend(str(route.get("primary_backend") or ""), default="")
    candidates: List[str] = []
    for raw in list(route.get("fallback_backends") or []) + ["dreamina", "seedance", "kling"]:
        backend = normalize_backend(str(raw or ""), default="")
        if not backend or backend == current or backend in candidates:
            continue
        if not video_backend_auto_routable(backend):
            continue
        plan = anchor_consumption_plan(backend, video_channel, anchor_count=anchor_count, need_end=need_end)
        if plan.get("consumption_mode") == "native_multiframe":
            candidates.append(backend)
    return candidates[0] if candidates else ""


def refresh_execution_contracts(
    routes: List[Dict[str, Any]],
    clips: Sequence[Any],
    *,
    root: Optional[Path] = None,
    episode: str,
    video_channel: str,
    urgency_tier: str,
    routing_mode: str = "auto",
) -> None:
    """Rebuild execution-facing route fields after final primary/fallback edits."""
    for idx, route in enumerate(routes):
        clip = clips[idx] if idx < len(clips) and isinstance(clips[idx], Mapping) else {}
        primary = normalize_backend(str(route.get("primary_backend") or ""), default="")
        clip_id = str(route.get("clip_id") or make_clip_id(clip, idx + 1))
        shot_type = str(route.get("shot_type") or infer_shot_type(clip))
        clip_seconds = float(route.get("clip_seconds") or clip_duration_seconds(clip) or 0)
        frame_req = _timeline_frame_requirements(clip)
        route["max_clip_seconds"] = video_backend_max_seconds(primary)
        if not (routing_mode == "fixed_default" and not (route.get("fallback_backends") or [])):
            route["fallback_backends"] = duration_safe_fallbacks(
                primary,
                route.get("fallback_backends") or [],
                duration_for_backend_selection(route),
                native_audio_policy=str(route.get("native_audio_policy") or ""),
            )
        route["frame_control"] = video_backend_frame_control(primary, video_channel)
        route["anchor_consumption"] = anchor_consumption_plan(
            primary,
            video_channel,
            anchor_count=int(frame_req.get("anchor_count") or 0),
            need_end=bool(frame_req.get("need_end")),
        )
        if routing_mode != "fixed_default" and route["anchor_consumption"].get("requires_split_relay"):
            replacement = native_multiframe_candidate(
                route,
                video_channel=video_channel,
                anchor_count=int(frame_req.get("anchor_count") or 0),
                need_end=bool(frame_req.get("need_end")),
            )
            if replacement:
                old = primary
                route["primary_backend"] = replacement
                route["fallback_backends"] = [
                    b for b in [old, *list(route.get("fallback_backends") or [])] if normalize_backend(str(b), default="") != replacement
                ][:3]
                route.setdefault("rationale", []).append(
                    f"frame_anchor_required: 本镜声明中段锚帧，{old} 只能 split_relay；改用 {replacement} 原生多关键帧以避免中锚被降级。"
                )
                flags = set(route.get("risk_flags") or [])
                flags.add("frame_anchor_rerouted")
                route["risk_flags"] = sorted(flags)
                primary = replacement
                route["max_clip_seconds"] = video_backend_max_seconds(primary)
                route["frame_control"] = video_backend_frame_control(primary, video_channel)
                route["anchor_consumption"] = anchor_consumption_plan(
                    primary,
                    video_channel,
                    anchor_count=int(frame_req.get("anchor_count") or 0),
                    need_end=bool(frame_req.get("need_end")),
                )
        segment_relay = duration_segment_relay_plan(clip, primary, route["anchor_consumption"], clip_id=clip_id)
        flags = set(route.get("risk_flags") or [])
        if segment_relay.get("required"):
            route["duration_segment_relay"] = segment_relay
            if segment_relay.get("supported"):
                flags.discard("long_duration")
                flags.add("duration_segment_relay")
                req = (
                    "长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。"
                )
                if req not in route.get("prompt_requirements", []):
                    route.setdefault("prompt_requirements", []).append(req)
            else:
                flags.add("long_duration")
                flags.discard("duration_segment_relay")
        else:
            route.pop("duration_segment_relay", None)
            flags.discard("duration_segment_relay")
        if not (routing_mode == "fixed_default" and not (route.get("fallback_backends") or [])):
            route["fallback_backends"] = duration_safe_fallbacks(
                primary,
                route.get("fallback_backends") or [],
                duration_for_backend_selection(route),
                native_audio_policy=str(route.get("native_audio_policy") or ""),
                anchor_contract=route["anchor_consumption"],
                video_channel=video_channel,
            )
        route["motion_control"] = motion_control_contract(clip, clip_id, shot_type, primary, episode)
        route["quality_tier"] = quality_tier_for_clip(shot_type, flags, primary)
        mref = motion_reference_plan(shot_type, primary)
        route["motion_reference"] = mref
        if mref.get("applicable"):
            flags.add("motion_reference_candidate")
            note = mref.get("note")
            if note and note not in route.get("rationale", []):
                route.setdefault("rationale", []).append(note)
            req = (
                "若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，"
                "锁运镜节奏；首条镜无前序参考则跳过。"
            )
            if req not in route.get("prompt_requirements", []):
                route.setdefault("prompt_requirements", []).append(req)
        else:
            flags.discard("motion_reference_candidate")
        route["risk_flags"] = sorted(flags)
        route["urgency_tier"] = urgency_tier
        if needs_identity_preservation_plan(route):
            route["identity_preservation_plan"] = identity_preservation_plan(route)
        else:
            route.pop("identity_preservation_plan", None)
        route["execution_recipe"] = execution_recipe_for_route(route, clip, video_channel=video_channel)
        # Capability routing and local executability are deliberately separate facts.
        # A model may be the right creative primary while this machine still needs a
        # manual handoff or a project-registered v2 wrapper.  Never claim automation
        # merely because the static model profile knows the capability.
        route["execution_adapter"] = video_execution_status(
            root or Path("."),
            route.get("primary_backend"),
            video_channel,
        )
        route["fallback_execution_adapters"] = [
            video_execution_status(root or Path("."), backend, video_channel)
            for backend in route.get("fallback_backends") or []
        ]
        route["route_executable"] = bool((route.get("execution_adapter") or {}).get("route_executable"))


def route_episode(
    root: Path,
    episode: str,
    *,
    storyboard_path: Optional[Path] = None,
    generated_at: Optional[str] = None,
    baseline: Optional[Dict[str, str]] = None,
    anchor_baseline: bool = True,
) -> Dict[str, Any]:
    settings = load_settings(root)
    routing_mode = routing_mode_from_settings(settings)
    configured_default_backend = project_default_backend(settings)
    default_backend = configured_default_backend
    legacy_default_note = ""
    if routing_mode != "fixed_default" and not video_backend_auto_routable(default_backend):
        default_backend = "seedance"
        legacy_default_note = (
            f"configured default backend {configured_default_backend} is legacy/manual-only; "
            f"auto routing uses {default_backend} instead"
        )
    av_mode = av_mode_from_settings(settings)
    overseas = is_overseas_target(settings)
    has_video_generation_audio_policy = "视频生成音频策略" in settings
    video_generation_audio_policy = video_generation_audio_policy_from_settings(settings)
    native_audio_setting = settings.get("视频原生音轨", "丢弃")
    lip_sync_setting = settings.get("对口型", "关闭")
    if av_mode != "native_av":
        if _is_silent_video_flow(video_generation_audio_policy) and (
            has_video_generation_audio_policy or not str(settings.get("对口型", "")).strip()
        ):
            native_audio_setting = "丢弃"
            lip_sync_setting = "关闭"
        elif _is_lipsync_video_flow(video_generation_audio_policy) and str(lip_sync_setting or "").strip().lower() in LIPSYNC_OFF_VALUES:
            lip_sync_setting = "配音对齐"
        elif _is_ambience_video_flow(video_generation_audio_policy) and "低音量" not in str(native_audio_setting):
            native_audio_setting = "低音量混入环境声"
    video_channel = settings.get("生视频渠道", "")
    fixed_fallback_backends = fixed_fallback_backends_from_settings(settings, default_backend)
    t2v_action = t2v_action_experimental_enabled(settings.get("T2V动作通道", "关闭"))
    storyboard = load_storyboard(root, episode, storyboard_path)
    clips = storyboard.get("clips") or []
    if not isinstance(clips, list):
        raise ValueError("storyboard.json clips must be a list")
    production_sound_plan: Dict[str, Any] = {}
    sound_routes: List[Mapping[str, Any]] = []
    if av_mode == "hybrid":
        try:
            production_sound_plan = build_production_mode_route(root, episode)
            sound_routes = [row for row in production_sound_plan.get("clip_routes") or [] if isinstance(row, Mapping)]
        except Exception as exc:
            production_sound_plan = {
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
                "clip_routes": [],
            }
    failure_counts = load_identity_failure_counts(root, episode)  # E4：identity 反复失败镜升锁
    # ③ 一角一后端亲和（advisory）：读 identity_registry 找已注册原生视频主体的角色，逐镜对账 primary
    registry = {}
    if _load_identity_registry is not None:
        try:
            registry = _load_identity_registry(str(root)) or {}
        except Exception:
            registry = {}
    backend_affinity = build_backend_affinity(registry)
    urgency_tier = urgency_tier_from_settings(settings)  # G8 时效档（成本轴·项目级意图）
    routes: List[Dict[str, Any]] = []
    for i, clip in enumerate(clips, 1):
        sound_route = sound_routes[i - 1] if i - 1 < len(sound_routes) else None
        routes.append(route_clip(
            clip,
            i,
            episode=episode,
            default_backend=default_backend,
            routing_mode=routing_mode,
            native_audio_setting=native_audio_setting,
            lip_sync_setting=lip_sync_setting,
            video_generation_audio_policy=video_generation_audio_policy,
            video_channel=video_channel,
            av_mode=av_mode,
            fixed_fallback_backends=fixed_fallback_backends,
            failure_counts=failure_counts,
            backend_affinity=backend_affinity,
            t2v_action=t2v_action,
            overseas=overseas,
            sound_route=sound_route,
        ))
    plan = {
        "kind": VIDEO_MODEL_ROUTES_KIND,
        "version": 1,
        "root": str(root),
        "episode": episode,
        "routing_mode": routing_mode,
        "production_mode": settings.get("制作模式", "") or PRODUCTION_MODE_DEFAULT,
        "av_mode": av_mode,
        "video_generation_audio_policy": video_generation_audio_policy,
        "urgency_tier": urgency_tier,
        "t2v_action_channel": t2v_action,
        "default_backend": default_backend,
        "configured_default_backend": configured_default_backend,
        "backend_consistency_scope": backend_consistency_scope(),
        "generated_at": generated_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "production_sound_route": {
            "status": production_sound_plan.get("status") if production_sound_plan else "fixed_project_mode",
            "kind": production_sound_plan.get("kind") if production_sound_plan else "",
            "version": production_sound_plan.get("version") if production_sound_plan else None,
            "summary": production_sound_plan.get("summary") if production_sound_plan else {},
        },
        "routes": routes,
    }
    # P0-2 打斗 motion 侧视觉盛宴：把风格自适应「经费在燃烧」指导挂进打斗/法术镜 route（与出图 runner 同源），
    # 让 LLM 撰写的出视频 prompt 拿得到同一份风格自适应文案——治「首帧盛宴、运动平淡」的图↔视频不对称。
    plan["motion_spectacle_guidance_applied"] = apply_motion_spectacle_guidance(
        plan["routes"], clips, _style_text_from_storyboard(storyboard)
    )
    # G8 时效档：项目级意图逐镜留痕，供 dashboard 拆 realtime vs batch 成本账、执行侧消费 batch 通道。
    for _entry in plan["routes"]:
        _entry["urgency_tier"] = urgency_tier
        recipe = _entry.get("execution_recipe")
        if isinstance(recipe, dict):
            recipe["urgency_tier"] = urgency_tier
    # 跨集后端锁：第1集打样落 设定库/model_routes_baseline.json，后续集按 shot_type 锚定同一后端，
    # 防"换集漂到别的后端→同角色跨集风格/质感漂移"。baseline=None 时不锚定（首集或显式跳过）。
    if baseline is None and anchor_baseline:
        baseline = load_baseline(root)
    if baseline:
        plan["baseline_drift"] = apply_baseline(plan, baseline)
        plan["baseline_anchored"] = any(bool(r.get("baseline_anchored")) for r in plan["routes"])
    benchmark = load_spectacle_backend_benchmark(root)
    applied_benchmark = apply_spectacle_backend_benchmark(
        plan["routes"],
        clips,
        benchmark=benchmark,
        episode=episode,
        default_backend=default_backend,
        video_channel=video_channel,
        routing_mode=routing_mode,
    )
    if benchmark:
        plan["spectacle_backend_benchmark"] = {
            "path": str(spectacle_backend_benchmark_path(root)),
            "applied": applied_benchmark,
        }
    # 冷启动后端先验：benchmark 未覆盖的奇观类型按动作物理默认排序兜底（仅自动路由·非 fixed_default）。
    applied_prior = apply_spectacle_backend_prior(
        plan["routes"],
        clips,
        benchmark=benchmark,
        default_backend=default_backend,
        routing_mode=routing_mode,
    )
    if applied_prior:
        plan["spectacle_backend_prior"] = {"applied": applied_prior}
    refresh_execution_contracts(
        plan["routes"],
        clips,
        root=root,
        episode=episode,
        video_channel=video_channel,
        urgency_tier=urgency_tier,
        routing_mode=routing_mode,
    )
    # 跨后端英雄镜多版：primary/fallback 全部定稿后再标英雄镜（名场面/开场钩/高潮），costly 选择点默认关闭。
    plan["hero_multi_version"] = apply_hero_multi_version(
        plan["routes"], clips,
        setting=settings.get("英雄镜多版", "关闭"), episode=episode, routing_mode=routing_mode,
    )
    # 多镜单次生成候选组（advisory）：在 primary 全部定稿（含 baseline 锚定）后再扫连续接力镜组。
    plan["multishot_groups"] = annotate_multishot_groups(plan["routes"])
    # 同场景/同角色连续镜 → 推荐改走原生多镜后端（advisory）。传项目 roster；roster 内无多镜后端时
    # 仍给规范候选但标 roster_switch_required（换后端须整项目统一·勿混用，由用户定夺）。
    roster = [default_backend, *(fixed_fallback_backends or [])]
    plan["multishot_reroute_recommendations"] = recommend_multishot_reroute(plan["routes"], roster)
    execution_states: Dict[str, int] = {}
    for _route in plan["routes"]:
        _state = str((_route.get("execution_adapter") or {}).get("state") or "unknown")
        execution_states[_state] = execution_states.get(_state, 0) + 1
    plan["execution_summary"] = {
        "adapter_version": 2,
        "states": execution_states,
        "automated_ready": sum(1 for _route in plan["routes"] if (_route.get("execution_adapter") or {}).get("automated")),
        "manual_or_unavailable": sum(1 for _route in plan["routes"] if not (_route.get("execution_adapter") or {}).get("automated")),
        "rule": "model capability does not imply local automation; use the per-route execution_adapter state",
    }
    plan["policy_lattice"] = policy_lattice_document()
    for _entry in plan["routes"]:
        _entry["policy_resolution"] = route_policy_resolution(
            _entry,
            {
                "routing_mode": routing_mode,
                "av_mode": av_mode,
                "urgency_tier": urgency_tier,
            },
        )
    if legacy_default_note:
        plan["routing_notes"] = [legacy_default_note]
    return plan


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 视频模型路由",
        "",
        f"- episode: {plan.get('episode')}",
        f"- routing_mode: {plan.get('routing_mode')}",
        f"- production_mode: {plan.get('production_mode')} (av_mode={plan.get('av_mode')})",
        f"- default_backend: {plan.get('default_backend')}",
        f"- execution_adapter_v2: {(plan.get('execution_summary') or {}).get('states', {})}",
        f"- generated_at: {plan.get('generated_at')}",
        "",
        "## 本集模型路由表",
        "",
        "| Clip | characters | shot_type | primary | fallback | mode | 时间基准 | 声音策略 | 表演轨 | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for route in plan.get("routes", []):
        fallback = ", ".join(route.get("fallback_backends", []))
        flags = ", ".join(route.get("risk_flags", [])) or "-"
        motion = route.get("motion_control") or {}
        motion_level = motion.get("level", "-") if isinstance(motion, Mapping) else "-"
        anchor_plan = route.get("anchor_consumption") or {}
        frame_mode = anchor_plan.get("consumption_mode", "-") if isinstance(anchor_plan, Mapping) else "-"
        characters = ", ".join(
            (str(c.get("character_id") or c.get("raw") or "") + (f"/{c.get('form')}" if c.get("form") else ""))
            for c in route.get("clip_characters", []) if isinstance(c, Mapping)
        ) or "-"
        policy = route.get("policy_resolution") if isinstance(route.get("policy_resolution"), Mapping) else {}
        lines.append(
            "| {clip} | {characters} | {shot} | {primary} | {fallback} | {mode} | {timing} | {strategy} | {track} | {tier} | {frame_mode} | {audio} | {identity} | {motion} | {policy} | {flags} | {degrade} |".format(
                clip=route.get("clip_id", ""),
                characters=characters.replace("|", "/"),
                shot=route.get("shot_type", ""),
                primary=route.get("primary_backend", ""),
                fallback=fallback,
                mode=route.get("mode", ""),
                timing=route.get("timing_basis", "-"),
                strategy=route.get("audio_strategy", "-"),
                track=route.get("performance_track_status", "-"),
                tier=route.get("quality_tier", "-"),
                frame_mode=frame_mode,
                audio=route.get("native_audio_policy", ""),
                identity=route.get("identity_requirement", ""),
                motion=motion_level,
                policy=policy.get("winner", "-"),
                flags=flags,
                degrade=str(route.get("degrade_plan", "")).replace("|", "/"),
            )
        )
    groups = plan.get("multishot_groups") or []
    if groups:
        lines.extend(["", "## 多镜单次生成候选组（advisory·可选一次 co-generate 消缝）", ""])
        for g in groups:
            lines.append(
                f"- {g.get('group_id')}（{g.get('backend')}）: {', '.join(g.get('members', []))} "
                "— 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。")
    lines.extend(["", "## 逐 Clip 路由理由", ""])
    for route in plan.get("routes", []):
        lines.append(f"### {route.get('clip_id')} — {route.get('shot_type')}")
        chars = route.get("clip_characters") if isinstance(route.get("clip_characters"), list) else []
        if chars:
            lines.append("- characters: " + ", ".join(
                str(c.get("character_id") or c.get("raw") or "") + (f"/{c.get('form')}" if c.get("form") else "")
                for c in chars if isinstance(c, Mapping)
            ))
        lines.append(f"- primary: {route.get('primary_backend')}")
        lines.append(f"- fallback: {', '.join(route.get('fallback_backends', []))}")
        lines.append(f"- mode: {route.get('mode')}")
        if route.get("audio_strategy"):
            lines.append(
                f"- sound: timing_basis={route.get('timing_basis')} / audio_strategy={route.get('audio_strategy')} / "
                f"performance_track={route.get('performance_track_status')} / voice_lock={route.get('voice_lock_status')}"
            )
            lines.append(
                f"- final_sound: stage={route.get('final_voice_stage')} / post_lipsync_required={route.get('post_lipsync_required')} / "
                f"base_video_only={route.get('base_video_only')}"
            )
        lines.append(f"- quality_tier: {route.get('quality_tier', '-')}")
        execution = route.get("execution_adapter") if isinstance(route.get("execution_adapter"), Mapping) else {}
        if execution:
            lines.append(
                f"- execution_adapter_v2: state={execution.get('state')} "
                f"adapter={execution.get('adapter_id') or '-'} automated={execution.get('automated')}"
            )
        mref = route.get("motion_reference") or {}
        if isinstance(mref, Mapping) and mref.get("applicable"):
            lines.append("- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)")
        msg = route.get("multishot_candidate") or {}
        if isinstance(msg, Mapping) and msg.get("group_id"):
            lines.append(f"- multishot_candidate: {msg.get('group_id')} {msg.get('members')}")
        lines.append(f"- identity: {route.get('identity_requirement')}")
        anchor_plan = route.get("anchor_consumption") or {}
        if isinstance(anchor_plan, Mapping):
            lines.append(
                f"- frame_consumption: {anchor_plan.get('consumption_mode')} "
                f"(execution={anchor_plan.get('execution_backend')}, anchors={anchor_plan.get('anchor_count')}, "
                f"need_end={anchor_plan.get('need_end')})"
            )
        motion = route.get("motion_control") or {}
        if isinstance(motion, Mapping):
            lines.append(f"- motion_control: {motion.get('level')} (manifest={motion.get('manifest_path') or '-'})")
            if motion.get("required_inputs"):
                lines.append(f"- motion_control_required_inputs: {', '.join(motion.get('required_inputs', []))}")
        recipe = route.get("execution_recipe") or {}
        if isinstance(recipe, Mapping):
            frame_inputs = recipe.get("frame_inputs") if isinstance(recipe.get("frame_inputs"), Mapping) else {}
            refs = recipe.get("reference_inputs") if isinstance(recipe.get("reference_inputs"), Mapping) else {}
            controls = recipe.get("control_inputs") if isinstance(recipe.get("control_inputs"), Mapping) else {}
            lines.append(
                "- execution_recipe: "
                f"execution={recipe.get('execution_backend')}; "
                f"frames={frame_inputs.get('consumption_mode')} anchors={frame_inputs.get('mid_anchors')}; "
                f"refs_max={refs.get('max_reference_images')}; "
                f"control_manifest={controls.get('manifest_path') or '-'}"
            )
        choreography = route.get("action_choreography") or {}
        if isinstance(choreography, Mapping) and choreography.get("required"):
            lines.append(f"- action_choreography: {choreography.get('beat_model')} (gate={choreography.get('gate_policy')})")
            fields = choreography.get("required_fields") or []
            if fields:
                lines.append(f"- action_choreography_required_fields: {', '.join(str(x) for x in fields)}")
        policy = route.get("policy_resolution") if isinstance(route.get("policy_resolution"), Mapping) else {}
        if policy:
            lines.append(f"- policy_resolution: winner={policy.get('winner')} signoff_required={policy.get('signoff_required')}")
            for conflict in policy.get("conflicts") or []:
                if isinstance(conflict, Mapping):
                    lines.append(
                        f"  - conflict {conflict.get('surface')}: "
                        f"{', '.join(str(x) for x in conflict.get('policies') or [])} -> {conflict.get('winner')}"
                    )
        lines.append("- rationale:")
        for item in route.get("rationale", []):
            lines.append(f"  - {item}")
        lines.append("- prompt_requirements:")
        for item in route.get("prompt_requirements", []):
            lines.append(f"  - {item}")
        lines.append(f"- degrade_plan: {route.get('degrade_plan')}")
        lines.append("")
    return "\n".join(lines)


MODEL_ROUTES_BASELINE_KIND = "n2d_model_routes_baseline"


def baseline_path(root: Path) -> Path:
    """跨集后端基线落 设定库/（与 voicemap/global_style 同级的跨集真值源）。"""
    return Path(root) / "设定库" / "model_routes_baseline.json"


def load_baseline(root: Path) -> Optional[Dict[str, str]]:
    """读 shot_type → primary_backend 基线；无则 None（首集尚未打样）。"""
    p = baseline_path(root)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    table = data.get("shot_type_backends") if isinstance(data, Mapping) else None
    return {str(k): str(v) for k, v in table.items()} if isinstance(table, Mapping) else None


def build_baseline(plan: Mapping[str, Any]) -> Dict[str, str]:
    """从一集 routes 抽 shot_type → 最常用 primary_backend（第1集打样写基线）。"""
    counts: Dict[str, Dict[str, int]] = {}
    for route in plan.get("routes", []) or []:
        st, pb = str(route.get("shot_type") or ""), str(route.get("primary_backend") or "")
        if not (st and pb):
            continue
        counts.setdefault(st, {})[pb] = counts.setdefault(st, {}).get(pb, 0) + 1
    return {st: max(by.items(), key=lambda kv: kv[1])[0] for st, by in counts.items()}


def apply_baseline(plan: Dict[str, Any], baseline: Mapping[str, str]) -> List[Dict[str, Any]]:
    """按跨集基线锚定 primary；更高优先级锁定只记录 deferred，不覆盖。"""
    drift: List[Dict[str, Any]] = []
    for route in plan.get("routes", []) or []:
        st = str(route.get("shot_type") or "")
        want = baseline.get(st)
        cur = str(route.get("primary_backend") or "")
        if not want:
            continue
        if want == cur:
            if plan.get("routing_mode") != "fixed_default":
                route["baseline_anchored"] = True
            continue
        if plan.get("routing_mode") == "fixed_default":
            route["baseline_deferred"] = {
                "wanted_backend": want,
                "current_primary": cur,
                "reason": "fixed_default",
            }
            route["risk_flags"] = sorted(set(route.get("risk_flags", [])) | {"baseline_deferred_by_fixed_mode"})
            route.setdefault("rationale", []).append(
                f"跨集基线要求「{want}」，但项目为固定生视频模型，保持用户固定后端「{cur}」。"
            )
            drift.append({"clip_id": route.get("clip_id"), "shot_type": st, "was": cur, "now": cur,
                          "skipped": want, "reason": "fixed_default"})
            continue
        locked = normalize_backend(str(route.get("locked_backend") or ""), default="")
        if locked and normalize_backend(str(want), default="") != locked:
            route["baseline_deferred"] = {
                "wanted_backend": want,
                "current_primary": cur,
                "locked_backend": locked,
                "reason": "identity_affinity_locked_backend",
            }
            route["risk_flags"] = sorted(set(route.get("risk_flags", [])) | {"baseline_deferred_by_locked_backend"})
            route.setdefault("rationale", []).append(
                f"跨集基线要求「{want}」，但角色后端亲和已锁「{locked}」；保持身份一致，基线不覆盖。"
            )
            drift.append({"clip_id": route.get("clip_id"), "shot_type": st, "was": cur, "now": cur,
                          "skipped": want, "reason": "identity_affinity_locked_backend"})
            continue
        if not video_backend_auto_routable(want):
            route["baseline_legacy_skipped"] = True
            route["risk_flags"] = sorted(set(route.get("risk_flags", [])) | {"baseline_legacy_backend_skipped"})
            route.setdefault("rationale", []).append(
                f"跨集基线要求 legacy/manual-only 后端「{want}」，已跳过自动锚定；需要人工确认后再固定。"
            )
            drift.append({"clip_id": route.get("clip_id"), "shot_type": st, "was": cur, "now": cur,
                          "skipped": want, "reason": "legacy_manual_backend"})
            continue
        fb = [b for b in (route.get("fallback_backends") or []) if b != want]
        if cur:
            fb = [cur] + [b for b in fb if b != cur]
        route["fallback_backends"] = fb[:3]
        route["primary_backend"] = want
        old_plan = route.get("anchor_consumption") if isinstance(route.get("anchor_consumption"), Mapping) else {}
        route["frame_control"] = video_backend_frame_control(want)
        route["anchor_consumption"] = anchor_consumption_plan(
            want,
            anchor_count=int(old_plan.get("anchor_count") or 0),
            need_end=bool(old_plan.get("need_end")),
        )
        route["baseline_anchored"] = True
        drift.append({"clip_id": route.get("clip_id"), "shot_type": st, "was": cur, "now": want})
    return drift


def write_baseline(plan: Mapping[str, Any], root: Path) -> Path:
    table = build_baseline(plan)
    p = baseline_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "kind": MODEL_ROUTES_BASELINE_KIND,
        "source_episode": plan.get("episode"),
        "shot_type_backends": table,
        "generated_at": plan.get("generated_at"),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def write_plan(plan: Mapping[str, Any], root: Path, episode: str) -> Dict[str, Path]:
    out_dir = root / "出视频" / episode / "prompt"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "video_model_routes.json"
    md_path = out_dir / "video_model_routes.md"
    policy_path = root / "生产数据" / "consistency_policy_lattice.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    policy_path.write_text(json.dumps(plan.get("policy_lattice") or policy_lattice_document(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path, "policy_lattice": policy_path}


def main() -> int:
    parser = argparse.ArgumentParser(description="Route n2d video clips to suitable model backends.")
    parser.add_argument("root", help="作品根, e.g. 创作区/制漫剧/剧名")
    parser.add_argument("episode", help="第N集")
    parser.add_argument("--storyboard", help="override storyboard.json path")
    parser.add_argument("--write", action="store_true", help="write video_model_routes.json/md under 出视频/第N集/prompt")
    parser.add_argument("--markdown", action="store_true", help="print markdown instead of JSON")
    parser.add_argument("--write-baseline", action="store_true",
                        help="把本集 shot_type→后端 写成 设定库/model_routes_baseline.json（第1集打样锁后端，跨集锚定）")
    parser.add_argument("--no-anchor", action="store_true",
                        help="不按 model_routes_baseline 锚定本集 primary（默认有基线就锚定，保跨集后端一致）")
    ns = parser.parse_args()

    root = Path(ns.root)
    storyboard = Path(ns.storyboard) if ns.storyboard else None
    # --write-baseline 用本集"自然路由"(不锚定)抽基线；否则有基线就锚定
    plan = route_episode(root, ns.episode, storyboard_path=storyboard,
                         anchor_baseline=not (ns.no_anchor or ns.write_baseline))
    if ns.write_baseline:
        bp = write_baseline(plan, root)
        print(f"wrote baseline {bp}")
    drift = plan.get("baseline_drift") or []
    if drift:
        print(f"⚠️ 后端跨集漂移/延后裁决：{len(drift)} 个 clip 的 shot_type 自然路由与基线不符", file=sys.stderr)
        for d in drift[:8]:
            note = f" skipped={d.get('skipped')} reason={d.get('reason')}" if d.get("skipped") else ""
            print(f"  - {d['clip_id']}({d['shot_type']}): {d['was']} → {d['now']}{note}", file=sys.stderr)
    if ns.write:
        paths = write_plan(plan, root, ns.episode)
        print(f"wrote {paths['json']}")
        print(f"wrote {paths['markdown']}")
        print(f"wrote {paths['policy_lattice']}")
    else:
        if ns.markdown:
            print(render_markdown(plan))
        else:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
