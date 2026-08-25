from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("producer.py")
spec = importlib.util.spec_from_file_location("novel_producer_under_test", SCRIPT)
producer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(producer)


def _action(status: str, action: str, *, role: str = "workflow_orchestrator", stage: str = "review") -> dict:
    return {
        "status": status,
        "action": action,
        "next_stage": stage,
        "agent_role": role,
        "recommended_commands": ["python3 safe.py project"],
        "signals": {},
    }


def test_runs_safe_command_records_telemetry_then_reaches_completion(tmp_path: Path) -> None:
    plans = iter([_action("dispatch", "execute_review"), _action("complete", "none", stage="")])
    calls, records = [], []
    result = producer.run_loop(
        str(tmp_path),
        planner=lambda *a, **k: next(plans),
        command_executor=lambda argv: calls.append(argv) or {"status": "complete", "returncode": 0},
        recorder=lambda *a, **k: records.append(k) or {},
    )
    assert result["status"] == "complete"
    assert calls == [["python3", "safe.py", "project"]]
    assert [row["result"] for row in records] == ["started", "succeeded"]


def test_final_acceptance_is_a_hard_boundary(tmp_path: Path) -> None:
    calls = []
    result = producer.run_loop(
        str(tmp_path),
        planner=lambda *a, **k: _action("needs_human", "final_acceptance", role="human", stage=""),
        command_executor=lambda argv: calls.append(argv) or {"status": "complete"},
        recorder=lambda *a, **k: {},
    )
    assert result["stop_reason"] == "final_acceptance"
    assert calls == []


def test_specialist_work_uses_adapter(tmp_path: Path) -> None:
    plans = iter([
        _action("dispatch", "claim_or_complete_semantic_job", role="specialist_writer", stage="draft"),
        _action("complete", "none", stage=""),
    ])
    calls = []
    result = producer.run_loop(
        str(tmp_path), planner=lambda *a, **k: next(plans),
        specialist_executor=lambda action, cycle: calls.append((action, cycle)) or {"status": "complete"},
        recorder=lambda *a, **k: {},
    )
    assert result["status"] == "complete"
    assert len(calls) == 1


def test_placeholder_command_never_executes(tmp_path: Path) -> None:
    action = _action("self_healing", "rebuild")
    action["recommended_commands"] = ["tool --person <name>"]
    result = producer.run_loop(
        str(tmp_path), planner=lambda *a, **k: action,
        command_executor=lambda argv: {"status": "complete"}, recorder=lambda *a, **k: {},
    )
    assert result["stop_reason"] == "safe_command_required"
