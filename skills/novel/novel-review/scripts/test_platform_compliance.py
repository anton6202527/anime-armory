#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import platform_compliance as pc


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def test_microdrama_title_and_license_warn():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "_meta.json"), json.dumps({
            "title": "复仇暴君杀疯了",
            "purpose": "微短剧源书",
            "rights_status": "original",
        }, ensure_ascii=False))
        report = pc.check(root)
        codes = [item["code"] for item in report["findings"]]
        assert report["target_detected"] == "microdrama"
        assert "title_extreme_revenge" in codes
        assert "microdrama_license_todo" in codes
        assert report["verdict"] == "review"


def test_content_keyword_risk_requires_context_review_not_block():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "_meta.json"), json.dumps({"title": "测试", "purpose": "漫剧源书"}, ensure_ascii=False))
        _write(os.path.join(root, "章节", "第01章.md"), "# 第1章\n反派施以酷刑，血肉模糊。")
        report = pc.check(root)
        assert report["verdict"] == "review"
        hit = next(item for item in report["findings"] if item["code"] == "bloody_violence")
        assert hit["severity"] == "warn"
        assert hit["confidence"] == "heuristic"
        assert hit["evidence_kind"] == "keyword_candidate"


def test_public_domain_microdrama_flags_classic_ip_review():
    # 公版改写 + 漫剧目标 → 触发广电2026-04 经典IP魔改复核(warn·非block)
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "_meta.json"), json.dumps({
            "title": "王敦传新编",
            "purpose": "漫剧源书",
            "rights_status": "public-domain",
        }, ensure_ascii=False))
        report = pc.check(root)
        codes = [item["code"] for item in report["findings"]]
        assert "classic_ip_alteration_review" in codes
        assert report["verdict"] == "review"  # warn 级，不硬阻断
        # 二手来源只登记为待核验，不能伪装成主管部门硬规则。
        source = next(s for s in report["regulatory_sources"] if s["date"] == "2026-04-01")
        assert source["reliability"] == "secondary_unverified"


def test_explicit_classic_ip_flag_flags_even_when_rights_owned():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "_meta.json"), json.dumps({
            "title": "经典重制",
            "purpose": "漫剧源书",
            "rights_status": "user-declared",
            "classic_ip_adaptation": True,
        }, ensure_ascii=False))
        report = pc.check(root)
        assert any(i["code"] == "classic_ip_alteration_review" for i in report["findings"])


def test_public_domain_general_novel_does_not_flag_classic_ip():
    # 纯小说(非漫剧目标)不触发漫剧专属新规
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "_meta.json"), json.dumps({
            "title": "春山来信", "rights_status": "public-domain",
        }, ensure_ascii=False))
        _write(os.path.join(root, "章节", "第01章.md"), "# 第1章\n她收到一封旧信。")
        report = pc.check(root)
        assert all(i["code"] != "classic_ip_alteration_review" for i in report["findings"])


def test_general_clean_project_passes_and_writes():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "_meta.json"), json.dumps({"title": "春山来信", "rights_status": "original"}, ensure_ascii=False))
        _write(os.path.join(root, "章节", "第01章.md"), "# 第1章\n她收到一封旧信。")
        report = pc.check(root)
        assert report["verdict"] == "pass"
        json_path, md_path = pc.write_artifacts(root, report)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
