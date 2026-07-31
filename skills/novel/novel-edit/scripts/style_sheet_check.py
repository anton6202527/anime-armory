#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic style-sheet readiness check for novel editing."""
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import date
from typing import Any


CHECK_KIND = "novel_style_sheet_check"
REQUIRED_HINTS = ("术语", "称谓", "格式", "时间", "章节")


def read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def issue(issue_id: str, severity: str, message: str, *, path: str = "") -> dict[str, str]:
    return {"id": issue_id, "severity": severity, "message": message, "path": path}


def build_check(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    relpath = "修订/style_sheet.md"
    path = os.path.join(root, relpath)
    text = read_text(path)
    findings: list[dict[str, str]] = []
    if not text.strip():
        findings.append(issue("STYLE-SHEET-MISSING", "blocking", "缺少 style_sheet.md；copyedit/proofread 前必须有统一表。", path=relpath))
    else:
        for hint in REQUIRED_HINTS:
            if hint not in text:
                findings.append(issue("STYLE-SHEET-SECTION-WEAK", "warning", f"style sheet 未明显覆盖：{hint}", path=relpath))
        todo_count = sum(text.count(token) for token in ("待补", "TODO", "TBD", "未填写"))
        if todo_count:
            findings.append(issue("STYLE-SHEET-TODO", "warning", f"style sheet 仍有 {todo_count} 个待补标记。", path=relpath))
    chapter_count = len(glob.glob(os.path.join(root, "章节", "第*.md")))
    if chapter_count and text and "章节" not in text:
        findings.append(issue("STYLE-SHEET-CHAPTER-COVERAGE", "warning", f"项目已有 {chapter_count} 章，但 style sheet 未记录章节/标题口径。", path=relpath))
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "style_sheet": {"path": relpath, "exists": os.path.exists(path)},
        "chapter_count": chapter_count,
        "blocking": sum(1 for item in findings if item["severity"] == "blocking"),
        "warnings": sum(1 for item in findings if item["severity"] != "blocking"),
        "findings": findings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Style Sheet Check",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- 章节数：{report.get('chapter_count', 0)}",
        f"- 阻断：{report.get('blocking', 0)}",
        f"- 警告：{report.get('warnings', 0)}",
        "",
        "## Findings",
        "",
    ]
    for item in report.get("findings") or []:
        lines.append(f"- [{item.get('severity')}] {item.get('id')}: {item.get('message')} {item.get('path') or ''}".rstrip())
    if not report.get("findings"):
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查 novel style sheet 终校准备度")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    report = build_check(root)
    if args.write:
        write_json(os.path.join(root, "修订", "style_sheet_check.json"), report)
        write_text(os.path.join(root, "修订", "style_sheet_check.md"), render_markdown(report))
        print(f"[ok] style sheet check: {os.path.join(root, '修订', 'style_sheet_check.md')}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 1 if report.get("blocking") else 0


if __name__ == "__main__":
    raise SystemExit(main())
