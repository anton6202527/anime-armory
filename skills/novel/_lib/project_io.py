#!/usr/bin/env python3
"""Shared project IO helpers for the self-contained novel family."""
from __future__ import annotations

import os
import re
from typing import List, Optional, Sequence, Tuple

from settings import get_setting, load_settings


CHAPTER_FALLBACK_NUMBER = 10 ** 6
TEXT_EXTENSIONS = (".md", ".txt")


def read_text(path: str, default: str = "", *, errors: str = "replace") -> str:
    try:
        with open(path, encoding="utf-8", errors=errors) as f:
            return f.read()
    except OSError:
        return default


def chapter_number_from_name(name: str) -> Optional[int]:
    match = re.search(r"(\d+)", os.path.basename(name or ""))
    return int(match.group(1)) if match else None


def chapter_label(chapter: int) -> str:
    return f"第{int(chapter):02d}章"


def parse_chapter_range(value) -> Optional[Tuple[int, int]]:
    if value in (None, ""):
        return None
    if isinstance(value, tuple):
        return value
    text = str(value).strip()
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    if text.isdigit():
        number = int(text)
        return number, number
    raise ValueError(f"章节范围应为 'N' 或 'N-M'，收到：{value!r}")


def _allowed_extension(name: str, extensions: Sequence[str]) -> bool:
    lowered = name.lower()
    return any(lowered.endswith(ext.lower()) for ext in extensions)


def list_chapter_files(
    project: str,
    chapter_range=None,
    single: Optional[int] = None,
    *,
    extensions: Sequence[str] = TEXT_EXTENSIONS,
    fill_missing_numbers: bool = False,
    numbered_only: bool = False,
) -> List[Tuple[int, str]]:
    """Return chapter files as ``[(chapter_number, path)]`` in natural order.

    ``fill_missing_numbers=True`` preserves wiki_builder's historical behavior:
    unnumbered chapter-like files get their sorted sequence number. Otherwise
    they use a high fallback number, matching older review/balance scripts.
    """
    chapter_dir = os.path.join(project, "章节")
    if not os.path.isdir(chapter_dir):
        return []
    rng = parse_chapter_range(chapter_range)
    items = []
    for name in os.listdir(chapter_dir):
        if name.startswith("_") or not _allowed_extension(name, extensions):
            continue
        number = chapter_number_from_name(name)
        if numbered_only and number is None:
            continue
        items.append([number, os.path.join(chapter_dir, name), name])
    items.sort(key=lambda item: (item[0] is None, item[0] if item[0] is not None else item[2], item[2]))
    out = []
    for seq, (number, path, _name) in enumerate(items, 1):
        idx = seq if number is None and fill_missing_numbers else (number or CHAPTER_FALLBACK_NUMBER)
        if single is not None and idx != single:
            continue
        if rng is not None and not (rng[0] <= idx <= rng[1]):
            continue
        out.append((idx, path))
    return out


def read_chapters(
    project: str,
    chapter_range=None,
    single: Optional[int] = None,
    *,
    extensions: Sequence[str] = TEXT_EXTENSIONS,
    fill_missing_numbers: bool = False,
    numbered_only: bool = False,
) -> List[Tuple[int, str, str]]:
    return [
        (idx, path, read_text(path))
        for idx, path in list_chapter_files(
            project,
            chapter_range,
            single,
            extensions=extensions,
            fill_missing_numbers=fill_missing_numbers,
            numbered_only=numbered_only,
        )
    ]


def find_chapter_file(
    project: str,
    chapter: int,
    *,
    extensions: Sequence[str] = TEXT_EXTENSIONS,
) -> str:
    matches = [
        path
        for idx, path in list_chapter_files(project, extensions=extensions)
        if idx == int(chapter)
    ]
    if not matches:
        chapter_dir = os.path.join(project, "章节")
        raise FileNotFoundError(f"找不到第 {chapter} 章：{chapter_dir}/{chapter_label(chapter)}*.md")
    return matches[0]


def load_project_settings(project: str):
    return load_settings(project)


def get_project_setting(project: str, key: str, default: Optional[str] = None) -> str:
    return get_setting(project, key, default)
