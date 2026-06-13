#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared text processing utilities for production and writing pipelines."""

import re

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
QUOTE_PAIRS = [("「", "」"), ("“", "”"), ("‘", "’"), ("『", "』"), ("\"", "\""), ("'", "'")]


def cjk_count(text: str) -> int:
    """Count CJK (Chinese, Japanese, Korean) characters in text."""
    if not text:
        return 0
    return len(CJK_RE.findall(text))


def strip_quotes(text: str) -> str:
    """Remove content inside paired quotes, returning only outside text."""
    out = text
    for a, b in QUOTE_PAIRS:
        if a == b:
            out = re.sub(re.escape(a) + r".*?" + re.escape(b), "", out)
        else:
            out = re.sub(re.escape(a) + r"[^" + re.escape(b) + r"]*" + re.escape(b), "", out)
    return out


def clean_punctuation(text: str) -> str:
    """Clean common punctuation mess, e.g. redundant commas or `。，`."""
    if not text:
        return ""
    text = re.sub(r"([。！？…—；：、》」』）])[，,]", r"\1", text)
    text = re.sub(r"[，,]{2,}", "，", text)
    text = re.sub(r"^\s*[，,、]+(?=.)", "", text, flags=re.M)
    return text.strip()


def is_placeholder(text: str) -> bool:
    """Detect common placeholder tokens."""
    if not text:
        return False
    return bool(re.search(r"待精修|占位|placeholder|TODO|（待", text))
