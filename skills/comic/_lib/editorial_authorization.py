#!/usr/bin/env python3
"""Project-local authorization checks for delegated comic editorial review.

This module deliberately recognizes only explicit project evidence.  It never
falls back to the comic defaults or a global preference: a ``delegate:``
reviewer may approve name/layout only when the project setting says so, or when
the project carries a current, digest-bound authorization envelope.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


DELEGATED_REVIEW_POLICY = "用户授权制作代理"
AUTHORIZATION_SCHEMA = "comic-editorial-authorization/v1"
AUTHORIZATION_RELATIVE_PATH = Path("生产数据") / "authorizations" / "editorial_review.json"
EDITORIAL_STAGES = {"name_board", "layout"}


class EditorialAuthorizationError(ValueError):
    """Raised when a delegated reviewer lacks current project authorization."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _sha256_json(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def project_review_policy(root: Path) -> str:
    """Read only the project file; absence must not inherit a permissive default."""
    path = root / "_设置.md"
    if not path.is_file():
        return ""
    pattern = re.compile(r"^\s*[-*]\s*(?:\*\*)?审阅策略(?:\*\*)?\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return re.split(r"\s+#", match.group(1), maxsplit=1)[0].strip()
    return ""


def authorization_payload_sha256(payload: dict[str, Any]) -> str:
    """Digest the envelope fields while excluding the digest itself."""
    subject = {key: value for key, value in payload.items() if key != "authorization_sha256"}
    return _sha256_json(subject)


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp 必须包含时区")
    return parsed.astimezone(timezone.utc)


def _setting_authorization(stage: str) -> dict[str, Any]:
    subject = {
        "source": "project_setting",
        "policy": DELEGATED_REVIEW_POLICY,
        "scope": ["name_board", "layout"],
    }
    return {
        "kind": "comic_editorial_review_authorization",
        **subject,
        "source_path": "_设置.md",
        "authorization_sha256": _sha256_json(subject),
        "stage": stage,
    }


def _envelope_authorization(root: Path, reviewer_id: str, stage: str) -> dict[str, Any]:
    path = root / AUTHORIZATION_RELATIVE_PATH
    if not path.is_file():
        raise EditorialAuthorizationError(
            "项目未显式设置 审阅策略=用户授权制作代理，且缺少 "
            f"{AUTHORIZATION_RELATIVE_PATH.as_posix()}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorialAuthorizationError(f"代理审阅授权 envelope 无法读取：{exc}") from exc
    if not isinstance(payload, dict):
        raise EditorialAuthorizationError("代理审阅授权 envelope 顶层必须是 object")

    errors: list[str] = []
    if payload.get("schema") != AUTHORIZATION_SCHEMA:
        errors.append(f"schema 必须为 {AUTHORIZATION_SCHEMA}")
    if payload.get("status") != "authorized":
        errors.append("status 必须为 authorized")
    authorized_by = str(payload.get("authorized_by") or "").strip()
    source_quote = str(payload.get("source_quote") or "").strip()
    issued_at = str(payload.get("issued_at") or "").strip()
    if not authorized_by or authorized_by.startswith("delegate:"):
        errors.append("authorized_by 必须是明确的非代理授权主体")
    if not source_quote:
        errors.append("缺 source_quote")
    if not issued_at:
        errors.append("缺 issued_at")
    else:
        try:
            _parse_timestamp(issued_at)
        except ValueError as exc:
            errors.append(f"issued_at 无效：{exc}")

    scope = payload.get("scope")
    scope_values = {str(item).strip() for item in scope} if isinstance(scope, list) else set()
    if not ({stage, "editorial_review", "*"} & scope_values):
        errors.append(f"scope 未授权 {stage}")
    delegate = str(payload.get("delegate") or "").strip()
    if delegate not in {reviewer_id, "*"}:
        errors.append(f"delegate 未授权 {reviewer_id}")

    expires_at = str(payload.get("expires_at") or "").strip()
    if expires_at:
        try:
            if _parse_timestamp(expires_at) <= datetime.now(timezone.utc):
                errors.append("授权已过期")
        except ValueError as exc:
            errors.append(f"expires_at 无效：{exc}")

    expected_digest = authorization_payload_sha256(payload)
    if str(payload.get("authorization_sha256") or "").strip().lower() != expected_digest:
        errors.append("authorization_sha256 不匹配")
    if errors:
        raise EditorialAuthorizationError("代理审阅授权 envelope 无效：" + "；".join(errors))

    return {
        "kind": "comic_editorial_review_authorization",
        "source": "authorization_envelope",
        "source_path": AUTHORIZATION_RELATIVE_PATH.as_posix(),
        "source_sha256": sha256_file(path),
        "authorization_sha256": expected_digest,
        "authorized_by": authorized_by,
        "scope": sorted(scope_values),
        "delegate": delegate,
        "stage": stage,
        "expires_at": expires_at,
    }


def delegated_review_authorization(root: Path, reviewed_by: str, stage: str) -> dict[str, Any] | None:
    """Return evidence for a delegate, or ``None`` for a human reviewer."""
    reviewer = reviewed_by.strip()
    if not reviewer.startswith("delegate:"):
        return None
    reviewer_id = reviewer.removeprefix("delegate:").strip()
    if not reviewer_id:
        raise EditorialAuthorizationError("delegate: 后必须提供代理身份")
    if stage not in EDITORIAL_STAGES:
        raise EditorialAuthorizationError(f"未知代理审阅 stage：{stage}")
    if project_review_policy(root) == DELEGATED_REVIEW_POLICY:
        return _setting_authorization(stage)
    return _envelope_authorization(root, reviewer_id, stage)


def delegated_authorization_errors(
    root: Path,
    reviewed_by: str,
    stage: str,
    receipt: Any,
) -> list[str]:
    """Verify that a persisted delegated approval still has current authority."""
    if not reviewed_by.strip().startswith("delegate:"):
        return []
    if not isinstance(receipt, dict):
        return ["delegate 审批缺 authorization receipt"]
    try:
        current = delegated_review_authorization(root, reviewed_by, stage)
    except EditorialAuthorizationError as exc:
        return [str(exc)]
    assert current is not None
    keys = ("kind", "source", "source_path", "authorization_sha256", "stage")
    errors = [f"delegate 审批 authorization {key} 已失效" for key in keys if receipt.get(key) != current.get(key)]
    if current.get("source") == "authorization_envelope":
        for key in ("source_sha256", "authorized_by", "scope", "delegate", "expires_at"):
            if receipt.get(key) != current.get(key):
                errors.append(f"delegate 审批 authorization {key} 已失效")
    return errors
