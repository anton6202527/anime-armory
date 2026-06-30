#!/usr/bin/env python3
"""Validate signed-off intentional discontinuity exceptions for n2d review."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
try:
    from n2d_contract import INTENTIONAL_DISCONTINUITY_MANIFEST_KIND
except Exception:  # pragma: no cover - standalone fallback
    INTENTIONAL_DISCONTINUITY_MANIFEST_KIND = "n2d_intentional_discontinuity_manifest"


def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _entries(manifest: Mapping[str, Any]) -> List[Dict[str, Any]]:
    raw = manifest.get("accepted") or manifest.get("exceptions") or manifest.get("signed_off") or []
    return [dict(x) for x in raw if isinstance(x, Mapping)]


def _date(value: Any) -> Optional[dt.date]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except Exception:
        return None


def validate_manifest(manifest: Mapping[str, Any], *, today: Optional[dt.date] = None) -> Dict[str, Any]:
    today = today or dt.date.today()
    findings: List[Dict[str, Any]] = []
    kind = str(manifest.get("kind") or "")
    if kind and kind != INTENTIONAL_DISCONTINUITY_MANIFEST_KIND:
        findings.append({
            "severity": "block",
            "code": "wrong_kind",
            "message": f"manifest kind must be {INTENTIONAL_DISCONTINUITY_MANIFEST_KIND}",
        })
    entries = _entries(manifest)
    for idx, entry in enumerate(entries, 1):
        loc = f"accepted[{idx}]"
        clip = str(entry.get("clip_id") or entry.get("clip") or "").strip()
        dimension = str(entry.get("dimension") or entry.get("dim") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        signoff = str(entry.get("signoff") or entry.get("approved_by") or "").strip()
        if not clip:
            findings.append({"severity": "block", "code": "missing_clip_id", "loc": loc, "message": "signed-off discontinuity needs clip_id"})
        if not dimension:
            findings.append({"severity": "block", "code": "missing_dimension", "loc": loc, "message": "signed-off discontinuity needs dimension"})
        if len(reason) < 8:
            findings.append({"severity": "block", "code": "missing_reason", "loc": loc, "message": "signed-off discontinuity needs a concrete story/edit reason"})
        if not signoff:
            findings.append({"severity": "warn", "code": "missing_signoff", "loc": loc, "message": "no reviewer/signoff recorded"})
        expires = _date(entry.get("expires_at") or entry.get("expires"))
        if expires and expires < today:
            findings.append({"severity": "block", "code": "expired", "loc": loc, "message": f"exception expired at {expires.isoformat()}"})
    counts = {
        "block": sum(1 for f in findings if f.get("severity") == "block"),
        "warn": sum(1 for f in findings if f.get("severity") == "warn"),
        "accepted": len(entries),
    }
    return {
        "kind": "n2d_intentional_discontinuity_audit",
        "version": 1,
        "status": "blocked" if counts["block"] else "pass",
        "counts": counts,
        "findings": findings,
        "accepted": entries,
    }


def _match_text(finding: Mapping[str, Any]) -> str:
    return " ".join(
        str(finding.get(key) or "")
        for key in ("clip_id", "clip", "loc", "dimension", "dim", "dim_key", "message", "msg", "text")
    )


def finding_is_signed_off(finding: Mapping[str, Any], manifest: Mapping[str, Any]) -> bool:
    hay = _match_text(finding)
    dim = str(finding.get("dimension") or finding.get("dim") or finding.get("dim_key") or "")
    for entry in _entries(manifest):
        clip = str(entry.get("clip_id") or entry.get("clip") or "").strip()
        edim = str(entry.get("dimension") or entry.get("dim") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        if not clip or not edim or len(reason) < 8:
            continue
        if clip in hay and (edim in hay or edim == dim or dim in edim):
            return True
    return False


def annotate_findings(findings: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for finding in findings:
        row = dict(finding)
        if finding_is_signed_off(row, manifest):
            row["intentional_discontinuity_signed_off"] = True
            row.setdefault("severity_before_signoff", row.get("severity") or row.get("sev"))
            row["severity"] = "info"
            row["sev"] = "info"
        out.append(row)
    return out


def audit_path(root: str | Path, ep: str) -> Path:
    return Path(root) / "生产数据" / f"intentional_discontinuity_audit_{ep}.json"


def manifest_path(root: str | Path, ep: str) -> Path:
    return Path(root) / "生产数据" / f"intentional_discontinuity_{ep}.json"


def run(root: str | Path, ep: str, findings: Optional[Sequence[Mapping[str, Any]]] = None, *, write: bool = False) -> Dict[str, Any]:
    path = manifest_path(root, ep)
    manifest = _load(path) if path.exists() else None
    if not isinstance(manifest, Mapping):
        report = {
            "kind": "n2d_intentional_discontinuity_audit",
            "version": 1,
            "status": "pass",
            "manifest_path": str(path),
            "counts": {"block": 0, "warn": 0, "accepted": 0},
            "findings": [],
            "accepted": [],
            "note": "no intentional discontinuity manifest; all consistency findings remain active",
        }
    else:
        report = validate_manifest(manifest)
        report["manifest_path"] = str(path)
        if findings is not None:
            report["annotated_findings"] = annotate_findings(findings, manifest)
    if write:
        out = audit_path(root, ep)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["path"] = str(out)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--findings-json", help="Optional findings payload to annotate")
    ap.add_argument("--write", action="store_true")
    ns = ap.parse_args(argv)
    findings = None
    if ns.findings_json:
        payload = _load(Path(ns.findings_json))
        if isinstance(payload, Mapping):
            findings = [x for x in payload.get("findings") or [] if isinstance(x, Mapping)]
        elif isinstance(payload, list):
            findings = [x for x in payload if isinstance(x, Mapping)]
    report = run(ns.root, ns.episode, findings, write=ns.write)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if report.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
