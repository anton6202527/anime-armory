#!/usr/bin/env python3
import importlib.util
import json
import sys
from pathlib import Path


for _name in ("contract", "progress_md"):
    sys.modules.pop(_name, None)
_PATH = Path(__file__).resolve().parent / "update_plan.py"
_SPEC = importlib.util.spec_from_file_location("ad_update_plan_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
update_plan = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(update_plan)


def test_nested_ad_child_path_maps_to_child_stage():
    assert update_plan.skill_name_for_relpath("skills/ad/ad-video/SKILL.md") == "ad-video"
    assert update_plan.stage_for_changed_file("skills/ad/ad-video/scripts/render.py") == "video"
    assert update_plan.stage_for_changed_file("skills/ad/ad-compose/scripts/deliver.py") == "compose"
    assert update_plan.skill_name_for_relpath("skills/ad/_lib/progress_md.py") == "ad"


def test_safe_replay_does_not_add_blanket_user_confirmation():
    steps = update_plan.build_execution_steps("/tmp/ad-project", {
        "rebuild_needed": True,
        "rerun_from": "script",
        "rerun_until": "review",
    })
    replay = next(step for step in steps if step.get("purpose") == "执行最小安全返工")
    assert replay["requires_confirmation"] is False
    assert "向用户确认" not in replay["instruction"]
    assert "仅在阶段预算" in replay["instruction"]
    assert any("ad-progress/scan.py" in step.get("command", "") for step in steps)


def test_atomic_writes_leave_no_shared_tmp_file(tmp_path):
    out = tmp_path / "生产数据" / "snapshot.json"
    update_plan.write_json(str(out), {"value": 1})
    assert json.loads(out.read_text(encoding="utf-8")) == {"value": 1}
    update_plan.write_text(str(out.with_suffix(".md")), "ok\n")
    assert not list(out.parent.glob("*.tmp"))
