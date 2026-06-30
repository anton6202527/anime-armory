#!/usr/bin/env python3
"""Check series motion grammar contracts against video routes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

KIND = "n2d_motion_grammar_consistency"


def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _allowed(grammar: Mapping[str, Any], shot_type: str) -> Mapping[str, Any]:
    by_type = grammar.get("shot_types") if isinstance(grammar.get("shot_types"), Mapping) else {}
    return by_type.get(shot_type) if isinstance(by_type.get(shot_type), Mapping) else {}


def check_routes(routes: Sequence[Mapping[str, Any]], grammar: Mapping[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    required_types = set(grammar.get("required_shot_types") or [])
    for route in routes:
        cid = str(route.get("clip_id") or "")
        shot = str(route.get("shot_type") or "")
        spec = _allowed(grammar, shot)
        if shot in required_types and not spec:
            findings.append({
                "severity": "warn",
                "dimension": "运动语法(MG1)",
                "loc": cid,
                "message": f"{shot} is required by motion grammar but has no shot_types entry",
            })
        if not spec:
            continue
        allowed_backends = [str(x) for x in spec.get("allowed_backends") or []]
        primary = str(route.get("primary_backend") or "")
        if allowed_backends and primary not in allowed_backends:
            findings.append({
                "severity": "warn",
                "dimension": "运动语法(MG1)",
                "loc": cid,
                "message": f"{shot} route backend {primary} not in motion grammar allowed_backends={allowed_backends}",
            })
        required_flags = set(str(x) for x in spec.get("required_risk_flags") or [])
        flags = set(str(x) for x in route.get("risk_flags") or [])
        missing = sorted(required_flags - flags)
        if missing:
            findings.append({
                "severity": "warn",
                "dimension": "运动语法(MG1)",
                "loc": cid,
                "message": f"{shot} missing motion grammar flags: {', '.join(missing)}",
            })
        if spec.get("motion_reference_required"):
            ref = route.get("motion_reference") if isinstance(route.get("motion_reference"), Mapping) else {}
            if not ref.get("applicable"):
                findings.append({
                    "severity": "warn",
                    "dimension": "运动语法(MG1)",
                    "loc": cid,
                    "message": f"{shot} requires a motion_reference according to motion_grammar.json",
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
    grammar = _load(root / "设定库" / "motion_grammar.json") or {}
    routes_payload = _load(root / "出视频" / ep / "prompt" / "video_model_routes.json") or {}
    routes = [r for r in routes_payload.get("routes") or [] if isinstance(r, Mapping)] if isinstance(routes_payload, Mapping) else []
    if not grammar:
        report = {
            "kind": KIND,
            "version": 1,
            "status": "pass",
            "findings": [],
            "counts": {"block": 0, "warn": 0},
            "note": "no 设定库/motion_grammar.json; motion grammar consistency falls back to route risk flags",
        }
    else:
        report = check_routes(routes, grammar)
    if write:
        out = root / "生产数据" / f"motion_grammar_consistency_{ep}.json"
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
