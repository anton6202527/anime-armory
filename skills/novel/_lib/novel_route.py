#!/usr/bin/env python3
"""Shared progress-table routing for the novel pipeline."""
from __future__ import annotations

import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from novel_contract import (
        PROGRESS_DONE,
        PROGRESS_ROUGH_PREFIX,
        PROGRESS_TODO,
        routing_stages,
        stage_specs,
    )
except ImportError:
    from .novel_contract import (
        PROGRESS_DONE,
        PROGRESS_ROUGH_PREFIX,
        PROGRESS_TODO,
        routing_stages,
        stage_specs,
    )

STAGES = routing_stages()
META_COLS = {"章节", "字数", "序号", "#", "标题"}

# 章节号解析 第N章
_FULLWIDTH = {ord("０") + i: ord("0") + i for i in range(10)}
_CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CH_TOKEN = r"[\d０-９一二三四五六七八九十百零〇两]+"
CH_ROW_RE = re.compile(r"^\|\s*第\s*" + _CH_TOKEN + r"\s*章\s*\|")

def _cn_to_int(s: str) -> Optional[int]:
    s = s.translate(_FULLWIDTH).strip()
    if s.isdigit():
        return int(s)
    if not s:
        return None
    total = section = 0
    for ch in s:
        if ch in ("十", "百"):
            unit = 10 if ch == "十" else 100
            section = (section or 1) * unit
            total += section
            section = 0
        elif ch in _CN_DIGIT:
            section = _CN_DIGIT[ch]
        else:
            return None
    return total + section

def chapter_number(value: str) -> Optional[int]:
    text = (value or "").strip()
    m = re.search(r"第\s*(" + _CH_TOKEN + r")\s*章", text)
    token = m.group(1) if m else re.sub(r"^\s*第|\s*章\s*$", "", text).strip()
    if not token or not re.fullmatch(_CH_TOKEN, token):
        return None
    return _cn_to_int(token)

def cell_state(v: str) -> str:
    v = (v or "").strip()
    if v == PROGRESS_DONE:
        return "done"
    if v.startswith(PROGRESS_ROUGH_PREFIX):
        return "rough"
    if v in ("—", "-", "N/A", "n/a", "无"):
        return "na"
    if v in (PROGRESS_TODO, ""):
        return "todo"
    return "todo"

def is_done(v: str) -> bool:
    return cell_state(v) in ("done", "na")

def progress_path(root: str) -> str:
    return os.path.join(root, "_进度.md")

def parse_progress(root: str) -> Tuple[List[str], List[Dict[str, str]]]:
    p = progress_path(root)
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    content = open(p, encoding="utf-8").read()
    
    try:
        from markdown_parser import parse_markdown_table
    except ImportError:
        from .markdown_parser import parse_markdown_table
        
    try:
        # Novels might use "章节" or "章" as identifier
        header, raw_rows = parse_markdown_table(content, header_identifier="章节")
    except ValueError:
        try:
            header, raw_rows = parse_markdown_table(content, header_identifier="章")
        except ValueError as e:
            raise ValueError(str(e))
        
    rows: List[Dict[str, str]] = []
    for r in raw_rows:
        ch = r.get("章节") or r.get("章") or r.get("_pk", "")
        num = chapter_number(ch)
        if num is not None:
            r["_ch"] = ch
            r["_num"] = num
            rows.append(r)
            
    return header, rows

def stage_of(root: str, row: Dict[str, str], header: List[str]) -> Dict[str, Optional[str]]:
    ch = row.get("_ch") or row.get("章节") or row.get("章") or ""
    
    specs = stage_specs()
    for spec in specs:
        label = spec["label"]
        if label not in header:
            continue
            
        val = row.get(label, "")
        if not is_done(val):
            skill = spec["skill"]
            cmd = f"npx skills run {skill} {{root}} {{ch}}"
            return {
                "ch": ch,
                "col": label,
                "label": label,
                "skill": skill,
                "cmd": cmd,
                "note": ""
            }
            
    return {"ch": ch, "col": None, "label": "✅已完结", "skill": None, "cmd": None, "note": ""}

def format_route(root: str, route: Dict[str, Optional[str]]) -> str:
    ch = route.get("ch") or ""
    label = route.get("label") or ""
    cmd = route.get("cmd")
    return f"{ch}: {label}" if not cmd else f"{ch}: {label}  → {cmd.format(root=root, ch=ch)}"

def summarize(root: str) -> Dict[str, object]:
    try:
        header, rows = parse_progress(root)
    except Exception as e:
        return {"error": str(e)}
        
    routes = [stage_of(root, r, header) for r in sorted(rows, key=lambda x: x["_num"])]
    first = next((r for r in routes if r.get("cmd")), None)
    done = sum(1 for r in routes if not r.get("cmd"))
    bottleneck: Dict[str, int] = {}
    for r in routes:
        if r.get("cmd"):
            label = str(r["label"])
            bottleneck[label] = bottleneck.get(label, 0) + 1
    return {"header": header, "rows": rows, "routes": routes, "first": first, "done": done, "bottleneck": bottleneck}
