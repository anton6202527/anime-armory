#!/usr/bin/env python3
"""Build a transitive impact graph for n2d consistency review."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
try:
    from n2d_contract import CONSISTENCY_DEPENDENCY_GRAPH_KIND
except Exception:  # pragma: no cover - standalone fallback
    CONSISTENCY_DEPENDENCY_GRAPH_KIND = "n2d_consistency_dependency_graph"


ENTITY_RE = re.compile(r"\b(?:CHAR|LOC|PROP|WEAPON|OUTFIT|VFX|MOTIF)_[A-Za-z0-9_]+\b")
CLIP_RE = re.compile(r"(?:Clip|CLIP)[ _-]?(\d{1,4})")
MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".m4v", ".wav", ".mp3"}


def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def normalize_clip_id(value: Any, idx: Optional[int] = None) -> str:
    raw = str(value or "").strip()
    m = CLIP_RE.search(raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    if raw:
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")
        return safe or (f"Clip_{idx:02d}" if idx else "Clip_00")
    return f"Clip_{idx:02d}" if idx else "Clip_00"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except Exception:
        return path.as_posix()


def _node(nodes: Dict[str, Dict[str, Any]], node_id: str, kind: str, label: str, **attrs: Any) -> None:
    row = nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label})
    for key, value in attrs.items():
        if value not in (None, "", [], {}):
            row[key] = value


def _edge(edges: List[Dict[str, Any]], src: str, dst: str, rel: str, **attrs: Any) -> None:
    if not src or not dst:
        return
    item = {"from": src, "to": dst, "relation": rel}
    item.update({k: v for k, v in attrs.items() if v not in (None, "", [], {})})
    if item not in edges:
        edges.append(item)


def _entity_ids(value: Any) -> List[str]:
    if isinstance(value, str):
        return list(dict.fromkeys(ENTITY_RE.findall(value)))
    if isinstance(value, Mapping):
        out: List[str] = []
        for v in value.values():
            out.extend(_entity_ids(v))
        return list(dict.fromkeys(out))
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        out: List[str] = []
        for v in value:
            out.extend(_entity_ids(v))
        return list(dict.fromkeys(out))
    return []


def _clip_from_path(path: Path) -> str:
    m = CLIP_RE.search(path.stem)
    return f"Clip_{int(m.group(1)):02d}" if m else ""


def _iter_media(folder: Path) -> Iterable[Path]:
    if not folder.is_dir():
        return []
    return (p for p in sorted(folder.rglob("*")) if p.is_file() and p.suffix.lower() in MEDIA_EXTS)


def _add_registry_nodes(root: Path, nodes: Dict[str, Dict[str, Any]]) -> None:
    reg = _load(root / "出图" / "共享" / "identity_registry.json") or {}
    for char in reg.get("characters") or []:
        if isinstance(char, Mapping) and char.get("id"):
            _node(nodes, f"entity:{char.get('id')}", "character", str(char.get("name") or char.get("id")), source="identity_registry")
    assets = _load(root / "出图" / "共享" / "asset_registry.json") or {}
    for asset in assets.get("assets") or []:
        if isinstance(asset, Mapping) and asset.get("id"):
            _node(nodes, f"entity:{asset.get('id')}", str(asset.get("type") or "asset"), str(asset.get("name") or asset.get("id")), source="asset_registry")


def _add_storyboard(root: Path, ep: str, nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
    path = root / "脚本" / ep / "storyboard.json"
    data = _load(path) or {}
    clips = data.get("clips") if isinstance(data, Mapping) else []
    clip_ids: List[str] = []
    _node(nodes, f"episode:{ep}", "episode", ep, path=_rel(root, path) if path.exists() else "")
    for idx, clip in enumerate(clips or [], 1):
        if not isinstance(clip, Mapping):
            continue
        cid = normalize_clip_id(clip.get("id") or clip.get("clip_id"), idx)
        clip_ids.append(cid)
        _node(
            nodes,
            f"clip:{cid}",
            "clip",
            cid,
            path=_rel(root, path),
            shot_type=clip.get("template") or clip.get("shot_type"),
            loc=clip.get("loc") or clip.get("location_id"),
        )
        _edge(edges, f"episode:{ep}", f"clip:{cid}", "contains")
        for entity_id in _entity_ids(clip):
            _node(nodes, f"entity:{entity_id}", "entity", entity_id, source="storyboard_reference")
            _edge(edges, f"entity:{entity_id}", f"clip:{cid}", "referenced_by_clip")
    return clip_ids


def _add_routes(root: Path, ep: str, nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
    path = root / "出视频" / ep / "prompt" / "video_model_routes.json"
    data = _load(path) or {}
    for route in (data.get("routes") if isinstance(data, Mapping) else []) or []:
        if not isinstance(route, Mapping):
            continue
        cid = normalize_clip_id(route.get("clip_id"))
        rid = f"route:{cid}"
        _node(nodes, rid, "route", cid, path=_rel(root, path), primary_backend=route.get("primary_backend"), policy_winner=(route.get("policy_resolution") or {}).get("winner") if isinstance(route.get("policy_resolution"), Mapping) else "")
        _edge(edges, f"clip:{cid}", rid, "routed_as")
        primary = str(route.get("primary_backend") or "")
        if primary:
            bid = f"backend:{primary}"
            _node(nodes, bid, "backend", primary)
            _edge(edges, bid, rid, "executes")
        for backend in route.get("fallback_backends") or []:
            bid = f"backend:{backend}"
            _node(nodes, bid, "backend", str(backend))
            _edge(edges, rid, bid, "fallback_backend")


def _add_media(root: Path, ep: str, nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
    images_by_clip: Dict[str, List[str]] = {}
    for path in _iter_media(root / "出图" / ep / "图片"):
        cid = _clip_from_path(path)
        nid = f"image:{_rel(root, path)}"
        _node(nodes, nid, "image", path.name, path=_rel(root, path))
        if cid:
            images_by_clip.setdefault(cid, []).append(nid)
            _edge(edges, f"clip:{cid}", nid, "renders_image")
    videos_by_clip: Dict[str, List[str]] = {}
    for path in _iter_media(root / "出视频" / ep / "视频"):
        cid = _clip_from_path(path)
        nid = f"video:{_rel(root, path)}"
        _node(nodes, nid, "video", path.name, path=_rel(root, path))
        if cid:
            videos_by_clip.setdefault(cid, []).append(nid)
            _edge(edges, f"clip:{cid}", nid, "renders_video")
            _edge(edges, f"route:{cid}", nid, "executes_route")
            for image_id in images_by_clip.get(cid, []):
                _edge(edges, image_id, nid, "image_to_video")
    finals: List[str] = []
    for path in _iter_media(root / "合成" / ep):
        if "成片" not in path.name:
            continue
        nid = f"final:{_rel(root, path)}"
        finals.append(nid)
        _node(nodes, nid, "final_video", path.name, path=_rel(root, path))
    for final_id in finals:
        for vids in videos_by_clip.values():
            for vid in vids:
                _edge(edges, vid, final_id, "composed_into")


def _add_evidence(root: Path, ep: str, nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
    prod = root / "生产数据"
    patterns = [
        f"score_{ep}.json",
        f"consistency_ledger_{ep}.json",
        f"contract_inheritance_{ep}.json",
        f"intentional_discontinuity_{ep}.json",
        f"native_voice_identity_{ep}.json",
        f"audio_space_consistency_{ep}.json",
        f"motion_grammar_consistency_{ep}.json",
        f"expression_state_consistency_{ep}.json",
    ]
    for name in patterns:
        path = prod / name
        if not path.exists():
            continue
        nid = f"evidence:{name}"
        _node(nodes, nid, "evidence", name, path=_rel(root, path))
        _edge(edges, f"episode:{ep}", nid, "has_evidence")


def _descendants(edges: Sequence[Mapping[str, Any]], starts: Sequence[str]) -> List[str]:
    forward: Dict[str, List[str]] = {}
    for edge in edges:
        forward.setdefault(str(edge.get("from")), []).append(str(edge.get("to")))
    seen = set(starts)
    q: deque[str] = deque(starts)
    out: List[str] = []
    while q:
        cur = q.popleft()
        for nxt in forward.get(cur, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            out.append(nxt)
            q.append(nxt)
    return out


def impact_plan(graph: Mapping[str, Any], changed: Sequence[str]) -> Dict[str, Any]:
    nodes = {str(n.get("id")): n for n in graph.get("nodes") or [] if isinstance(n, Mapping)}
    starts: List[str] = []
    for raw in changed:
        token = str(raw)
        candidates = [token, f"entity:{token}", f"clip:{normalize_clip_id(token)}"]
        starts.extend(c for c in candidates if c in nodes and c not in starts)
    impacted = _descendants(graph.get("edges") or [], starts)
    return {
        "changed": list(changed),
        "start_nodes": starts,
        "impacted_nodes": impacted,
        "impacted_clips": sorted({n.split(":", 1)[1] for n in impacted if n.startswith("clip:")}),
        "impacted_media": [n for n in impacted if n.startswith(("image:", "video:", "final:"))],
    }


def build_graph(root: str | Path, ep: str, changed: Sequence[str] = ()) -> Dict[str, Any]:
    root = Path(root)
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    _add_registry_nodes(root, nodes)
    clip_ids = _add_storyboard(root, ep, nodes, edges)
    _add_routes(root, ep, nodes, edges)
    _add_media(root, ep, nodes, edges)
    _add_evidence(root, ep, nodes, edges)
    graph: Dict[str, Any] = {
        "kind": CONSISTENCY_DEPENDENCY_GRAPH_KIND,
        "version": 1,
        "root": str(root),
        "episode": ep,
        "nodes": sorted(nodes.values(), key=lambda x: str(x.get("id"))),
        "edges": edges,
        "summary": {
            "nodes": len(nodes),
            "edges": len(edges),
            "clips": len(clip_ids),
            "images": sum(1 for n in nodes if n.startswith("image:")),
            "videos": sum(1 for n in nodes if n.startswith("video:")),
        },
    }
    if changed:
        graph["impact_plan"] = impact_plan(graph, changed)
    return graph


def write_graph(graph: Mapping[str, Any], root: str | Path, ep: str) -> Path:
    path = Path(root) / "生产数据" / f"consistency_dependency_graph_{ep}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--changed", action="append", default=[], help="Changed entity/clip id, e.g. CHAR_01 or Clip_03")
    ap.add_argument("--write", action="store_true")
    ns = ap.parse_args(argv)
    graph = build_graph(ns.root, ns.episode, ns.changed)
    if ns.write:
        path = write_graph(graph, ns.root, ns.episode)
        graph["path"] = str(path)
    print(json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
