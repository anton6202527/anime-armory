#!/usr/bin/env python3
"""Explicit, project-local authority for delegated current-pixel review.

This permission lets an execution agent that actually inspects the current
contact sheet advance reversible internal production.  It never authorizes a
named final acceptance, public release, rights decision or budget expansion.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


POLICY = "用户授权制作代理实际查看当前像素"
SCHEMA = "comic-visual-review-authorization/v1"
RELATIVE_PATH = Path("生产数据") / "authorizations" / "visual_review.json"
STAGES = {"panel_pixels", "identity_pixels", "platform_preview"}


class VisualAuthorizationError(ValueError):
    pass


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def authorization_payload_sha256(payload: dict[str, Any]) -> str:
    return _sha({key: value for key, value in payload.items() if key != "authorization_sha256"})


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def project_policy(root: Path) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return ""
    pattern = re.compile(r"^\s*[-*]\s*(?:\*\*)?视觉审阅策略(?:\*\*)?\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return re.split(r"\s+#", match.group(1), maxsplit=1)[0].strip()
    return ""


def _setting(stage: str) -> dict[str, Any]:
    material = {"source": "project_setting", "policy": POLICY, "scope": sorted(STAGES)}
    return {
        "kind": "comic_visual_review_authorization", **material,
        "source_path": "_设置.md", "authorization_sha256": _sha(material), "stage": stage,
    }


def _envelope(root: Path, reviewer_id: str, stage: str) -> dict[str, Any]:
    path = root / RELATIVE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VisualAuthorizationError(f"missing/unreadable {RELATIVE_PATH.as_posix()}") from exc
    errors = []
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
        payload = payload if isinstance(payload, dict) else {}
    if payload.get("status") != "authorized":
        errors.append("status must be authorized")
    scope = {str(item) for item in payload.get("scope") or []}
    if not ({stage, "visual_review", "*"} & scope):
        errors.append(f"scope does not authorize {stage}")
    delegate = str(payload.get("delegate") or "")
    if delegate not in {reviewer_id, "*"}:
        errors.append(f"delegate does not authorize {reviewer_id}")
    authorized_by = str(payload.get("authorized_by") or "").strip()
    if not authorized_by or authorized_by.startswith("delegate:"):
        errors.append("authorized_by must be a named non-delegate")
    if not str(payload.get("source_quote") or "").strip():
        errors.append("source_quote is required")
    try:
        _timestamp(str(payload.get("issued_at") or ""))
    except ValueError:
        errors.append("issued_at is invalid")
    expires = str(payload.get("expires_at") or "").strip()
    if expires:
        try:
            if _timestamp(expires) <= datetime.now(timezone.utc):
                errors.append("authorization expired")
        except ValueError:
            errors.append("expires_at is invalid")
    expected = authorization_payload_sha256(payload)
    if payload.get("authorization_sha256") != expected:
        errors.append("authorization_sha256 mismatch")
    if errors:
        raise VisualAuthorizationError("; ".join(errors))
    return {
        "kind": "comic_visual_review_authorization", "source": "authorization_envelope",
        "source_path": RELATIVE_PATH.as_posix(), "source_sha256": file_sha(path),
        "authorization_sha256": expected, "authorized_by": authorized_by,
        "delegate": delegate, "scope": sorted(scope), "stage": stage, "expires_at": expires,
    }


def delegated_visual_authorization(root: Path, reviewer: str, stage: str) -> dict[str, Any] | None:
    actor = str(reviewer or "").strip()
    if not actor.startswith("delegate:"):
        return None
    reviewer_id = actor.removeprefix("delegate:").strip()
    if not reviewer_id:
        raise VisualAuthorizationError("delegate id is required")
    if stage not in STAGES:
        raise VisualAuthorizationError(f"unknown visual review stage: {stage}")
    return _setting(stage) if project_policy(root) == POLICY else _envelope(root, reviewer_id, stage)


def authorization_errors(root: Path, reviewer: str, stage: str, receipt: Any) -> list[str]:
    if not str(reviewer or "").startswith("delegate:"):
        return []
    if not isinstance(receipt, dict):
        return ["delegated visual review lacks authorization receipt"]
    try:
        current = delegated_visual_authorization(root, reviewer, stage)
    except VisualAuthorizationError as exc:
        return [str(exc)]
    assert current is not None
    keys = {"kind", "source", "source_path", "authorization_sha256", "stage"}
    if current.get("source") == "authorization_envelope":
        keys |= {"source_sha256", "authorized_by", "delegate", "scope", "expires_at"}
    return [f"visual authorization {key} is stale" for key in sorted(keys) if receipt.get(key) != current.get(key)]
