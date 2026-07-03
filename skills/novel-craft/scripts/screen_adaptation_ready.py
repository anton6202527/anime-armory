#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Screen-adaptation readiness gate for finished novel text.

This script stays inside the novel line. It does not create a visual-production
contract. It checks whether the finished text and evidence files are clean
enough for a user-selected downstream adaptation workflow.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import date
from typing import Any


_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_LIB = os.path.join(_SKILLS, "novel", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from novel_contract import normalize_rights_status  # noqa: E402
from project_io import load_project_settings  # noqa: E402


SHORT_DRAMA_KEYS = ("红果", "抖音", "漫剧", "短剧", "微短剧")
CORE_SETTING_CANDIDATES = {
    "characters": ("设定/角色卡.md", "设定/人物.md"),
    "world": ("设定/世界观.md", "设定/设定圣经.md"),
    "outline": ("设定/章纲.md",),
    "reader_contract": ("设定/读者契约.md",),
}


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def nonempty(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0


def add(checks: list[dict[str, Any]], check_id: str, status: str, message: str,
        *, path: str = "", next_action: str = "") -> None:
    checks.append({
        "id": check_id,
        "status": status,
        "message": message,
        "path": path,
        "next_action": next_action,
    })


def has_short_drama_target(meta: dict[str, Any], settings: dict[str, Any]) -> bool:
    blob = " ".join(str(x or "") for x in (
        meta.get("target_platform"), meta.get("purpose"), meta.get("draft_mode"),
        settings.get("目标平台"), settings.get("小说用途"), settings.get("目标用途"),
    ))
    return any(key in blob for key in SHORT_DRAMA_KEYS)


def exported_or_chapter_files(root: str) -> list[str]:
    files = []
    files.extend(glob.glob(os.path.join(root, "导出", "*.txt")))
    files.extend(glob.glob(os.path.join(root, "导出", "*.docx")))
    files.extend(glob.glob(os.path.join(root, "章节", "第*.md")))
    return sorted(set(files))


def review_is_clean(payload: Any) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "缺少或无法读取 review_report.json"
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    blocking_count = int(summary.get("blocking_count") or 0)
    blocking_findings = [
        item for item in payload.get("findings") or []
        if isinstance(item, dict) and (item.get("blocking") is True or item.get("severity") in {"blocking", "阻断级"})
    ]
    if blocking_count or blocking_findings:
        return False, f"review 仍有阻断项：summary={blocking_count}, findings={len(blocking_findings)}"
    return True, "review 无阻断项"


def score_is_usable(payload: Any, *, require_adaptation: bool) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "缺少或无法读取 score_report.json"
    verdict = str(payload.get("verdict") or "")
    if verdict in {"大改", "弃稿重立"}:
        return False, f"评分结论为 {verdict}，不适合直接进入转制"
    adaptation = payload.get("adaptation_check")
    if require_adaptation and not isinstance(adaptation, dict):
        return False, "目标命中短剧/漫剧，但缺少 adaptation_check"
    if isinstance(adaptation, dict) and adaptation.get("low_potential"):
        return False, "短剧/漫剧改编潜力偏低，先用 novel-condense 或 rewrite 调整结构"
    return True, f"评分结论可用：{verdict or '未写 verdict'}"


def collect(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    settings = load_project_settings(root)
    checks: list[dict[str, Any]] = []

    files = exported_or_chapter_files(root)
    if files:
        add(checks, "TEXT-FILES", "pass", f"发现可选成品文本/章节文件 {len(files)} 个",
            path=", ".join(rel(root, p) for p in files[:6]))
    else:
        add(checks, "TEXT-FILES", "block", "缺少 导出/*.txt|*.docx 或 章节/第*.md",
            next_action="先用 novel-craft/scripts/export.py 导出，或确认章节定稿已落 章节/。")

    status = normalize_rights_status(meta.get("rights_status"))
    if status in {"original", "user-owned", "user-declared", "public-domain"}:
        add(checks, "RIGHTS", "pass", f"权利状态已声明：{status}")
    else:
        add(checks, "RIGHTS", "block", f"权利状态不可用：{status}",
            next_action="补 _meta.json/source_manifest.json 的 rights_status、rights_basis 与发行地区。")
    if meta.get("requires_user_rights") and not (meta.get("rights_declared") or meta.get("rights_declared_at")):
        add(checks, "RIGHTS-DECLARATION", "block", "来源要求用户授权声明，但缺 rights_declared/rights_declared_at",
            next_action="补授权留痕，或换公版/自有文本。")

    for key, candidates in CORE_SETTING_CANDIDATES.items():
        hit = next((os.path.join(root, item) for item in candidates if nonempty(os.path.join(root, item))), "")
        if hit:
            add(checks, f"SETTING-{key.upper()}", "pass", f"已找到 {rel(root, hit)}", path=rel(root, hit))
        else:
            add(checks, f"SETTING-{key.upper()}", "warn", f"缺少 {key} 核心设定文件",
                next_action="补角色、世界观、章纲、读者契约，避免视觉改编时临场发明。")

    ai_usage = load_json(os.path.join(root, "合规", "ai_usage.json"))
    if isinstance(ai_usage, dict):
        add(checks, "AI-USAGE", "pass", "AI 使用披露已记录", path="合规/ai_usage.json")
    else:
        add(checks, "AI-USAGE", "block", "缺少 合规/ai_usage.json",
            next_action="跑 novel-craft/scripts/ai_usage.py，记录文本主创模式、人工贡献和复核步骤。")

    review_ok, review_msg = review_is_clean(load_json(os.path.join(root, "审稿", "review_report.json")))
    add(checks, "REVIEW", "pass" if review_ok else "block", review_msg,
        path="审稿/review_report.json",
        next_action="" if review_ok else "跑 novel-review/build_review_report.py 并清掉阻断项。")

    require_adaptation = has_short_drama_target(meta, settings)
    score_ok, score_msg = score_is_usable(load_json(os.path.join(root, "评分", "score_report.json")),
                                          require_adaptation=require_adaptation)
    add(checks, "SCORE", "pass" if score_ok else "block", score_msg,
        path="评分/score_report.json",
        next_action="" if score_ok else "补 novel-score；短剧/漫剧目标必须含 adaptation_check。")

    if require_adaptation:
        baselines = glob.glob(os.path.join(root, "评分", "market_baseline_*.json"))
        if baselines:
            add(checks, "MARKET-BASELINE", "pass", f"已找到市场基准 {rel(root, sorted(baselines)[-1])}")
        else:
            add(checks, "MARKET-BASELINE", "warn", "短剧/漫剧目标缺少 market_baseline",
                next_action="跑 collect_market_baseline.py，并补红果/抖音结构化证据。")

    briefs = glob.glob(os.path.join(root, "导出", "宣发", "*video_brief.md"))
    if briefs:
        add(checks, "VIDEO-BRIEF", "pass", f"已有宣发视频 brief {len(briefs)} 个，可辅助选 pilot 高光段")
    else:
        add(checks, "VIDEO-BRIEF", "warn", "缺少高光视频 brief",
            next_action="可跑 novel-promote 生成高光片段/短视频 brief，用来选择首个 pilot。")

    blocks = sum(1 for item in checks if item["status"] == "block")
    warns = sum(1 for item in checks if item["status"] == "warn")
    verdict = "block" if blocks else ("review" if warns else "ready")
    next_actions = [item for item in checks if item["status"] != "pass"]
    return {
        "schema_version": 1,
        "kind": "novel_screen_adaptation_readiness",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": meta.get("title") or meta.get("source_title") or os.path.basename(root),
        "target_is_short_drama": require_adaptation,
        "verdict": verdict,
        "counts": {"block": blocks, "warn": warns, "pass": sum(1 for item in checks if item["status"] == "pass")},
        "candidate_text_files": [rel(root, p) for p in files],
        "checks": checks,
        "next_actions": next_actions,
        "pilot_advice": [
            "先选 1 集或 3-5 个高风险镜头做 pilot，不要整书直接批量转制。",
            "视觉生产阶段应重新建立角色、场景、道具、镜头和合规产物的独立台账。",
            "参考图、首帧、首尾帧和成片 provenance 应在视觉生产线中重新落档。",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 转制就绪检查",
        "",
        f"- 作品：{report['title']}",
        f"- 判定：{report['verdict']}",
        f"- 阻断/警告/通过：{report['counts']['block']} / {report['counts']['warn']} / {report['counts']['pass']}",
        "",
        "| status | id | message | next |",
        "|---|---|---|---|",
    ]
    for item in report["checks"]:
        lines.append(f"| {item['status']} | {item['id']} | {item['message']} | {item.get('next_action') or ''} |")
    lines.extend(["", "## Pilot 建议", ""])
    for item in report.get("pilot_advice") or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "导出")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "screen_adaptation_readiness.json")
    md_path = os.path.join(out_dir, "转制就绪检查.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="小说成品转制就绪检查")
    parser.add_argument("project_root")
    parser.add_argument("--json", action="store_true", help="打印 JSON")
    parser.add_argument("--no-write", action="store_true", help="只检查不写 导出/ 报告")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = collect(root)
    if not args.no_write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] readiness JSON → {json_path}")
        print(f"[ok] readiness MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[summary] verdict={report['verdict']} block={report['counts']['block']} warn={report['counts']['warn']}")
    return 1 if report["verdict"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
