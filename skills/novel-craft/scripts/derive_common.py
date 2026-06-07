#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
derive_common.py — novel-* 派生类 init 脚本的共享工具（单一真值源）。

被 create / spinoff / rewrite / expand / condense / continue 的 init_project.py 共用，
消除各脚本里逐份复制的 docx→txt / 版权判定，并统一落 `_设置.md`（_偏好约定 选择点存储）。

各 init 顶部按相对路径引入：
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "novel-craft", "scripts"))
    from derive_common import docx_to_txt, detect_rights_status, write_settings
"""
import os
import sys


def docx_to_txt(docx_path, out_txt_path):
    """.docx 段落 → 纯文本（每段一行）。"""
    try:
        from docx import Document
    except ImportError:
        print("[err] 缺依赖：pip install python-docx", file=sys.stderr)
        sys.exit(2)
    doc = Document(docx_path)
    with open(out_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(p.text for p in doc.paragraphs))


def detect_rights_status(novel_txt_path, i_have_rights):
    """读 txt 头部 provenance 注释块判版权（novel-fetch 抓的带 `# copyright: ...`）。
    返回 'public-domain' / 'user-declared' / 'unknown'。"""
    try:
        with open(novel_txt_path, "r", encoding="utf-8") as f:
            head = f.read(2000)
    except FileNotFoundError:
        return "unknown"
    for line in head.splitlines():
        if not line.startswith("#"):
            break
        if "copyright" in line.lower():
            val = line.split(":", 1)[1].strip().lower() if ":" in line else ""
            if any(k in val for k in ("public", "公版", "gutenberg", "wikisource", "维基文库")):
                return "public-domain"
            if any(k in val for k in ("用户声明", "user-declared")):
                return "user-declared"
    return "user-declared" if i_have_rights else "unknown"


def write_settings(out_root, fields, *, note=None):
    """落 `<作品根>/_设置.md` —— 本作私有选择点（_偏好约定 的 per-work 存储）。

    fields: 有序 dict {中文标签: 值}（如 目标平台/权利来源/输出格式/篇幅档）。
    init 时按 CLI/默认值落定一次，同项目后续沉默沿用；改了在此更新。
    """
    lines = ["# 设置 — 本作私有选择点（_偏好约定）", ""]
    if note:
        lines += [f"> {note}", ""]
    for k, v in fields.items():
        shown = v if v not in (None, "", []) else "（未定）"
        lines.append(f"- **{k}**：{shown}")
    lines += [
        "",
        "> 这些值由 init 按 CLI 参数/全局默认落定；同项目后续**沉默沿用**，"
        "改了在此更新。合规/不可逆/花钱多的点每次仍向用户确认。",
    ]
    with open(os.path.join(out_root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
