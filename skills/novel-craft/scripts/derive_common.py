#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
derive_common.py — novel-* 派生类 init 脚本的共享工具（单一真值源）。

被 create / spinoff / rewrite / expand / condense / continue 的 init_project.py 共用，
消除各脚本里逐份复制的 docx→txt / 版权判定，并统一落 `_设置.md`（skills/novel-craft/references/选择点与偏好.md 选择点存储）。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "novel", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from settings import write_settings as _write_settings  # noqa: E402  vendored 进 novel/_lib

from contract import rights_metadata  # noqa: E402


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


def build_rights_metadata(
    rights_status,
    *,
    i_have_rights=False,
    source_type="",
    source_url="",
    rights_jurisdiction=None,
    distribution_regions=None,
):
    return rights_metadata(
        rights_status,
        source_type=source_type,
        source_url=source_url,
        rights_declared=i_have_rights or rights_status in {"original", "user-owned", "user-declared"},
        rights_jurisdiction=rights_jurisdiction,
        distribution_regions=distribution_regions,
    )


def write_settings(out_root, fields, *, note=None):
    """落 `<作品根>/_设置.md` —— 本作私有选择点（skills/novel-craft/references/选择点与偏好.md 的 per-work 存储）。

    fields: 有序 dict {中文标签: 值}（如 目标平台/权利来源/输出格式/篇幅档）。
    init 时按 CLI/默认值落定一次，同项目后续沉默沿用；改了在此更新。
    """
    # 使用 common/settings.py 的单一真值源实现，保持 Novel 线路的 bold_keys=True
    _write_settings(out_root, fields, note=note, bold_keys=True)
