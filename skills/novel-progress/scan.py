#!/usr/bin/env python3
"""novel-progress/scan.py — 写小说进度扫描器（只读）。"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

# Add _lib to path
LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'novel', '_lib'))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

# Also add novel skill root to path to import summarize
NOVEL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'novel'))
if NOVEL_ROOT not in sys.path:
    sys.path.insert(0, NOVEL_ROOT)

from novel_route import format_route, summarize as novel_summarize

try:
    from qa_gate import collect_gate_status, format_gate_status
except Exception:  # qa_gate 缺失时优雅降级
    collect_gate_status = None
    format_gate_status = None

LINE_DIR = "写小说"

def find_repo_root(start):
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "skills")):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(start)

def report(root, out):
    res = novel_summarize(root)
    if "error" in res:
        out.append(f"（无可解析的进度表: {res['error']}）")
        return

    header = res["header"]
    rows = res["rows"]
    done = res["done"]
    first = res["first"]
    bottleneck = res["bottleneck"]

    out.append(f"章节数: {len(rows)} | 完结: {done}/{len(rows)}")
    
    # Simple stages summary
    flow = [h for h in header if h not in {"章节", "字数", "序号", "#", "标题"}]
    stages_done = []
    for c in flow:
        count = sum(1 for r in rows if r.get(c) == "✅")
        stages_done.append(f"{c} {count}/{len(rows)}")
    out.append("各阶段完成: " + " | ".join(stages_done))

    if first:
        out.append(f"前沿: {format_route(root, first)}")
    else:
        out.append("✅ 全部完成。")

    if bottleneck:
        items = sorted(bottleneck.items(), key=lambda kv: kv[1], reverse=True)
        out.append("待办缺口: " + " · ".join(f"{k}={v}" for k, v in items[:5]))

    if collect_gate_status is not None:
        try:
            gate = collect_gate_status(root)
        except Exception:
            gate = None
        if gate and gate.get("blocking"):
            n = len(gate.get("blockers") or [])
            out.append(f"⛔ QA gate 阻断: {n} 项（导出/发布前必须清；详见 novel-gate.py）")

def main():
    repo_root = find_repo_root(os.path.dirname(__file__))
    
    args = sys.argv[1:]
    works = []
    if args:
        for a in args:
            root = os.path.abspath(a)
            if os.path.isfile(os.path.join(root, "_进度.md")):
                works.append((root, os.path.relpath(root, repo_root)))
    else:
        base = os.path.join(repo_root, LINE_DIR)
        if os.path.isdir(base):
            for name in sorted(os.listdir(base)):
                root = os.path.join(base, name)
                if os.path.isfile(os.path.join(root, "_进度.md")):
                    works.append((root, os.path.join(LINE_DIR, name)))

    if not works:
        print(f"未找到任何含 _进度.md 的小说。线根目录：{LINE_DIR}/")
        return

    def run_report(root, rel):
        out = [f"=== {rel} ==="]
        report(root, out)
        return "\n".join(out)

    with ThreadPoolExecutor(max_workers=min(len(works), 16)) as executor:
        blocks = list(executor.map(lambda w: run_report(*w), works))

    print("\n\n".join(blocks))

if __name__ == "__main__":
    main()
