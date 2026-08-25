from __future__ import annotations

import importlib.util
from pathlib import Path


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
