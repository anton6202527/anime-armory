#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold and check the author's creative intent dossier.

The reader contract says what the book promises to readers. The author intent
file records what the author will not compromise while making the book more
commercial, readable, or platform-safe.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from typing import Any


INTENT_KIND = "novel_author_intent"
CHECK_KIND = "novel_author_intent_check"
REQUIRED_FIELDS = (
    "core_theme",
    "target_emotional_aftertaste",
    "non_negotiables",
    "aesthetic_boundaries",
    "forbidden_tropes",
    "ethical_boundaries",
    "misreading_risks",
)


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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


def paths(root: str) -> tuple[str, str, str]:
    setting_dir = os.path.join(root, "设定")
    return (
        os.path.join(setting_dir, "author_intent.json"),
        os.path.join(setting_dir, "作者意图.md"),
        os.path.join(setting_dir, "author_intent_check.json"),
    )


def _split_values(values: list[str] | None, fallback: list[str]) -> list[str]:
    out: list[str] = []
    for value in values or []:
        for part in str(value).replace("，", ",").split(","):
            item = part.strip()
            if item and item not in out:
                out.append(item)
    return out or fallback


def build_intent(root: str, args: argparse.Namespace | None = None) -> dict[str, Any]:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    args = args or argparse.Namespace()
    return {
        "schema_version": 1,
        "kind": INTENT_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "title": getattr(args, "title", "") or meta.get("title") or os.path.basename(root),
        "core_theme": getattr(args, "theme", "") or "待填写：这本书真正想让读者带走的问题或情感。",
        "target_emotional_aftertaste": getattr(args, "aftertaste", "") or "待填写：读完最后一章后希望留下的余味。",
        "non_negotiables": _split_values(
            getattr(args, "non_negotiable", None),
            ["待填写：哪类核心设定、人物尊严、主题表达不可为爽点牺牲。"],
        ),
        "aesthetic_boundaries": _split_values(
            getattr(args, "aesthetic_boundary", None),
            ["待填写：语言密度、残酷程度、幽默尺度、情色/暴力/猎奇边界。"],
        ),
        "forbidden_tropes": _split_values(
            getattr(args, "forbidden_trope", None),
            ["待填写：本项目不采用或必须反套路处理的桥段。"],
        ),
        "ethical_boundaries": _split_values(
            getattr(args, "ethical_boundary", None),
            ["待填写：不可被旁白合理化的价值、伤害或专业风险。"],
        ),
        "misreading_risks": _split_values(
            getattr(args, "misreading_risk", None),
            ["待填写：目标读者可能误读、反感或弃读的点，以及预防方式。"],
        ),
        "comparison_titles": _split_values(getattr(args, "comparison_title", None), []),
        "revision_policy": {
            "market_feedback_can_change": "节奏、开篇信息顺序、钩子密度、部分桥段呈现方式。",
            "market_feedback_cannot_change": "core_theme / non_negotiables / ethical_boundaries，除非作者显式修订本文件。",
        },
    }


def render_markdown(intent: dict[str, Any]) -> str:
    lines = [
        "# 作者意图",
        "",
        f"- 生成日期：{intent.get('generated_at')}",
        f"- 书名：{intent.get('title')}",
        "",
        "## 核心主题",
        "",
        str(intent.get("core_theme") or ""),
        "",
        "## 目标余味",
        "",
        str(intent.get("target_emotional_aftertaste") or ""),
        "",
    ]
    sections = [
        ("不可妥协项", "non_negotiables"),
        ("审美边界", "aesthetic_boundaries"),
        ("禁用套路", "forbidden_tropes"),
        ("伦理边界", "ethical_boundaries"),
        ("误读风险", "misreading_risks"),
        ("对照作品", "comparison_titles"),
    ]
    for title, key in sections:
        lines.extend([f"## {title}", ""])
        values = intent.get(key) or []
        if values:
            lines.extend(f"- {item}" for item in values)
        else:
            lines.append("- 无")
        lines.append("")
    policy = intent.get("revision_policy") or {}
    lines.extend([
        "## 修订政策",
        "",
        f"- 可被市场反馈改变：{policy.get('market_feedback_can_change') or ''}",
        f"- 不可被市场反馈改变：{policy.get('market_feedback_cannot_change') or ''}",
    ])
    return "\n".join(lines).rstrip() + "\n"


def check_intent(root: str) -> dict[str, Any]:
    json_path, md_path, _check_path = paths(root)
    payload = load_json(json_path, {}) or {}
    findings: list[dict[str, str]] = []
    if not isinstance(payload, dict) or payload.get("kind") != INTENT_KIND:
        findings.append({
            "id": "AUTHOR-INTENT-MISSING",
            "severity": "blocking",
            "message": "缺少 设定/author_intent.json 或 kind 不正确。",
            "path": "设定/author_intent.json",
        })
    else:
        for field in REQUIRED_FIELDS:
            value = payload.get(field)
            missing = not value
            if isinstance(value, str):
                missing = not value.strip() or "待填写" in value
            elif isinstance(value, list):
                missing = not any(str(item).strip() and "待填写" not in str(item) for item in value)
            if missing:
                findings.append({
                    "id": f"AUTHOR-INTENT-{field.upper()}-MISSING",
                    "severity": "blocking" if field in {"core_theme", "non_negotiables"} else "warning",
                    "message": f"作者意图字段 {field} 未完成。",
                    "path": "设定/author_intent.json",
                })
    if not os.path.exists(md_path):
        findings.append({
            "id": "AUTHOR-INTENT-MD-MISSING",
            "severity": "warning",
            "message": "缺少给作者阅读的 设定/作者意图.md。",
            "path": "设定/作者意图.md",
        })
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "passed": not blockers,
        "findings": findings,
    }


def write_intent(root: str, intent: dict[str, Any]) -> tuple[str, str]:
    json_path, md_path, _check_path = paths(root)
    write_json(json_path, intent)
    write_text(md_path, render_markdown(intent))
    return json_path, md_path


def write_check(root: str, report: dict[str, Any]) -> str:
    _json_path, _md_path, check_path = paths(root)
    write_json(check_path, report)
    return check_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成/检查作者创作意图档案")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scaffold")
    sc.add_argument("project_root")
    sc.add_argument("--title", default="")
    sc.add_argument("--theme", default="")
    sc.add_argument("--aftertaste", default="")
    sc.add_argument("--non-negotiable", action="append", default=[])
    sc.add_argument("--aesthetic-boundary", action="append", default=[])
    sc.add_argument("--forbidden-trope", action="append", default=[])
    sc.add_argument("--ethical-boundary", action="append", default=[])
    sc.add_argument("--misreading-risk", action="append", default=[])
    sc.add_argument("--comparison-title", action="append", default=[])
    ck = sub.add_parser("check")
    ck.add_argument("project_root")
    ck.add_argument("--write", action="store_true")
    ck.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    if args.cmd == "scaffold":
        intent = build_intent(root, args)
        json_path, md_path = write_intent(root, intent)
        print(f"[ok] author intent JSON → {json_path}")
        print(f"[ok] author intent MD   → {md_path}")
        return 0
    report = check_intent(root)
    if args.write:
        print(f"[ok] author intent check → {write_check(root, report)}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(f"[summary] blocking={report['blocking']} warnings={report['warnings']}")
        for item in report["findings"]:
            print(f"- [{item['severity']}] {item['id']}: {item['message']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
