#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smart Update Dispatcher.

n2d has a full skill snapshot + bounded rebuild planner. For selective
image/video refresh, update delegates to the media planner for n2d/mv/ad and
emits explicit no-op plans for text/audio-only lines.
"""

import argparse
import os
import re
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

COMMON = os.path.join(REPO, "skills", "update", "_lib")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from line_detect import LINE_LABELS, LINE_ROOTS, detect_line  # noqa: E402

N2D_UPDATE = os.path.join(REPO, "skills", "n2d-update", "scripts", "update_plan.py")
MEDIA_REFRESH = os.path.join(REPO, "skills", "update", "scripts", "media_refresh.py")


def relpath(path):
    try:
        return os.path.relpath(path, REPO)
    except ValueError:
        return path


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
    # 集号是位置参数（如 第2集），--all 是显式全量；其余 --flag 不算选集。
    return any(a == "--all" or not a.startswith("-") for a in extra_args)


EPISODE_RE = re.compile(r"^(第\d+集|\d+)$")


def split_target(project_root, extra_args):
    """允许 `dispatch.py check 第1集`：首参是集号且不是已存在目录时，root 退回当前目录。"""
    if EPISODE_RE.match(project_root) and not os.path.isdir(project_root):
        return ".", [project_root] + list(extra_args)
    return project_root, list(extra_args)


def run_n2d(cmd_name, root, extra_args):
    if not os.path.isfile(N2D_UPDATE):
        print(f"[err] 找不到 n2d-update 脚本：{relpath(N2D_UPDATE)}", file=sys.stderr)
        return 2
    forwarded = list(extra_args)
    if not has_episode_selector(forwarded):
        forwarded.append("--all")
    cmd = [sys.executable, N2D_UPDATE, cmd_name, os.path.abspath(root)] + forwarded
    # 子进程直写同一 fd；先 flush 父进程缓冲，否则管道下标题/分隔线全部乱序。
    sys.stdout.flush()
    result = subprocess.run(cmd, check=False)
    return result.returncode


def run_media(root, line, extra_args):
    if not os.path.isfile(MEDIA_REFRESH):
        print(f"[err] 找不到 update media 脚本：{relpath(MEDIA_REFRESH)}", file=sys.stderr)
        return 2
    cmd = [sys.executable, MEDIA_REFRESH, os.path.abspath(root), "--line", line] + list(extra_args)
    sys.stdout.flush()
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
        print("拍广告线目前没有自动化更新嗅探；广告法、品牌定妆与交付规格变化时建议从 ad-script 人工复核，或跑 ad-review 做投放前质检。")
    else:
        print("该上下文目前暂未接入自动化更新嗅探脚本。")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="智能更新分发：n2d 快照重制 + n2d/mv/ad 媒体选择性刷新")
    ap.add_argument("cmd", choices=["check", "record", "media"], help="执行的操作")
    ap.add_argument("project_root", nargs="?", default=".", help="作品根、产线根或仓库根；默认当前目录")
    ap.add_argument("cmd_args", nargs=argparse.REMAINDER, help="传递给底层 update 脚本的附加参数")
    args = ap.parse_args(argv)

    target, cmd_args = split_target(args.project_root, args.cmd_args)
    root = os.path.abspath(target)
    detected = detect_line(root, REPO)

    if args.cmd == "media":
        if detected in ("repo", "n2d:root") or detected.endswith(":root"):
            print("[提示] media 选择性刷新计划需要具体作品根，并用 --image/--video/--target 指定少量目标。")
            return 1
        if detected in LINE_ROOTS:
            print(f"[dispatch] 检测到 {LINE_LABELS.get(detected, detected)} 产线上下文 → {relpath(MEDIA_REFRESH)}")
            print("")
            return run_media(root, detected, cmd_args)
        print("[提示] 无法识别产线上下文，media 计划未生成。")
        return 1

    if detected == "repo":
        return aggregate_n2d(args.cmd, cmd_args)
    if detected == "n2d:root":
        return aggregate_n2d(args.cmd, cmd_args)
    if detected == "n2d":
        print(f"[dispatch] 检测到 {LINE_LABELS['n2d']} 产线上下文 → {relpath(N2D_UPDATE)}")
        print("")
        return run_n2d(args.cmd, root, cmd_args)
    if detected.endswith(":root"):
        return unsupported(detected.split(":", 1)[0])
    if detected in LINE_ROOTS:
        return unsupported(detected)

    print("[提示] 无法识别产线上下文。")
    print("当前完整支持：`制漫剧/<剧名>` 或仓库根下的 n2d 全剧扫描。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
