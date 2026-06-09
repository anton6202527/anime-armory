#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build scheduler-readable novel review reports.

Takes deterministic findings from mechanical_check.py and optional human/LLM
findings, then writes:
  - 审稿/review_report.json
  - 审稿/审稿报告.md

This closes the gap between "机检发现问题" and the QA gate contract consumed by
novel-craft/progress.py and export.py.
"""
import argparse
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.append(os.path.join(SKILLS_ROOT, "novel-craft", "scripts"))

from report_snapshot import snapshot_chapters
from waivers import make_waiver


SEVERITY_MAP = {
    "🔴": "blocking",
    "🟡": "suggestion",
    "🟢": "polish",
    "blocking": "blocking",
    "suggestion": "suggestion",
    "polish": "polish",
}

DIMENSION_MAP = {
    "格式": "format",
    "章号": "format",
    "标题": "outline",
    "字数": "wordcount",
    "原文照搬": "plagiarism",
}

RETURN_STAGE_BY_DIM = {
    "format": "draft",
    "outline": "outline",
    "wordcount": "draft",
    "plagiarism": "draft",
}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def read_meta(root):
    return load_json(os.path.join(root, "_meta.json"), {}) or {}


def rel(root, path):
    if not path:
        return None
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")


def owner_skill(meta):
    kind = meta.get("kind")
    if kind in {"create", "rewrite", "spinoff", "expand", "condense", "continue"}:
        return f"novel-{kind}"
    return "novel-review"


def affected_files_for(finding):
    chapter = finding.get("chapter")
    if isinstance(chapter, int) and chapter > 0:
        return [f"章节/第{chapter:02d}章.md"]
    dim = finding.get("dim") or finding.get("dimension")
    if dim in {"章号", "格式"}:
        return ["章节/"]
    return []


def missing_mechanical_waiver(root, mechanical_path, scope, source_snapshot):
    waiver = make_waiver(
        "missing_mechanical",
        reason="explicit --allow-missing-mechanical",
        affected_gate="mechanical_check",
        source="novel-review/scripts/build_review_report.py",
        details={
            "intended_mechanical_findings_path": rel(root, mechanical_path),
        },
        scope={
            "review_scope": scope,
            "source_aggregate_hash": (source_snapshot or {}).get("aggregate_hash") or "",
            "chapter_count": len((source_snapshot or {}).get("files") or []),
        },
    )
    waiver["risk"] = "格式、字数、章号、术语漂移、原文照搬等确定性机检未执行；本报告不是正常全量通过。"
    return waiver


def normalize_mechanical_finding(raw, idx, meta):
    severity = SEVERITY_MAP.get(raw.get("severity"), "suggestion")
    dimension = DIMENSION_MAP.get(raw.get("dim"), raw.get("dim") or "mechanical")
    stage = RETURN_STAGE_BY_DIM.get(dimension, "draft")
    skill = "novel-craft" if dimension in {"format", "outline", "wordcount"} else owner_skill(meta)
    if dimension == "plagiarism":
        skill = owner_skill(meta)
    chapter = raw.get("chapter")
    if chapter == 0:
        chapter = None
    return {
        "id": f"REV-MECH-{idx:03d}",
        "severity": severity,
        "dimension": dimension,
        "chapter": chapter,
        "location": "全局" if chapter is None else f"第{chapter}章",
        "evidence": raw.get("evidence", ""),
        "problem": raw.get("msg") or raw.get("problem") or "",
        "fix_hint": _fix_hint(dimension, raw),
        "recommended_skill": skill,
        "return_to_stage": stage,
        "affected_files": affected_files_for(raw),
        "blocking": severity == "blocking",
        "confidence": "high",
        "source": "mechanical_check",
    }


def _fix_hint(dimension, raw):
    if dimension == "format":
        return "修正章节文件命名、H1 标题、章号连续性或 meta 注释。"
    if dimension == "outline":
        return "同步正文标题与设定/章纲.md，或回章纲阶段确认新标题。"
    if dimension == "wordcount":
        return "按目标平台字数带宽增删内容，保留本章戏剧节拍和钩子。"
    if dimension == "plagiarism":
        return "重写雷同段，保留事件骨架但不要复刻原文表达。"
    return raw.get("fix_hint") or "按问题定位回源头阶段修订。"


def normalize_human_finding(raw, idx):
    severity = SEVERITY_MAP.get(raw.get("severity"), raw.get("severity") or "suggestion")
    finding = dict(raw)
    finding.setdefault("id", f"REV-HUMAN-{idx:03d}")
    finding["severity"] = severity
    finding.setdefault("dimension", raw.get("dimension") or "manual")
    finding.setdefault("chapter", raw.get("chapter"))
    finding.setdefault("location", "全局" if raw.get("chapter") in (None, 0) else f"第{raw.get('chapter')}章")
    finding.setdefault("evidence", "")
    finding.setdefault("problem", raw.get("problem") or raw.get("msg") or "")
    finding.setdefault("fix_hint", raw.get("fix_hint") or "按人工审稿建议修订。")
    finding.setdefault("recommended_skill", raw.get("recommended_skill") or "novel-review")
    finding.setdefault("return_to_stage", raw.get("return_to_stage") or "draft")
    finding.setdefault("affected_files", raw.get("affected_files") or affected_files_for(raw))
    finding.setdefault("blocking", severity == "blocking")
    finding.setdefault("confidence", raw.get("confidence") or "medium")
    finding.setdefault("source", "human_assessment")
    return finding


def load_human_findings(path):
    if not path:
        return []
    payload = load_json(path)
    if payload is None:
        raise FileNotFoundError(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("findings") or []
    raise ValueError("human assessment 必须是 list 或含 findings 的 object")


def build_next_actions(findings):
    actions = []
    seen = set()
    priority_for = {"blocking": "must", "suggestion": "should", "polish": "could"}
    for finding in findings:
        if finding["severity"] not in {"blocking", "suggestion"}:
            continue
        key = (finding["recommended_skill"], finding["return_to_stage"], finding["severity"])
        if key in seen:
            for action in actions:
                if (
                    action["recommended_skill"],
                    action["return_to_stage"],
                    "blocking" if action["priority"] == "must" else "suggestion",
                ) == key:
                    action["finding_ids"].append(finding["id"])
            continue
        seen.add(key)
        actions.append({
            "priority": priority_for[finding["severity"]],
            "action": finding["fix_hint"],
            "recommended_skill": finding["recommended_skill"],
            "return_to_stage": finding["return_to_stage"],
            "finding_ids": [finding["id"]],
        })
    return actions


def write_markdown(path, meta, report):
    lines = [
        f"# 审稿报告 — {meta.get('title') or meta.get('source_title') or '未定'}",
        "",
        "## 概览",
        "",
        f"- 阻断级：{report['summary']['blocking_count']}",
        f"- 建议级：{report['summary']['suggestion_count']}",
        f"- 润色级：{report['summary']['polish_count']}",
        f"- 结论：{report['summary']['verdict']}",
        f"- 显式豁免：{report['summary'].get('waiver_count', 0)}",
        "",
    ]
    if report.get("waivers"):
        lines.extend(["## 显式豁免", ""])
        for waiver in report["waivers"]:
            lines.append(
                f"- **{waiver['id']}** [{waiver['type']}] {waiver['reason']}；"
                f"影响 gate：{waiver['affected_gate']}；风险：{waiver['risk']}"
            )
        lines.append("")
    lines.extend(["## 问题清单", ""])
    if not report["findings"]:
        lines.append("- 未发现问题。")
    for finding in report["findings"]:
        lines.append(
            f"- **{finding['id']}** [{finding['severity']}] {finding['location']} · "
            f"{finding['dimension']}：{finding['problem']}"
        )
        if finding.get("evidence"):
            lines.append(f"  - 证据：{finding['evidence']}")
        lines.append(f"  - 修法：{finding['fix_hint']}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build_report(root, mechanical_path=None, human_path=None, scope="full", allow_missing_mechanical=False):
    meta = read_meta(root)
    if mechanical_path is None:
        mechanical_path = os.path.join(root, "审稿", "mechanical_findings.json")
    mechanical_exists = os.path.exists(mechanical_path)
    if not mechanical_exists and not allow_missing_mechanical:
        raise FileNotFoundError(
            f"缺少机检文件：{mechanical_path}；先运行 mechanical_check.py --json-out，"
            "或显式加 --allow-missing-mechanical。"
        )
    source_snapshot = snapshot_chapters(root, mode=f"review:{scope}")
    waivers = []
    if not mechanical_exists:
        waivers.append(missing_mechanical_waiver(root, mechanical_path, scope, source_snapshot))
    mechanical = load_json(mechanical_path, {}) if mechanical_exists else {}
    mechanical = mechanical or {}
    raw_mechanical = mechanical.get("findings") or []
    findings = [
        normalize_mechanical_finding(raw, idx + 1, meta)
        for idx, raw in enumerate(raw_mechanical)
    ]
    human = load_human_findings(human_path)
    findings.extend(normalize_human_finding(raw, idx + 1) for idx, raw in enumerate(human))
    order = {"blocking": 0, "suggestion": 1, "polish": 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f.get("chapter") or 0, f["id"]))
    summary = {
        "blocking_count": sum(1 for f in findings if f["severity"] == "blocking" or f.get("blocking")),
        "suggestion_count": sum(1 for f in findings if f["severity"] == "suggestion"),
        "polish_count": sum(1 for f in findings if f["severity"] == "polish"),
        "waiver_count": len(waivers),
        "verdict": "blocked" if any(f.get("blocking") for f in findings) else ("needs_revision" if findings else "pass"),
    }
    return {
        "schema_version": 1,
        "kind": "novel_review_report",
        "project_root": os.path.abspath(root),
        "generated_at": date.today().isoformat(),
        "scope": {"mode": scope},
        "source_snapshot": source_snapshot,
        "summary": summary,
        "mechanical_findings_path": rel(root, mechanical_path) if os.path.exists(mechanical_path) else None,
        "waivers": waivers,
        "findings": findings,
        "next_actions": build_next_actions(findings),
    }


def main():
    ap = argparse.ArgumentParser(description="把 novel 机检/人判结果汇总成 review_report.json")
    ap.add_argument("project_root")
    ap.add_argument("--mechanical", default=None, help="mechanical_check.py --json-out 产物；缺省 审稿/mechanical_findings.json")
    ap.add_argument("--human-assessment", default=None, help="人工/LLM 审稿 JSON；list 或含 findings 字段")
    ap.add_argument("--scope", default="full")
    ap.add_argument("--allow-missing-mechanical", action="store_true",
                    help="显式允许没有机检文件时生成报告；默认缺机检即失败")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    try:
        report = build_report(
            root,
            args.mechanical,
            args.human_assessment,
            scope=args.scope,
            allow_missing_mechanical=args.allow_missing_mechanical,
        )
    except Exception as exc:
        print(f"[err] 构建 review_report 失败：{exc}", file=sys.stderr)
        sys.exit(2)

    review_dir = os.path.join(root, "审稿")
    os.makedirs(review_dir, exist_ok=True)
    json_path = os.path.join(review_dir, "review_report.json")
    md_path = os.path.join(review_dir, "审稿报告.md")
    write_json(json_path, report)
    write_markdown(md_path, read_meta(root), report)
    print(f"[ok] review report JSON → {json_path}")
    print(f"[ok] review report MD   → {md_path}")
    print(f"     阻断：{report['summary']['blocking_count']} | 建议：{report['summary']['suggestion_count']} | 润色：{report['summary']['polish_count']}")


if __name__ == "__main__":
    main()
