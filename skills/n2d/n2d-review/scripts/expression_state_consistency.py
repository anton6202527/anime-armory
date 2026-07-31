#!/usr/bin/env python3
"""Check expression/state deltas against identity invariants."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
try:
    from n2d_contract import MICRO_EXPRESSION_FIELD
except Exception:  # pragma: no cover
    MICRO_EXPRESSION_FIELD = "微表情节拍"

KIND = "n2d_expression_state_consistency"


def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _characters(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = _load(root / "出图" / "共享" / "identity_registry.json") or {}
    rows = data.get("characters") or [] if isinstance(data, Mapping) else []
    return {str(r.get("id")): r for r in rows if isinstance(r, Mapping) and r.get("id")}


def _clip_characters(clip: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for key in ("character_ids", "characters"):
        raw = clip.get(key)
        if isinstance(raw, str):
            out.append(raw)
        elif isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray)):
            for item in raw:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, Mapping) and item.get("character_id"):
                    out.append(str(item.get("character_id")))
    return list(dict.fromkeys(out))


def check_storyboard(storyboard: Mapping[str, Any], characters: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    clips = storyboard.get("clips") or []
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        cid = str(clip.get("id") or clip.get("clip_id") or f"Clip_{idx:02d}")
        continuity = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
        expr_span = str(continuity.get("expression_span") or clip.get("expression_span") or "").strip().lower()
        micro = str(continuity.get(MICRO_EXPRESSION_FIELD) or clip.get(MICRO_EXPRESSION_FIELD) or "").strip()
        if expr_span in {"大", "big", "large", "cross_emotion"} and not micro:
            findings.append({
                "severity": "warn",
                "dimension": "状态化表情(EXP2)",
                "loc": cid,
                "message": f"big expression span needs {MICRO_EXPRESSION_FIELD} so identity is locked while emotion changes",
            })
        state_delta = continuity.get("state_delta") or continuity.get("visual_state_delta") or clip.get("state_delta")
        if not isinstance(state_delta, Mapping):
            continue
        for char_id in _clip_characters(clip):
            char = characters.get(char_id) or {}
            invariants = set(str(x) for x in (char.get("identity_invariants") or char.get("invariants") or []))
            allowed = set(str(x) for x in (char.get("allowed_state_deltas") or char.get("allowed_deltas") or []))
            changed = set(str(x) for x in state_delta.keys())
            illegal = sorted((changed & invariants) - allowed)
            if illegal:
                findings.append({
                    "severity": "block",
                    "dimension": "状态化表情(EXP2)",
                    "loc": cid,
                    "message": f"{char_id} state_delta changes identity invariants without allowed_state_deltas: {', '.join(illegal)}",
                })
    return {
        "kind": KIND,
        "version": 1,
        "status": "blocked" if any(f["severity"] == "block" for f in findings) else "pass",
        "findings": findings,
        "counts": {
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
        },
    }


def run(root: str | Path, ep: str, *, write: bool = False) -> Dict[str, Any]:
    root = Path(root)
    storyboard = _load(root / "脚本" / ep / "storyboard.json") or {}
    report = check_storyboard(storyboard if isinstance(storyboard, Mapping) else {}, _characters(root))
    if write:
        out = root / "生产数据" / f"expression_state_consistency_{ep}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["path"] = str(out)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ns = ap.parse_args(argv)
    report = run(ns.root, ns.episode, write=ns.write)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if report.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
