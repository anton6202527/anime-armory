#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Total context allocation with explicit inclusion and obligation receipts."""
from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def allocate_sections(
    sections: Iterable[Mapping[str, Any]],
    *,
    max_chars: int,
    reserved_chars: int = 0,
    minimum_slice: int = 240,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Allocate one total budget; required obligations are never silently dropped."""
    normalized = []
    for index, raw in enumerate(sections):
        text = str(raw.get("text") or "")
        normalized.append({
            "id": str(raw.get("id") or f"section_{index}"),
            "text": text,
            "priority": int(raw.get("priority") or 0),
            "required": bool(raw.get("required")),
            "obligations": [str(item) for item in raw.get("obligations") or [] if str(item)],
            "index": index,
        })
    available = max(0, int(max_chars) - max(0, int(reserved_chars)))
    allocation: dict[str, str] = {}
    records = []
    used = 0
    ordered = sorted(normalized, key=lambda row: (not row["required"], -row["priority"], row["index"]))
    for row in ordered:
        text = row["text"]
        remaining = max(0, available - used)
        if not text:
            included, status = "", "empty"
        elif row["required"]:
            included, status = text, "included_required"
        elif len(text) <= remaining:
            included, status = text, "included"
        elif remaining >= minimum_slice:
            marker = "\n...（上下文总预算截断；按 receipt.source_paths 回读原文件）"
            included = text[:max(0, remaining - len(marker))].rstrip() + marker
            status = "truncated"
        else:
            included, status = "", "dropped"
        allocation[row["id"]] = included
        used += len(included)
        records.append({
            "id": row["id"], "status": status, "required": row["required"],
            "priority": row["priority"], "original_chars": len(text),
            "included_chars": len(included), "source_sha256": sha256_text(text),
            "obligations": row["obligations"],
        })
    obligation_status: dict[str, str] = {}
    for record in records:
        for obligation in record["obligations"]:
            state = "covered" if record["included_chars"] else "missing"
            if obligation_status.get(obligation) != "covered":
                obligation_status[obligation] = state
    receipt = {
        "schema_version": 1,
        "kind": "novel_context_budget_receipt",
        "max_chars": int(max_chars),
        "reserved_chars": int(reserved_chars),
        "available_optional_chars": available,
        "allocated_chars": used,
        "over_budget_due_to_required": used > available,
        "sections": sorted(records, key=lambda row: next(item["index"] for item in normalized if item["id"] == row["id"])),
        "obligation_coverage": obligation_status,
        "missing_obligations": sorted(key for key, state in obligation_status.items() if state != "covered"),
    }
    return allocation, receipt
