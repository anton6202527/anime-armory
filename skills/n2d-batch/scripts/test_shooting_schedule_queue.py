from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("queue.py")
SCRIPT_DIR = SCRIPT.resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != SCRIPT_DIR]
shadow = sys.modules.get("queue")
if shadow is not None and Path(getattr(shadow, "__file__", "") or "").resolve() == SCRIPT.resolve():
    del sys.modules["queue"]
spec = importlib.util.spec_from_file_location("n2d_batch_queue_for_shooting_schedule_test", SCRIPT)
queue = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(queue)


def test_tasks_from_shooting_schedule_seed_are_clip_scoped(tmp_path: Path) -> None:
    seed = {
        "kind": "n2d_ai_shooting_schedule_batch_seed",
        "version": 1,
        "episode": "第1集",
        "status": "ready",
        "source_schedule": "脚本/第1集/ai_shooting_schedule.json",
        "batch_tasks": [{
            "episode": "第1集",
            "stage_key": "image",
            "clip_id": "Clip_01",
            "affected_shots": ["Clip_01"],
            "rerun_scope": "only Clip_01",
            "schedule_bucket": "pilot_high_risk_first",
        }],
    }

    tasks = queue.tasks_from_shooting_schedule(
        str(tmp_path),
        seed,
        cost_estimates=queue.DEFAULT_COST_ESTIMATES,
        max_retries=1,
    )

    assert len(tasks) == 1
    assert tasks[0]["stage_key"] == "image"
    assert tasks[0]["affected_shots"] == ["Clip_01"]
    assert "--shots Clip_01" in tasks[0]["command"]
    assert tasks[0]["source_schedule"] == "脚本/第1集/ai_shooting_schedule.json"
