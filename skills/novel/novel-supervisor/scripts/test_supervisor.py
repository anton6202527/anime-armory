#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import supervisor


def write_minimal_project(root: str) -> None:
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试书", "kind": "create"}, f)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# 设置\n")
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write("# 进度\n")


def test_supervisor_requests_revision_plan_for_review_blockers():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "审稿"))
        write_minimal_project(root)
        with open(os.path.join(root, "审稿", "review_report.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": [{"id": "R1", "blocking": True}]}, f)

        action = supervisor.decide_next_action(root)
        assert action["status"] == "self_healing"
        assert action["action"] == "build_revision_plan"
        assert "revision_planner.py" in action["recommended_commands"][0]


def test_supervisor_dispatches_next_stage_with_handoff_shape():
    with tempfile.TemporaryDirectory() as root:
        write_minimal_project(root)
        with open(os.path.join(root, "设定", "角色卡.md"), "w", encoding="utf-8") as f:
            f.write("角色\n")
        with open(os.path.join(root, "设定", "读者契约.md"), "w", encoding="utf-8") as f:
            f.write("契约\n")

        action = supervisor.decide_next_action(root)
        assert action["next_stage"] == "author_workflow"
        assert action["status"] == "dispatch"
        assert "author_workflow.py" in action["recommended_commands"][0]
        assert action["handoff"]["kind"] == "novel_specialist_handoff_contract"


def test_read_only_decisions_do_not_increment_circuit_ledger():
    with tempfile.TemporaryDirectory() as root:
        write_minimal_project(root)

        first = supervisor.decide_next_action(root)
        second = supervisor.decide_next_action(root)

        assert first["signals"]["retry_count"] == 0
        assert second["signals"]["retry_count"] == 0
        assert not os.path.exists(os.path.join(root, "生产数据", "supervisor_ledger.json"))


def test_three_failed_execution_records_trip_circuit_breaker_and_success_resets():
    with tempfile.TemporaryDirectory() as root:
        write_minimal_project(root)

        for _ in range(3):
            status = supervisor.record_execution_event(
                root,
                stage_key="review",
                result="failed",
                run_id="run-a",
                finding_hash="finding-1",
                reason="review still blocking",
            )

        assert status["failure_count"] == 3
        assert status["tripped"] is True
        assert supervisor.circuit_status(root, "review", run_id="run-a", finding_hash="finding-1")["tripped"] is True

        reset = supervisor.record_execution_event(
            root,
            stage_key="review",
            result="succeeded",
            run_id="run-a",
            finding_hash="finding-1",
            reason="fixed",
        )
        assert reset["failure_count"] == 0
        assert reset["tripped"] is False


def test_circuit_breaker_is_scoped_by_stage_run_and_finding_hash():
    with tempfile.TemporaryDirectory() as root:
        write_minimal_project(root)
        for _ in range(3):
            supervisor.record_execution_event(
                root,
                stage_key="review",
                result="failed",
                run_id="run-a",
                finding_hash="finding-1",
            )

        assert supervisor.circuit_status(root, "review", run_id="run-a", finding_hash="finding-1")["tripped"]
        assert not supervisor.circuit_status(root, "score", run_id="run-a", finding_hash="finding-1")["tripped"]
        assert not supervisor.circuit_status(root, "review", run_id="run-b", finding_hash="finding-1")["tripped"]
        assert not supervisor.circuit_status(root, "review", run_id="run-a", finding_hash="finding-2")["tripped"]


def test_decide_next_action_sees_run_and_finding_scoped_breaker_records():
    with tempfile.TemporaryDirectory() as root:
        write_minimal_project(root)
        for _ in range(3):
            supervisor.record_execution_event(
                root,
                stage_key="review",
                result="failed",
                run_id="run-a",
                finding_hash="finding-1",
                reason="same blocker returned",
            )

        original_dry_run = supervisor.dry_run_plan
        try:
            supervisor.dry_run_plan = lambda _root: {
                "title": "测试书",
                "next_stage": "review",
                "stages": [{"key": "review", "status": "ready", "agent_role": "specialist_reviewer"}],
            }
            action = supervisor.decide_next_action(root)
        finally:
            supervisor.dry_run_plan = original_dry_run

        assert action["status"] == "needs_human"
        assert action["action"] == "circuit_breaker_tripped"
        assert action["signals"]["retry_count"] == 3
        assert action["signals"]["circuit_breaker"]["tripped_entries"][0]["run_id"] == "run-a"


def test_rolling_circuit_breaker_trips_across_runs_for_same_finding():
    with tempfile.TemporaryDirectory() as root:
        write_minimal_project(root)
        for run_id in ("run-a", "run-b", "run-c"):
            supervisor.record_execution_event(
                root,
                stage_key="review",
                result="failed",
                run_id=run_id,
                finding_hash="same-finding",
                reason="same blocker returned",
            )

        assert not supervisor.circuit_status(root, "review", run_id="run-c", finding_hash="same-finding")["tripped"]
        aggregate = supervisor.aggregate_circuit_status(root, "review", active_run_id="run-c")
        assert aggregate["tripped"] is True
        rolling = [item for item in aggregate["tripped_entries"] if item.get("scope") == "rolling"]
        assert rolling
        assert rolling[0]["failure_count"] == 3


def test_circuit_breaker_armed_flag_reflects_telemetry_presence():
    # B1·诚实可见化：没有任何执行回报 → armed=False（inert·静默不保护）；喂一条遥测后 armed=True
    with tempfile.TemporaryDirectory() as root:
        cold = supervisor.aggregate_circuit_status(root, "draft")
        assert cold["armed"] is False and cold["telemetry_present"] is False
        assert cold["tripped"] is False and cold["note"]   # 有明确说明为何 inert
        supervisor.record_execution_event(root, stage_key="draft", result="started", run_id="r1")
        warm = supervisor.aggregate_circuit_status(root, "draft", active_run_id="r1")
        assert warm["armed"] is True and warm["telemetry_present"] is True
        assert warm["note"] == ""
