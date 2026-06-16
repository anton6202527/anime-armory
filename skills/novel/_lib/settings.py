#!/usr/bin/env python3
"""Minimal per-project settings helpers for the novel family.

Novel has no settings skill or CLI. This module only reads and writes
`_设置.md` plus private global defaults for init/score scripts.
"""
from __future__ import annotations

import os
import re
import time
from typing import Dict, List, Optional


DEFAULTS = {
    "权利来源": "未声明",
    "输出格式": "txt+docx",
    "小说生成模式": "稳妥初稿",
    "小说生成工作流": "默认单步",
    "章节生成粒度": "逐章",
    "发行地区": "未定",
    "AI使用披露": "AI-assisted",
}

GLOBAL_SETTINGS_CANDIDATES = (
    "创作偏好-默认.md",
    os.path.join(".agents", "创作偏好-默认.md"),
    os.path.join(".codex", "创作偏好-默认.md"),
    os.path.join(".claude", "创作偏好-默认.md"),
)

SETTING_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?([^\n:：#]+?)(?:\*\*)?\s*[:：]\s*(.+?)\s*$"
)


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


def _looks_like_record_line(line: str) -> bool:
    stripped = re.sub(r"^[-*]\s*", "", line.strip())
    return bool(re.match(r"\d{4}-\d{2}-\d{2}\b", stripped))


def _settings_region_lines(text: str) -> List[str]:
    lines: List[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if re.match(r"^##+\s*记录\b", stripped):
            break
        if not stripped or stripped.startswith(">") or stripped.startswith("#"):
            continue
        if _looks_like_record_line(stripped):
            continue
        lines.append(raw)
    return lines


def _extract_setting(text: str, key: str) -> Optional[str]:
    key_pattern = rf"(?:\*\*)?{re.escape(key)}(?:\*\*)?"
    pat = re.compile(rf"^\s*(?:[-*]\s*)?{key_pattern}\s*[:：]\s*(.+?)\s*$", re.M)
    for line in _settings_region_lines(text):
        match = pat.match(line)
        if match:
            value = re.split(r"\s+#", match.group(1), maxsplit=1)[0].strip()
            return value or None
    return None


def load_settings(work_root: str) -> Dict[str, str]:
    """Parse `<作品根>/_设置.md` into `{key: value}` without defaults."""
    text = _read_text(os.path.join(work_root.rstrip("/"), "_设置.md"))
    out: Dict[str, str] = {}
    for line in _settings_region_lines(text):
        match = SETTING_LINE_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = re.split(r"\s+#", match.group(2), maxsplit=1)[0].strip()
        if key and key not in out:
            out[key] = normalize_setting_value(key, value)
    return out


def append_record(work_root: str, message: str, *, date: Optional[str] = None) -> None:
    """Append a human-readable change record to `<作品根>/_设置.md`."""
    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    content = _read_text(path)
    if not content:
        content = "# 设置 — 本作私有选择点（skills/novel-craft/references/选择点与偏好.md）\n"
    lines = content.splitlines()
    entry = f"- {date or time.strftime('%Y-%m-%d')} {message}"
    for idx, line in enumerate(lines):
        if re.match(r"^##+\s*记录\b", line.strip()):
            lines.insert(idx + 1, entry)
            break
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["## 记录", entry])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def write_settings(
    work_root: str,
    fields: Dict[str, str],
    *,
    note: Optional[str] = None,
    bold_keys: bool = False,
) -> None:
    """Rewrite `<作品根>/_设置.md` for per-work private choices."""
    lines = ["# 设置 — 本作私有选择点（skills/novel-craft/references/选择点与偏好.md）", ""]
    if note:
        lines += [f"> {note}", ""]

    for key, value in fields.items():
        shown = value if value not in (None, "", []) else "（未定）"
        key_text = f"**{key}**" if bold_keys else key
        lines.append(f"- {key_text}：{shown}")

    lines += [
        "",
        "> 这些值由 init 按 CLI 参数/全局默认落定；同项目后续**沉默沿用**，"
        "改了在此更新。合规/不可逆/花钱多的点每次仍向用户确认。",
    ]

    os.makedirs(work_root.rstrip("/"), exist_ok=True)
    path = os.path.join(work_root.rstrip("/"), "_设置.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    append_record(work_root, "项目设置初始化（继承自 CLI/全局默认）")


def global_settings_paths(repo_root: str) -> List[str]:
    return [os.path.join(repo_root, rel) for rel in GLOBAL_SETTINGS_CANDIDATES]


def global_settings_path(repo_root: str) -> str:
    for path in global_settings_paths(repo_root):
        if os.path.exists(path):
            return path
    return global_settings_paths(repo_root)[0]


def normalize_setting_value(key: str, value: str) -> str:
    """Normalize historical aliases that should not leak into novel execution."""
    normalized = (value or "").strip()
    if key == "篇幅档" and normalized in {"抖音漫剧", "红果短剧"}:
        return "漫剧"
    if key == "小说生成工作流" and normalized in {"三段式", "Trio", "trio"}:
        return "三步迭代"
    return normalized


def get_setting(work_root: str, key: str, default: Optional[str] = None) -> str:
    """Read project setting, then private global defaults, then fallback."""
    work_root = work_root.rstrip("/")
    project = _extract_setting(_read_text(os.path.join(work_root, "_设置.md")), key)
    if project:
        return normalize_setting_value(key, project)
    repo = repo_root_from(work_root)
    for path in global_settings_paths(repo):
        global_value = _extract_setting(_read_text(path), key)
        if global_value:
            return normalize_setting_value(key, global_value)
    if default is not None:
        return normalize_setting_value(key, default)
    return normalize_setting_value(key, DEFAULTS.get(key, ""))
