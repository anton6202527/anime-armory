#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Typed content-dependency DAG and minimal downstream invalidation planning."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(root: Path, path: str | Path) -> str:
    return os.path.relpath(Path(path), root).replace(os.sep, "/")


def _chapter_number(path: str) -> int:
    match = re.search(r"第0*(\d+)章", path)
    return int(match.group(1)) if match else 0


def build_graph(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    def add_node(relpath: str, node_type: str) -> None:
        path = root_path / relpath
        nodes[relpath] = {
            "id": relpath, "type": node_type, "exists": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else "",
        }

    def add_edge(source: str, target: str, edge_type: str, reason: str) -> None:
        if source in nodes and target in nodes:
            edge = {"source": source, "target": target, "type": edge_type, "reason": reason}
            if edge not in edges:
                edges.append(edge)

    contracts = [
        "_meta.json", "_设置.md", "设定/author_intent.json", "设定/创作蓝图.md",
        "设定/读者契约.md", "设定/章纲.md", "设定/scene_cards.json", "设定/人物.md",
        "设定/角色卡.md", "设定/世界观.md",
    ]
    for path in contracts:
        add_node(path, "contract")
    chapters = sorted(
        [rel(root_path, path) for path in glob.glob(str(root_path / "章节" / "第*.md"))],
        key=_chapter_number,
    )
    for path in chapters:
        add_node(path, "chapter")
        number = _chapter_number(path)
        delta = f"审稿/state_delta_第{number:02d}章.json"
        add_node(delta, "state_delta")
    ledgers = [
        "审稿/state_ledger.json", "设定/动态百科.json", "设定/foreshadowing_ledger.json",
        "设定/knowledge_ledger.json", "设定/timeline.json",
    ]
    reports = ["审稿/review_report.json", "评分/score_report.json", "修订/revision_plan.json"]
    releases = ["导出/release_manifest.json", "导出/completion_verdict.json", "导出/final_acceptance.json"]
    exports = [rel(root_path, path) for path in glob.glob(str(root_path / "导出" / "*")) if Path(path).is_file()]
    for path in ledgers:
        add_node(path, "ledger")
    for path in reports:
        add_node(path, "report")
    for path in sorted(set(exports + releases)):
        add_node(path, "release" if path in releases else "export")

    for contract in contracts:
        for chapter in chapters:
            add_edge(contract, chapter, "story_contract", "chapter must obey this story contract")
    for index, chapter in enumerate(chapters):
        number = _chapter_number(chapter)
        delta = f"审稿/state_delta_第{number:02d}章.json"
        add_edge(chapter, delta, "state_extraction", "state delta is extracted from chapter semantics")
        for ledger in ledgers:
            add_edge(delta, ledger, "state_merge", "canonical state ledger consumes chapter delta")
        if index + 1 < len(chapters):
            add_edge(chapter, chapters[index + 1], "continuity", "later chapter carries prior facts, knowledge and open threads")
        for report in reports[:2]:
            add_edge(chapter, report, "snapshot", "full-manuscript report hashes chapter bytes")
        for export in exports:
            add_edge(chapter, export, "render", "export contains chapter content")
    add_edge("审稿/review_report.json", "修订/revision_plan.json", "finding", "revision tasks consume review findings")
    add_edge("评分/score_report.json", "修订/revision_plan.json", "finding", "revision tasks consume score actions")
    for source in [*chapters, *reports, *exports, "_meta.json", "_设置.md"]:
        add_edge(source, "导出/release_manifest.json", "release_digest", "release digest binds current artifact hash")
    add_edge("导出/release_manifest.json", "导出/completion_verdict.json", "completion", "machine readiness derives from release manifest")
    add_edge("导出/release_manifest.json", "导出/final_acceptance.json", "acceptance", "acceptance receipt binds release digest")
    add_edge("导出/final_acceptance.json", "导出/completion_verdict.json", "completion", "accepted verdict requires current receipt")
    return {
        "schema_version": 1,
        "kind": "novel_content_dependency_graph",
        "generated_at": now_iso(),
        "project_root": str(root_path),
        "nodes": sorted(nodes.values(), key=lambda row: row["id"]),
        "edges": sorted(edges, key=lambda row: (row["source"], row["target"], row["type"])),
    }


def invalidation_plan(graph: dict[str, Any], changed: Iterable[str], *, change_kind: str = "semantic") -> dict[str, Any]:
    changed_ids = [str(path).replace(os.sep, "/").lstrip("./") for path in changed]
    allowed = {
        "prose_only": {"snapshot", "render", "release_digest", "completion", "acceptance"},
        "state": {"state_extraction", "state_merge", "continuity", "snapshot", "render", "finding", "release_digest", "completion", "acceptance"},
        "semantic": None,
        "structure": None,
    }.get(change_kind)
    adjacency: dict[str, list[dict[str, str]]] = {}
    for edge in graph.get("edges") or []:
        if allowed is not None and edge.get("type") not in allowed:
            continue
        adjacency.setdefault(edge["source"], []).append(edge)
    queue = list(changed_ids)
    seen = set(changed_ids)
    causes: dict[str, list[dict[str, str]]] = {}
    while queue:
        source = queue.pop(0)
        for edge in adjacency.get(source, []):
            target = edge["target"]
            causes.setdefault(target, []).append(edge)
            if target not in seen:
                seen.add(target)
                queue.append(target)
    affected = sorted(seen - set(changed_ids))
    return {
        "schema_version": 1,
        "kind": "novel_content_invalidation_plan",
        "generated_at": now_iso(),
        "change_kind": change_kind,
        "changed": changed_ids,
        "affected": affected,
        "affected_count": len(affected),
        "causes": {key: value for key, value in causes.items() if key in affected},
        "minimality_note": "only typed downstream edges allowed by change_kind are traversed; no directory-wide blanket invalidation",
    }
