#!/usr/bin/env python3
"""Classify legacy n2d seams without pretending the inference is approval.

The command writes deterministic candidates and marks them pending review.  P-2
sign-off is still required before P-3/video gates accept the result.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

N2D_LIB = Path(__file__).resolve().parents[2] / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
from seam_contract import normalize_seam_mode, requires_boundary_frame, requirements_for, seam_evidence  # noqa: E402


def clip_id(row: Mapping[str, Any], idx: int) -> str:
    raw = str(row.get("clip_id") or row.get("id") or "")
    match = re.search(r"(?:clip|镜头)[_\s-]?(\d+)", raw, re.I)
    return f"Clip_{int(match.group(1)):02d}" if match else (raw or f"Clip_{idx:02d}")


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def candidate_evidence(mode: str, left: Mapping[str, Any], right: Mapping[str, Any]) -> Dict[str, Any]:
    evidence = dict(seam_evidence(left))
    values = {
        "boundary_frame": left.get("endframe_png") or left.get("last_frame") or "",
        "end_state": left.get("end_state") or "",
        "start_state": right.get("start_state") or "",
        "action_phase_out": left.get("end_state") or "",
        "action_phase_in": right.get("start_state") or "",
        "screen_direction": left.get("screen_direction") or left.get("eyeline") or "",
        "eyeline_source": left.get("eyeline") or "",
        "eyeline_target": right.get("eyeline") or "",
        "axis": left.get("axis") or right.get("axis") or "",
        "audio_source": left.get("sound_bridge") or left.get("audio_bridge") or "",
    }
    for field in requirements_for(mode):
        if field in values and values[field]:
            evidence.setdefault(field, values[field])
        else:
            evidence.setdefault(field, f"待补：{field}")
    return evidence


def migrate(root: Path, episode: str, *, write: bool = False) -> Dict[str, Any]:
    ep = episode if episode.startswith("第") and episode.endswith("集") else f"第{episode}集"
    path = root / "脚本" / ep / "storyboard.json"
    data = load_json(path)
    clips = [row for row in data.get("clips") or [] if isinstance(row, dict)]
    rows = []
    for idx, (left, right) in enumerate(zip(clips, clips[1:]), 1):
        continuity = left.get("continuity") if isinstance(left.get("continuity"), dict) else {}
        continuity = dict(continuity)
        mode_info = normalize_seam_mode(
            continuity.get("seam_mode"), continuity.get("transition"),
            need_endframe=bool(continuity.get("need_endframe")),
        )
        mode = str(mode_info.get("mode") or "")
        if mode:
            right_cont = right.get("continuity") if isinstance(right.get("continuity"), dict) else {}
            continuity["seam_mode"] = mode
            continuity["seam_mode_source"] = "legacy_inferred_pending_p2_review" if mode_info.get("source") != "explicit" else "explicit"
            continuity["seam_evidence"] = candidate_evidence(mode, continuity, right_cont)
            continuity["need_endframe"] = requires_boundary_frame(mode)
            left["continuity"] = continuity
        rows.append({
            "seam": f"{clip_id(left, idx)}->{clip_id(right, idx + 1)}",
            "mode": mode or "unclassified",
            "source": mode_info.get("source"),
            "needs_review": True,
            "missing_transition": not bool(str(continuity.get("transition") or "").strip()),
        })
    if write and data:
        write_json(path, data)
        # Force the P-2 pack back to review; an older approval must not survive
        # a new editorial seam classification.
        signoff = root / "脚本" / ep / "director_blocking_signoff.json"
        if signoff.is_file():
            payload = load_json(signoff)
            payload["status"] = "pending"
            payload["approvals"] = []
            write_json(signoff, payload)
    return {
        "kind": "n2d_seam_migration",
        "episode": ep,
        "status": "needs_review" if rows else "no_seams",
        "written": write,
        "storyboard": str(path),
        "seams": rows,
        "next": "在 P-2 transition_map 逐缝确认 seam_mode/seam_evidence，再重签 p2；迁移推断本身不是导演审批。",
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="migrate legacy n2d seam contracts")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    payload = migrate(Path(ns.root).resolve(), ns.episode, write=ns.write)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else f"{payload['episode']} seams: {payload['status']} ({len(payload['seams'])})")
    return 0 if payload["status"] in {"needs_review", "no_seams"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
