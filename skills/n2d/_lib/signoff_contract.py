#!/usr/bin/env python3
"""Auditable sign-off contracts for n2d creative and production handoffs.

``status=confirmed`` means an artifact is complete enough to review.  It is not
an approval.  This module keeps approval as a separate, hash-bound manifest so
an artifact generator cannot silently approve its own output.

The implementation is standard-library only and intentionally independent of
any particular agent or review UI.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

try:
    from autonomy_policy import (
        DELEGATED_REVIEWER_ID,
        authorization_sha256,
        delegation_record,
        load_authorization,
        validate_authorization,
    )
except ImportError:  # pragma: no cover - package import fallback
    from .autonomy_policy import (
        DELEGATED_REVIEWER_ID,
        authorization_sha256,
        delegation_record,
        load_authorization,
        validate_authorization,
    )


KIND = "n2d_artifact_signoff"
VERSION = 1
APPROVED_DECISIONS = {"approved", "approved_with_risk"}
GENERIC_REVIEWER_IDS = {
    "", "agent", "human", "agent_or_human", "unknown", "anonymous", "todo",
    "tbd", "automation", "automation:n2d", "system",
}

PROFILE_ROLE_GROUPS: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]] = {
    "p1": (
        ("creative", ("showrunner", "head_writer", "director")),
        ("production", ("producer",)),
    ),
    "table_read": (("editorial", ("director", "head_writer")),),
    "p2": (
        ("creative", ("director",)),
        ("production", ("producer", "editor")),
    ),
    "animatic": (
        ("creative", ("director",)),
        ("editorial", ("editor", "producer")),
    ),
    "p3": (("handoff", ("producer", "assistant_director", "script_supervisor")),),
}

PROFILE_SCOPES = {
    "p1": "p1_development_greenlight",
    "table_read": "stage1_table_read",
    "p2": "p2_director_blocking",
    "animatic": "stage2_animatic",
    "p3": "p3_production_handoff",
}

SCOPE_PROFILES = {scope: profile for profile, scope in PROFILE_SCOPES.items()}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_rel(root: Path, value: str | Path) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            return str(path)
    return path.as_posix().lstrip("./")


def artifact_fingerprint(root: Path, rels: Iterable[str | Path]) -> Dict[str, Any]:
    """Hash a stable list of files, preserving missing inputs as explicit nulls."""
    files: Dict[str, str | None] = {}
    digest = hashlib.sha256()
    for rel in sorted({_norm_rel(root, item) for item in rels}):
        path = root / rel
        sha = file_sha256(path) if path.is_file() else None
        files[rel] = sha
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update((sha or "-").encode("ascii"))
        digest.update(b"\n")
    return {"files": files, "sha": digest.hexdigest()}


def fingerprint_is_fresh(recorded: Any, root: Path) -> bool | None:
    if not isinstance(recorded, Mapping):
        return None
    files = recorded.get("files")
    sha = recorded.get("sha")
    if not isinstance(files, Mapping) or not isinstance(sha, str) or not sha:
        return None
    return artifact_fingerprint(root, [str(path) for path in files])["sha"] == sha


def normalize_role_groups(groups: Sequence[Mapping[str, Any] | Tuple[str, Sequence[str]]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in groups:
        if isinstance(item, Mapping):
            group = str(item.get("group") or "").strip()
            roles = item.get("roles") or []
        else:
            group, roles = item
        role_list = sorted({str(role).strip().lower() for role in roles if str(role).strip()})
        if group and role_list:
            out.append({"group": group, "roles": role_list})
    return out


def profile_spec(root: Path, profile: str, episode: str = "") -> Dict[str, Any]:
    """Return the canonical sign-off path, inputs, evidence and role groups."""
    key = str(profile or "").strip().lower()
    if key not in PROFILE_SCOPES:
        raise ValueError(f"未知 signoff profile: {profile}")
    ep = str(episode or "").strip()
    if key != "p1" and not ep:
        raise ValueError(f"{key} signoff 需要 --episode")
    if ep and not (ep.startswith("第") and ep.endswith("集")):
        ep = f"第{ep}集"

    if key == "p1":
        novel_files = sorted(
            path.relative_to(root).as_posix()
            for base in (root / "小说", root)
            if base.is_dir()
            for path in base.glob("*")
            if path.is_file() and path.suffix.lower() in {".txt", ".docx", ".md"}
            and (
                base != root
                or (
                    path.parent == root
                    and path.name not in {"_进度.md", "_设置.md"}
                    and not path.name.startswith(".")
                )
            )
        )
        inputs = novel_files + (["_设置.md"] if (root / "_设置.md").is_file() else [])
        evidence = [f"开发包/{name}" for name in (
            "series_bible.md", "adaptation_strategy.json", "season_arc.json",
            "production_feasibility.json", "pilot_greenlight.md",
        )]
        signoff_path = "开发包/signoff.json"
    elif key == "table_read":
        inputs = [
            f"脚本/{ep}/voiceover.txt",
            f"合成/{ep}/配音/时长清单.json",
        ]
        evidence = [f"脚本/{ep}/table_read_packet.json", f"脚本/{ep}/table_read_packet.md"]
        signoff_path = f"脚本/{ep}/table_read_signoff.json"
    elif key == "p2":
        inputs = [
            "设定库/source_comprehension.json",
            f"脚本/{ep}/voiceover.txt",
            f"脚本/{ep}/table_read_packet.json",
            f"脚本/{ep}/table_read_signoff.json",
        ]
        evidence = [f"脚本/{ep}/{name}" for name in (
            "director_beat_sheet.json", "axis_blocking_map.json", "shot_progression_plan.json",
            "transition_map.json", "vertical_composition_plan.json", "edit_rhythm_map.json",
        )]
        signoff_path = f"脚本/{ep}/director_blocking_signoff.json"
    elif key == "animatic":
        inputs = [
            f"脚本/{ep}/storyboard.json",
            f"脚本/{ep}/镜头时长.json",
            f"脚本/{ep}/字幕_中文.srt",
            f"合成/{ep}/配音/voice_zh.wav",
        ]
        evidence = [
            f"脚本/{ep}/animatic_packet.json",
            f"脚本/{ep}/animatic_packet.md",
            f"生产数据/animatic_{ep}.json",
            f"生产数据/animatic_{ep}.html",
            f"生产数据/timelines/{ep}/animatic_timeline.otio",
        ]
        signoff_path = f"脚本/{ep}/animatic_signoff.json"
    else:  # p3
        inputs = [
            "设定库/source_comprehension.json",
            f"脚本/{ep}/voiceover.txt",
            f"脚本/{ep}/storyboard.json",
            f"脚本/{ep}/镜头时长.json",
            f"脚本/{ep}/director_blocking_signoff.json",
            f"脚本/{ep}/animatic_signoff.json",
            f"脚本/{ep}/preventive_contracts.json",
            f"生产数据/script_quality_contract_{ep}.json",
        ]
        evidence = [f"脚本/{ep}/{name}" for name in (
            "production_breakdown.json", "continuity_breakdown.json", "continuity_chain.json",
            "continuity_bible.json", "ai_shooting_schedule.json", "ai_call_sheet.md",
        )]
        signoff_path = f"脚本/{ep}/production_handoff_signoff.json"

    return {
        "profile": key,
        "artifact_scope": PROFILE_SCOPES[key],
        "episode": ep,
        "signoff_path": signoff_path,
        "input_paths": inputs,
        "evidence_paths": evidence,
        "required_role_groups": PROFILE_ROLE_GROUPS[key],
    }


def new_manifest(
    root: Path,
    *,
    artifact_scope: str,
    episode: str = "",
    author_id: str = "automation:n2d",
    input_paths: Sequence[str | Path] = (),
    evidence_paths: Sequence[str | Path] = (),
    required_role_groups: Sequence[Mapping[str, Any] | Tuple[str, Sequence[str]]] = (),
) -> Dict[str, Any]:
    return {
        "kind": KIND,
        "version": VERSION,
        "artifact_scope": artifact_scope,
        "episode": episode,
        "authored_by": str(author_id or "automation:n2d").strip(),
        "created_at": now_iso(),
        "input_fingerprint": artifact_fingerprint(root, input_paths),
        "evidence_fingerprint": artifact_fingerprint(root, evidence_paths),
        "required_approval_groups": normalize_role_groups(required_role_groups),
        "approvals": [],
        "status": "pending",
    }


def _approval_key(item: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(item.get("reviewer_id") or "").strip().lower(),
        str(item.get("reviewer_role") or "").strip().lower(),
    )


def record_approval(
    manifest: Mapping[str, Any],
    root: Path,
    *,
    reviewer_id: str,
    reviewer_role: str,
    evidence_paths: Sequence[str | Path],
    decision: str = "approved",
    note: str = "",
    unresolved_risks: Sequence[str] = (),
    waiver_reason: str = "",
    delegation_authorization: Mapping[str, Any] | None = None,
    delegation_profile: str = "",
) -> Dict[str, Any]:
    payload = dict(manifest)
    rid = str(reviewer_id or "").strip()
    role = str(reviewer_role or "").strip().lower()
    decision = str(decision or "approved").strip().lower()
    delegated = isinstance(delegation_authorization, Mapping)
    profile = str(delegation_profile or SCOPE_PROFILES.get(str(payload.get("artifact_scope") or ""), "")).strip().lower()
    if rid.lower() in GENERIC_REVIEWER_IDS:
        raise ValueError("reviewer_id 必须是明确身份，不能使用 agent_or_human/unknown 等泛称")
    if rid.lower().startswith("delegate:") and not delegated:
        raise ValueError("delegate reviewer 必须绑定有效的项目级 autonomy authorization")
    delegation_meta: Dict[str, Any] = {}
    if delegated:
        if rid != DELEGATED_REVIEWER_ID:
            raise ValueError(f"代理签收 reviewer_id 必须是 {DELEGATED_REVIEWER_ID}")
        delegation_meta = delegation_record(root, delegation_authorization, profile=profile)
    if not role:
        raise ValueError("reviewer_role 不能为空")
    if rid.lower() == str(payload.get("authored_by") or "").strip().lower():
        raise ValueError("产物作者不能审批自己的产物；请使用独立 reviewer_id")
    if decision not in APPROVED_DECISIONS | {"changes_requested", "rejected"}:
        raise ValueError(f"不支持的 decision: {decision}")
    risks = [str(item).strip() for item in unresolved_risks if str(item).strip()]
    if decision == "approved_with_risk" and (not risks or not str(waiver_reason).strip()):
        raise ValueError("approved_with_risk 必须同时写 unresolved_risks 与 waiver_reason")
    evidence = artifact_fingerprint(root, evidence_paths)
    missing = [path for path, sha in evidence["files"].items() if not sha]
    if missing:
        raise ValueError("签收证据文件不存在：" + "、".join(missing))
    recorded_inputs = payload.get("input_fingerprint")
    recorded_evidence = payload.get("evidence_fingerprint")
    if fingerprint_is_fresh(recorded_inputs, root) is not True:
        raise ValueError("input_fingerprint 缺失或过期；请刷新 manifest 后重新签收")
    if fingerprint_is_fresh(recorded_evidence, root) is not True:
        raise ValueError("evidence_fingerprint 缺失或过期；请刷新 manifest 后重新签收")
    expected_evidence_files = (
        recorded_evidence.get("files") if isinstance(recorded_evidence, Mapping) else {}
    )
    if not isinstance(expected_evidence_files, Mapping):
        expected_evidence_files = {}
    uncovered = [
        str(path)
        for path, sha in expected_evidence_files.items()
        if not sha or evidence["files"].get(str(path)) != sha
    ]
    if uncovered:
        raise ValueError("本次审批证据未覆盖完整待签产物：" + "、".join(uncovered))
    recorded_input_files = recorded_inputs.get("files") if isinstance(recorded_inputs, Mapping) else {}
    missing_upstream_signoffs = [
        str(path) for path, sha in (recorded_input_files.items() if isinstance(recorded_input_files, Mapping) else [])
        if str(path).endswith("signoff.json") and not sha
    ]
    if missing_upstream_signoffs:
        raise ValueError("缺上游签收，不能审批当前交接：" + "、".join(missing_upstream_signoffs))
    approval = {
        "reviewer_id": rid,
        "reviewer_role": role,
        "decision": decision,
        "reviewed_at": now_iso(),
        "signed_input_fingerprint_sha": str(recorded_inputs.get("sha") or ""),
        "signed_evidence_fingerprint_sha": str(recorded_evidence.get("sha") or ""),
        "evidence": [
            {"path": path, "sha256": sha}
            for path, sha in evidence["files"].items()
            if sha
        ],
        "note": str(note or "").strip(),
        "unresolved_risks": risks,
        "waiver_reason": str(waiver_reason or "").strip(),
    }
    approval.update(delegation_meta)
    approvals = [item for item in payload.get("approvals") or [] if isinstance(item, Mapping)]
    key = _approval_key(approval)
    approvals = [dict(item) for item in approvals if _approval_key(item) != key]
    approvals.append(approval)
    payload["approvals"] = approvals
    payload["status"] = derived_status(payload)
    payload["updated_at"] = now_iso()
    return payload


def derived_status(manifest: Mapping[str, Any]) -> str:
    approvals = [item for item in manifest.get("approvals") or [] if isinstance(item, Mapping)]
    if any(str(item.get("decision") or "").lower() in {"changes_requested", "rejected"} for item in approvals):
        return "changes_requested"
    groups = normalize_role_groups(manifest.get("required_approval_groups") or [])
    for group in groups:
        roles = set(group["roles"])
        if not any(
            str(item.get("decision") or "").lower() in APPROVED_DECISIONS
            and str(item.get("reviewer_role") or "").strip().lower() in roles
            for item in approvals
        ):
            return "pending"
    return "approved" if groups else "pending"


def validate_manifest(
    manifest: Any,
    root: Path,
    *,
    artifact_scope: str,
    input_paths: Sequence[str | Path],
    evidence_paths: Sequence[str | Path],
    required_role_groups: Sequence[Mapping[str, Any] | Tuple[str, Sequence[str]]],
) -> List[str]:
    issues: List[str] = []
    if not isinstance(manifest, Mapping):
        return ["缺结构化 signoff manifest"]
    if manifest.get("kind") != KIND:
        issues.append(f"kind 必须是 {KIND}")
    if str(manifest.get("artifact_scope") or "") != artifact_scope:
        issues.append(f"artifact_scope 不匹配：期望 {artifact_scope}")
    author_id = str(manifest.get("authored_by") or "").strip()
    if not author_id:
        issues.append("缺 authored_by，无法执行作者/审批者分离")
    expected_groups = normalize_role_groups(required_role_groups)
    actual_groups = normalize_role_groups(manifest.get("required_approval_groups") or [])
    if actual_groups != expected_groups:
        issues.append("required_approval_groups 与当前流程合同不一致")
    expected_inputs = artifact_fingerprint(root, input_paths)
    recorded_inputs = manifest.get("input_fingerprint")
    if not isinstance(recorded_inputs, Mapping) or recorded_inputs.get("sha") != expected_inputs["sha"]:
        issues.append("input_fingerprint 缺失或过期；上游输入变化后必须重新签收")
    missing_upstream_signoffs = [
        path for path, sha in expected_inputs["files"].items()
        if path.endswith("signoff.json") and not sha
    ]
    if missing_upstream_signoffs:
        issues.append("缺上游签收：" + "、".join(missing_upstream_signoffs))
    expected_evidence = artifact_fingerprint(root, evidence_paths)
    recorded_evidence = manifest.get("evidence_fingerprint")
    if not isinstance(recorded_evidence, Mapping) or recorded_evidence.get("sha") != expected_evidence["sha"]:
        issues.append("evidence_fingerprint 缺失或过期；待签产物变化后必须重新签收")
    missing_outputs = [path for path, sha in expected_evidence["files"].items() if not sha]
    if missing_outputs:
        issues.append("待签产物缺失：" + "、".join(missing_outputs))

    profile = SCOPE_PROFILES.get(artifact_scope, "")
    approvals = [item for item in manifest.get("approvals") or [] if isinstance(item, Mapping)]
    valid_approvals: List[Mapping[str, Any]] = []
    for item in approvals:
        rid = str(item.get("reviewer_id") or "").strip()
        role = str(item.get("reviewer_role") or "").strip().lower()
        decision = str(item.get("decision") or "").strip().lower()
        prefix = f"approval[{rid or '?'}:{role or '?'}]"
        if rid.lower() in GENERIC_REVIEWER_IDS:
            issues.append(f"{prefix} reviewer_id 不是明确身份")
            continue
        review_mode = str(item.get("review_mode") or "").strip().lower()
        if rid.lower().startswith("delegate:") and review_mode != "delegated_autonomy":
            issues.append(f"{prefix} delegate reviewer 未绑定 delegated_autonomy 元数据")
            continue
        if review_mode == "delegated_autonomy":
            authorization = load_authorization(root)
            delegation_issues = validate_authorization(authorization, root, profile=profile)
            if delegation_issues:
                issues.append(f"{prefix} 项目级自主授权失效：{'；'.join(delegation_issues)}")
                continue
            if rid != DELEGATED_REVIEWER_ID:
                issues.append(f"{prefix} delegated reviewer_id 不匹配")
                continue
            if str(item.get("authorized_by") or "") != str(authorization.get("authorized_by") or ""):
                issues.append(f"{prefix} authorized_by 与当前自主授权不一致")
                continue
            if str(item.get("authorization_id") or "") != str(authorization.get("authorization_id") or ""):
                issues.append(f"{prefix} authorization_id 与当前自主授权不一致")
                continue
            if str(item.get("authorization_sha256") or "") != authorization_sha256(root):
                issues.append(f"{prefix} autonomy authorization 哈希已变化，需重新签收")
                continue
        if author_id and rid.lower() == author_id.lower():
            issues.append(f"{prefix} 违反作者/审批者分离")
            continue
        if decision not in APPROVED_DECISIONS:
            continue
        if not str(item.get("reviewed_at") or "").strip():
            issues.append(f"{prefix} 缺 reviewed_at")
            continue
        if str(item.get("signed_input_fingerprint_sha") or "") != expected_inputs["sha"]:
            issues.append(f"{prefix} 未绑定当前 input_fingerprint")
            continue
        if str(item.get("signed_evidence_fingerprint_sha") or "") != expected_evidence["sha"]:
            issues.append(f"{prefix} 未绑定当前 evidence_fingerprint")
            continue
        risks = [str(r).strip() for r in item.get("unresolved_risks") or [] if str(r).strip()]
        if decision == "approved_with_risk" and (not risks or not str(item.get("waiver_reason") or "").strip()):
            issues.append(f"{prefix} 风险签收缺 unresolved_risks/waiver_reason")
            continue
        evidence = [row for row in item.get("evidence") or [] if isinstance(row, Mapping)]
        if not evidence:
            issues.append(f"{prefix} 缺 path+sha256 审批证据")
            continue
        evidence_map = {
            _norm_rel(root, str(row.get("path") or "")): str(row.get("sha256") or "")
            for row in evidence
        }
        uncovered = [
            path for path, sha in expected_evidence["files"].items()
            if not sha or evidence_map.get(path) != sha
        ]
        if uncovered:
            issues.append(f"{prefix} 审批证据未覆盖完整待签产物：{', '.join(uncovered)}")
            continue
        stale = False
        for row in evidence:
            rel = _norm_rel(root, str(row.get("path") or ""))
            sha = str(row.get("sha256") or "")
            path = root / rel
            if not rel or not sha or not path.is_file() or file_sha256(path) != sha:
                issues.append(f"{prefix} 证据缺失或哈希过期：{rel or '?'}")
                stale = True
                break
        if not stale:
            valid_approvals.append(item)

    for group in expected_groups:
        roles = set(group["roles"])
        if not any(str(item.get("reviewer_role") or "").strip().lower() in roles for item in valid_approvals):
            issues.append(f"缺 {group['group']} 审批；允许角色：{', '.join(group['roles'])}")
    if str(manifest.get("status") or "").lower() != derived_status(manifest):
        issues.append("status 不是由当前 approvals 派生的最新状态")
    if derived_status(manifest) != "approved":
        issues.append("signoff 尚未 approved")
    return issues


def load_manifest(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_manifest(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
