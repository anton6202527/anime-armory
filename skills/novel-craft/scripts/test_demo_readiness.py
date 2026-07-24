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


# ── 黄金三章硬对表 ───────────────────────────────────────────────────────────

def _golden_project(root, *, conflicts, promises=None, chapter_text="# 第1章\n平静叙述。"):
    write_json(os.path.join(root, "_meta.json"),
               {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
    gate = {"status": "passed", "style_anchor": {"summary": "短句强钩子"}}
    if promises is not None:
        gate["reader_contract"] = {"theme": "代价", "reader_promises": promises}
    write_json(os.path.join(root, "审稿", "demo_gate.json"), gate)
    write_json(os.path.join(root, "设定", "scene_cards.json"), {
        "kind": "novel_scene_cards",
        "scenes": [{"chapter": i + 1, "scene_no": 1, "conflict": c}
                   for i, c in enumerate(conflicts)],
    })
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    for i in range(1, 4):
        with open(os.path.join(root, "章节", f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(chapter_text)


def test_golden_chapters_flag_hollow_conflict():
    with tempfile.TemporaryDirectory() as root:
        _golden_project(root, conflicts=["", "", "宗门大比"])  # 2/3 为空 → 矛盾未立
        ids = {i["id"] for i in demo_readiness.build_readiness(root)["issues"]}
        assert "DEMO-OPENING-CONFLICT-HOLLOW" in ids


def test_golden_chapters_quiet_when_conflicts_filled():
    with tempfile.TemporaryDirectory() as root:
        _golden_project(root, conflicts=["夺舍危机", "追杀", "宗门大比"])
        ids = {i["id"] for i in demo_readiness.build_readiness(root)["issues"]}
        assert "DEMO-OPENING-CONFLICT-HOLLOW" not in ids


def test_golden_chapters_flag_selling_point_late():
    with tempfile.TemporaryDirectory() as root:
        _golden_project(root, conflicts=["夺舍危机"],
                        promises=["看主角用炼丹金手指逆袭"],
                        chapter_text="# 第1章\n他在山下砍柴，日子平淡。")
        ids = {i["id"] for i in demo_readiness.build_readiness(root)["issues"]}
        assert "DEMO-SELLING-POINT-LATE" in ids


def test_golden_chapters_quiet_when_promise_seeded_early():
    with tempfile.TemporaryDirectory() as root:
        _golden_project(root, conflicts=["夺舍危机"],
                        promises=["看主角用炼丹金手指逆袭"],
                        chapter_text="# 第1章\n他握着祖传丹炉，第一次尝试炼丹。")
        ids = {i["id"] for i in demo_readiness.build_readiness(root)["issues"]}
        assert "DEMO-SELLING-POINT-LATE" not in ids


def test_golden_chapters_skip_without_cards_or_promises():
    # scene_cards 与 reader_promises 都缺 → 两项硬对表整体优雅跳过（不臆造）
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"),
                   {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        write_json(os.path.join(root, "审稿", "demo_gate.json"),
                   {"status": "passed", "style_anchor": {"summary": "短句强钩子"}})
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("# 第1章\n")
        ids = {i["id"] for i in demo_readiness.build_readiness(root)["issues"]}
        assert not {"DEMO-OPENING-CONFLICT-HOLLOW", "DEMO-SELLING-POINT-LATE"} & ids
