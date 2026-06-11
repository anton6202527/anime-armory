#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smart Update Dispatcher.

Currently only the n2d line has a full skill snapshot + bounded rebuild planner.
Other lines are detected explicitly and receive a friendly no-op message.
"""

import argparse
import os
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

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
N2D_UPDATE = os.path.join(REPO, "skills", "n2d-update", "scripts", "update_plan.py")


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


def detect_line(root):
    root = os.path.abspath(root)
    if root == REPO:
        return "repo"

    parts = path_parts(root)
    if parts:
        first = parts[0]
        for line, line_root in LINE_ROOTS.items():
            if first == line_root:
                return line if len(parts) > 1 else f"{line}:root"

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


def n2d_projects():
    base = os.path.join(REPO, LINE_ROOTS["n2d"])
    if not os.path.isdir(base):
        return []
    projects = []
    for name in sorted(os.listdir(base)):
        root = os.path.join(base, name)
        if os.path.isdir(root) and os.path.isfile(os.path.join(root, "_进度.md")):
            projects.append(root)
    return projects


def has_episode_selector(extra_args):
    return bool(extra_args)


def run_n2d(cmd_name, root, extra_args):
    if not os.path.isfile(N2D_UPDATE):
        print(f"[err] 找不到 n2d-update 脚本：{relpath(N2D_UPDATE)}", file=sys.stderr)
        return 2
    forwarded = list(extra_args)
    if not has_episode_selector(forwarded):
        forwarded.append("--all")
    cmd = [sys.executable, N2D_UPDATE, cmd_name, os.path.abspath(root)] + forwarded
    result = subprocess.run(cmd, check=False)
    return result.returncode


def aggregate_n2d(cmd_name, extra_args):
    projects = n2d_projects()
    if not projects:
        print("[提示] 未发现 `制漫剧/*/_进度.md` 项目。")
        return 0
    print(f"# update — n2d 全仓库扫描 ({len(projects)})")
    failures = 0
    for project in projects:
        print("")
        print(f"--- {relpath(project)} ---")
        rc = run_n2d(cmd_name, project, extra_args)
        if rc:
            failures += 1
            print(f"[warn] {relpath(project)} update 返回 {rc}")
    return 1 if failures else 0


def unsupported(line):
    print(f"[提示] 检测到 {LINE_LABELS.get(line, line)} 产线上下文。")
    if line == "novel":
        print("小说线目前没有 skill 快照→最小重制计划工具；建议先跑 `novel-review` 流程自审或看 git diff。")
    elif line == "song":
        print("写歌线目前没有自动化更新嗅探；歌曲成品、take manifest 与授权记录建议人工复核。")
    elif line == "mv":
        print("制MV线目前没有自动化更新嗅探；涉及出图/出视频模板变化时建议从 mv-plan/mv-review 人工定位重跑范围。")
    elif line == "ad":
        print("拍广告线目前没有自动化更新嗅探；广告法、品牌定妆与交付规格变化时建议从 ad-script/ad-review 人工复核。")
    else:
        print("该上下文目前暂未接入自动化更新嗅探脚本。")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="智能更新分发：n2d 完整支持，其它产线友好提示")
    ap.add_argument("cmd", choices=["check", "record"], help="执行的操作")
    ap.add_argument("project_root", nargs="?", default=".", help="作品根、产线根或仓库根；默认当前目录")
    ap.add_argument("cmd_args", nargs=argparse.REMAINDER, help="传递给底层 update 脚本的附加参数")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    detected = detect_line(root)

    if detected == "repo":
        return aggregate_n2d(args.cmd, args.cmd_args)
    if detected == "n2d:root":
        return aggregate_n2d(args.cmd, args.cmd_args)
    if detected == "n2d":
        print(f"[dispatch] 检测到 {LINE_LABELS['n2d']} 产线上下文 → {relpath(N2D_UPDATE)}")
        print("")
        return run_n2d(args.cmd, root, args.cmd_args)
    if detected.endswith(":root"):
        return unsupported(detected.split(":", 1)[0])
    if detected in LINE_ROOTS:
        return unsupported(detected)

    print("[提示] 无法识别产线上下文。")
    print("当前完整支持：`制漫剧/<剧名>` 或仓库根下的 n2d 全剧扫描。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
