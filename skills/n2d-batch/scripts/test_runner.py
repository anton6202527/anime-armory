from __future__ import annotations

import importlib.util
import json
from pathlib import Path


QUEUE_SCRIPT = Path(__file__).with_name("queue.py")
queue_spec = importlib.util.spec_from_file_location("n2d_batch_queue", QUEUE_SCRIPT)
queue = importlib.util.module_from_spec(queue_spec)
assert queue_spec.loader is not None
queue_spec.loader.exec_module(queue)

RUNNER_SCRIPT = Path(__file__).with_name("runner.py")
runner_spec = importlib.util.spec_from_file_location("n2d_batch_runner", RUNNER_SCRIPT)
runner = importlib.util.module_from_spec(runner_spec)
assert runner_spec.loader is not None
runner_spec.loader.exec_module(runner)


def write_progress(root: Path) -> None:
    (root / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 1/3 | ⬜ | ⬜ | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )


def write_image_queue(root: Path, *, max_retries: int = 1) -> None:
    write_progress(root)
    tasks = queue.route_tasks(
        str(root),
        episodes=None,
        stage_filters={"image"},
        cost_estimates=queue.load_cost_estimates(str(root)),
        max_retries=max_retries,
    )
    ledger = queue.make_queue(
        str(root),
        tasks,
        max_concurrency=1,
        max_retries=max_retries,
        budget=queue.apply_budget(tasks, None, None),
    )
    queue.save_queue(str(root), ledger)


def write_config(root: Path, command: str) -> Path:
    path = root / "生产数据" / "batch_runner.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"commands": {"image": command}}, ensure_ascii=False), encoding="utf-8")
    return path


def test_runner_claims_executes_marks_done_and_records_dashboard(tmp_path: Path) -> None:
    write_image_queue(tmp_path)
    out_file = tmp_path / "runner_was_here.txt"
    config = write_config(
        tmp_path,
        "python3 -c \"import os, pathlib; pathlib.Path(os.environ['N2D_ROOT']).joinpath('runner_was_here.txt').write_text(os.environ['N2D_TASK_ID'], encoding='utf-8')\"",
    )

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config))

    assert result["processed"] == 1
    assert out_file.read_text(encoding="utf-8").startswith("001-image")
    loaded = queue.load_queue(str(tmp_path))
    assert loaded["tasks"][0]["status"] == "done"
    assert loaded["tasks"][0]["attempts"] == 1
    events = (tmp_path / "生产数据" / "production_events.jsonl").read_text(encoding="utf-8").splitlines()
    assert any("n2d-batch/scripts/runner.py" in line for line in events)


def test_runner_failure_requeues_then_fails_after_retry_limit(tmp_path: Path) -> None:
    write_image_queue(tmp_path, max_retries=1)
    config = write_config(tmp_path, "python3 -c \"import sys; sys.exit(7)\"")

    first = runner.run_once(str(tmp_path), limit=1, config_path=str(config))
    loaded = queue.load_queue(str(tmp_path))
    assert first["results"][0]["runner_status"] == "fail"
    assert loaded["tasks"][0]["status"] == "retry_queued"
    assert loaded["tasks"][0]["attempts"] == 1

    second = runner.run_once(str(tmp_path), limit=1, config_path=str(config))
    loaded = queue.load_queue(str(tmp_path))
    assert second["results"][0]["runner_status"] == "fail"
    assert loaded["tasks"][0]["status"] == "failed"
    assert loaded["tasks"][0]["attempts"] == 2
    assert loaded["tasks"][0]["last_runner"]["exit_code"] == 7


def test_runner_marks_unconfigured_slash_command_as_retryable_failure(tmp_path: Path) -> None:
    write_image_queue(tmp_path, max_retries=1)

    result = runner.run_once(str(tmp_path), limit=1)
    loaded = queue.load_queue(str(tmp_path))

    assert result["results"][0]["runner_status"] == "fail"
    assert "slash command" in result["results"][0]["note"]
    assert loaded["tasks"][0]["status"] == "retry_queued"


def test_runner_marks_done_even_when_dashboard_telemetry_fails(tmp_path: Path) -> None:
    write_image_queue(tmp_path)
    config = write_config(tmp_path, "python3 -c \"pass\"")
    original = runner.append_runner_event

    def boom(*args, **kwargs):
        raise RuntimeError("dashboard unavailable")

    runner.append_runner_event = boom
    try:
        result = runner.run_once(str(tmp_path), limit=1, config_path=str(config))
    finally:
        runner.append_runner_event = original

    loaded = queue.load_queue(str(tmp_path))
    assert result["results"][0]["runner_status"] == "pass"
    assert loaded["tasks"][0]["status"] == "done"
    assert "telemetry_error" in loaded["tasks"][0]["last_runner"]


def test_verify_outputs_turns_exit_zero_into_retryable_failure(tmp_path: Path) -> None:
    write_image_queue(tmp_path, max_retries=1)
    config = write_config(tmp_path, "python3 -c \"pass\"")

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), verify_outputs=True, no_dashboard=True)
    loaded = queue.load_queue(str(tmp_path))

    assert result["results"][0]["runner_status"] == "fail"
    assert "verification failed" in result["results"][0]["note"]
    assert loaded["tasks"][0]["status"] == "retry_queued"


def test_verify_outputs_accepts_voice_alternative_contract(tmp_path: Path) -> None:
    write_progress(tmp_path)
    voice_dir = tmp_path / "合成" / "第1集" / "配音"
    voice_dir.mkdir(parents=True)
    (voice_dir / "voice_zh.wav").write_bytes(b"RIFF")
    (voice_dir / "时长清单.json").write_text("{}", encoding="utf-8")
    task = {"stage_key": "voice", "episode": "第1集"}

    assert runner.verify_task_completion(str(tmp_path), task) == []


def test_verify_outputs_accepts_single_compose_variant(tmp_path: Path) -> None:
    task = {"stage_key": "compose", "episode": "第1集"}
    out_dir = tmp_path / "合成" / "第1集"
    out_dir.mkdir(parents=True)
    (out_dir / "成片_第1集_zh.mp4").write_bytes(b"mp4")
    spec = queue.find_stage("compose")

    assert runner.verify_output_contract(str(tmp_path), task, spec) == []
