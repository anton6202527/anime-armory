#!/usr/bin/env python3
"""Fail-closed policy for external visual references used by n2d-image.

The source manifest may also contain research-only observations.  Those rows
remain useful to writers, but only an explicitly rights-cleared, watermark-free
row whose current bytes still match its declared SHA may become a backend image
input.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


REFERENCE_MANIFEST_REL = Path("设定库") / "参考资料" / "视觉参考" / "reference_manifest.json"
IDENTITY_GENERATION_POLICIES = frozenset({"identity_reference", "identity_body_reference"})
STYLE_GENERATION_POLICIES = frozenset({"style_source_only"})
GENERATION_POLICIES = IDENTITY_GENERATION_POLICIES | STYLE_GENERATION_POLICIES

# Values are normalized by removing spaces, underscores and hyphens.
AUTHORIZED_RIGHTS_STATUSES = frozenset({
    "authorized",
    "authorised",
    "fullyauthorized",
    "authorizedforgeneration",
    "approved",
    "authorizationapproved",
    "userowned",
    "userdeclaredowned",
    "selfowned",
    "selfauthorized",
    "owned",
    "ownedbyuser",
    "licensed",
    "licenseapproved",
    "licensedforgeneration",
    "rightscleared",
    "cleared",
    "已授权",
    "授权通过",
    "自有",
    "用户自有",
    "权利已清",
})
DISALLOWED_WORKFLOW_STATUSES = frozenset({
    "analysisonly",
    "pending",
    "pendingrightsreview",
    "availablependingrightsreview",
    "userprovidedreferencependingrightsreview",
    "acceptedforinternalgenerationpendingrightsreview",
    "blocked",
    "rejected",
    "unlicensed",
    "unknown",
})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _normalized_token(value: Any) -> str:
    return re.sub(r"[\s_-]+", "", str(value or "").strip().lower())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_project_file(root: Path, raw: Any) -> Tuple[str, Optional[Path], List[str]]:
    value = str(raw or "").strip()
    if not value:
        return "", None, ["path_missing"]
    if "\x00" in value:
        return "", None, ["path_invalid_nul"]
    if os.path.isabs(value) or (len(value) >= 3 and value[1] == ":" and value[2] in {"/", "\\"}):
        return "", None, ["absolute_path_not_allowed"]

    root_real = root.expanduser().resolve()
    resolved = (root_real / value).resolve(strict=False)
    try:
        if os.path.commonpath((str(root_real), str(resolved))) != str(root_real):
            return "", None, ["path_outside_project_root"]
        canonical = resolved.relative_to(root_real).as_posix()
    except (ValueError, OSError):
        return "", None, ["path_outside_project_root"]
    if value.replace("\\", "/") != canonical:
        return canonical, resolved, ["path_not_canonical_project_relative"]
    if not resolved.is_file():
        return canonical, resolved, ["file_missing"]
    return canonical, resolved, []


def evaluate_generation_reference(
    root: Path,
    row: Mapping[str, Any],
    *,
    allowed_policies: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Return current eligibility and evidence for one external reference row."""
    issues: List[str] = []
    policy = str(row.get("use_policy") or "").strip()
    allowed = set(allowed_policies or GENERATION_POLICIES)
    if policy not in allowed:
        issues.append("use_policy_not_generation_eligible")

    rights_status = _normalized_token(row.get("rights_status"))
    if rights_status not in AUTHORIZED_RIGHTS_STATUSES:
        issues.append("rights_status_not_authorized_or_user_owned")

    workflow_status = _normalized_token(row.get("status"))
    if workflow_status in DISALLOWED_WORKFLOW_STATUSES:
        issues.append("workflow_status_pending_or_blocked")
    if row.get("eligible_for_generation") is not True:
        issues.append("eligible_for_generation_not_true")
    if row.get("backend_upload_allowed") is not True:
        issues.append("backend_upload_allowed_not_true")

    # Unknown is not equivalent to clean.  Require a literal false so a missing
    # watermark review cannot silently become permission to upload.
    if row.get("watermark_present") is not False:
        issues.append("watermark_present_or_not_explicitly_false")
    if row.get("has_watermark") is True or row.get("watermarked") is True or row.get("watermark") is True:
        issues.append("watermark_present_or_not_explicitly_false")

    canonical, path, path_issues = _canonical_project_file(root, row.get("path"))
    issues.extend(path_issues)
    actual_sha = sha256_file(path) if path is not None and path.is_file() and not path_issues else ""
    declared_sha = str(row.get("sha256") or "").strip().lower()
    if not SHA256_RE.fullmatch(declared_sha):
        issues.append("declared_sha256_missing_or_invalid")
    elif actual_sha and declared_sha != actual_sha:
        issues.append("declared_sha256_mismatch")

    return {
        "eligible": not issues,
        "issues": sorted(set(issues)),
        "path": canonical,
        "sha256": actual_sha,
        "use_policy": policy,
    }


def reference_manifest_path(root: Path) -> Path:
    return root / REFERENCE_MANIFEST_REL


def load_reference_manifest(root: Path) -> Tuple[Optional[Mapping[str, Any]], List[str]]:
    path = reference_manifest_path(root)
    if not path.exists():
        return None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"reference_manifest_invalid_json:{type(exc).__name__}"]
    if not isinstance(data, Mapping):
        return None, ["reference_manifest_root_must_be_object"]
    references = data.get("references")
    if not isinstance(references, list):
        return data, ["reference_manifest_references_must_be_list"]
    return data, []


def reference_manifest_generation_issues(root: Path) -> List[str]:
    """Validate rows that explicitly request backend generation use.

    Research/analysis-only rows are intentionally retained without blocking the
    project; they simply can never be attached.  Active identity/style rows fail
    the paid shared-asset preflight if any eligibility evidence is incomplete.
    """
    data, issues = load_reference_manifest(root)
    out = list(issues)
    if data is None:
        return out
    for index, row in enumerate(data.get("references") or [], 1):
        if not isinstance(row, Mapping):
            out.append(f"reference[{index}]:row_must_be_object")
            continue
        policy = str(row.get("use_policy") or "").strip()
        if policy not in GENERATION_POLICIES:
            continue
        result = evaluate_generation_reference(root, row, allowed_policies=(policy,))
        if result["eligible"]:
            continue
        ref_id = str(row.get("id") or row.get("reference_id") or index).strip()
        for issue in result["issues"]:
            out.append(f"reference[{ref_id}]:{issue}")
    return sorted(set(out))
