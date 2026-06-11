#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic progress scanner/updater for 写小说/<项目>/.

Usage:
    python3 skills/novel-craft/scripts/progress.py <作品根> [--limit 5]
    python3 skills/novel-craft/scripts/progress.py set <作品根> <stage> done|todo

Novel skills can use this to resume from the first unfinished stage, and to
mark stable machine stages without hand-editing _进度.md.
"""
import argparse
import json
import os
import re
import sys

# Inject common directory for markdown_parser
COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'common'))
if COMMON_DIR not in sys.path:
    sys.path.insert(0, COMMON_DIR)

from markdown_parser import file_lock, atomic_write_text, update_checklist_stage

from contract import stage_info
from qa_gate import collect_gate_status, format_gate_status


CHECK_RE = re.compile(r"^\s*-\s*\[\s\]\s*(.+?)\s*$")
TABLE_RE = re.compile(r"^\|\s*([^|]+?)\s*\|.*\[\s\]\s*\|")
DONE_TABLE_RE = re.compile(r"^\|\s*([^|]+?)\s*\|.*\[[xX]\]\s*\|")
STAGE_RE = re.compile(r"<!--\s*stage:([a-z_]+)\s*-->")
COMMENT_RE = re.compile(r"\s*<!--.*?-->\s*")


def progress_path(root):
    return os.path.join(root, "_进度.md")


def progress_lock_path(root):
    return os.path.join(root, "_进度.lock")


def load_meta(root):
    path = os.path.join(root, "_meta.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def scan_progress(root):
    path = progress_path(root)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    items = []
    section = "未分组"
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    has_machine_schema = any("novel-progress-schema" in line for line in lines)
    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = CHECK_RE.match(line)
        if m:
            raw_item = m.group(1).strip()
            sm = STAGE_RE.search(raw_item)
            if has_machine_schema and not sm:
                continue
            item = COMMENT_RE.sub("", raw_item).strip()
            items.append({
                "line": lineno,
                "section": section,
                "item": item,
                "stage": sm.group(1) if sm else None,
            })
            continue
        mt = TABLE_RE.match(line)
        if has_machine_schema:
            continue
        if mt and not DONE_TABLE_RE.match(line):
            key = mt.group(1).strip()
            if key and key not in ("---", "章"):
                items.append({"line": lineno, "section": section,
                              "item": f"章节/条目 {key}", "stage": None})
    return items


def set_stage(root, stage_key, state):
    """Mark one machine-readable stage done/todo under an exclusive lock, using common parser."""
    path = progress_path(root)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    
    with file_lock(progress_lock_path(root)):
        with open(path, encoding="utf-8") as f:
            content = f.read()
            
        new_content, changed = update_checklist_stage(content, stage_key, state)
        
        if changed:
            atomic_write_text(path, new_content)
            
    return {"stage": stage_key, "state": state, "changed": changed, "path": path}


def scan_main(argv=None):
    ap = argparse.ArgumentParser(description="读取 novel 项目 _进度.md，报告下一步")
    ap.add_argument("project_root")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args(argv)

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
    
    findings_files = []
    try:
        from glob import glob
        findings_files = glob(os.path.join(root, "审稿", "*findings*.json")) + glob(os.path.join(root, "审稿", "consistency_audit.json"))
    except Exception:
        pass
    if findings_files:
        print("\n次要缺口/待办:")
        print("  - 存在未解决的一致性 findings (建议调 novel-review 修复或确认)")

    rest = items[1:args.limit]
    if rest:
        print("\n后续未完成项：")
        for item in rest:
            stage = f" [{item['stage']}]" if item.get("stage") else ""
            print(f"-{stage} {item['section']} / {item['item']}  (line {item['line']})")


def set_main(argv):
    ap = argparse.ArgumentParser(description="安全更新 novel 项目 _进度.md 的机器阶段")
    ap.add_argument("project_root")
    ap.add_argument("stage")
    ap.add_argument("state", choices=("done", "todo"))
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    try:
        result = set_stage(root, args.stage, args.state)
    except FileNotFoundError as e:
        print(f"[err] 找不到进度文件：{e.filename}", file=sys.stderr)
        sys.exit(2)
    except KeyError as e:
        print(f"[err] {e}", file=sys.stderr)
        sys.exit(2)
    changed = "updated" if result["changed"] else "already"
    print(f"[ok] _进度.md {changed}: {args.stage} -> {args.state}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "set":
        return set_main(argv[1:])
    return scan_main(argv)


if __name__ == "__main__":
    main()
