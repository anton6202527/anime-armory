#!/usr/bin/env python3
"""Small URL adapter for GPT-SoVITS-compatible local TTS services.

n2d-voice normally calls a CosyVoice-style wrapper:
  /inference_zero_shot?text=&prompt_text=&prompt_wav=

The official GPT-SoVITS API exposes the same capability at the root endpoint
with different parameter names:
  /?text=&text_language=&refer_wav_path=&prompt_text=&prompt_language=
"""
from __future__ import annotations

from typing import List, Tuple
from urllib.parse import urlencode, urlparse


def _base(url: str) -> str:
    return str(url or "").strip().rstrip("/")


def cosy_style_url(url: str, text: str, ref_audio: str | None, ref_text: str | None) -> str:
    base = _base(url)
    endpoint = base if base.endswith("/inference_zero_shot") else f"{base}/inference_zero_shot"
    query = urlencode({
        "text": text,
        "prompt_text": ref_text or "",
        "prompt_wav": ref_audio or "",
    })
    return f"{endpoint}?{query}"


def official_gptsovits_url(
    url: str,
    text: str,
    ref_audio: str | None,
    ref_text: str | None,
    *,
    text_language: str = "zh",
    prompt_language: str = "zh",
    speed: float = 1.0,
) -> str:
    base = _base(url)
    if base.endswith("/inference_zero_shot"):
        base = base[: -len("/inference_zero_shot")]
    if urlparse(base).path == "":
        base = f"{base}/"
    query = urlencode({
        "refer_wav_path": ref_audio or "",
        "prompt_text": ref_text or "",
        "prompt_language": prompt_language,
        "text": text,
        "text_language": text_language,
        "speed": speed,
    })
    return f"{base}?{query}"


def endpoint_candidates(
    label: str,
    url: str,
    text: str,
    ref_audio: str | None,
    ref_text: str | None,
    *,
    text_language: str = "zh",
    speed: float = 1.0,
) -> List[Tuple[str, str]]:
    """Return endpoint URLs to try, in priority order."""
    if "gpt" in label.lower() and "sovits" in label.lower():
        official = (
            "official_gptsovits",
            official_gptsovits_url(
                url,
                text,
                ref_audio,
                ref_text,
                text_language=text_language,
                prompt_language="zh",
                speed=speed,
            ),
        )
        cosy = ("cosy_style", cosy_style_url(url, text, ref_audio, ref_text))
        if _base(url).endswith("/inference_zero_shot"):
            return [cosy, official]
        return [official, cosy]
    return [("cosy_style", cosy_style_url(url, text, ref_audio, ref_text))]
