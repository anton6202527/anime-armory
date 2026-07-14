#!/usr/bin/env python3
"""Build a compact context pack for one n2d stage.

The pack is intentionally small and deterministic: it lists the exact files an
agent should inspect, with hashes and short previews, instead of forcing the
agent to read every SKILL.md/reference in the n2d tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_action_registry import context_pack_relpath, stage_action_spec  # noqa: E402
import genre_packs  # noqa: E402


KIND = "n2d_context_pack"
VERSION = 1
MAX_TEXT_CHARS = 2400


STAGE_FILES = {
    "script_stage1": [
        "_设置.md",
        "_进度.md",
        "开发包/series_bible.md",
        "开发包/adaptation_strategy.json",
        "开发包/season_arc.json",
        "开发包/production_feasibility.json",
        "开发包/pilot_greenlight.md",
        "脚本/{ep}/raw.txt",
        "设定库/中段开工前情资产包.md",
    ],
    "script_stage2": [
        "_设置.md",
        "_进度.md",
        "脚本/{ep}/director_beat_sheet.json",
        "脚本/{ep}/axis_blocking_map.json",
        "脚本/{ep}/shot_progression_plan.json",
        "脚本/{ep}/transition_map.json",
        "脚本/{ep}/vertical_composition_plan.json",
        "脚本/{ep}/edit_rhythm_map.json",
        "生产数据/director_blocking_pack_{ep}.md",
        "脚本/{ep}/voiceover.txt",
        "脚本/{ep}/bgm.txt",
        "出图/共享/identity_registry.json",
    ],
    "image_prompt": [
        "_设置.md",
        "_进度.md",
        "脚本/{ep}/storyboard.json",
        "脚本/{ep}/素材清单.md",
        "出图/共享/identity_registry.json",
        "出图/共享/asset_registry.json",
        "生产数据/spectacle_plan_{ep}.json",
    ],
    "image": [
        "_设置.md",
        "_进度.md",
        "出图/{ep}/prompt/01_分镜出图.md",
        "出图/共享/identity_registry.json",
        "出图/共享/asset_registry.json",
        "生产数据/reference_pack_{ep}.json",
    ],
    "video_prompt": [
        "_设置.md",
        "_进度.md",
        "脚本/{ep}/storyboard.json",
        "生产数据/video_model_routes_{ep}.json",
        "生产数据/spectacle_sequence_plan_{ep}.json",
        "出图/共享/asset_registry.json",
    ],
    "video": [
        "_设置.md",
        "_进度.md",
        "出视频/{ep}/prompt/01_分镜出视频.md",
        "生产数据/video_model_routes_{ep}.json",
        "生产数据/contract_inheritance_{ep}.json",
    ],
    "compose": [
        "_设置.md",
        "_进度.md",
        "脚本/{ep}/镜头时长.json",
        "生产数据/action_edit_cues_{ep}.json",
        "生产数据/video_qc_{ep}.json",
    ],
    "review": [
        "_设置.md",
        "_进度.md",
        "生产数据/score_{ep}.json",
        "生产数据/consistency_ledger_{ep}.json",
        "生产数据/review_ui_findings_{ep}.json",
    ],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def preview_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    out = "\n".join(lines[:80])
    if len(out) > MAX_TEXT_CHARS:
        out = out[:MAX_TEXT_CHARS].rstrip() + "\n..."
    return out


def preview_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"preview": preview_text(path)}
    if isinstance(data, dict):
        keys = list(data.keys())[:40]
        summary = {key: data.get(key) for key in keys if key in {"kind", "version", "episode", "summary", "status", "verdict", "stage", "clips", "graph_hash"}}
        summary["top_level_keys"] = keys
        return summary
    if isinstance(data, list):
        return {"items": len(data), "first": data[0] if data else None}
    return {"value": data}


def episode_number(ep: str) -> Optional[int]:
    import re

    m = re.search(r"\d+", str(ep or ""))
    return int(m.group(0)) if m else None


def likely_midstart(root: Optional[Path], ep: str) -> bool:
    """Infer a middle-start job from local structure.

    A mid-start context pack is mandatory when the project begins from a later
    episode/chapter without earlier raw context. For normal sequential projects
    it is optional: include it if the file exists, but don't report it missing.
    """
    n = episode_number(ep)
    if root is None or not n or n <= 1:
        return False
    return not (root / "脚本" / "第1集" / "raw.txt").is_file()


def candidate_relpaths(stage_key: str, ep: str, root: Optional[Path] = None) -> List[str]:
    base = ["_设置.md", "_进度.md"]
    items = STAGE_FILES.get(stage_key, base)
    out: List[str] = []
    for item in items:
        rel = item.format(ep=ep)
        if rel == "设定库/中段开工前情资产包.md":
            path_exists = bool(root and (root / rel).is_file())
            if not path_exists and not likely_midstart(root, ep):
                continue
        if rel not in out:
            out.append(rel)
    graph_rel = f"生产数据/episode_graph_{ep}.json"
    if graph_rel not in out:
        out.append(graph_rel)
    return out


def collect_files(root: Path, relpaths: Iterable[str]) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    for rel in relpaths:
        path = root / rel
        item: Dict[str, Any] = {"relpath": rel, "exists": path.is_file()}
        if path.is_file():
            item["bytes"] = path.stat().st_size
            item["sha256"] = sha256_file(path)
            item["preview"] = preview_json(path) if path.suffix == ".json" else preview_text(path)
        files.append(item)
    return files


def build_pack(root: str, ep: str, stage_key: str) -> Dict[str, Any]:
    root_path = Path(root)
    action = stage_action_spec(stage_key)
    files = collect_files(root_path, candidate_relpaths(stage_key, ep, root_path))
    genre_context = genre_packs.build_context(root_path, ep, stage_key)
    return {
        "kind": KIND,
        "version": VERSION,
        "root": root,
        "episode": ep,
        "stage_key": stage_key,
        "action_contract": action,
        "genre_pack_context": genre_context,
        "files": files,
        "missing_required_files": [f["relpath"] for f in files if not f.get("exists")],
        "usage": {
            "read_order": [f["relpath"] for f in files if f.get("exists")],
            "rule": "Use this pack first; open full references only when the pack points to a missing contract or ambiguity.",
        },
    }


def render_markdown(pack: Dict[str, Any]) -> str:
    lines = [
        "# n2d Context Pack",
        "",
        f"- 集：{pack.get('episode')}",
        f"- 阶段：{pack.get('stage_key')}",
        f"- specialist：{(pack.get('action_contract') or {}).get('specialist')}",
        "",
        "## Files",
        "",
        "| file | exists | bytes | sha256 |",
        "|---|---:|---:|---|",
    ]
    for item in pack.get("files") or []:
        sha = str(item.get("sha256") or "")[:12]
        lines.append(f"| {item.get('relpath')} | {item.get('exists')} | {item.get('bytes', 0)} | `{sha}` |")
    missing = pack.get("missing_required_files") or []
    lines.extend(["", "## Missing", ""])
    lines.append("无" if not missing else "\n".join(f"- {m}" for m in missing))
    lines.append("")
    return "\n".join(lines)


def write_pack(pack: Dict[str, Any]) -> Dict[str, str]:
    root = Path(str(pack["root"]))
    rel_json = context_pack_relpath(str(pack["episode"]), str(pack["stage_key"]))
    path_json = root / rel_json
    path_md = root / "生产数据" / "views" / "context_packs" / path_json.with_suffix(".md").name
    path_json.parent.mkdir(parents=True, exist_ok=True)
    path_md.parent.mkdir(parents=True, exist_ok=True)
    path_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path_md.write_text(render_markdown(pack), encoding="utf-8")
    return {
        "json": str(path_json),
        "markdown": str(path_md),
        "rel_json": rel_json,
        "rel_markdown": path_md.relative_to(root).as_posix(),
        "markdown_role": "derived_view",
    }


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="build an n2d stage context pack")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("stage_key")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    pack = build_pack(ns.root, ns.episode, ns.stage_key)
    if ns.write:
        pack["outputs"] = write_pack(pack)
    if ns.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
