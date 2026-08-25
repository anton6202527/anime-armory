#!/usr/bin/env python3
"""Canonical Comic release digest and single final completion verdict.

The release report may expose many diagnostic/readiness views, but this module
is the only Comic component allowed to answer whether one delivery unit is
finally complete.  Provider success, dashboard rows and ``_进度.md`` are only
evidence.  Final completion requires a named receipt bound to the current
canonical release digest (or, for a public/commercial release, the already
named release acceptance that made the current report pass).
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


VERDICT_KIND = "comic_completion_verdict"
ACCEPTANCE_KIND = "comic_final_acceptance"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _records(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    records = []
    for row in rows:
        path = str(row.get("path") or "").replace(os.sep, "/")
        digest = str(row.get("sha256") or "")
        if path and digest:
            records.append({"path": path, "sha256": digest})
    return sorted(records, key=lambda item: item["path"])


def release_digest_payload(report: Mapping[str, Any]) -> dict[str, Any]:
    """Stable material for exactly one active medium/usage delivery."""
    return {
        "schema_version": 1,
        "chapter": str(report.get("chapter") or ""),
        "medium": str(report.get("medium") or ""),
        "usage": str(report.get("usage") or ""),
        "target_platform": str(report.get("target_platform") or ""),
        "artifacts": _records(row for row in report.get("artifacts") or [] if isinstance(row, Mapping)),
        "review_receipt": dict(report.get("review_receipt_binding") or {}),
        "finding_dispositions": dict(report.get("finding_disposition_binding") or {}),
        "platform_preview": dict(report.get("platform_preview_binding") or {}),
        "medium_contract": dict(report.get("medium_specific_binding") or {}),
        "provenance": dict(report.get("provenance_binding") or {}),
        "rights": dict(report.get("rights_binding") or {}),
        "blocking_issues": sorted(
            str(item.get("code") or "")
            for item in report.get("issues") or []
            if isinstance(item, Mapping) and item.get("blocks_active_delivery")
        ),
    }


def canonical_release_digest(report: Mapping[str, Any]) -> str:
    return stable_sha256(release_digest_payload(report))


def acceptance_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / f"final_acceptance_{chapter}.json"


def verdict_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / f"completion_verdict_{chapter}.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def acceptance_status(root: Path, chapter: str, release_digest: str) -> dict[str, Any]:
    path = acceptance_path(root, chapter)
    receipt = load_json(path)
    issues = []
    if not receipt:
        issues.append("final acceptance receipt is missing")
    elif receipt.get("kind") != ACCEPTANCE_KIND:
        issues.append("final acceptance kind is invalid")
    elif receipt.get("decision") != "accepted":
        issues.append("final acceptance decision is not accepted")
    elif not str(receipt.get("accepted_by") or "").strip():
        issues.append("final acceptance lacks accepted_by")
    elif str(receipt.get("release_digest") or "") != release_digest:
        issues.append("final acceptance is stale against current release_digest")
    return {
        "exists": path.is_file(),
        "path": str(path.relative_to(root)),
        "accepted": not issues,
        "issues": issues,
        "receipt": receipt,
    }


def public_release_acceptance_current(root: Path, chapter: str, report: Mapping[str, Any]) -> bool:
    """The release verdict already validates every component of this receipt."""
    if str(report.get("usage") or "") not in {"public", "commercial"}:
        return False
    receipt = load_json(root / "生产数据" / f"release_acceptance_{chapter}.json")
    return bool(
        report.get("verdict") == "pass"
        and receipt.get("status") in {"approved", "accepted", "pass"}
        and str(receipt.get("reviewer") or "").strip()
    )


def build_completion_verdict(root: Path, report: Mapping[str, Any]) -> dict[str, Any]:
    digest = canonical_release_digest(report)
    blockers = [
        {"code": str(item.get("code") or ""), "reason": str(item.get("reason") or "")}
        for item in report.get("issues") or []
        if isinstance(item, Mapping) and item.get("blocks_active_delivery")
    ]
    if report.get("verdict") != "pass" and not blockers:
        blockers.append({"code": "release_verdict_blocked", "reason": "active release verdict is blocked"})
    final = acceptance_status(root, str(report.get("chapter") or ""), digest)
    accepted_via_release = public_release_acceptance_current(root, str(report.get("chapter") or ""), report)
    if blockers:
        status = "blocked"
    elif final["accepted"] or accepted_via_release:
        status = "accepted"
    else:
        status = "machine_ready"
    return {
        "schema_version": 1,
        "kind": VERDICT_KIND,
        "generated_at": now_iso(),
        "project_root": str(root.resolve()),
        "chapter": str(report.get("chapter") or ""),
        "status": status,
        "complete": status == "accepted",
        "release_digest": digest,
        "active_delivery": {
            "medium": report.get("medium"),
            "usage": report.get("usage"),
            "target_platform": report.get("target_platform"),
        },
        "machine_ready": not blockers,
        "blockers": blockers,
        "acceptance": final,
        "accepted_via_current_public_release_receipt": accepted_via_release,
        "definition": "accepted iff the active delivery is machine-ready and a named final/current public release acceptance binds its exact current evidence",
        "non_authoritative_views": ["_进度.md", "dashboard", "provider_succeeded", "delivery_states", "machine_complete"],
    }


def write_completion_verdict(root: Path, report: Mapping[str, Any]) -> Path:
    path = verdict_path(root, str(report.get("chapter") or ""))
    atomic_json(path, build_completion_verdict(root, report))
    return path


def accept_final(root: Path, report: Mapping[str, Any], *, accepted_by: str, note: str) -> dict[str, Any]:
    actor = str(accepted_by or "").strip()
    if not actor or actor.startswith("delegate:"):
        raise ValueError("final acceptance requires a named non-delegate accepted_by")
    verdict = build_completion_verdict(root, report)
    if not verdict["machine_ready"]:
        raise ValueError("active delivery is not machine-ready")
    receipt = {
        "schema_version": 1,
        "kind": ACCEPTANCE_KIND,
        "decision": "accepted",
        "accepted_at": now_iso(),
        "accepted_by": actor,
        "note": str(note or "").strip(),
        "chapter": report.get("chapter"),
        "release_digest": verdict["release_digest"],
        "active_delivery": verdict["active_delivery"],
    }
    atomic_json(acceptance_path(root, str(report.get("chapter") or "")), receipt)
    write_completion_verdict(root, report)
    return receipt
