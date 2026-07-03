#!/usr/bin/env python3
"""Shared helpers for optional video-side consistency checks.

These helpers intentionally stay standard-library only. Heavy VLM/embedding/
tracking runners can write sidecar JSON reports; the n2d-review gate only reads
those reports and turns them into consistent findings.
"""
from __future__ import annotations

import glob
import json
import os
import re
from typing import Any, Iterable, List, Optional, Sequence, Tuple


CLIP_RE = re.compile(r"(?i)(?:Clip|镜头|镜)\s*[_ -]?0*([0-9]+)")


def load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def load_first_json(root: str, rels: Sequence[str]) -> Tuple[Optional[Any], str]:
    for rel in rels:
        candidates = sorted(glob.glob(os.path.join(root, rel))) if any(ch in rel for ch in "*?[") else [os.path.join(root, rel)]
        for path in candidates:
            data = load_json(path)
            if data is not None:
                return data, os.path.relpath(path, root)
    return None, ""


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if value in (None, ""):
        return []
    return [value]


def rows_from(data: Any, keys: Sequence[str]) -> List[dict]:
    raw: Any = data
    if isinstance(data, dict):
        raw = []
        for key in keys:
            if key in data:
                raw = data.get(key)
                break
    return [item for item in as_list(raw) if isinstance(item, dict)]


def clip_label(value: Any, fallback: str = "") -> str:
    text = str(value or "")
    match = CLIP_RE.search(text)
    if match:
        return f"Clip_{int(match.group(1)):02d}"
    return text.strip() or fallback


def verdict_from(row: dict) -> str:
    raw = str(row.get("verdict") or row.get("severity") or row.get("status") or row.get("result") or "").strip().lower()
    if raw in {"block", "fail", "failed", "red", "error", "critical"}:
        return "block"
    if raw in {"warn", "warning", "yellow", "review", "needs_review"}:
        return "warn"
    if raw in {"ok", "pass", "passed", "green", "true", "match"}:
        return "ok"
    return ""


def boolish_false(value: Any) -> bool:
    return value is False or str(value).strip().lower() in {"false", "no", "0", "mismatch", "fail", "failed"}


def finding(
    verdict: str,
    message: str,
    *,
    shot: Any = "",
    stage: str = "video",
    artifacts: Sequence[str] = (),
    **extra: Any,
) -> dict:
    row = {
        "verdict": verdict,
        "message": message,
        "return_to_stage": stage,
        "affected_artifacts": [str(a) for a in artifacts if a],
    }
    label = clip_label(shot)
    if label:
        row["shot"] = label
        row["affected_shots"] = [label]
    for key, value in extra.items():
        if value not in (None, "", [], {}):
            row[key] = value
    return row


def existing_media(root: str, ep: str) -> List[str]:
    patterns = (
        os.path.join(root, "出视频", ep, "**", "*.mp4"),
        os.path.join(root, "出视频", ep, "**", "*.mov"),
        os.path.join(root, "合成", ep, "**", "*.mp4"),
        os.path.join(root, "合成", ep, "**", "*.mov"),
    )
    out: List[str] = []
    for pattern in patterns:
        out.extend(glob.glob(pattern, recursive=True))
    return sorted(set(out))


def story_text(root: str, ep: str) -> str:
    parts = [
        read_text(os.path.join(root, "脚本", ep, "voiceover.txt")),
        read_text(os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")),
        read_text(os.path.join(root, "出视频", ep, "prompt", "01_clips.md")),
    ]
    data = load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    if data is not None:
        try:
            parts.append(json.dumps(data, ensure_ascii=False))
        except Exception:
            parts.append(str(data))
    return "\n".join(p for p in parts if p)


def has_native_av_route(root: str, ep: str) -> bool:
    rels = (
        os.path.join("生产数据", "video_model_routes.json"),
        os.path.join("出视频", ep, "prompt", "video_model_routes.json"),
        os.path.join("出视频", ep, "prompt", "routes.json"),
    )
    for rel in rels:
        data = load_json(os.path.join(root, rel))
        if data is None:
            continue
        text = json.dumps(data, ensure_ascii=False).lower()
        if any(token in text for token in ("native_audio", "native av", "native_av", "原生音", "多人对话", "dialogue")):
            return True
    return False


def contains_any(text: str, tokens: Iterable[str]) -> bool:
    return any(token.lower() in text.lower() for token in tokens if token)
