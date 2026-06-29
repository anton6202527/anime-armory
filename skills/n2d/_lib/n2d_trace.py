#!/usr/bin/env python3
"""Trace helpers shared by n2d supervisor, batch and dashboard events."""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
import uuid
from typing import Any, Dict, Optional


TRACE_KIND = "n2d_trace_context"
TRACE_VERSION = 1


def _clean(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff.]+", "_", text)
    return text.strip("_") or "na"


def stable_root_hash(root: str) -> str:
    return hashlib.sha256(os.path.abspath(root).encode("utf-8")).hexdigest()[:12]


def new_trace_context(
    root: str,
    episode: Optional[str],
    stage_key: str,
    *,
    action: str = "",
    parent_trace_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    inherited = os.environ.get("N2D_TRACE_ID") or parent_trace_id
    if inherited:
        trace_id = inherited
    else:
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        nonce = uuid.uuid4().hex[:8]
        trace_id = f"tr_{_clean(stage_key)}_{stable_root_hash(root)}_{ts}_{nonce}"
    span_id = hashlib.sha256(
        f"{trace_id}|{episode or ''}|{stage_key}|{action}|{uuid.uuid4().hex}".encode("utf-8")
    ).hexdigest()[:16]
    idem = idempotency_key or os.environ.get("N2D_IDEMPOTENCY_KEY") or ""
    return {
        "kind": TRACE_KIND,
        "version": TRACE_VERSION,
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_trace_id": parent_trace_id or os.environ.get("N2D_PARENT_TRACE_ID") or "",
        "idempotency_key": idem,
        "root_hash": stable_root_hash(root),
        "episode": episode or "",
        "stage_key": stage_key,
        "action": action,
    }


def trace_env(trace: Dict[str, Any]) -> Dict[str, str]:
    env = {
        "N2D_TRACE_ID": str(trace.get("trace_id") or ""),
        "N2D_PARENT_TRACE_ID": str(trace.get("parent_trace_id") or trace.get("trace_id") or ""),
        "N2D_SPAN_ID": str(trace.get("span_id") or ""),
    }
    if trace.get("idempotency_key"):
        env["N2D_IDEMPOTENCY_KEY"] = str(trace["idempotency_key"])
    return env


def enrich_meta(meta: Optional[Dict[str, Any]], trace: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(meta or {})
    for key in ("trace_id", "span_id", "parent_trace_id", "idempotency_key"):
        if trace.get(key) and not out.get(key):
            out[key] = trace[key]
    return out
