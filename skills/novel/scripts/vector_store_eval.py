#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluate novel retrieval quality against a golden query set."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any


HERE = os.path.dirname(os.path.abspath(__file__))
NOVEL_LIB = os.path.abspath(os.path.join(HERE, "..", "_lib"))
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)

from vector_store import VectorStore  # noqa: E402


EVAL_KIND = "novel_vector_store_project_eval"


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def chapter_number(name: str) -> int:
    digits = "".join(ch for ch in name if ch.isdigit())
    return int(digits or 0)


def build_store_from_chapters(root: str) -> VectorStore:
    store = VectorStore()
    chapter_dir = os.path.join(root, "章节")
    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    if os.path.isdir(chapter_dir):
        for name in sorted(os.listdir(chapter_dir), key=chapter_number):
            if not name.endswith(".md"):
                continue
            path = os.path.join(chapter_dir, name)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            doc_id = rel(root, path)
            base_meta = {
                "doc_id": doc_id,
                "id": doc_id,
                "source_path": doc_id,
                "chapter": chapter_number(name),
            }
            chunk_docs, chunk_metas = VectorStore.chunk_document(text, base_metadata=base_meta)
            for meta in chunk_metas:
                chunk_id = meta.get("chunk_id") or meta.get("id") or doc_id
                meta["doc_id"] = doc_id
                meta["id"] = chunk_id
                meta["source_path"] = doc_id
            docs.extend(chunk_docs)
            metas.extend(chunk_metas)
    store.add_documents(docs, metas)
    return store


def load_cases(path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = load_json(path, []) or []
    if isinstance(payload, dict):
        cases = payload.get("cases") or []
        thresholds = payload.get("thresholds") or {}
    else:
        cases = payload
        thresholds = {}
    if not isinstance(cases, list):
        raise ValueError("golden cases must be a list or a dict with cases")
    return cases, thresholds if isinstance(thresholds, dict) else {}


def _evaluate_production(root: str, cases: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    """用**生产引擎** retrieval.rank（draft_packets.relevant_chapters 实际调用的 BM25 排序原语）
    对整章语料跑同一组 golden cases。golden 的 expected_ids 即章 doc_id（章节/第NN章.md），与生产
    召回的章 id 同粒度——所以这是对"真正上线的检索"打分，而非旁路 VectorStore。"""
    import retrieval  # noqa: E402  同在 _lib
    chapter_dir = os.path.join(root, "章节")
    corpus: list[tuple[str, str]] = []
    if os.path.isdir(chapter_dir):
        for name in sorted(os.listdir(chapter_dir), key=chapter_number):
            if name.endswith(".md"):
                path = os.path.join(chapter_dir, name)
                with open(path, encoding="utf-8") as f:
                    corpus.append((rel(root, path), f.read()))
    # 度量算术走 retrieval.score_golden_cases（与 VectorStore.evaluate_golden 同一份·去重）。
    return retrieval.score_golden_cases(
        cases, lambda q, k: [cid for cid, _ in retrieval.rank(q, corpus, k=k)], top_k=top_k)


def evaluate_project(
    root: str,
    *,
    index_path: str = "",
    golden_path: str = "",
    top_k: int = 5,
    min_recall: float = 0.8,
    min_mrr: float = 0.5,
    use_vector: bool = False,
    engine: str = "production",
) -> dict[str, Any]:
    """engine="production"（默认）：测 retrieval.rank（生产实际用的引擎），保证回归绿灯盖在上线引擎上。
    engine="vector_store"：测 VectorStore（旁路/实验引擎），仅供对照。"""
    root = os.path.abspath(root)
    index_path = index_path or os.path.join(root, "生产数据", "vector_store.json")
    golden_path = golden_path or os.path.join(root, "生产数据", "retrieval_golden.json")
    if not os.path.exists(golden_path):
        raise FileNotFoundError(f"golden retrieval file not found: {golden_path}")
    cases, thresholds = load_cases(golden_path)
    min_recall = float(thresholds.get("min_recall_at_k", min_recall))
    min_mrr = float(thresholds.get("min_mrr", min_mrr))
    if engine == "production":
        raw = _evaluate_production(root, cases, top_k)
        index_source = "章节/*.md (retrieval.rank · 生产引擎)"
        index_metadata = {"engine": "retrieval.rank", "granularity": "chapter"}
    else:
        if os.path.exists(index_path):
            store = VectorStore.load(index_path, use_vector=use_vector)
            index_source = rel(root, index_path)
        else:
            store = build_store_from_chapters(root)
            index_source = "章节/*.md"
        raw = store.evaluate_golden(cases, top_k=top_k)
        index_metadata = store.index_metadata
    passed = raw["recall_at_k"] >= min_recall and raw["mrr"] >= min_mrr
    return {
        "schema_version": 1,
        "kind": EVAL_KIND,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": root,
        "engine": engine,
        "index_source": index_source,
        "golden_path": rel(root, golden_path),
        "thresholds": {
            "top_k": top_k,
            "min_recall_at_k": min_recall,
            "min_mrr": min_mrr,
        },
        "passed": passed,
        "index_metadata": index_metadata,
        "metrics": {
            "case_count": raw["case_count"],
            "hit_count": raw["hit_count"],
            "recall_at_k": raw["recall_at_k"],
            "mrr": raw["mrr"],
            "failure_count": len(raw.get("failures") or []),
        },
        "failures": raw.get("failures") or [],
        "cases": raw.get("cases") or [],
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") or {}
    thresholds = report.get("thresholds") or {}
    lines = [
        "# Vector Store Retrieval Eval",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- passed: {report.get('passed')}",
        f"- index_source: {report.get('index_source')}",
        f"- golden_path: {report.get('golden_path')}",
        f"- recall_at_{thresholds.get('top_k')}: {metrics.get('recall_at_k', 0):.3f} / min={thresholds.get('min_recall_at_k')}",
        f"- mrr: {metrics.get('mrr', 0):.3f} / min={thresholds.get('min_mrr')}",
        f"- cases: {metrics.get('case_count', 0)} failures={metrics.get('failure_count', 0)}",
        "",
        "## Failures",
        "",
    ]
    failures = report.get("failures") or []
    if not failures:
        lines.append("- none")
    else:
        for item in failures:
            lines.append(f"- {item.get('query')}: expected={item.get('expected_ids')} got={item.get('result_ids')}")
    return "\n".join(lines) + "\n"


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "vector_store_eval.json")
    md_path = os.path.join(out_dir, "vector_store_eval.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report))
    return json_path, md_path


def compare_engines(root: str, *, golden_path: str = "", index_path: str = "",
                    top_k: int = 5) -> dict[str, Any]:
    """一条命令量出 BM25 vs 向量混合 的 recall/MRR 差距，供「换默认前先测」决策。

    跑三路同一 golden 集：production（上线引擎 retrieval.rank）、vector_store/bm25、
    vector_store/hybrid（use_vector=True；缺 sentence_transformers 会按 C4 降级，
    届时 vector_available=False、hybrid 实测=bm25，诚实标注而非假装测了向量）。
    返回各路 metrics + delta（hybrid 相对 bm25 的 recall/MRR 增量）+ recommendation。"""
    bm25 = evaluate_project(root, golden_path=golden_path, index_path=index_path,
                            top_k=top_k, engine="vector_store", use_vector=False)
    hybrid = evaluate_project(root, golden_path=golden_path, index_path=index_path,
                              top_k=top_k, engine="vector_store", use_vector=True)
    prod = evaluate_project(root, golden_path=golden_path, index_path=index_path,
                            top_k=top_k, engine="production")
    vector_available = bool((hybrid.get("index_metadata") or {}).get("vector_ready"))
    d_recall = hybrid["metrics"]["recall_at_k"] - bm25["metrics"]["recall_at_k"]
    d_mrr = hybrid["metrics"]["mrr"] - bm25["metrics"]["mrr"]
    if not vector_available:
        rec = ("sentence_transformers 不可用——向量层未真正参与，hybrid 实测=BM25。"
               "无证据支持开向量；保持 BM25 默认，装依赖后再 --compare。")
    elif d_recall > 0.02 or d_mrr > 0.02:
        rec = f"向量混合在本语料有提升（Δrecall={d_recall:+.3f} Δmrr={d_mrr:+.3f}）——值得考虑把 retrieval 默认升 hybrid。"
    else:
        rec = f"向量混合在本语料无明显提升（Δrecall={d_recall:+.3f} Δmrr={d_mrr:+.3f}）——保持 BM25 默认，别为零收益扛依赖。"
    return {
        "kind": "novel_retrieval_engine_compare",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": os.path.abspath(root),
        "vector_available": vector_available,
        "engines": {
            "production_retrieval_rank": prod["metrics"],
            "vector_store_bm25": bm25["metrics"],
            "vector_store_hybrid": hybrid["metrics"],
        },
        "delta_hybrid_vs_bm25": {"recall_at_k": d_recall, "mrr": d_mrr},
        "recommendation": rec,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="evaluate novel vector/BM25 retrieval against golden cases")
    parser.add_argument("project_root")
    parser.add_argument("--index", default="", help="saved vector store JSON; default 生产数据/vector_store.json, fallback builds from 章节/")
    parser.add_argument("--golden", default="", help="golden query JSON; default 生产数据/retrieval_golden.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-recall", type=float, default=0.8)
    parser.add_argument("--min-mrr", type=float, default=0.5)
    parser.add_argument("--use-vector", action="store_true", help="try loading vector embeddings/dependencies")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--allow-fail", action="store_true")
    parser.add_argument("--engine", choices=["production", "vector_store"], default="production",
                        help="production=测上线引擎 retrieval.rank（默认）；vector_store=测旁路 VectorStore")
    parser.add_argument("--compare", action="store_true",
                        help="一条命令对比 BM25 vs 向量混合 recall/MRR 差距（换默认前先测）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    if args.compare:
        try:
            cmp = compare_engines(root, golden_path=args.golden, index_path=args.index, top_k=args.top_k)
        except Exception as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 1
        print(json.dumps(cmp, ensure_ascii=False, indent=2))
        return 0
    try:
        report = evaluate_project(
            root,
            index_path=args.index,
            golden_path=args.golden,
            top_k=args.top_k,
            min_recall=args.min_recall,
            min_mrr=args.min_mrr,
            use_vector=args.use_vector,
            engine=args.engine,
        )
    except Exception as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 1
    if args.write:
        json_path, md_path = write_report(root, report)
        if not args.json:
            print(f"[ok] vector eval JSON → {json_path}")
            print(f"[ok] vector eval MD   → {md_path}")
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_markdown(report))
    return 0 if report.get("passed") or args.allow_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
