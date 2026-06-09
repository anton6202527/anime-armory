#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic read-only progress scanner for 写小说/<项目>/.

Usage:
    python3 skills/novel-craft/scripts/progress.py <作品根> [--limit 5]

It intentionally does not edit _进度.md. Novel skills can use this to resume
from the first unfinished checklist/table item without depending on a bespoke
progress format per workflow.
"""
import argparse
import json
import os
import re
import sys

from contract import stage_info
from qa_gate import collect_gate_status, format_gate_status


CHECK_RE = re.compile(r"^\s*-\s*\[\s\]\s*(.+?)\s*$")
TABLE_RE = re.compile(r"^\|\s*([^|]+?)\s*\|.*\[\s\]\s*\|")
DONE_TABLE_RE = re.compile(r"^\|\s*([^|]+?)\s*\|.*\[[xX]\]\s*\|")
STAGE_RE = re.compile(r"<!--\s*stage:([a-z_]+)\s*-->")
COMMENT_RE = re.compile(r"\s*<!--.*?-->\s*")


def load_meta(root):
    path = os.path.join(root, "_meta.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def scan_progress(root):
    path = os.path.join(root, "_进度.md")
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    items = []
    section = "未分组"
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.rstrip("\n")
            if line.startswith("## "):
                section = line[3:].strip()
                continue
            m = CHECK_RE.match(line)
            if m:
                raw_item = m.group(1).strip()
                sm = STAGE_RE.search(raw_item)
                item = COMMENT_RE.sub("", raw_item).strip()
                items.append({
                    "line": lineno,
                    "section": section,
                    "item": item,
                    "stage": sm.group(1) if sm else None,
                })
                continue
            mt = TABLE_RE.match(line)
            if mt and not DONE_TABLE_RE.match(line):
                key = mt.group(1).strip()
                if key and key not in ("---", "章"):
                    items.append({"line": lineno, "section": section,
                                  "item": f"章节/条目 {key}", "stage": None})
    return items


def main():
    ap = argparse.ArgumentParser(description="读取 novel 项目 _进度.md，报告下一步")
    ap.add_argument("project_root")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    try:
        items = scan_progress(root)
    except FileNotFoundError as e:
        print(f"[err] 找不到进度文件：{e.filename}", file=sys.stderr)
        sys.exit(2)

    meta = load_meta(root)
    title = meta.get("title") or meta.get("source_title") or os.path.basename(root)
    kind = meta.get("kind", "unknown")
    gate_status = collect_gate_status(root)
    print(f"# novel progress — {title} ({kind})")
    if not items:
        if gate_status["blocking"]:
            print("[done] _进度.md 未发现未完成项，但 QA gate 仍有阻断。")
            print("")
            print(format_gate_status(gate_status))
        else:
            print("[ok] _进度.md 未发现未完成项。")
        return
    first = items[0]
    stage = f" [{first['stage']}]" if first.get("stage") else ""
    print(f"[next]{stage} {first['section']} / {first['item']}  (line {first['line']})")
    info = stage_info(kind, first.get("stage")) if first.get("stage") else None
    if info:
        print(f"      owner: {info['owner']}")
        print(f"      gate: {info['gate']}")
        print(f"      on_fail: {info['on_fail']}")
    if gate_status["blocking"]:
        print("")
        print(format_gate_status(gate_status))
    rest = items[1:args.limit]
    if rest:
        print("\n后续未完成项：")
        for item in rest:
            stage = f" [{item['stage']}]" if item.get("stage") else ""
            print(f"-{stage} {item['section']} / {item['item']}  (line {item['line']})")


if __name__ == "__main__":
    main()
