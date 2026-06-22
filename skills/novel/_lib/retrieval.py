#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retrieval.py — 跨窗口语义检索（长程一致性的检索增强 · 纯标准库）

为什么：写章上下文此前只喂「固定章纲切片 + 前 3 章窗口 + 账本摘录」。写到第 230 章要用到第 47 章
埋的细节时，固定窗口够不着——这正是 LLM 长程依赖的软肋（SCORE/知识图谱实时检索都在解这条）。
本模块做**确定性词面检索**（无需模型/向量库）：用本章计划要写的内容当 query，在**窗口之外的所有
旧章**里按 BM25 相关度召回最相关的 K 章，注入写作包，让作者/AI 写新章时"想得起"久远的相关旧章。

中文分词不依赖 jieba：用 **CJK 字符 bigram** 作 term（与 semantic_continuity 的 bigram 重叠同源），
BM25 打分。纯函数（bigram/idf/bm25/rank）带 pytest；IO 包装 relevant_chapters 读 章节/ 目录。

  python3 retrieval.py <作品根> --chapter 230 [--k 3] [--window 3]
"""
import os
import re
import sys
import glob
import math
import argparse
from collections import Counter

WINDOW_DEFAULT = 3       # 紧邻前 N 章已在写作包"上一章承接"里，检索只看更早的章（避免重复）
TOPK_DEFAULT = 3
_CJK_RE = re.compile(r"[一-鿿]")
_CHAPTER_LINE_RE = re.compile(
    r"第\s*0*(\d+)\s*章(?:\s*[《「\"]?([^—\n》」\"]+)[》」\"]?)?\s*(?:[—:：-]\s*(.*))?"
)


# ---------- 纯函数（无依赖 · pytest 覆盖） ----------

def cjk_bigrams(text):
    """文本 → CJK 字符 bigram 列表（非汉字处断开，不跨标点成 bigram）。纯函数·可测。"""
    out = []
    run = []
    for ch in text or "":
        if _CJK_RE.match(ch):
            run.append(ch)
        else:
            for i in range(len(run) - 1):
                out.append(run[i] + run[i + 1])
            run = []
    for i in range(len(run) - 1):
        out.append(run[i] + run[i + 1])
    return out


def doc_freq(corpus_tokens):
    """[token-list,...] → {term: 出现该 term 的文档数}。纯函数·可测。"""
    df = Counter()
    for toks in corpus_tokens:
        for t in set(toks):
            df[t] += 1
    return df


def idf(df, n_docs):
    """BM25 idf（带 +0.5 平滑，且下限 0 不为负）。纯函数·可测。"""
    return {t: max(0.0, math.log(1 + (n_docs - n + 0.5) / (n + 0.5))) for t, n in df.items()}


def bm25_score(query_tokens, doc_tokens, idf_map, avg_len, k1=1.5, b=0.75):
    """单文档 BM25 相关度。纯函数·可测。"""
    if not doc_tokens:
        return 0.0
    tf = Counter(doc_tokens)
    dl = len(doc_tokens)
    score = 0.0
    for t in set(query_tokens):
        f = tf.get(t, 0)
        if not f:
            continue
        w = idf_map.get(t, 0.0)
        score += w * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / (avg_len or 1)))
    return score


def rank(query_text, corpus, k=TOPK_DEFAULT, min_score=0.0):
    """query + corpus=[(id,text)] → 相关度 top-k [(id, score)]（降序，过滤 ≤min_score）。纯函数·可测。"""
    docs = [(cid, cjk_bigrams(text)) for cid, text in corpus]
    docs = [(cid, toks) for cid, toks in docs if toks]
    if not docs:
        return []
    df = doc_freq([toks for _, toks in docs])
    idf_map = idf(df, len(docs))
    avg = sum(len(toks) for _, toks in docs) / len(docs)
    q = cjk_bigrams(query_text)
    if not q:
        return []
    scored = [(cid, bm25_score(q, toks, idf_map, avg)) for cid, toks in docs]
    scored = [(c, round(s, 4)) for c, s in scored if s > min_score]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:k]


def best_excerpt(query_text, text, span=180):
    """在 text 里定位与 query bigram 命中最密的位置，截一段 ~span 字摘要。纯函数·可测。"""
    if not text:
        return ""
    qset = set(cjk_bigrams(query_text))
    if not qset:
        return text[:span]
    best_pos, best_hits = 0, -1
    step = max(1, span // 3)
    for start in range(0, max(1, len(text) - span + 1), step):
        window = text[start:start + span]
        hits = sum(1 for bg in set(cjk_bigrams(window)) if bg in qset)
        if hits > best_hits:
            best_hits, best_pos = hits, start
    return text[best_pos:best_pos + span].strip()


# ---------- IO ----------

def _chapter_num(path):
    m = re.search(r"(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else None


def load_prior_chapters(root, chapter, window=WINDOW_DEFAULT):
    """读 章节/ 下章号 < (chapter - window) 的旧章 → [(id, text)]（窗口内的近章已在写作包里，排除）。"""
    out = []
    cutoff = chapter - window
    for path in sorted(glob.glob(os.path.join(root, "章节", "*.md"))):
        cid = _chapter_num(path)
        if cid is None or cid >= cutoff or cid < 1:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                out.append((cid, f.read()))
        except Exception:
            continue
    return out


def default_query(root, chapter):
    """从设定/章纲.md 取本章条目作为 CLI 默认 query；缺条目时返回空串。"""
    outline_path = os.path.join(root, "设定", "章纲.md")
    try:
        with open(outline_path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return ""
    for raw in lines:
        match = _CHAPTER_LINE_RE.search(raw)
        if not match:
            continue
        if int(match.group(1)) != int(chapter):
            continue
        parts = [raw.strip(), (match.group(2) or "").strip(), (match.group(3) or "").strip()]
        return " ".join(part for part in parts if part)
    return ""


def relevant_chapters(root, chapter, query, k=TOPK_DEFAULT, window=WINDOW_DEFAULT):
    """窗口外旧章里召回与 query 最相关的 k 章 → [{chapter, score, excerpt}]。缺章/无信号 → []。"""
    corpus = load_prior_chapters(root, chapter, window)
    if not corpus:
        return []
    by_id = dict(corpus)
    out = []
    for cid, score in rank(query, corpus, k=k):
        out.append({"chapter": cid, "score": score,
                    "excerpt": best_excerpt(query, by_id.get(cid, ""))})
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="跨窗口语义检索（BM25·CJK bigram）")
    p.add_argument("project_path")
    p.add_argument("--chapter", type=int, required=True)
    p.add_argument("--query", default=None, help="检索词（默认用本章章纲条目）")
    p.add_argument("--k", type=int, default=TOPK_DEFAULT)
    p.add_argument("--window", type=int, default=WINDOW_DEFAULT)
    args = p.parse_args(argv)
    query = args.query or default_query(args.project_path, args.chapter)
    hits = relevant_chapters(args.project_path, args.chapter, query, args.k, args.window)
    if not hits:
        print("（无可召回的相关旧章——语料不足或无词面信号）")
        return 0
    for h in hits:
        print(f"第{h['chapter']:02d}章 (相关度 {h['score']}) — {h['excerpt'][:60]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
