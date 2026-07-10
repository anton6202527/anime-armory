#!/usr/bin/env python3
"""Song-owned compiler for backend-specific music generation fields."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Mapping, Sequence


KIND = "song_compiled_compose_prompt"
VERSION = 1
PROFILE_VERSION = "2026-07-10.1"
_INTERNAL_RE = re.compile(r"(?:创作/|素材/|歌/|\.md\b|song_brief|reference_pack|chord_sheet|topline_notes)", re.I)


def one_line(value: Any, limit: int = 500) -> str:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        text = ", ".join(one_line(v) for v in value if one_line(v))
    else:
        text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip(" ；;,，。")
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(",", 1)[0].rsplit("；", 1)[0]
    return (cut or text[:limit]).rstrip(" ；;,，。") + "…"


def normalize_backend(value: Any) -> str:
    text = one_line(value).lower()
    if "suno" in text:
        return "suno"
    if "udio" in text:
        return "udio"
    if "ace" in text or "ace-step" in text:
        return "ace_step"
    if "diffrhythm" in text or "diff rhythm" in text:
        return "diff_rhythm"
    if "manual" in text or "人工" in text:
        return "manual"
    return text or "generic"


def profile_for(value: Any) -> Dict[str, Any]:
    backend = normalize_backend(value)
    if backend in {"suno", "udio"}:
        return {"backend": backend, "profile": f"{backend}_custom_fields", "field_map": {"style": "style", "lyrics": "lyrics", "title": "title"}}
    if backend == "ace_step":
        return {"backend": backend, "profile": "ace_step_prompt_lyrics", "field_map": {"style": "prompt", "lyrics": "lyrics", "duration": "audio_duration"}}
    if backend == "diff_rhythm":
        return {"backend": backend, "profile": "diff_rhythm_style_lyrics", "field_map": {"style": "style_prompt", "lyrics": "lyrics", "duration": "duration"}}
    return {"backend": backend, "profile": "generic_separate_style_lyrics", "field_map": {"style": "style", "lyrics": "lyrics", "duration": "duration_seconds"}}


def _hash(contract: Mapping[str, Any]) -> str:
    raw = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _style(contract: Mapping[str, Any]) -> str:
    pieces: List[str] = []
    for value in (
        contract.get("style_seed"),
        contract.get("sonic_identity"),
        contract.get("emotional_arc"),
        contract.get("hook_intent"),
    ):
        text = one_line(value, 220)
        if text and "待填写" not in text and text not in pieces:
            pieces.append(text)
    return ", ".join(pieces)


def compile_prompt(contract: Mapping[str, Any]) -> Dict[str, Any]:
    profile = profile_for(contract.get("backend"))
    style = _style(contract)
    lyrics = str(contract.get("lyrics") or "").strip()
    duration = contract.get("duration_seconds")
    title = one_line(contract.get("title"), 120)
    submit_fields: Dict[str, Any] = {
        profile["field_map"]["style"]: style,
        profile["field_map"]["lyrics"]: lyrics,
    }
    if title and "title" in profile["field_map"]:
        submit_fields[profile["field_map"]["title"]] = title
    if duration and "duration" in profile["field_map"]:
        submit_fields[profile["field_map"]["duration"]] = int(duration)
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "take_id": one_line(contract.get("take_id")),
        "backend": profile["backend"],
        "profile": profile["profile"],
        "field_map": profile["field_map"],
        "style_prompt": style,
        "lyrics": lyrics,
        "duration_seconds": int(duration) if duration else None,
        "submit_fields": submit_fields,
        "source_contract_sha256": _hash(contract),
        "lyrics_sha256": hashlib.sha256(lyrics.encode("utf-8")).hexdigest(),
    }
    payload["lint"] = lint(payload)
    return payload


def lint(payload: Mapping[str, Any]) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    style = one_line(payload.get("style_prompt"), 100000)
    lyrics = str(payload.get("lyrics") or "").strip()
    fields = payload.get("submit_fields")
    if not style:
        errors.append("empty_style_prompt")
    if not lyrics:
        errors.append("empty_lyrics")
    if _INTERNAL_RE.search(style):
        errors.append("style_prompt_contains_internal_contract_reference")
    if not isinstance(fields, Mapping) or len(fields) < 2:
        errors.append("missing_backend_submit_fields")
    if len(style) > 700:
        warnings.append(f"style_prompt_verbose:{len(style)}")
    if not re.search(r"\[(?:verse|chorus|bridge|intro|outro|pre[- ]?chorus|hook|主歌|副歌|桥段)", lyrics, re.I):
        warnings.append("lyrics_missing_section_tags")
    expected_lyrics_hash = hashlib.sha256(lyrics.encode("utf-8")).hexdigest()
    if payload.get("lyrics_sha256") and payload.get("lyrics_sha256") != expected_lyrics_hash:
        errors.append("lyrics_hash_mismatch")
    return {"errors": errors, "warnings": warnings}


def render_markdown(payload: Mapping[str, Any]) -> str:
    meta = "; ".join(
        f"{key}={payload.get(key)}"
        for key in ("kind", "version", "profile_version", "profile", "backend", "source_contract_sha256", "lyrics_sha256")
    )
    params = {
        key: value
        for key, value in (payload.get("submit_fields") or {}).items()
        if key not in {payload.get("field_map", {}).get("style"), payload.get("field_map", {}).get("lyrics")}
    }
    return "\n".join([
        "## 后端编译提交字段",
        f"**编译元数据**：{meta}",
        "",
        f"### `{payload.get('field_map', {}).get('style', 'style')}`",
        "```text",
        str(payload.get("style_prompt") or "").strip(),
        "```",
        "",
        f"### `{payload.get('field_map', {}).get('lyrics', 'lyrics')}`",
        "```lyrics",
        str(payload.get("lyrics") or "").strip(),
        "```",
        "",
        "### 结构化参数",
        "```json",
        json.dumps(params, ensure_ascii=False, indent=2),
        "```",
    ])
