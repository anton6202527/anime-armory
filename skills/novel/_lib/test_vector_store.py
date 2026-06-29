#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile

from vector_store import BM25Fallback, VectorStore, tokenize


def test_tokenize_mixed_chinese_and_latin():
    tokens = tokenize("姜月初拿起玉佩 Alpha-7")
    assert "姜" in tokens
    assert "玉佩" in tokens
    assert "alpha" in tokens
    assert "7" in tokens


def test_bm25_fallback_ranks_matching_chinese_document_first():
    bm25 = BM25Fallback([
        "夜色里只有风声。",
        "姜月初把黑色玉佩收入袖中，妖纹微亮。",
        "厨房传来热粥香气。",
    ])

    results = bm25.search("玉佩 妖纹", top_k=2)
    assert results[0][0] == 1
    assert results[0][1] > 0


def test_vector_store_default_bm25_and_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        store = VectorStore()
        store.add_documents(
            [
                "宗门大殿晨钟响起。",
                "姜月初在雨夜发现玉佩里的妖纹地图。",
                "市井茶楼有人议论榜单。",
            ],
            [{"id": "hall"}, {"id": "jade"}, {"id": "market"}],
        )

        results = store.search("玉佩 妖纹", top_k=1)
        assert results[0]["metadata"]["id"] == "jade"
        assert results[0]["rank_source"] == "bm25"
        assert store.index_metadata["retrieval"] == "bm25"

        path = os.path.join(tmp, "index.json")
        store.save(path)
        loaded = VectorStore.load(path)
        assert loaded.search("玉佩 妖纹", top_k=1)[0]["metadata"]["id"] == "jade"


def test_vector_store_alias_timeline_chunk_update_delete_and_golden_eval():
    store = VectorStore()
    docs, metas = VectorStore.chunk_document(
        "姜月初在雨夜发现玉佩。她被同伴称作阿月，随后进入宗门大殿。",
        chunk_size=18,
        overlap=4,
        base_metadata={
            "id": "ch1",
            "source_path": "章节/第01章.md",
            "chapter": 1,
            "entity_aliases": {"姜月初": ["阿月", "月初"]},
            "timeline": [{"event": "雨夜获玉佩", "chapter": 1}],
        },
    )
    store.add_documents(docs, metas)
    store.add_documents(
        ["市井茶楼里有人议论榜单。"],
        [{"id": "market", "chapter": 2, "entities": [{"name": "茶楼老板", "aliases": ["老板娘"]}]}],
    )

    alias_hit = store.search("阿月 玉佩", top_k=1)[0]
    assert alias_hit["doc_id"].startswith("ch1#chunk")
    assert "姜月初" in alias_hit["matched_aliases"]
    assert store.index_metadata["alias_count"] >= 3
    assert store.timeline_index[0]["event"] == "雨夜获玉佩"
    assert store.chunk_manifest[0]["source_path"] == "章节/第01章.md"

    report = store.evaluate_golden([
        {"query": "月初在哪里得到玉佩", "expected_ids": [alias_hit["doc_id"]], "top_k": 3},
        {"query": "老板娘 榜单", "expected_ids": ["market"], "top_k": 3},
    ], top_k=3)
    assert report["recall_at_k"] == 1.0
    assert report["mrr"] > 0

    store.update_document("market", "茶楼老板娘改开灵药铺，讨论丹药榜。", {"aliases": ["老板娘"], "timeline": ["灵药铺开张"]})
    assert store.search("灵药铺 老板娘", top_k=1)[0]["doc_id"] == "market"
    assert store.delete_documents(["market"]) == 1
    assert not any(result["doc_id"] == "market" for result in store.search("老板娘", top_k=5))
