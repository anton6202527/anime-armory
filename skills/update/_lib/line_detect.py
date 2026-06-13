#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产线上下文探测（公共稳定基建）。

progress / update 两个公共 dispatcher 共用：给一个目录，判断它属于哪条生产线
（novel/n2d/song/mv/ad）、是作品根还是产线根还是仓库根。新增产线时只改这里。
"""

import os

LINE_ORDER = ("novel", "n2d", "song", "mv", "ad")

LINE_ROOTS = {
    "novel": "写小说",
    "n2d": "制漫剧",
    "song": "写歌",
    "mv": "制MV",
    "ad": "拍广告",
}

LINE_LABELS = dict(LINE_ROOTS)

# 仓库外 / symlink 项目的兜底：按各线特征文件识别。
MARKERS = (
    ("ad", ("需求", "brief.json")),
    ("song", ("词", "lyrics.md")),
    ("mv", ("视觉蓝图.md",)),
    ("mv", ("节拍", "beatgrid.json")),
    ("novel", ("章节",)),
)

N2D_PROJECT_MARKERS = (
    "小说",
    "脚本",
    "分镜",
    "设定库",
    "出图",
    "出视频",
    "配音",
    "合成",
    "生产数据",
)


def relpath(path, repo):
    try:
        return os.path.relpath(path, repo)
    except ValueError:
        return path


def path_parts(path, repo):
    rel = relpath(os.path.abspath(path), repo)
    if rel == "." or rel.startswith(".."):
        return []
    return rel.split(os.sep)


def detect_line(root, repo):
    """返回 "repo" / "<line>" / "<line>:root" / "unknown"。"""
    root = os.path.abspath(root)
    if root == os.path.abspath(repo):
        return "repo"

    parts = path_parts(root, repo)
    if parts:
        first = parts[0]
        for line, line_root in LINE_ROOTS.items():
            if first == line_root:
                return line if len(parts) > 1 else f"{line}:root"

    for line, marker in MARKERS:
        if os.path.exists(os.path.join(root, *marker)):
            return line
    if os.path.isfile(os.path.join(root, "_进度.md")) and any(
        os.path.exists(os.path.join(root, marker)) for marker in N2D_PROJECT_MARKERS
    ):
        return "n2d"
    return "unknown"
