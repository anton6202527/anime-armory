#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import pytest

import build_reference_distribution as brd


def _write_report(path, total=80):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_score_report",
            "total_score": total,
            "tier": "合格偏上",
            "verdict": "小改",
            "scores": [
                {"dimension": "topic_heat", "raw_score": 8},
                {"dimension": "retention", "raw_score": 7},
            ],
        }, f, ensure_ascii=False)


def test_build_distribution_from_score_report():
    with tempfile.TemporaryDirectory() as tmp:
        report = os.path.join(tmp, "proj", "评分", "score_report.json")
        _write_report(report, total=82)
        sample = brd.sample_from_report({
            "path": report,
            "rights_status": "original",
            "source_label": "自有样本",
            "title": "样本A",
        })
        payload = brd.build_distribution([sample], title="测试分布")
        assert payload["kind"] == "novel_reference_score_distribution"
        assert payload["sample_count"] == 1
        assert payload["samples"][0]["scores"]["topic_heat"] == 8


def test_parse_sample_rejects_unknown_rights():
    with pytest.raises(Exception):
        brd.parse_sample("score_report.json|unknown")
