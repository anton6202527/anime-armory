#!/usr/bin/env python3
"""Advertising-owned backend compiler for model-facing video prompts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Mapping, Optional


KIND = "ad_compiled_video_prompt"
VERSION = 1
PROFILE_VERSION = "2026-07-10.1"
HEADING = "### 后端编译提交 prompt"
_NEGATIVE_RE = re.compile(r"\b(?:no|not|never|avoid|without|don't|do not)\b|不要|禁止|不得|避免", re.I)


def one_line(value: Any, limit: int = 240) -> str:
    if isinstance(value, list):
        text = "、".join(str(v).strip() for v in value if str(v).strip())
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
        (("luma", "pika"), "luma_pika"),
        (("seedance",), "seedance"),
        (("dreamina", "jimeng", "即梦"), "dreamina"),
        (("kling", "可灵"), "kling"),
    ):
        if any(alias in text for alias in aliases):
            return name
    return text or "generic"


def profile_for(value: Any) -> Dict[str, str]:
    backend = normalize_backend(value)
    if backend == "runway":
        return {"backend": backend, "profile": "runway_ad_positive", "language": "en", "negative": "none"}
    if backend == "veo":
        return {"backend": backend, "profile": "veo_ad_cinematography", "language": "en", "negative": "separate"}
    if backend == "luma_pika":
        return {"backend": backend, "profile": "english_ad_keyframe", "language": "en", "negative": "separate"}
    return {"backend": backend, "profile": "zh_ad_motion_first", "language": "zh", "negative": "inline_guard"}


def _hash(contract: Mapping[str, Any]) -> str:
    raw = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _opening(mode: str, language: str) -> str:
    frames = "frame" in mode.lower()
    if language == "en":
        return "Animate from the supplied first frame to the final frame" if frames else "Animate the supplied first frame"
    return "从已提交首帧连续运动到尾帧" if frames else "以已提交首帧为视觉真值"


def compile_prompt(contract: Mapping[str, Any]) -> Dict[str, Any]:
    profile = profile_for(contract.get("backend"))
    language = profile["language"]
    mode = one_line(contract.get("mode")) or "image2video"
    action = one_line(contract.get("product_action") or contract.get("action"), 220)
    camera = one_line(contract.get("camera_motion"), 120)
    environment = one_line(contract.get("environment_motion"), 100)
    end_state = one_line(contract.get("end_state"), 120)
    product_hold = one_line(contract.get("product_hold"), 140)
    text_strategy = one_line(contract.get("text_strategy"), 120)
    negative_elements = [one_line(v, 80) for v in contract.get("negative_elements") or [] if one_line(v, 80)]

    parts: List[str] = []
    if language == "en":
        parts.append(_opening(mode, language) + ".")
        parts.append(f"Primary product action: {action}." if action else "")
        parts.append(f"Camera: {camera}." if camera else "")
        parts.append(f"Environment response: {environment}." if environment else "")
        parts.append(f"End and hold on: {end_state}." if end_state else "")
        parts.append(f"Product hold: {product_hold}." if product_hold else "")
        parts.append(f"Typography treatment: {text_strategy}." if text_strategy else "")
    else:
        parts.append(_opening(mode, language) + "。")
        parts.append(f"产品主动作：{action}。" if action else "")
        parts.append(f"镜头：{camera}。" if camera else "")
        parts.append(f"环境响应：{environment}。" if environment else "")
        parts.append(f"结尾停稳在：{end_state}。" if end_state else "")
        parts.append(f"产品保持：{product_hold}。" if product_hold else "")
        parts.append(f"文字策略：{text_strategy}。" if text_strategy else "")
        parts.append("产品比例、包装结构、Logo 位置和品牌色保持稳定；画面只保留已登记产品与品牌元素。")
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
        "prompt": prompt,
        "negative_prompt": negative_prompt,
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
    if not re.search(r"产品主动作：|Primary product action:", prompt):
        errors.append("missing_product_action")
    if not re.search(r"镜头：|Camera:", prompt):
        errors.append("missing_camera_motion")
    if backend == "runway" and _NEGATIVE_RE.search(prompt):
        errors.append("runway_prompt_contains_negative_command")
    if backend == "runway" and one_line(payload.get("negative_prompt")):
        errors.append("runway_negative_prompt_must_be_empty")
    if len(prompt) > (650 if str(payload.get("language")) == "zh" else 900):
        warnings.append(f"submit_prompt_verbose:{len(prompt)}")
    if len([p for p in re.split(r"[。；;.!?]+", prompt) if p.strip()]) > 12:
        warnings.append("submit_prompt_many_clauses")
    return {"errors": errors, "warnings": warnings}


def render_markdown(payload: Mapping[str, Any]) -> str:
    meta = "; ".join(
        f"{key}={payload.get(key)}"
        for key in (
            "kind", "version", "profile_version", "profile", "backend", "mode", "language",
            "source_contract_sha256",
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
