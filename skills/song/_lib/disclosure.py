#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared AI-usage + 授权 disclosure plumbing for all production lines.

Every line (novel / song / mv / ad …) writes a publishing-facing disclosure pair
`<作品根>/合规/ai_usage.json` + `合规/AI使用说明.md`. The *content* (which fields,
which 说明 wording, which usage-mode choices) is line-specific and stays in each
`*-craft/scripts/ai_usage.py`; only the IO, the universal payload fields, and the
markdown skeleton live here — the single source of truth so the four copies can no
longer drift. Mirrors how `settings.py` / `text_utils.py` were promoted to common.

This module owns NO business semantics: no stage tables, no per-line field sets.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

import io_utils  # sibling in 本线 _lib（vendored，与 disclosure 同目录）

COMPLIANCE_DIR = "合规"
JSON_NAME = "ai_usage.json"
MD_NAME = "AI使用说明.md"


def load_meta(root: str) -> Dict:
    """Read `<root>/_meta.json`, returning `{}` when absent."""
    return io_utils.load_meta(root)


def resolve_root_or_exit(project_root: str) -> str:
    """Absolutize + verify the work root; exit(2) with the standard message if missing."""
    root = os.path.abspath(project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    return root


def base_payload(
    root: str,
    kind: str,
    meta: Optional[Dict] = None,
    *,
    title: Optional[str] = None,
    publish_target: str = "未定",
    human_contribution: str = "",
) -> Dict:
    """Build the 7 universal disclosure fields; callers `.update()` line-specific ones.

    `title` falls back to `meta['title']` then the folder name — pass an explicit
    value to add line-specific fallbacks (e.g. novel's `source_title`).
    """
    meta = meta or {}
    return {
        "schema_version": 1,
        "kind": kind,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": title or meta.get("title") or os.path.basename(root),
        "publish_target": publish_target,
        "human_contribution": human_contribution,
    }


def render_markdown(
    payload: Dict,
    *,
    md_title: str,
    field_lines: Iterable[str],
    notes: Iterable[str],
    contribution_placeholder: str,
) -> str:
    """Render the fixed disclosure skeleton; `field_lines`/`notes` are line-specific."""
    lines: List[str] = [
        f"# {md_title}",
        "",
        f"- 生成日期：{payload['generated_at']}",
        f"- 项目：{payload['project_root']}",
        *field_lines,
        "",
        "## 人工贡献记录",
        payload["human_contribution"] or contribution_placeholder,
        "",
        "## 说明",
        *notes,
    ]
    return "\n".join(lines) + "\n"


def write(
    root: str,
    payload: Dict,
    *,
    md_title: str,
    field_lines: Iterable[str],
    notes: Iterable[str],
    contribution_placeholder: str,
) -> Tuple[str, str]:
    """Write both disclosure files under `<root>/合规/`; return (json_path, md_path)."""
    compliance_dir = os.path.join(root, COMPLIANCE_DIR)
    os.makedirs(compliance_dir, exist_ok=True)
    json_path = os.path.join(compliance_dir, JSON_NAME)
    md_path = os.path.join(compliance_dir, MD_NAME)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(
            render_markdown(
                payload,
                md_title=md_title,
                field_lines=field_lines,
                notes=notes,
                contribution_placeholder=contribution_placeholder,
            )
        )
    return json_path, md_path
