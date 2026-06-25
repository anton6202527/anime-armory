#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import edit_plan


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def test_edit_plan_consumes_revision_balance_and_simulate_inputs():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "修订", "revision_plan.json"), {
            "kind": "novel_revision_plan",
            "inputs": {"pacing_signals": True, "reader_panel_signals": True},
            "tasks": [{
                "id": "PACING-CH07",
                "priority": "P1",
                "chapter": 7,
                "title": "节奏诊断：第7章 注水偏弱",
                "reason": "目标推进不足。",
                "source": "pacing_signals",
                "return_to_stage": "balance",
                "recommended_skill": "novel-balance",
            }],
        })
        write_json(os.path.join(root, "评分", "pacing_signals.json"), {
            "kind": "novel_pacing_signals",
            "chapters": [{
                "chapter": 8,
                "verdict": "🔴 三项皆低，弃书点风险",
                "reason": "冲突、信息、回收都弱。",
            }],
            "烂尾预警": {
                "回收率": 0.25,
                "超期伏笔数": 3,
                "烂尾级超期": 1,
                "through_chapter": 9,
            },
        })
        write_json(os.path.join(root, "评分", "reader_panel_signals.json"), {
            "analysis_mode": "signal_only",
            "signal_only": True,
            "qualitative_completed": False,
            "chapters_read": [1, 2, 3],
            "hook_strength": 0.2,
            "retention_prior": 0.31,
        })

        plan = edit_plan.build_plan(root)
        assert plan["inputs"]["revision_plan"] is True
        assert plan["inputs"]["pacing_signals"] is True
        assert plan["inputs"]["reader_panel_signals"] is True

        titles = {task["title"] for task in plan["tasks"]}
        assert "节奏诊断：第7章 注水偏弱" in titles
        assert any("弃书点风险" in title for title in titles)
        assert any("伏笔回收编辑排程" in title for title in titles)
        assert "模拟读者信号仅作低权重留存先验" in titles
        assert any("模拟留存先验偏低" in title for title in titles)
