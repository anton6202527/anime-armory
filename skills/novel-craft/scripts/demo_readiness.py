#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-batch demo readiness gate for novel projects.

This deterministic gate does not judge prose by itself. It verifies that the
semantic demo gate, commercial score, and literary/aesthetic anchors have been
recorded before a project moves from demo chapters into bulk drafting.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import date
from typing import Any


READINESS_KIND = "novel_demo_readiness"


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


def commercial_project(root: str, meta: dict[str, Any]) -> bool:
    settings = ""
    path = os.path.join(root, "_设置.md")
    if os.path.exists(path):
        settings = open(path, encoding="utf-8", errors="replace").read()
    text = " ".join([
        str(meta.get("purpose") or ""),
        str(meta.get("target_platform") or ""),
        settings,
    ])
    return any(key in text for key in ("商业连载", "红果", "番茄", "抖音", "漫剧", "短剧", "微短剧", "KDP", "出海", "平台"))


def add_issue(items: list[dict[str, str]], issue_id: str, severity: str, message: str, path: str = "") -> None:
    items.append({"id": issue_id, "severity": severity, "message": message, "path": path})


def build_readiness(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    demo_gate = load_json(os.path.join(root, "审稿", "demo_gate.json"), {}) or {}
    score = load_json(os.path.join(root, "评分", "score_report.json"), {}) or {}
    aesthetic = load_json(os.path.join(root, "设定", "aesthetic_bank.json"), {}) or {}
    chapters = sorted(glob.glob(os.path.join(root, "章节", "第*.md")))
    commercial = commercial_project(root, meta)
    issues: list[dict[str, str]] = []

    if demo_gate.get("status") != "passed":
        add_issue(issues, "DEMO-GATE-NOT-PASSED", "blocking", "审稿/demo_gate.json status 不是 passed。", "审稿/demo_gate.json")
    reader_contract = demo_gate.get("reader_contract") if isinstance(demo_gate.get("reader_contract"), dict) else {}
    style_anchor = demo_gate.get("style_anchor") if isinstance(demo_gate.get("style_anchor"), dict) else {}
    if not style_anchor.get("summary"):
        add_issue(issues, "DEMO-STYLE-ANCHOR-WEAK", "warning", "demo_gate 缺少 style_anchor.summary，后续写章文风锚弱。", "审稿/demo_gate.json")
    if not reader_contract:
        add_issue(issues, "DEMO-READER-CONTRACT-MISSING", "warning", "demo_gate 未同步 reader_contract。", "审稿/demo_gate.json")

    decision = (score.get("production_decision") or {}).get("decision") if isinstance(score, dict) else ""
    verdict = score.get("verdict") if isinstance(score, dict) else ""
    if commercial and not score:
        add_issue(issues, "DEMO-COMMERCIAL-SCORE-MISSING", "blocking", "商业/平台项目 Demo 后必须有 opening/full score_report。", "评分/score_report.json")
    elif decision == "kill" or verdict in {"弃稿重立", "kill"}:
        add_issue(issues, "DEMO-COMMERCIAL-SCORE-KILL", "blocking", f"score 结论为 {verdict or decision}，不应批量写。", "评分/score_report.json")
    elif decision in {"revise", "major_rewrite"} or verdict in {"大改", "小改"}:
        add_issue(issues, "DEMO-COMMERCIAL-SCORE-REVISE", "warning", f"score 结论为 {verdict or decision}，批量写前应确认开篇已修。", "评分/score_report.json")

    samples = aesthetic.get("samples") if isinstance(aesthetic, dict) else []
    literary_score = 0
    literary_score += 25 if reader_contract.get("theme") else 0
    literary_score += 20 if reader_contract.get("aesthetic_register") else 0
    literary_score += 20 if style_anchor.get("summary") else 0
    literary_score += 20 if isinstance(samples, list) and samples else 0
    literary_score += 15 if chapters else 0
    if literary_score < 60:
        add_issue(issues, "DEMO-LITERARY-ANCHOR-WEAK", "warning", f"文学/审美锚点分 {literary_score}/100；建议补 reader_contract.aesthetic_register 或 aesthetic_bank。", "设定/aesthetic_bank.json")

    blockers = [item for item in issues if item["severity"] == "blocking"]
    warnings = [item for item in issues if item["severity"] != "blocking"]
    return {
        "schema_version": 1,
        "kind": READINESS_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "commercial_project": commercial,
        "demo_chapter_count": len(chapters),
        "ready_for_batch": not blockers,
        "commercial_gate": {
            "score_present": bool(score),
            "decision": decision,
            "verdict": verdict,
            "status": "block" if any(item["id"].startswith("DEMO-COMMERCIAL") and item["severity"] == "blocking" for item in issues) else "pass",
        },
        "literary_gate": {
            "score": literary_score,
            "status": "pass" if literary_score >= 60 else "warning",
            "has_aesthetic_bank": isinstance(samples, list) and bool(samples),
            "has_style_anchor": bool(style_anchor.get("summary")),
            "has_reader_contract": bool(reader_contract),
        },
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "issues": issues,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Demo Readiness",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- commercial_project：{report.get('commercial_project')}",
        f"- ready_for_batch：{report.get('ready_for_batch')}",
        f"- commercial_gate：{report.get('commercial_gate')}",
        f"- literary_gate：{report.get('literary_gate')}",
        "",
        "## Issues",
        "",
    ]
    for item in report.get("issues") or []:
        lines.append(f"- [{item.get('severity')}] {item.get('id')}: {item.get('message')} {item.get('path') or ''}".rstrip())
    if not report.get("issues"):
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def write_readiness(root: str, report: dict[str, Any]) -> tuple[str, str]:
    json_path = os.path.join(root, "审稿", "demo_readiness.json")
    md_path = os.path.join(root, "审稿", "demo_readiness.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查 Demo 章批量写作前准备度")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    report = build_readiness(root)
    if args.write:
        json_path, md_path = write_readiness(root, report)
        print(f"[ok] demo readiness JSON → {json_path}")
        print(f"[ok] demo readiness MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0 if report.get("ready_for_batch") else 1


if __name__ == "__main__":
    raise SystemExit(main())
