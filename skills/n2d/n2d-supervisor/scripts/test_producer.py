from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("producer.py")
spec = importlib.util.spec_from_file_location("n2d_producer_under_test", SCRIPT)
producer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(producer)


def _plan(reason: str, *, stage: str = "image", dispatch: bool = False, safe: bool = False) -> dict:
    return {
        "episode": "第1集",
        "next_action": {
            "frontier": {"ep": "第1集", "stage_key": stage},
            "stop_reason": reason,
            "action_card": {"exact_command": "python3 skills/n2d/n2d-batch/scripts/runner.py /work --limit 1"},
        },
        "dispatch": {
            "stage_key": stage,
            "should_call_specialist": dispatch,
            "authorized_batch_execution": safe,
            "safe_local_execution": False,
            "specialist": {"name": "n2d-visual-agent"},
        },
        "summary": {"stop_reason": reason},
    }


def test_producer_runs_authorized_stage_then_reaches_done(tmp_path: Path) -> None:
    plans = iter([_plan("needs_stage_execution", dispatch=True, safe=True), _plan("done", stage="review")])
    calls = []

    result = producer.run_loop(
        str(tmp_path), "第1集",
        planner=lambda *a, **k: next(plans),
        command_executor=lambda argv: calls.append(argv) or {"status": "complete", "returncode": 0},
    )

    assert result["status"] == "complete"
    assert result["stop_reason"] == "done"
    assert len(calls) == 1
    assert producer.output_path(tmp_path, "第1集").is_file()
    journal = producer.journal_path(tmp_path, "第1集")
    rows = [line for line in journal.read_text(encoding="utf-8").splitlines() if line]
    assert len(rows) == result["cycles"] == 2
    assert result["iteration_budget"]["used_cycles"] == 2
    assert result["iteration_budget"]["remaining_cycles"] == 38
    wal = [
        json.loads(line) for line in producer.work_unit_wal_path(tmp_path, "第1集")
        .read_text(encoding="utf-8").splitlines() if line
    ]
    assert [row["event"] for row in wal] == [
        "work_unit_prepared", "work_unit_started", "work_unit_committed",
    ]


def test_producer_never_crosses_real_human_boundary(tmp_path: Path) -> None:
    called = []
    result = producer.run_loop(
        str(tmp_path), "第1集",
        planner=lambda *a, **k: _plan("needs_payment_confirm"),
        command_executor=lambda argv: called.append(argv) or {"status": "complete"},
    )
    assert result["stop_reason"] == "needs_payment_confirm"
    assert called == []


def test_producer_dispatches_agent_stage_through_specialist_adapter(tmp_path: Path) -> None:
    plans = iter([_plan("needs_agent_gen", stage="image_prompt", dispatch=True), _plan("done")])
    calls = []
    result = producer.run_loop(
        str(tmp_path), "第1集",
        planner=lambda *a, **k: next(plans),
        specialist_executor=lambda plan, cycle: calls.append((plan, cycle)) or {"status": "complete"},
    )
    assert result["status"] == "complete"
    assert len(calls) == 1


def test_producer_stops_non_convergent_frontier(tmp_path: Path) -> None:
    result = producer.run_loop(
        str(tmp_path), "第1集",
        max_stagnant_cycles=1,
        planner=lambda *a, **k: _plan("needs_stage_execution", dispatch=True, safe=True),
        command_executor=lambda argv: {"status": "complete"},
    )
    assert result["stop_reason"] == "non_convergent"


def test_episode_lease_rejects_a_concurrent_producer(tmp_path: Path) -> None:
    with producer.producer_lease(tmp_path, "第1集"):
        with pytest.raises(RuntimeError, match="producer_busy"):
            with producer.producer_lease(tmp_path, "第1集"):
                pass


def test_stable_work_unit_digest_ignores_cycle_and_generated_time() -> None:
    left = _plan("needs_stage_execution", dispatch=True, safe=True)
    right = _plan("needs_stage_execution", dispatch=True, safe=True)
    left["generated_at"] = "2026-01-01T00:00:00Z"
    right["generated_at"] = "2027-01-01T00:00:00Z"
    argv = ["python3", "skills/n2d/n2d-batch/scripts/runner.py", "/work", "--limit", "1"]
    assert producer.work_unit_digest(
        left, "第1集", operation_kind="stage_execution", argv=argv,
    ) == producer.work_unit_digest(
        right, "第1集", operation_kind="stage_execution", argv=argv,
    )
    assert producer.work_unit_digest(
        left, "第1集", operation_kind="stage_execution", argv=argv,
    ) != producer.work_unit_digest(
        right, "第1集", operation_kind="stage_execution", argv=[*argv, "--stop-on-fail"],
    )


def test_crash_after_effect_reconciles_advanced_frontier_without_replay(tmp_path: Path) -> None:
    state = {"effect_done": False}
    calls: list[list[str]] = []

    def planner(*args, **kwargs):
        return _plan("done", stage="review") if state["effect_done"] else _plan(
            "needs_stage_execution", dispatch=True, safe=True
        )

    def executor(argv):
        calls.append(list(argv))
        state["effect_done"] = True
        return {"status": "complete", "returncode": 0}

    def crash(phase, _record):
        if phase == "after_effect":
            raise RuntimeError("simulated process death")

    with pytest.raises(RuntimeError, match="simulated process death"):
        producer.run_loop(
            str(tmp_path), "第1集", planner=planner,
            command_executor=executor, fault_injector=crash,
        )
    lease = json.loads(
        (tmp_path / "生产数据" / "producer" / "producer_lease_第1集.json")
        .read_text(encoding="utf-8")
    )
    assert lease["status"] == "aborted"

    result = producer.run_loop(
        str(tmp_path), "第1集", planner=planner, command_executor=executor,
    )
    assert result["status"] == "complete"
    assert result["stop_reason"] == "done"
    assert len(calls) == 1
    recovery = [row for row in result["events"] if row.get("cycle") == 0]
    assert recovery and recovery[0]["status"] == "effect_observed_after_crash"
    claims = list((tmp_path / "生产数据" / "producer" / "work_units" / "第1集").glob("*.json"))
    assert len(claims) == 1
    assert json.loads(claims[0].read_text(encoding="utf-8"))["status"] == "effect_observed_after_crash"


def test_crash_after_prepare_reclaims_unstarted_work_unit_safely(tmp_path: Path) -> None:
    state = {"effect_done": False}
    calls: list[list[str]] = []

    def planner(*args, **kwargs):
        return _plan("done", stage="review") if state["effect_done"] else _plan(
            "needs_stage_execution", dispatch=True, safe=True
        )

    def executor(argv):
        calls.append(list(argv))
        state["effect_done"] = True
        return {"status": "complete", "returncode": 0}

    def crash(phase, _record):
        if phase == "after_prepared":
            raise RuntimeError("crashed before start")

    with pytest.raises(RuntimeError, match="before start"):
        producer.run_loop(
            str(tmp_path), "第1集", planner=planner, command_executor=executor,
            fault_injector=crash,
        )

    result = producer.run_loop(
        str(tmp_path), "第1集", planner=planner, command_executor=executor,
    )
    assert result["status"] == "complete"
    assert len(calls) == 1
    recovery = [row for row in result["events"] if row.get("cycle") == 0]
    assert recovery and recovery[0]["status"] == "abandoned_before_start"
    wal = [
        json.loads(line) for line in producer.work_unit_wal_path(tmp_path, "第1集")
        .read_text(encoding="utf-8").splitlines() if line
    ]
    assert [row["event"] for row in wal] == [
        "work_unit_prepared", "work_unit_reconciled", "work_unit_prepared",
        "work_unit_started", "work_unit_committed",
    ]


def test_crash_with_unchanged_frontier_stops_ambiguous_and_never_replays(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def executor(argv):
        calls.append(list(argv))
        return {"status": "complete", "returncode": 0}

    def crash(phase, _record):
        if phase == "after_effect":
            raise RuntimeError("simulated process death")

    planner = lambda *args, **kwargs: _plan("needs_stage_execution", dispatch=True, safe=True)
    with pytest.raises(RuntimeError, match="simulated process death"):
        producer.run_loop(
            str(tmp_path), "第1集", planner=planner,
            command_executor=executor, fault_injector=crash,
        )

    result = producer.run_loop(
        str(tmp_path), "第1集", planner=planner, command_executor=executor,
    )
    assert result["status"] == "stopped"
    assert result["stop_reason"] == "ambiguous_started_work_unit"
    assert len(calls) == 1
