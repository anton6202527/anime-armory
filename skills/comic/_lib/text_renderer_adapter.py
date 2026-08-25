#!/usr/bin/env python3
"""Truthful Comic lettering renderer capability probe and selection."""
from __future__ import annotations

import shutil
from typing import Any


def probe() -> dict[str, Any]:
    pango = shutil.which("pango-view")
    harfbuzz = shutil.which("hb-shape")
    if pango and harfbuzz:
        return {
            "adapter_id": "pango_harfbuzz", "status": "executable",
            "supports": ["complex_shaping", "rtl", "cjk_horizontal", "font_fallback"],
            "commands": {"pango_view": pango, "hb_shape": harfbuzz},
        }
    return {
        "adapter_id": "pillow_draft", "status": "draft_only",
        "supports": ["cjk_horizontal", "latin_horizontal"],
        "missing": [name for name, value in (("pango-view", pango), ("hb-shape", harfbuzz)) if not value],
        "reason": "professional complex shaping adapter is unavailable; Pillow remains a draft renderer",
    }


def suitability(*, language_mode: str, direction: str, available: dict[str, Any] | None = None) -> dict[str, Any]:
    adapter = dict(available or probe())
    rtl = str(direction or "").lower() in {"rtl", "right-to-left", "从右到左"}
    complex_language = any(token in str(language_mode or "").lower() for token in ("arab", "hebrew", "thai", "devanagari", "阿拉伯", "希伯来", "泰"))
    required = "complex_shaping" if rtl or complex_language else "cjk_horizontal"
    return {
        **adapter, "required_capability": required,
        "suitable": required in set(adapter.get("supports") or []),
        "publication_claim_allowed": adapter.get("status") == "executable" and required in set(adapter.get("supports") or []),
    }
