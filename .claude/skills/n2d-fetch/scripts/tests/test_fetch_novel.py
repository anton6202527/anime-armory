# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fetch_novel as fn


def test_missing_deps_returns_pip_hint():
    missing = fn.missing_deps(have={"requests", "bs4"})  # trafilatura & docx absent
    assert "trafilatura" in missing
    assert "python-docx" in missing  # reported by install name, not import name


def test_no_missing_deps_when_all_present():
    have = {"requests", "bs4", "trafilatura", "docx"}
    assert fn.missing_deps(have=have) == []


def test_paywalled_known_sites():
    assert fn.is_paywalled("https://www.qidian.com/book/123/")
    assert fn.is_paywalled("https://fanqienovel.com/page/456")
    assert fn.is_paywalled("https://www.jjwxc.net/onebook.php?novelid=1")


def test_not_paywalled_public_sites():
    assert not fn.is_paywalled("https://zh.wikisource.org/wiki/紅樓夢")
    assert not fn.is_paywalled("https://www.gutenberg.org/ebooks/1342")


def test_detect_source():
    assert fn.detect_source("https://zh.wikisource.org/wiki/紅樓夢") == "wikisource"
    assert fn.detect_source("https://www.gutenberg.org/ebooks/1342") == "gutenberg"
    assert fn.detect_source("https://gutendex.com/books/1342") == "gutenberg"
    assert fn.detect_source("https://some-random-site.example/book/1") == "generic"


def test_assemble_text_uses_chapter_headings():
    chapters = [
        {"title": "楔子", "body": "第一段。\n第二段。"},
        {"title": "初遇", "body": "正文内容。"},
    ]
    text = fn.assemble_text(chapters)
    lines = text.splitlines()
    assert "第1章 楔子" in lines
    assert "第2章 初遇" in lines
    # 章节标题必须能被 split_novel.py 的 CHAPTER_RE 命中
    chapter_re = __import__("re").compile(
        r"^\s*第\s*[0-9零一二三四五六七八九十百千两]+\s*[章回节卷]")
    headings = [ln for ln in lines if chapter_re.match(ln)]
    assert len(headings) == 2


def test_assemble_text_blank_line_after_heading():
    text = fn.assemble_text([{"title": "x", "body": "body"}])
    assert "第1章 x\n\nbody" in text
