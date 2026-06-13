#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared Markdown parsing library for Anime Armory progress files.

Provides stable, unified methods to read and update Markdown checklists
and tables across all production lines (n2d, novel, song, mv).
"""
import fcntl
import os
import re
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple, Any

CHECK_RE = re.compile(r"^(\s*-\s*)\[([ xX])\]\s*(.*?)\s*$")
STAGE_RE = re.compile(r"<!--\s*stage:([a-z_]+)\s*-->")
COMMENT_RE = re.compile(r"\s*<!--.*?-->\s*")


@contextmanager
def file_lock(lock_path: str):
    """Exclusive file lock for safe atomic writes."""
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    with open(lock_path, "w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def atomic_write_text(path: str, text: str):
    """Write text atomically using a temporary file."""
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def parse_checklist(content: str) -> List[Dict[str, Any]]:
    """Parse Markdown checklist items into a structured list.
    
    Returns a list of dicts: {"line": int, "section": str, "item": str, "stage": str|None, "state": "done"|"todo"}
    """
    items = []
    section = "未分组"
    has_machine_schema = "novel-progress-schema" in content or "machine-readable" in content
    
    for lineno, raw in enumerate(content.splitlines(), 1):
        line = raw.rstrip("\n")
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        
        m = CHECK_RE.match(line)
        if m:
            state_char = m.group(2)
            state = "done" if state_char in "xX" else "todo"
            raw_item = m.group(3).strip()
            
            sm = STAGE_RE.search(raw_item)
            if has_machine_schema and not sm:
                continue
            
            item = COMMENT_RE.sub("", raw_item).strip()
            items.append({
                "line": lineno,
                "section": section,
                "item": item,
                "stage": sm.group(1) if sm else None,
                "state": state
            })
    return items


def update_checklist_stage(content: str, stage_key: str, state: str) -> Tuple[str, bool]:
    """Update a specific stage in a Markdown checklist to 'done' or 'todo'.
    
    Returns (new_content, changed_boolean).
    """
    if state not in {"done", "todo"}:
        raise ValueError("state must be 'done' or 'todo'")
    mark = "x" if state == "done" else " "
    changed = False
    found = False
    out = []
    
    for raw in content.splitlines(keepends=True):
        if f"stage:{stage_key}" in raw and re.match(r"^(\s*-\s*)\[[ xX]\]", raw):
            found = True
            new = re.sub(r"^(\s*-\s*)\[[ xX]\]", rf"\1[{mark}]", raw, count=1)
            if new != raw:
                changed = True
            out.append(new)
        else:
            out.append(raw)
            
    if not found:
        raise KeyError(f"stage not found in checklist: {stage_key}")
        
    return "".join(out), changed


def parse_markdown_table(content: str, header_identifier: str = "集") -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse a Markdown table into a header list and a list of row dicts.
    
    Locates the table by finding a header row containing `header_identifier`.
    """
    header = None
    rows = []
    
    for ln in content.splitlines():
        if header is None:
            if re.match(r"^\|\s*" + re.escape(header_identifier) + r"\s*\|", ln):
                header = [c.strip() for c in ln.split("|")[1:-1]]
            continue
            
        if header and ln.startswith("|") and not re.match(r"^\|[\s\-:]+\|$", ln):
            cells = [c.strip() for c in ln.split("|")[1:len(header) + 1]]
            if len(cells) >= 1:
                row = dict(zip(header, cells))
                # Store the primary key (first column) automatically
                row["_pk"] = cells[0]
                rows.append(row)
                
    if header is None:
        raise ValueError(f"未找到包含表头标识 '{header_identifier}' 的 Markdown 表格")
    return header, rows


def update_markdown_table_cell(content: str, pk_col_index: int, pk_value: str, target_col_index: int, new_value: str) -> Tuple[str, bool]:
    """Update a specific cell in a Markdown table.
    
    Returns (new_content, changed_boolean).
    """
    out = []
    changed = False
    found = False
    in_table = False
    
    for raw in content.splitlines(keepends=True):
        is_table_row = raw.strip().startswith("|")
        if is_table_row:
            in_table = True
            cells = raw.split("|")
            # Account for empty strings before first | and after last |
            if len(cells) > max(pk_col_index, target_col_index):
                # Clean PK value check (strip whitespace and handle potential markup)
                cell_pk = cells[pk_col_index].strip()
                if pk_value in cell_pk:
                    found = True
                    old_val = cells[target_col_index].strip()
                    if old_val != new_value:
                        cells[target_col_index] = f" {new_value} "
                        changed = True
                    out.append("|".join(cells))
                    continue
        elif in_table:
            # We left the table
            in_table = False
            
        out.append(raw)
        
    if not found:
        raise KeyError(f"Row with PK '{pk_value}' not found in table.")
        
    return "".join(out), changed
