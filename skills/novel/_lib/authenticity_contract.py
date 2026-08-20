#!/usr/bin/env python3
"""Single validation contract for an optional novel authenticity read.

The validator checks workflow evidence, never whether a portrayal is
creatively or morally "acceptable".  An authenticity read becomes a hard
gate only when its own valid record explicitly declares
``required_for_release=true``.  Otherwise incomplete or malformed evidence is
kept visible as a warning.
"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

from report_snapshot import validate_snapshot


KIND = "novel_authenticity_read"
CHECK_KIND = "novel_authenticity_read_check"
REL_JSON = os.path.join("修订", "authenticity_read.json")

FINDING_CATEGORIES = {
    "stereotype",
    "accuracy",
    "framing",
    "language",
    "agency",
    "harm",
    "context",
    "positive_representation",
}
FINDING_SEVERITIES = {"note", "consider", "major"}
AUTHOR_DECISIONS = {"accepted", "adapted", "declined", "questioned", "resolved"}
CLOSED_DECISIONS = AUTHOR_DECISIONS - {"questioned"}

_UNSET = object()


def _finding(severity: str, finding_id: str, message: str) -> dict[str, str]:
    return {"severity": severity, "id": finding_id, "message": message, "path": REL_JSON}


def _issue_severity(required: bool) -> str:
    return "blocking" if required else "warning"


def _nonempty_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def load_authenticity_record(root: str) -> tuple[Any, str | None, bool]:
    """Return ``(payload, parse_error, exists)`` without leaking JSON errors."""
    path = os.path.join(root, REL_JSON)
    if not os.path.exists(path):
        return None, None, False
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None, True
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc), True


def evaluate_authenticity_read(
    root: str,
    payload: Any = _UNSET,
    *,
    parse_error: str | None = None,
) -> dict[str, Any]:
    """Evaluate scope, reviewer fit, version binding, and author decisions.

    The result is shared by the CLI, edit plan, author workflow, pipeline, and
    release manifest so those consumers cannot silently disagree.
    """
    exists = True
    if payload is _UNSET:
        payload, parse_error, exists = load_authenticity_record(root)
    if not exists:
        return {
            "schema_version": 1,
            "kind": CHECK_KIND,
            "generated_at": date.today().isoformat(),
            "project_root": ".",
            "applicable": False,
            "required_for_release": False,
            "blocking": 0,
            "warnings": 0,
            "passed": True,
            "findings": [],
            "note": "项目未启用真实性/文化审读；这是可选专业流程，不自动推断作者身份或题材风险。",
        }

    findings: list[dict[str, str]] = []
    if parse_error:
        findings.append(_finding(
            "warning",
            "AUTH-SCHEMA",
            f"authenticity_read.json 无法解析：{parse_error}；无法从损坏文件推断 required，默认不发明发布门禁。",
        ))
        required = False
    elif not isinstance(payload, dict) or payload.get("kind") != KIND:
        required = bool(payload.get("required_for_release")) if isinstance(payload, dict) else False
        findings.append(_finding(
            _issue_severity(required),
            "AUTH-SCHEMA",
            "authenticity_read.json 缺失或 kind 不正确。",
        ))
    else:
        required = bool(payload.get("required_for_release"))
        issue_severity = _issue_severity(required)
        if payload.get("schema_version") != 1:
            findings.append(_finding(
                issue_severity,
                "AUTH-SCHEMA-VERSION",
                "authenticity_read.json 必须声明 schema_version=1。",
            ))
        scopes = _nonempty_strings(payload.get("scope"))
        if not scopes:
            findings.append(_finding(
                issue_severity,
                "AUTH-SCOPE-MISSING",
                "尚未说明本次审读覆盖的群体、经验或场景范围。",
            ))

        reviewer = payload.get("reviewer") if isinstance(payload.get("reviewer"), dict) else {}
        if not str(reviewer.get("reviewer_id") or "").strip():
            findings.append(_finding(
                issue_severity,
                "AUTH-REVIEWER-ID-MISSING",
                "尚未记录匿名 reviewer_id；无需真实姓名，但要有可追踪的审读者代号。",
            ))
        if not str(reviewer.get("fit_statement") or "").strip():
            findings.append(_finding(
                issue_severity,
                "AUTH-REVIEWER-FIT-MISSING",
                "尚未说明审读者与本次 scope 的匹配度。",
            ))

        if payload.get("status") != "completed":
            findings.append(_finding(
                issue_severity,
                "AUTH-NOT-COMPLETED",
                "真实性/文化审读已登记但尚未完成。" if required else "真实性/文化审读尚未完成；不阻断普通发布。",
            ))
        else:
            fresh, reason = validate_snapshot(root, payload.get("source_snapshot"))
            if not fresh:
                findings.append(_finding(
                    issue_severity,
                    "AUTH-SNAPSHOT-STALE",
                    f"审读报告未绑定当前正文：{reason}",
                ))

        rows = payload.get("findings")
        if not isinstance(rows, list):
            findings.append(_finding(issue_severity, "AUTH-FINDINGS-SCHEMA", "findings 必须是数组。"))
            rows = []
        for index, item in enumerate(rows, 1):
            item_id = f"AUTH finding #{index}"
            if not isinstance(item, dict):
                findings.append(_finding(issue_severity, "AUTH-FINDING-SCHEMA", f"{item_id} 不是 object。"))
                continue
            item_id = str(item.get("id") or item_id)
            category = str(item.get("category") or "")
            severity = str(item.get("severity") or "")
            if category not in FINDING_CATEGORIES or severity not in FINDING_SEVERITIES:
                findings.append(_finding(
                    issue_severity,
                    "AUTH-FINDING-SCHEMA",
                    f"{item_id} 的 category/severity 不符合契约。",
                ))
                continue
            if severity != "major":
                continue
            if item.get("status") != "closed":
                findings.append(_finding(
                    issue_severity,
                    "AUTH-MAJOR-OPEN",
                    f"{item_id} 尚待作者裁决；可接受、调整、拒绝或追问，但 required 流程须在追问解决后再关闭。",
                ))
                continue
            decision = str(item.get("author_decision") or "").strip()
            note = str(item.get("author_note") or "").strip()
            decided_by = str(item.get("decided_by") or "").strip()
            missing = []
            if decision not in CLOSED_DECISIONS:
                missing.append("有效 author_decision")
            if not note:
                missing.append("author_note")
            if not decided_by:
                missing.append("decided_by")
            if missing:
                findings.append(_finding(
                    issue_severity,
                    "AUTH-MAJOR-DECISION-INCOMPLETE",
                    f"{item_id} 虽标为 closed，但缺 {'、'.join(missing)}；不得把手改状态当成作者裁决。",
                ))

    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": ".",
        "applicable": True,
        "required_for_release": required,
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "passed": not blockers,
        "findings": findings,
        "note": "流程通过只证明审读范围、版本和作者裁决有账，不证明任何群体存在唯一正确表达。",
    }
