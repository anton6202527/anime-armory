#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import demo_readiness


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def test_demo_readiness_blocks_commercial_project_without_score():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        write_json(os.path.join(root, "审稿", "demo_gate.json"), {"status": "passed", "style_anchor": {"summary": "短句强钩子"}})
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("# 第1章\n")

        report = demo_readiness.build_readiness(root)
        assert report["ready_for_batch"] is False
        ids = {item["id"] for item in report["issues"]}
        assert "DEMO-COMMERCIAL-SCORE-MISSING" in ids


def test_demo_readiness_passes_with_score_and_literary_anchors():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        write_json(os.path.join(root, "审稿", "demo_gate.json"), {
            "status": "passed",
            "style_anchor": {"summary": "短句强钩子"},
            "reader_contract": {"theme": "代价", "aesthetic_register": "冷峻克制"},
        })
        write_json(os.path.join(root, "评分", "score_report.json"), {
            "production_decision": {"decision": "go"},
            "verdict": "pass",
        })
        write_json(os.path.join(root, "设定", "aesthetic_bank.json"), {
            "kind": "novel_aesthetic_bank",
            "samples": [{"sample_id": "AES-001", "transfer_rule": "行动先行"}],
        })
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("# 第1章\n")

        report = demo_readiness.build_readiness(root)
        assert report["ready_for_batch"] is True
        assert report["literary_gate"]["score"] >= 60
