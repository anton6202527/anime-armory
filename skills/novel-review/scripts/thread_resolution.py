#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
thread_resolution.py — 支线/open_threads 收口检查（纯标准库，确定性机检）

审稿/state_ledger.json（novel-craft/reconcile_ledger.py 维护）逐章累积
open_threads / resolved_threads，但没有任何东西去盯：
  1) 支线开太久没收口（span 超过 max_open_span 章）→ 建议级 subplot_stale
  2) 卷末/书末（--finale）仍挂着的支线 → 阻断级 subplot_unresolved_at_finale
     （结局还吊着一条支线 = 烂尾。非 finale 时不报，只看 span。）

哨兵只报候选，每条带证据 + auto 标志，最终由人/LLM 定夺（容错铁律：宁缺毋滥）。
字段缺失（如某 thread 无 opened_chapter）→ 跳过该 thread 的 span 检查，不臆造。

  python3 thread_resolution.py <作品根> [--finale] [--max-span 30] [--json]

测试：cd skills/novel-review/scripts && python3 -m pytest test_thread_resolution.py
"""
import os
import re
import sys
import json
import argparse

MAX_OPEN_SPAN = 30  # 支线开超过此章数仍未收口 → 建议级（与下游章纲纪律一致）


def _thread_id(thread):
    """容错取 thread 的可读标识：id → thread → description → 'thread'。"""
    if not isinstance(thread, dict):
        return str(thread)[:60] if thread else "thread"
    for k in ("id", "thread", "description", "desc"):
        v = thread.get(k)
        if v:
            return str(v)[:60]
    return "thread"


def _thread_desc(thread):
    """容错取 thread 的描述文本（作 evidence）。"""
    if not isinstance(thread, dict):
        return str(thread)[:80] if thread else ""
    for k in ("description", "desc", "thread", "id"):
        v = thread.get(k)
        if v:
            return str(v)[:80]
    return ""


def _opened_chapter(thread):
    """容错取支线开启章号：opened_chapter → chapter → opened_at → opened_in_chapter。
    取不到（缺字段/非数字）→ None（调用方据此跳过 span 检查，不臆造）。"""
    if not isinstance(thread, dict):
        return None
    for k in ("opened_chapter", "chapter", "opened_at", "opened_in_chapter"):
        if k in thread and thread[k] is not None:
            try:
                return int(thread[k])
            except (TypeError, ValueError):
                continue
    return None


def overdue_threads(open_threads, current_chapter, max_open_span=MAX_OPEN_SPAN):
    """支线开太久仍未收口（建议级）。纯函数·可测。

    对每条 open_thread：有 opened_chapter 且 (current_chapter - opened_chapter) > max_open_span
    → 报 subplot_stale。无 opened_chapter 的 thread 跳过（不臆造跨度）。
    """
    alerts = []
    if current_chapter is None:
        return alerts
    try:
        cur = int(current_chapter)
    except (TypeError, ValueError):
        return alerts
    for thread in (open_threads or []):
        opened = _opened_chapter(thread)
        if opened is None:
            continue
        span = cur - opened
        if span > max_open_span:
            alerts.append({
                "type": "subplot_stale",
                "entity": _thread_id(thread),
                "severity": "建议级",
                "chapter": cur,
                "opened_chapter": opened,
                "span": span,
                "evidence": _thread_desc(thread),
                "auto": True,
                "note": f"支线「{_thread_id(thread)}」自第{opened}章开启已挂 {span} 章未收口"
                        f"（>{max_open_span}，疑遗忘/拖沓——请回收或调整章纲）",
            })
    return alerts


def unresolved_at_finale(open_threads, is_finale):
    """卷末/书末仍挂着的支线（阻断级）。纯函数·可测。

    is_finale 为真时，每条仍 open 的 thread → subplot_unresolved_at_finale（结局吊支线=烂尾）。
    非 finale → 返回 []（普通章只看 span，由 overdue_threads 负责）。
    """
    if not is_finale:
        return []
    alerts = []
    for thread in (open_threads or []):
        opened = _opened_chapter(thread)
        item = {
            "type": "subplot_unresolved_at_finale",
            "entity": _thread_id(thread),
            "severity": "阻断级",
            "evidence": _thread_desc(thread),
            "auto": True,
            "note": f"支线「{_thread_id(thread)}」直到卷末/书末仍未收口"
                    f"（结局遗留未解支线＝烂尾，必须回收或显式弃置）",
        }
        if opened is not None:
            item["opened_chapter"] = opened
        alerts.append(item)
    return alerts


def _load_ledger(project):
    """读 审稿/state_ledger.json；缺/坏 → None（据此优雅跳过，不臆造）。"""
    path = os.path.join(project, "审稿", "state_ledger.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _last_chapter(project):
    """末章号：优先 wiki_builder.list_chapters，导入失败则扫目录文件名里的数字。
    取不到 → None。"""
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "novel-wiki", "scripts"))
        from wiki_builder import list_chapters  # type: ignore
        chaps = list_chapters(project)
        if chaps:
            return max(c[0] for c in chaps)
    except Exception:
        pass
    best = None
    for root in (os.path.join(project, "章节"), os.path.join(project, "正文"), project):
        if not os.path.isdir(root):
            continue
        for fn in os.listdir(root):
            m = re.search(r"(\d+)", fn)
            if m:
                n = int(m.group(1))
                best = n if best is None else max(best, n)
        if best is not None:
            break
    return best


def analyze(project, current_chapter=None, finale=False, max_open_span=MAX_OPEN_SPAN):
    """加载 state_ledger，跑 overdue +（finale 时）finale 收口检查。

    返回 {"alerts":[...], "open":N, "resolved":N}；
    ledger 缺失/无 threads → 优雅跳过（alerts=[] + note）。
    """
    ledger = _load_ledger(project)
    if ledger is None:
        return {"alerts": [], "open": 0, "resolved": 0,
                "note": "审稿/state_ledger.json 不存在，跳过支线收口检查"}
    open_threads = ledger.get("open_threads") or []
    resolved = ledger.get("resolved_threads") or []
    if not open_threads:
        return {"alerts": [], "open": 0, "resolved": len(resolved),
                "note": "open_threads 为空，无待收口支线"}

    if current_chapter is None:
        current_chapter = _last_chapter(project)

    alerts = overdue_threads(open_threads, current_chapter, max_open_span)
    if finale:
        alerts = alerts + unresolved_at_finale(open_threads, True)
    return {
        "alerts": alerts,
        "open": len(open_threads),
        "resolved": len(resolved),
        "current_chapter": current_chapter,
        "finale": bool(finale),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="支线/open_threads 收口检查（卷末/书末烂尾防线）")
    p.add_argument("project_path")
    p.add_argument("--finale", action="store_true",
                   help="卷末/书末审稿模式：仍挂着的支线一律阻断级")
    p.add_argument("--max-span", type=int, default=MAX_OPEN_SPAN,
                   help=f"支线开超过此章数未收口报建议级（默认 {MAX_OPEN_SPAN}）")
    p.add_argument("--json", action="store_true", help="仅打印 JSON 结果")
    args = p.parse_args(argv)

    result = analyze(args.project_path, finale=args.finale, max_open_span=args.max_span)
    alerts = result["alerts"]
    blocking = sum(1 for a in alerts if a.get("severity") == "阻断级")

    out_dir = os.path.join(args.project_path, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "thread_findings.json")
    payload = {
        "status": "clean" if not alerts else "issues",
        "finale": bool(args.finale),
        "open": result["open"],
        "resolved": result["resolved"],
        "blocking": blocking,
        "alerts": alerts,
    }
    if "note" in result:
        payload["note"] = result["note"]
    if "current_chapter" in result:
        payload["current_chapter"] = result["current_chapter"]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif alerts:
        print(f"⚠️ 支线收口：{len(alerts)} 条候选（阻断 {blocking}，open {result['open']}/"
              f"resolved {result['resolved']}）→ {out_path}")
        for a in alerts:
            print(f"  [{a['severity']}] {a['type']} · {a['entity']} · {a.get('evidence','')}")
    else:
        note = result.get("note", "0 待收口问题")
        print(f"✅ 支线收口：{note}（open {result['open']}/resolved {result['resolved']}）→ {out_path}")

    # 阻断级（finale 仍挂支线＝烂尾）非零退出，让上游硬挡（与 logic_sentry/power_system 同约定）。
    if blocking:
        sys.exit(1)


if __name__ == "__main__":
    main()
