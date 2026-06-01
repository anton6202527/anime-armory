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
