#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared `_进度.md` stage-table parsing for the read-only progress reporters.

song / mv / ad each route the public `progress` skill to their own
`*-craft/scripts/progress.py`, which scans a `## …阶段…` markdown table and reports
the current frontier. The *table scan* (section scoping + cell extraction + header /
separator skip) was copy-implemented 3× with subtly diverging column layouts (ad is
2-col `阶段|状态`, song/mv are 3-col `阶段|skill|状态`) — exactly the kind of drift a
single source of truth prevents. This module owns ONLY that pure scan; per-line state
classification, frontier rules, hints and printing stay in each `*-craft`.

No business semantics live here: no stage tables, no gate rules.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence


def parse_stage_rows(
    text: str,
    *,
    section_keywords: Sequence[str],
    require_all: bool = False,
    min_cols: int = 2,
    label_col: int = 0,
    status_col: int = -1,
    owner_col: Optional[int] = None,
) -> List[Dict[str, str]]:
    """Extract stage rows from the markdown table under a matching `## …` section.

    A `## ` header opens the target section when its text contains the
    `section_keywords` (any one by default, or all when `require_all=True`); the
    section runs until the next `## ` header. Within it, pipe-rows are parsed into
    `{"label", "status"[, "owner"]}` dicts. Header (`阶段`) and separator (`---`)
    rows and rows with fewer than `min_cols` cells are skipped. Column indices are
    explicit so each line keeps its exact layout.
    """
    keywords = list(section_keywords)
    rows: List[Dict[str, str]] = []
    in_section = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_section = all(k in s for k in keywords) if require_all else any(k in s for k in keywords)
            continue
        if not in_section or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < min_cols:
            continue
        label = cells[label_col]
        if label in ("阶段", "") or set(label) <= set("-: "):
            continue
        row = {"label": label, "status": cells[status_col]}
        if owner_col is not None:
            row["owner"] = cells[owner_col]
        rows.append(row)
    return rows
