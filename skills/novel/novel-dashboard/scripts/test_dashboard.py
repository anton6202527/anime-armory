#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import dashboard


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def test_dashboard_collects_core_signals_and_writes_outputs():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"))
        write_json(os.path.join(root, "_meta.json"), {"title": "测试小说", "kind": "create"})
        with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
            f.write("# 设置\n")
        with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
            f.write("# 进度\n")
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("# 第1章\n")
        write_json(os.path.join(root, "审稿", "review_report.json"), {
            "findings": [{"id": "R1", "blocking": True, "problem": "测试阻断"}],
        })
        write_json(os.path.join(root, "修订", "revision_plan.json"), {
            "tasks": [{"id": "T1", "priority": "P0", "conflict": True}],
        })
        write_json(os.path.join(root, "审稿", "review_board.json"), {
            "kind": "novel_review_board",
            "decision": "hold_for_editor_arbitration",
            "approval_required": True,
            "generated_at": "2026-06-26T00:00:00",
        })
        write_json(os.path.join(root, "生产数据", "prompt_cache_metrics.json"), {
            "kind": "novel_prompt_cache_metrics",
            "item_count": 2,
            "cache_control_coverage": 1.0,
            "static_context_ratio": 0.42,
            "cache_readiness_ratio": 0.42,
            "actual_cache_hit_ratio": 0.25,
            "actual_usage": {"record_count": 3},
            "estimated_static_tokens": 120,
        })
        write_json(os.path.join(root, "生产数据", "vector_store_eval.json"), {
            "kind": "novel_vector_store_project_eval",
            "passed": True,
            "thresholds": {"top_k": 3},
            "metrics": {"recall_at_k": 0.9, "mrr": 0.8, "case_count": 10, "failure_count": 1},
        })
        write_json(os.path.join(root, "生产数据", "supervisor_ledger.json"), {
            "kind": "novel_supervisor_circuit_ledger",
            "rolling_entries": {
                "rolling|review|finding": {
                    "stage": "review",
                    "finding_hash": "finding",
                    "failure_count": 3,
                    "cooldown_until": "2999-01-01T00:00:00",
                }
            },
        })
        write_json(os.path.join(root, "生产数据", "author_workflow.json"), {
            "kind": "novel_author_workflow",
            "current_step": "demo",
            "next_action": "python3 skills/novel/novel-craft/scripts/demo_readiness.py",
            "steps": [
                {"key": "setup", "label": "入口", "status": "done", "blockers": [], "warnings": []},
                {"key": "demo", "label": "Demo", "status": "pending", "blockers": ["demo gate"], "warnings": []},
            ],
        })
        from importlib.util import spec_from_file_location, module_from_spec
        queue_path = os.path.join(os.path.dirname(__file__), "..", "..", "novel-batch", "scripts", "queue.py")
        spec = spec_from_file_location("novel_batch_queue_test", os.path.abspath(queue_path))
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        q = module.NovelBatchQueue(root)
        q.upsert_tasks(module.build_tasks(root, "dashboard", [], "echo {task_id}", max_retries=0, priority="P2"))
        task = q.claim_task("worker-a")
        artifact_rel, _artifact = q.write_run_artifact(
            task,
            "worker-a",
            {"status": "completed", "returncode": 0, "elapsed_ms": 12},
            argv=["python3", "skills/novel/novel-dashboard/scripts/dashboard.py"],
            stdout="ok\n",
            stderr="",
            before={},
            after={},
        )
        q.attach_run_artifact(task["id"], artifact_rel, {"status": "completed", "elapsed_ms": 12})

        payload = dashboard.build_dashboard(root)
        assert payload["kind"] == "novel_dashboard"
        assert payload["review"]["blocking_count"] == 1
        assert payload["revision"]["task_count"] == 1
        assert payload["batch"]["summary"]["total"] == 1
        assert payload["batch"]["run_artifacts"]["count"] == 1
        assert payload["review_board"]["decision"] == "hold_for_editor_arbitration"
        assert payload["prompt_cache"]["cache_control_coverage"] == 1.0
        assert payload["prompt_cache"]["actual_cache_hit_ratio"] == 0.25
        assert payload["vector_eval"]["recall_at_k"] == 0.9
        assert payload["supervisor"]["rolling_tripped_count"] == 1
        assert payload["ops_slo"]["retrieval_recall_at_k"] == 0.9
        assert payload["author_workflow"]["current_step"] == "demo"
        assert payload["author_workflow"]["active_blockers"] == ["demo gate"]

        json_path, md_path, html_path = dashboard.write_outputs(root, payload, html_out=True)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        assert os.path.exists(html_path)
        assert os.path.exists(os.path.join(root, "生产数据", "novel_dashboard_history.jsonl"))
        with open(md_path, encoding="utf-8") as f:
            assert "author workflow" in f.read()


def test_review_snapshot_staleness_detected_live(tmp_path):
    # 过期自盲修复回归（王敦外传实证）：正文在 review 报告之后被改（扩写）时，dashboard
    # 每次 build 都要实时核验 source_snapshot——不能因为报告文件本身没变就报"0 过期"。
    import json
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dashboard as db

    root = str(tmp_path)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    ch = os.path.join(root, "章节", "第01章.md")
    with open(ch, "w", encoding="utf-8") as f:
        f.write("旧正文")
    lib = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "..", "_lib"))
    sys.path.insert(0, lib)
    from report_snapshot import snapshot_chapters
    snap = snapshot_chapters(root, mode="review:full")
    with open(os.path.join(root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
        json.dump({"findings": [], "source_snapshot": snap}, f, ensure_ascii=False)

    assert db.review_summary(root)["snapshot"]["fresh"] is True
    # 改稿（扩写）后：同一份报告必须被实时判过期
    with open(ch, "w", encoding="utf-8") as f:
        f.write("扩写后的正文，比原来长了很多")
    res = db.review_summary(root)
    assert res["snapshot"]["fresh"] is False
    assert "重新" in res["snapshot"]["msg"]
