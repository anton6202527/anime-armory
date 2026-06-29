from __future__ import annotations

import importlib.util
import json
from pathlib import Path


QUEUE_SCRIPT = Path(__file__).with_name("queue.py")
queue_spec = importlib.util.spec_from_file_location("n2d_batch_queue_for_governance_test", QUEUE_SCRIPT)
queue = importlib.util.module_from_spec(queue_spec)
assert queue_spec.loader is not None
queue_spec.loader.exec_module(queue)

SCRIPT = Path(__file__).with_name("governance.py")
spec = importlib.util.spec_from_file_location("governance", SCRIPT)
governance = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(governance)


def test_governance_reports_dead_letters_and_writes_files(tmp_path: Path) -> None:
    task = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("image"),
        reason="progress",
        priority=1,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=0,
    )
    ledger = queue.make_queue(
        str(tmp_path),
        [task],
        max_concurrency=1,
        max_retries=0,
        budget=queue.apply_budget([task], None, None),
    )
    queue.save_queue(str(tmp_path), ledger)
    claimed = queue.claim(str(tmp_path), limit=1, worker="w1")
    queue.mark(
        str(tmp_path),
        claimed[0]["id"],
        "fail",
        "verification failed: missing output",
        runner={"exit_code": 0, "note": "verification failed: missing output"},
        expected_worker="w1",
        expected_attempt=1,
    )

    payload = governance.evaluate(str(tmp_path))
    governance.write_report(str(tmp_path), payload)

    assert payload["status"] == "critical"
    assert payload["summary"]["dead_letters"] == 1
    assert payload["dead_letters"][0]["error_class"] == "output_contract"
    pdir = tmp_path / "生产数据"
    assert (pdir / "dead_letter_queue.json").is_file()
    assert json.loads((pdir / "batch_governance.json").read_text(encoding="utf-8"))["kind"] == "n2d_batch_governance"


def test_init_slo_writes_template(tmp_path: Path) -> None:
    path = governance.write_slo(str(tmp_path))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_batch_slo"
    assert "image" in data["stages"]
