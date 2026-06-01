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


def test_write_txt_has_provenance_then_body(tmp_path):
    prov = {"source_url": "https://zh.wikisource.org/wiki/X", "fetched": "2026-06-01",
            "chapters": 2, "chars": 99, "copyright": "公版（中文维基文库）"}
    text = fn.assemble_text([{"title": "楔子", "body": "正文。"}])
    p = tmp_path / "X.txt"
    fn.write_txt(str(p), text, prov)
    content = p.read_text(encoding="utf-8")
    assert content.startswith("#")  # provenance is a comment block
    assert "source_url: https://zh.wikisource.org/wiki/X" in content
    assert "第1章 楔子" in content
    # provenance block sits before the first chapter heading
    assert content.index("source_url") < content.index("第1章")


def test_write_docx_roundtrip(tmp_path):
    import docx
    text = fn.assemble_text([{"title": "楔子", "body": "第一段。"},
                             {"title": "初遇", "body": "第二段。"}])
    prov = {"source_url": "u", "fetched": "2026-06-01", "chapters": 2,
            "chars": 10, "copyright": "公版"}
    p = tmp_path / "X.docx"
    fn.write_docx(str(p), text, prov)
    assert p.exists()
    doc = docx.Document(str(p))
    headings = [para.text for para in doc.paragraphs if para.style.name.startswith("Heading")]
    assert "第1章 楔子" in headings
    assert "第2章 初遇" in headings


def test_extract_body_from_html():
    here = os.path.dirname(__file__)
    html = open(os.path.join(here, "fixtures", "chapter.html"), encoding="utf-8").read()
    body = fn.extract_body(html, url="https://example.test/ch1")
    assert "正文第一段" in body
    assert "正文第二段" in body
    assert "上一章" not in body  # 导航噪声被剔除
    assert "版权所有" not in body


def test_extract_chapter_links_resolves_and_filters():
    here = os.path.dirname(__file__)
    html = open(os.path.join(here, "fixtures", "index.html"), encoding="utf-8").read()
    links = fn.extract_chapter_links(html, base_url="https://example.test/book/1/index.html")
    titles = [t for _, t in links]
    urls = [u for u, _ in links]
    assert titles == ["第一章 开端", "第二章 发展", "第三章 高潮"]
    assert urls[0] == "https://example.test/book/1/ch1.html"  # 相对链接已解析为绝对
    assert all("ch" in u for u in urls)  # 「首页」「关于」等非章节链接被过滤


def test_fetch_generic_with_injected_getter():
    here = os.path.dirname(__file__)
    index = open(os.path.join(here, "fixtures", "index.html"), encoding="utf-8").read()
    chapter = open(os.path.join(here, "fixtures", "chapter.html"), encoding="utf-8").read()

    def fake_get(url):
        return index if url.endswith("index.html") else chapter

    chapters = fn.fetch_generic("https://example.test/book/1/index.html", get=fake_get)
    assert len(chapters) == 3
    assert chapters[0]["title"] == "第一章 开端"
    assert "正文第一段" in chapters[0]["body"]
