#!/usr/bin/env python3
"""Check native voice identity and audio-space continuity evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

KIND = "n2d_audio_space_consistency"


def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _routes(root: Path, ep: str) -> List[Mapping[str, Any]]:
    data = _load(root / "出视频" / ep / "prompt" / "video_model_routes.json") or {}
    if not isinstance(data, Mapping):
        return []
    return [r for r in data.get("routes") or [] if isinstance(r, Mapping)]


def _native_voice_index(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = _load(root / "生产数据" / f"native_voice_identity_{ep}.json") or {}
    rows = data.get("clips") or data.get("segments") or [] if isinstance(data, Mapping) else []
    out: Dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if isinstance(row, Mapping) and row.get("clip_id"):
            out[str(row.get("clip_id"))] = row
    return out


def check(routes: Sequence[Mapping[str, Any]], ambient_map: Mapping[str, Any], native_voice: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    locations = ambient_map.get("locations") if isinstance(ambient_map.get("locations"), Mapping) else {}
    for route in routes:
        cid = str(route.get("clip_id") or "")
        loc = str(route.get("loc") or route.get("location_id") or "")
        native_policy = str(route.get("native_audio_policy") or "")
        if loc and locations and loc not in locations:
            findings.append({
                "severity": "warn",
                "dimension": "声音空间(ASP)",
                "loc": cid,
                "message": f"location {loc} has no ambient_map entry",
            })
        if native_policy == "native_speech":
            evidence = native_voice.get(cid) or {}
            if not evidence:
                findings.append({
                    "severity": "warn",
                    "dimension": "原生声纹(NV1)",
                    "loc": cid,
                    "message": "native_speech route lacks native_voice_identity evidence; use voice-first fallback or add speaker proof",
                })
                continue
            if not evidence.get("speaker_key") and not evidence.get("voice_key"):
                findings.append({
                    "severity": "warn",
                    "dimension": "原生声纹(NV1)",
                    "loc": cid,
                    "message": "native_voice_identity evidence lacks speaker_key/voice_key",
                })
            if str(evidence.get("status") or "").lower() in {"fail", "blocked", "mismatch"}:
                findings.append({
                    "severity": "block",
                    "dimension": "原生声纹(NV1)",
                    "loc": cid,
                    "message": "native voice identity evidence failed",
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
    ambient = _load(root / "设定库" / "ambient_map.json") or {}
    report = check(_routes(root, ep), ambient if isinstance(ambient, Mapping) else {}, _native_voice_index(root, ep))
    if write:
        out = root / "生产数据" / f"audio_space_consistency_{ep}.json"
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
