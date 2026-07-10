#!/usr/bin/env python3
"""MV-owned compiler from strict clip contracts to provider-facing prompts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence


KIND = "mv_compiled_video_prompt"
VERSION = 1
PROFILE_VERSION = "2026-07-10.1"
HEADING = "### 后端编译提交 prompt"
_NEGATIVE_RE = re.compile(r"\b(?:no|not|never|avoid|without|don't|do not)\b|不要|禁止|不得|避免", re.I)
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_INTERNAL_RE = re.compile(r"(?:出图/|\.png\b|lead_id|reference_group|skills/mv/|identity_registry)", re.I)


def one_line(value: Any, limit: int = 240) -> str:
    if isinstance(value, Mapping):
        text = "；".join(f"{k}={one_line(v)}" for k, v in value.items() if one_line(v))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        text = "、".join(one_line(v) for v in value if one_line(v))
    else:
        text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip(" ；;,，。")
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit("；", 1)[0].rsplit("。", 1)[0]
    return (cut or text[:limit]).rstrip(" ；;,，。") + "…"


def normalize_backend(value: Any) -> str:
    text = one_line(value).lower()
    for aliases, name in (
        (("runway", "gen-4", "gen4"), "runway"),
        (("veo", "gemini"), "veo"),
        (("luma", "ray3", "dream machine"), "luma"),
        (("pika",), "pika"),
        (("seedance",), "seedance"),
        (("dreamina", "jimeng", "即梦"), "dreamina"),
        (("kling", "可灵"), "kling"),
        (("hailuo", "海螺"), "hailuo"),
        (("wan", "万相"), "wan"),
        (("hunyuan", "混元"), "hunyuan"),
        (("ltx",), "ltx"),
        (("sora",), "sora"),
        (("manual", "人工"), "manual"),
    ):
        if any(alias in text for alias in aliases):
            return name
    return text or "generic"


def profile_for(value: Any) -> Dict[str, str]:
    backend = normalize_backend(value)
    if backend == "runway":
        return {"backend": backend, "profile": "runway_mv_positive", "language": "en", "negative": "none"}
    if backend == "veo":
        return {"backend": backend, "profile": "veo_mv_cinematography", "language": "en", "negative": "separate"}
    if backend in {"luma", "pika", "sora"}:
        return {"backend": backend, "profile": "english_mv_keyframe", "language": "en", "negative": "separate"}
    return {"backend": backend, "profile": "zh_mv_motion_first", "language": "zh", "negative": "inline_guard"}


def _hash(contract: Mapping[str, Any]) -> str:
    raw = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compile_prompt(contract: Mapping[str, Any]) -> Dict[str, Any]:
    profile = profile_for(contract.get("backend"))
    preferred_language = profile["language"]
    mode = one_line(contract.get("mode")) or "image2video"
    action = one_line(contract.get("primary_action") or contract.get("action"), 240)
    camera = one_line(contract.get("camera_motion"), 140)
    environment = one_line(contract.get("environment_motion"), 100)
    rhythm = one_line(contract.get("rhythm"), 110)
    end_state = one_line(contract.get("end_state"), 140)
    negative_elements = [one_line(v, 80) for v in contract.get("negative_elements") or [] if one_line(v, 80)]
    language = "mixed" if preferred_language == "en" and _CJK_RE.search(" ".join((action, camera, environment, rhythm, end_state))) else preferred_language

    parts: List[str] = []
    if preferred_language == "en":
        parts.append("Animate continuously from the supplied first frame to the final frame." if "frame" in mode.lower() else "Animate the supplied first frame.")
        parts.append(f"Primary action: {action}." if action else "")
        parts.append(f"Camera: {camera}." if camera else "")
        parts.append(f"Environment motion: {environment}." if environment else "")
        parts.append(f"Rhythm: {rhythm}." if rhythm else "")
        parts.append(f"End and hold on: {end_state}." if end_state else "")
        parts.append("Keep the registered performer, wardrobe, composition and lighting stable.")
    else:
        parts.append("从已提交首帧连续运动到尾帧。" if "frame" in mode.lower() else "以已提交首帧为视觉真值。")
        parts.append(f"人物主动作：{action}。" if action else "")
        parts.append(f"镜头：{camera}。" if camera else "")
        parts.append(f"环境响应：{environment}。" if environment else "")
        parts.append(f"卡点：{rhythm}。" if rhythm else "")
        parts.append(f"结尾停稳在：{end_state}。" if end_state else "")
        parts.append("人物身份、服装、构图与光位保持首帧一致；成片歌曲在合成阶段铺设。")
        if negative_elements:
            parts.append("避免：" + "、".join(negative_elements) + "。")
    prompt = " ".join(part for part in parts if part).strip()
    negative_prompt = ", ".join(negative_elements) if profile["negative"] == "separate" else ""
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "clip_id": one_line(contract.get("clip_id")),
        "backend": profile["backend"],
        "profile": profile["profile"],
        "mode": mode,
        "language": language,
        "native_audio_policy": "external_song_track",
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "request_controls": {
            "frame_inputs": list(contract.get("frame_inputs") or []),
            "reference_inputs": list(contract.get("reference_inputs") or []),
            "generate_audio": False,
        },
        "source_contract_sha256": _hash(contract),
    }
    payload["lint"] = lint(payload)
    return payload


def lint(payload: Mapping[str, Any]) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    prompt = one_line(payload.get("prompt"), 100000)
    backend = normalize_backend(payload.get("backend"))
    if not prompt:
        errors.append("empty_submit_prompt")
    if not re.search(r"人物主动作：|Primary action:", prompt):
        errors.append("missing_primary_action")
    if not re.search(r"镜头：|Camera:", prompt):
        errors.append("missing_camera_motion")
    if str(payload.get("native_audio_policy")) != "external_song_track":
        errors.append("mv_audio_policy_must_use_external_song_track")
    if backend == "runway" and _NEGATIVE_RE.search(prompt):
        errors.append("runway_prompt_contains_negative_command")
    if backend == "runway" and one_line(payload.get("negative_prompt")):
        errors.append("runway_negative_prompt_must_be_empty")
    if _INTERNAL_RE.search(prompt):
        errors.append("submit_prompt_contains_internal_contract_reference")
    if len(prompt) > (650 if str(payload.get("language")) in {"zh", "mixed"} else 900):
        warnings.append(f"submit_prompt_verbose:{len(prompt)}")
    if len([p for p in re.split(r"[。；;.!?]+", prompt) if p.strip()]) > 12:
        warnings.append("submit_prompt_many_clauses")
    return {"errors": errors, "warnings": warnings}


def render_markdown(payload: Mapping[str, Any]) -> str:
    meta = "; ".join(
        f"{key}={payload.get(key)}"
        for key in (
            "kind", "version", "profile_version", "profile", "backend", "mode", "language",
            "native_audio_policy", "source_contract_sha256",
        )
    )
    lines = [HEADING, f"**编译元数据**：{meta}", "```text", str(payload.get("prompt") or "").strip(), "```"]
    if one_line(payload.get("negative_prompt")):
        lines += ["", "### 后端负向字段（单独提交，不拼入主 prompt）", "```text", str(payload["negative_prompt"]).strip(), "```"]
    return "\n".join(lines)


_BLOCK_RE = re.compile(
    r"###\s*后端编译提交\s*prompt\s*\n\*\*编译元数据\*\*[：:]\s*([^\n]+)\n```(?:text)?\s*\n?(.*?)```",
    re.I | re.S,
)
_NEG_RE = re.compile(r"###\s*后端负向字段[^\n]*\n```(?:text)?\s*\n?(.*?)```", re.I | re.S)


def parse_markdown(text: str) -> Optional[Dict[str, Any]]:
    match = _BLOCK_RE.search(text or "")
    if not match:
        return None
    meta: Dict[str, Any] = {}
    for part in match.group(1).split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            meta[key.strip()] = value.strip()
    if str(meta.get("version") or "").isdigit():
        meta["version"] = int(meta["version"])
    neg = _NEG_RE.search(text or "")
    return {**meta, "prompt": match.group(2).strip(), "negative_prompt": neg.group(1).strip() if neg else ""}
