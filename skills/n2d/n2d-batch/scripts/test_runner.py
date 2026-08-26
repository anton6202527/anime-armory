from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
import types
import wave
from pathlib import Path

import pytest
from PIL import Image


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


@pytest.fixture(autouse=True)
def explicit_test_only_producer_binding(monkeypatch):
    """Compatibility fixtures may bypass real producer artifacts; production has no switch."""
    monkeypatch.setattr(runner, "ALLOW_TEST_FIXTURE_AUTHORIZATION", True)


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


def write_test_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\x00\x00" * 800)


def write_test_mp4(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                "color=c=black:s=16x16:d=0.2", "-an", "-c:v", "mpeg4", str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except FileNotFoundError:
        pytest.skip("ffmpeg unavailable")
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")


def write_test_png(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color).save(path)


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
    # Explicit test-only approval fixture. Being queued is intentionally insufficient authority.
    for task in ledger["tasks"]:
        task["input_fingerprint"] = f"fixture-input-{task['id']}"
        task["production_authorization"] = runner.make_production_authorization(
            task,
            approval_id=f"test-approval-{task['id']}",
            approver="qa-human@example.invalid",
            model="any",
            channel="any",
            root=str(root),
        )
    queue.save_queue(str(root), ledger)


def write_config(root: Path, command: str) -> Path:
    path = root / "生产数据" / "batch_runner.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"commands": {"image": command}, "next_preflight": False}, ensure_ascii=False), encoding="utf-8")
    ledger = queue.load_queue(str(root))
    for task in ledger.get("tasks", []):
        if task.get("stage_key") in runner.PRODUCTION_STAGE_KEYS:
            task["production_authorization"] = runner.make_production_authorization(
                task,
                approval_id=f"test-approval-{task['id']}",
                approver="qa-human@example.invalid",
                model="any",
                channel="any",
                root=str(root),
                resolved_command=command,
            )
    queue.save_queue(str(root), ledger)
    return path


@pytest.fixture
def authorized_image_frontier(monkeypatch):
    """Canonical action-card fixture: exact task frontier + explicit payment stop."""
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": {"ep": "第1集", "stage_key": "image", "label": "出图"},
            "stop_reason": "needs_payment_confirm",
            "action_card": {"headline": "test payment approval"},
            "gate": None,
        },
    )


@pytest.fixture
def successful_image_postconditions(monkeypatch):
    monkeypatch.setattr(runner, "verify_task_completion", lambda root, task: [])
    monkeypatch.setattr(
        runner,
        "refresh_gate",
        lambda root, ep, stage: {
            "stage": stage,
            "exit_code": 0,
            "blocks": 0,
            "warns": 0,
            "findings_path": "test_gate.json",
        },
    )


def canonical_authorization_task(**updates) -> dict:
    task = {
        "id": "001-image-progress",
        "idempotency_key": "n2d:test:001-image-progress",
        "episode": "第1集",
        "stage_key": "image",
        "estimated_cost": {"amount": 3.0, "unit": "work_units"},
        "command": "python3 -c \"pass\"",
        "input_fingerprint": "fixture-input-v1",
        "affected_shots": ["Clip_01"],
        "affected_artifacts": [],
        "rerun_scope": "第1集 Clip_01",
    }
    task.update(updates)
    return task


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


@pytest.mark.parametrize(
    "name",
    (
        "run_n2d_script_stage2.sh",
        "run_n2d_image.sh",
        "run_n2d_video.sh",
        "run_n2d_compose.sh",
        "run_n2d_review.sh",
    ),
)
def test_standard_batch_wrapper_resolves_repo_root_from_arbitrary_cwd(
    tmp_path: Path, name: str
) -> None:
    wrapper = SKILL_ROOT / "scripts" / name
    completed = subprocess.run(
        ["bash", str(wrapper)],
        cwd=tmp_path,
        env={**os.environ, "N2D_WRAPPER_SELF_CHECK": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert Path(completed.stdout.strip()).resolve() == SKILL_ROOT.parents[2]


def test_image_wrapper_resolves_repository_root_not_skills_directory() -> None:
    wrapper = (SKILL_ROOT / "scripts" / "run_n2d_image.sh").read_text(encoding="utf-8")

    assert 'REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"' in wrapper
    assert 'REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"' not in wrapper


def test_paid_image_outer_launcher_cannot_strip_authorized_environment(tmp_path: Path) -> None:
    inner = (
        "python3 skills/n2d/n2d-image/scripts/codex_image_runner.py "
        f'"{tmp_path}" 第1集 --shots Clip_01'
    )
    malicious_outer = f"bash -c 'env -i {inner}'"
    with pytest.raises(runner.ProducerContractError, match="arbitrary outer wrappers are forbidden"):
        runner._assert_safe_image_launcher(
            str(tmp_path), "第1集", malicious_outer, inner
        )

    canonical = (
        f'bash "{SKILL_ROOT / "scripts" / "run_n2d_image.sh"}" '
        f'"{tmp_path}" 第1集'
    )
    runner._assert_safe_image_launcher(str(tmp_path), "第1集", canonical, inner)


def test_paid_direct_producer_rejects_shell_suffix() -> None:
    command = (
        "python3 skills/n2d/n2d-image/scripts/codex_image_runner.py /tmp/work 第1集 "
        "--shots Clip_01; env -i python3 spend_again.py"
    )
    with pytest.raises(runner.ProducerContractError, match="shell control"):
        runner._assert_direct_python_producer(command, "codex_image_runner.py")


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


def test_exact_action_card_never_falls_through_to_generic_claim(tmp_path: Path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(runner, "production_governance_interlock", lambda _root: None)
    monkeypatch.setattr(
        runner.queue_mod,
        "claim_exact",
        lambda *args, **kwargs: calls.append((args, kwargs)) or [],
    )
    monkeypatch.setattr(
        runner.queue_mod,
        "claim",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("generic claim forbidden")),
    )

    result = runner.run_once(
        str(tmp_path),
        limit=1,
        task_id="001-video-progress-abc",
        expected_plan_digest="sha256:" + "a" * 64,
        episode="第1集",
        stage_key="video",
    )

    assert len(calls) == 1
    assert result["claimed"] == 0
    assert result["results"][0]["runner_status"] == "fail"
    assert "no fallback task" in result["results"][0]["note"]


def test_stale_exact_claim_cli_returns_structured_failure_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(runner, "production_governance_interlock", lambda _root: None)
    monkeypatch.setattr(
        runner.queue_mod,
        "claim_exact",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("exact current plan unavailable or changed: stale action card")
        ),
    )

    rc = runner.main([
        str(tmp_path),
        "--task-id", "001-video-progress-stale",
        "--expected-plan-digest", "sha256:" + "a" * 64,
        "--episode", "第1集",
        "--stage", "video",
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == 1
    assert payload["claimed"] == 0
    assert payload["results"][0]["queue_status"] == "blocked_exact_claim"
    assert payload["results"][0]["error"]["type"] == "ValueError"
    assert "stale action card" in payload["results"][0]["note"]
    assert "Traceback" not in captured.err


def test_critical_governance_interlock_blocks_before_claim(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "production_governance_interlock",
        lambda _root: {
            "status": "blocked",
            "violations": [{"level": "critical", "kind": "stop_loss"}],
        },
    )
    monkeypatch.setattr(
        runner.queue_mod,
        "claim",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("claim forbidden")),
    )

    result = runner.run_once(str(tmp_path), limit=1)

    assert result["claimed"] == 0
    assert result["results"][0]["queue_status"] == "blocked_governance"


def test_runner_claims_executes_marks_done_and_records_dashboard(
    tmp_path: Path, authorized_image_frontier, successful_image_postconditions
) -> None:
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


def test_runner_failure_requeues_then_fails_after_retry_limit(tmp_path: Path, authorized_image_frontier) -> None:
    write_image_queue(tmp_path, max_retries=1)
    command = "python3 -c \"import sys; sys.exit(7)\""
    config = write_config(tmp_path, command)

    first = runner.run_once(str(tmp_path), limit=1, config_path=str(config))
    loaded = queue.load_queue(str(tmp_path))
    assert first["results"][0]["runner_status"] == "fail"
    assert loaded["tasks"][0]["status"] == "retry_queued"
    assert loaded["tasks"][0]["attempts"] == 1

    # A production approval is single-attempt. Explicitly re-authorize attempt 2 after
    # inspecting the paid failure; the stale attempt-1 receipt must not fund retries forever.
    retry_task = loaded["tasks"][0]
    retry_task["production_authorization"] = runner.make_production_authorization(
        retry_task,
        approval_id="test-approval-attempt-2",
        approver="qa-human@example.invalid",
        model="any",
        channel="any",
        root=str(tmp_path),
        resolved_command=command,
    )
    queue.save_queue(str(tmp_path), loaded)

    second = runner.run_once(str(tmp_path), limit=1, config_path=str(config))
    loaded = queue.load_queue(str(tmp_path))
    assert second["results"][0]["runner_status"] == "fail"
    assert loaded["tasks"][0]["status"] == "failed"
    assert loaded["tasks"][0]["attempts"] == 2
    assert loaded["tasks"][0]["last_runner"]["exit_code"] == 7
    assert loaded["tasks"][0]["last_runner"]["error_class"] == "command_failed"
    assert loaded["tasks"][0]["dead_letter"] is True


def test_runner_marks_unconfigured_slash_command_as_retryable_failure(tmp_path: Path, authorized_image_frontier) -> None:
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


def test_runner_marks_done_even_when_dashboard_telemetry_fails(
    tmp_path: Path, authorized_image_frontier, successful_image_postconditions
) -> None:
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


def test_output_verification_is_default_and_turns_exit_zero_into_retryable_failure(
    tmp_path: Path, authorized_image_frontier
) -> None:
    write_image_queue(tmp_path, max_retries=1)
    config = write_config(tmp_path, "python3 -c \"pass\"")

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), no_dashboard=True)
    loaded = queue.load_queue(str(tmp_path))

    assert result["results"][0]["runner_status"] == "fail"
    assert "verification failed" in result["results"][0]["note"]
    assert loaded["tasks"][0]["status"] == "retry_queued"


def test_verify_outputs_accepts_voice_alternative_contract(tmp_path: Path) -> None:
    write_progress(tmp_path)
    voice_dir = tmp_path / "合成" / "第1集" / "配音"
    voice_dir.mkdir(parents=True)
    write_test_wav(voice_dir / "voice_zh.wav")
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
    write_test_mp4(out_dir / "成片_第1集_zh.mp4")
    spec = queue.find_stage("compose")

    assert runner.verify_output_contract(str(tmp_path), task, spec) == []


# ── #1 返工 pass 后自动重跑门禁刷新 findings（闭环复检最后一环）────────────────
def test_runner_auto_reruns_gate_after_pass(tmp_path: Path, monkeypatch, authorized_image_frontier) -> None:
    write_image_queue(tmp_path)
    config = write_config(tmp_path, "python3 -c \"pass\"")
    calls = []
    monkeypatch.setattr(
        runner, "refresh_gate",
        lambda root, ep, stage: calls.append((ep, stage)) or {"stage": stage, "exit_code": 0, "blocks": 0, "warns": 0, "findings_path": "x"},
    )
    monkeypatch.setattr(runner, "verify_task_completion", lambda root, task: [])

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config))

    assert calls == [("第1集", "image")]  # 该任务 gate_stage=image，pass 后自动重跑一次
    assert result["results"][0]["gate_refreshed"]["stage"] == "image"


def test_runner_no_gate_flag_cannot_skip_production_gate(
    tmp_path: Path, monkeypatch, authorized_image_frontier
) -> None:
    write_image_queue(tmp_path)
    config = write_config(tmp_path, "python3 -c \"pass\"")
    calls = []
    monkeypatch.setattr(
        runner,
        "refresh_gate",
        lambda *a, **k: calls.append(a) or {"stage": "image", "exit_code": 0, "blocks": 0, "warns": 0},
    )
    monkeypatch.setattr(runner, "verify_task_completion", lambda root, task: [])

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), auto_gate=False)

    assert calls, "production stage must ignore --no-gate"
    assert result["results"][0]["queue_status"] == "done"


def test_runner_auto_gate_disabled_via_config_cannot_skip_production_gate(
    tmp_path: Path, monkeypatch, authorized_image_frontier
) -> None:
    write_image_queue(tmp_path)
    path = write_config(tmp_path, "python3 -c \"pass\"")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["auto_gate"] = False
    path.write_text(json.dumps(data), encoding="utf-8")
    calls = []
    monkeypatch.setattr(
        runner,
        "refresh_gate",
        lambda *a, **k: calls.append(a) or {"stage": "image", "exit_code": 0, "blocks": 0, "warns": 0},
    )
    monkeypatch.setattr(runner, "verify_task_completion", lambda root, task: [])

    runner.run_once(str(tmp_path), limit=1, config_path=str(path))

    assert calls, "production stage must ignore auto_gate=false"


def test_runner_gate_failure_marks_qa_blocked_not_done(
    tmp_path: Path, monkeypatch, authorized_image_frontier
) -> None:
    write_image_queue(tmp_path)
    config = write_config(tmp_path, "python3 -c \"pass\"")

    def boom(*a, **k):
        raise RuntimeError("gate.py exploded")

    monkeypatch.setattr(runner, "refresh_gate", boom)
    monkeypatch.setattr(runner, "verify_task_completion", lambda root, task: [])
    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config))

    loaded = queue.load_queue(str(tmp_path))
    assert loaded["tasks"][0]["status"] == "qa_blocked"
    assert result["results"][0]["runner_status"] == "qa_blocked"
    assert "gate.py exploded" in result["results"][0]["gate_refreshed"]["error"]


# ── 产物内容校验：存在但零字节/坏 JSON 不算就位（output_contract 不收「空壳产物」）──────


def test_verify_outputs_rejects_empty_file(tmp_path: Path) -> None:
    task = {"stage_key": "compose", "episode": "第1集"}
    out_dir = tmp_path / "合成" / "第1集"
    out_dir.mkdir(parents=True)
    (out_dir / "成片_第1集_zh.mp4").write_bytes(b"")
    spec = queue.find_stage("compose")

    issues = runner.verify_output_contract(str(tmp_path), task, spec)
    assert issues, "零字节成片不该通过 output_contract"
    assert "empty file" in issues[0]


def test_verify_outputs_rejects_empty_directory(tmp_path: Path) -> None:
    task = {"stage_key": "video", "episode": "第1集"}
    (tmp_path / "出视频" / "第1集" / "视频").mkdir(parents=True)
    spec = queue.find_stage("video")

    issues = runner.verify_output_contract(str(tmp_path), task, spec)

    assert issues and "empty directory" in issues[0]


def test_verify_outputs_rejects_nonempty_but_invalid_media(tmp_path: Path) -> None:
    task = {"stage_key": "compose", "episode": "第1集"}
    out_dir = tmp_path / "合成" / "第1集"
    out_dir.mkdir(parents=True)
    (out_dir / "成片_第1集_zh.mp4").write_bytes(b"this is not an mp4")

    issues = runner.verify_output_contract(str(tmp_path), task, queue.find_stage("compose"))

    assert issues and "invalid mp4 media header" in issues[0]


def test_verify_outputs_rejects_truncated_mp4_with_valid_ftyp_header(tmp_path: Path) -> None:
    task = {"stage_key": "compose", "episode": "第1集"}
    out_dir = tmp_path / "合成" / "第1集"
    out_dir.mkdir(parents=True)
    (out_dir / "成片_第1集_zh.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom" + b"0" * 20)

    issues = runner.verify_output_contract(str(tmp_path), task, queue.find_stage("compose"))

    assert issues and "invalid or undecodable mp4 media" in issues[0]


def test_producer_completion_requires_each_declared_physical_target(tmp_path: Path) -> None:
    write_test_png(tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png", (255, 0, 0))
    task = {
        "stage_key": "image",
        "episode": "第1集",
        "_runner_producer_contract": {
            "kind": "n2d_image_paid_submit_binding",
            "version": 1,
            "episode": "第1集",
            "records": [{"target": "出图/第1集/图片/Clip_03.png", "shot": "Clip_03"}],
        },
    }

    issues = runner.verify_producer_contract_outputs(str(tmp_path), task)

    assert issues == ["producer target unusable: 出图/第1集/图片/Clip_03.png (missing)"]


def test_producer_completion_rejects_unchanged_old_target_and_accepts_new_sha(tmp_path: Path) -> None:
    target = tmp_path / "出图" / "第1集" / "图片" / "Clip_03.png"
    write_test_png(target, (255, 0, 0))
    task = {
        "stage_key": "image",
        "episode": "第1集",
        "_runner_producer_contract": {
            "kind": "n2d_image_paid_submit_binding",
            "version": 1,
            "episode": "第1集",
            "records": [{"target": "出图/第1集/图片/Clip_03.png", "shot": "Clip_03"}],
        },
    }
    task["_runner_output_baseline"] = runner.producer_output_bindings(str(tmp_path), task)

    assert runner.verify_producer_contract_outputs(str(tmp_path), task) == [
        "producer target was not refreshed by this attempt: 出图/第1集/图片/Clip_03.png"
    ]

    write_test_png(target, (0, 255, 0))
    assert runner.verify_producer_contract_outputs(str(tmp_path), task) == []


def test_verify_outputs_rejects_invalid_json(tmp_path: Path) -> None:
    write_progress(tmp_path)
    voice_dir = tmp_path / "合成" / "第1集" / "配音"
    voice_dir.mkdir(parents=True)
    write_test_wav(voice_dir / "voice_zh.wav")
    (voice_dir / "时长清单.json").write_text("{broken", encoding="utf-8")
    task = {"stage_key": "voice", "episode": "第1集"}
    spec = queue.find_stage("voice")

    issues = runner.verify_output_contract(str(tmp_path), task, spec)
    assert issues, "坏 JSON 时长清单不该通过 output_contract"
    assert "invalid json" in " | ".join(issues)


# ── 花钱 stage 禁关 next-preflight：image/video/compose 无视关闭配置强制预检 ──────


def test_paid_stage_forces_next_preflight_even_when_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "next_preflight_issue",
        lambda root, task: {"stop_reason": "blocked_by_gate", "headline": "gate 未放行"},
    )
    task = {"stage_key": "image", "episode": "第1集", "command": "python3 -c \"pass\""}

    result = runner.execute_task(
        str(tmp_path),
        task,
        {},
        command_override="python3 -c \"pass\"",
        shell=False,
        timeout_sec=None,
        dry_run=True,
        no_dashboard=True,
        verify_outputs=False,
        next_preflight=False,
        build_dashboard=False,
    )

    assert result["status"] == "fail"
    assert "production stage image 强制 canonical preflight" in result["note"]
    assert "next_preflight blocked" in result["note"]


def test_non_paid_stage_respects_next_preflight_off(tmp_path: Path, monkeypatch) -> None:
    called = {"n": 0}

    def _boom(root, task):
        called["n"] += 1
        return {"stop_reason": "blocked_by_gate", "headline": "gate 未放行"}

    monkeypatch.setattr(runner, "next_preflight_issue", _boom)
    task = {"stage_key": "script_stage2", "episode": "第1集", "command": "python3 -c \"pass\""}

    result = runner.execute_task(
        str(tmp_path),
        task,
        {},
        command_override="python3 -c \"pass\"",
        shell=False,
        timeout_sec=None,
        dry_run=True,
        no_dashboard=True,
        verify_outputs=False,
        next_preflight=False,
        build_dashboard=False,
    )

    assert called["n"] == 0, "非花钱 stage 关闭 next-preflight 后不该再调用预检"
    assert result["status"] == "pass"


# ── canonical production state 反例：queued≠授权、frontier 唯一、dry-run 真只读 ─────


def test_queued_production_task_without_task_bound_approval_fails_closed(
    tmp_path: Path, monkeypatch, authorized_image_frontier
) -> None:
    write_image_queue(tmp_path, max_retries=1)
    out_file = tmp_path / "must_not_run.txt"
    config = write_config(
        tmp_path,
        "python3 -c \"import os, pathlib; pathlib.Path(os.environ['N2D_ROOT']).joinpath('must_not_run.txt').write_text('ran')\"",
    )
    ledger = queue.load_queue(str(tmp_path))
    ledger["tasks"][0].pop("production_authorization", None)
    queue.save_queue(str(tmp_path), ledger)

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), no_dashboard=True)

    assert result["results"][0]["runner_status"] == "fail"
    assert "production_authorization_required" in result["results"][0]["note"]
    assert queue.load_queue(str(tmp_path))["tasks"][0]["status"] == "retry_queued"
    assert not out_file.exists()


@pytest.mark.parametrize("stop_reason", ["done", "prework_failed", "needs_stage_execution"])
def test_production_non_executable_stop_reasons_fail_closed(
    tmp_path: Path, monkeypatch, stop_reason: str
) -> None:
    task = canonical_authorization_task()
    task["_runner_production_authorization"] = runner.make_production_authorization(
        task,
        approval_id="fixture-1",
        approver="qa-human@example.invalid",
        model="any",
        channel="any",
    )
    frontier = None if stop_reason == "done" else {"ep": "第1集", "stage_key": "image"}
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": frontier,
            "stop_reason": stop_reason,
            "action_card": {"headline": stop_reason},
            "gate": None,
        },
    )

    issue = runner._canonical_next_preflight_issue(str(tmp_path), task, preview=True)

    assert issue is not None
    assert issue["stop_reason"] == stop_reason


def test_production_task_must_match_current_frontier_stage(tmp_path: Path, monkeypatch) -> None:
    task = canonical_authorization_task()
    task["_runner_production_authorization"] = runner.make_production_authorization(
        task,
        approval_id="fixture-1",
        approver="qa-human@example.invalid",
        model="any",
        channel="any",
    )
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": {"ep": "第1集", "stage_key": "video"},
            "stop_reason": "needs_payment_confirm",
            "action_card": {},
            "gate": None,
        },
    )

    issue = runner._canonical_next_preflight_issue(str(tmp_path), task, preview=True)

    assert issue is not None
    assert issue["stop_reason"] == "frontier_mismatch"


def test_canonical_preflight_accepts_safe_local_compose_without_payment_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    task = canonical_authorization_task(
        id="001-compose-progress",
        idempotency_key="n2d:test:001-compose-progress",
        stage_key="compose",
    )
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": {"ep": "第1集", "stage_key": "compose"},
            "stop_reason": "needs_stage_execution",
            "action_card": {
                "execution_effect": {
                    "safe_local_execution": True,
                    "local_only": True,
                    "paid": False,
                },
            },
            "gate": None,
        },
    )

    assert runner._canonical_next_preflight_issue(str(tmp_path), task, preview=True) is None


def test_canonical_preflight_rechecks_v2_envelope_behind_authorized_probe(
    tmp_path: Path, monkeypatch
) -> None:
    task = canonical_authorization_task(
        model="GPT Image 2", channel="Codex CLI", status="running", attempts=1,
    )
    runner.bind_production_execution_context(str(tmp_path), task, {}, str(task["command"]))
    receipt = runner.spend_envelope_mod.make_envelope(
        tmp_path,
        envelope_id="phase-image-preflight",
        approver="producer@example.invalid",
        approval_reference="approval-ui:phase-image-preflight",
        source_quote="我确认按该阶段预算包继续执行付费出图。",
        stage="image",
        model="GPT Image 2",
        channel="Codex CLI",
        input_sha256=runner.phase_envelope_input_digest(task),
        scope=runner.production_task_scope(task),
        max_calls=1,
        max_attempts=1,
        cost_ceiling=3,
        currency="work_units",
    )
    task["_runner_production_authorization"] = receipt
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": {"ep": "第1集", "stage_key": "image"},
            "stop_reason": "needs_stage_execution",
            "action_card": {
                "phase_spend_envelope": {
                    "status": "authorized",
                    "read_only": True,
                    "consumed": False,
                    "envelope_id": receipt["envelope_id"],
                },
            },
            "gate": None,
        },
    )

    assert runner._canonical_next_preflight_issue(str(tmp_path), task, preview=True) is None
    # A read-only card is only a hint.  Exact current runtime binding is checked again here.
    task["_runner_submit_request_digest"] = "sha256:" + "f" * 64
    issue = runner._canonical_next_preflight_issue(str(tmp_path), task, preview=True)
    assert issue is not None
    assert issue["stop_reason"] == "production_authorization_required"
    assert "input_sha256 mismatch" in issue["headline"]


def test_dry_run_does_not_claim_mark_increment_attempt_or_execute(
    tmp_path: Path, authorized_image_frontier
) -> None:
    write_image_queue(tmp_path)
    before = queue.load_queue(str(tmp_path))["tasks"][0]
    out_file = tmp_path / "dry_run_must_not_execute.txt"
    config = write_config(
        tmp_path,
        "python3 -c \"import os, pathlib; pathlib.Path(os.environ['N2D_ROOT']).joinpath('dry_run_must_not_execute.txt').write_text('ran')\"",
    )

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), dry_run=True)
    after = queue.load_queue(str(tmp_path))["tasks"][0]

    assert result["claimed"] == 0 and result["previewed"] == 1 and result["processed"] == 0
    assert result["results"][0]["runner_status"] == "would_run"
    assert after["status"] == before["status"] == "queued"
    assert after["attempts"] == before["attempts"] == 0
    assert after["history"] == before["history"]
    assert not out_file.exists()


def test_post_gate_block_is_qa_blocked_not_done(
    tmp_path: Path, monkeypatch, authorized_image_frontier
) -> None:
    write_image_queue(tmp_path)
    config = write_config(tmp_path, "python3 -c \"pass\"")
    monkeypatch.setattr(runner, "verify_task_completion", lambda root, task: [])
    monkeypatch.setattr(
        runner,
        "refresh_gate",
        lambda root, ep, stage: {"stage": stage, "exit_code": 1, "blocks": 2, "warns": 0},
    )

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config), no_dashboard=True)

    assert result["results"][0]["runner_status"] == "qa_blocked"
    assert result["results"][0]["queue_status"] == "qa_blocked"
    assert queue.load_queue(str(tmp_path))["tasks"][0]["status"] == "qa_blocked"


def test_production_authorization_digest_detects_tampering() -> None:
    task = canonical_authorization_task()
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-tamper",
        approver="producer@example.invalid",
        model="veo-3.1-generate-001",
        channel="vertex-ai",
    )
    receipt["ceiling"]["amount"] = 99.0  # digest intentionally not recomputed
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and "authorization_digest mismatch" in issue


def test_v2_phase_envelope_authorizes_bounded_idempotent_retries(tmp_path: Path) -> None:
    task = canonical_authorization_task(
        model="GPT Image 2",
        channel="Codex CLI",
        status="running",
        attempts=1,
    )
    runner.bind_production_execution_context(str(tmp_path), task, {}, str(task["command"]))
    receipt = runner.spend_envelope_mod.make_envelope(
        tmp_path,
        envelope_id="phase-image-bounded",
        approver="producer@example.invalid",
        approval_reference="approval-ui:phase-image-bounded",
        source_quote="我确认按该阶段预算包继续执行付费出图。",
        stage="image",
        model="GPT Image 2",
        channel="Codex CLI",
        input_sha256=runner.phase_envelope_input_digest(task),
        scope=runner.production_task_scope(task),
        max_calls=2,
        max_attempts=2,
        cost_ceiling=6,
        currency="work_units",
    )
    task["_runner_production_authorization"] = receipt
    assert runner._authorization_issue(task, str(tmp_path)) is None

    first = runner.spend_envelope_mod.consume(
        tmp_path, receipt, **runner._phase_consumption_kwargs(task)
    )
    assert first["idempotent"] is False
    with pytest.raises(runner.spend_envelope_mod.SpendEnvelopeError, match="provider replay blocked"):
        runner.spend_envelope_mod.consume(
            tmp_path, receipt, **runner._phase_consumption_kwargs(task)
        )
    runner.spend_envelope_mod.finalize(
        tmp_path,
        receipt,
        consumption_id=first["consumption"]["consumption_id"],
        evidence={
            "kind": "n2d_provider_recovery_evidence",
            "provider_submit_id": "test-receipt-attempt-1",
            "provider_status": "success",
            "query_receipt_reference": "provider-query:test-receipt-attempt-1",
            "query_response_sha256": "sha256:" + "c" * 64,
        },
    )

    task["attempts"] = 2
    assert runner._authorization_issue(task, str(tmp_path)) is None
    runner.spend_envelope_mod.consume(
        tmp_path, receipt, **runner._phase_consumption_kwargs(task)
    )
    task["attempts"] = 3
    issue = runner._authorization_issue(task, str(tmp_path))
    assert issue and "max_attempts exceeded" in issue


def test_crash_after_v2_reservation_cannot_reinvoke_provider_for_same_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    task = canonical_authorization_task(
        model="GPT Image 2", channel="Codex CLI", status="running", attempts=1,
    )
    config = {"commands": {"image": str(task["command"])}}
    runner.bind_production_execution_context(str(tmp_path), task, config, str(task["command"]))
    receipt = runner.spend_envelope_mod.make_envelope(
        tmp_path,
        envelope_id="phase-image-crash-window",
        approver="producer@example.invalid",
        approval_reference="approval-ui:phase-image-crash-window",
        source_quote="我确认按该阶段预算包继续执行付费出图。",
        stage="image",
        model="GPT Image 2",
        channel="Codex CLI",
        input_sha256=runner.phase_envelope_input_digest(task),
        scope=runner.production_task_scope(task),
        max_calls=2,
        max_attempts=2,
        cost_ceiling=6,
        currency="work_units",
    )
    task["phase_spend_envelope"] = receipt
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": {"ep": "第1集", "stage_key": "image"},
            "stop_reason": "needs_stage_execution",
            "action_card": {
                "phase_spend_envelope": {
                    "status": "authorized", "read_only": True, "consumed": False,
                },
            },
            "gate": None,
        },
    )
    calls = {"provider": 0}

    def crash_after_submit(*args, **kwargs):
        calls["provider"] += 1
        raise subprocess.TimeoutExpired(cmd="producer", timeout=1)

    monkeypatch.setattr(runner, "run_process", crash_after_submit)
    first = runner.execute_task(
        str(tmp_path), task, config, command_override=None, shell=False, timeout_sec=1,
        dry_run=False, no_dashboard=True, verify_outputs=False, next_preflight=True,
        build_dashboard=False,
    )
    second = runner.execute_task(
        str(tmp_path), task, config, command_override=None, shell=False, timeout_sec=1,
        dry_run=False, no_dashboard=True, verify_outputs=False, next_preflight=True,
        build_dashboard=False,
    )

    assert first["status"] == "fail" and second["status"] == "fail"
    assert calls["provider"] == 1
    assert "provider replay blocked" in second["note"]
    ledger = json.loads((tmp_path / runner.spend_envelope_mod.LEDGER_REL).read_text(encoding="utf-8"))
    assert len(ledger["envelopes"]["phase-image-crash-window"]["consumptions"]) == 1


def test_successful_v2_execution_passes_queue_completion_validator(
    tmp_path: Path, monkeypatch
) -> None:
    task = canonical_authorization_task(
        model="GPT Image 2", channel="Codex CLI", status="running", attempts=1,
    )
    config = {"commands": {"image": str(task["command"])}}
    runner.bind_production_execution_context(str(tmp_path), task, config, str(task["command"]))
    receipt = runner.spend_envelope_mod.make_envelope(
        tmp_path,
        envelope_id="phase-image-completion",
        approver="producer@example.invalid",
        approval_reference="approval-ui:phase-image-completion",
        source_quote="我确认按该阶段预算包继续执行付费出图。",
        stage="image", model="GPT Image 2", channel="Codex CLI",
        input_sha256=runner.phase_envelope_input_digest(task),
        scope=runner.production_task_scope(task), max_calls=1, max_attempts=1,
        cost_ceiling=3, currency="work_units",
    )
    task["phase_spend_envelope"] = receipt
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": {"ep": "第1集", "stage_key": "image"},
            "stop_reason": "needs_stage_execution",
            "action_card": {"phase_spend_envelope": {
                "status": "authorized", "read_only": True, "consumed": False,
            }},
            "gate": None,
        },
    )
    monkeypatch.setattr(runner, "run_process", lambda *args, **kwargs: (0, "ok", ""))
    monkeypatch.setattr(runner, "verify_task_completion", lambda root, task: [])

    result = runner.execute_task(
        str(tmp_path), task, config, command_override=None, shell=False, timeout_sec=1,
        dry_run=False, no_dashboard=True, verify_outputs=True, next_preflight=True,
        build_dashboard=False,
    )

    assert result["status"] == "pass"
    completion_issue = runner.queue_mod._runner_completion_issue(
        {"root": str(tmp_path)},
        task,
        task["last_runner"],
        {"acceptance_required": False},
    )
    assert completion_issue is None
    assert task["last_runner"]["completion"]["phase_spend_completion"]["status"] == "pass"


def test_v2_phase_envelope_rejects_current_execution_hash_change(tmp_path: Path) -> None:
    task = canonical_authorization_task(
        model="GPT Image 2", channel="Codex CLI", status="running", attempts=1,
    )
    runner.bind_production_execution_context(str(tmp_path), task, {}, str(task["command"]))
    receipt = runner.spend_envelope_mod.make_envelope(
        tmp_path,
        envelope_id="phase-image-input-change",
        approver="producer@example.invalid",
        approval_reference="approval-ui:phase-image-input-change",
        source_quote="我确认按该阶段预算包继续执行付费出图。",
        stage="image",
        model="GPT Image 2",
        channel="Codex CLI",
        input_sha256=runner.phase_envelope_input_digest(task),
        scope=runner.production_task_scope(task),
        max_calls=2,
        max_attempts=2,
        cost_ceiling=6,
        currency="work_units",
    )
    task["_runner_production_authorization"] = receipt
    assert runner._authorization_issue(task, str(tmp_path)) is None
    task["_runner_submit_request_digest"] = "sha256:" + "f" * 64
    issue = runner._authorization_issue(task, str(tmp_path))
    assert issue and "input_sha256 mismatch" in issue


def test_expired_production_authorization_is_rejected() -> None:
    task = canonical_authorization_task()
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-expired",
        approver="producer@example.invalid",
        model="any",
        channel="any",
        expires_at="2020-01-01T00:00:00+00:00",
    )
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue == "production_authorization expired"


def test_production_authorization_model_mismatch_is_rejected() -> None:
    task = canonical_authorization_task(model="veo-3.1-generate-001")
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-model",
        approver="producer@example.invalid",
        model="kling-v2.1-master",
        channel="any",
    )
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and "model mismatch" in issue


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("model", "veo-3.1-generate-001", "execution model missing"),
        ("channel", "vertex-ai", "execution channel missing"),
    ],
)
def test_concrete_authorization_requires_observed_execution_binding(
    field: str, value: str, expected: str
) -> None:
    task = canonical_authorization_task()
    approval = {"model": "any", "channel": "any"}
    approval[field] = value
    task["_runner_production_authorization"] = runner.make_production_authorization(
        task,
        approval_id=f"approval-{field}",
        approver="producer@example.invalid",
        **approval,
    )

    issue = runner._authorization_issue(task)

    assert issue and expected in issue


def test_production_estimate_over_authorization_ceiling_is_rejected() -> None:
    task = canonical_authorization_task()
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-cost",
        approver="producer@example.invalid",
        model="any",
        channel="any",
        ceiling=2.5,
        currency="work_units",
    )
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and "exceeds authorization ceiling" in issue


def test_changing_resolved_command_invalidates_production_authorization(
    tmp_path: Path, authorized_image_frontier
) -> None:
    write_image_queue(tmp_path)
    original = "python3 -c \"pass\""
    config_path = write_config(tmp_path, original)
    changed_output = tmp_path / "changed_command_ran.txt"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    data["commands"]["image"] = (
        "python3 -c \"import pathlib; "
        f"pathlib.Path(r'{changed_output}').write_text('ran', encoding='utf-8')\""
    )
    config_path.write_text(json.dumps(data), encoding="utf-8")

    result = runner.run_once(str(tmp_path), limit=1, config_path=str(config_path), no_dashboard=True)

    assert result["results"][0]["runner_status"] == "fail"
    assert "production_authorization_required" in result["results"][0]["note"]
    assert "execution" in result["results"][0]["note"]
    assert not changed_output.exists()


def test_changing_command_entrypoint_bytes_invalidates_authorization(tmp_path: Path) -> None:
    wrapper = tmp_path / "paid_wrapper.py"
    wrapper.write_text("raise SystemExit(0)\n", encoding="utf-8")
    command = f'python3 "{wrapper}"'
    task = canonical_authorization_task(command=command)
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-wrapper-v1",
        approver="producer@example.invalid",
        model="any",
        channel="any",
        root=str(tmp_path),
        resolved_command=command,
    )

    wrapper.write_text("raise SystemExit(7)\n", encoding="utf-8")
    runner.bind_production_execution_context(str(tmp_path), task, {}, command)
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and "execution" in issue


def test_changing_image_producer_prompt_invalidates_authorization(
    tmp_path: Path, monkeypatch
) -> None:
    prompt = tmp_path / "脚本" / "第1集" / "分镜剧本.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("prompt-v1", encoding="utf-8")
    task = canonical_authorization_task()
    task.pop("input_fingerprint")
    command = str(task["command"])

    def exact_image_contract(root, task, config, resolved_command):
        prompt_text = prompt.read_text(encoding="utf-8")
        digest = runner._canonical_json_digest({"compiled_prompt": prompt_text})
        return {
            "kind": "n2d_image_paid_submit_binding",
            "version": 1,
            "backend": "fixture-producer",
            "records": [{
                "target": "出图/第1集/图片/Clip_01.png",
                "input_fingerprint": digest,
                "submit_request_sha256": digest,
            }],
        }

    monkeypatch.setattr(runner, "resolve_image_producer_contract", exact_image_contract)
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-prompt-v1",
        approver="producer@example.invalid",
        model="any",
        channel="any",
        root=str(tmp_path),
        resolved_command=command,
    )
    prompt.write_text("prompt-v2", encoding="utf-8")
    runner.bind_production_execution_context(str(tmp_path), task, {}, command)
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and "execution" in issue


def test_changing_video_producer_frame_invalidates_authorization(
    tmp_path: Path, monkeypatch
) -> None:
    frame = tmp_path / "出图" / "第1集" / "图片" / "Clip_01_首帧.png"
    frame.parent.mkdir(parents=True)
    frame.write_bytes(b"frame-v1")
    task = canonical_authorization_task(
        stage_key="video",
        command="bash run_n2d_video.sh",
        estimated_cost={"amount": 12.0, "unit": "work_units"},
    )
    task.pop("input_fingerprint")
    command = str(task["command"])

    def exact_video_contract(root, task, config, resolved_command):
        digest = runner._binding_digest(frame.read_bytes().hex())
        return {
            "kind": "n2d_video_paid_submit_binding",
            "version": 1,
            "episode": "第1集",
            "batch_input_fingerprint": digest,
            "records": [{"clip": "Clip_01", "submit_request_sha256": digest}],
        }

    monkeypatch.setattr(runner, "resolve_video_producer_contract", exact_video_contract)
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-frame-v1",
        approver="producer@example.invalid",
        model="any",
        channel="any",
        root=str(tmp_path),
        resolved_command=command,
    )
    frame.write_bytes(b"frame-v2")
    runner.bind_production_execution_context(str(tmp_path), task, {}, command)
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and "execution" in issue


def test_real_image_compiled_prompt_change_invalidates_authorization(
    tmp_path: Path, monkeypatch
) -> None:
    """Exercise the real image producer compiler; a task-provided hash is not enough."""
    monkeypatch.setattr(runner, "ALLOW_TEST_FIXTURE_AUTHORIZATION", False)
    prompt = tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(
        "## Clip_01（冷开场）\n"
        "**目标落档**：`出图/第1集/图片/Clip01_first.png`\n"
        "**剧本描述**：她在雨夜缓慢抬眼，镜头极缓推近。\n"
        "**专项镜头模板**：shot_type=close_up；continuity_must=[]；negative=[\"文字\", \"水印\"]。\n",
        encoding="utf-8",
    )
    command = (
        "python3 skills/n2d/n2d-image/scripts/codex_image_runner.py "
        f'"{tmp_path}" 第1集 --shots Clip_01'
    )
    task = canonical_authorization_task(command=command)
    task.pop("input_fingerprint")
    contract = runner.resolve_image_producer_contract(
        str(tmp_path), task, {"env": {"N2D_IMAGE_COMMAND": command}}, command
    )
    record = contract["records"][0]
    assert record["submit_request_sha256"].startswith("sha256:")
    assert record["compiled_request_sha256"]
    assert record["submit_request_sha256"] != record["compiled_request_sha256"]
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-real-image-v1",
        approver="producer@example.invalid",
        model="any",
        channel="any",
        root=str(tmp_path),
        resolved_command=command,
        config={"env": {"N2D_IMAGE_COMMAND": command}},
    )

    prompt.write_text(prompt.read_text(encoding="utf-8").replace("缓慢抬眼", "骤然回头"), encoding="utf-8")
    runner.bind_production_execution_context(
        str(tmp_path), task, {"env": {"N2D_IMAGE_COMMAND": command}}, command
    )
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and "execution" in issue


def test_image_contract_is_compiled_under_exact_child_config_environment(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(runner, "ALLOW_TEST_FIXTURE_AUTHORIZATION", False)
    monkeypatch.delenv("N2D_ASPECT", raising=False)
    prompt = tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(
        "## Clip_01（环境绑定）\n"
        "**目标落档**：`出图/第1集/图片/Clip01_first.png`\n"
        "**剧本描述**：她站在雨幕中。\n"
        "**专项镜头模板**：shot_type=wide；continuity_must=[]；negative=[\"文字\"]。\n",
        encoding="utf-8",
    )
    command = (
        "python3 skills/n2d/n2d-image/scripts/codex_image_runner.py "
        f'"{tmp_path}" 第1集 --shots Clip_01'
    )
    task = canonical_authorization_task(command=command)
    task.pop("input_fingerprint")

    vertical = runner.resolve_image_producer_contract(
        str(tmp_path),
        task,
        {"env": {"N2D_IMAGE_COMMAND": command, "N2D_ASPECT": "9:16"}},
        command,
    )
    wide = runner.resolve_image_producer_contract(
        str(tmp_path),
        task,
        {"env": {"N2D_IMAGE_COMMAND": command, "N2D_ASPECT": "16:9"}},
        command,
    )

    assert vertical["records"][0]["input_fingerprint"] != wide["records"][0]["input_fingerprint"]
    assert vertical["records"][0]["submit_request_sha256"] != wide["records"][0]["submit_request_sha256"]
    assert vertical["execution_environment"]["digest"] != wide["execution_environment"]["digest"]
    assert os.environ.get("N2D_ASPECT") is None


def test_real_video_frame_change_invalidates_authorization(
    tmp_path: Path, monkeypatch
) -> None:
    """Exercise the real prepared-manifest and submit-snapshot implementation."""
    monkeypatch.setattr(runner, "ALLOW_TEST_FIXTURE_AUTHORIZATION", False)
    video = runner._load_producer_module("video", "n2d-video/scripts/video_runner.py")
    frame = tmp_path / "出图" / "第1集" / "图片" / "Clip_01_first.png"
    frame.parent.mkdir(parents=True)
    frame.write_bytes(b"frame-v1")
    prompt = tmp_path / "生产数据" / "video_batches" / "第1集" / "01_01" / "prompts" / "Clip_01.prompt.txt"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("以首帧为真值。人物缓慢抬眼；镜头极缓推近。\n", encoding="utf-8")
    manifest_path = tmp_path / "生产数据" / "video_batch_第1集_01_01.json"
    manifest = {
        "kind": "n2d_video_batch",
        "version": 1,
        "episode": "第1集",
        "backend": "dreamina",
        "channel": "即梦/Dreamina",
        "model_version": "3.0",
        "video_budget_tier": "standard",
        "video_resolution": "720p",
        "ratio": "9:16",
        "batch_id": "01_01",
        "items": [{
            "clip": "Clip_01",
            "target": "Clip_01.mp4",
            "image": str(frame),
            "prompt_file": str(prompt),
            "submit_duration": 4,
            "status": "prepared",
        }],
    }
    manifest["input_fingerprint"] = video.current_video_manifest_input_fingerprint(tmp_path, manifest)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    command = (
        "python3 skills/n2d/n2d-video/scripts/video_runner.py submit "
        f'"{tmp_path}" "{manifest_path}" --clip Clip_01'
    )
    task = canonical_authorization_task(
        stage_key="video",
        command=command,
        producer_manifest=str(manifest_path),
        physical_clips=["Clip_01"],
        estimated_cost={"amount": 12.0, "unit": "work_units"},
    )
    task.pop("input_fingerprint")
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-real-video-v1",
        approver="producer@example.invalid",
        model="any",
        channel="any",
        root=str(tmp_path),
        resolved_command=command,
    )

    frame.write_bytes(b"frame-v2")
    runner.bind_production_execution_context(str(tmp_path), task, {}, command)
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and (
        "canonical producer contract unavailable" in issue or "execution" in issue
    )


@pytest.mark.parametrize(
    ("range_value", "expected"),
    [("02-02", "missing for explicit range"), ("not-a-range", "range is invalid")],
)
def test_video_explicit_range_never_falls_back_to_another_manifest(
    tmp_path: Path, range_value: str, expected: str
) -> None:
    production = tmp_path / "生产数据"
    production.mkdir(parents=True)
    # A different singleton manifest used to be picked as an unsafe fallback.
    (production / "video_batch_第1集_01_01.json").write_text("{}", encoding="utf-8")
    task = canonical_authorization_task(
        stage_key="video",
        physical_clips=["Clip_01"],
    )

    with pytest.raises(runner.ProducerContractError, match=expected):
        runner.resolve_video_producer_contract(
            str(tmp_path),
            task,
            {"env": {"N2D_VIDEO_RANGE": range_value}},
            "python3 skills/n2d/n2d-video/scripts/video_runner.py submit",
        )


@pytest.mark.parametrize("stage", ["voice", "compose"])
def test_stage_without_canonical_producer_manifest_cannot_be_authorized(
    tmp_path: Path, monkeypatch, stage: str
) -> None:
    monkeypatch.setattr(runner, "ALLOW_TEST_FIXTURE_AUTHORIZATION", False)
    task = canonical_authorization_task(
        stage_key=stage,
        command=f"bash run_n2d_{stage}.sh",
    )
    task.pop("input_fingerprint")

    with pytest.raises(ValueError, match="cannot issue production authorization"):
        runner.make_production_authorization(
            task,
            approval_id=f"approval-{stage}",
            approver="producer@example.invalid",
            model="any",
            channel="any",
            root=str(tmp_path),
            resolved_command=str(task["command"]),
        )


def test_changing_submit_request_digest_invalidates_authorization() -> None:
    task = canonical_authorization_task(submit_request_sha256="a" * 64)
    receipt = runner.make_production_authorization(
        task,
        approval_id="approval-request-v1",
        approver="producer@example.invalid",
        model="any",
        channel="any",
    )
    task["submit_request_sha256"] = "b" * 64
    task["_runner_production_authorization"] = receipt

    issue = runner._authorization_issue(task)

    assert issue and "execution" in issue


def test_review_acceptance_signoff_is_human_only_fail_closed(tmp_path: Path, monkeypatch) -> None:
    task = {
        "id": "001-review-progress",
        "episode": "第1集",
        "stage_key": "review",
    }
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": {"ep": "第1集", "stage_key": "review"},
            "stop_reason": "needs_acceptance_signoff",
            "action_card": {"headline": "等待人工验收签收"},
            "gate": None,
        },
    )

    issue = runner._canonical_next_preflight_issue(str(tmp_path), task, preview=True)

    assert issue is not None
    assert issue["stop_reason"] == "needs_acceptance_signoff"

    task["command"] = "python3 -c \"pass\""
    result = runner.execute_task(
        str(tmp_path),
        task,
        {},
        command_override=str(task["command"]),
        shell=False,
        timeout_sec=None,
        dry_run=True,
        no_dashboard=True,
        verify_outputs=False,
        next_preflight=False,
        build_dashboard=False,
    )
    assert result["status"] == "qa_blocked"
    assert "acceptance evidence verification failed" in result["note"]


def test_review_runner_waits_for_acceptance_then_reconciles_without_rerun(
    tmp_path: Path, monkeypatch
) -> None:
    write_progress(tmp_path)
    task = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("review"),
        reason="rerun",
        priority=1,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )
    ledger = queue.make_queue(str(tmp_path), [task], max_concurrency=1, max_retries=1, budget={})
    queue.save_queue(str(tmp_path), ledger)
    marker = tmp_path / "review_command_count.txt"
    command = (
        "python3 -c \"from pathlib import Path; "
        f"p=Path(r'{marker}'); p.write_text((p.read_text() if p.exists() else '')+'x')\""
    )
    config_path = tmp_path / "生产数据" / "batch_runner.json"
    config_path.write_text(
        json.dumps({"commands": {"review": command}, "next_preflight": False}),
        encoding="utf-8",
    )
    production = tmp_path / "生产数据"
    for name in (
        "score_第1集.json",
        "consistency_ledger_第1集.json",
        "review_ui_第1集.json",
        "review_ui_findings_第1集.json",
    ):
        (production / name).write_text("{}", encoding="utf-8")
    master = tmp_path / "合成" / "第1集" / "成片_第1集_zh.mp4"
    master.parent.mkdir(parents=True)
    write_test_mp4(master)
    monkeypatch.setattr(
        runner.run_mod,
        "next_action",
        lambda root, ep, **kwargs: {
            "frontier": {"ep": "第1集", "stage_key": "review"},
            "stop_reason": "needs_acceptance_signoff",
            "action_card": {"headline": "等待人工验收签收"},
            "gate": None,
        },
    )
    monkeypatch.setattr(
        runner,
        "refresh_gate",
        lambda root, ep, stage: {"stage": stage, "exit_code": 0, "blocks": 0, "warns": 0},
    )
    monkeypatch.setattr(
        queue.acceptance_contract,
        "check_acceptance",
        lambda root, ep: {"status": "fail", "valid": False, "decision": "", "issues": ["missing"]},
    )

    first = runner.run_once(str(tmp_path), limit=1, config_path=str(config_path), no_dashboard=True)
    waiting = queue.load_queue(str(tmp_path))["tasks"][0]

    assert first["results"][0]["queue_status"] == "qa_blocked"
    assert waiting["completion_block_reason"] == "needs_acceptance_signoff"
    assert waiting["last_runner"]["completion"]["output_verification"]["status"] == "pass"
    assert waiting["last_runner"]["completion"]["post_gate"]["status"] == "pass"
    assert "worker" not in waiting and "lease_until" not in waiting
    assert not marker.exists(), "needs_acceptance_signoff must not rerun review"

    monkeypatch.setattr(
        queue.acceptance_contract,
        "check_acceptance",
        lambda root, ep: {
            "status": "pass",
            "valid": True,
            "decision": "approved",
            "receipt_id": "receipt-1",
            "issues": [],
        },
    )
    progress_path = tmp_path / "_进度.md"
    progress_lines = progress_path.read_text(encoding="utf-8").splitlines()
    cells = progress_lines[2].split("|")
    cells[-2] = " ✅ "
    progress_lines[2] = "|".join(cells)
    progress_path.write_text("\n".join(progress_lines), encoding="utf-8")
    reconciled = queue.mark(str(tmp_path), task["id"], "pass", "human receipt available")

    assert reconciled["status"] == "done"
    assert reconciled["attempts"] == 1
    assert not marker.exists(), "receipt reconciliation must not rerun review"
