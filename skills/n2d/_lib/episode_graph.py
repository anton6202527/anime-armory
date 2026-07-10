#!/usr/bin/env python3
"""Materialize one episode's canonical lineage graph from existing n2d artifacts.

The graph is an index, not a second workflow engine: it derives nodes and edges
from storyboard, route, batch, media, rough-cut, master and release artifacts.
It never changes their status and never replaces `_进度.md` or a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


KIND = "n2d_episode_graph"
VERSION = 1
CLIP_RE = re.compile(r"Clip[_-]?(\d+)", re.IGNORECASE)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _load(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(256 * 1024), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _json_sha(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def clip_id(value: Any, fallback: int = 0) -> str:
    match = CLIP_RE.search(str(value or ""))
    number = int(match.group(1)) if match else fallback
    return f"Clip_{number:02d}" if number > 0 else str(value or "unknown")


def graph_path(root: str | Path, episode: str) -> Path:
    return Path(root) / "生产数据" / f"episode_graph_{episode}.json"


def _source(source_files: list[Dict[str, Any]], root: Path, path: Path, role: str) -> None:
    if not path.is_file():
        return
    rel = _rel(root, path)
    if any(row.get("path") == rel for row in source_files):
        return
    source_files.append({"role": role, "path": rel, "sha256": _sha(path), "bytes": path.stat().st_size})


def build(root: str | Path, episode: str) -> Dict[str, Any]:
    root_path = Path(root).resolve()
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()
    gaps: list[Dict[str, Any]] = []
    sources: list[Dict[str, Any]] = []

    def node(node_id: str, node_type: str, **fields: Any) -> str:
        nodes[node_id] = {"id": node_id, "type": node_type, **fields}
        return node_id

    def edge(source: str, relation: str, target: str) -> None:
        edges.add((source, relation, target))

    episode_node = node(f"episode:{episode}", "episode", episode=episode)
    storyboard_path = root_path / "脚本" / episode / "storyboard.json"
    storyboard = _load(storyboard_path)
    _source(sources, root_path, storyboard_path, "storyboard")
    story_clips: set[str] = set()
    for index, row in enumerate(storyboard.get("clips") or storyboard.get("shots") or [], 1):
        if not isinstance(row, Mapping):
            continue
        cid = clip_id(row.get("id") or row.get("clip"), index)
        story_clips.add(cid)
        nid = node(
            f"clip:{cid}", "story_clip", clip=cid,
            duration_sec=row.get("duration") or row.get("duration_sec"),
            scene=str(row.get("scene") or ""),
        )
        edge(episode_node, "contains", nid)

    route_path = root_path / "出视频" / episode / "prompt" / "video_model_routes.json"
    routes = _load(route_path)
    _source(sources, root_path, route_path, "video_routes")
    routed_clips: set[str] = set()
    for index, row in enumerate(routes.get("routes") or [], 1):
        if not isinstance(row, Mapping):
            continue
        cid = clip_id(row.get("clip_id") or row.get("clip"), index)
        routed_clips.add(cid)
        rid = node(
            f"route:{cid}", "video_route", clip=cid,
            backend=str(row.get("primary_backend") or ""),
            channel=str(row.get("primary_channel") or row.get("channel") or ""),
            executable=bool(row.get("route_executable")),
            execution_state=str((row.get("execution_adapter") or {}).get("state") or ""),
        )
        if f"clip:{cid}" in nodes:
            edge(f"clip:{cid}", "routed_by", rid)
        else:
            gaps.append({"severity": "warn", "code": "route_without_story_clip", "clip": cid, "source": _rel(root_path, route_path)})
    if routes and story_clips:
        for cid in sorted(story_clips - routed_clips):
            gaps.append({"severity": "warn", "code": "story_clip_without_route", "clip": cid})

    batch_paths = sorted((root_path / "生产数据").glob(f"video_batch_{episode}_*.json"))
    batch_paths += sorted((root_path / "生产数据" / "multishot_batches" / episode).glob("*_derived_clips.json"))
    media_nodes: list[str] = []
    for batch_path in batch_paths:
        batch = _load(batch_path)
        if not isinstance(batch.get("items"), list):
            continue
        _source(sources, root_path, batch_path, "video_batch")
        for index, item in enumerate(batch.get("items") or [], 1):
            if not isinstance(item, Mapping):
                continue
            physical = str(item.get("clip") or f"unit_{index:02d}")
            cid = clip_id(item.get("story_clip") or item.get("relay_parent") or physical, index)
            jid = node(
                f"job:{batch_path.stem}:{physical}", "video_job", clip=cid, physical_clip=physical,
                status=str(item.get("status") or "unknown"), provider=str(item.get("cost_provider") or batch.get("backend") or ""),
                adapter_id=str((item.get("execution_adapter") or {}).get("adapter_id") or ""),
                submit_id=str(item.get("submit_id") or ""), source_manifest=_rel(root_path, batch_path),
            )
            if f"route:{cid}" in nodes:
                edge(f"route:{cid}", "executed_as", jid)
            elif f"clip:{cid}" in nodes:
                edge(f"clip:{cid}", "executed_as", jid)
            else:
                gaps.append({"severity": "warn", "code": "video_job_without_story_clip", "clip": cid, "physical_clip": physical})
            raw_target = str(item.get("target_path") or "")
            target = Path(raw_target) if raw_target else root_path / "出视频" / episode / "视频" / str(item.get("target") or "")
            if raw_target and not target.is_absolute():
                target = root_path / target
            if target.is_file():
                rel = _rel(root_path, target)
                mid = node(
                    f"media:{rel}", "video_media", clip=cid, physical_clip=physical, path=rel,
                    sha256=_sha(target), bytes=target.stat().st_size, status=str(item.get("status") or "file_present"),
                )
                media_nodes.append(mid)
                edge(jid, "produced", mid)

    proxy_path = root_path / "生产数据" / f"post_video_proxy_{episode}.json"
    proxy = _load(proxy_path)
    _source(sources, root_path, proxy_path, "rough_cut_manifest")
    proxy_node = ""
    if proxy:
        output = root_path / str(proxy.get("output") or "")
        proxy_node = node(
            f"rough_cut:{episode}", "rough_cut", status=str(proxy.get("status") or "unknown"),
            path=_rel(root_path, output) if output else "", sha256=_sha(output) if output.is_file() else "",
        )
        edge(episode_node, "has_rough_cut", proxy_node)
        timeline_paths = {str(row.get("source") or "") for row in proxy.get("timeline") or [] if isinstance(row, Mapping)}
        for mid in media_nodes:
            media_path = str(nodes[mid].get("path") or "")
            if not timeline_paths or media_path in timeline_paths:
                edge(mid, "included_in", proxy_node)

    master_nodes: list[str] = []
    compose_dir = root_path / "合成" / episode
    if compose_dir.is_dir():
        for master in sorted(compose_dir.rglob("*.mp4")):
            if "_proxy" in master.parts or "_work" in master.parts:
                continue
            rel = _rel(root_path, master)
            mid = node(f"master:{rel}", "delivery_master", path=rel, sha256=_sha(master), bytes=master.stat().st_size)
            master_nodes.append(mid)
            edge(proxy_node or episode_node, "assembled_into", mid)

    release_path = root_path / "生产数据" / f"release_verdict_{episode}.json"
    release = _load(release_path)
    _source(sources, root_path, release_path, "release_verdict")
    if release:
        release_node = node(
            f"release:{episode}", "release_verdict", status=str(release.get("status") or "unknown"),
            profile=str(release.get("profile") or ""), source=_rel(root_path, release_path),
        )
        for master in master_nodes or [episode_node]:
            edge(master, "assessed_by", release_node)

    node_rows = sorted(nodes.values(), key=lambda row: str(row["id"]))
    edge_rows = [
        {"source": source, "relation": relation, "target": target}
        for source, relation, target in sorted(edges)
    ]
    stable = {
        "kind": KIND, "version": VERSION, "root": str(root_path), "episode": episode,
        "nodes": node_rows, "edges": edge_rows, "source_files": sorted(sources, key=lambda row: row["path"]),
        "lineage_gaps": gaps,
    }
    # The project may be copied to another machine.  Absolute root is useful
    # for local diagnostics but must not make an otherwise identical lineage
    # graph look different after a portable handoff.
    graph_hash = _json_sha({key: value for key, value in stable.items() if key != "root"})
    return {
        **stable,
        "generated_at": _now(),
        "graph_hash": graph_hash,
        "summary": {
            "nodes": len(node_rows), "edges": len(edge_rows), "story_clips": len(story_clips),
            "routes": len(routed_clips), "video_media": len(set(media_nodes)), "masters": len(master_nodes),
            "lineage_gaps": len(gaps),
        },
        "status": "warn" if gaps else "pass",
        "authority": "derived index only; _进度.md and existing gates remain authoritative",
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    lines = [
        f"# Episode Graph · {payload.get('episode')}", "",
        f"- 状态：{payload.get('status')}",
        f"- graph hash：`{str(payload.get('graph_hash') or '')[:16]}`",
        f"- nodes / edges：{summary.get('nodes', 0)} / {summary.get('edges', 0)}",
        f"- story / routes / media / masters：{summary.get('story_clips', 0)} / {summary.get('routes', 0)} / {summary.get('video_media', 0)} / {summary.get('masters', 0)}",
        "", "## Lineage gaps", "",
    ]
    gaps = payload.get("lineage_gaps") or []
    lines.extend(["- 无"] if not gaps else [f"- {row.get('severity')} `{row.get('code')}` {row.get('clip') or ''}" for row in gaps])
    lines.extend(["", "> 本图只是现有产物的派生索引，不替代 `_进度.md`、gate 或 release verdict。", ""])
    return "\n".join(lines)


def write(root: str | Path, episode: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, str]:
    data = dict(payload or build(root, episode))
    path = graph_path(root, episode)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    md = path.with_suffix(".md")
    md.write_text(render_markdown(data), encoding="utf-8")
    return {"json": str(path), "markdown": str(md)}


__all__ = ["KIND", "VERSION", "build", "clip_id", "graph_path", "render_markdown", "write"]
