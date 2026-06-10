#!/usr/bin/env python3
"""Shared per-project settings helpers.

The user-facing convention lives in `skills/_偏好约定.md`. This module only
implements deterministic read/write helpers for `_设置.md`; it does not ask
questions or infer preferences.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional


DEFAULTS = {
    "制作模式": "配音先行",
    "基础视觉风格": "写实电影感",
    "生图AI": "Codex",
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
    """Return a setting value from common markdown forms."""
    key_pattern = rf"(?:\*\*)?{re.escape(key)}(?:\*\*)?"
    pat = re.compile(rf"^\s*(?:[-*]\s*)?{key_pattern}\s*[:：]\s*(.+?)\s*$", re.M)
    m = pat.search(text)
    if not m:
        return None
    val = re.split(r"\s+#", m.group(1), maxsplit=1)[0].strip()
    return val or None


def load_settings(work_root: str) -> Dict[str, str]:
    """Parse `<作品根>/_设置.md` into `{key: value}` without global defaults."""
    text = _read_text(os.path.join(work_root.rstrip("/"), "_设置.md"))
    out: Dict[str, str] = {}
    pat = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?([^:：#]+?)(?:\*\*)?\s*[:：]\s*(.+?)\s*$", re.M)
    for m in pat.finditer(text):
        key = m.group(1).strip()
        val = re.split(r"\s+#", m.group(2), maxsplit=1)[0].strip()
        if key and key not in out:
            out[key] = val
    return out


def write_settings(work_root: str, fields: Dict[str, str], *, note: Optional[str] = None, bold_keys: bool = False):
    """Write `<作品根>/_设置.md` for per-work private choices."""
    lines = ["# 设置 — 本作私有选择点（_偏好约定）", ""]
    if note:
        lines += [f"> {note}", ""]

    for k, v in fields.items():
        shown = v if v not in (None, "", []) else "（未定）"
        key_str = f"**{k}**" if bold_keys else k
        lines.append(f"- {key_str}：{shown}")

    lines += [
        "",
        "> 这些值由 init 按 CLI 参数/全局默认落定；同项目后续**沉默沿用**，"
        "改了在此更新。合规/不可逆/花钱多的点每次仍向用户确认。",
    ]

    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


GLOBAL_SETTINGS_CANDIDATES = (
    "创作偏好-默认.md",
    os.path.join(".agents", "创作偏好-默认.md"),
    os.path.join(".codex", "创作偏好-默认.md"),
    os.path.join(".claude", "创作偏好-默认.md"),
)


def global_settings_paths(repo_root: str) -> List[str]:
    return [os.path.join(repo_root, rel) for rel in GLOBAL_SETTINGS_CANDIDATES]


def global_settings_path(repo_root: str) -> str:
    for path in global_settings_paths(repo_root):
        if os.path.exists(path):
            return path
    return global_settings_paths(repo_root)[0]


def get_setting(work_root: str, key: str, default: Optional[str] = None) -> str:
    """Read a setting from `<作品根>/_设置.md`, then global defaults, then fallback."""
    work_root = work_root.rstrip("/")
    project = _extract_setting(_read_text(os.path.join(work_root, "_设置.md")), key)
    if project:
        return project
    repo = repo_root_from(work_root)
    for path in global_settings_paths(repo):
        global_val = _extract_setting(_read_text(path), key)
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


def is_native_av(work_root: str) -> bool:
    """`制作模式=原生音画`: speaking shots use native synchronized A/V."""
    mode = production_mode(work_root)
    return "原生音画" in mode or "native_av" in mode.lower()


def watermark_setting(work_root: str) -> str:
    return get_setting(work_root, "水印", DEFAULTS["水印"])
