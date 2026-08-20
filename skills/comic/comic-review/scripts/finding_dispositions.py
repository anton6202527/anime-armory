#!/usr/bin/env python3
"""SHA-bound disposition ledger for comic review warnings.

Gate reports remain the source of findings.  This append-only ledger records
who resolved a subjective warning and why; it cannot downgrade deterministic
``block`` findings and becomes stale when the finding or referenced pixels
change.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows compatibility
    fcntl = None


KIND = "comic_finding_disposition"
SCHEMA_VERSION = 1
RESOLVED_STATUSES = {"false_positive", "risk_accepted"}
EVENT_STATUSES = RESOLVED_STATUSES | {"reopened"}


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def stable_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ledger_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / "finding_dispositions" / f"{chapter}.jsonl"


def current_finding_source(root: Path, chapter: str) -> tuple[Path, Mapping[str, Any]]:
    """Prefer the receipt-bound review report; keep the sidecar for migration.

    Public release validates and SHA-binds ``comic_gate_review_*`` through its
    gate receipt.  Reading only the convenience ``gate_findings_*`` sidecar
    would let a missing/deleted sidecar turn a warning-bearing report into an
    apparent zero-warning summary.
    """
    report_path = root / "生产数据" / f"comic_gate_review_{chapter}.json"
    report = load_json(report_path, {})
    if isinstance(report, Mapping) and isinstance(report.get("findings"), list):
        return report_path, report
    sidecar_path = root / "生产数据" / f"gate_findings_review_{chapter}.json"
    sidecar = load_json(sidecar_path, {})
    return sidecar_path, sidecar if isinstance(sidecar, Mapping) else {}


def current_findings(root: Path, chapter: str) -> list[dict[str, Any]]:
    _path, payload = current_finding_source(root, chapter)
    if not isinstance(payload, Mapping):
        return []
    findings: list[dict[str, Any]] = []
    for raw in payload.get("findings") or []:
        if not isinstance(raw, Mapping):
            continue
        severity = str(raw.get("severity") or "")
        machine_severity = str(raw.get("machine_severity") or "")
        if severity != "warn" and machine_severity != "warn":
            continue
        finding = dict(raw)
        finding["stage"] = str(payload.get("stage") or "review")
        finding["chapter"] = chapter
        finding["finding_id"] = finding_id(finding)
        finding["artifact_sha256"] = artifact_sha(root, chapter, finding)
        findings.append(finding)
    # A gate may legitimately emit several warnings with the same broad code
    # and artifact (for example two distinct style checks on one panel, or
    # several missing reference views).  The base identity intentionally omits
    # mutable prose so an edited reason normally makes an existing disposition
    # stale.  Only when identities collide in the *same current report* do we
    # append a deterministic semantic discriminator, keeping every warning
    # independently addressable instead of letting a dict overwrite siblings.
    groups: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        groups.setdefault(str(finding["finding_id"]), []).append(finding)
    for base_id, group in groups.items():
        if len(group) <= 1:
            continue
        discriminator_counts: dict[str, int] = {}
        for finding in group:
            semantic = stable_sha({
                "reason": str(finding.get("reason") or ""),
                "suggested_fix": str(finding.get("suggested_fix") or ""),
                "return_to_stage": str(finding.get("return_to_stage") or ""),
                "confidence": str(finding.get("confidence") or ""),
            })[:10]
            occurrence = discriminator_counts.get(semantic, 0) + 1
            discriminator_counts[semantic] = occurrence
            suffix = semantic if occurrence == 1 else f"{semantic}-{occurrence}"
            finding["finding_base_id"] = base_id
            finding["finding_id"] = f"{base_id}-{suffix}"
    for finding in findings:
        finding["finding_fingerprint"] = finding_fingerprint(finding)
    return findings


def finding_id(finding: Mapping[str, Any]) -> str:
    identity = {
        "stage": str(finding.get("stage") or "review"),
        "code": str(finding.get("code") or ""),
        "artifact": str(finding.get("artifact") or ""),
        "panel_id": str(finding.get("panel_id") or ""),
        "character_id": str(finding.get("character_id") or ""),
        "evidence_family": str(finding.get("evidence_family") or finding.get("category") or ""),
    }
    return "CF-" + stable_sha(identity)[:16]


def artifact_sha(root: Path, chapter: str, finding: Mapping[str, Any]) -> str:
    raw = str(finding.get("artifact") or "").strip()
    candidate = Path(raw).expanduser() if raw else Path()
    if raw:
        candidate = candidate if candidate.is_absolute() else root / candidate
        if candidate.is_file():
            return file_sha(candidate)
    panel_id = str(finding.get("panel_id") or "").strip()
    if panel_id:
        for suffix in (".png", ".jpg", ".jpeg", ".webp"):
            candidate = root / "出图" / chapter / "panels" / f"{panel_id}{suffix}"
            if candidate.is_file():
                return file_sha(candidate)
    return ""


def finding_fingerprint(finding: Mapping[str, Any]) -> str:
    return stable_sha({
        "finding_id": str(finding.get("finding_id") or finding_id(finding)),
        "severity": str(finding.get("severity") or ""),
        "machine_severity": str(finding.get("machine_severity") or ""),
        "reason": str(finding.get("reason") or ""),
        "suggested_fix": str(finding.get("suggested_fix") or ""),
        "artifact_sha256": str(finding.get("artifact_sha256") or ""),
    })


def _parse_ledger_lines(lines: list[str], chapter: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    expected_sequence = 1
    previous_sha = ""
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append({"line": line_number, "code": "invalid_json"})
            continue
        if not isinstance(event, dict):
            errors.append({"line": line_number, "code": "event_not_object"})
            continue
        required_text = ("finding_id", "finding_fingerprint", "reviewer", "reason", "decided_at")
        structural_ok = (
            event.get("kind") == KIND
            and event.get("schema_version") == SCHEMA_VERSION
            and event.get("chapter") == chapter
            and event.get("status") in EVENT_STATUSES
            and all(str(event.get(key) or "").strip() for key in required_text)
            and event.get("sequence") == expected_sequence
            and str(event.get("previous_event_sha256") or "") == previous_sha
        )
        recorded_sha = str(event.get("event_sha256") or "")
        payload = {key: value for key, value in event.items() if key != "event_sha256"}
        sha_ok = bool(recorded_sha) and recorded_sha == stable_sha(payload)
        if not structural_ok or not sha_ok:
            codes: list[str] = []
            if event.get("kind") != KIND:
                codes.append("kind_mismatch")
            if event.get("schema_version") != SCHEMA_VERSION:
                codes.append("schema_mismatch")
            if event.get("chapter") != chapter:
                codes.append("chapter_mismatch")
            if event.get("status") not in EVENT_STATUSES:
                codes.append("status_invalid")
            if not all(str(event.get(key) or "").strip() for key in required_text):
                codes.append("required_field_missing")
            if event.get("sequence") != expected_sequence:
                codes.append("sequence_mismatch")
            if str(event.get("previous_event_sha256") or "") != previous_sha:
                codes.append("hash_chain_mismatch")
            if not sha_ok:
                codes.append("event_sha_invalid")
            errors.append({"line": line_number, "code": "+".join(codes) or "event_invalid"})
            continue
        events.append(event)
        previous_sha = recorded_sha
        expected_sequence += 1
    return events, errors


def read_ledger(root: Path, chapter: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = ledger_path(root, chapter)
    if not path.is_file():
        return [], []
    with path.open("r", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
        lines = handle.readlines()
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return _parse_ledger_lines(lines, chapter)


def read_events(root: Path, chapter: str) -> list[dict[str, Any]]:
    events, _errors = read_ledger(root, chapter)
    return events


def summarize(root: Path, chapter: str) -> dict[str, Any]:
    source_path, _payload = current_finding_source(root, chapter)
    findings = current_findings(root, chapter)
    events, integrity_errors = read_ledger(root, chapter)
    latest = (
        {str(event.get("finding_id")): event for event in events if event.get("finding_id")}
        if not integrity_errors
        else {}
    )
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    reopened: list[dict[str, Any]] = []
    for finding in findings:
        event = latest.get(str(finding["finding_id"]))
        if not event:
            unresolved.append(finding)
            continue
        status = str(event.get("status") or "")
        current = (
            status in RESOLVED_STATUSES
            and str(event.get("finding_fingerprint") or "") == finding["finding_fingerprint"]
            and str(event.get("artifact_sha256") or "") == finding["artifact_sha256"]
            and bool(str(event.get("reviewer") or "").strip())
            and bool(str(event.get("reason") or "").strip())
        )
        record = {**finding, "disposition": event}
        if current:
            resolved.append(record)
        else:
            unresolved.append(finding)
            if status == "reopened":
                reopened.append(record)
            else:
                stale.append(record)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "comic_finding_disposition_summary",
        "chapter": chapter,
        "source": str(source_path.relative_to(root)),
        "ledger": str(ledger_path(root, chapter).relative_to(root)),
        "total": len(findings),
        "currently_resolved": len(resolved),
        "unresolved_count": len(unresolved),
        "stale_count": len(stale),
        "reopened_count": len(reopened),
        "ledger_integrity_error_count": len(integrity_errors),
        "ledger_integrity_errors": integrity_errors,
        "resolved": resolved,
        "unresolved": unresolved,
        "stale": stale,
        "reopened": reopened,
    }


def append_disposition(
    root: Path,
    chapter: str,
    finding_id_value: str,
    *,
    status: str,
    reviewer: str,
    reason: str,
    evidence: str = "",
) -> dict[str, Any]:
    if status not in EVENT_STATUSES:
        raise ValueError(f"status must be one of {sorted(EVENT_STATUSES)}")
    if not reviewer.strip() or not reason.strip():
        raise ValueError("reviewer and reason are required")
    current = {finding["finding_id"]: finding for finding in current_findings(root, chapter)}
    finding = current.get(finding_id_value)
    if not finding:
        raise ValueError("finding-id is not a current review warning")
    event = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "chapter": chapter,
        "finding_id": finding_id_value,
        "finding_fingerprint": finding["finding_fingerprint"],
        "artifact": str(finding.get("artifact") or ""),
        "artifact_sha256": finding["artifact_sha256"],
        "status": status,
        "reviewer": reviewer.strip(),
        "reason": reason.strip(),
        "evidence": evidence.strip(),
        "decided_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    path = ledger_path(root, chapter)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        existing, integrity_errors = _parse_ledger_lines(handle.readlines(), chapter)
        if integrity_errors:
            raise ValueError("finding disposition ledger integrity check failed; restore the append-only ledger before writing")
        event["sequence"] = len(existing) + 1
        event["previous_event_sha256"] = str(existing[-1].get("event_sha256") or "") if existing else ""
        event["event_sha256"] = stable_sha(event)
        handle.seek(0, os.SEEK_END)
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return event


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画 review warning 处置账")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    sub = parser.add_subparsers(dest="command", required=True)
    show = sub.add_parser("list")
    show.add_argument("--json", action="store_true")
    dispose = sub.add_parser("dispose")
    dispose.add_argument("--finding-id", required=True)
    dispose.add_argument("--status", choices=sorted(EVENT_STATUSES), required=True)
    dispose.add_argument("--reviewer", required=True)
    dispose.add_argument("--reason", required=True)
    dispose.add_argument("--evidence", default="")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    if args.command == "dispose":
        try:
            event = append_disposition(
                root, args.chapter, args.finding_id, status=args.status,
                reviewer=args.reviewer, reason=args.reason, evidence=args.evidence,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(event, ensure_ascii=False, indent=2))
        return 0
    summary = summarize(root, args.chapter)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"findings={summary['total']} resolved={summary['currently_resolved']} "
            f"unresolved={summary['unresolved_count']} stale={summary['stale_count']} "
            f"ledger_integrity_errors={summary['ledger_integrity_error_count']}"
        )
        for finding in summary["unresolved"]:
            print(f"- {finding['finding_id']} {finding.get('code')} {finding.get('artifact')}")
    return 1 if summary["unresolved_count"] or summary["ledger_integrity_error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
