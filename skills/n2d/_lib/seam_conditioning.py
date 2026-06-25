#!/usr/bin/env python3
"""Seam conditioning hints: feed temporal_consistency seam analysis back into
next-episode video prompt generation.

Reads temporal_consistency seam analysis results from the consistency audit,
generates conditioning hints for the NEXT episode's video prompts, and writes
them to `生产数据/seam_conditioning_<ep>.json`.

Design: pure logic, no model/I/O dependencies beyond stdlib. The hints are
advisory text that n2d-video SKILL.md references for next-episode prompt
generation — suggesting first/last frame chain conditioning for seams that
showed structural/colour/face drift in the consistency audit.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence

KIND = "n2d_seam_conditioning_hints"
VERSION = 1


def build_hints(seam_findings: Sequence[Dict[str, Any]], ep: str) -> Dict[str, Any]:
    """seam_findings: [{tail, next_first, verdict, struct_verdict, color_verdict,
    face_verdict, action_verdict, transition, ...}] from temporal_consistency
    seam_analyze.

    Returns {kind, version, episode, hints: [{shot_N, shot_Np1, severity, fields, hint_text}]}.
    Pure function, testable."""
    hints: List[Dict[str, Any]] = []
    for f in seam_findings:
        if not isinstance(f, dict):
            continue
        verdict = str(f.get("verdict") or "").lower()
        if verdict not in ("warn", "block"):
            continue
        # Collect which specific fields triggered the warning
        fields = []
        for field_key in ("struct_verdict", "color_verdict", "face_verdict", "action_verdict"):
            fv = str(f.get(field_key) or "").lower()
            if fv in ("warn", "block"):
                fields.append(field_key.replace("_verdict", ""))
        if not fields:
            fields = ["structure"]
        tail = str(f.get("tail") or "?")
        nxt = str(f.get("next_first") or "?")
        hint = (
            f"Seam from {tail} to {nxt} showed {', '.join(fields)} drift "
            f"in episode {ep} consistency audit. "
            f"Recommend: use {tail} as first-frame conditioning reference "
            f"for {nxt} in the next episode's video prompt generation, "
            f"or add an explicit seam-bridge shot between these two."
        )
        hints.append({
            "tail": tail,
            "next_first": nxt,
            "severity": verdict,
            "fields": fields,
            "hint": hint,
        })
    return {"kind": KIND, "version": VERSION, "episode": ep, "hints": hints}


def write_hints(root: str, ep: str, hints: Dict[str, Any]) -> Optional[str]:
    """Write hints to 生产数据/seam_conditioning_<ep>.json. Returns path written or None."""
    prod_dir = os.path.join(root, "生产数据")
    os.makedirs(prod_dir, exist_ok=True)
    path = os.path.join(prod_dir, f"seam_conditioning_{ep}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(hints, fh, ensure_ascii=False, indent=2)
    return path
