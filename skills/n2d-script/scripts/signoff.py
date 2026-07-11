#!/usr/bin/env python3
"""Create, approve and verify hash-bound n2d sign-off manifests.

Examples:
  python3 skills/n2d-script/scripts/signoff.py <作品根> p2 init 第1集
  python3 skills/n2d-script/scripts/signoff.py <作品根> p2 approve 第1集 \
      --reviewer-id user:alice --reviewer-role director --note "blocking/axis approved"
  python3 skills/n2d-script/scripts/signoff.py <作品根> p2 check 第1集 --json

The same person may wear multiple crew roles in a solo production, but an
approval identity may not equal the recorded artifact author identity.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence


N2D_LIB = Path(__file__).resolve().parents[2] / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

from signoff_contract import (  # noqa: E402
    artifact_fingerprint,
    load_manifest,
    new_manifest,
    profile_spec,
    record_approval,
    validate_manifest,
    write_manifest,
)


def _init(root: Path, spec: Dict[str, Any], author_id: str, *, force: bool = False) -> Dict[str, Any]:
    path = root / spec["signoff_path"]
    if path.is_file() and not force:
        payload = load_manifest(path)
        return {"status": "exists", "path": spec["signoff_path"], "manifest": payload}
    payload = new_manifest(
        root,
        artifact_scope=spec["artifact_scope"],
        episode=spec["episode"],
        author_id=author_id,
        input_paths=spec["input_paths"],
        evidence_paths=spec["evidence_paths"],
        required_role_groups=spec["required_role_groups"],
    )
    write_manifest(path, payload)
    return {"status": "initialized", "path": spec["signoff_path"], "manifest": payload}


def _check(root: Path, spec: Dict[str, Any]) -> Dict[str, Any]:
    path = root / spec["signoff_path"]
    payload = load_manifest(path)
    issues = validate_manifest(
        payload,
        root,
        artifact_scope=spec["artifact_scope"],
        input_paths=spec["input_paths"],
        evidence_paths=spec["evidence_paths"],
        required_role_groups=spec["required_role_groups"],
    )
    return {
        "kind": "n2d_signoff_check",
        "profile": spec["profile"],
        "episode": spec["episode"],
        "path": spec["signoff_path"],
        "status": "pass" if not issues else "block",
        "issues": issues,
        "required_approval_groups": [
            {"group": group, "roles": list(roles)}
            for group, roles in spec["required_role_groups"]
        ],
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d hash-bound sign-off")
    ap.add_argument("root")
    ap.add_argument("profile", choices=("p1", "table_read", "p2", "animatic", "p3"))
    ap.add_argument("command", choices=("init", "approve", "check"))
    ap.add_argument("episode", nargs="?", default="", help="p1 可省略；其他 profile 必填第N集")
    ap.add_argument("--author-id", default="automation:n2d")
    ap.add_argument("--reviewer-id", default="")
    ap.add_argument("--reviewer-role", default="")
    ap.add_argument("--decision", choices=("approved", "approved_with_risk", "changes_requested", "rejected"), default="approved")
    ap.add_argument("--note", default="")
    ap.add_argument("--risk", action="append", default=[])
    ap.add_argument("--waiver-reason", default="")
    ap.add_argument("--evidence", action="append", default=[], help="额外证据路径；默认总会签全部 profile 产物")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    try:
        spec = profile_spec(root, ns.profile, ns.episode)
        if ns.command == "init":
            result = _init(root, spec, ns.author_id, force=ns.force)
            code = 0
        elif ns.command == "approve":
            path = root / spec["signoff_path"]
            payload = load_manifest(path)
            if not payload:
                payload = _init(root, spec, ns.author_id)["manifest"]
            current_inputs = artifact_fingerprint(root, spec["input_paths"])
            current_evidence = artifact_fingerprint(root, spec["evidence_paths"])
            recorded_inputs = payload.get("input_fingerprint")
            recorded_evidence = payload.get("evidence_fingerprint")
            if (
                not isinstance(recorded_inputs, dict)
                or recorded_inputs.get("sha") != current_inputs["sha"]
                or not isinstance(recorded_evidence, dict)
                or recorded_evidence.get("sha") != current_evidence["sha"]
            ):
                payload = new_manifest(
                    root,
                    artifact_scope=spec["artifact_scope"],
                    episode=spec["episode"],
                    author_id=str(payload.get("authored_by") or ns.author_id),
                    input_paths=spec["input_paths"],
                    evidence_paths=spec["evidence_paths"],
                    required_role_groups=spec["required_role_groups"],
                )
            payload = record_approval(
                payload,
                root,
                reviewer_id=ns.reviewer_id,
                reviewer_role=ns.reviewer_role,
                evidence_paths=[*spec["evidence_paths"], *ns.evidence],
                decision=ns.decision,
                note=ns.note,
                unresolved_risks=ns.risk,
                waiver_reason=ns.waiver_reason,
            )
            write_manifest(path, payload)
            result = _check(root, spec)
            result["approval_recorded"] = True
            result["approval_status"] = payload.get("status")
            # Recording one required role is a successful mutation even when
            # the overall multi-role sign-off is still pending. `check` remains
            # the command whose exit code represents final gate readiness.
            code = 0
        else:
            result = _check(root, spec)
            code = 0 if result["status"] == "pass" else 1
    except (ValueError, OSError) as exc:
        result = {"status": "error", "message": str(exc)}
        code = 2
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"signoff {ns.profile}: {result.get('status')} · {result.get('path', '')}")
        if result.get("approval_recorded") and result.get("status") != "pass":
            print("- 本次审批已记录；仍缺其它角色或存在待处理签收问题，完成后再运行 check。")
        for issue in result.get("issues") or []:
            print(f"- {issue}")
        if result.get("message"):
            print(f"- {result['message']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
