#!/usr/bin/env python3
"""Append-only Comic asset provenance ledger with an auditable hash chain."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


LEDGER_REL = Path("生产数据") / "asset_provenance.jsonl"
KIND = "comic_asset_provenance_event"


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def load_events(root: Path) -> list[dict[str, Any]]:
    path = root / LEDGER_REL
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    except (OSError, ValueError):
        return []
    return rows


def validate_chain(events: list[Mapping[str, Any]]) -> list[str]:
    errors, previous = [], ""
    for index, row in enumerate(events, 1):
        body = {key: value for key, value in row.items() if key != "event_sha256"}
        if str(row.get("previous_event_sha256") or "") != previous:
            errors.append(f"row {index}: previous_event_sha256 mismatch")
        expected = canonical_sha256(body)
        if str(row.get("event_sha256") or "") != expected:
            errors.append(f"row {index}: event_sha256 mismatch")
        previous = str(row.get("event_sha256") or "")
    return errors


def append_event(
    root: Path,
    asset: Path,
    *,
    action: str,
    model: str = "",
    model_version: str = "",
    channel: str = "",
    references: list[Mapping[str, Any]] | None = None,
    human_contribution: str = "",
    rights_basis: str = "",
) -> dict[str, Any]:
    root, asset = root.resolve(), asset.resolve()
    try:
        rel = str(asset.relative_to(root))
    except ValueError as exc:
        raise ValueError("asset must be inside project root") from exc
    if not asset.is_file():
        raise ValueError("asset does not exist")
    existing = load_events(root)
    chain_errors = validate_chain(existing)
    if chain_errors:
        raise ValueError("provenance ledger chain is invalid: " + "; ".join(chain_errors))
    body = {
        "schema_version": 1,
        "kind": KIND,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "asset_path": rel.replace(os.sep, "/"),
        "asset_sha256": file_sha256(asset),
        "action": str(action or "").strip(),
        "model": str(model or "").strip(),
        "model_version": str(model_version or "").strip(),
        "channel": str(channel or "").strip(),
        "references": list(references or []),
        "human_contribution": str(human_contribution or "").strip(),
        "rights_basis": str(rights_basis or "").strip(),
        "previous_event_sha256": str(existing[-1].get("event_sha256") or "") if existing else "",
        "c2pa_status": "not_signed",
    }
    if not body["action"]:
        raise ValueError("action is required")
    event = {**body, "event_sha256": canonical_sha256(body)}
    ledger = root / LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def binding(root: Path, artifacts: list[Mapping[str, Any]]) -> dict[str, Any]:
    events = load_events(root)
    errors = validate_chain(events)
    latest = {}
    for event in events:
        latest[(str(event.get("asset_path") or ""), str(event.get("asset_sha256") or ""))] = event
    missing = []
    for artifact in artifacts:
        key = (str(artifact.get("path") or ""), str(artifact.get("sha256") or ""))
        if key not in latest:
            missing.append(key[0])
    ledger = root / LEDGER_REL
    return {
        "ledger_path": LEDGER_REL.as_posix(),
        "ledger_sha256": file_sha256(ledger),
        "event_count": len(events),
        "chain_valid": not errors,
        "chain_errors": errors,
        "artifacts_without_current_event": missing,
        "human_authorship_summary_present": any(str(row.get("human_contribution") or "").strip() for row in events),
        "c2pa_status": "signed" if events and all(row.get("c2pa_status") == "signed" for row in events) else "not_signed",
    }


def write_c2pa_sidecar(root: Path, artifact: Path) -> Path:
    """Write a disclosure sidecar; never claim a cryptographic C2PA signature."""
    events = [
        row for row in load_events(root)
        if row.get("asset_path") == str(artifact.resolve().relative_to(root.resolve())).replace(os.sep, "/")
        and row.get("asset_sha256") == file_sha256(artifact)
    ]
    sidecar = artifact.with_suffix(artifact.suffix + ".provenance.json")
    payload = {
        "kind": "comic_c2pa_compatible_disclosure_sidecar",
        "asset": str(artifact.resolve().relative_to(root.resolve())).replace(os.sep, "/"),
        "asset_sha256": file_sha256(artifact),
        "c2pa_status": "not_signed",
        "notice": "This sidecar is a disclosure record, not a signed C2PA Content Credential.",
        "events": events,
    }
    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sidecar
