#!/usr/bin/env python3
"""Backend-aware compiler for n2d video submit prompts.

The production contract is intentionally richer than the text sent to a video
model.  This module is the boundary between those two layers: callers pass a
canonical clip contract, and the compiler emits a concise, backend-specific
submit prompt plus request-side metadata.  It never mutates the source
contract and never hides missing deterministic requirements behind prose.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

from n2d_platform_profiles import quantize_video_duration


KIND = "n2d_compiled_video_prompt"
VERSION = 2
PROFILE_VERSION = "2026-07-10.2"
COMPILED_HEADING = "### 后端编译提交 prompt"

_RUNWAY_NEGATIVE_RE = re.compile(
    r"\b(?:no|not|never|avoid|without|don't|do not)\b|不要|禁止|不得|避免|无文字|无水印",
    re.IGNORECASE,
)
_NATIVE_SPEECH_VALUES = {"native_speech", "native_av"}
_CJK_RE = re.compile(r"[\u3400-\u9fff]")


def _one_line(value: Any) -> str:
    if isinstance(value, str):
        text = value
    elif isinstance(value, Mapping):
        text = "；".join(f"{k}={_one_line(v)}" for k, v in value.items() if _one_line(v))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        text = "、".join(_one_line(v) for v in value if _one_line(v))
    else:
        text = str(value or "")
    return re.sub(r"\s+", " ", text).strip(" ；;,，。")


def _compact(value: Any, limit: int) -> str:
    text = _one_line(value)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit("；", 1)[0].rsplit("。", 1)[0].rsplit(",", 1)[0]
    return (cut or text[:limit]).rstrip(" ；;,，。") + "…"


def normalize_backend(value: Any) -> str:
    raw = _one_line(value).lower()
    aliases = (
        (("runway", "gen-4", "gen4"), "runway"),
        (("veo", "gemini"), "veo"),
        (("luma", "dream machine"), "luma"),
        (("seedance",), "seedance"),
        (("dreamina", "jimeng", "即梦"), "dreamina"),
        (("kling", "可灵"), "kling"),
        (("wan", "万相"), "wan"),
        (("pika",), "pika"),
    )
    for names, canonical in aliases:
        if any(name in raw for name in names):
            return canonical
    return raw or "generic"


def backend_profile(value: Any) -> Dict[str, Any]:
    backend = normalize_backend(value)
    if backend == "runway":
        return {
            "name": "runway_motion_positive",
            "backend": backend,
            "language": "en",
            "negative_strategy": "positive_only",
            "advisory_char_limit": 700,
        }
    if backend == "veo":
        return {
            "name": "veo_cinematography",
            "backend": backend,
            "language": "en",
            "negative_strategy": "separate_element_list",
            "advisory_char_limit": 900,
        }
    if backend in {"luma", "pika"}:
        return {
            "name": "english_motion_keyframe",
            "backend": backend,
            "language": "en",
            "negative_strategy": "separate",
            "advisory_char_limit": 800,
        }
    return {
        "name": "zh_motion_first",
        "backend": backend,
        "language": "zh",
        "negative_strategy": "compact_inline_guard",
        "advisory_char_limit": 600,
    }


def _source_hash(contract: Mapping[str, Any]) -> str:
    raw = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_positive_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0


def compile_duration_plan(contract: Mapping[str, Any], backend: Any = None) -> Dict[str, Any]:
    """Keep narrative, edit and backend-generation clocks separate."""
    story_span = _as_positive_float(
        contract.get("story_span_sec") or contract.get("duration")
    )
    edit_target = _as_positive_float(
        contract.get("edit_target_sec") or story_span
    )
    target = backend or contract.get("backend") or contract.get("primary_backend")
    plan = quantize_video_duration(
        edit_target,
        target,
        contract.get("channel"),
        model_version=contract.get("model_version"),
        mode=contract.get("backend_mode") or contract.get("frame_strategy") or contract.get("mode"),
    )
    usable_end = float((plan.get("usable_window") or [0.0, edit_target])[1] or 0.0)
    hold = min(0.5, max(0.2, usable_end * 0.15)) if usable_end else 0.0
    action_start = min(0.25, usable_end * 0.08) if usable_end else 0.0
    action_end = max(action_start, usable_end - hold)
    plan.update({
        "story_span_sec": round(story_span, 3),
        "edit_target_sec": round(edit_target, 3),
        "action_start_sec": round(action_start, 3),
        "action_end_sec": round(action_end, 3),
        "hold_end_sec": round(usable_end, 3),
    })
    return plan


def _timing_sentence(plan: Mapping[str, Any], language: str) -> str:
    start = _as_positive_float(plan.get("action_start_sec"))
    end = _as_positive_float(plan.get("action_end_sec"))
    hold_end = _as_positive_float(plan.get("hold_end_sec"))
    request = _as_positive_float(plan.get("backend_request_sec"))
    if not hold_end:
        return ""
    if language == "en":
        text = (
            f"Timing: perform the primary action from {start:.2f}s to {end:.2f}s; "
            f"hold the final state through {hold_end:.2f}s."
        )
        if request > hold_end + 0.05:
            text += f" From {hold_end:.2f}s to {request:.2f}s, keep only the final hold for trimming."
        return text
    text = f"时间：{start:.2f}-{end:.2f}秒完成主动作，持续保持落幅到{hold_end:.2f}秒。"
    if request > hold_end + 0.05:
        text += f"{hold_end:.2f}-{request:.2f}秒只保持落幅供后期裁切，不开始新动作。"
    return text


def _mode_opening(mode: str, language: str) -> str:
    low = mode.lower()
    if language == "en":
        if low in {"text2video", "t2v"}:
            return "Create the shot"
        if "frame" in low or low in {"frames2video", "first_last_frame"}:
            return "Animate continuously from the first keyframe to the final keyframe"
        if "multi" in low:
            return "Animate through the supplied keyframes in order"
        return "Animate the supplied first frame"
    if low in {"text2video", "t2v"}:
        return "生成本镜"
    if "frame" in low or low in {"frames2video", "first_last_frame"}:
        return "从首帧连续运动到尾帧"
    if "multi" in low:
        return "按已提交关键帧顺序连续运动"
    return "以已提交首帧为视觉真值"


def _positive_guard(language: str) -> str:
    if language == "en":
        return (
            "Keep the registered subjects, identity, wardrobe, composition and lighting stable; "
            "the frame stays clean and free of added text or watermarks."
        )
    return "仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。"


def _audio_sentence(policy: str, mode: str, language: str) -> str:
    native = policy.lower() == "native_speech" or mode.lower() == "native_av"
    ambience = policy.lower() in {"ambience", "native_sfx", "environment_sfx"}
    if language == "en":
        if native:
            return "Generate only the registered on-screen dialogue with synchronized lip movement; add no narration or extra lines."
        if ambience:
            return "Generate only low-risk ambient and action sound; spoken voice remains absent."
        return ""
    if native:
        return "仅同步生成本镜已登记的画内台词与口型，不添加旁白或额外台词。"
    if ambience:
        return "只生成低风险环境声与动作音效，不生成人声。"
    return ""


def compile_video_prompt(contract: Mapping[str, Any], backend: Any = None) -> Dict[str, Any]:
    """Compile one canonical clip contract into one submit prompt payload."""
    target = backend or contract.get("backend") or contract.get("primary_backend")
    profile = backend_profile(target)
    preferred_language = str(profile["language"])
    mode = _one_line(contract.get("mode")) or "image2video"
    english_profile = preferred_language == "en"
    action = _compact(
        contract.get("primary_action_en") if english_profile and contract.get("primary_action_en") else
        contract.get("primary_action") or contract.get("action"),
        240,
    )
    camera = _compact(
        contract.get("camera_motion_en") if english_profile and contract.get("camera_motion_en") else
        contract.get("camera_motion"),
        120,
    )
    environment = _compact(
        contract.get("environment_motion_en") if english_profile and contract.get("environment_motion_en") else
        contract.get("environment_motion"),
        120,
    )
    end_state = _compact(
        contract.get("end_state_en") if english_profile and contract.get("end_state_en") else
        contract.get("end_state"),
        140,
    )
    subject = _compact(contract.get("subject_en") if english_profile and contract.get("subject_en") else contract.get("subject"), 100)
    scene = _compact(contract.get("scene_en") if english_profile and contract.get("scene_en") else contract.get("scene"), 120)
    rhythm = _compact(contract.get("rhythm_en") if english_profile and contract.get("rhythm_en") else contract.get("rhythm"), 100)
    language = "mixed" if english_profile and _CJK_RE.search(" ".join((action, camera, environment, end_state, subject, scene, rhythm))) else preferred_language
    audio_policy = _one_line(contract.get("native_audio_policy")) or "none"
    frame_strategy = _one_line(contract.get("frame_strategy")) or "first_only"
    opening_mode = (
        "frames2video" if frame_strategy in {"first_last", "split_relay"}
        else "multiframe2video" if frame_strategy == "native_multiframe"
        else mode
    )
    opening = _mode_opening(opening_mode, preferred_language)
    duration_plan = compile_duration_plan(contract, target)

    parts: List[str] = []
    if preferred_language == "en":
        if mode.lower() in {"text2video", "t2v"}:
            setup = ", ".join(piece for piece in (subject, scene) if piece)
            parts.append(f"{opening}: {setup}." if setup else f"{opening}.")
        else:
            parts.append(f"{opening}.")
        if action:
            parts.append(f"Primary action: {action}.")
        if camera:
            parts.append(f"Camera: {camera}.")
        if environment:
            parts.append(f"Environment motion: {environment}.")
        if rhythm:
            parts.append(f"Rhythm: {rhythm}.")
        timing = _timing_sentence(duration_plan, preferred_language)
        if timing:
            parts.append(timing)
        if end_state:
            parts.append(f"End and hold on: {end_state}.")
    else:
        if mode.lower() in {"text2video", "t2v"}:
            setup = "；".join(piece for piece in (subject, scene) if piece)
            parts.append(f"{opening}：{setup}。" if setup else f"{opening}。")
        else:
            parts.append(f"{opening}。")
        if action:
            parts.append(f"主动作：{action}。")
        if camera:
            parts.append(f"镜头：{camera}。")
        if environment:
            parts.append(f"环境响应：{environment}。")
        if rhythm:
            parts.append(f"节奏：{rhythm}。")
        timing = _timing_sentence(duration_plan, preferred_language)
        if timing:
            parts.append(timing)
        if end_state:
            parts.append(f"结尾停稳在：{end_state}。")

    if profile["negative_strategy"] == "compact_inline_guard":
        parts.append(_positive_guard(preferred_language))
    audio_sentence = _audio_sentence(audio_policy, mode, preferred_language)
    if audio_sentence:
        parts.append(audio_sentence)

    must_avoid = [_one_line(v) for v in contract.get("must_avoid") or [] if _one_line(v)]
    negative_prompt = ""
    if profile["negative_strategy"] == "separate_element_list":
        negative_prompt = ", ".join(must_avoid)
    elif profile["negative_strategy"] == "separate":
        negative_prompt = "; ".join(must_avoid)

    prompt = " ".join(part for part in parts if part).strip()
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "clip_id": _one_line(contract.get("clip_id")),
        "backend": profile["backend"],
        "profile": profile["name"],
        "mode": mode,
        "language": language,
        "native_audio_policy": audio_policy,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "frame_strategy": frame_strategy,
        "duration_plan": duration_plan,
        "request_controls": {
            "frame_inputs": list(contract.get("frame_inputs") or []),
            "reference_inputs": list(contract.get("reference_inputs") or []),
            "control_inputs": list(contract.get("control_inputs") or []),
            "audio_inputs": list(contract.get("audio_inputs") or []),
        },
        "source_contract_sha256": _source_hash(contract),
    }
    payload["lint"] = lint_compiled_prompt(payload)
    return payload


def lint_compiled_prompt(payload: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Return deterministic errors and advisory compactness warnings."""
    errors: List[str] = []
    warnings: List[str] = []
    prompt = _one_line(payload.get("prompt"))
    profile = backend_profile(payload.get("backend"))
    mode = _one_line(payload.get("mode")).lower()
    audio_policy = _one_line(payload.get("native_audio_policy")).lower()
    controls_present = isinstance(payload.get("request_controls"), Mapping)
    controls = payload.get("request_controls") if controls_present else {}
    version = int(payload.get("version") or 0)
    duration_plan = payload.get("duration_plan") if isinstance(payload.get("duration_plan"), Mapping) else {}

    if not prompt:
        errors.append("empty_submit_prompt")
    if not re.search(r"Primary action:|主动作：", prompt):
        errors.append("missing_primary_action")
    if not re.search(r"Camera:|镜头：", prompt):
        errors.append("missing_camera_motion")
    if profile["backend"] == "runway" and _RUNWAY_NEGATIVE_RE.search(prompt):
        errors.append("runway_prompt_contains_negative_command")
    if profile["backend"] == "runway" and _one_line(payload.get("negative_prompt")):
        errors.append("runway_negative_prompt_must_be_empty")
    if controls_present and mode not in {"text2video", "t2v"} and not list(controls.get("frame_inputs") or []):
        errors.append("image_conditioned_mode_missing_frame_inputs")
    if (audio_policy == "native_speech" or mode == "native_av") and not re.search(
        r"registered on-screen dialogue|已登记的画内台词", prompt
    ):
        errors.append("native_speech_prompt_missing_registered_dialogue_guard")
    if len(prompt) > int(profile["advisory_char_limit"]):
        warnings.append(
            f"submit_prompt_verbose:{len(prompt)}>{profile['advisory_char_limit']}"
        )
    clause_count = len([p for p in re.split(r"[。；;.!?]+", prompt) if p.strip()])
    if clause_count > 12:
        warnings.append(f"submit_prompt_many_clauses:{clause_count}>12")
    if _one_line(payload.get("language")).lower() == "mixed":
        warnings.append("english_profile_contains_source_language; provide *_en fields to compile fully English")
    if version >= 2:
        if _one_line(payload.get("frame_strategy")) not in {
            "first_only", "first_last", "native_multiframe", "split_relay",
            "edit_cut", "edit_cut_pending_assets", "reference_qc", "reroute_required",
        }:
            errors.append("missing_or_invalid_frame_strategy")
        edit_target = _as_positive_float(duration_plan.get("edit_target_sec"))
        request = _as_positive_float(duration_plan.get("backend_request_sec"))
        if not edit_target or not request:
            errors.append("missing_duration_plan")
        elif request + 0.05 < edit_target and not bool(duration_plan.get("requires_split")):
            errors.append("backend_duration_shorter_than_edit_target_without_split")
        if not re.search(r"Timing:|时间：", prompt):
            errors.append("submit_prompt_missing_timing_window")
    return {"errors": errors, "warnings": warnings}


def render_compiled_markdown(payload: Mapping[str, Any]) -> str:
    """Render the submit artifact embedded in 01_clips.md.

    Only the first fenced block is model-facing.  Metadata and any separate
    negative field remain outside it for adapters/gates.
    """
    duration = payload.get("duration_plan") if isinstance(payload.get("duration_plan"), Mapping) else {}
    meta = (
        f"kind={payload.get('kind')}; version={payload.get('version')}; "
        f"profile_version={payload.get('profile_version')}; profile={payload.get('profile')}; "
        f"backend={payload.get('backend')}; mode={payload.get('mode')}; "
        f"language={payload.get('language')}; native_audio_policy={payload.get('native_audio_policy')}; "
        f"frame_strategy={payload.get('frame_strategy')}; "
        f"story_span_sec={duration.get('story_span_sec')}; edit_target_sec={duration.get('edit_target_sec')}; "
        f"backend_request_sec={duration.get('backend_request_sec')}; "
        f"action_start_sec={duration.get('action_start_sec')}; action_end_sec={duration.get('action_end_sec')}; "
        f"hold_end_sec={duration.get('hold_end_sec')}; trim_mode={duration.get('trim_mode')}; "
        f"requires_split={str(bool(duration.get('requires_split'))).lower()}; "
        f"duration_quantization={duration.get('quantization_reason')}; "
        f"source_contract_sha256={payload.get('source_contract_sha256')}"
    )
    lines = [
        COMPILED_HEADING,
        f"**编译元数据**：{meta}",
        "```text",
        str(payload.get("prompt") or "").strip(),
        "```",
    ]
    negative = _one_line(payload.get("negative_prompt"))
    if negative:
        lines += [
            "",
            "### 后端负向字段（单独提交，不拼入主 prompt）",
            "```text",
            negative,
            "```",
        ]
    return "\n".join(lines)


_COMPILED_BLOCK_RE = re.compile(
    r"###\s*后端编译提交\s*prompt\s*\n"
    r"\*\*编译元数据\*\*[：:]\s*([^\n]+)\n"
    r"```(?:text)?\s*\n?(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
_NEGATIVE_BLOCK_RE = re.compile(
    r"###\s*后端负向字段[^\n]*\n```(?:text)?\s*\n?(.*?)```",
    re.IGNORECASE | re.DOTALL,
)


def parse_compiled_markdown(section: str) -> Optional[Dict[str, Any]]:
    match = _COMPILED_BLOCK_RE.search(section or "")
    if not match:
        return None
    meta: Dict[str, str] = {}
    for piece in match.group(1).split(";"):
        if "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        meta[key.strip()] = value.strip()
    negative_match = _NEGATIVE_BLOCK_RE.search(section or "")
    payload: Dict[str, Any] = {
        **meta,
        "version": int(meta.get("version", "0")) if meta.get("version", "").isdigit() else 0,
        "prompt": match.group(2).strip(),
        "negative_prompt": negative_match.group(1).strip() if negative_match else "",
    }
    if any(key in meta for key in ("edit_target_sec", "backend_request_sec", "story_span_sec")):
        payload["duration_plan"] = {
            "story_span_sec": _as_positive_float(meta.get("story_span_sec")),
            "edit_target_sec": _as_positive_float(meta.get("edit_target_sec")),
            "backend_request_sec": _as_positive_float(meta.get("backend_request_sec")),
            "action_start_sec": _as_positive_float(meta.get("action_start_sec")),
            "action_end_sec": _as_positive_float(meta.get("action_end_sec")),
            "hold_end_sec": _as_positive_float(meta.get("hold_end_sec")),
            "trim_mode": meta.get("trim_mode") or "none",
            "requires_split": str(meta.get("requires_split") or "").lower() == "true",
            "quantization_reason": meta.get("duration_quantization") or "",
        }
    return payload
