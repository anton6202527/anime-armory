#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "novel", "_lib"))
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


def test_write_profile_outputs_json_and_markdown():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"target_platform": "Amazon", "rights_status": "original"}, f, ensure_ascii=False)
        json_path, md_path = cp.write_profile(root)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        payload = json.load(open(json_path, encoding="utf-8"))
        assert payload["kind"] == "novel_compliance_profile"
