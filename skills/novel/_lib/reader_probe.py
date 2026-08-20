#!/usr/bin/env python3
"""Freshness contract for novel-simulate's scope-bound synthetic probe.

The probe is context-only, but consumers still must not present observations
from an older manuscript as current.  This module keeps scope selection and
snapshot validation in one novel-local implementation.
"""
from __future__ import annotations

import os
from typing import Any

from project_io import list_chapter_files
from report_snapshot import rel_path, snapshot_files, validate_snapshot


OPENING_CHAPTER_LIMIT = 3


def scope_chapter_files(root: str, scope: str, chapter: int | None = None) -> list[tuple[int, str]]:
    chapters = list_chapter_files(root, numbered_only=True)
    if scope == "opening":
        return chapters[:OPENING_CHAPTER_LIMIT]
    if scope == "chapter":
        if chapter is None:
            return []
        return [(number, path) for number, path in chapters if number == int(chapter)]
    return []


def build_reader_probe_snapshot(root: str, scope: str, chapter: int | None = None) -> dict[str, Any]:
    selected = scope_chapter_files(root, scope, chapter)
    if not selected:
        if scope == "chapter":
            raise FileNotFoundError(f"找不到请求的第 {chapter} 章；chapter scope 不允许回退到其它章节")
        raise FileNotFoundError(f"{root}/章节 下没有可用于 opening scope 的编号章节")
    mode = f"reader_probe:{scope}:{chapter if scope == 'chapter' else OPENING_CHAPTER_LIMIT}"
    return snapshot_files(root, [path for _number, path in selected], mode=mode)


def _version(payload: dict[str, Any]) -> int:
    try:
        return int(payload.get("schema_version") or 0)
    except (TypeError, ValueError):
        return 0


def reader_probe_freshness(root: str, payload: Any) -> dict[str, Any]:
    """Return ``fresh|stale|unknown`` without exposing stale signal values.

    v1/v2 never carried a scope-bound snapshot, so their freshness is unknown
    rather than fresh.  v3 is a strict contract: missing/invalid scope or
    snapshot is stale and must be regenerated.
    """
    if not isinstance(payload, dict):
        return {"status": "stale", "reason": "合成叙事探针不是 JSON object；需重跑 novel-simulate。"}
    version = _version(payload)
    if version < 3:
        return {
            "status": "unknown",
            "reason": "reader_panel_signals schema v1/v2 未绑定实际 scope 正文，新鲜度未知；请重跑 novel-simulate 迁移 v3。",
        }
    scope = str(payload.get("scope") or "").strip()
    if scope not in {"opening", "chapter"}:
        return {"status": "stale", "reason": "schema v3 缺少合法 scope；需重跑 novel-simulate。"}
    requested_chapter = payload.get("scope_chapter")
    if scope == "chapter":
        try:
            requested_chapter = int(requested_chapter)
        except (TypeError, ValueError):
            return {"status": "stale", "reason": "chapter scope 缺少 scope_chapter；需重跑 novel-simulate。"}
    else:
        requested_chapter = None

    current = scope_chapter_files(root, scope, requested_chapter)
    if not current:
        if scope == "chapter":
            reason = f"第 {requested_chapter} 章已不存在；合成叙事探针过期，需重跑。"
        else:
            reason = "opening scope 当前没有编号章节；合成叙事探针过期，需重跑。"
        return {"status": "stale", "reason": reason}

    snapshot = payload.get("source_snapshot")
    if not isinstance(snapshot, dict):
        return {"status": "stale", "reason": "schema v3 缺少 source_snapshot；不能证明绑定当前正文，需重跑 novel-simulate。"}
    recorded = snapshot.get("files")
    if not isinstance(recorded, list):
        return {"status": "stale", "reason": "source_snapshot.files 无效；需重跑 novel-simulate。"}
    current_paths = [rel_path(root, path) for _number, path in current]
    recorded_paths = [str(item.get("path") or "") for item in recorded if isinstance(item, dict)]
    if current_paths != recorded_paths:
        return {
            "status": "stale",
            "reason": "合成叙事探针的实际 scope 文件集合已变化（含新增/删除章）；需重跑 novel-simulate。",
        }
    ok, reason = validate_snapshot(root, snapshot)
    if not ok:
        return {"status": "stale", "reason": reason.replace("review/score", "novel-simulate")}
    return {
        "status": "fresh",
        "reason": "source_snapshot 与当前实际 scope 正文一致",
        "scope": scope,
        "chapters": [number for number, _path in current],
        "aggregate_hash": snapshot.get("aggregate_hash") or "",
    }


def sanitized_reader_probe(payload: dict[str, Any], freshness: dict[str, Any]) -> dict[str, Any]:
    """Keep current signals only when fresh; sanitize stale/legacy payloads."""
    status = freshness.get("status")
    if status == "fresh":
        out = dict(payload)
        out["freshness"] = freshness
        return out
    return {
        "schema_version": payload.get("schema_version"),
        "kind": payload.get("kind") or "novel_synthetic_reader_probe",
        "scope": payload.get("scope"),
        "chapters_read": payload.get("chapters_read") or [],
        "evidence_type": "synthetic_probe",
        "decision_authority": "context_only",
        "numeric_score_eligible": False,
        "signal_only": True,
        "freshness": freshness,
        "surface_signals": {},
        "perspectives": {},
        "note": "stale/legacy signal values intentionally omitted from consumer view",
    }
