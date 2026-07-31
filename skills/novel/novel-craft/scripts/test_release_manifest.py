#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import release_manifest


def write_json(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def make_project(root: str) -> None:
    os.makedirs(os.path.join(root, "章节"))
    os.makedirs(os.path.join(root, "导出"))
    os.makedirs(os.path.join(root, "审稿"))
    os.makedirs(os.path.join(root, "评分"))
    os.makedirs(os.path.join(root, "合规"))
    write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "kind": "create", "rights_status": "original", "outputs": ["txt"]})
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# 设置\n文本主创模式：AI辅助\n")
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("# 第1章\n正文\n")
    with open(os.path.join(root, "导出", "测试书.txt"), "w", encoding="utf-8") as f:
        f.write("正文\n")


def write_ready_evidence(root: str) -> None:
    review_snapshot = release_manifest.snapshot_chapters(root, mode="review:full")
    score_snapshot = release_manifest.snapshot_chapters(root, mode="score:full")
    write_json(os.path.join(root, "审稿", "review_report.json"), {
        "schema_version": 1,
        "kind": "novel_review_report",
        "project_root": root,
        "generated_at": "2026-06-26",
        "scope": {"mode": "full"},
        "source_snapshot": review_snapshot,
        "summary": {
            "blocking_count": 0,
            "suggestion_count": 0,
            "polish_count": 0,
            "waiver_count": 0,
            "verdict": "pass",
        },
        "mechanical_findings_path": "",
        "waivers": [],
        "findings": [],
        "next_actions": [],
    })
    write_json(os.path.join(root, "评分", "score_task.json"), {
        "schema_version": 1,
        "kind": "novel_score_task",
        "source_snapshot": score_snapshot,
    })
    write_json(os.path.join(root, "评分", "score_report.json"), {
        "schema_version": 1,
        "kind": "novel_score_report",
        "project_root": root,
        "generated_at": "2026-06-26",
        "target_platform": "测试平台",
        "score_task_id": "score-test",
        "score_task_path": "评分/score_task.json",
        "assessment_prompt_hash": "abc",
        "scope": {"mode": "full", "chapter_count": 1},
        "source_snapshot": score_snapshot,
        "market_baseline": {"freshness": {"status": "fresh", "blocking": False}},
        "scores": [],
        "deductions": [],
        "total_score": 80,
        "tier": "B",
        "verdict": "小改",
        "production_decision": {"decision": "revise"},
        "rewrite_roi": "medium",
        "waivers": [],
        "next_actions": [],
    })
    write_json(os.path.join(root, "合规", "ai_usage.json"), {
        "schema_version": 1,
        "kind": "novel_ai_usage",
        "project_root": root,
        "title": "测试书",
        "publish_target": "测试平台",
        "human_contribution": "人工完成蓝图、设定、审稿与终稿取舍。",
        "rights_status": "original",
        "text_mode": "AI-assisted",
        "text_authorship_mode": "AI辅助",
        "image_mode": "未使用AI图片",
        "disclosure_detail": {
            "text_directness": "revision_only",
            "human_steering": "人工控制人物、结构和最终表达。",
            "replaceability": "assistive_non_replaceable",
            "direct_incorporation": "minor_phrases",
            "review_steps": ["人工通读", "设定一致性审稿"],
        },
        "chapter_usage": [{
            "chapter": 1,
            "path": "章节/第01章.md",
            "usage_mode": "AI-assisted",
            "human_review_required": True,
            "note": "",
        }],
    })
    write_json(os.path.join(root, "评分", "reader_test_plan.json"), {
        "schema_version": 1,
        "kind": "novel_reader_test_plan",
        "project_root": root,
        "generated_at": "2026-06-26",
        "platform": "内测",
        "source_name": "开篇测试",
        "scope": "opening:1-3",
        "target_reader": "测试平台核心读者",
        "min_sample": 30,
        "cohorts": [{
            "cohort_id": "C01",
            "description": "测试平台核心读者",
            "sample_source": "内测读者",
            "inclusion_criteria": "目标题材读者",
        }],
        "variants": [{
            "variant_id": "A",
            "take_id": "opening-v1",
            "hypothesis": "验证前三章钩子是否成立",
        }],
        "experiment_design": {
            "ab_test_id": "opening-test",
            "assignment": "随机分发",
            "comparison_unit": "variant_id/take_id within same scope",
            "randomization_note": "同一渠道同一日期",
        },
        "data_collection_fields": ["reader_id", "chapter", "event", "count", "timestamp", "ab_test_id", "variant_id", "take_id", "comment", "sentiment"],
        "privacy_note": "匿名化后导入。",
        "attribution_required_fields": ["ab_test_id", "variant_id", "take_id"],
        "metrics": [{
            "name": "completion_rate",
            "target": 0.65,
            "direction": "higher_is_better",
        }],
    })
    write_json(os.path.join(root, "评分", "reader_telemetry_summary.json"), {
        "schema_version": 1,
        "kind": "novel_reader_telemetry_summary",
        "project_root": root,
        "generated_at": "2026-06-27",
        "reader_test_plan": {"present": True, "path": "评分/reader_test_plan.json"},
        "aggregate": {
            "total_starts": 30,
            "total_completes": 21,
            "completion_rate": 0.7,
        },
        "weakest_chapters": [],
        "flags": [],
    })
    write_json(os.path.join(root, "导出", "metadata_pack.json"), {
        "schema_version": 1,
        "kind": "novel_metadata_pack",
        "generated_at": "2026-06-27",
        "project_root": root,
        "title": "测试书",
        "short_blurb": "主角在第一章面对选择并付出代价。",
        "long_description": "长简介。",
        "keywords": ["测试", "成长", "幻想"],
        "categories": ["Fantasy"],
        "age_rating": "16+",
        "rights_summary": {"rights_status": "original"},
    })
    compliance_lib = release_manifest._load_compliance_lib()
    write_json(os.path.join(root, "合规", "compliance_profile.json"), compliance_lib.build_profile(root))


def test_release_manifest_hashes_chapters_exports_and_evidence():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_json(os.path.join(root, "审稿", "review_report.json"), {"findings": []})

        manifest = release_manifest.build_manifest(root, release_name="v1")
        assert manifest["kind"] == "novel_release_manifest"
        assert manifest["release_name"] == "v1"
        assert len(manifest["chapters"]) == 1
        assert len(manifest["exports"]) == 1
        assert manifest["evidence"]["review_report"]["exists"] is True
        assert "score_report" in manifest["missing_evidence"]
        assert manifest["release_ready"] is False

        json_path, md_path = release_manifest.write_manifest(root, manifest)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)


def test_release_manifest_ready_when_required_evidence_is_current():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_ready_evidence(root)

        manifest = release_manifest.build_manifest(root, release_name="v1")
        assert manifest["release_ready"] is True, manifest["release_readiness"]
        assert manifest["release_profile"] == "platform_publish"
        assert manifest["release_readiness"]["blocker_count"] == 0
        assert manifest["chapter_source_snapshot"]["aggregate_hash"] == manifest["chapter_aggregate_hash"]


def test_platform_publish_requires_reader_telemetry_or_scoped_waiver():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_ready_evidence(root)
        os.remove(os.path.join(root, "评分", "reader_telemetry_summary.json"))

        blocked = release_manifest.build_manifest(root, release_name="v1")
        blocker_ids = [item["id"] for item in blocked["release_readiness"]["blockers"]]
        assert "RELEASE-READER-TELEMETRY-NOT-DECLARED" in blocker_ids
        assert blocked["release_ready"] is False

        with open(os.path.join(root, "审稿", "waiver_log.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": "WAIVER-READER-DATA-001",
                "type": "reader_data_missing",
                "reason": "封闭评审项目，无公开平台读者数据。",
                "affected_gate": "release_manifest",
                "source": "human",
                "scope": {"release_profile": "platform_publish"},
            }, ensure_ascii=False) + "\n")

        waived = release_manifest.build_manifest(root, release_name="v1")
        waived_ids = [item["id"] for item in waived["release_readiness"]["blockers"]]
        warning_ids = [item["id"] for item in waived["release_readiness"]["warnings"]]
        assert "RELEASE-READER-TELEMETRY-NOT-DECLARED" not in waived_ids
        assert "RELEASE-READER-TELEMETRY-WAIVED" in warning_ids
        assert waived["release_ready"] is True, waived["release_readiness"]


def test_release_manifest_builds_evidence_index_for_release_audit():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_ready_evidence(root)
        os.makedirs(os.path.join(root, "资料"), exist_ok=True)
        write_json(os.path.join(root, "评分", "market_baseline_2026-06-26.json"), {
            "kind": "novel_market_baseline",
            "baseline_date": "2026-06-26",
        })
        with open(os.path.join(root, "评分", "题材热榜_2026-06-26.md"), "w", encoding="utf-8") as f:
            f.write("# 题材热榜\n")
        write_json(os.path.join(root, "资料", "research_sources.json"), {
            "kind": "novel_research_sources",
            "sources": [],
        })

        manifest = release_manifest.build_manifest(root, release_name="v1")
        by_path = {item["path"]: item for item in manifest["evidence_index"]}
        assert "章节/第01章.md" in by_path
        assert "导出/测试书.txt" in by_path
        assert by_path["评分/score_report.json"]["source"] == "score_report"
        assert by_path["评分/market_baseline_2026-06-26.json"]["source"] == "market_baseline"
        assert by_path["资料/research_sources.json"]["purpose"].startswith("research source ledger")

        _json_path, md_path = release_manifest.write_manifest(root, manifest)
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
        assert "## Evidence Index" in md
        assert "评分/market_baseline_2026-06-26.json" in md


def test_release_manifest_blocks_stale_review_snapshot():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_ready_evidence(root)
        with open(os.path.join(root, "章节", "第01章.md"), "a", encoding="utf-8") as f:
            f.write("新增一句导致旧报告过期。\n")

        manifest = release_manifest.build_manifest(root, release_name="v1")
        assert manifest["release_ready"] is False
        blocker_ids = [item["id"] for item in manifest["release_readiness"]["blockers"]]
        assert "RELEASE-REVIEW_REPORT-STALE" in blocker_ids


def test_internal_draft_profile_does_not_require_publish_evidence():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)

        manifest = release_manifest.build_manifest(root, release_name="draft", release_profile="internal_draft")
        assert manifest["release_ready"] is True, manifest["release_readiness"]
        assert manifest["release_profile"] == "internal_draft"
        assert manifest["missing_evidence"]


def test_kdp_profile_requires_kdp_target_and_resolved_compliance_requirements():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_ready_evidence(root)

        missing_target = release_manifest.build_manifest(root, release_name="kdp", release_profile="kdp_publish")
        ids = [item["id"] for item in missing_target["release_readiness"]["blockers"]]
        assert "RELEASE-KDP-TARGET-MISSING" in ids

        with open(os.path.join(root, "_meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
        meta["target_platform"] = "KDP"
        write_json(os.path.join(root, "_meta.json"), meta)
        write_json(os.path.join(root, "合规", "compliance_profile.json"), {
            "schema_version": 1,
            "kind": "novel_compliance_profile",
            "target_axes": {"kdp": True, "raw_target_text": "KDP"},
            "requirements": [{
                "id": "kdp_ai_generated_disclosure",
                "severity": "blocking",
                "status": "action_required",
                "reason": "KDP UI disclosure not confirmed",
            }],
        })

        unresolved = release_manifest.build_manifest(root, release_name="kdp", release_profile="kdp_publish")
        ids = [item["id"] for item in unresolved["release_readiness"]["blockers"]]
        assert "RELEASE-KDP-KDP_AI_GENERATED_DISCLOSURE" in ids


def test_release_manifest_blocks_stale_compliance_fingerprint_for_publish_profiles():
    with tempfile.TemporaryDirectory() as root:
        make_project(root)
        write_ready_evidence(root)
        with open(os.path.join(root, "合规", "ai_usage.json"), encoding="utf-8") as f:
            ai_usage = json.load(f)
        ai_usage["human_contribution"] = "更新后的人工贡献说明。"
        write_json(os.path.join(root, "合规", "ai_usage.json"), ai_usage)

        manifest = release_manifest.build_manifest(root, release_name="v1")
        ids = [item["id"] for item in manifest["release_readiness"]["blockers"]]
        assert "RELEASE-COMPLIANCE-FINGERPRINT-STALE" in ids
