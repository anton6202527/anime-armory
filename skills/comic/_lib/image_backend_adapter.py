#!/usr/bin/env python3
"""Comic image backend capability normalization.

This module is deliberately local to the comic line. It maps the project's
model/channel settings to execution constraints that prompt/job builders can
consume without hard-coding one backend path.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


@dataclass(frozen=True)
class ImageBackendCapabilities:
    adapter_id: str
    model: str
    channel: str
    supports_image_inputs: bool
    persistent_subject: bool
    reference_image_limit: int
    single_character_reference_limit: int
    multi_character_reference_limit: int
    non_character_reference_limit: int
    style_reference_limit: int
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def resolve_capabilities(model: str, channel: str = "") -> ImageBackendCapabilities:
    """Return conservative, backend-facing reference budgets.

    The values are capability ceilings for job construction, not claims that a
    local runner for every backend is installed. Runner availability is checked
    elsewhere. Unknown/custom backends fall back to the legacy 6-image budget.
    """
    model_raw = str(model or "自定义").strip() or "自定义"
    channel_raw = str(channel or "manual").strip() or "manual"
    combined = _norm(model_raw + " " + channel_raw)

    if any(token in combined for token in ("gpt image", "gpt-image", "openai", "codex")):
        return ImageBackendCapabilities(
            adapter_id="openai_gpt_image_project_memory",
            model=model_raw,
            channel=channel_raw,
            supports_image_inputs=True,
            persistent_subject=False,
            reference_image_limit=16,
            single_character_reference_limit=5,
            multi_character_reference_limit=3,
            non_character_reference_limit=2,
            style_reference_limit=2,
            notes="OpenAI/Codex route: use project-memory references via real image inputs; no public persistent subject id is assumed.",
        )

    if any(token in combined for token in ("gemini", "nano banana")):
        return ImageBackendCapabilities(
            adapter_id="gemini_multi_reference",
            model=model_raw,
            channel=channel_raw,
            supports_image_inputs=True,
            persistent_subject=False,
            reference_image_limit=14,
            single_character_reference_limit=5,
            multi_character_reference_limit=3,
            non_character_reference_limit=2,
            style_reference_limit=2,
            notes="Gemini/Nano Banana route: prefer multiple image references; persistent subject id is not assumed by default.",
        )

    if any(token in combined for token in ("seedream", "可灵", "kling", "主体库", "subject")):
        return ImageBackendCapabilities(
            adapter_id="native_subject_capable",
            model=model_raw,
            channel=channel_raw,
            supports_image_inputs=True,
            persistent_subject=True,
            reference_image_limit=10,
            single_character_reference_limit=4,
            multi_character_reference_limit=3,
            non_character_reference_limit=2,
            style_reference_limit=1,
            notes="Backend appears subject-library capable; registry should record any real subject id separately from reference images.",
        )

    if any(token in combined for token in ("dreamina", "即梦")):
        return ImageBackendCapabilities(
            adapter_id="dreamina_image2image",
            model=model_raw,
            channel=channel_raw,
            supports_image_inputs=True,
            persistent_subject=False,
            reference_image_limit=10,
            single_character_reference_limit=5,
            multi_character_reference_limit=4,
            non_character_reference_limit=2,
            style_reference_limit=1,
            notes=(
                "Dreamina official CLI image2image route: 1-10 local image inputs are supported "
                "(verified 2026-07-16 with `dreamina image2image --help`); keep one slot for "
                "style_only when the panel also needs identity/location/prop anchors."
            ),
        )

    if any(token in combined for token in ("flux", "comfyui", "sdxl", "stable diffusion")):
        return ImageBackendCapabilities(
            adapter_id="open_pipeline_reference",
            model=model_raw,
            channel=channel_raw,
            supports_image_inputs=True,
            persistent_subject=False,
            reference_image_limit=8,
            single_character_reference_limit=4,
            multi_character_reference_limit=2,
            non_character_reference_limit=1,
            style_reference_limit=1,
            notes="Open/local pipeline route: reference budget is conservative; LoRA/control adapters must be recorded separately.",
        )

    return ImageBackendCapabilities(
        adapter_id="manual_or_unknown",
        model=model_raw,
        channel=channel_raw,
        supports_image_inputs=False if "manual" in combined else True,
        persistent_subject=False,
        reference_image_limit=6,
        single_character_reference_limit=4,
        multi_character_reference_limit=2,
        non_character_reference_limit=1,
        style_reference_limit=1,
        notes="Unknown/custom route: use the legacy compact reference budget until a backend adapter is added.",
    )


def capabilities_from_settings(settings: dict[str, str]) -> ImageBackendCapabilities:
    return resolve_capabilities(settings.get("生图模型", "自定义"), settings.get("生图渠道", "manual"))
