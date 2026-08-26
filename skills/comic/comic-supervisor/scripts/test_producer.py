from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import time

import pytest


MODULE = Path(__file__).with_name("producer.py")
SPEC = importlib.util.spec_from_file_location("comic_producer_tested", MODULE)
assert SPEC and SPEC.loader
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)

DIGEST_A = "a" * 64


def test_loop_executes_safe_actions_until_accepted(tmp_path: Path):
    actions = iter([
        {"status": "runnable", "action": "advance", "next_stage": "layout", "agent_role": "deterministic_runner", "recommended_commands": ["python3 -V"], "work_unit_input_digest": DIGEST_A},
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
        {"status": "specialist_required", "action": "write", "next_stage": "漫画脚本", "agent_role": "comic_writer", "work_unit_input_digest": DIGEST_A},
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
        planner=lambda _r, _c: {"status": "runnable", "action": "advance", "agent_role": "deterministic_runner", "recommended_commands": ["python3 -V"], "work_unit_input_digest": DIGEST_A},
        command_executor=lambda _argv: {"status": "complete"},
    )
    assert stuck["stop_reason"] == "non_convergent"


def test_crashed_claim_is_not_executed_twice(tmp_path: Path):
    action = {
        "status": "runnable", "action": "advance", "next_stage": "layout",
        "agent_role": "deterministic_runner", "recommended_commands": ["python3 -V"],
        "work_unit_input_digest": DIGEST_A,
    }
    script = (
        "import importlib.util, os, pathlib\n"
        f"p=pathlib.Path({str(MODULE)!r})\n"
        "s=importlib.util.spec_from_file_location('crash_producer',p)\n"
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
        f"r=pathlib.Path({str(tmp_path)!r}); c='第1话'\n"
        f"lease=m.producer_lease(r,c); token=lease.__enter__(); m.claim_action(r,c,{action!r},lease_token=token,frontier=m._frontier_snapshot(r,c))\n"
        "os._exit(23)\n"
    )
    crashed = subprocess.run([sys.executable, "-c", script], check=False)
    assert crashed.returncode == 23
    calls = []
    result = producer.run_loop(
        tmp_path, "第1话", planner=lambda _r, _c: action,
        command_executor=lambda argv: calls.append(argv) or {"status": "complete"},
    )
    assert result["stop_reason"] == "ambiguous_prior_claim"
    assert calls == []


def test_second_process_cannot_claim_same_chapter(tmp_path: Path):
    ready = tmp_path / "lease-ready"
    script = (
        "import importlib.util, pathlib, time\n"
        f"p=pathlib.Path({str(MODULE)!r})\n"
        "s=importlib.util.spec_from_file_location('lease_producer',p)\n"
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
        f"r=pathlib.Path({str(tmp_path)!r}); ready=pathlib.Path({str(ready)!r})\n"
        "lease=m.producer_lease(r,'第1话'); lease.__enter__(); ready.write_text('ready'); time.sleep(5)\n"
    )
    child = subprocess.Popen([sys.executable, "-c", script])
    try:
        deadline = time.time() + 3
        while not ready.exists() and time.time() < deadline:
            time.sleep(0.02)
        assert ready.exists()
        result = producer.run_loop(
            tmp_path, "第1话", planner=lambda _r, _c: {"status": "complete", "action": "complete"},
        )
        assert result["stop_reason"] == "producer_busy"
    finally:
        child.terminate()
        child.wait(timeout=3)


def test_wal_has_claim_before_finish_and_hash_bound_card(tmp_path: Path):
    actions = iter([
        {"status": "runnable", "action": "advance", "next_stage": "layout", "agent_role": "deterministic_runner", "recommended_commands": ["python3 -V"], "work_unit_input_digest": DIGEST_A},
        {"status": "complete", "action": "complete"},
    ])
    producer.run_loop(
        tmp_path, "第1话", planner=lambda _r, _c: next(actions),
        command_executor=lambda _argv: {"status": "complete"},
    )
    wal = tmp_path / "生产数据" / "producer" / "第1话" / "events.jsonl"
    rows = [json.loads(line) for line in wal.read_text(encoding="utf-8").splitlines()]
    phases = [row["phase"] for row in rows]
    assert phases.index("claimed") < phases.index("finished")
    claim = next(row for row in rows if row["phase"] == "claimed")
    card = tmp_path / "生产数据" / "producer" / "第1话" / "action_cards" / f"{claim['action_card_sha256']}.json"
    payload = json.loads(card.read_text(encoding="utf-8"))
    asserted_sha = payload.pop("action_card_sha256")
    assert producer._digest(payload) == asserted_sha


def test_real_crash_after_progress_side_effect_never_replays_command(tmp_path: Path):
    action = {
        "status": "runnable", "action": "advance", "next_stage": "layout",
        "agent_role": "deterministic_runner", "recommended_commands": ["python3 -V"],
        "work_unit_input_digest": DIGEST_A,
    }
    progress = tmp_path / "_进度.md"
    script = (
        "import importlib.util, os, pathlib\n"
        f"p=pathlib.Path({str(MODULE)!r})\n"
        "s=importlib.util.spec_from_file_location('side_effect_crash_producer',p)\n"
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
        f"r=pathlib.Path({str(tmp_path)!r}); action={action!r}\n"
        "def execute(_argv):\n"
        " (r/'_进度.md').write_text('side effect committed before crash\\n',encoding='utf-8')\n"
        " os._exit(41)\n"
        "m.run_loop(r,'第1话',planner=lambda _r,_c: action,command_executor=execute)\n"
    )
    crashed = subprocess.run([sys.executable, "-c", script], check=False)
    assert crashed.returncode == 41
    assert progress.read_text(encoding="utf-8").startswith("side effect committed")

    replayed: list[list[str]] = []
    result = producer.run_loop(
        tmp_path,
        "第1话",
        planner=lambda _r, _c: action,
        command_executor=lambda argv: replayed.append(list(argv)) or {"status": "complete"},
    )

    assert replayed == []
    assert result["stop_reason"] == "claimed_action_without_progress"
    claims = list((tmp_path / "生产数据" / "producer" / "第1话" / "claims").glob("*.json"))
    assert len(claims) == 1
    claim = json.loads(claims[0].read_text(encoding="utf-8"))
    assert claim["status"] == "reconciled_frontier_advanced"
    assert claim["command_records"][0]["status"] == "effect_observed_after_crash"
    command_wal = tmp_path / "生产数据" / "producer" / "第1话" / "commands.jsonl"
    assert "command_started" in command_wal.read_text(encoding="utf-8")


def test_new_upstream_input_revision_allows_same_command_as_new_work_unit(tmp_path: Path):
    base = {
        "status": "runnable", "action": "run_comic_batch_frontier",
        "next_stage": "页面排版", "agent_role": "deterministic_runner",
        "recommended_commands": ["python3 -V"],
    }
    calls: list[str] = []
    first_actions = iter([
        {**base, "work_unit_input_digest": "a" * 64},
        {"status": "complete", "action": "complete"},
    ])
    first = producer.run_loop(
        tmp_path, "第1话", planner=lambda _r, _c: next(first_actions),
        command_executor=lambda _argv: calls.append("v1") or {"status": "complete"},
    )
    assert first["status"] == "complete"

    second_actions = iter([
        {**base, "work_unit_input_digest": "b" * 64},
        {"status": "complete", "action": "complete"},
    ])
    second = producer.run_loop(
        tmp_path, "第1话", planner=lambda _r, _c: next(second_actions),
        command_executor=lambda _argv: calls.append("v2") or {"status": "complete"},
    )
    assert second["status"] == "complete"
    assert calls == ["v1", "v2"]
    claims = list((tmp_path / "生产数据" / "producer" / "第1话" / "claims").glob("*.json"))
    assert len(claims) == 2


@pytest.mark.parametrize("digest", ["", "legacy-unversioned", "a" * 63, "g" * 64])
def test_new_mutating_action_requires_canonical_work_unit_digest(tmp_path: Path, digest: str) -> None:
    calls: list[list[str]] = []
    action = {
        "status": "runnable", "action": "advance", "next_stage": "layout",
        "agent_role": "deterministic_runner", "recommended_commands": ["python3 -V"],
        "work_unit_input_digest": digest,
    }
    result = producer.run_loop(
        tmp_path, "第1话", planner=lambda _r, _c: action,
        command_executor=lambda argv: calls.append(list(argv)) or {"status": "complete"},
    )
    assert result["stop_reason"] == "invalid_action_contract"
    assert calls == []
    assert not list((tmp_path / "生产数据" / "producer" / "第1话" / "claims").glob("*.json"))


def test_legacy_digest_is_available_only_to_explicit_migration_path() -> None:
    action = {
        "status": "runnable", "action": "legacy-action", "next_stage": "layout",
        "recommended_commands": ["python3 -V"],
    }
    with pytest.raises(ValueError, match="invalid_action_contract"):
        producer._logical_action_material("第1话", action)
    migrated = producer._logical_action_material(
        "第1话", action, allow_legacy_migration=True
    )
    assert migrated["action_intent"]["work_unit_input_digest"] == producer.LEGACY_WORK_UNIT_DIGEST
