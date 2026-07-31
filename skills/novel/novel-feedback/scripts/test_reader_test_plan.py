#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile

import reader_test_plan


def test_reader_test_plan_contains_experiment_and_privacy_fields():
    with tempfile.TemporaryDirectory() as root:
        args = type("Args", (), {
            "project_root": root,
            "platform": "内测",
            "source_name": "开篇测试",
            "scope": "opening:1-3",
            "target_reader": "女频核心读者",
            "min_sample": 30,
            "min_completion": 0.65,
            "max_drop": 0.25,
            "min_completion_delta": 0.05,
            "take": ["opening-a", "opening-b"],
            "hypothesis": ["强钩子", "慢热"],
            "cohort": ["女频核心读者"],
            "sample_source": "内测群",
            "inclusion_criteria": "过去 30 天读过同题材",
            "ab_test_id": "opening-hook",
            "assignment": "随机分发",
            "randomization_note": "同一渠道同日",
            "privacy_note": "匿名化后导入。",
            "question": None,
        })()
        plan = reader_test_plan.build_plan(args)
        assert plan["cohorts"][0]["sample_source"] == "内测群"
        assert plan["experiment_design"]["ab_test_id"] == "opening-hook"
        assert {"ab_test_id", "variant_id", "take_id"} <= set(plan["attribution_required_fields"])
        assert "privacy_note" in plan
