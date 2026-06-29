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


def test_rank_from_index_matches_token_rank():
    # 同一语料：基于缓存 tf 的排序必须与全量 token 排序逐位一致
    corpus = [
        (5, "沈念在山洞里捡到一柄断剑，断剑通体玄铁，刻着古老封印。"),
        (12, "今日天气晴朗，众人在城中闲逛，买了些糕点。"),
        (40, "关于那柄断剑的封印之谜，始终萦绕心头。"),
    ]
    from collections import Counter
    indexed = []
    for cid, text in corpus:
        toks = r.cjk_bigrams(text)
        indexed.append((cid, dict(Counter(toks)), len(toks)))
    q = "断剑 封印 玄铁"
    assert r.rank_from_index(q, indexed, k=3) == r.rank(q, corpus, k=3)


def test_build_index_is_incremental(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    p1 = os.path.join(root, "章节", "第01章.md")
    with open(p1, "w", encoding="utf-8") as f:
        f.write("沈念捡到断剑，刻着封印。")
    idx1 = r.build_or_update_index(root)
    h1 = idx1["chapters"]["1"]["hash"]
    # 未改动 → 复用同 hash
    idx2 = r.build_or_update_index(root)
    assert idx2["chapters"]["1"]["hash"] == h1
    # 改动 → hash 更新
    with open(p1, "w", encoding="utf-8") as f:
        f.write("沈念把断剑重铸，封印彻底解开了，玄铁化光。")
    idx3 = r.build_or_update_index(root)
    assert idx3["chapters"]["1"]["hash"] != h1
    # 删除 → 索引剔除
    os.remove(p1)
    idx4 = r.build_or_update_index(root)
    assert "1" not in idx4["chapters"]


def test_relevant_chapters_uses_index_and_matches_scan(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    data = {
        1: "沈念在山洞里捡到一柄断剑，断剑通体玄铁，刻着古老封印。",
        2: "今日天气晴朗，众人在城中闲逛，买了些糕点。",
        3: "关于那柄断剑的封印之谜，始终萦绕心头。",
        4: "市集喧闹，叫卖声此起彼伏。",
    }
    for cid, text in data.items():
        with open(os.path.join(root, "章节", f"第{cid:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(text)
    # 第8章、window=3 → 看第1-4章；索引路径与全量扫描结果一致
    via_index = r.relevant_chapters(root, 8, "断剑 封印", k=2, window=3)
    via_scan = r._relevant_chapters_scan(root, 8, "断剑 封印", k=2, window=3)
    assert [h["chapter"] for h in via_index] == [h["chapter"] for h in via_scan]
    assert os.path.exists(r._index_path(root))  # 索引落盘


def test_cosine_basic():
    assert r.cosine([1, 0], [1, 0]) == 1.0
    assert r.cosine([1, 0], [0, 1]) == 0.0
    assert r.cosine([], [1]) == 0.0
    assert r.cosine([0, 0], [1, 1]) == 0.0


def _fake_embedder(texts):
    # 2 维语义向量：[出现"断剑"次数, 出现"封印"次数]
    return [[t.count("断剑"), t.count("封印")] for t in texts]


def test_semantic_rerank_orders_by_cosine():
    cand = [(1, "全是天气与日常"), (2, "封印封印封印"), (3, "断剑")]
    out = r.semantic_rerank("封印", cand, _fake_embedder, k=3)
    assert out[0][0] == 2                  # 封印 最相关排首
    assert out[0][1] > out[1][1]           # 首位分数严格高于次位（无关章 cosine=0）


def test_semantic_rerank_degrades_on_bad_embedder():
    cand = [(1, "封印")]
    assert r.semantic_rerank("封印", cand, lambda ts: (_ for _ in ()).throw(RuntimeError()), k=2) == []
    assert r.semantic_rerank("封印", cand, lambda ts: [[1.0]], k=2) == []  # 形状不符（应=len+1）


def test_relevant_chapters_uses_injected_embedder(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    data = {
        1: "断剑断剑断剑，全篇都在讲断剑这把武器。",  # BM25 对 query"断剑"最高
        2: "封印封印封印封印，讲的是封印之力。",       # 语义 embedder 对 query 偏好这里
        3: "市集喧闹与日常。",
        4: "另一段无关的日常。",
    }
    for cid, text in data.items():
        with open(os.path.join(root, "章节", f"第{cid:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(text)
    # 注入 fake embedder，query 偏"封印"→ 语义重排应把第2章顶到首位（而非 BM25 的第1章）
    hits = r.relevant_chapters(root, 8, "封印", k=2, window=3, embedder=_fake_embedder)
    assert hits[0]["chapter"] == 2


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


def test_score_golden_cases_recall_mrr():
    import retrieval
    # ranker 返回固定 result_ids，验证 recall@k / MRR 算术
    cases = [
        {"query": "a", "expected_ids": ["2"]},   # 命中在第2位 → rr=1/2
        {"query": "b", "expected_id": "9"},       # 不命中
    ]
    ranker = lambda q, k: ["1", "2", "3"]
    out = retrieval.score_golden_cases(cases, ranker, top_k=3)
    assert out["case_count"] == 2 and out["hit_count"] == 1
    assert out["recall_at_k"] == 0.5
    assert abs(out["mrr"] - 0.25) < 1e-9   # (0.5 + 0)/2
    assert len(out["failures"]) == 1
