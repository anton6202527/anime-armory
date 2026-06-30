#!/usr/bin/env python3
"""Derive edit/SFX cues for high-dynamic and large-scale n2d clips."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import (  # noqa: E402
    ACTION_EDIT_CUES_KIND,
    edit_cues_for_spectacle,
    infer_spectacle_type,
)


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def storyboard_path(root: Path, ep: str) -> Path:
    return root / "脚本" / ep / "storyboard.json"


def output_json_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"action_edit_cues_{ep}.json"


def output_md_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"action_edit_cues_{ep}.md"


def make_clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("clip_id") or clip.get("id") or clip.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{idx:02d}"


def load_storyboard(root: Path, ep: str) -> Dict[str, Any]:
    p = storyboard_path(root, ep)
    if not p.is_file():
        raise FileNotFoundError(f"storyboard not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("storyboard.json top-level must be an object")
    return data


def clip_contract(clip: Mapping[str, Any], kind: str) -> Dict[str, Any]:
    if kind == "large_establishing":
        for key in ("large_scene_contract", "spectacle_contract", "template_contract"):
            val = clip.get(key)
            if isinstance(val, dict):
                return dict(val)
        return {}
    val = clip.get("template_contract")
    return dict(val) if isinstance(val, dict) else {}


def build_cues(root: Path, ep: str) -> Dict[str, Any]:
    data = load_storyboard(root, ep)
    clips = data.get("clips") or []
    if not isinstance(clips, list):
        raise ValueError("storyboard.json clips must be a list")
    rows: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        kind = infer_spectacle_type(clip)
        if not kind:
            continue
        contract = clip_contract(clip, kind)
        rows.append({
            "clip_id": make_clip_id(clip, idx),
            "source_id": str(clip.get("id") or clip.get("clip_id") or clip.get("label") or ""),
            "spectacle_type": kind,
            "cues": edit_cues_for_spectacle(kind, contract),
            "mix_notes": [
                "keep cues as edit-layer hints; do not hide unreadable motion with excessive shake",
                "if a cue exposes a broken contact or pose, return to n2d-video rather than masking it in compose",
            ],
        })
    return {
        "kind": ACTION_EDIT_CUES_KIND,
        "version": 1,
        "episode": ep,
        "clips": rows,
        "summary": {"clips_with_cues": len(rows)},
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 动作/大场景剪辑 cues",
        "",
        f"- episode: {plan.get('episode')}",
        "",
    ]
    for row in plan.get("clips") or []:
        lines.append(f"## {row.get('clip_id')} — {row.get('spectacle_type')}")
        for cue in row.get("cues") or []:
            lines.append(f"- {cue.get('cue')} @ {cue.get('when')}")
        lines.append("")
    return "\n".join(lines).rstrip()


def write_cues(plan: Mapping[str, Any], root: Path, ep: str) -> Dict[str, Path]:
    jp = output_json_path(root, ep)
    mp = output_md_path(root, ep)
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mp.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    return {"json": jp, "markdown": mp}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build n2d action edit cues")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    plan = build_cues(root, ep)
    if ns.write:
        paths = write_cues(plan, root, ep)
        plan["written"] = {k: str(v) for k, v in paths.items()}
    if ns.markdown:
        print(render_markdown(plan))
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
