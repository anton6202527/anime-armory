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

LINE_ORDER = ("novel", "n2d", "song", "mv", "ad")
LINE_ROOTS = {
    "novel": "写小说",
    "n2d": "制漫剧",
    "song": "写歌",
    "mv": "制MV",
    "ad": "拍广告",
}
LINE_LABELS = {
    "novel": "写小说",
    "n2d": "制漫剧",
    "song": "写歌",
    "mv": "制MV",
    "ad": "拍广告",
}
LINE_SCRIPTS = {
    "novel": "skills/novel-craft/scripts/progress.py",
    "n2d": "skills/n2d-progress/scan.py",
    "song": "skills/song-craft/scripts/progress.py",
    "mv": "skills/mv-craft/scripts/progress.py",
    "ad": "skills/ad/scripts/route.py",
}


def repo_path(*parts):
    return os.path.join(REPO, *parts)


def script_path(line):
    return repo_path(*LINE_SCRIPTS[line].split("/"))


def relpath(path):
    try:
        return os.path.relpath(path, REPO)
    except ValueError:
        return path


def path_parts(path):
    rel = relpath(os.path.abspath(path))
    if rel == "." or rel.startswith(".."):
        return []
    return rel.split(os.sep)


def is_repo_root(root):
    return os.path.abspath(root) == REPO


def detect_line(root):
    root = os.path.abspath(root)
    if is_repo_root(root):
        return "repo"

    parts = path_parts(root)
    if parts:
        first = parts[0]
        for line, line_root in LINE_ROOTS.items():
            if first == line_root:
                return line if len(parts) > 1 else f"{line}:root"

    # Fallback for callers outside the repo or symlinked project roots.
    markers = (
        ("ad", os.path.join(root, "需求", "brief.json")),
        ("song", os.path.join(root, "词", "lyrics.md")),
        ("mv", os.path.join(root, "视觉蓝图.md")),
        ("mv", os.path.join(root, "节拍", "beatgrid.json")),
        ("novel", os.path.join(root, "章节")),
    )
    for line, marker in markers:
        if os.path.exists(marker):
            return line
    if os.path.isfile(os.path.join(root, "_进度.md")) and os.path.isdir(os.path.join(root, "小说")):
        return "n2d"
    return "unknown"


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
    script = script_path(line)
    print(f"[提示] {LINE_LABELS[line]} 产线尚未提供可调用的进度脚本：{relpath(script)}")
    print("       请直接读取该项目的 `_进度.md`，或先补对应产线 progress 脚本。")
    return 0


def run_line(line, root, extra_args):
    script = script_path(line)
    if not os.path.isfile(script):
        return print_missing(line)
    cmd = [sys.executable, script, os.path.abspath(root)] + list(extra_args)
    result = subprocess.run(cmd, check=False)
    return result.returncode


def aggregate(lines, extra_args):
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
        for project in projects:
            print("")
            print(f"--- {relpath(project)} ---")
            rc = run_line(line, project, extra_args)
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
    ap.add_argument("cmd_args", nargs=argparse.REMAINDER, help="传递给底层只读 progress 脚本的附加参数")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    detected = detect_line(root)

    if detected == "repo":
        return aggregate(LINE_ORDER, args.cmd_args)
    if detected.endswith(":root"):
        line = detected.split(":", 1)[0]
        return aggregate((line,), args.cmd_args)
    if detected in LINE_SCRIPTS:
        if not os.path.isdir(root):
            print(f"[err] 找不到作品根：{root}", file=sys.stderr)
            return 2
        print(f"[dispatch] 检测到 {LINE_LABELS[detected]} 产线上下文 → {relpath(script_path(detected))}")
        print("")
        return run_line(detected, root, args.cmd_args)

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
