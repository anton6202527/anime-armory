#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import revision_planner as rp


def test_revision_plan_merges_review_score_feedback_and_simulate():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": [{
                "problem": "第1章钩子弱",
                "blocking": True,
                "affected_files": ["章节/第01章.md"],
                "recommended_skill": "novel-rewrite",
                "return_to_stage": "rewrite",
            }]}, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "score_report.json"), "w", encoding="utf-8") as f:
            json.dump({"verdict": "大改", "rewrite_roi": "high", "next_actions": []}, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "reader_telemetry_summary.json"), "w", encoding="utf-8") as f:
            json.dump({
                "weakest_chapters": [2],
                "experiments": {"best_by_ab_test": [{
                    "ab_test_id": "hook",
                    "variant_id": "A",
                    "take_ids": ["take-a"],
                }]},
            }, f, ensure_ascii=False)
        with open(os.path.join(root, "评分", "reader_panel_signals.json"), "w", encoding="utf-8") as f:
            json.dump({"signal_only": True, "analysis_mode": "signal_only"}, f)

        plan = rp.build_plan(root)
        ids = {task["id"] for task in plan["tasks"]}
        assert {"REV-001", "SCORE-VERDICT", "FEEDBACK-CH02", "EXPERIMENT-hook", "SIMULATE-SIGNAL-ONLY"} <= ids
        json_path, md_path = rp.write_plan(root, plan)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
