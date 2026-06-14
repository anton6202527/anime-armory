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

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  与 gate 共用的单一真值源
    MOTION_CONTROL_REQUIRED_SHOT_TYPES,  # 高危接触镜头集
    SHOT_TYPE_KEYWORDS,                  # 镜头类型判定关键词（与 gate 专项模板检测同源）
    VIDEO_MODEL_ROUTES_KIND,             # 路由产物 kind
    is_native_av_mode,                   # 原生音画判定（与 n2d_settings/gate 同源）
)
from n2d_platform_profiles import (  # noqa: E402  视频后端档案单一真值源
    LIPSYNC_AUDIO_REF_BACKENDS,
    MOTION_CONTROL_PROFILES,
    NATIVE_AV_BACKENDS,
    VIDEO_BACKEND_LABELS,
    VIDEO_BACKEND_MAX_SECONDS,
    normalize_video_backend,
    video_backend_max_seconds,
)
from n2d_settings import load_settings as _load_settings_md  # noqa: E402  _设置.md 解析单一真值源


BACKEND_LABELS = VIDEO_BACKEND_LABELS
BACKEND_MAX_SECONDS = VIDEO_BACKEND_MAX_SECONDS

# 运镜/运动控制能力档与「音频参考口型」后端集的单一真值源已上移到 n2d_platform_profiles
# （与 frame_control 同属 CATALOG_VERIFIED 带日期快照 + freshness 注册，C2 易变候选清单要求）。
# 这里保留本地别名以兼容既有 .get() 调用点；运动控制 vs 身份绑定（n2d_contract.IDENTITY_VIDEO_ADAPTERS）
# 仍是两个刻意不合并的关注点，身份类能力词若在契约改名，platform_profiles 里的同名字串要同步。
BACKEND_MOTION_CONTROL = MOTION_CONTROL_PROFILES

SPEECH_SHOT_TYPES = {"dialogue_shot_reverse", "dialogue_closeup"}

# 关闭对口型的 _设置.md 值；其余值（开启/配音对齐/原生口型/on…）视为 opt-in。
LIPSYNC_OFF_VALUES = {"", "关闭", "否", "off", "no", "none", "disable", "disabled"}
FALLBACK_OFF_VALUES = {"", "无", "不使用", "关闭", "否", "off", "no", "none", "disable", "disabled"}

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


def _has_any(text: str, words: Iterable[str]) -> bool:
    lower = text.lower()
    return any(w.lower() in lower for w in words)


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
    if any(_value_has_named_character(clip.get(k)) for k in CHARACTER_FIELD_KEYS):
        return True
    template = str(clip.get("template") or "").strip()
    if template in COMPLEX_TEMPLATES:
        return True
    if re.search(r"\bCHAR_[A-Za-z0-9_]+(?:/[^\s，；、`]+)?\b", text):
        return True
    return _has_any(text, ("角色", "人物", "主角", "脸", "发型", "服装", "character", "face"))


def clip_has_mouth_visible(clip: Mapping[str, Any]) -> bool:
    text = _clip_text(clip)
    return _has_any(text, ("口型", "嘴", "说话", "台词", "正脸", "mouth", "lip-sync", "speaking", "dialogue"))


def clip_named_character_count(clip: Mapping[str, Any]) -> int:
    """同框具名角色数（从 template_contract.character_slots / face_priority 取）。
    ≥5 时路由偏好 Sora（2026 行业：Sora 2 对 5+ 角色同框最稳，超 Kling 2-3 张脸上限）。"""
    tc = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    slots = tc.get("character_slots")
    if isinstance(slots, Mapping):
        return len(slots)
    for key in ("face_priority", "character_slots"):
        val = tc.get(key)
        if isinstance(val, (list, tuple)):
            return len(val)
    return 0


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


def backend_supports_dual_keyframe(backend: str) -> bool:
    """该后端是否支持双关键帧（首尾硬约束插值）。纯函数·可测。"""
    caps = BACKEND_MOTION_CONTROL.get(normalize_backend(backend), {}).get("capabilities", [])
    return bool(DUAL_KEYFRAME_CAPS.intersection(caps))


def is_relay_clip(clip: Mapping[str, Any]) -> bool:
    """该 clip 是否接力/无缝转场镜（尾帧接力，接缝应近乎同构图）。纯函数·可测。"""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    if clip.get("relay") or cont.get("relay"):
        return True
    # 画板 schema 的规范字段是 need_endframe（无下划线）；need_end_frame 仅作旧别名兜底。
    if any(clip.get(k) or cont.get(k) for k in ("need_endframe", "need_end_frame")):
        return True
    trans = str(clip.get("transition") or cont.get("transition") or "").strip().lower()
    return trans in RELAY_TRANSITIONS


def seam_relay_plan(clip: Mapping[str, Any], primary: str,
                    fallback_backends: List[str]) -> Dict[str, Any]:
    """接力镜的双关键帧路由计划。纯函数·可测：返回 seam_relay 子表（非接力镜也返回 is_relay=False）。

    primary 已支持双关键帧 → seam_guaranteed=True（接缝结构保证）；不支持 → 从 fallback 里挑一个
    支持的当 dual_keyframe_fallback，提示改用它把尾帧作硬约束。"""
    relay = is_relay_clip(clip)
    prim_ok = backend_supports_dual_keyframe(primary)
    plan: Dict[str, Any] = {"is_relay": relay, "primary_supports_dual_keyframe": prim_ok}
    if not relay:
        return plan
    plan["boundary_frame_shared"] = True  # 上一镜尾帧 = 本镜首帧（同一张授权图），两镜复用省一次出图
    plan["seam_guaranteed"] = prim_ok
    if not prim_ok:
        plan["dual_keyframe_fallback"] = next(
            (b for b in fallback_backends if backend_supports_dual_keyframe(b)), None)
    return plan


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
    fixed_fallback_backends: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if routing_mode == "fixed_default":
        route = _route_fixed(clip, shot_type, default_backend, fixed_fallback_backends)
        if av_mode == "native_av" and _is_speech_shot(clip, shot_type):
            route["rationale"].append("制作模式=原生音画，但视频模型路由=固定生视频模型；固定选择优先，不自动切 native_speech 后端")
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
        # 5+ 同框 或 群像(ensemble) → Sora primary（行业：Sora 2 对 5+ 角色同框最稳）；
        # 2-3 具名脸的常见同框仍走 Kling（Character ID/主体库 + 运动笔刷锁站位）。
        big_ensemble = shot_type == "ensemble_blocking" or clip_named_character_count(clip) >= 5
        mp_primary = "sora" if big_ensemble else "kling"
        mp_fallback = [b for b in (["kling", "seedance", default_backend] if big_ensemble
                                   else ["seedance", default_backend]) if b != mp_primary]
        mp_rationale = [
            "multi-person staging needs reference controls and stable screen direction",
            "single-backend generic generation often swaps faces or screen positions",
        ]
        if big_ensemble:
            mp_rationale.append("5+ 同框/群像：Sora 2 多角色一致性最强，超 Kling 2-3 张脸上限；仍不稳则按 degrade_plan 拆组")
        route = {
            "primary_backend": mp_primary,
            "fallback_backends": mp_fallback,
            "mode": "frames2video",
            "native_audio_policy": "none",
            "identity_requirement": "character_id_or_reference_group",
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
    fixed_fallback_backends: Optional[List[str]] = None,
    failure_counts: Optional[Dict[str, int]] = None,
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
        fixed_fallback_backends=fixed_fallback_backends,
    )
    primary = normalize_backend(route["primary_backend"], default_backend)
    clip_id = make_clip_id(clip, index)
    risk_flags = risk_flags_for_clip(clip, shot_type, primary)
    if route.get("native_audio_policy") == "native_speech":
        risk_flags = sorted(set(risk_flags) | {"native_speech"})
    seam_relay = seam_relay_plan(clip, primary, route["fallback_backends"])
    rationale = list(route["rationale"])
    prompt_requirements = list(route["prompt_requirements"])
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
        "native_audio_policy": route["native_audio_policy"],
        "identity_requirement": route["identity_requirement"],
        "max_clip_seconds": video_backend_max_seconds(primary),
        "risk_flags": risk_flags,
        "seam_relay": seam_relay,
        "motion_control": motion_control_contract(clip, clip_id, shot_type, primary, episode),
        "rationale": rationale,
        "prompt_requirements": prompt_requirements,
        "degrade_plan": route["degrade_plan"],
    }
    fc = (failure_counts or {}).get(clip_id, 0)
    if fc:  # E4：本镜 identity 反复失败 → 升锁（含固定后端模式只收紧不换厂）
        entry = escalate_identity_for_failures(entry, fc, fixed_mode=(routing_mode == "fixed_default"))
    return entry


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
    default_backend = project_default_backend(settings)
    routing_mode = routing_mode_from_settings(settings)
    av_mode = av_mode_from_settings(settings)
    native_audio_setting = settings.get("视频原生音轨", "丢弃")
    lip_sync_setting = settings.get("对口型", "关闭")
    fixed_fallback_backends = fixed_fallback_backends_from_settings(settings, default_backend)
    storyboard = load_storyboard(root, episode, storyboard_path)
    clips = storyboard.get("clips") or []
    if not isinstance(clips, list):
        raise ValueError("storyboard.json clips must be a list")
    failure_counts = load_identity_failure_counts(root, episode)  # E4：identity 反复失败镜升锁
    plan = {
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
                fixed_fallback_backends=fixed_fallback_backends,
                failure_counts=failure_counts,
            )
            for i, clip in enumerate(clips, 1)
        ],
    }
    # 跨集后端锁：第1集打样落 设定库/model_routes_baseline.json，后续集按 shot_type 锚定同一后端，
    # 防"换集漂到别的后端→同角色跨集风格/质感漂移"。baseline=None 时不锚定（首集或显式跳过）。
    if baseline is None and anchor_baseline:
        baseline = load_baseline(root)
    if baseline:
        plan["baseline_drift"] = apply_baseline(plan, baseline)
        plan["baseline_anchored"] = True
    return plan


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
    """按基线锚定每条 route 的 primary（baseline 胜，原 primary 降为 fallback 首项保留）；返回漂移清单。"""
    drift: List[Dict[str, Any]] = []
    for route in plan.get("routes", []) or []:
        st = str(route.get("shot_type") or "")
        want = baseline.get(st)
        cur = str(route.get("primary_backend") or "")
        if not want or want == cur:
            continue
        fb = [b for b in (route.get("fallback_backends") or []) if b != want]
        if cur:
            fb = [cur] + [b for b in fb if b != cur]
        route["fallback_backends"] = fb[:3]
        route["primary_backend"] = want
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
        print(f"⚠️ 后端跨集漂移：{len(drift)} 个 clip 的 shot_type 自然路由与基线不符，已按基线锚定（原后端降为 fallback）", file=sys.stderr)
        for d in drift[:8]:
            print(f"  - {d['clip_id']}({d['shot_type']}): {d['was']} → {d['now']}", file=sys.stderr)
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
