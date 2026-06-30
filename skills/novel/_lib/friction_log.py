#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production-time friction "埋点" for the novel-* line.

When a novel-* stage skill hits friction at production time — a gate it had to
waive, a degraded fallback, a low/needs-rework verdict — it appends ONE
structured signal line to ``<作品根>/生产数据/优化信号.jsonl``. The signal is a
note-to-future-self, NOT a human-facing message: ``novel-review`` mode② (流程自审,
``self_audit.py``) ingests these on the next run and surfaces unresolved ones as
process-optimization findings. This closes the loop so that simply re-running the
pipeline keeps re-triggering self-optimization without the user re-explaining.

Pattern: detection is scattered across the pipeline (each stage reports its own
friction here), while resolution is funnelled into self-audit. Detection is
report-only; nothing self-edits skills — humans/self-audit decide what to change.

Append is idempotent per ``signature`` (kind + scoped key): a re-run that hits the
same friction does NOT bloat the log; only genuinely new friction is recorded.
"""
import hashlib
import json
import os
from datetime import date, datetime


SIGNAL_LOG_REL = os.path.join("生产数据", "优化信号.jsonl")

# Severity vocabulary kept tiny on purpose: advice < warn < block.
SEVERITIES = ("advice", "warn", "block")


def signal_log_path(root):
    return os.path.join(root, SIGNAL_LOG_REL)


def _signature(kind, key):
    raw = f"{kind}::{key or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def make_signal(kind, *, skill, severity, title, detail,
                suggested_fix="", evidence=None, key=""):
    """Build (don't persist) one optimization signal.

    key: a stable scope string so re-runs of the *same* friction collapse to one
    signal (e.g. the gate name + baseline_date). Empty key → kind-level dedupe.
    """
    if severity not in SEVERITIES:
        severity = "advice"
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return {
        "id": f"FRICTION-{kind.upper().replace('_', '-')}-{stamp}",
        "schema_version": 1,
        "kind": kind,
        "skill": skill,
        "severity": severity,
        "created_at": date.today().isoformat(),
        "title": title,
        "detail": detail,
        "suggested_fix": suggested_fix,
        "evidence": evidence or {},
        "signature": _signature(kind, key),
        "status": "open",
    }


def load_signals(root):
    path = signal_log_path(root)
    if not os.path.exists(path):
        return []
    out = []
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
                out.append(payload)
    return out


def open_signatures(root):
    return {
        s.get("signature")
        for s in load_signals(root)
        if str(s.get("status") or "open") == "open"
    }


def log_friction(root, kind, *, skill, severity, title, detail,
                 suggested_fix="", evidence=None, key=""):
    """Append one optimization signal unless an open one with the same signature
    already exists. Returns the signal dict (existing or new), or None if root is
    falsy. Never raises on a write error — instrumentation must not break a run.
    """
    if not root:
        return None
    signal = make_signal(
        kind, skill=skill, severity=severity, title=title, detail=detail,
        suggested_fix=suggested_fix, evidence=evidence, key=key,
    )
    try:
        if signal["signature"] in open_signatures(root):
            return signal
        path = signal_log_path(root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(signal, ensure_ascii=False) + "\n")
    except OSError:
        return signal
    return signal


def resolve_signals(root, signatures):
    """Mark matching signals resolved (rewrites the log). Used once a friction is
    addressed so it stops re-surfacing. Best-effort; tolerant of a missing log."""
    path = signal_log_path(root)
    if not os.path.exists(path):
        return 0
    signals = load_signals(root)
    want = set(signatures or [])
    n = 0
    for s in signals:
        if s.get("signature") in want and str(s.get("status") or "open") == "open":
            s["status"] = "resolved"
            s["resolved_at"] = date.today().isoformat()
            n += 1
    if n:
        with open(path, "w", encoding="utf-8") as f:
            for s in signals:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return n
