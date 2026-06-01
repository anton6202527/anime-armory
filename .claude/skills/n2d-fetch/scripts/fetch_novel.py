#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_novel.py — 给定章节目录页 URL，联网抓取公版小说全文，输出 .txt + .docx。
（合法性：默认只抓公版/开放授权来源；付费墙站直接拒抓。详见 ../SKILL.md 与 ../references/sources.md。）

用法:
    python3 fetch_novel.py <目录页URL> --name "<书名>" [--out <作品根>]

选项:
    --name 书名      输出文件名与标题（必填）
    --out  作品根    输出到 <作品根>/小说/；缺省 = artifacts/<书名>/
    --source auto|gutenberg|wikisource|generic   抓取引擎（默认 auto 探测）
    --i-have-rights  对非公版/通用兜底 URL 声明你有权使用（跳过合法性确认）

依赖: requests beautifulsoup4 trafilatura python-docx
"""
import argparse
import os
import re
import sys

# 依赖：import 名 -> pip 安装名
_DEP_INSTALL_NAME = {
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "trafilatura": "trafilatura",
    "docx": "python-docx",
}


def _detect_have():
    have = set()
    for mod in _DEP_INSTALL_NAME:
        try:
            __import__(mod)
            have.add(mod)
        except ImportError:
            pass
    return have


def missing_deps(have=None):
    """返回缺失依赖的 pip 安装名列表（按 _DEP_INSTALL_NAME 顺序）。"""
    if have is None:
        have = _detect_have()
    return [install for mod, install in _DEP_INSTALL_NAME.items() if mod not in have]
