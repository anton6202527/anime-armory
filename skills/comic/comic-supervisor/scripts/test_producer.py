from pathlib import Path
import importlib.util


MODULE = Path(__file__).with_name("producer.py")
SPEC = importlib.util.spec_from_file_location("comic_producer_tested", MODULE)
assert SPEC and SPEC.loader
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)


def test_loop_executes_safe_actions_until_accepted(tmp_path: Path):
    actions = iter([
        {"status": "runnable", "action": "advance", "next_stage": "layout", "agent_role": "deterministic_runner", "recommended_commands": ["python3 -V"]},
        {"status": "complete", "action": "complete", "next_stage": "完成"},
    ])
    result = producer.run_loop(
        tmp_path, "第1话", planner=lambda _root, _chapter: next(actions),
        command_executor=lambda _argv: {"status": "complete", "returncode": 0},
    )
    assert result["status"] == "complete"
    assert result["stop_reason"] == "accepted"


def test_specialist_adapter_and_crash_resume_contract(tmp_path: Path):
    calls = []
    actions = iter([
        {"status": "specialist_required", "action": "write", "next_stage": "漫画脚本", "agent_role": "comic_writer"},
        {"status": "complete", "action": "complete", "next_stage": "完成"},
    ])
    result = producer.run_loop(
        tmp_path, "第1话", planner=lambda _root, _chapter: next(actions),
        specialist=lambda root, chapter, action, cycle: calls.append((chapter, cycle)) or {"status": "complete"},
    )
    assert result["status"] == "complete" and calls == [("第1话", 1)]
    assert (tmp_path / "生产数据" / "producer" / "第1话" / "producer_run.json").is_file()


def test_hard_boundary_and_non_convergence_stop(tmp_path: Path):
    boundary = producer.run_loop(
        tmp_path, "第1话", planner=lambda _r, _c: {"status": "needs_human", "action": "final_acceptance", "hard_boundary": True},
    )
    assert boundary["stop_reason"] == "final_acceptance"
    stuck = producer.run_loop(
        tmp_path, "第1话", max_cycles=6, max_stagnant_cycles=1,
        planner=lambda _r, _c: {"status": "runnable", "action": "advance", "agent_role": "deterministic_runner", "recommended_commands": ["python3 -V"]},
        command_executor=lambda _argv: {"status": "complete"},
    )
    assert stuck["stop_reason"] == "non_convergent"
