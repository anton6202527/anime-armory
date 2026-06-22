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


def test_content_hard_risk_blocks():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "_meta.json"), json.dumps({"title": "测试", "purpose": "漫剧源书"}, ensure_ascii=False))
        _write(os.path.join(root, "章节", "第01章.md"), "# 第1章\n反派施以酷刑，血肉模糊。")
        report = pc.check(root)
        assert report["verdict"] == "block"
        assert any(item["code"] == "bloody_violence" for item in report["findings"])


def test_general_clean_project_passes_and_writes():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "_meta.json"), json.dumps({"title": "春山来信", "rights_status": "original"}, ensure_ascii=False))
        _write(os.path.join(root, "章节", "第01章.md"), "# 第1章\n她收到一封旧信。")
        report = pc.check(root)
        assert report["verdict"] == "pass"
        json_path, md_path = pc.write_artifacts(root, report)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
