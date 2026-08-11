#!/usr/bin/env python3
"""Authorize and apply project-scoped low-risk delegated n2d sign-offs.

This CLI never executes paid media generation, public release, voice cloning,
or destructive source/boundary changes.  It only records hash-bound internal
handoff approvals after the evidence files themselves are review-ready.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple


N2D_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

from autonomy_policy import (  # noqa: E402
    DELEGATED_REVIEWER_ID,
    SETTING_KEY,
    SETTING_VALUE,
    authorization_path,
    load_authorization,
    new_authorization,
    validate_authorization,
    write_authorization,
)
from signoff_contract import (  # noqa: E402
    artifact_fingerprint,
    load_manifest,
    new_manifest,
    profile_spec,
    record_approval,
    validate_manifest,
    write_manifest,
)


READY_STATUSES = {"confirmed", "ready", "pass", "approved", "locked", "accepted"}
FRONTMATTER_STATUS_RE = re.compile(r"^status\s*:\s*([^#\n]+)", re.IGNORECASE | re.MULTILINE)


def _json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _artifact_status(path: Path) -> str:
    if path.suffix.lower() == ".json":
        return str(_json(path).get("status") or "").strip().lower()
    if path.suffix.lower() in {".md", ".markdown"}:
        text = path.read_text(encoding="utf-8", errors="ignore")[:4096]
        match = FRONTMATTER_STATUS_RE.search(text)
        return str(match.group(1)).strip().lower() if match else ""
    return ""


def _review_ready(root: Path, evidence_paths: Sequence[str]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    status_files = 0
    for rel in evidence_paths:
        path = root / rel
        if not path.is_file():
            issues.append(f"缺待签产物：{rel}")
            continue
        status = _artifact_status(path)
        if status:
            status_files += 1
            if status not in READY_STATUSES:
                issues.append(f"待签产物尚不可审：{rel} status={status}")
    if not issues and status_files == 0:
        issues.append("待签产物没有任何 confirmed/ready 状态证据，拒绝代理签收")
    return not issues, issues


def _check_manifest(root: Path, spec: Mapping[str, Any], manifest: Mapping[str, Any]) -> List[str]:
    return validate_manifest(
        manifest,
        root,
        artifact_scope=str(spec["artifact_scope"]),
        input_paths=spec["input_paths"],
        evidence_paths=spec["evidence_paths"],
        required_role_groups=spec["required_role_groups"],
    )


def _role_for_group(roles: Sequence[str]) -> str:
    for preferred in ("director", "producer", "head_writer", "editor", "assistant_director", "script_supervisor", "showrunner"):
        if preferred in roles:
            return preferred
    return str(roles[0])


def authorize(root: Path, *, authorized_by: str, source_quote: str) -> Dict[str, Any]:
    payload = new_authorization(root, authorized_by=authorized_by, source_quote=source_quote)
    issues = validate_authorization(payload, root)
    if issues:
        return {"status": "error", "issues": issues, "setting_required": f"{SETTING_KEY}={SETTING_VALUE}"}
    path = write_authorization(root, payload)
    return {"status": "active", "path": str(path), "authorization": payload}


def status(root: Path) -> Dict[str, Any]:
    payload = load_authorization(root)
    issues = validate_authorization(payload, root)
    return {
        "status": "active" if not issues else "invalid",
        "path": str(authorization_path(root)),
        "issues": issues,
        "authorization": payload,
    }


def approve(root: Path, profile: str, episode: str = "") -> Dict[str, Any]:
    spec = profile_spec(root, profile, episode)
    path = root / str(spec["signoff_path"])
    current = load_manifest(path)
    if current and not _check_manifest(root, spec, current):
        return {
            "status": "already_approved",
            "profile": profile,
            "episode": spec["episode"],
            "path": str(spec["signoff_path"]),
        }

    authorization = load_authorization(root)
    authorization_issues = validate_authorization(authorization, root, profile=profile)
    if authorization_issues:
        return {"status": "invalid_authorization", "issues": authorization_issues}
    ready, readiness_issues = _review_ready(root, spec["evidence_paths"])
    if not ready:
        return {"status": "not_ready", "issues": readiness_issues}

    current_inputs = artifact_fingerprint(root, spec["input_paths"])
    current_evidence = artifact_fingerprint(root, spec["evidence_paths"])
    if (
        not current
        or not isinstance(current.get("input_fingerprint"), dict)
        or current["input_fingerprint"].get("sha") != current_inputs["sha"]
        or not isinstance(current.get("evidence_fingerprint"), dict)
        or current["evidence_fingerprint"].get("sha") != current_evidence["sha"]
    ):
        current = new_manifest(
            root,
            artifact_scope=spec["artifact_scope"],
            episode=spec["episode"],
            author_id=str(current.get("authored_by") or "automation:n2d") if current else "automation:n2d",
            input_paths=spec["input_paths"],
            evidence_paths=spec["evidence_paths"],
            required_role_groups=spec["required_role_groups"],
        )

    for group_name, roles in spec["required_role_groups"]:
        role = _role_for_group(roles)
        current = record_approval(
            current,
            root,
            reviewer_id=DELEGATED_REVIEWER_ID,
            reviewer_role=role,
            evidence_paths=spec["evidence_paths"],
            note=(
                f"项目负责人已启用“{SETTING_VALUE}”；代理按当前 confirmed/ready 产物与哈希完成"
                f" {profile}:{group_name} 内部交接签收。独立人审已由负责人在授权范围内豁免。"
            ),
            delegation_authorization=authorization,
            delegation_profile=profile,
        )
    write_manifest(path, current)
    issues = _check_manifest(root, spec, current)
    return {
        "status": "approved" if not issues else "block",
        "profile": profile,
        "episode": spec["episode"],
        "path": str(spec["signoff_path"]),
        "issues": issues,
        "approval_mode": "delegated_autonomy",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="n2d low-risk delegated approval policy")
    sub = parser.add_subparsers(dest="command", required=True)
    auth = sub.add_parser("authorize")
    auth.add_argument("root")
    auth.add_argument("--authorized-by", required=True)
    auth.add_argument("--source-quote", required=True)
    auth.add_argument("--json", action="store_true")
    check = sub.add_parser("status")
    check.add_argument("root")
    check.add_argument("--json", action="store_true")
    sign = sub.add_parser("approve")
    sign.add_argument("root")
    sign.add_argument("profile", choices=("p1", "table_read", "p2", "animatic", "p3"))
    sign.add_argument("episode", nargs="?", default="")
    sign.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    root = Path(ns.root).resolve()
    if ns.command == "authorize":
        result = authorize(root, authorized_by=ns.authorized_by, source_quote=ns.source_quote)
    elif ns.command == "status":
        result = status(root)
    else:
        result = approve(root, ns.profile, ns.episode)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"autonomy {ns.command}: {result.get('status')}")
        for issue in result.get("issues") or []:
            print(f"- {issue}")
    return 0 if result.get("status") in {"active", "approved", "already_approved"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
