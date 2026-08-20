#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan, record, and check an authenticity read for a novel manuscript.

The tool is deliberately author-controlled.  It never decides whether a
portrayal is acceptable and never rewrites prose.  A reviewer records
contextual findings; the author records a decision for each finding.  The
review becomes a release blocker only when the project explicitly marks it as
required.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from typing import Any


HERE = os.path.dirname(os.path.abspath(__file__))
NOVEL_LIB = os.path.abspath(os.path.join(HERE, "..", "..", "_lib"))
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)

from authenticity_contract import (  # noqa: E402
    AUTHOR_DECISIONS,
    CHECK_KIND,
    CLOSED_DECISIONS,
    FINDING_CATEGORIES,
    FINDING_SEVERITIES,
    KIND,
    evaluate_authenticity_read,
)
from report_snapshot import snapshot_chapters  # noqa: E402


REL_JSON = os.path.join("修订", "authenticity_read.json")
REL_MD = os.path.join("修订", "authenticity_read.md")
REL_CHECK_JSON = os.path.join("修订", "authenticity_read_check.json")
REL_CHECK_MD = os.path.join("修订", "authenticity_read_check.md")

def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def paths(root: str) -> tuple[str, str, str, str]:
    return tuple(os.path.join(root, rel) for rel in (REL_JSON, REL_MD, REL_CHECK_JSON, REL_CHECK_MD))


def split_values(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        item = str(value or "").strip()
        if item and item not in out:
            out.append(item)
    return out


def scaffold(
    root: str,
    *,
    scopes: list[str],
    reader_id: str = "",
    fit_statement: str = "",
    author_context: str = "",
    required: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": KIND,
        "created_at": date.today().isoformat(),
        "updated_at": date.today().isoformat(),
        # Persist project-relative context only; the absolute workspace path is
        # an execution detail and must not leak into portable project artifacts.
        "project_root": ".",
        "required_for_release": bool(required),
        "status": "planned",
        "scope": split_values(scopes),
        "author_context": str(author_context or "").strip(),
        "reviewer": {
            "reviewer_id": str(reader_id or "").strip(),
            "fit_statement": str(fit_statement or "").strip(),
            "privacy_note": "只记录与本稿审读匹配度有关的最小信息；不要求真实姓名、证件或敏感身份细节。",
        },
        "findings": [],
        "source_snapshot": None,
        "completion": None,
        "author_authority": (
            "审读者提供语境与建议；作者可接受、调整、拒绝或追问。"
            "工具只检查流程闭环，不自动裁决人物或表达是否合格。"
        ),
    }


def next_finding_id(payload: dict[str, Any]) -> str:
    high = 0
    for finding in payload.get("findings") or []:
        match = re.fullmatch(r"AUTH-(\d+)", str(finding.get("id") or ""))
        if match:
            high = max(high, int(match.group(1)))
    return f"AUTH-{high + 1:03d}"


def add_finding(
    payload: dict[str, Any],
    *,
    category: str,
    severity: str,
    location: str,
    observation: str,
    suggestion: str = "",
) -> dict[str, Any]:
    if category not in FINDING_CATEGORIES:
        raise ValueError(f"unknown category: {category}")
    if severity not in FINDING_SEVERITIES:
        raise ValueError(f"unknown severity: {severity}")
    if not observation.strip():
        raise ValueError("observation 不能为空")
    finding = {
        "id": next_finding_id(payload),
        "category": category,
        "severity": severity,
        "location": location.strip(),
        "observation": observation.strip(),
        "suggestion": suggestion.strip(),
        "status": "open",
        "author_decision": "",
        "author_note": "",
        "decided_by": "",
        "decided_at": "",
        "resolved_at": "",
    }
    payload.setdefault("findings", []).append(finding)
    payload["status"] = "in_progress"
    payload["updated_at"] = date.today().isoformat()
    return finding


def resolve_finding(
    payload: dict[str, Any],
    finding_id: str,
    *,
    decision: str,
    author_note: str,
    decided_by: str = "author",
) -> dict[str, Any]:
    if decision not in AUTHOR_DECISIONS:
        raise ValueError(f"unknown decision: {decision}")
    if not author_note.strip():
        raise ValueError("作者裁决必须记录理由或处理说明")
    if not str(decided_by or "").strip():
        raise ValueError("作者裁决必须记录 decided_by")
    for finding in payload.get("findings") or []:
        if finding.get("id") == finding_id:
            finding["status"] = "questioned" if decision == "questioned" else "closed"
            finding["author_decision"] = decision
            finding["author_note"] = author_note.strip()
            finding["decided_by"] = str(decided_by).strip()
            finding["decided_at"] = date.today().isoformat()
            finding["resolved_at"] = date.today().isoformat() if decision in CLOSED_DECISIONS else ""
            payload["updated_at"] = date.today().isoformat()
            return finding
    raise ValueError(f"unknown finding id: {finding_id}")


def complete_read(
    root: str,
    payload: dict[str, Any],
    *,
    reviewer_id: str = "",
    fit_statement: str = "",
    summary: str,
) -> dict[str, Any]:
    reviewer = payload.setdefault("reviewer", {})
    if reviewer_id.strip():
        reviewer["reviewer_id"] = reviewer_id.strip()
    if fit_statement.strip():
        reviewer["fit_statement"] = fit_statement.strip()
    if not str(reviewer.get("reviewer_id") or "").strip():
        raise ValueError("完成审读前需记录匿名 reviewer_id")
    if not str(reviewer.get("fit_statement") or "").strip():
        raise ValueError("完成审读前需说明审读者与本次 scope 的匹配度")
    if not isinstance(payload.get("scope"), list) or not split_values(payload.get("scope")):
        raise ValueError("完成审读前需说明至少一个 scope")
    if not summary.strip():
        raise ValueError("完成审读前需写 summary")
    payload["status"] = "completed"
    # Use the review namespace so validate_snapshot also notices chapters added
    # after the read, rather than checking only files already in the snapshot.
    payload["source_snapshot"] = snapshot_chapters(root, mode="review:authenticity")
    payload["completion"] = {
        "completed_at": date.today().isoformat(),
        "summary": summary.strip(),
    }
    payload["updated_at"] = date.today().isoformat()
    return payload


_PAYLOAD_UNSET = object()


def check(root: str, payload: Any = _PAYLOAD_UNSET) -> dict[str, Any]:
    if payload is _PAYLOAD_UNSET:
        return evaluate_authenticity_read(root)
    return evaluate_authenticity_read(root, payload)


def render(payload: dict[str, Any]) -> str:
    reviewer = payload.get("reviewer") or {}
    lines = [
        "# 真实性 / 文化审读",
        "",
        f"- 状态：{payload.get('status')}",
        f"- 发布前必需：{payload.get('required_for_release', False)}",
        f"- 范围：{'；'.join(payload.get('scope') or []) or '待补'}",
        f"- 审读者 ID：{reviewer.get('reviewer_id') or '待补'}",
        f"- 匹配说明：{reviewer.get('fit_statement') or '待补'}",
        "",
        "> 审读者提供语境和建议，作者保留最终创作裁决。接受、调整、拒绝或追问都可以，但重大意见必须留下理由。",
        "",
        "## 作者给审读者的语境",
        "",
        str(payload.get("author_context") or "待补"),
        "",
        "## Findings",
        "",
    ]
    rows = payload.get("findings") or []
    if not rows:
        lines.append("- 暂无；审读者应同时记录有效表达和需要讨论的表达。")
    for item in rows:
        lines.extend([
            f"### {item.get('id')} · {item.get('category')} · {item.get('severity')}",
            f"- 位置：{item.get('location') or '全局'}",
            f"- 观察：{item.get('observation') or ''}",
            f"- 建议：{item.get('suggestion') or '无'}",
            f"- 作者裁决：{item.get('author_decision') or '待定'}",
            f"- 裁决人：{item.get('decided_by') or '待定'}",
            f"- 作者说明：{item.get('author_note') or '待定'}",
            "",
        ])
    completion = payload.get("completion") or {}
    lines.extend(["## 完成摘要", "", str(completion.get("summary") or "待完成")])
    return "\n".join(lines).rstrip() + "\n"


def render_check(report: dict[str, Any]) -> str:
    lines = [
        "# 真实性 / 文化审读检查",
        "",
        f"- applicable：{report.get('applicable')}",
        f"- required_for_release：{report.get('required_for_release')}",
        f"- blocking：{report.get('blocking')} / warnings：{report.get('warnings')}",
        f"- passed：{report.get('passed')}",
        "",
    ]
    for item in report.get("findings") or []:
        lines.append(f"- [{item.get('severity')}] {item.get('id')}: {item.get('message')}")
    if report.get("note"):
        lines.extend(["", f"> {report['note']}"])
    return "\n".join(lines).rstrip() + "\n"


def save(root: str, payload: dict[str, Any]) -> tuple[str, str]:
    json_path, md_path, _check_json, _check_md = paths(root)
    write_json(json_path, payload)
    write_text(md_path, render(payload))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="真实性/文化审读：作者裁决式咨询记录")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold")
    sc.add_argument("project_root")
    sc.add_argument("--scope", action="append", default=[])
    sc.add_argument("--reader-id", default="")
    sc.add_argument("--fit", default="")
    sc.add_argument("--author-context", default="")
    sc.add_argument("--required", action="store_true")

    add = sub.add_parser("add")
    add.add_argument("project_root")
    add.add_argument("--category", choices=sorted(FINDING_CATEGORIES), required=True)
    add.add_argument("--severity", choices=sorted(FINDING_SEVERITIES), default="consider")
    add.add_argument("--location", default="")
    add.add_argument("--observation", required=True)
    add.add_argument("--suggestion", default="")

    resolve = sub.add_parser("resolve")
    resolve.add_argument("project_root")
    resolve.add_argument("--finding", required=True)
    resolve.add_argument("--decision", choices=sorted(AUTHOR_DECISIONS), required=True)
    resolve.add_argument("--author-note", required=True)
    resolve.add_argument("--decided-by", required=True, help="作者/主编等最终裁决主体")

    complete = sub.add_parser("complete")
    complete.add_argument("project_root")
    complete.add_argument("--reader-id", default="")
    complete.add_argument("--fit", default="")
    complete.add_argument("--summary", required=True)

    ck = sub.add_parser("check")
    ck.add_argument("project_root")
    ck.add_argument("--write", action="store_true")
    ck.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    json_path, _md_path, check_json, check_md = paths(root)

    if args.cmd == "scaffold":
        payload = scaffold(
            root,
            scopes=args.scope,
            reader_id=args.reader_id,
            fit_statement=args.fit,
            author_context=args.author_context,
            required=args.required,
        )
        out_json, out_md = save(root, payload)
        print(f"[ok] authenticity read → {out_json}")
        print(f"[ok] human view        → {out_md}")
        return 0

    if args.cmd == "check":
        report = check(root)
        if args.write:
            write_json(check_json, report)
            write_text(check_md, render_check(report))
            print(f"[ok] authenticity check → {check_md}")
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif not args.write:
            print(f"[summary] blocking={report['blocking']} warnings={report['warnings']}")
        return 0 if report["passed"] else 1

    payload = load_json(json_path, None)
    if not isinstance(payload, dict) or payload.get("kind") != KIND:
        print("[err] 先运行 authenticity_read.py scaffold")
        return 2
    try:
        if args.cmd == "add":
            item = add_finding(
                payload,
                category=args.category,
                severity=args.severity,
                location=args.location,
                observation=args.observation,
                suggestion=args.suggestion,
            )
            print(f"[ok] finding added: {item['id']}")
        elif args.cmd == "resolve":
            item = resolve_finding(
                payload,
                args.finding,
                decision=args.decision,
                author_note=args.author_note,
                decided_by=args.decided_by,
            )
            print(f"[ok] finding resolved: {item['id']} decision={item['author_decision']}")
        elif args.cmd == "complete":
            complete_read(
                root,
                payload,
                reviewer_id=args.reader_id,
                fit_statement=args.fit,
                summary=args.summary,
            )
            print("[ok] authenticity read completed and bound to current chapters")
    except ValueError as exc:
        print(f"[err] {exc}")
        return 2
    save(root, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
