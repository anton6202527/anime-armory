#!/usr/bin/env python3
"""Shared settings helpers for the novel2drama/n2d pipeline.

The user-facing convention lives in `skills/_偏好约定.md`.  This module only
implements the read-only parts that scripts need for deterministic routing and
gates; it intentionally does not ask questions or write private preferences.
"""
from __future__ import annotations

import os
import re
from typing import Optional


DEFAULTS = {
    "制作模式": "配音先行",
    "生图AI": "Codex only",
    "生视频AI": "即梦",
    "出视频规格": "预算一般",
    "视频原生音轨": "丢弃",
    "水印": "AI合规标识",
    "字幕语言": "中文",
}


def repo_root_from(path: str) -> str:
    """Walk upward until the repository root is found."""
    d = os.path.abspath(path)
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "skills")):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(path)


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _extract_setting(text: str, key: str) -> Optional[str]:
    """Return a setting value from common markdown forms.

    Supported forms:
      - `- 制作模式: 配音先行`
      - `制作模式: 配音先行`
      - `制作模式：配音先行`
    Inline comments are stripped.  The first matching line wins inside a file;
    project settings are read before global defaults.
    """
    pat = re.compile(rf"^\s*(?:[-*]\s*)?{re.escape(key)}\s*[:：]\s*(.+?)\s*$", re.M)
    m = pat.search(text)
    if not m:
        return None
    val = re.split(r"\s+#", m.group(1), maxsplit=1)[0].strip()
    return val or None


def global_settings_path(repo_root: str) -> str:
    return os.path.join(repo_root, ".claude", "创作偏好-默认.md")


def get_setting(work_root: str, key: str, default: Optional[str] = None) -> str:
    """Read a setting from `<作品根>/_设置.md`, then global defaults, then fallback."""
    work_root = work_root.rstrip("/")
    project = _extract_setting(_read_text(os.path.join(work_root, "_设置.md")), key)
    if project:
        return project
    repo = repo_root_from(work_root)
    global_val = _extract_setting(_read_text(global_settings_path(repo)), key)
    if global_val:
        return global_val
    if default is not None:
        return default
    return DEFAULTS.get(key, "")


def production_mode(work_root: str) -> str:
    mode = get_setting(work_root, "制作模式", DEFAULTS["制作模式"])
    return mode or DEFAULTS["制作模式"]


def is_video_first(work_root: str) -> bool:
    return "先出视频" in production_mode(work_root)


def watermark_setting(work_root: str) -> str:
    return get_setting(work_root, "水印", DEFAULTS["水印"])

