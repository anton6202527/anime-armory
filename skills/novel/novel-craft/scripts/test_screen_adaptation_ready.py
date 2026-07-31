#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import screen_adaptation_ready as sar


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def make_ready_project(root):
    write_json(os.path.join(root, "_meta.json"), {
        "title": "测试书",
        "rights_status": "original",
        "target_platform": "红果",
        "purpose": "漫剧源书",
    })
    write(os.path.join(root, "_设置.md"), "- 目标平台：红果\n- 小说用途：漫剧源书\n")
    write(os.path.join(root, "章节", "第01章.md"), "# 第1章\n正文\n")
    write(os.path.join(root, "设定", "角色卡.md"), "主角：沈念\n")
    write(os.path.join(root, "设定", "世界观.md"), "世界观\n")
    write(os.path.join(root, "设定", "章纲.md"), "第1章 开局\n")
    write(os.path.join(root, "设定", "读者契约.md"), "核心承诺\n")
    write_json(os.path.join(root, "合规", "ai_usage.json"), {"kind": "novel_ai_usage"})
    write_json(os.path.join(root, "审稿", "review_report.json"), {
        "summary": {"blocking_count": 0},
        "findings": [],
    })
    write_json(os.path.join(root, "评分", "score_report.json"), {
        "verdict": "小改",
        "adaptation_check": {"low_potential": False, "scores": {}},
    })
    write_json(os.path.join(root, "评分", "market_baseline_2026-06-26.json"), {"kind": "novel_market_baseline"})


def test_screen_adaptation_ready_passes_clean_project_with_minor_warnings():
    with tempfile.TemporaryDirectory() as root:
        make_ready_project(root)
        report = sar.collect(root)
        assert report["verdict"] in {"ready", "review"}
        assert report["counts"]["block"] == 0
        assert report["target_is_short_drama"] is True
        json_path, md_path = sar.write_report(root, report)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)


def test_screen_adaptation_ready_blocks_missing_rights_review_score_ai_usage():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {
            "title": "测试书",
            "rights_status": "unknown",
            "target_platform": "红果",
        })
        report = sar.collect(root)
        block_ids = {item["id"] for item in report["checks"] if item["status"] == "block"}
        assert "TEXT-FILES" in block_ids
        assert "RIGHTS" in block_ids
        assert "AI-USAGE" in block_ids
        assert "REVIEW" in block_ids
        assert "SCORE" in block_ids
        assert report["verdict"] == "block"


def test_short_drama_target_requires_adaptation_check():
    with tempfile.TemporaryDirectory() as root:
        make_ready_project(root)
        write_json(os.path.join(root, "评分", "score_report.json"), {"verdict": "小改"})
        report = sar.collect(root)
        score = next(item for item in report["checks"] if item["id"] == "SCORE")
        assert score["status"] == "block"
        assert "adaptation_check" in score["message"]
