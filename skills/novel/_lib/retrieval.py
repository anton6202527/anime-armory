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
import json
import math
import hashlib
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


def doc_freq_from_tf(tf_maps):
    """[tf-dict,...] → {term: 出现该 term 的文档数}（tf 的键即该文档去重后的 term）。纯函数·可测。
    与 doc_freq 等价：doc_freq 数 set(toks)，这里数 tf.keys()，二者相同。"""
    df = Counter()
    for tf in tf_maps:
        for t in tf:
            df[t] += 1
    return df


def bm25_score_tf(query_tokens, tf, dl, idf_map, avg_len, k1=1.5, b=0.75):
    """基于预存 term-freq 的单文档 BM25（与 bm25_score 同公式，省去重新 tokenize）。纯函数·可测。"""
    if not dl:
        return 0.0
    score = 0.0
    for t in set(query_tokens):
        f = tf.get(t, 0)
        if not f:
            continue
        w = idf_map.get(t, 0.0)
        score += w * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / (avg_len or 1)))
    return score


def rank_from_index(query_text, chapters, k=TOPK_DEFAULT, min_score=0.0):
    """query + chapters=[(id, tf-dict, dl)] → top-k [(id, score)]，结果与 rank() 对同一语料一致。纯函数·可测。"""
    chapters = [(cid, tf, dl) for cid, tf, dl in chapters if dl]
    if not chapters:
        return []
    df = doc_freq_from_tf([tf for _, tf, _ in chapters])
    idf_map = idf(df, len(chapters))
    avg = sum(dl for _, _, dl in chapters) / len(chapters)
    q = cjk_bigrams(query_text)
    if not q:
        return []
    scored = [(cid, bm25_score_tf(q, tf, dl, idf_map, avg)) for cid, tf, dl in chapters]
    scored = [(c, round(s, 4)) for c, s in scored if s > min_score]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:k]


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


# ---------- 语义重排（可选适配器·默认关闭，遵循设计宪法 C4：主流程不硬绑 embedding） ----------

def cosine(a, b):
    """余弦相似度。纯函数·可测。"""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def semantic_rerank(query_text, candidates, embedder, k=TOPK_DEFAULT):
    """对 BM25 宽召回的候选做语义重排。

    candidates=[(cid, text)]；embedder(list[str])->list[vec]（一次性 embed query + 各候选）。
    返回按 query 余弦相似降序的 [(cid, score)]；embedder 出错/形状不符 → []（调用方据此回退 BM25）。纯函数·可测。
    """
    if not candidates:
        return []
    texts = [t for _, t in candidates]
    try:
        vecs = embedder([query_text] + texts)
    except Exception:
        return []
    if not vecs or len(vecs) != len(texts) + 1:
        return []
    qv = vecs[0]
    scored = [(cid, round(cosine(qv, vecs[i + 1]), 6)) for i, (cid, _t) in enumerate(candidates)]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:k]


_EMBEDDER_CACHE = None


def _load_embedder():
    """best-effort 语义嵌入适配器：**默认 None → 纯 BM25**（与历史行为一致）。

    仅当环境变量 `NOVEL_RETRIEVAL_EMBED` 置位（非空且非 0/off/false/no）且可选后端可用时，返回
    embedder callable（list[str]->list[vec]）。遵循设计宪法 C4：主流程绝不硬绑 embedding——
    未装/加载失败一律优雅降级回 BM25，不让缺依赖中断写作包生成。模型名可经 `NOVEL_RETRIEVAL_EMBED_MODEL` 覆盖。
    """
    global _EMBEDDER_CACHE
    if _EMBEDDER_CACHE is not None:
        return _EMBEDDER_CACHE or None
    flag = os.environ.get("NOVEL_RETRIEVAL_EMBED", "").strip().lower()
    if flag in {"", "0", "off", "false", "no"}:
        _EMBEDDER_CACHE = False
        return None
    embedder = None
    try:  # 可选后端：sentence-transformers；未安装/失败则降级 BM25。
        from sentence_transformers import SentenceTransformer  # type: ignore
        model_name = os.environ.get(
            "NOVEL_RETRIEVAL_EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        _model = SentenceTransformer(model_name)

        def embedder(texts):  # noqa: F811
            return [list(map(float, v)) for v in _model.encode(texts)]
    except Exception:
        embedder = None
    _EMBEDDER_CACHE = embedder or False
    return embedder


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


# ---------- 持久增量索引（几百章规模避免每次出包全量重读重 tokenize） ----------

INDEX_VERSION = 1


def _index_path(root):
    return os.path.join(root, "审稿", "_retrieval_index.json")


def _sha1_text(text):
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def _load_index(root):
    try:
        with open(_index_path(root), encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") == INDEX_VERSION and isinstance(data.get("chapters"), dict):
            return data
    except Exception:
        pass
    return {"version": INDEX_VERSION, "chapters": {}}


def _save_index(root, index):
    path = _index_path(root)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False)
        os.replace(tmp, path)  # 原子替换，避免多 worker 写半截
    except Exception:
        pass


def build_or_update_index(root):
    """增量维护 章节/ 的 BM25 索引：内容 hash 不变的章复用缓存 tf，只对新增/改动章重新 tokenize。
    返回 {version, chapters:{cid: {hash, len, tf}}}。任何单章读失败跳过，不致命。"""
    index = _load_index(root)
    chapters = index.get("chapters", {})
    seen = set()
    for path in sorted(glob.glob(os.path.join(root, "章节", "*.md"))):
        cid = _chapter_num(path)
        if cid is None or cid < 1:
            continue
        key = str(cid)
        seen.add(key)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        h = _sha1_text(text)
        entry = chapters.get(key)
        if entry and entry.get("hash") == h and "tf" in entry:
            continue  # 未变 → 复用缓存
        toks = cjk_bigrams(text)
        chapters[key] = {"hash": h, "len": len(toks), "tf": dict(Counter(toks))}
    for key in list(chapters.keys()):  # 删除已不存在的章
        if key not in seen:
            del chapters[key]
    index["chapters"] = chapters
    _save_index(root, index)
    return index


def _read_chapter_text(root, cid):
    for path in glob.glob(os.path.join(root, "章节", "*.md")):
        if _chapter_num(path) == cid:
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return ""
    return ""


def _relevant_chapters_scan(root, chapter, query, k=TOPK_DEFAULT, window=WINDOW_DEFAULT):
    """全量扫描兜底实现（索引异常时回退）：读窗口外旧章正文，现算 BM25。"""
    corpus = load_prior_chapters(root, chapter, window)
    if not corpus:
        return []
    by_id = dict(corpus)
    out = []
    for cid, score in rank(query, corpus, k=k):
        out.append({"chapter": cid, "score": score,
                    "excerpt": best_excerpt(query, by_id.get(cid, ""))})
    return out


def relevant_chapters(root, chapter, query, k=TOPK_DEFAULT, window=WINDOW_DEFAULT, embedder=None):
    """窗口外旧章里召回与 query 最相关的 k 章 → [{chapter, score, excerpt}]。缺章/无信号 → []。

    走持久增量索引：排序只用缓存 tf（不重读全部旧章），仅对命中的章读正文做摘要。
    **默认纯 BM25**（embedder=None 且未开 NOVEL_RETRIEVAL_EMBED 时，行为与历史一致）。
    若可用语义 embedder（显式传入或环境开启）：BM25 宽召回 → 语义余弦重排到 k（解决词面召不回的语义近邻）；
    语义任何环节失败 → 回退 BM25 top-k。索引任何异常 → 回退全量扫描，保证可用性。
    """
    try:
        cutoff = chapter - window
        index = build_or_update_index(root)
        chapters = []
        for key, entry in index.get("chapters", {}).items():
            try:
                cid = int(key)
            except (TypeError, ValueError):
                continue
            if cid < 1 or cid >= cutoff:
                continue
            chapters.append((cid, entry.get("tf", {}) or {}, int(entry.get("len") or 0)))
        if not chapters:
            return []
        if embedder is None:
            embedder = _load_embedder()
        if embedder is not None:
            wide = max(k * 4, 12)  # BM25 宽召回，给语义重排留候选
            wide_hits = rank_from_index(query, chapters, k=wide)
            cand = [(cid, _read_chapter_text(root, cid)) for cid, _s in wide_hits]
            reranked = semantic_rerank(query, cand, embedder, k=k)
            if reranked:
                texts = {cid: t for cid, t in cand}
                return [{"chapter": cid, "score": score,
                         "excerpt": best_excerpt(query, texts.get(cid, ""))}
                        for cid, score in reranked]
            # 语义失败 → 落回 BM25
        out = []
        for cid, score in rank_from_index(query, chapters, k=k):
            out.append({"chapter": cid, "score": score,
                        "excerpt": best_excerpt(query, _read_chapter_text(root, cid))})
        return out
    except Exception:
        return _relevant_chapters_scan(root, chapter, query, k, window)


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
