#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import prompt_cache_metrics
import review_board


def write_json(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def test_review_board_holds_for_blockers_and_writes_outputs():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "审稿", "review_report.json"), {
            "summary": {"blocking_count": 1},
            "findings": [{"id": "R1", "blocking": True}],
        })
        write_json(os.path.join(root, "评分", "score_report.json"), {
            "total_score": 72,
            "verdict": "小改",
            "production_decision": {"decision": "revise"},
        })
        write_json(os.path.join(root, "修订", "revision_plan.json"), {
            "tasks": [{"id": "T1", "priority": "P0", "conflict": True}],
        })

        board = review_board.build_board(root)
        assert board["decision"] == "hold_for_editor_arbitration"
        assert board["approval_required"] is True
        assert board["signals"]["review"]["blocking_count"] == 1

        json_path, md_path, written = review_board.write_board(root, board, html_out=True)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        assert os.path.exists(os.path.join(root, "审稿", "review_board.html"))
        assert written["decision"] == "hold_for_editor_arbitration"


def test_review_board_requires_fresh_review_and_score_snapshots():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("正文\n")
        snapshot = review_board.snapshot_chapters(root, mode="review:full")
        write_json(os.path.join(root, "审稿", "review_report.json"), {
            "source_snapshot": snapshot,
            "summary": {"blocking_count": 0},
            "findings": [],
        })
        write_json(os.path.join(root, "评分", "score_report.json"), {
            "source_snapshot": snapshot,
            "total_score": 88,
            "verdict": "通过",
            "production_decision": {"decision": "go"},
        })

        ready = review_board.build_board(root)
        assert ready["decision"] == "ready_for_release_review"
        assert ready["signals"]["review"]["source_snapshot_fresh"] is True

        with open(os.path.join(root, "章节", "第01章.md"), "a", encoding="utf-8") as f:
            f.write("新内容\n")
        stale = review_board.build_board(root)
        assert stale["decision"] == "hold_for_editor_arbitration"
        assert any("stale" in reason for reason in stale["reasons"])


def test_prompt_cache_metrics_scans_packets_and_writes_outputs():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "写作任务"), exist_ok=True)
        packet = os.path.join(root, "写作任务", "第01章.md")
        with open(packet, "w", encoding="utf-8") as f:
            f.write(
                '<static_context cache_control="ephemeral">\n'
                "设定圣经和角色卡路径。\n"
                "</static_context>\n"
                "本章动态任务：写雨夜获玉佩。\n"
            )
        write_json(os.path.join(root, "语义任务", "job1.json"), {
            "prompt": '<static_context cache_control="ephemeral">审稿标准</static_context>检查第1章',
            "usage": {"input_tokens": 1000, "input_token_details": {"cached_tokens": 250}},
        })
        os.makedirs(os.path.join(root, "写作任务", "trio"), exist_ok=True)
        with open(os.path.join(root, "写作任务", "trio", "第01章_editor.md"), "w", encoding="utf-8") as f:
            f.write('<static_context>风格锚点</static_context>\n编辑任务\n')

        metrics = prompt_cache_metrics.collect_metrics(root)
        assert metrics["packet_count"] == 2
        assert metrics["semantic_job_count"] == 1
        assert metrics["cache_control_coverage"] > 0
        assert metrics["static_context_ratio"] > 0
        assert metrics["actual_usage"]["record_count"] == 1
        assert metrics["actual_cache_hit_ratio"] == 0.25

        json_path, md_path, written = prompt_cache_metrics.write_metrics(root, metrics)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        assert written["estimated_static_tokens"] > 0


def _write_packet(root: str, name: str, static_body: str, dynamic_body: str) -> None:
    os.makedirs(os.path.join(root, "写作任务"), exist_ok=True)
    with open(os.path.join(root, "写作任务", name), "w", encoding="utf-8") as f:
        f.write(
            f'<static_context cache_control="ephemeral">\n{static_body}\n</static_context>\n'
            f"<dynamic_context>\n{dynamic_body}\n</dynamic_context>\n"
        )


def test_shared_static_prefix_true_when_static_blocks_identical():
    # 两个章节包的 static 块字节一致（整部不变的设定/风格）→ 缓存可跨章共享。
    with tempfile.TemporaryDirectory() as root:
        stable = "## 必读源文件\n- 设定/世界观.md\n## Demo 风格锚点\n- 冷峻克制"
        _write_packet(root, "第01章.md", stable, "本章章纲：雨夜获玉佩。")
        _write_packet(root, "第02章.md", stable, "本章章纲：拍卖会掉马。")

        metrics = prompt_cache_metrics.collect_metrics(root)
        assert metrics["shared_static_prefix"] is True
        assert metrics["static_prefix_variants"] == 1
        assert metrics["static_prefix_packets"] == 2
        assert not any("static_context 前缀不一致" in r for r in metrics["recommendations"])


def test_shared_static_prefix_false_flags_per_chapter_leak():
    # 逐章内容（第NN章/本章）漏进 static 块 → static 前缀逐章漂移，缓存命中归零，并定位泄漏来源。
    with tempfile.TemporaryDirectory() as root:
        _write_packet(root, "第01章.md", "## 必读源文件\n- 设定/世界观.md\n本章章纲：第01章雨夜", "动态")
        _write_packet(root, "第02章.md", "## 必读源文件\n- 设定/世界观.md\n本章章纲：第02章掉马", "动态")

        metrics = prompt_cache_metrics.collect_metrics(root)
        assert metrics["shared_static_prefix"] is False
        assert metrics["static_prefix_variants"] == 2
        recs = " ".join(metrics["recommendations"])
        assert "static_context 前缀不一致" in recs
        assert "疑似逐章" in recs  # 泄漏定位命中 第NN章/本章


def test_prompt_cache_metrics_records_real_usage_jsonl():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "写作任务"), exist_ok=True)
        with open(os.path.join(root, "写作任务", "第01章.md"), "w", encoding="utf-8") as f:
            f.write(
                '<static_context cache_control="ephemeral">设定</static_context>\n'
                '<dynamic_context>本章任务</dynamic_context>\n'
            )

        path, record = prompt_cache_metrics.record_usage(
            root,
            {"usage": {"input_tokens": 2000, "input_token_details": {"cached_tokens": 800}}},
            source="openai.responses:test",
        )
        assert os.path.exists(path)
        assert record["cached_input_tokens"] == 800

        metrics = prompt_cache_metrics.collect_metrics(root)
        assert metrics["actual_usage"]["record_count"] == 1
        assert metrics["actual_usage"]["input_tokens"] == 2000
        assert metrics["actual_cache_hit_ratio"] == 0.4
