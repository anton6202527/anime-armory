#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BM25-first retrieval for long novel projects, with an optional vector layer.

Honest naming (don't oversell): the **shipping default is deterministic BM25**
(mixed CJK unigram+bigram tokenizer). The vector/"hybrid" layer is **opt-in and
lazy** (`use_vector=True`) and needs `numpy` + `sentence_transformers`; absent
those it silently degrades to BM25 (C4). `index_metadata["retrieval"]` reports
which actually ran ("bm25" | "hybrid") — callers/eval should read it rather than
assume "hybrid". Whether the vector layer beats BM25 on a given novel corpus is
an empirical question: measure with `vector_store_eval.py --compare` on a real
`retrieval_golden.json` before flipping the default on.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter
from typing import Any


LATIN_RE = re.compile(r"[A-Za-z0-9_]+")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")


def tokenize(text: str) -> list[str]:
    """Tokenize mixed Chinese/Latin prose without third-party dependencies."""
    text = str(text or "").lower()
    tokens: list[str] = []
    for match in re.finditer(r"[A-Za-z0-9_]+|[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+", text):
        part = match.group(0)
        if LATIN_RE.fullmatch(part):
            tokens.append(part)
            continue
        chars = list(part)
        tokens.extend(chars)
        tokens.extend("".join(chars[i:i + 2]) for i in range(len(chars) - 1))
    return [token for token in tokens if token.strip()]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return sorted(value)
    return [value]


def _string_values(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for nested in value.values():
            out.extend(_string_values(nested))
    elif isinstance(value, (list, tuple, set)):
        for nested in value:
            out.extend(_string_values(nested))
    elif value not in (None, ""):
        out.append(str(value))
    return out


class BM25Fallback:
    """Small BM25 implementation tuned for deterministic local retrieval."""

    def __init__(self, corpus: list[str], *, k1: float = 1.5, b: float = 0.75):
        self.corpus = list(corpus)
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(doc) for doc in self.corpus]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        self.term_freqs = [Counter(tokens) for tokens in self.doc_tokens]
        self.doc_freq: Counter[str] = Counter()
        for tf in self.term_freqs:
            self.doc_freq.update(tf.keys())

    def idf(self, term: str) -> float:
        n_docs = len(self.doc_tokens)
        df = self.doc_freq.get(term, 0)
        if not n_docs or not df:
            return 0.0
        return math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

    def score_doc(self, query_terms: list[str], doc_index: int) -> float:
        if not query_terms or doc_index >= len(self.term_freqs):
            return 0.0
        tf = self.term_freqs[doc_index]
        dl = self.doc_lengths[doc_index] or 1
        avgdl = self.avgdl or 1.0
        score = 0.0
        for term in query_terms:
            freq = tf.get(term, 0)
            if not freq:
                continue
            denom = freq + self.k1 * (1.0 - self.b + self.b * dl / avgdl)
            score += self.idf(term) * (freq * (self.k1 + 1.0)) / denom
        return score

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        query_terms = tokenize(query)
        scored = [
            (idx, self.score_doc(query_terms, idx))
            for idx in range(len(self.corpus))
        ]
        scored = [(idx, score) for idx, score in scored if score > 0]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:top_k]


class VectorStore:
    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        *,
        use_vector: bool | None = False,
        vector_weight: float = 0.65,
    ):
        self.corpus: list[str] = []
        self.metadata: list[dict[str, Any]] = []
        self.model_name = model_name
        self.vector_weight = max(0.0, min(1.0, float(vector_weight)))
        self.vector_requested = use_vector is True
        self.use_vector = False
        self.vector_error = ""
        self.model = None
        self.embeddings = None
        self._np = None
        self.bm25 = BM25Fallback([])
        self.alias_index: dict[str, list[str]] = {}
        self.alias_to_canonical: dict[str, str] = {}
        self.timeline_index: list[dict[str, Any]] = []

    @property
    def index_metadata(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "novel_vector_store_index",
            "document_count": len(self.corpus),
            "retrieval": "hybrid" if self.use_vector else "bm25",
            "vector_requested": self.vector_requested,
            "vector_ready": self.use_vector,
            "vector_model": self.model_name if self.use_vector else "",
            "vector_error": self.vector_error,
            "tokenizer": "mixed_cjk_unigram_bigram_latin",
            "alias_count": len(self.alias_to_canonical),
            "timeline_event_count": len(self.timeline_index),
            "chunk_count": len(self.chunk_manifest),
        }

    def _ensure_vector(self) -> bool:
        if self.use_vector:
            return True
        if not self.vector_requested:
            return False
        try:
            import numpy as np  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:
            self.vector_error = str(exc)
            logging.info("Vector dependencies unavailable; using BM25 retrieval: %s", exc)
            self.vector_requested = False
            return False
        logging.info("Vector support enabled. Loading model %s...", self.model_name)
        self._np = np
        self.model = SentenceTransformer(self.model_name)
        self.use_vector = True
        return True

    def _normalize_metadata(self, metadata: dict[str, Any] | None, idx: int) -> dict[str, Any]:
        meta = dict(metadata or {})
        doc_id = str(meta.get("doc_id") or meta.get("id") or meta.get("chunk_id") or f"doc_{idx + 1:04d}")
        meta.setdefault("doc_id", doc_id)
        meta.setdefault("id", doc_id)
        return meta

    def _entity_alias_groups(self, metadata: dict[str, Any]) -> dict[str, set[str]]:
        groups: dict[str, set[str]] = {}

        def add_group(canonical: Any, aliases: Any = None) -> None:
            name = str(canonical or "").strip()
            if not name:
                return
            group = groups.setdefault(name, {name})
            for alias in _as_list(aliases):
                alias_s = str(alias or "").strip()
                if alias_s:
                    group.add(alias_s)

        entity_aliases = metadata.get("entity_aliases")
        if isinstance(entity_aliases, dict):
            for canonical, aliases in entity_aliases.items():
                add_group(canonical, aliases)
        for entity in _as_list(metadata.get("entities")):
            if isinstance(entity, dict):
                canonical = entity.get("canonical") or entity.get("name") or entity.get("id")
                add_group(canonical, entity.get("aliases") or entity.get("alias"))
            else:
                add_group(entity)
        if metadata.get("entity") or metadata.get("canonical"):
            add_group(metadata.get("canonical") or metadata.get("entity"), metadata.get("aliases"))
        elif metadata.get("aliases"):
            doc_id = metadata.get("doc_id") or metadata.get("id")
            add_group(doc_id, metadata.get("aliases"))
        return groups

    def _metadata_search_text(self, metadata: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("id", "doc_id", "chunk_id", "title", "chapter", "chapter_label", "scene", "source_path"):
            value = metadata.get(key)
            if value not in (None, ""):
                parts.append(str(value))
        for group in self._entity_alias_groups(metadata).values():
            parts.extend(sorted(group))
        for key in ("aliases", "tags", "keywords", "timeline", "events", "summary"):
            parts.extend(_string_values(metadata.get(key)))
        return " ".join(parts)

    def _indexed_corpus(self) -> list[str]:
        return [
            f"{text}\n{self._metadata_search_text(meta)}".strip()
            for text, meta in zip(self.corpus, self.metadata)
        ]

    def _rebuild_metadata_indexes(self) -> None:
        self.alias_index = {}
        self.alias_to_canonical = {}
        self.timeline_index = []
        for idx, meta in enumerate(self.metadata):
            for canonical, aliases in self._entity_alias_groups(meta).items():
                existing = set(self.alias_index.get(canonical, []))
                existing.update(aliases)
                self.alias_index[canonical] = sorted(existing)
                for alias in aliases:
                    self.alias_to_canonical[alias.lower()] = canonical
            for event in _as_list(meta.get("timeline") or meta.get("events")):
                if isinstance(event, dict):
                    record = dict(event)
                else:
                    record = {"event": str(event)}
                record.setdefault("doc_id", meta.get("doc_id") or meta.get("id"))
                record.setdefault("chapter", meta.get("chapter"))
                record.setdefault("source_index", idx)
                self.timeline_index.append(record)

    def _rebuild_bm25(self) -> None:
        self._rebuild_metadata_indexes()
        self.bm25 = BM25Fallback(self._indexed_corpus())

    def _rebuild_vector_embeddings(self) -> None:
        if self._ensure_vector() and self.model is not None:
            self.embeddings = self.model.encode(self.corpus, convert_to_numpy=True)

    def add_documents(self, docs: list[str], metadatas: list[dict[str, Any]] | None = None) -> None:
        if not docs:
            return
        start_idx = len(self.corpus)
        self.corpus.extend(str(doc or "") for doc in docs)
        source_meta = metadatas or [{} for _ in docs]
        for offset, _doc in enumerate(docs):
            meta = source_meta[offset] if offset < len(source_meta) else {}
            self.metadata.append(self._normalize_metadata(meta, start_idx + offset))
        self._rebuild_bm25()
        if self._ensure_vector() and self.model is not None:
            new_embeddings = self.model.encode(docs, convert_to_numpy=True)
            if self.embeddings is None:
                self.embeddings = new_embeddings
            else:
                self.embeddings = self._np.vstack((self.embeddings, new_embeddings))

    def expand_query(self, query: str) -> str:
        expanded = [str(query or "")]
        query_lower = str(query or "").lower()
        for canonical, aliases in self.alias_index.items():
            terms = set(aliases)
            terms.add(canonical)
            if any(term and term.lower() in query_lower for term in terms):
                expanded.extend(sorted(terms))
        return " ".join(term for term in expanded if term)

    def _matched_aliases(self, expanded_query: str, metadata: dict[str, Any]) -> list[str]:
        q = expanded_query.lower()
        matches: set[str] = set()
        for aliases in self._entity_alias_groups(metadata).values():
            for alias in aliases:
                if alias and alias.lower() in q:
                    matches.add(alias)
        return sorted(matches)

    def _result_record(self, idx: int, score: float, *, bm25_score: float, vector_score: float | None,
                       rank_source: str, expanded_query: str) -> dict[str, Any]:
        meta = self.metadata[idx]
        return {
            "score": float(score),
            "bm25_score": float(bm25_score),
            "vector_score": None if vector_score is None else float(vector_score),
            "rank_source": rank_source,
            "text": self.corpus[idx],
            "metadata": meta,
            "doc_id": meta.get("doc_id") or meta.get("id"),
            "matched_aliases": self._matched_aliases(expanded_query, meta),
        }

    def _bm25_results(self, query: str, top_k: int) -> list[dict[str, Any]]:
        out = []
        expanded = self.expand_query(query)
        for idx, score in self.bm25.search(expanded, top_k):
            out.append(self._result_record(idx, score, bm25_score=score, vector_score=None, rank_source="bm25", expanded_query=expanded))
        return out

    @staticmethod
    def _normalize(scores: dict[int, float]) -> dict[int, float]:
        if not scores:
            return {}
        max_score = max(scores.values())
        if max_score <= 0:
            return {idx: 0.0 for idx in scores}
        return {idx: score / max_score for idx, score in scores.items()}

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.corpus:
            return []
        top_k = max(1, int(top_k))
        expanded = self.expand_query(query)
        bm25_scores = dict(self.bm25.search(expanded, max(top_k * 4, top_k)))
        if not self.use_vector or self.embeddings is None or self.model is None:
            return self._bm25_results(query, top_k)

        np = self._np
        query_emb = self.model.encode([expanded], convert_to_numpy=True)
        similarities = np.dot(self.embeddings, query_emb.T).flatten()
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_emb)
        norms[norms == 0] = 1e-10
        cosine_scores = similarities / norms
        vector_scores = {idx: float(cosine_scores[idx]) for idx in range(len(self.corpus))}
        bm25_norm = self._normalize(bm25_scores)
        vector_norm = self._normalize(vector_scores)
        all_indices = set(vector_scores) | set(bm25_scores)
        combined = []
        bm25_weight = 1.0 - self.vector_weight
        for idx in all_indices:
            score = self.vector_weight * vector_norm.get(idx, 0.0) + bm25_weight * bm25_norm.get(idx, 0.0)
            combined.append((idx, score))
        combined.sort(key=lambda item: (-item[1], item[0]))
        results = []
        for idx, score in combined[:top_k]:
            results.append(self._result_record(
                idx,
                score,
                bm25_score=bm25_scores.get(idx, 0.0),
                vector_score=vector_scores.get(idx, 0.0),
                rank_source="hybrid",
                expanded_query=expanded,
            ))
        return results

    @property
    def chunk_manifest(self) -> list[dict[str, Any]]:
        chunks = []
        for idx, meta in enumerate(self.metadata):
            if meta.get("chunk_id") or meta.get("chunk_index") is not None:
                chunks.append({
                    "doc_id": meta.get("doc_id") or meta.get("id"),
                    "chunk_id": meta.get("chunk_id") or meta.get("doc_id") or meta.get("id"),
                    "chunk_index": meta.get("chunk_index"),
                    "source_path": meta.get("source_path") or "",
                    "chapter": meta.get("chapter"),
                    "start_char": meta.get("start_char"),
                    "end_char": meta.get("end_char"),
                    "size_chars": len(self.corpus[idx]),
                })
        return chunks

    @staticmethod
    def chunk_document(
        text: str,
        *,
        chunk_size: int = 1200,
        overlap: int = 160,
        base_metadata: dict[str, Any] | None = None,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        text = str(text or "")
        chunk_size = max(1, int(chunk_size))
        overlap = max(0, min(int(overlap), chunk_size - 1)) if chunk_size > 1 else 0
        docs: list[str] = []
        metas: list[dict[str, Any]] = []
        pos = 0
        index = 0
        base = dict(base_metadata or {})
        source_id = str(base.get("doc_id") or base.get("id") or base.get("source_path") or "doc")
        while pos < len(text):
            end = min(len(text), pos + chunk_size)
            chunk = text[pos:end]
            docs.append(chunk)
            meta = dict(base)
            meta.update({
                "doc_id": f"{source_id}#chunk{index + 1:04d}",
                "chunk_id": f"{source_id}#chunk{index + 1:04d}",
                "chunk_index": index,
                "start_char": pos,
                "end_char": end,
            })
            metas.append(meta)
            if end >= len(text):
                break
            pos = max(end - overlap, pos + 1)
            index += 1
        return docs, metas

    def update_document(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> bool:
        for idx, meta in enumerate(self.metadata):
            if str(meta.get("doc_id") or meta.get("id")) == str(doc_id):
                self.corpus[idx] = str(text or "")
                merged = dict(meta)
                if metadata:
                    merged.update(metadata)
                self.metadata[idx] = self._normalize_metadata(merged, idx)
                self._rebuild_bm25()
                if self.use_vector:
                    self._rebuild_vector_embeddings()
                return True
        self.add_documents([text], [metadata or {"doc_id": doc_id, "id": doc_id}])
        return False

    def delete_documents(self, ids: list[str]) -> int:
        wanted = {str(item) for item in ids}
        kept_corpus: list[str] = []
        kept_meta: list[dict[str, Any]] = []
        removed = 0
        for text, meta in zip(self.corpus, self.metadata):
            doc_id = str(meta.get("doc_id") or meta.get("id"))
            if doc_id in wanted:
                removed += 1
                continue
            kept_corpus.append(text)
            kept_meta.append(meta)
        if removed:
            self.corpus = kept_corpus
            self.metadata = kept_meta
            self._rebuild_bm25()
            if self.use_vector:
                self._rebuild_vector_embeddings()
        return removed

    def evaluate_golden(self, cases: list[dict[str, Any]], *, top_k: int = 5) -> dict[str, Any]:
        # 度量算术走 retrieval.score_golden_cases（与 vector_store_eval._evaluate_production 同一份·去重）。
        from retrieval import score_golden_cases  # 同在 _lib

        def _ranker(query: str, k: int) -> list[str]:
            return [str(item.get("doc_id") or (item.get("metadata") or {}).get("id") or "")
                    for item in self.search(query, top_k=k)]

        base = score_golden_cases(cases, _ranker, top_k=top_k)
        return {"schema_version": 1, "kind": "novel_vector_store_golden_eval", "top_k": top_k, **base}

    def to_dict(self) -> dict[str, Any]:
        embeddings = None
        if self.embeddings is not None:
            try:
                embeddings = self.embeddings.tolist()
            except AttributeError:
                embeddings = self.embeddings
        return {
            "schema_version": 1,
            "kind": "novel_vector_store",
            "index_metadata": self.index_metadata,
            "corpus": self.corpus,
            "metadata": self.metadata,
            "alias_index": self.alias_index,
            "timeline_index": self.timeline_index,
            "chunk_manifest": self.chunk_manifest,
            "embeddings": embeddings,
        }

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: str, *, use_vector: bool | None = False) -> "VectorStore":
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        meta = payload.get("index_metadata") or {}
        model_name = meta.get("vector_model") or "paraphrase-multilingual-MiniLM-L12-v2"
        store = cls(model_name=model_name, use_vector=False)
        store.add_documents(payload.get("corpus") or [], payload.get("metadata") or [])
        if use_vector:
            store.vector_requested = True
            saved = payload.get("embeddings")
            if saved is not None and store._ensure_vector() and store._np is not None:
                store.embeddings = store._np.array(saved)
            else:
                store._rebuild_vector_embeddings()
        return store
