#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Text language/direction helpers for the comic pipeline.

The helpers are deliberately deterministic and small. They do not try to be a
full shaping engine; they record metadata and identify cases that need a
proper language-aware renderer instead of the current Pillow draft renderer.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


TEXT_LANGUAGE_ALIASES = {
    "zh": "中文",
    "chinese": "中文",
    "cn": "中文",
    "中文": "中文",
    "en": "英文",
    "english": "英文",
    "英文": "英文",
    "zh_en": "中上英下",
    "zh-en": "中上英下",
    "中英": "中上英下",
    "中上英下": "中上英下",
    "中文上英文下": "中上英下",
    "en_zh": "英上中下",
    "en-zh": "英上中下",
    "英中": "英上中下",
    "英上中下": "英上中下",
    "英文上中文下": "英上中下",
}

LANGUAGE_TAGS = {
    "中文": ("zh-Hans", "ltr", "Hans"),
    "英文": ("en", "ltr", "Latn"),
    "中上英下": ("zh-Hans", "ltr", "Hans"),
    "英上中下": ("en", "ltr", "Latn"),
}

RTL_RANGES = (
    (0x0590, 0x08FF),
    (0xFB1D, 0xFDFF),
    (0xFE70, 0xFEFF),
)
THAI_LIKE_RANGES = (
    (0x0E00, 0x0E7F),
    (0x1780, 0x17FF),
    (0x1000, 0x109F),
    (0x1980, 0x19DF),
)


def normalize_text_language(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "中文"
    lowered = re.sub(r"\s+", " ", raw).lower()
    return TEXT_LANGUAGE_ALIASES.get(lowered, raw)


def custom_language_payload(mode: str) -> str:
    match = re.match(r"^\s*自定义语言\s*[（(](.+?)[)）]\s*$", str(mode or ""))
    return match.group(1).strip() if match else ""


def char_script(ch: str) -> str:
    code = ord(ch)
    if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0x20000 <= code <= 0x2A6DF:
        return "cjk"
    if ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
        return "latin"
    if any(start <= code <= end for start, end in RTL_RANGES):
        return "rtl"
    if any(start <= code <= end for start, end in THAI_LIKE_RANGES):
        return "segmentation_required"
    if unicodedata.category(ch).startswith("L"):
        return "other"
    return ""


def script_counts(text: str) -> dict[str, int]:
    counts = {"cjk": 0, "latin": 0, "rtl": 0, "segmentation_required": 0, "other": 0}
    for ch in str(text or ""):
        if ch.isspace() or unicodedata.category(ch).startswith("P"):
            continue
        script = char_script(ch)
        if script:
            counts[script] += 1
    return counts


def dominant_script(text: str) -> str:
    counts = script_counts(text)
    total = sum(counts.values())
    if total <= 0:
        return "unknown"
    script, count = max(counts.items(), key=lambda item: item[1])
    return script if count / total >= 0.35 else "mixed"


def first_strong_direction(text: str) -> str:
    for ch in str(text or ""):
        bidi = unicodedata.bidirectional(ch)
        if bidi in {"R", "AL"}:
            return "rtl"
        if bidi == "L":
            return "ltr"
    return "unknown"


def infer_language_metadata(text: str, language_mode: str | None = None) -> dict[str, str]:
    mode = normalize_text_language(language_mode) if str(language_mode or "").strip() else ""
    custom = custom_language_payload(mode)
    if custom:
        lang = custom
        direction = first_strong_direction(text)
        script = dominant_script(text)
    elif mode in LANGUAGE_TAGS:
        lang, direction, script = LANGUAGE_TAGS[mode]
    else:
        lang = mode or "und"
        direction = first_strong_direction(text)
        script = dominant_script(text)

    detected_script = dominant_script(text)
    if detected_script in {"rtl", "segmentation_required"}:
        script = detected_script
    if direction == "unknown":
        direction = "rtl" if detected_script == "rtl" else "ltr"
    if not lang:
        lang = "und"
    return {
        "lang": lang,
        "dir": direction,
        "script": script,
        "line_break": line_break_mode_for_script(detected_script if detected_script != "unknown" else script),
    }


def line_break_mode_for_script(script: str) -> str:
    if script == "cjk" or script in {"Hans", "Hant"}:
        return "cjk"
    if script == "latin" or script == "Latn":
        return "word"
    if script == "segmentation_required":
        return "dictionary_required"
    if script == "rtl":
        return "bidi_required"
    return "unknown"


def requires_advanced_text_layout(metadata: dict[str, str]) -> bool:
    return metadata.get("dir") == "rtl" or metadata.get("line_break") in {"dictionary_required", "bidi_required"}


def text_from_item(item: dict[str, Any], text_language: str) -> str:
    mode = normalize_text_language(text_language)
    if mode == "英文":
        return str(item.get("text_en") or item.get("text") or item.get("text_zh") or "").strip()
    if mode == "中上英下":
        return "\n".join(
            part for part in (str(item.get("text_zh") or item.get("text") or "").strip(), str(item.get("text_en") or "").strip()) if part
        )
    if mode == "英上中下":
        return "\n".join(
            part for part in (str(item.get("text_en") or "").strip(), str(item.get("text_zh") or item.get("text") or "").strip()) if part
        )
    if mode.startswith("自定义语言"):
        return str(item.get("text_custom") or item.get("text") or "").strip()
    return str(item.get("text_zh") or item.get("text") or item.get("text_en") or "").strip()


def unsupported_lettering_items(lettering: dict[str, Any] | None, text_language: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in (lettering or {}).get("items") or []:
        if not isinstance(item, dict):
            continue
        text = text_from_item(item, text_language)
        if not text:
            continue
        metadata = {
            "lang": str(item.get("lang") or "").strip(),
            "dir": str(item.get("dir") or "").strip(),
            "script": str(item.get("script") or "").strip(),
            "line_break": str(item.get("line_break") or "").strip(),
        }
        if not metadata["lang"] or not metadata["dir"] or not metadata["line_break"]:
            metadata = infer_language_metadata(text, text_language)
        if requires_advanced_text_layout(metadata):
            out.append(
                {
                    "item_id": str(item.get("item_id") or ""),
                    "panel_id": str(item.get("panel_id") or ""),
                    "lang": metadata.get("lang", ""),
                    "dir": metadata.get("dir", ""),
                    "line_break": metadata.get("line_break", ""),
                    "reason": "requires language-aware shaping/line breaking beyond the draft Pillow renderer",
                }
            )
    return out


def estimated_line_count(text: str, slot_w: int = 430, font_size: int = 44) -> int:
    raw = str(text or "").strip()
    if not raw:
        return 1
    total = 0
    for line in raw.splitlines() or [raw]:
        line = line.strip()
        if not line:
            total += 1
            continue
        script = dominant_script(line)
        if script == "cjk":
            chars = len([ch for ch in line if not ch.isspace()])
            per_line = max(6, int(slot_w / max(font_size * 0.92, 1)))
        elif script == "latin":
            words = line.split()
            chars = sum(len(word) for word in words) + max(0, len(words) - 1) if words else len(line)
            per_line = max(10, int(slot_w / max(font_size * 0.52, 1)))
        elif script == "rtl":
            chars = len([ch for ch in line if not ch.isspace()])
            per_line = max(9, int(slot_w / max(font_size * 0.58, 1)))
        elif script == "segmentation_required":
            chars = len([ch for ch in line if not ch.isspace()])
            per_line = max(8, int(slot_w / max(font_size * 0.70, 1)))
        else:
            chars = len([ch for ch in line if not ch.isspace()])
            per_line = max(8, int(slot_w / max(font_size * 0.70, 1)))
        total += max(1, (chars + per_line - 1) // per_line)
    return total
