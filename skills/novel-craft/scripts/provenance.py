#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append-only provenance log for novel workflow artifacts."""
from __future__ import annotations

import hashlib
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any

from store import file_lock


PROVENANCE_KIND = "novel_provenance_event"
PROVENANCE_REL = os.path.join("生产数据", "provenance.jsonl")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _rel(root: str, path: str) -> str:
    return os.path.relpath(os.path.abspath(path), os.path.abspath(root)).replace(os.sep, "/")


def _artifact_rel(root: str, path: str) -> str:
    abs_path = path if os.path.isabs(path) else os.path.join(root, path)
    return _rel(root, abs_path)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact(root: str, path: str) -> dict[str, Any]:
    abs_path = path if os.path.isabs(path) else os.path.join(root, path)
    payload: dict[str, Any] = {
        "path": _rel(root, abs_path),
        "exists": os.path.exists(abs_path),
    }
    if os.path.isfile(abs_path):
        payload.update({
            "sha256": sha256_file(abs_path),
            "size_bytes": os.path.getsize(abs_path),
        })
    return payload


def _coerce_paths(value: list[str] | tuple[str, ...] | None) -> list[str]:
    return [str(item) for item in (value or []) if str(item or "").strip()]


def append_event(
    root: str,
    *,
    event_type: str,
    tool: str,
    inputs: list[str] | tuple[str, ...] | None = None,
    outputs: list[str] | tuple[str, ...] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one provenance event and return the event payload.

    The log is intentionally JSONL instead of one mutable JSON document so long
    runs can recover even if a later stage is interrupted.
    """
    root = os.path.abspath(root)
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(root, PROVENANCE_REL)
    event = {
        "schema_version": 1,
        "kind": PROVENANCE_KIND,
        "event_type": str(event_type or ""),
        "tool": str(tool or ""),
        "created_at": _now(),
        "project_root": root,
        "inputs": [_artifact(root, path) for path in _coerce_paths(inputs)],
        "outputs": [_artifact(root, path) for path in _coerce_paths(outputs)],
        "metadata": metadata or {},
    }
    line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    with file_lock(log_path + ".lock"):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return event


def read_events(root: str) -> list[dict[str, Any]]:
    path = os.path.join(os.path.abspath(root), PROVENANCE_REL)
    if not os.path.exists(path):
        return []
    events: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def events_for_artifact(root: str, artifact_path: str) -> list[dict[str, Any]]:
    root = os.path.abspath(root)
    target = _artifact_rel(root, artifact_path)
    hits: list[dict[str, Any]] = []
    for event in read_events(root):
        input_paths = [item.get("path") for item in event.get("inputs") or [] if isinstance(item, dict)]
        output_paths = [item.get("path") for item in event.get("outputs") or [] if isinstance(item, dict)]
        if target in input_paths or target in output_paths:
            payload = dict(event)
            payload["artifact_role"] = "output" if target in output_paths else "input"
            hits.append(payload)
    return hits


def lineage_for_artifact(root: str, artifact_path: str, *, max_depth: int = 4) -> dict[str, Any]:
    root = os.path.abspath(root)
    target = _artifact_rel(root, artifact_path)
    events = read_events(root)
    producers: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        for output in event.get("outputs") or []:
            if isinstance(output, dict) and output.get("path"):
                producers.setdefault(str(output["path"]), []).append(event)

    visited: set[str] = set()

    def walk(path: str, depth: int) -> dict[str, Any]:
        if depth > max_depth or path in visited:
            return {"path": path, "truncated": depth > max_depth}
        visited.add(path)
        producing_events = producers.get(path) or []
        nodes = []
        for event in producing_events[-3:]:
            inputs = []
            for item in event.get("inputs") or []:
                if not isinstance(item, dict) or not item.get("path"):
                    continue
                inputs.append(walk(str(item["path"]), depth + 1))
            nodes.append({
                "event_type": event.get("event_type"),
                "tool": event.get("tool"),
                "created_at": event.get("created_at"),
                "metadata": event.get("metadata") or {},
                "inputs": inputs,
            })
        return {"path": path, "producers": nodes}

    return {
        "schema_version": 1,
        "kind": "novel_artifact_lineage",
        "project_root": root,
        "artifact": target,
        "lineage": walk(target, 0),
    }


def openlineage_events(root: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, event in enumerate(read_events(root), 1):
        meta = event.get("metadata") or {}
        run_id = str(meta.get("run_id") or meta.get("job_id") or f"{event.get('event_type')}_{idx}")
        out.append({
            "eventType": "COMPLETE",
            "eventTime": event.get("created_at"),
            "producer": "anime-armory/novel",
            "job": {
                "namespace": "novel",
                "name": event.get("tool") or event.get("event_type"),
            },
            "run": {
                "runId": run_id,
                "facets": {
                    "novel_event": {
                        "_producer": "anime-armory/novel",
                        "_schemaURL": "local://novel_provenance_event",
                        "event_type": event.get("event_type"),
                        "metadata": meta,
                    },
                },
            },
            "inputs": [
                {
                    "namespace": "file",
                    "name": item.get("path"),
                    "facets": {"sha256": {"value": item.get("sha256")}},
                }
                for item in event.get("inputs") or [] if isinstance(item, dict)
            ],
            "outputs": [
                {
                    "namespace": "file",
                    "name": item.get("path"),
                    "facets": {"sha256": {"value": item.get("sha256")}},
                }
                for item in event.get("outputs") or [] if isinstance(item, dict)
            ],
        })
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="novel provenance query helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    events = sub.add_parser("events", help="print all provenance events")
    events.add_argument("project_root")

    lineage = sub.add_parser("lineage", help="print recursive lineage for one artifact")
    lineage.add_argument("project_root")
    lineage.add_argument("artifact")
    lineage.add_argument("--max-depth", type=int, default=4)

    artifact = sub.add_parser("artifact-events", help="print events mentioning one artifact")
    artifact.add_argument("project_root")
    artifact.add_argument("artifact")

    ol = sub.add_parser("openlineage", help="export OpenLineage-like events")
    ol.add_argument("project_root")

    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    if args.cmd == "events":
        print(json.dumps(read_events(root), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "lineage":
        print(json.dumps(lineage_for_artifact(root, args.artifact, max_depth=args.max_depth), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "artifact-events":
        print(json.dumps(events_for_artifact(root, args.artifact), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "openlineage":
        print(json.dumps(openlineage_events(root), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
