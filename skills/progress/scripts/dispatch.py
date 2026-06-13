#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smart Progress Dispatcher.

Read-only progress entrypoint for all production lines.  It detects whether the
target is a project root, a line root, or the repository root, then routes to
the line-owned progress scanner.
"""

import argparse
import os
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

COMMON = os.path.join(REPO, "skills", "progress", "_lib")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from line_detect import LINE_LABELS, LINE_ORDER, LINE_ROOTS, detect_line  # noqa: E402

LINE_SCRIPTS = {
    "novel": "skills/novel-craft/scripts/progress.py",
    "n2d": "skills/n2d-progress/scan.py",
    "song": "skills/song-craft/scripts/progress.py",
    "mv": "skills/mv-craft/scripts/progress.py",
    "ad": "skills/ad-craft/scripts/progress.py",
}

LIMIT_COMPATIBLE_LINES = {"novel", "song", "mv"}


def repo_path(*parts):
    return os.path.join(REPO, *parts)


def script_path(line):
    return repo_path(*LINE_SCRIPTS[line].split("/"))


def relpath(path):
    try:
        return os.path.relpath(path, REPO)
    except ValueError:
        return path


def is_within(path, parent):
    path = os.path.abspath(path)
    parent = os.path.abspath(parent)
    try:
        return os.path.commonpath([path, parent]) == parent
    except ValueError:
        return False


def resolve_project_root(path, line, max_external_ascents=8):
    """Return the nearest ancestor project root for a line context."""
    current = os.path.abspath(path)
    if os.path.isfile(current):
        current = os.path.dirname(current)
    if not os.path.exists(current):
        return None

    line_root = repo_path(LINE_ROOTS[line])
    stop_at = os.path.abspath(line_root) if is_within(current, line_root) else None
    external_ascents = 0

    while True:
        if stop_at and current == stop_at:
            return None
        if os.path.isfile(os.path.join(current, "_进度.md")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        if stop_at is None:
            external_ascents += 1
            if external_ascents > max_external_ascents:
                return None
        current = parent


def projects_for_line(line):
    base = repo_path(LINE_ROOTS[line])
    if not os.path.isdir(base):
        return []
    projects = []
    for name in sorted(os.listdir(base)):
        if name.startswith("."):
            continue
        root = os.path.join(base, name)
        if os.path.isdir(root) and os.path.isfile(os.path.join(root, "_进度.md")):
            projects.append(root)
    return projects


def print_missing(line):
    print(f"[err] {LINE_LABELS[line]} 产线尚未提供可调用的进度脚本：{relpath(script_path(line))}", file=sys.stderr)
    print("      请直接读取该项目的 `_进度.md`，或先补对应产线 progress 脚本。", file=sys.stderr)
    return 2


def line_args(line, limit):
    if limit is not None and line in LIMIT_COMPATIBLE_LINES:
        return ["--limit", str(limit)]
    return []


def run_line(line, root, limit=None):
    script = script_path(line)
    if not os.path.isfile(script):
        return print_missing(line)
    cmd = [sys.executable, script, os.path.abspath(root)] + line_args(line, limit)
    # 子进程直写同一 fd；先 flush 父进程缓冲，否则管道下标题/分隔线全部乱序。
    sys.stdout.flush()
    result = subprocess.run(cmd, check=False)
    return result.returncode


def aggregate(lines, limit=None):
    print("# progress — 全仓库只读扫描")
    print("")
    failures = 0
    found = 0
    for line in lines:
        projects = projects_for_line(line)
        if not projects:
            continue
        found += len(projects)
        print(f"## {LINE_LABELS[line]} ({len(projects)})")
        if not os.path.isfile(script_path(line)):
            failures += len(projects)
            print_missing(line)
            print("")
            continue
        for project in projects:
            print("")
            print(f"--- {relpath(project)} ---")
            rc = run_line(line, project, limit)
            if rc:
                failures += 1
                print(f"[warn] {relpath(project)} 进度扫描返回 {rc}")
        print("")
    if not found:
        print("[提示] 未发现带 `_进度.md` 的作品目录。")
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="智能进度分发：只读探测并调用各产线 progress")
    ap.add_argument("project_root", nargs="?", default=".", help="作品根、产线根或仓库根；默认当前目录")
    ap.add_argument("--limit", type=int, default=None, help="限制底层脚本展示的后续待办数量（仅支持 novel/song/mv）")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    detected = detect_line(root, REPO)

    if detected == "repo":
        return aggregate(LINE_ORDER, args.limit)
    if detected.endswith(":root"):
        line = detected.split(":", 1)[0]
        return aggregate((line,), args.limit)
    if detected in LINE_SCRIPTS:
        project_root = resolve_project_root(root, detected)
        if project_root is None:
            print(f"[err] 找不到作品根：{root}", file=sys.stderr)
            return 2
        print(f"[dispatch] 检测到 {LINE_LABELS[detected]} 产线上下文 → {relpath(script_path(detected))}")
        print("")
        return run_line(detected, project_root, args.limit)

    print("[提示] 无法识别产线上下文。")
    print("请提供作品根目录，例如：")
    print("  python3 skills/progress/scripts/dispatch.py 写小说/某书")
    print("  python3 skills/progress/scripts/dispatch.py 制漫剧/某剧")
    print("  python3 skills/progress/scripts/dispatch.py 写歌/某歌")
    print("  python3 skills/progress/scripts/dispatch.py 制MV/某歌")
    print("  python3 skills/progress/scripts/dispatch.py 拍广告/某项目")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
