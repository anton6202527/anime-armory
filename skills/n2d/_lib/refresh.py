#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选项刷新——确定性骨架（搜索/核验由 AI 代理按 SKILL.md 执行）。

把「候选快照会过期」从 prose 约定变成可操作流程。分工：
- 本脚本（确定性）：① `status` 报哪些候选源过期/缺戳；② `bump` 在 AI 改完某份候选清单后，
  把它的「采集日期」戳记推到新日并把本次刷新（含来源/diff 摘要）落进 provenance ledger；
  ③ `log` 回看刷新审计。
- AI 代理（SKILL.md 流程）：对 status 标 stale 的源，用实时搜索/官方文档/专业知识核验当前
  候选是否新增/改名/淘汰/改规格，编辑对应文件的候选清单，**写清来源**，再调 `bump` 落档。

不联网、不调模型；只读写仓库内文件 + 一个 jsonl 审计账本。

CLI:
    python3 refresh.py status [--today YYYY-MM-DD] [--json]
    python3 refresh.py bump <source-id> --source "<出处URL/文档>" [--date YYYY-MM-DD]
                       [--note "本轮改了什么"] [--by <agent/人>]
    python3 refresh.py log [--json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from typing import Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)  # freshness 是同目录兄弟（本线 _lib）

import freshness as fr  # noqa: E402  候选源登记表 + 戳记解析单一真值源

LEDGER = os.path.join(_HERE, "..", "refresh_log.jsonl")
_STAMP_LINE_RE = re.compile(r"(采集日期\s*[:：]\s*)(\d{4}-\d{2}-\d{2})")


def _source_by_id(sid: str) -> Optional[Dict[str, object]]:
    for s in fr.CANDIDATE_SOURCES:
        if s["id"] == sid:
            return s
    return None


def cmd_status(args) -> int:
    today = _dt.date.fromisoformat(args.today) if args.today else _dt.date.today()
    results = fr.check_all(today)
    if args.json:
        print(json.dumps({"today": today.isoformat(), "results": results},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"# 候选刷新工单（基准日 {today.isoformat()}）\n")
    print(fr.render_table(results))
    stale = [r for r in results if r["status"] in fr._BAD_STATUSES]
    if not stale:
        print("\n全部新鲜，无需刷新。")
        return 0
    print(f"\n## 待刷新 {len(stale)} 项——逐项按 SKILL.md 流程处理：\n")
    for r in stale:
        print(f"### {r['id']}  （{r['status']}）")
        print(f"- 文件：`{r['path']}`")
        print(f"- 覆盖选择点：{'/'.join(r['choice_points'])}")
        print(f"- 动作：实时搜索/官方文档核验这些选择点的当前候选 → 编辑上面文件的候选清单（写清来源）"
              f" → `python3 refresh.py bump {r['id']} --source \"<出处>\" --note \"<改了啥>\"`")
        print()
    return 0


def cmd_bump(args) -> int:
    src = _source_by_id(args.source_id)
    if src is None:
        ids = ", ".join(s["id"] for s in fr.CANDIDATE_SOURCES)
        print(f"未知候选源 id: {args.source_id}\n可选：{ids}", file=sys.stderr)
        return 2
    abspath = os.path.join(fr.REPO_ROOT, str(src["path"]))
    try:
        with open(abspath, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"读不到候选源文件：{abspath}（{e}）", file=sys.stderr)
        return 2

    new_date = args.date or _dt.date.today().isoformat()
    try:
        _dt.date.fromisoformat(new_date)
    except ValueError:
        print(f"--date 非法：{new_date}", file=sys.stderr)
        return 2

    m = _STAMP_LINE_RE.search(text)
    if not m:
        print(f"该文件没有「采集日期：YYYY-MM-DD」戳记行，无法 bump：{src['path']}\n"
              f"先在文件里加一行 `采集日期：{new_date}` 再重试。", file=sys.stderr)
        return 2
    old_date = m.group(2)
    new_text = text[:m.start()] + m.group(1) + new_date + text[m.end():]
    with open(abspath, "w", encoding="utf-8") as f:
        f.write(new_text)

    entry = {
        "ts": (args.ts or _dt.datetime.now().isoformat(timespec="seconds")),
        "source_id": args.source_id,
        "path": str(src["path"]),
        "choice_points": list(src.get("choice_points", [])),
        "old_date": old_date,
        "new_date": new_date,
        "source": args.source,
        "note": args.note or "",
        "by": args.by or "ai-agent",
    }
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"✅ {args.source_id} 采集日期 {old_date} → {new_date}，已落 provenance ledger。")
    return 0


def cmd_log(args) -> int:
    if not os.path.isfile(LEDGER):
        print("（暂无刷新记录）")
        return 0
    rows: List[Dict] = []
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    for r in rows:
        print(f"- {r['ts']}  {r['source_id']}  {r['old_date']}→{r['new_date']}  "
              f"by {r.get('by','?')}  来源：{r.get('source','—')}  {r.get('note','')}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="候选项刷新骨架")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="报哪些候选源过期/缺戳")
    p.add_argument("--today", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("bump", help="改完候选清单后推采集日期+落 provenance")
    p.add_argument("source_id")
    p.add_argument("--source", required=True, help="本次核验出处（URL/官方文档/榜单）")
    p.add_argument("--date", default=None, help="新采集日期 YYYY-MM-DD（默认今天）")
    p.add_argument("--note", default=None, help="本轮改了什么")
    p.add_argument("--by", default=None, help="刷新者（agent/人）")
    p.add_argument("--ts", default=None, help=argparse.SUPPRESS)  # 测试可注入固定时间
    p.set_defaults(func=cmd_bump)

    p = sub.add_parser("log", help="回看刷新审计账本")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_log)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
