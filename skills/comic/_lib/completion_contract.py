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
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


VERDICT_KIND = "comic_completion_verdict"
ACCEPTANCE_KIND = "comic_final_acceptance"
AUTOMATED_ACCEPTOR_RE = re.compile(
    r"(?:^|[^a-z0-9])(agent|ai|assistant|automation|bot|chatgpt|claude|codex|delegate|listener|"
    r"machine|model|producer|supervisor|system)(?:[^a-z0-9]|$)|"
    r"^(?:代理|制作代理|自动化|机器人|模型|系统|系统代理|执行器)(?:$|[:：/#@])", re.I
)


def is_named_human(value: Any) -> bool:
    actor = str(value or "").strip()
    return bool(actor) and not AUTOMATED_ACCEPTOR_RE.search(actor)


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
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    try:
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:  # pragma: no cover - directory fsync is platform-specific
        pass
    try:
        parent_fd = os.open(path.parent.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except OSError:  # pragma: no cover
        pass


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
        "settings": dict(report.get("settings_binding") or {}),
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
    elif not is_named_human(receipt.get("accepted_by")):
        issues.append("final acceptance requires a named human accepted_by")
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
        "release_inputs_fingerprint": digest,
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


def _safe_project_path(root: Path, raw: str) -> Path | None:
    if not str(raw or "").strip():
        return None
    candidate = (root / str(raw)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _binding_file_issues(root: Path, value: Any, prefix: str = "binding") -> list[str]:
    issues: list[str] = []
    if isinstance(value, Mapping):
        for path_key, sha_key in (
            ("path", "sha256"), ("report_path", "report_sha256"),
            ("ledger_path", "ledger_sha256"), ("meta_path", "meta_sha256"),
        ):
            path_raw = str(value.get(path_key) or "")
            expected = str(value.get(sha_key) or "")
            if path_raw and expected:
                path = _safe_project_path(root, path_raw)
                if path is None:
                    issues.append(f"{prefix} path escapes project root: {path_raw}")
                elif sha256_file(path) != expected:
                    issues.append(f"{prefix} is missing or stale: {path_raw}")
        for key, item in value.items():
            issues.extend(_binding_file_issues(root, item, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            issues.extend(_binding_file_issues(root, item, f"{prefix}[{index}]"))
    return issues


def verify_report_inputs(root: Path, report: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute the active release fingerprint from current bytes, not claims."""
    digest = canonical_release_digest(report)
    issues: list[str] = []
    if str(report.get("release_digest") or digest) != digest:
        issues.append("release report digest is internally inconsistent")
    for row in report.get("artifacts") or []:
        if not isinstance(row, Mapping):
            continue
        path = _safe_project_path(root, str(row.get("path") or ""))
        expected = str(row.get("sha256") or "")
        if path is None or not expected or sha256_file(path) != expected:
            issues.append(f"release artifact is missing or stale: {row.get('path') or '<unknown>'}")
    for key in (
        "settings_binding", "review_receipt_binding", "finding_disposition_binding",
        "platform_preview_binding", "medium_specific_binding", "provenance_binding", "rights_binding",
    ):
        issues.extend(_binding_file_issues(root, report.get(key) or {}, key))
    return {"current": not issues, "release_digest": digest, "issues": sorted(set(issues))}


def verify_stored_completion(root: Path, chapter: str, stored: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate the sole completion verdict against the active immutable bundle."""
    contract = load_json(root / "生产数据" / f"release_contract_{chapter}.json")
    issues: list[str] = []
    if contract.get("kind") != "comic_active_release_contract":
        issues.append("active release contract is missing or invalid")
    bundle_raw = str(contract.get("bundle_path") or "")
    bundle_path = _safe_project_path(root, bundle_raw) if bundle_raw else None
    report = load_json(bundle_path) if bundle_path is not None else {}
    if not report:
        issues.append("active immutable release bundle is missing")
    else:
        bundle_sha = str(contract.get("bundle_sha256") or "")
        if not bundle_sha or sha256_file(bundle_path) != bundle_sha:
            issues.append("active immutable release bundle SHA is stale")
    completion_raw = str(contract.get("completion_path") or "")
    completion_path = _safe_project_path(root, completion_raw) if completion_raw else None
    if completion_path is not None:
        completion = load_json(completion_path)
        completion_sha = str(contract.get("completion_sha256") or "")
        if not completion or not completion_sha or sha256_file(completion_path) != completion_sha:
            issues.append("active immutable completion candidate is missing or stale")
    else:
        # Legacy pointer compatibility.  New revisions always carry their own
        # immutable completion candidate and select it atomically with the
        # release bundle.
        completion = dict(stored or load_json(verdict_path(root, chapter)))
        if contract.get("schema_version", 0) >= 3:
            issues.append("active release revision lacks completion candidate binding")
    verification = verify_report_inputs(root, report) if report else {"current": False, "release_digest": "", "issues": []}
    issues.extend(verification.get("issues") or [])
    digest = str(verification.get("release_digest") or "")
    if str(contract.get("release_digest") or "") != digest:
        issues.append("active pointer release_digest does not match its bundle")
    expected = build_completion_verdict(root, report) if report else {}
    if completion.get("kind") != VERDICT_KIND:
        issues.append("completion verdict is missing or invalid")
    if str(completion.get("release_digest") or "") != digest:
        issues.append("completion verdict release_digest is stale")
    if str(completion.get("release_inputs_fingerprint") or "") != digest:
        issues.append("completion verdict input fingerprint is stale")
    if completion.get("status") != expected.get("status"):
        issues.append("completion verdict status does not match current active evidence")
    return {
        "current": not issues,
        "status": completion.get("status") if not issues else "stale",
        "release_digest": digest,
        "issues": sorted(set(issues)),
        "completion": completion,
        "expected": expected,
        "active_contract": contract,
    }


def prepare_completion_candidate(root: Path, report: Mapping[str, Any]) -> tuple[dict[str, Any], Path]:
    """Write an immutable completion candidate inside its release revision."""
    verdict = build_completion_verdict(root, report)
    chapter = str(report.get("chapter") or "")
    digest = str(verdict.get("release_digest") or "")
    candidate_id = stable_sha256(verdict)
    path = root / "生产数据" / "releases" / chapter / digest / "completions" / f"{candidate_id}.json"
    if path.is_file():
        if load_json(path) != verdict:
            raise ValueError("immutable completion candidate conflicts with its digest path")
    else:
        atomic_json(path, verdict)
    return verdict, path


def write_completion_verdict(root: Path, report: Mapping[str, Any]) -> Path:
    path = verdict_path(root, str(report.get("chapter") or ""))
    verdict, candidate_path = prepare_completion_candidate(root, report)
    atomic_json(path, verdict)
    contract_path = root / "生产数据" / f"release_contract_{report.get('chapter')}.json"
    contract = load_json(contract_path)
    if (
        contract.get("kind") == "comic_active_release_contract"
        and str(contract.get("release_digest") or "") == str(verdict.get("release_digest") or "")
        and str(contract.get("bundle_path") or "")
    ):
        contract.update({
            "schema_version": max(3, int(contract.get("schema_version") or 0)),
            "completion_path": str(candidate_path.relative_to(root)),
            "completion_sha256": sha256_file(candidate_path),
            "completion_activated_at": now_iso(),
        })
        atomic_json(contract_path, contract)
    return path


def accept_final(root: Path, report: Mapping[str, Any], *, accepted_by: str, note: str) -> dict[str, Any]:
    actor = str(accepted_by or "").strip()
    if not is_named_human(actor):
        raise ValueError("final acceptance requires a named human accepted_by, not an automated identity")
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
