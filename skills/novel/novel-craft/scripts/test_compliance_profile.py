#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "_lib"))
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
LIB_PATH = os.path.join(LIB_DIR, "compliance_profile.py")
SCRIPT_PATH = os.path.join(HERE, "compliance_profile.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cp = load_module("compliance_profile_lib_under_test", LIB_PATH)
cli = load_module("compliance_profile_cli_under_test", SCRIPT_PATH)


def test_kdp_ai_generated_requires_disclosure_until_confirmed():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "合规"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"target_platform": "KDP", "rights_status": "original"}, f, ensure_ascii=False)
        with open(os.path.join(root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
            json.dump({"text_mode": "AI-generated", "kind": "novel_ai_usage", "schema_version": 1}, f, ensure_ascii=False)

        profile = cp.build_profile(root)
        blockers, _warnings = cp.gate_items(profile)
        assert any(item["id"] == "kdp_ai_generated_disclosure" for item in blockers)

        cli._confirm(root, "kdp_ai_generated_disclosure", note="KDP UI checked")
        profile = cp.build_profile(root)
        blockers, _warnings = cp.gate_items(profile)
        assert not any(item["id"] == "kdp_ai_generated_disclosure" for item in blockers)


def test_kdp_ai_generated_image_requires_disclosure_even_without_ai_text():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "合规"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"target_platform": "KDP", "rights_status": "original"}, f, ensure_ascii=False)
        with open(os.path.join(root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
            json.dump({
                "text_mode": "未使用AI文本",
                "image_mode": "AI-generated",
                "kind": "novel_ai_usage",
                "schema_version": 1,
            }, f, ensure_ascii=False)

        profile = cp.build_profile(root)
        blockers, _warnings = cp.gate_items(profile)
        assert any(item["id"] == "kdp_ai_generated_disclosure" for item in blockers)


def test_kdp_ai_generated_translation_requires_disclosure():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "合规"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"target_platform": "KDP", "rights_status": "original"}, f, ensure_ascii=False)
        with open(os.path.join(root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
            json.dump({
                "text_mode": "未使用AI文本",
                "image_mode": "未使用AI图片",
                "translation_mode": "AI-generated",
            }, f, ensure_ascii=False)
        profile = cp.build_profile(root)
        blockers, _warnings = cp.gate_items(profile)
        assert any(item["id"] == "kdp_ai_generated_disclosure" for item in blockers)


def test_write_profile_outputs_json_and_markdown():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"target_platform": "Amazon", "rights_status": "original"}, f, ensure_ascii=False)
        json_path, md_path = cp.write_profile(root)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        payload = json.load(open(json_path, encoding="utf-8"))
        assert payload["kind"] == "novel_compliance_profile"
        assert payload["input_fingerprint"]
        assert "input_fingerprint_components" in payload


def test_eu_human_or_ai_assisted_fiction_is_not_auto_blocked():
    for mode in ("未使用AI文本", "AI-assisted"):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "合规"), exist_ok=True)
            with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"distribution_regions": ["EU"], "rights_status": "original"}, f)
            with open(os.path.join(root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
                json.dump({"text_mode": mode, "human_contribution": "作者完成最终表达与逐章复核"}, f, ensure_ascii=False)
            profile = cp.build_profile(root)
            blockers, _warnings = cp.gate_items(profile)
            assert not any(item["id"].startswith("eu_ai_act") for item in blockers)


def test_eu_ai_generated_fiction_gets_scope_note_not_universal_label_block():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "合规"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"distribution_regions": ["EU"], "rights_status": "original"}, f)
        with open(os.path.join(root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
            json.dump({"text_mode": "AI-generated"}, f)
        profile = cp.build_profile(root)
        req = next(item for item in profile["requirements"] if item["id"] == "eu_ai_act_article_50_scope_note")
        assert req["severity"] == "info"
        blockers, _warnings = cp.gate_items(profile)
        assert not any(item["id"].startswith("eu_ai_act") for item in blockers)


def test_eu_public_interest_ai_text_without_editorial_control_requires_review_only():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "合规"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({
                "distribution_regions": ["EU"],
                "rights_status": "original",
                "public_interest_publication": True,
            }, f)
        with open(os.path.join(root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
            json.dump({"text_mode": "AI-generated"}, f)
        profile = cp.build_profile(root)
        blockers, warnings = cp.gate_items(profile)
        assert not any(item["id"].startswith("eu_ai_act") for item in blockers)
        assert any(item["id"] == "eu_ai_act_article_50_public_interest_text" for item in warnings)


def test_china_ai_assisted_requires_scope_review_not_generated_content_block():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "合规"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"distribution_regions": ["CN"], "rights_status": "original"}, f)
        with open(os.path.join(root, "合规", "ai_usage.json"), "w", encoding="utf-8") as f:
            json.dump({"text_mode": "AI-assisted"}, f)
        profile = cp.build_profile(root)
        blockers, warnings = cp.gate_items(profile)
        assert not any(item["id"] == "cn_ai_labeling_plan" for item in blockers)
        assert any(item["id"] == "cn_ai_assisted_scope_review" for item in warnings)
