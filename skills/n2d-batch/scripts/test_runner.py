from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import types
from pathlib import Path


QUEUE_SCRIPT = Path(__file__).with_name("queue.py")
SCRIPT_DIR = QUEUE_SCRIPT.resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != SCRIPT_DIR]
queue_spec = importlib.util.spec_from_file_location("n2d_batch_queue", QUEUE_SCRIPT)
queue = importlib.util.module_from_spec(queue_spec)
assert queue_spec.loader is not None
queue_spec.loader.exec_module(queue)

RUNNER_SCRIPT = Path(__file__).with_name("runner.py")
runner_spec = importlib.util.spec_from_file_location("n2d_batch_runner", RUNNER_SCRIPT)
runner = importlib.util.module_from_spec(runner_spec)
assert runner_spec.loader is not None
runner_spec.loader.exec_module(runner)

SKILL_ROOT = Path(__file__).resolve().parents[1]


def write_progress(root: Path) -> None:
    (root / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | 1/3 | ⬜ | ⬜ | ⬜ | ⬜ |",
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
    path.write_text(json.dumps({"commands": {"image": command}, "next_preflight": False}, ensure_ascii=False), encoding="utf-8")
    return path


def test_standard_batch_wrappers_and_example_config_exist() -> None:
    for name in ("run_n2d_script_stage2.sh", "run_n2d_image.sh", "run_n2d_video.sh", "run_n2d_compose.sh", "run_n2d_review.sh"):
        assert (SKILL_ROOT / "scripts" / name).is_file()
    example = SKILL_ROOT / "references" / "batch_runner.example.json"
    data = json.loads(example.read_text(encoding="utf-8"))
    assert {"voice", "script_stage2", "image", "video", "compose", "review"} <= set(data["commands"])
    assert "run_n2d_script_stage2.sh" in data["commands"]["script_stage2"]
    assert "run_n2d_image.sh" in data["commands"]["image"]
    assert "run_n2d_video.sh" in data["commands"]["video"]
    assert "N2D_VIDEO_RANGE=" in data["commands"]["video"]
    assert "run_n2d_compose.sh" in data["commands"]["compose"]
    assert "run_n2d_review.sh" in data["commands"]["review"]


def test_runner_sanitizes_local_queue_shadowing(monkeypatch) -> None:
    fake_local_queue = types.ModuleType("queue")
    fake_local_queue.__file__ = str(QUEUE_SCRIPT)
    original_queue = sys.modules.get("queue")
    sys.modules["queue"] = fake_local_queue
    monkeypatch.syspath_prepend(str(SCRIPT_DIR))
    try:
        runner._sanitize_import_path_for_stdlib()
        std_queue = importlib.import_module("queue")
        assert hasattr(std_queue, "SimpleQueue")
        assert Path(std_queue.__file__).resolve() != QUEUE_SCRIPT.resolve()
    finally:
        if original_queue is not None:
            sys.modules["queue"] = original_queue
        else:
            sys.modules.pop("queue", None)


def test_runner_claims_executes_marks_done_and_records_dashboard(tmp_path: Path) -> None:
    write_image_queue(tmp_path)
    out_file = tmp_path / "runner_was_here.txt"
    config = write_config(
        tmp_path,
        "python3 -c \"import os, pathlib; pathlib.Path(os.environ['N2D_ROOT']).joinpath('runner_was_here.txt').write_text(os.environ['N2D_TASK_ID']+'|'+os.environ['N2D_IDEMPOTENCY_KEY'], encoding='utf-8')\"",
    )

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config))

    assert result["processed"] == 1
    written = out_file.read_text(encoding="utf-8")
    assert written.startswith("001-image")
    assert "|" in written and written.split("|", 1)[1]
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
    assert loaded["tasks"][0]["last_runner"]["error_class"] == "command_failed"
    assert loaded["tasks"][0]["dead_letter"] is True


def test_runner_marks_unconfigured_slash_command_as_retryable_failure(tmp_path: Path) -> None:
    write_image_queue(tmp_path, max_retries=1)

    result = runner.run_once(str(tmp_path), limit=1, next_preflight=False)
    loaded = queue.load_queue(str(tmp_path))

    assert result["results"][0]["runner_status"] == "fail"
    assert "slash command" in result["results"][0]["note"]
    assert loaded["tasks"][0]["status"] == "retry_queued"


def test_runner_next_preflight_blocks_before_command(tmp_path: Path, monkeypatch) -> None:
    write_image_queue(tmp_path, max_retries=1)
    out_file = tmp_path / "should_not_exist.txt"
    config = write_config(
        tmp_path,
        "python3 -c \"import os, pathlib; pathlib.Path(os.environ['N2D_ROOT']).joinpath('should_not_exist.txt').write_text('ran')\"",
    )
    monkeypatch.setattr(
        runner,
        "next_preflight_issue",
        lambda root, task: {"stop_reason": "blocked_by_image_qc", "headline": "image_qc 未放行"},
    )

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), next_preflight=True, no_dashboard=True)
    loaded = queue.load_queue(str(tmp_path))

    assert result["results"][0]["runner_status"] == "fail"
    assert "next_preflight blocked" in result["results"][0]["note"]
    assert loaded["tasks"][0]["status"] == "retry_queued"
    assert not out_file.exists()


def test_runner_defaults_next_preflight_on_when_config_omits_setting(tmp_path: Path, monkeypatch) -> None:
    write_image_queue(tmp_path, max_retries=1)
    out_file = tmp_path / "should_not_exist.txt"
    config = tmp_path / "生产数据" / "batch_runner.json"
    config.write_text(
        json.dumps({
            "commands": {
                "image": "python3 -c \"import os, pathlib; pathlib.Path(os.environ['N2D_ROOT']).joinpath('should_not_exist.txt').write_text('ran')\""
            }
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runner,
        "next_preflight_issue",
        lambda root, task: {"stop_reason": "blocked_by_gate", "headline": "gate 未放行"},
    )

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), no_dashboard=True)

    assert result["results"][0]["runner_status"] == "fail"
    assert "next_preflight blocked" in result["results"][0]["note"]
    assert not out_file.exists()


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


def test_verify_outputs_accepts_script_stage2_zh_only_contract(tmp_path: Path) -> None:
    write_progress(tmp_path)
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    for name in ("分镜剧本.md", "故事板.md", "storyboard.json", "素材清单.md", "字幕_中文.srt", "镜头时长.json"):
        (ep_dir / name).write_text("{}" if name.endswith(".json") else "ok", encoding="utf-8")
    task = {"stage_key": "script_stage2", "episode": "第1集"}

    assert runner.verify_task_completion(str(tmp_path), task) == []


def test_verify_outputs_accepts_single_compose_variant(tmp_path: Path) -> None:
    task = {"stage_key": "compose", "episode": "第1集"}
    out_dir = tmp_path / "合成" / "第1集"
    out_dir.mkdir(parents=True)
    (out_dir / "成片_第1集_zh.mp4").write_bytes(b"mp4")
    spec = queue.find_stage("compose")

    assert runner.verify_output_contract(str(tmp_path), task, spec) == []


# ── #1 返工 pass 后自动重跑门禁刷新 findings（闭环复检最后一环）────────────────
def test_runner_auto_reruns_gate_after_pass(tmp_path: Path, monkeypatch) -> None:
    write_image_queue(tmp_path)
    config = write_config(tmp_path, "python3 -c \"pass\"")
    calls = []
    monkeypatch.setattr(
        runner, "refresh_gate",
        lambda root, ep, stage: calls.append((ep, stage)) or {"stage": stage, "exit_code": 0, "blocks": 0, "warns": 0, "findings_path": "x"},
    )

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config))

    assert calls == [("第1集", "image")]  # 该任务 gate_stage=image，pass 后自动重跑一次
    assert result["results"][0]["gate_refreshed"]["stage"] == "image"


def test_runner_no_gate_flag_skips_auto_gate(tmp_path: Path, monkeypatch) -> None:
    write_image_queue(tmp_path)
    config = write_config(tmp_path, "python3 -c \"pass\"")
    calls = []
    monkeypatch.setattr(runner, "refresh_gate", lambda *a, **k: calls.append(a) or {})

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), auto_gate=False)

    assert calls == []
    assert "gate_refreshed" not in result["results"][0]


def test_runner_auto_gate_disabled_via_config(tmp_path: Path, monkeypatch) -> None:
    write_image_queue(tmp_path)
    path = tmp_path / "生产数据" / "batch_runner.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"commands": {"image": "python3 -c \"pass\""}, "auto_gate": False}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(runner, "refresh_gate", lambda *a, **k: calls.append(a) or {})

    runner.run_once(str(tmp_path), limit=1, config_path=str(path))

    assert calls == []


def test_runner_gate_failure_does_not_break_mark(tmp_path: Path, monkeypatch) -> None:
    write_image_queue(tmp_path)
    config = write_config(tmp_path, "python3 -c \"pass\"")

    def boom(*a, **k):
        raise RuntimeError("gate.py exploded")

    monkeypatch.setattr(runner, "refresh_gate", boom)
    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config))

    loaded = queue.load_queue(str(tmp_path))
    assert loaded["tasks"][0]["status"] == "done"  # 门禁重跑失败不回滚已 mark 的任务
    assert "gate.py exploded" in result["results"][0]["gate_refreshed"]["error"]
