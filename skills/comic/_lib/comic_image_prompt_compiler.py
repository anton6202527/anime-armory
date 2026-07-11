#!/usr/bin/env python3
"""Comic-owned compiler from panel production contracts to image prompts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Mapping, Sequence


KIND = "comic_compiled_image_prompt"
VERSION = 1
PROFILE_VERSION = "2026-07-10.2"
_INTERNAL_RE = re.compile(
    r"(?:CHAR_|MON_|LOC_|PROP_|SYS_|FX_|STYLE_|出图/|\.png\b|identity_registry|asset_registry|reference_group)",
    re.I,
)


def one_line(value: Any, limit: int = 520) -> str:
    if isinstance(value, Mapping):
        text = "；".join(f"{k}={one_line(v)}" for k, v in value.items() if one_line(v))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        text = "；".join(one_line(v) for v in value if one_line(v))
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
        (("gpt image", "gpt-image", "openai", "codex"), "gpt_image"),
        (("gemini", "nano banana"), "gemini"),
        (("seedream",), "seedream"),
        (("kling", "可灵", "主体库"), "kling_subject"),
        (("dreamina", "即梦"), "dreamina"),
        (("flux", "comfyui", "sdxl", "stable diffusion"), "diffusion_pipeline"),
        (("manual", "人工"), "manual"),
    ):
        if any(alias in text for alias in aliases):
            return name
    return text or "generic"


def profile_for(value: Any) -> Dict[str, str]:
    backend = normalize_backend(value)
    if backend == "gpt_image":
        return {"backend": backend, "profile": "gpt_image_comic_natural", "negative": "inline_guard"}
    if backend == "gemini":
        return {"backend": backend, "profile": "gemini_comic_structured", "negative": "inline_guard"}
    if backend in {"seedream", "kling_subject", "dreamina"}:
        return {"backend": backend, "profile": "zh_comic_reference_first", "negative": "inline_guard"}
    if backend == "diffusion_pipeline":
        return {"backend": backend, "profile": "diffusion_comic_tags", "negative": "separate"}
    return {"backend": backend, "profile": "generic_comic_natural", "negative": "inline_guard"}


def _hash(contract: Mapping[str, Any]) -> str:
    raw = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compile_prompt(contract: Mapping[str, Any]) -> Dict[str, Any]:
    profile = profile_for(contract.get("backend"))
    visible = one_line(contract.get("visible_facts"), 420)
    style = one_line(contract.get("style"), 260)
    composition = one_line(contract.get("composition"), 300)
    scene = one_line(contract.get("scene_continuity"), 340)
    identity = one_line(contract.get("identity_hold"), 320)
    finishing = one_line(contract.get("finishing"), 360)
    text_strategy = one_line(contract.get("text_strategy"), 220)
    anatomy = one_line(contract.get("anatomy"), 220)
    negative_elements = [one_line(v, 70) for v in contract.get("negative_elements") or [] if one_line(v, 70)]

    parts = ["生成一张铺满画布的单格无字漫画画面。"]
    parts.append(f"画面事实：{visible}。" if visible else "")
    parts.append(f"构图与表演：{composition}。" if composition else "")
    parts.append(f"画风与稿层：{style}。" if style else "")
    parts.append(f"场景连续性：{scene}。" if scene else "")
    parts.append(f"参考保持：{identity}。" if identity else "")
    parts.append(f"线稿、黑场、网点与效果：{finishing}。" if finishing else "")
    parts.append(f"文字处理：{text_strategy}。" if text_strategy else "")
    parts.append(f"人体与道具：{anatomy}。" if anatomy else "")
    if profile["negative"] == "inline_guard" and negative_elements:
        parts.append("避免：" + "、".join(negative_elements) + "。")
    prompt = " ".join(part for part in parts if part).strip()
    negative_prompt = ", ".join(negative_elements) if profile["negative"] == "separate" else ""
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "panel_id": one_line(contract.get("panel_id")),
        "backend": profile["backend"],
        "profile": profile["profile"],
        "language": "zh",
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "request_controls": {
            "reference_inputs": list(contract.get("reference_inputs") or []),
            "canvas": dict(contract.get("canvas") or {}),
        },
        "source_contract_sha256": _hash(contract),
    }
    payload["lint"] = lint(payload)
    return payload


def lint(payload: Mapping[str, Any]) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    prompt = one_line(payload.get("prompt"), 100000)
    if not prompt:
        errors.append("empty_submit_prompt")
    if "画面事实：" not in prompt:
        errors.append("missing_visible_facts")
    if "画风与稿层：" not in prompt:
        errors.append("missing_style_or_render_stage")
    if _INTERNAL_RE.search(prompt):
        errors.append("submit_prompt_contains_internal_contract_reference")
    if any(token in prompt for token in ("对白：", "旁白：", "台词：")):
        errors.append("submit_prompt_contains_exact_dialogue")
    if len(prompt) > 1400:
        warnings.append(f"submit_prompt_verbose:{len(prompt)}")
    if len([p for p in re.split(r"[。；;.!?]+", prompt) if p.strip()]) > 20:
        warnings.append("submit_prompt_many_clauses")
    return {"errors": errors, "warnings": warnings}
