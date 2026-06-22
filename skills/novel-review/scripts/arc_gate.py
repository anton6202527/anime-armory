#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arc-level gate for long-form novel consistency.

Per-chapter checks catch local mistakes. This gate reads a small chapter window
and verifies that the whole arc still pays down the reader contract instead of
accumulating events with no promise progress.
"""
import argparse
import json
import os
import re
import sys
from datetime import date


def _read_text(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value).strip()
    return [s] if s else []


def _parse_arc(value):
    match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", str(value))
    if not match:
        raise ValueError("--arc 格式应为 1-5")
    start, end = int(match.group(1)), int(match.group(2))
    if end < start:
        raise ValueError("--arc 结束章不能小于开始章")
    return start, end


def _chapter_file(root, chapter):
    chdir = os.path.join(root, "章节")
    if not os.path.isdir(chdir):
        return ""
    pat = re.compile(rf"第\s*0*{chapter}\s*章")
    for name in sorted(os.listdir(chdir)):
        if name.endswith(".md") and pat.search(name):
            return os.path.join(chdir, name)
    fallback = os.path.join(chdir, f"第{chapter:02d}章.md")
    return fallback if os.path.exists(fallback) else ""


def _delta_path(root, chapter):
    return os.path.join(root, "审稿", f"state_delta_第{chapter:02d}章.json")


def _arc_plan_path(root, start, end):
    return os.path.join(root, "审稿", f"arc_plan_第{start:02d}-{end:02d}章.json")


def _contract_banned(root):
    gate = _load_json(os.path.join(root, "审稿", "demo_gate.json"), {}) or {}
    reader_contract = gate.get("reader_contract") if isinstance(gate.get("reader_contract"), dict) else {}
    out = []
    out.extend(_as_list(gate.get("banned_drift")))
    out.extend(_as_list(reader_contract.get("banned_drift")))
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def analyze(root, start, end):
    root = os.path.abspath(root)
    blocks = []
    warnings = []
    chapter_reports = []
    progress_streak = []
    any_progress = False
    any_theme = False
    any_threads_resolved = False
    banned_items = _contract_banned(root)

    for chapter in range(start, end + 1):
        chapter_path = _chapter_file(root, chapter)
        delta_path = _delta_path(root, chapter)
        delta = {}
        chapter_warnings = []
        if not chapter_path:
            blocks.append({
                "severity": "阻断级",
                "type": "chapter_missing",
                "chapter": chapter,
                "message": f"缺失章节正文：第{chapter:02d}章",
            })
            text = ""
        else:
            text = _read_text(chapter_path)
        if not os.path.exists(delta_path):
            blocks.append({
                "severity": "阻断级",
                "type": "state_delta_missing",
                "chapter": chapter,
                "message": f"缺失状态增量：state_delta_第{chapter:02d}章.json",
            })
        else:
            try:
                delta = _load_json(delta_path, {}) or {}
            except json.JSONDecodeError as exc:
                blocks.append({
                    "severity": "阻断级",
                    "type": "state_delta_invalid_json",
                    "chapter": chapter,
                    "message": f"state_delta_第{chapter:02d}章.json 不合法：{exc}",
                })
                delta = {}
        progress = _as_list(delta.get("reader_contract_progress"))
        theme_alignment = str(delta.get("theme_alignment") or "").strip()
        if progress:
            any_progress = True
            progress_streak = []
        else:
            progress_streak.append(chapter)
            chapter_warnings.append("missing_reader_contract_progress")
            if len(progress_streak) >= 3:
                blocks.append({
                    "severity": "阻断级",
                    "type": "reader_contract_stall",
                    "chapter": chapter,
                    "message": f"连续 {len(progress_streak)} 章缺少 reader_contract_progress：第{progress_streak[0]:02d}-{progress_streak[-1]:02d}章。",
                })
        if theme_alignment:
            any_theme = True
        else:
            chapter_warnings.append("missing_theme_alignment")
        if _as_list(delta.get("threads_resolved")):
            any_threads_resolved = True
        for banned in banned_items:
            if banned and (banned in text or banned in json.dumps(delta, ensure_ascii=False)):
                warnings.append({
                    "severity": "建议级",
                    "type": "banned_drift_seen",
                    "chapter": chapter,
                    "message": f"第{chapter:02d}章出现禁偏项「{banned}」精确短语；请人工确认是否跑偏。",
                })
                break
        chapter_reports.append({
            "chapter": chapter,
            "chapter_file": chapter_path,
            "state_delta": delta_path,
            "has_reader_contract_progress": bool(progress),
            "has_theme_alignment": bool(theme_alignment),
            "resolved_threads": len(_as_list(delta.get("threads_resolved"))),
            "warnings": chapter_warnings,
        })

    if not any_progress:
        blocks.append({
            "severity": "阻断级",
            "type": "arc_without_reader_contract_progress",
            "message": f"第{start:02d}-{end:02d}章整段没有任何 reader_contract_progress。",
        })
    if not any_theme:
        blocks.append({
            "severity": "阻断级",
            "type": "arc_without_theme_alignment",
            "message": f"第{start:02d}-{end:02d}章整段没有任何 theme_alignment。",
        })
    if end - start + 1 >= 5 and not any_threads_resolved:
        warnings.append({
            "severity": "建议级",
            "type": "no_thread_resolved_in_arc",
            "message": "本弧段 5 章以上但没有任何 threads_resolved；请确认钩子/伏笔没有只种不收。",
        })

    plan = _load_json(_arc_plan_path(root, start, end), None)
    if plan:
        expected = list(range(start, end + 1))
        got = plan.get("chapters") or []
        if got != expected:
            warnings.append({
                "severity": "建议级",
                "type": "arc_plan_range_mismatch",
                "message": f"已存在 arc_plan，但 chapters={got!r} 与当前检查范围 {expected!r} 不一致。",
            })
    else:
        warnings.append({
            "severity": "建议级",
            "type": "arc_plan_missing",
            "message": "缺少弧段任务包/计划；长篇建议先跑 novel-craft/scripts/arc_packets.py 生成弧段目标。",
        })

    if not os.path.exists(os.path.join(root, "审稿", "state_ledger.json")):
        warnings.append({
            "severity": "建议级",
            "type": "state_ledger_missing",
            "message": "缺少 state_ledger.json；弧段 gate 只能看 state_delta，无法做更完整的跨章状态压力测试。",
        })

    return {
        "schema_version": 1,
        "kind": "novel_arc_gate",
        "checked_at": date.today().isoformat(),
        "arc": f"{start}-{end}",
        "chapters": chapter_reports,
        "status": "blocked" if blocks else ("warnings" if warnings else "clean"),
        "blocking": len(blocks),
        "warnings": len(warnings),
        "findings": blocks + warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="长篇弧段 gate：检查一段章节是否仍推进读者契约与题旨")
    parser.add_argument("root")
    parser.add_argument("--arc", required=True, help="章节范围，如 1-5")
    parser.add_argument("--json-out", help="输出 JSON 路径；默认写入 审稿/arc_gate_第AA-BB章.json")
    parser.add_argument("--advisory", action="store_true", help="只报告，不用非零退出阻断流程")
    args = parser.parse_args()

    try:
        start, end = _parse_arc(args.arc)
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        sys.exit(2)

    report = analyze(args.root, start, end)
    out_path = args.json_out or os.path.join(
        os.path.abspath(args.root), "审稿", f"arc_gate_第{start:02d}-{end:02d}章.json"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if report["blocking"]:
        print(f"❌ 第{start:02d}-{end:02d}章弧段 gate 阻断 {report['blocking']} 项 → {out_path}")
        for item in report["findings"]:
            if item.get("severity") == "阻断级":
                print(f"  [阻断级] {item['type']}: {item['message']}")
        if not args.advisory:
            sys.exit(1)
    elif report["warnings"]:
        print(f"⚠️ 第{start:02d}-{end:02d}章弧段 gate 有建议 {report['warnings']} 项 → {out_path}")
    else:
        print(f"✅ 第{start:02d}-{end:02d}章弧段 gate 通过 → {out_path}")


if __name__ == "__main__":
    main()
