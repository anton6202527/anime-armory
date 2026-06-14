#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared waiver logging for novel-* gate bypasses."""
import json
import os
from datetime import date, datetime


WAIVER_LOG_REL = os.path.join("审稿", "waiver_log.jsonl")


def waiver_log_path(root):
    return os.path.join(root, WAIVER_LOG_REL)


def make_waiver(waiver_type, *, reason, affected_gate, source, details=None, scope=None):
    day = date.today().isoformat()
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return {
        "id": f"WAIVER-{waiver_type.upper().replace('_', '-')}-{stamp}",
        "type": waiver_type,
        "created_at": day,
        "reason": reason,
        "affected_gate": affected_gate,
        "source": source,
        "details": details or {},
        "scope": scope or {},
    }


def append_waiver(root, waiver):
    path = waiver_log_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = dict(waiver)
    payload.setdefault("created_at", date.today().isoformat())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def load_waivers(root):
    path = waiver_log_path(root)
    if not os.path.exists(path):
        return []
    waivers = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict):
                waivers.append(payload)
    return waivers


def waiver_matches(waiver, waiver_type, scope=None):
    if waiver.get("type") != waiver_type:
        return False
    if not scope:
        return True
    waiver_scope = waiver.get("scope")
    if not isinstance(waiver_scope, dict):
        return False
    for key, value in scope.items():
        if str(waiver_scope.get(key) or "") != str(value or ""):
            return False
    return True


def has_waiver(waivers, waiver_type, scope=None):
    return any(waiver_matches(w, waiver_type, scope) for w in waivers)


def baseline_freshness_scope(freshness):
    freshness = freshness or {}
    return {
        "baseline_date": str(freshness.get("baseline_date") or ""),
        "freshness_status": str(freshness.get("status") or ""),
    }
