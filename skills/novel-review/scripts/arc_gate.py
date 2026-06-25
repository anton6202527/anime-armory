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


def _after_colon(text):
    parts = re.split(r"[:：]", text, maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def _extract_core_contract_questions(contract_text):
    dramatic_question = ""
    must_answer = []
    for line in contract_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if "核心戏剧问题" in stripped or "dramatic_question" in stripped.lower():
            dramatic_question = _after_colon(stripped) or stripped
        if "终局必须回答" in stripped or "must_answer" in stripped.lower():
            tail = _after_colon(stripped)
            if tail:
                must_answer.append(tail)
            continue
        if stripped.startswith("- ") and ("？" in stripped or "?" in stripped):
            must_answer.append(stripped.lstrip("- ").strip())
    seen = set()
    must_answer = [item for item in must_answer if item and not (item in seen or seen.add(item))]
    return dramatic_question, must_answer


def _core_resolution_hit(combined, dramatic_question, must_answer):
    strong_kw = (
        "核心问题解决", "主线完结", "主线核心冲突", "终局必须回答",
        "最终答案", "终局答案", "终极答案", "最终揭秘",
    )
    if any(kw in combined for kw in strong_kw):
        return True, []
    answered = [item for item in [dramatic_question] + must_answer if item and item in combined]
    return bool(answered), answered


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

    # ── 反向刹车：非终局禁解主线核心冲突 (P2-⑧) ──────────────────────────
    # 行业最佳实践：AI 倾向于过早"收束"冲突（稳定偏差），必须检测主线戏剧问题
    # 是否在终局前被意外回答。分辨率阈值：当前进度 < 总章数 80% 且弧段包含
    # 对核心戏剧问题的"解决"信号 → 阻断。
    meta = _load_json(os.path.join(root, "_meta.json"), {}) or {}
    target_chapters = int(meta.get("target_chapters") or 0)
    if target_chapters > 0:
        threshold = max(int(target_chapters * 0.8), target_chapters - 3)
        if end < threshold:
            contract_path = os.path.join(root, "设定", "读者契约.md")
            contract_text = _read_text(contract_path) if os.path.exists(contract_path) else ""
            dramatic_question, must_answer = _extract_core_contract_questions(contract_text)

            # 检测弧段内对核心问题的"过早回答"
            resolution_kw = ("回答", "最终答案", "真相大白", "谜底揭晓", "终极答案",
                            "核心问题解决", "主线完结", "最终揭秘", "水落石出", "尘埃落定",
                            "不复存在", "不再重要", "被颠覆", "失去意义")
            for rpt in chapter_reports:
                ch = rpt["chapter"]
                delta = _load_json(_delta_path(root, ch), {}) or {}
                progress = _as_list(delta.get("reader_contract_progress"))
                theme = str(delta.get("theme_alignment") or "")
                combined = " ".join(progress) + " " + theme
                if any(kw in combined for kw in resolution_kw):
                    is_core, answered = _core_resolution_hit(combined, dramatic_question, must_answer)
                    item = {
                        "severity": "阻断级" if is_core else "建议级",
                        "type": "premature_resolution" if is_core else "resolution_signal_needs_review",
                        "chapter": ch,
                        "message": (
                            f"反向刹车：第{ch:02d}章出现收束信号（进度 {end}/{target_chapters}，"
                            f"{end*100//target_chapters}%）。核心问题：「{dramatic_question or '见读者契约'}」"
                            + (f"；疑似已回答：{'、'.join(answered)}" if answered else "")
                            + ("。非终局章节禁止解决主线核心冲突，请推迟到终局。"
                               if is_core else "。未命中核心问题/终局必须回答项，按局部支线回收候选提醒人审。")
                        ),
                    }
                    if is_core:
                        blocks.append(item)
                        break
                    warnings.append(item)

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
