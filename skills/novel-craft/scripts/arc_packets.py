#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build arc-level drafting packets for long novel projects.

Per-chapter packets are necessary but not enough for long-form work: the writer
also needs a rolling arc goal so the middle of the book does not lose the reader
contract. This script materializes that arc packet without calling any model.
"""
import argparse
import json
import os
import re
import sys
from datetime import date


CHAPTER_RE = re.compile(r"第\s*0*(\d+)\s*章\s*(?:[《<]([^》>]+)[》>])?\s*(?:[—-]\s*(.*))?")


def _read_text(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _clip(text, limit=1800):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...（已截断；按路径读取原文件）"


def _parse_arc(value):
    match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", str(value))
    if not match:
        raise ValueError("--arc 格式应为 1-5")
    start, end = int(match.group(1)), int(match.group(2))
    if end < start:
        raise ValueError("--arc 结束章不能小于开始章")
    return start, end


def _parse_outline(root):
    text = _read_text(os.path.join(root, "设定", "章纲.md"))
    outline = {}
    for raw in text.splitlines():
        match = CHAPTER_RE.search(raw)
        if not match:
            continue
        chapter = int(match.group(1))
        outline[chapter] = {
            "title": (match.group(2) or "").strip(),
            "beat": (match.group(3) or raw).strip(),
            "raw": raw.strip(),
        }
    return outline


def _reader_contract(root):
    gate = _load_json(os.path.join(root, "审稿", "demo_gate.json"), {}) or {}
    rc = gate.get("reader_contract") if isinstance(gate.get("reader_contract"), dict) else {}
    text = _read_text(os.path.join(root, "设定", "读者契约.md"))
    return gate, rc, text


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value).strip()
    return [s] if s else []


def _fmt_list(value):
    items = _as_list(value)
    return "、".join(items) if items else "未填写"


def _open_threads(ledger):
    ledger = ledger or {}
    threads = []
    for key in ("open_threads", "unresolved_hooks"):
        for item in ledger.get(key, []) if isinstance(ledger.get(key, []), list) else []:
            if isinstance(item, dict):
                label = item.get("id") or item.get("question") or item.get("title") or item.get("description")
                note = item.get("status") or item.get("urgency") or ""
                if label:
                    threads.append(f"{label} {f'({note})' if note else ''}".strip())
            elif str(item).strip():
                threads.append(str(item).strip())
    return threads[:12]


def _arc_paths(root, start, end):
    stem = f"第{start:02d}-{end:02d}章"
    return (
        os.path.join(root, "写作任务", f"弧段_{stem}.md"),
        os.path.join(root, "审稿", f"arc_plan_{stem}.json"),
    )


def _revision_tasks_in_window(root, start, end):
    """汇流后的修订计划里落在本弧段章窗内（或全书级 P0 无章号）的任务，按优先级排序。
    让 revision_plan.json 真正回流进弧段重写，而非躺成无人读的报告。"""
    plan = _load_json(os.path.join(root, "修订", "revision_plan.json"), None)
    if not isinstance(plan, dict):
        return []
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    picked = []
    for t in plan.get("tasks") or []:
        if not isinstance(t, dict):
            continue
        ch = t.get("chapter")
        if (isinstance(ch, int) and start <= ch <= end) or (ch is None and t.get("priority") == "P0"):
            picked.append(t)
    return sorted(picked, key=lambda t: (rank.get(t.get("priority"), 9), t.get("chapter") or 0))


def build(root, start, end):
    root = os.path.abspath(root)
    meta = _load_json(os.path.join(root, "_meta.json"), {}) or {}
    outline = _parse_outline(root)
    gate, reader_contract, contract_text = _reader_contract(root)
    ledger = _load_json(os.path.join(root, "审稿", "state_ledger.json"), {}) or {}
    chapters = []
    for chapter in range(start, end + 1):
        item = outline.get(chapter, {})
        chapters.append({
            "chapter": chapter,
            "title": item.get("title") or "",
            "beat": item.get("beat") or "（章纲未写本章条目）",
            "raw": item.get("raw") or "",
        })
    required_contract = {
        "theme": reader_contract.get("theme") or "",
        "dramatic_question": reader_contract.get("dramatic_question") or "",
        "must_answer": _as_list(reader_contract.get("must_answer")),
        "reader_promises": _as_list(reader_contract.get("reader_promises")) or _as_list(gate.get("reader_promises")),
        "delight_engine": _as_list(reader_contract.get("delight_engine")),
        "banned_drift": _as_list(reader_contract.get("banned_drift")) or _as_list(gate.get("banned_drift")),
    }
    plan = {
        "schema_version": 1,
        "kind": "novel_arc_plan",
        "created_at": date.today().isoformat(),
        "title": meta.get("title", ""),
        "arc": f"{start}-{end}",
        "chapters": list(range(start, end + 1)),
        "required_contract": required_contract,
        "open_threads_snapshot": _open_threads(ledger),
        "outline": chapters,
        "revision_tasks": _revision_tasks_in_window(root, start, end),
        "gate_after_write": f"python3 skills/novel-review/scripts/arc_gate.py \"{root}\" --arc {start}-{end}",
    }
    packet_lines = [
        f"# 弧段写作任务包：第 {start:02d}-{end:02d} 章",
        "",
        "## 弧段目标",
        f"- 作品：{meta.get('title', '未命名')}",
        f"- 目标平台：{meta.get('target_platform', '未指定')}",
        f"- 篇幅档：{meta.get('scale', '未指定')}",
        "- 本弧段不是单章事件清单，必须形成一个可感知的推进：承诺推进、关系变化、秘密揭示、代价升级或阶段性回收至少命中两类。",
        "",
        "## 读者契约压舱石",
        f"- 核心题旨：{required_contract['theme'] or '未填写'}",
        f"- 核心戏剧问题：{required_contract['dramatic_question'] or '未填写'}",
        f"- 终局必须回答：{_fmt_list(required_contract['must_answer'])}",
        f"- 本弧段要继续兑现的读者承诺：{_fmt_list(required_contract['reader_promises'])}",
        f"- 好看机制：{_fmt_list(required_contract['delight_engine'])}",
        f"- 禁偏清单：{_fmt_list(required_contract['banned_drift'])}",
        "",
        "## 章节节拍",
    ]
    for item in chapters:
        title = f"《{item['title']}》" if item["title"] else ""
        packet_lines.append(f"- 第{item['chapter']:02d}章 {title}：{item['beat']}")
    revision_tasks = plan["revision_tasks"]
    if revision_tasks:
        packet_lines.extend(["", "## 本弧段待处理修订项（来自 `修订/revision_plan.json`）",
                             "> review/score/balance/feedback/simulate 汇流——本弧段重写须先消化："])
        for t in revision_tasks:
            ch = t.get("chapter")
            where = f"第{ch:02d}章" if isinstance(ch, int) else "全书级"
            reason = (t.get("reason") or "").strip()
            packet_lines.append(
                f"- [{t.get('priority')}] {where} · {t.get('title')}"
                f"（{t.get('recommended_skill')}·{t.get('return_to_stage')}）"
                + (f" — {reason}" if reason else ""))
    threads = plan["open_threads_snapshot"]
    packet_lines.extend([
        "",
        "## 未收线程快照",
        "\n".join(f"- {thread}" for thread in threads) if threads else "（state_ledger 未登记未收线程；写前人工确认没有遗漏高价值伏笔。）",
        "",
        "## 写作纪律",
        "- 本弧段内不得连续 3 章缺少 `reader_contract_progress`。",
        "- 每章 state_delta 都要写 `theme_alignment`；整段不能只有事件推进。",
        "- 若新增设定、关系、能力代价、秘密揭示，必须进入对应章节 `state_delta_第NN章.json`。",
        "- 本弧段写完后跑：",
        "```bash",
        plan["gate_after_write"],
        "```",
        "",
        "## `设定/读者契约.md` 摘录",
        _clip(contract_text, 1800) if contract_text else "（缺 `设定/读者契约.md`；长篇写作前应补齐。）",
        "",
    ])
    return "\n".join(packet_lines), plan


def main():
    parser = argparse.ArgumentParser(description="生成长篇弧段写作任务包")
    parser.add_argument("root")
    parser.add_argument("--arc", required=True, help="章节范围，如 1-5")
    parser.add_argument("--stdout", action="store_true", help="只打印任务包，不写文件")
    args = parser.parse_args()

    try:
        start, end = _parse_arc(args.arc)
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        sys.exit(2)

    packet, plan = build(args.root, start, end)
    if args.stdout:
        print(packet)
        return

    packet_path, plan_path = _arc_paths(os.path.abspath(args.root), start, end)
    _write_text(packet_path, packet)
    _write_json(plan_path, plan)
    print(f"[ok] 弧段任务包: {packet_path}")
    print(f"[ok] 弧段计划: {plan_path}")
    print(f"[next] 本弧段写完后跑: {plan['gate_after_write']}")


if __name__ == "__main__":
    main()
