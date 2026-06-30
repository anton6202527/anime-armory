#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight semantic response schemas for novel semantic jobs.

No external jsonschema dependency is used here; these checks are intentionally
small but strict enough to stop unbound free-form prose from entering machine
artifacts.
"""
from __future__ import annotations

from typing import Any


SCHEMAS: dict[str, dict[str, Any]] = {
    "score_assessment": {
        "required": {
            "score_task_id": "str",
            "scores": "list",
            "deductions": "list",
        },
        "optional": {
            "title_check": "dict",
            "adaptation_check": "dict",
            "verdict": "str",
        },
    },
    "ledger_reconcile": {
        "required": {
            "chapter": "int",
            "status": "str",
            "notes": "str",
        },
        "optional": {
            "chapter_file_hash": "str",
            "delta_hash": "str",
        },
        "allowed": {
            "status": {"ok", "passed", "pass", "verified", "通过"},
        },
    },
    "market_evidence_search": {
        "required": {
            "platform": "str",
            "date": "str",
            "source": "str",
            "summary": "str",
            "url": "str",
        },
        "optional": {
            "query": "str",
            "confidence": "str",
        },
    },
}


def _type_ok(value: Any, type_name: str) -> bool:
    if type_name == "str":
        return isinstance(value, str) and bool(value.strip())
    if type_name == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "list":
        return isinstance(value, list)
    if type_name == "dict":
        return isinstance(value, dict)
    if type_name == "bool":
        return isinstance(value, bool)
    return True


def validate_payload(schema_ref: str, payload: Any, required_fields: list[str] | None = None) -> list[str]:
    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["response must be a JSON object"]
    for field in required_fields or []:
        if field not in payload:
            issues.append(f"missing required field: {field}")
    schema = SCHEMAS.get(schema_ref)
    if not schema:
        return issues
    for field, type_name in (schema.get("required") or {}).items():
        if field not in payload:
            issues.append(f"missing schema field: {field}")
            continue
        if not _type_ok(payload[field], type_name):
            issues.append(f"field {field} must be {type_name}")
    for field, allowed in (schema.get("allowed") or {}).items():
        if field in payload and str(payload[field]) not in allowed:
            issues.append(f"field {field} has unsupported value: {payload[field]!r}")
    return issues


def schema_contract(schema_ref: str) -> dict[str, Any]:
    schema = SCHEMAS.get(schema_ref) or {}
    return {
        "schema_ref": schema_ref,
        "required": schema.get("required") or {},
        "optional": schema.get("optional") or {},
        "allowed": {k: sorted(v) for k, v in (schema.get("allowed") or {}).items()},
    }
