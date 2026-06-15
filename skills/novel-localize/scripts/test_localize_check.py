#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_localize_check.py — 从脚本自身目录运行：
    cd skills/novel-localize/scripts && python -m pytest test_localize_check.py
"""
import json
import os
import tempfile

import localize_check as lc


def _mk_project(src_chapters, tgt_chapters=None, glossary=None, lang="en"):
    root = tempfile.mkdtemp()
    cdir = os.path.join(root, "章节")
    os.makedirs(cdir)
    for n, text in src_chapters.items():
        with open(os.path.join(cdir, f"第{n:02d}章_x.md"), "w", encoding="utf-8") as f:
            f.write(f"# 第{n}章\n\n{text}")
    if tgt_chapters is not None:
        tdir = os.path.join(root, "出海", lang, "章节")
        os.makedirs(tdir)
        for n, text in tgt_chapters.items():
            with open(os.path.join(tdir, f"第{n:02d}章_x.md"), "w", encoding="utf-8") as f:
                f.write(text)
    if glossary is not None:
        gdir = os.path.join(root, "出海", lang)
        os.makedirs(gdir, exist_ok=True)
        with open(os.path.join(gdir, "术语表.json"), "w", encoding="utf-8") as f:
            json.dump(glossary, f, ensure_ascii=False)
    return root


def test_clean_translation_no_flags():
    root = _mk_project(
        {1: "沈念走进大殿。"},
        {1: "Shen Nian walked into the great hall, her steps measured and calm."},
        {"terms": [{"source": "沈念", "target": "Shen Nian", "type": "person"}]},
    )
    rows, summary = lc.check(root, "en")
    assert summary["flagged_chapters"] == []
    assert summary["missing_chapters"] == []


def test_untranslated_cjk_residue_flagged():
    root = _mk_project(
        {1: "沈念走进大殿，她心中一动。"},
        {1: "Shen Nian walked in. 她心中一动，思绪万千，久久不能平复下来。"},
    )
    rows, summary = lc.check(root, "en")
    assert 1 in summary["flagged_chapters"]
    assert any("未译" in f for f in rows[0]["flags"])


def test_unlocalized_term_flagged():
    # 术语表要求 沈念→Shen Nian，但译文仍残留"沈念" → 专名漏锁
    root = _mk_project(
        {1: "沈念冷笑。"},
        {1: "沈念 sneered coldly at the ministers gathered before her throne."},
        {"terms": [{"source": "沈念", "target": "Shen Nian"}]},
    )
    rows, summary = lc.check(root, "en")
    assert rows[0]["unlocalized_terms"] == ["沈念"]
    assert any("术语未本地化" in f for f in rows[0]["flags"])


def test_missing_chapter_reported():
    root = _mk_project({1: "第一章内容。", 2: "第二章内容。"},
                       {1: "Chapter one content here, fully translated."})
    rows, summary = lc.check(root, "en")
    assert summary["missing_chapters"] == [2]
    assert summary["blocking"] >= 1


def test_truncation_short_translation_flagged():
    root = _mk_project(
        {1: "沈念走进大殿，群臣噤声，她环视四周缓缓开口说出那句惊天之言。"},
        {1: "She spoke."},  # 远短于源
    )
    rows, summary = lc.check(root, "en")
    assert any("截断" in f for f in rows[0]["flags"])


def test_cjk_target_lang_skips_residue():
    # 目标语 ja（含汉字）→ 不把残留 CJK 当漏译
    root = _mk_project(
        {1: "沈念走进大殿。"},
        {1: "沈念は大殿に足を踏み入れた。"},
        lang="ja",
    )
    rows, summary = lc.check(root, "ja")
    assert summary["residue_check"] is False
    assert not any("未译" in f for f in rows[0]["flags"])


def test_no_glossary_graceful():
    root = _mk_project({1: "内容。"}, {1: "Content, translated cleanly and at length."})
    rows, summary = lc.check(root, "en")
    assert summary["glossary_terms"] == 0  # 无术语表不报错


def test_main_writes_report():
    root = _mk_project({1: "沈念。"}, {1: "Shen Nian stood there quietly for a long while."})
    import sys
    argv = sys.argv
    sys.argv = ["localize_check.py", root, "--lang", "en"]
    try:
        rc = lc.main()
    finally:
        sys.argv = argv
    assert rc == 0
    report = os.path.join(root, "出海", "en", "localize_report.json")
    data = json.load(open(report, encoding="utf-8"))
    assert data["kind"] == "novel_localize_report"
