#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读 拍广告/<项目>/_进度.md 的「阶段进度」表，报告当前前沿 + 下一步该跑哪个 ad-* skill。

只读，不改文件。解析很宽容：只看「阶段进度」段里 `| 阶段 | 状态 | ...` 行的前两列，
按 ad-craft 阶段表把中文阶段标签映射回 stage key，找第一个未 ✅ 的阶段作为前沿。
"""
import argparse
import os
import re
import sys

_CRAFT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ad-craft", "scripts"))
if _CRAFT not in sys.path:
    sys.path.insert(0, _CRAFT)
import contract  # noqa: E402

DONE = "✅"


def parse_stage_rows(text):
    """从 _进度.md 抽「阶段进度」段的 (label, status) 列表。"""
    rows = []
    in_section = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_section = "阶段进度" in s
            continue
        if not in_section or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("阶段", "") or set(cells[0]) <= set("-: "):
            continue
        rows.append((cells[0], cells[1]))
    return rows


def main():
    ap = argparse.ArgumentParser(description="拍广告进度路由（只读）")
    ap.add_argument("project_root")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    prog = os.path.join(root, "_进度.md")
    if not os.path.isfile(prog):
        print(f"[err] 没有 _进度.md：{root}\n建议先 init_project.py 立项。", file=sys.stderr)
        sys.exit(2)

    with open(prog, encoding="utf-8") as f:
        rows = parse_stage_rows(f.read())

    stage_by_label = {s["label"]: s for s in contract.stage_table()}
    frontier = None
    print(f"# {os.path.basename(root)} — 拍广告进度\n")
    for label, status in rows:
        meta = stage_by_label.get(label)
        owner = meta["owner"] if meta else "?"
        print(f"- {status} {label}  ·  {owner}")
        if frontier is None and DONE not in status and "二期" not in label:
            frontier = (label, meta)

    print()
    if frontier is None:
        print("[done] 阶段进度看起来都已完成 ✅ —— 下一步：投放前 AI/授权披露（ad-craft ai_usage.py）+ 二期质检 ad-review。")
        return
    label, meta = frontier
    owner = meta["owner"] if meta else "?"
    key = meta["key"] if meta else "?"
    gate = " ⚠️ 高风险（花钱/不可逆）阶段，正式生产前确认" if key in contract.GATE_STAGES else ""
    print(f"[前沿] 下一步：**{label}** → 跑 `{owner}`{gate}")


if __name__ == "__main__":
    main()
