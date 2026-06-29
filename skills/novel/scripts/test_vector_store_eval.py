#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import vector_store_eval


def write_json(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def test_vector_store_eval_builds_from_chapters_and_writes_report():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("姜月初在雨夜发现玉佩，妖纹微亮。\n")
        with open(os.path.join(root, "章节", "第02章.md"), "w", encoding="utf-8") as f:
            f.write("市井茶楼有人议论榜单。\n")
        write_json(os.path.join(root, "生产数据", "retrieval_golden.json"), {
            "thresholds": {"min_recall_at_k": 1.0, "min_mrr": 1.0},
            "cases": [
                {"query": "玉佩 妖纹", "expected_ids": ["章节/第01章.md"]},
                {"query": "茶楼 榜单", "expected_ids": ["章节/第02章.md"]},
            ],
        })

        report = vector_store_eval.evaluate_project(root, top_k=1, engine="vector_store")
        assert report["passed"] is True
        assert report["engine"] == "vector_store"
        assert report["metrics"]["recall_at_k"] == 1.0
        assert report["index_metadata"]["chunk_count"] == 2

        json_path, md_path = vector_store_eval.write_report(root, report)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)


def test_default_engine_is_production_and_matches_shipped_retrieval():
    # 默认 engine=production：用 retrieval.rank（draft_packets 实际调用的引擎）打分，
    # 保证回归绿灯盖在上线引擎上，而非旁路 VectorStore。
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("姜月初在雨夜发现玉佩，妖纹微亮。\n")
        with open(os.path.join(root, "章节", "第02章.md"), "w", encoding="utf-8") as f:
            f.write("市井茶楼有人议论榜单与终局密钥。\n")
        write_json(os.path.join(root, "生产数据", "retrieval_golden.json"), {
            "thresholds": {"min_recall_at_k": 1.0, "min_mrr": 1.0},
            "cases": [
                {"query": "玉佩 妖纹", "expected_ids": ["章节/第01章.md"]},
                {"query": "茶楼 终局密钥", "expected_ids": ["章节/第02章.md"]},
            ],
        })
        report = vector_store_eval.evaluate_project(root, top_k=1)  # 默认 production
        assert report["engine"] == "production"
        assert report["index_metadata"]["engine"] == "retrieval.rank"
        assert report["passed"] is True
        assert report["metrics"]["recall_at_k"] == 1.0


def test_vector_store_eval_chunks_long_chapters_but_keeps_chapter_doc_id():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        long_text = "伏笔 " * 700 + "终局密钥藏在青铜门后。"
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write(long_text)
        write_json(os.path.join(root, "生产数据", "retrieval_golden.json"), {
            "thresholds": {"min_recall_at_k": 1.0, "min_mrr": 1.0},
            "cases": [
                {"query": "终局密钥 青铜门", "expected_ids": ["章节/第01章.md"]},
            ],
        })

        report = vector_store_eval.evaluate_project(root, top_k=1, engine="vector_store")
        case = report["cases"][0]
        assert report["passed"] is True
        assert report["index_metadata"]["document_count"] > 1
        assert case["result_ids"] == ["章节/第01章.md"]
