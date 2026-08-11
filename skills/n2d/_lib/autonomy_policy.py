#!/usr/bin/env python3
"""Project-scoped delegated approval policy for low-risk n2d work.

The policy deliberately does not turn an agent into a human reviewer.  It
records that the project owner waived independent review for reversible,
internal creative handoffs while retaining explicit stops for money, rights,
release, voice cloning, and destructive changes.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

try:
    from settings import get_setting
except ImportError:  # pragma: no cover - package import fallback
    from .settings import get_setting


KIND = "n2d_autonomy_authorization"
VERSION = 1
AUTHORIZATION_REL = "生产数据/autonomy_authorization.json"
POLICY = "only_high_risk_human"
SETTING_KEY = "人工批准策略"
SETTING_VALUE = "仅高风险停审"
DELEGATED_REVIEWER_ID = "delegate:n2d-agent"
DELEGABLE_SIGNOFF_PROFILES = ("p1", "table_read", "p2", "animatic", "p3")
DELEGABLE_BOUNDARY_DECISIONS = ("keep",)
REQUIRED_HUMAN_STOPS = (
    "paid_generation_or_purchase",
    "rights_compliance_or_age_rating",
    "voice_clone_or_biometric_authorization",
    "public_release_or_distribution",
    "destructive_or_irreversible_change",
)

_AUTOMATION_ID_RE = re.compile(
    r"^(?:auto(?:mated|mation)?|machine|system|agent|bot|ai|codex|claude|gpt|gemini|copilot|delegate)",
    re.IGNORECASE,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authorization_path(root: str | Path) -> Path:
    return Path(root).resolve() / AUTHORIZATION_REL


def _authorization_id(root: Path, authorized_by: str, authorized_at: str) -> str:
    raw = f"{root.resolve()}\0{authorized_by}\0{authorized_at}".encode("utf-8")
    return "AUTH_" + hashlib.sha256(raw).hexdigest()[:16]


def _human_authorizer_error(value: Any) -> str:
    authorizer = str(value or "").strip()
    if not authorizer:
        return "authorized_by 不能为空"
    if _AUTOMATION_ID_RE.match(authorizer) or authorizer.lower() in {"human", "user", "unknown", "anonymous", "todo", "tbd"}:
        return "authorized_by 必须是明确的项目负责人身份，不能是自动化/泛称身份"
    return ""


def new_authorization(
    root: str | Path,
    *,
    authorized_by: str,
    source_quote: str,
    allowed_signoff_profiles: Sequence[str] = DELEGABLE_SIGNOFF_PROFILES,
) -> Dict[str, Any]:
    project_root = Path(root).resolve()
    error = _human_authorizer_error(authorized_by)
    if error:
        raise ValueError(error)
    quote = str(source_quote or "").strip()
    if not quote:
        raise ValueError("source_quote 不能为空；必须保留用户的一次性授权原话")
    profiles = [str(item).strip().lower() for item in allowed_signoff_profiles if str(item).strip()]
    unknown = sorted(set(profiles) - set(DELEGABLE_SIGNOFF_PROFILES))
    if unknown:
        raise ValueError("存在不可委托 signoff profile：" + "、".join(unknown))
    authorized_at = now_iso()
    return {
        "kind": KIND,
        "version": VERSION,
        "status": "active",
        "policy": POLICY,
        "project_root": str(project_root),
        "project_name": project_root.name,
        "authorization_id": _authorization_id(project_root, str(authorized_by).strip(), authorized_at),
        "authorized_by": str(authorized_by).strip(),
        "authorized_at": authorized_at,
        "source_quote": quote,
        "delegated_reviewer_id": DELEGATED_REVIEWER_ID,
        "allowed_signoff_profiles": profiles,
        "allowed_boundary_decisions": list(DELEGABLE_BOUNDARY_DECISIONS),
        "allowed_internal_actions": [
            "reversible_text_and_prompt_decisions",
            "hash_bound_internal_handoff_signoff",
            "non_mutating_boundary_keep_with_semantic_evidence",
            "deterministic_checks_and_internal_previews",
        ],
        "human_confirmation_required": list(REQUIRED_HUMAN_STOPS),
        "independent_review": "waived_by_project_owner_for_allowed_internal_actions",
    }


def load_authorization(root: str | Path) -> Dict[str, Any]:
    path = authorization_path(root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def write_authorization(root: str | Path, payload: Mapping[str, Any]) -> Path:
    path = authorization_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def validate_authorization(
    payload: Any,
    root: str | Path,
    *,
    profile: str = "",
    boundary_decision: str = "",
) -> List[str]:
    issues: List[str] = []
    project_root = Path(root).resolve()
    if not isinstance(payload, Mapping):
        return ["缺项目级自主授权"]
    if payload.get("kind") != KIND:
        issues.append(f"kind 必须是 {KIND}")
    if int(payload.get("version") or 0) != VERSION:
        issues.append(f"version 必须是 {VERSION}")
    if str(payload.get("status") or "").strip().lower() != "active":
        issues.append("自主授权不是 active")
    if str(payload.get("policy") or "") != POLICY:
        issues.append(f"policy 必须是 {POLICY}")
    if str(payload.get("project_root") or "") != str(project_root):
        issues.append("自主授权绑定的 project_root 与当前作品根不一致")
    authorizer_error = _human_authorizer_error(payload.get("authorized_by"))
    if authorizer_error:
        issues.append(authorizer_error)
    if not str(payload.get("authorized_at") or "").strip():
        issues.append("缺 authorized_at")
    if not str(payload.get("source_quote") or "").strip():
        issues.append("缺用户授权原话 source_quote")
    if str(payload.get("delegated_reviewer_id") or "") != DELEGATED_REVIEWER_ID:
        issues.append(f"delegated_reviewer_id 必须是 {DELEGATED_REVIEWER_ID}")
    required_stops = {str(item) for item in payload.get("human_confirmation_required") or []}
    missing_stops = sorted(set(REQUIRED_HUMAN_STOPS) - required_stops)
    if missing_stops:
        issues.append("自主授权缺不可放开的高风险停审项：" + "、".join(missing_stops))
    effective = str(get_setting(str(project_root), SETTING_KEY, "逐节点人工批准") or "")
    if effective != SETTING_VALUE:
        issues.append(f"{SETTING_KEY} 未设为 {SETTING_VALUE}")
    if profile:
        key = str(profile).strip().lower()
        if key not in DELEGABLE_SIGNOFF_PROFILES:
            issues.append(f"profile={key} 不属于可委托内部签收")
        allowed = {str(item).strip().lower() for item in payload.get("allowed_signoff_profiles") or []}
        if key not in allowed:
            issues.append(f"当前授权未覆盖 signoff profile={key}")
    if boundary_decision:
        decision = str(boundary_decision).strip().lower()
        allowed = {str(item).strip().lower() for item in payload.get("allowed_boundary_decisions") or []}
        if decision not in DELEGABLE_BOUNDARY_DECISIONS or decision not in allowed:
            issues.append(f"边界 decision={decision} 不可代理签收；改边界必须人工停审")
    return issues


def authorization_sha256(root: str | Path) -> str:
    path = authorization_path(root)
    return file_sha256(path) if path.is_file() else ""


def delegation_record(
    root: str | Path,
    payload: Mapping[str, Any],
    *,
    profile: str = "",
    boundary_decision: str = "",
) -> Dict[str, Any]:
    issues = validate_authorization(payload, root, profile=profile, boundary_decision=boundary_decision)
    if issues:
        raise ValueError("；".join(issues))
    return {
        "review_mode": "delegated_autonomy",
        "independent_review": "waived_by_project_owner",
        "authorized_by": str(payload.get("authorized_by") or ""),
        "authorization_id": str(payload.get("authorization_id") or ""),
        "authorization_path": AUTHORIZATION_REL,
        "authorization_sha256": authorization_sha256(root),
        "delegation_profile": str(profile or "boundary_keep"),
    }
