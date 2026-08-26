#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("update_plan.py")
SPEC = importlib.util.spec_from_file_location("mv_update_plan_under_test", SCRIPT)
update_plan = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(update_plan)


def test_nested_skill_and_stage_mapping_table() -> None:
    cases = (
        ("skills/mv/mv-video/scripts/video_jobs.py", "mv-video", "video_jobs"),
        ("skills/mv/mv-video/scripts/video_qc.py", "mv-video", "video"),
        ("skills/mv/mv-compose/scripts/delivery_qc.py", "mv-compose", "compose"),
        ("skills/mv/mv-progress/SKILL.md", "mv-progress", None),
        ("skills/mv/SKILL.md", "mv", "setup"),
        ("outside-workspace/not-a-skill/SKILL.md", None, None),
    )
    for path, expected_skill, expected_stage in cases:
        assert update_plan.skill_name_for_relpath(path) == expected_skill, path
        assert update_plan.stage_for_changed_file(path) == expected_stage, path


def test_reversible_replay_is_a_machine_action_without_blanket_confirmation() -> None:
    steps = update_plan.build_execution_steps("/work/mv", {
        "rebuild_needed": True,
        "rerun_from": "image",
        "rerun_until": "compose",
    })
    actions = {step.get("action"): step for step in steps if step.get("type") == "machine_action"}
    replay = actions["replay_reversible_stage_range"]
    assert replay["from_stage"] == "image"
    assert replay["through_stage"] == "compose"
    assert replay["requires_user_confirmation"] is False
    assert "phase_budget_missing_or_expired" in replay["stop_before"]
    assert "final_human_acceptance" in replay["stop_before"]
    assert actions["snapshot_current_outputs"]["strategy"] == "versioned_copy_before_replace"
    machine_order = [step["action"] for step in steps if step.get("type") == "machine_action"]
    assert machine_order == ["snapshot_current_outputs", "replay_reversible_stage_range"]
    assert all(step.get("purpose") != "确认返工范围" for step in steps)


def test_atomic_json_uses_unique_temps_under_concurrent_writers(tmp_path: Path) -> None:
    target = tmp_path / "生产数据" / "plan.json"

    def write(index: int) -> None:
        update_plan.write_json(str(target), {"writer": index, "payload": "x" * 2000})

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(32)))

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["writer"] in range(32)
    assert payload["payload"] == "x" * 2000
    assert not list(target.parent.glob(f".{target.name}.tmp.*"))
