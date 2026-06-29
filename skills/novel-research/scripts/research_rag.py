#!/usr/bin/env python3
# coding: utf-8
"""Dynamic RAG engine for novel-research: retrieves context-aware knowledge chunks.

真实实现：复用 novel/_lib/vector_store.py 的 BM25（默认）/可选向量检索（C4：缺依赖自动降级 BM25），
对 资料/专业资料包_*.md + 素材/*.md 建索引后检索。**不再伪造结果**——无语料时返回空集 +
status="no_corpus"，让调用方据实判断，绝不返回硬编码 score 让 gate 误信。
"""

import os
import sys
import glob
import json
import argparse
from typing import Dict, Any, List

_LIB = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "novel", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)


def _corpus_files(project_root: str) -> List[str]:
    pats = [
        os.path.join(project_root, "资料", "专业资料包_*.md"),
        os.path.join(project_root, "素材", "观察素材库.md"),
        os.path.join(project_root, "素材", "*.md"),
    ]
    seen, out = set(), []
    for pat in pats:
        for f in sorted(glob.glob(pat)):
            if f not in seen and os.path.isfile(f):
                seen.add(f)
                out.append(f)
    return out


def query_knowledge_base(project_root: str, query: str, top_k: int = 3,
                         use_vector: bool = False) -> Dict[str, Any]:
    """检索 资料/素材 语料中与 query 最相关的 top_k 片段。

    返回 {"status", "engine", "retrieval", "chunks":[{"source","content","score"}]}。
    status ∈ no_corpus / ok / unavailable。score 来自真实 BM25/向量打分，不再硬编码。
    engine/retrieval 报**实际**生效的检索模式（bm25 / hybrid），而非静态字符串——调用方据此判断
    本次是纯词法还是混合（默认 BM25；use_vector=True 且 sentence_transformers 可用才升 hybrid·C4 缺依赖
    自动降级 bm25）。
    """
    files = _corpus_files(project_root)
    if not files:
        return {"status": "no_corpus", "engine": "none", "retrieval": "none",
                "note": "资料/专业资料包_*.md 与 素材/*.md 均不存在；先用 novel-research 产出资料包再检索。",
                "chunks": []}
    try:
        from vector_store import VectorStore  # noqa: E402
    except Exception as exc:  # pragma: no cover - C4 graceful degrade
        return {"status": "unavailable", "engine": "none", "retrieval": "none",
                "note": f"vector_store 不可用：{exc}", "chunks": []}

    store = VectorStore(use_vector=use_vector)
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        base = {"id": os.path.relpath(path, project_root), "source": os.path.basename(path)}
        docs, metas = VectorStore.chunk_document(text, base_metadata=base)
        store.add_documents(docs, metas)
    results = store.search(query, top_k=top_k)
    chunks = [{
        "source": (r.get("metadata") or {}).get("source") or (r.get("metadata") or {}).get("id") or "",
        "content": r.get("text") or "",
        "score": r.get("score"),
    } for r in results]
    meta = store.index_metadata
    mode = meta.get("retrieval", "bm25")  # "bm25" | "hybrid"——实际生效模式
    out = {"status": "ok", "engine": f"vector_store:{mode}", "retrieval": mode, "chunks": chunks}
    if use_vector and mode != "hybrid":
        out["note"] = "请求向量但 sentence_transformers 不可用，已按 C4 降级为 BM25。"
    return out


def main():
    p = argparse.ArgumentParser(description="Dynamic RAG for Novel Research")
    p.add_argument("project_path")
    p.add_argument("--query", required=True, help="Semantic query to search for")
    p.add_argument("--top_k", type=int, default=3, help="Number of chunks to return")
    p.add_argument("--use-vector", action="store_true",
                   help="试启用向量混合检索（需 sentence_transformers；缺则 C4 自动降级 BM25）")
    args = p.parse_args()

    result = query_knowledge_base(args.project_path, args.query, args.top_k,
                                  use_vector=args.use_vector)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
