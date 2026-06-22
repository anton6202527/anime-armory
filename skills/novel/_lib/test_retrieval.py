# -*- coding: utf-8 -*-
"""retrieval 纯函数单测。
cd skills/novel/_lib && python3 -m pytest test_retrieval.py
"""
import os

import retrieval as r


def test_cjk_bigrams_breaks_on_noncjk():
    assert r.cjk_bigrams("断剑") == ["断剑"]
    # 标点处断开，不跨标点
    assert r.cjk_bigrams("断剑，重铸") == ["断剑", "重铸"]
    assert r.cjk_bigrams("abc") == []


def test_doc_freq_counts_documents_not_occurrences():
    df = r.doc_freq([["断剑", "断剑", "重铸"], ["断剑", "封印"]])
    assert df["断剑"] == 2      # 出现在 2 个文档
    assert df["重铸"] == 1


def test_idf_nonnegative():
    df = r.doc_freq([["a"], ["a"], ["b"]])
    idf = r.idf(df, 3)
    assert all(v >= 0 for v in idf.values())


def test_rank_prefers_topically_relevant_chapter():
    corpus = [
        (5, "沈念在山洞里捡到一柄断剑，断剑通体玄铁，刻着古老封印。"),
        (12, "今日天气晴朗，众人在城中闲逛，买了些糕点。"),
        (40, "关于那柄断剑的封印之谜，始终萦绕心头。"),
    ]
    ranked = r.rank("断剑 封印 玄铁", corpus, k=2)
    ids = [cid for cid, _ in ranked]
    assert 5 in ids and 40 in ids   # 与断剑/封印相关的章排前
    assert 12 not in ids            # 无关章不入选


def test_rank_empty_query_or_corpus():
    assert r.rank("", [(1, "断剑")], k=3) == []
    assert r.rank("断剑", [], k=3) == []


def test_bm25_zero_when_no_overlap():
    idf = {"断剑": 1.0}
    assert r.bm25_score(["断剑"], r.cjk_bigrams("天气晴朗"), idf, 5) == 0.0


def test_best_excerpt_locates_dense_region():
    text = "前面都是无关的日常描写。" * 10 + "断剑的封印在此刻松动了。" + "后面又是无关内容。" * 5
    ex = r.best_excerpt("断剑 封印", text, span=30)
    assert "断剑" in ex and "封印" in ex


def test_cli_default_query_uses_chapter_outline(tmp_path, capsys):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    with open(os.path.join(root, "设定", "章纲.md"), "w", encoding="utf-8") as f:
        f.write("# 章纲\n- 第 05 章 《旧剑回响》 — 断剑封印再次松动\n")
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("沈念在山洞里捡到一柄断剑，断剑通体玄铁，刻着古老封印。")

    assert r.main([root, "--chapter", "5", "--k", "1"]) == 0
    out = capsys.readouterr().out
    assert "第01章" in out
