#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical release digest and final completion verdict for novel projects.

The novel line has many useful execution/readiness views.  This module is the
single place allowed to answer the business question "is this release finally
complete?".  Provider success, pipeline-run status, dashboard status and
``release_ready`` remain evidence; only a hash-bound final acceptance receipt
can promote ``machine_ready`` to ``accepted``.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


VERDICT_KIND = "novel_completion_verdict"
ACCEPTANCE_KIND = "novel_final_acceptance_receipt"
VERDICT_REL = Path("导出") / "completion_verdict.json"
ACCEPTANCE_REL = Path("导出") / "final_acceptance.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def atomic_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, target)


def _canonical_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    out = []
    for item in records:
        path = str(item.get("path") or "").replace(os.sep, "/")
        digest = str(item.get("sha256") or "")
        if path and digest:
            out.append({"path": path, "sha256": digest})
    return sorted(out, key=lambda row: row["path"])


def release_digest_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the stable payload whose SHA-256 identifies one release.

    Generated timestamps, absolute roots and readiness messages are excluded.
    Any manuscript, export, contract or release-evidence byte change produces a
    new digest and therefore invalidates an old final-acceptance receipt.
    """
    evidence = manifest.get("evidence") if isinstance(manifest.get("evidence"), Mapping) else {}
    evidence_records = []
    for key, item in sorted(evidence.items()):
        if isinstance(item, Mapping) and item.get("exists") and item.get("sha256"):
            evidence_records.append({"key": str(key), "path": str(item.get("path") or ""), "sha256": str(item["sha256"])})
    return {
        "schema_version": 1,
        "release_profile": str(manifest.get("release_profile") or ""),
        "release_name": str(manifest.get("release_name") or ""),
        "meta": _canonical_records([manifest.get("meta") or {}]),
        "settings": _canonical_records([manifest.get("settings") or {}]),
        "chapters": _canonical_records(manifest.get("chapters") or []),
        "exports": _canonical_records(manifest.get("exports") or []),
        "evidence": evidence_records,
    }


def canonical_release_digest(manifest: Mapping[str, Any]) -> str:
    raw = json.dumps(release_digest_payload(manifest), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def acceptance_status(root: str | Path, release_digest: str) -> dict[str, Any]:
    path = Path(root) / ACCEPTANCE_REL
    receipt = _load_json(path)
    issues = []
    if not receipt:
        issues.append("final acceptance receipt is missing")
    elif receipt.get("kind") != ACCEPTANCE_KIND:
        issues.append("final acceptance receipt kind is invalid")
    elif str(receipt.get("decision") or "") != "accepted":
        issues.append("final acceptance decision is not accepted")
    elif not str(receipt.get("accepted_by") or "").strip():
        issues.append("final acceptance lacks accepted_by")
    elif str(receipt.get("release_digest") or "") != release_digest:
        issues.append("final acceptance is stale against current release_digest")
    return {
        "exists": path.is_file(),
        "path": str(ACCEPTANCE_REL).replace(os.sep, "/"),
        "accepted": not issues,
        "issues": issues,
        "receipt": receipt,
    }


def manifest_integrity_issues(root: str | Path, manifest: Mapping[str, Any]) -> list[str]:
    """Verify the manifest still describes current bytes, not only old records."""
    root_path = Path(root).resolve()
    records: list[Mapping[str, Any]] = []
    for key in ("meta", "settings"):
        row = manifest.get(key)
        if isinstance(row, Mapping) and row.get("exists") is not False and row.get("sha256"):
            records.append(row)
    records.extend(row for row in manifest.get("chapters") or [] if isinstance(row, Mapping))
    records.extend(row for row in manifest.get("exports") or [] if isinstance(row, Mapping))
    evidence = manifest.get("evidence") if isinstance(manifest.get("evidence"), Mapping) else {}
    records.extend(row for row in evidence.values() if isinstance(row, Mapping) and row.get("exists"))
    issues = []
    for row in records:
        relpath = str(row.get("path") or "")
        if not relpath:
            continue
        path = (root_path / relpath).resolve()
        try:
            path.relative_to(root_path)
        except ValueError:
            issues.append(f"manifest path escapes project root: {relpath}")
            continue
        if not path.is_file():
            issues.append(f"manifest-bound file is missing: {relpath}")
        elif sha256_file(path) != str(row.get("sha256") or ""):
            issues.append(f"manifest-bound file hash changed: {relpath}")
    return issues


def build_completion_verdict(root: str | Path, manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root_path = Path(root)
    manifest_path = root_path / "导出" / "release_manifest.json"
    release = dict(manifest or _load_json(manifest_path))
    blockers = []
    stored_digest = str(release.get("release_digest") or "")
    current_digest = canonical_release_digest(release) if release else ""
    if not release:
        blockers.append("release manifest is missing")
    elif release.get("release_ready") is not True:
        blockers.append("release manifest is not machine-ready")
    if release:
        blockers.extend(manifest_integrity_issues(root_path, release))
    if release and (not stored_digest or stored_digest != current_digest):
        blockers.append("release manifest digest is missing or stale")
    acceptance = acceptance_status(root_path, current_digest) if current_digest else {
        "exists": False, "path": str(ACCEPTANCE_REL), "accepted": False,
        "issues": ["release digest unavailable"], "receipt": {},
    }
    if blockers:
        status = "blocked"
    elif acceptance["accepted"]:
        status = "accepted"
    else:
        status = "machine_ready"
    return {
        "schema_version": 1,
        "kind": VERDICT_KIND,
        "generated_at": now_iso(),
        "project_root": str(root_path.resolve()),
        "status": status,
        "complete": status == "accepted",
        "business_state_source": "_进度.md",
        "release_manifest": "导出/release_manifest.json",
        "release_digest": current_digest,
        "machine_ready": not blockers,
        "blockers": blockers,
        "acceptance": acceptance,
        "definition": "accepted iff the current release is machine-ready and a named final acceptance receipt binds the current release_digest",
    }


def write_completion_verdict(root: str | Path, manifest: Mapping[str, Any] | None = None) -> str:
    path = Path(root) / VERDICT_REL
    atomic_json(path, build_completion_verdict(root, manifest))
    return str(path)


def accept_release(root: str | Path, *, accepted_by: str, note: str = "") -> dict[str, Any]:
    root_path = Path(root)
    verdict = build_completion_verdict(root_path)
    if not verdict.get("machine_ready"):
        raise ValueError("release is not machine-ready; final acceptance cannot be recorded")
    actor = str(accepted_by or "").strip()
    if not actor:
        raise ValueError("accepted_by is required")
    receipt = {
        "schema_version": 1,
        "kind": ACCEPTANCE_KIND,
        "decision": "accepted",
        "accepted_at": now_iso(),
        "accepted_by": actor,
        "note": str(note or "").strip(),
        "release_digest": verdict["release_digest"],
        "release_manifest": "导出/release_manifest.json",
    }
    atomic_json(root_path / ACCEPTANCE_REL, receipt)
    write_completion_verdict(root_path)
    return receipt
