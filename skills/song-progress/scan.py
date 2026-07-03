#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""song-progress/scan.py — 写歌进度扫描器（只读）。

默认扫描 `创作区/写歌/<曲名>/_进度.md`，并兼容旧 `写歌/<曲名>/_进度.md`。
单项目口径复用 song-craft/scripts/progress.py；本脚本只负责发现作品并聚合输出。
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import os
import sys
from contextlib import redirect_stdout

CREATION_ROOT_DIR = "创作区"
LINE_DIR = "写歌"


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


def line_root_candidates(repo_root: str) -> list[str]:
    return [
        os.path.join(repo_root, CREATION_ROOT_DIR, LINE_DIR),
        os.path.join(repo_root, LINE_DIR),
    ]


def load_single_project_progress(repo_root: str):
    path = os.path.join(repo_root, "skills", "song-craft", "scripts", "progress.py")
    spec = importlib.util.spec_from_file_location("song_craft_progress", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def run_report(progress_mod, root: str, rel: str, limit: int) -> str:
    out = [f"=== {rel} ==="]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            progress_mod.report(root, limit)
    except Exception as exc:  # pragma: no cover - 单项目坏表不应拖垮整线看板
        out.append(f"（扫描失败，跳过本曲：{type(exc).__name__}: {exc}）")
        return "\n".join(out)
    body = buf.getvalue().strip()
    out.append(body or "（无输出）")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="写歌进度仪表盘（只读）")
    ap.add_argument("project_roots", nargs="*", help="可选：一个或多个歌曲项目根，或 _进度.md 文件")
    ap.add_argument("--root", default=None, help="仓库根；默认自动向上查找")
    ap.add_argument("--limit", type=int, default=5, help="每个项目展示的后续待办条数")
    args = ap.parse_args(argv)

    repo_root = os.path.abspath(args.root) if args.root else find_repo_root(os.path.dirname(__file__))
    works = collect_works(repo_root, args.project_roots)
    if not works:
        print(f"未找到任何含 _进度.md 的歌曲项目。线根目录：{CREATION_ROOT_DIR}/{LINE_DIR}/")
        return 0

    progress_mod = load_single_project_progress(repo_root)
    print("\n\n".join(run_report(progress_mod, root, rel, args.limit) for root, rel in works))
    print(f"\n--- 共 {len(works)} 首歌 ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
