#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad-progress/scan.py — 拍广告进度扫描器（只读）。

默认扫描 `创作区/拍广告/<项目>/_进度.md`，并兼容旧 `拍广告/<项目>/_进度.md`。
广告线不拆集：进度由阶段表 + 交付版本矩阵共同表达。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

CREATION_ROOT_DIR = "创作区"
LINE_DIR = "拍广告"
DONE = "done"
PARTIAL = "partial"
TODO = "todo"


def find_repo_root(start: str) -> str:
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "skills")) and (
            os.path.isfile(os.path.join(d, "AGENTS.md"))
            or os.path.isfile(os.path.join(d, "CLAUDE.md"))
        ):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(start)


def load_line_modules(repo_root: str):
    craft_dir = os.path.join(repo_root, "skills", "ad-craft", "scripts")
    lib_dir = os.path.join(repo_root, "skills", "ad", "_lib")
    for path in (craft_dir, lib_dir):
        if path not in sys.path:
            sys.path.insert(0, path)
    import contract  # noqa: WPS433,E402
    import progress_md  # noqa: WPS433,E402

    return contract, progress_md


def line_root_candidates(repo_root: str) -> list[str]:
    return [
        os.path.join(repo_root, CREATION_ROOT_DIR, LINE_DIR),
        os.path.join(repo_root, LINE_DIR),
    ]


def progress_root(path: str) -> str | None:
    root = os.path.abspath(path)
    if os.path.basename(root) == "_进度.md" and os.path.isfile(root):
        root = os.path.dirname(root)
    if os.path.isfile(os.path.join(root, "_进度.md")):
        return root
    return None


def collect_works(repo_root: str, targets: list[str]) -> list[tuple[str, str]]:
    works: list[tuple[str, str]] = []
    if targets:
        for target in targets:
            root = progress_root(target)
            rel = os.path.relpath(os.path.abspath(target), repo_root)
            if root is None:
                print(f"（跳过 {rel}：无 _进度.md）")
                continue
            works.append((root, os.path.relpath(root, repo_root)))
        return works

    for base in line_root_candidates(repo_root):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            root = os.path.join(base, name)
            if os.path.isfile(os.path.join(root, "_进度.md")):
                works.append((root, os.path.relpath(root, repo_root)))
    return works


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_stage_rows(progress_md, text: str) -> list[dict[str, str]]:
    return progress_md.parse_stage_rows(
        text,
        section_keywords=("阶段进度",),
        min_cols=2,
        label_col=0,
        status_col=1,
    )


def parse_deliverables(progress_md, text: str) -> list[dict[str, str]]:
    return progress_md.parse_stage_rows(
        text,
        section_keywords=("交付版本矩阵",),
        min_cols=7,
        label_col=0,
        status_col=5,
    )


def state_of(status: str) -> str:
    raw = (status or "").strip()
    low = raw.lower()
    if "✅" in raw or "[x]" in low:
        return DONE
    match = re.search(r"(\d+)\s*/\s*(\d+)", raw)
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        if total > 0 and current >= total:
            return DONE
        if current > 0:
            return PARTIAL
    if "🔴" in raw or "⏳" in raw or "rough" in low or "block" in low or raw not in ("", "⬜", "[ ]"):
        return PARTIAL
    return TODO


def marker(state: str) -> str:
    return {DONE: "✅", PARTIAL: "⏳", TODO: "⬜"}.get(state, "⬜")


def brief_hint(contract, root: str) -> str:
    path = os.path.join(root, "需求", "brief.json")
    if not os.path.isfile(path):
        return "brief: 缺 需求/brief.json，建议先回 ad-concept 第0步补齐客户需求"
    try:
        with open(path, encoding="utf-8") as fh:
            check = contract.brief_check(json.load(fh))
    except (OSError, json.JSONDecodeError):
        return "brief: 需求/brief.json 读取失败，请先检查 JSON 格式"
    if check["missing_required"]:
        return (
            "brief: 缺必填项 "
            + "、".join(check["missing_required"])
            + "，先让 ad-concept 第0步访谈补齐"
        )
    if check["missing_deferred"]:
        return (
            "brief: 合规项待补 "
            + "、".join(check["missing_deferred"])
            + "，不阻塞创意/脚本，但进出图/出视频/合成 gate 前必须补齐"
        )
    return ""


def report(contract, progress_md, root: str, rel: str, limit: int) -> str:
    out = [f"=== {rel} ==="]
    progress_file = os.path.join(root, "_进度.md")
    try:
        text = read_text(progress_file)
    except OSError as exc:
        out.append(f"（无可解析的进度表: {exc}）")
        return "\n".join(out)

    rows = parse_stage_rows(progress_md, text)
    if not rows:
        out.append("（_进度.md 未发现可解析的「阶段进度」表）")
        return "\n".join(out)

    stage_by_label = {str(s.get("label", "")): s for s in contract.stage_table()}
    states = [(row, state_of(row["status"])) for row in rows]
    done = sum(1 for _, state in states if state == DONE)
    out.append(f"阶段数: {len(rows)} | 完成: {done}/{len(rows)}")
    out.append("各阶段: " + " | ".join(f"{row['label']} {marker(state)}" for row, state in states))

    deliverables = parse_deliverables(progress_md, text)
    if deliverables:
        deliverable_states = [(row, state_of(row["status"])) for row in deliverables]
        d_done = sum(1 for _, state in deliverable_states if state == DONE)
        out.append(
            "交付件: "
            + f"{d_done}/{len(deliverables)} "
            + " | ".join(f"{row['label']} {marker(state)}" for row, state in deliverable_states[:6])
        )
        if len(deliverables) > 6:
            out.append(f"  - …另有 {len(deliverables) - 6} 个交付件")

    hint = brief_hint(contract, root)
    if hint:
        out.append(hint)

    frontier_index = next((i for i, (_, state) in enumerate(states) if state != DONE), None)
    if frontier_index is None:
        out.append("✅ 阶段进度看起来都已完成。下一步：ad-review M0 质检 + ad-craft AI/授权披露确认。")
        return "\n".join(out)

    row, state = states[frontier_index]
    meta = stage_by_label.get(row["label"], {})
    owner = meta.get("owner", "ad")
    key = meta.get("key", "")
    gate = meta.get("gate", "")
    vt = f"（当前 {row['status']}）" if row["status"] and state != TODO else ""
    out.append(f"前沿: {row['label']} {vt} → skill: {owner}")
    if gate:
        out.append(f"  gate: {gate}")
    if key in getattr(contract, "GATE_STAGES", ()):
        out.append("  ⚠️ 高风险阶段：会花钱/不可逆，正式生产前确认后端、交付规格并先跑 ad-craft gate")

    later = [item for item in states[frontier_index + 1:] if item[1] != DONE]
    if later:
        out.append("后续待办:")
        for item, item_state in later[:limit]:
            meta = stage_by_label.get(item["label"], {})
            out.append(f"  - {item['label']} {marker(item_state)} → {meta.get('owner', 'ad')}")
        if len(later) > limit:
            out.append(f"  - …另有 {len(later) - limit} 项")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="拍广告进度仪表盘（只读）")
    ap.add_argument("project_roots", nargs="*", help="可选：一个或多个广告项目根，或 _进度.md 文件")
    ap.add_argument("--root", default=None, help="仓库根；默认自动向上查找")
    ap.add_argument("--limit", type=int, default=5, help="每个项目展示的后续待办条数")
    args = ap.parse_args(argv)

    repo_root = os.path.abspath(args.root) if args.root else find_repo_root(os.path.dirname(__file__))
    contract, progress_md = load_line_modules(repo_root)
    works = collect_works(repo_root, args.project_roots)
    if not works:
        print(f"未找到任何含 _进度.md 的广告项目。线根目录：{CREATION_ROOT_DIR}/{LINE_DIR}/")
        return 0

    print("\n\n".join(report(contract, progress_md, root, rel, args.limit) for root, rel in works))
    print(f"\n--- 共 {len(works)} 条广告项目 ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
