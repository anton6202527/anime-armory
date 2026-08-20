from __future__ import annotations

import importlib.util
import base64
import json
import os
import sys
import threading
import datetime as dt
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("queue.py")
SCRIPT_DIR = SCRIPT.resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != SCRIPT_DIR]
shadow = sys.modules.get("queue")
if shadow is not None and Path(getattr(shadow, "__file__", "") or "").resolve() == SCRIPT.resolve():
    del sys.modules["queue"]
spec = importlib.util.spec_from_file_location("n2d_batch_queue", SCRIPT)
queue = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(queue)


def write_progress(root: Path) -> None:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (root / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | — | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
                "| 第2集 | 820 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | 1/3 | ⬜ | ⬜ | ⬜ | ⬜ |",
                "| 第3集 | 830 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | 1/2 | ⬜ | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )


def production_completion(root: Path, task: dict, *, gate_required: bool) -> dict:
    """Explicit canonical completion evidence used only by queue unit fixtures."""
    digest = "sha256:" + "a" * 64
    execution = {
        "command_digest": digest,
        "input_fingerprint": digest,
        "submit_request_digest": digest,
        "producer_contract_digest": digest,
    }
    scope = {
        "rerun_scope": str(task.get("rerun_scope") or ""),
        "affected_shots": sorted({str(item) for item in task.get("affected_shots", []) if str(item)}),
        "affected_artifacts": sorted({str(item) for item in task.get("affected_artifacts", []) if str(item)}),
    }
    estimate = task.get("estimated_cost") or {}
    task_binding = {
        "task_id": str(task.get("id") or ""),
        "idempotency_key": str(task.get("idempotency_key") or ""),
        "episode": queue.normalize_episode(str(task.get("episode") or "")),
        "stage_key": str(task.get("stage_key") or ""),
        "attempt": int(task.get("attempts") or 0),
        "scope": scope,
        "estimated_cost": {
            "amount": float(estimate.get("amount")),
            "currency": str(estimate.get("unit") or ""),
        },
        "execution": execution,
    }
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    authorization = {
        "version": 1,
        "approval_id": "test-approval",
        "decision": "approved",
        "approver": "qa-human@example.invalid",
        "issued_at": (now - dt.timedelta(minutes=1)).isoformat(),
        "expires_at": (now + dt.timedelta(hours=1)).isoformat(),
        "task_id": task_binding["task_id"],
        "idempotency_key": task_binding["idempotency_key"],
        "task_digest": queue._canonical_sha256(task_binding),
        "attempt": task_binding["attempt"],
        "stage_key": task_binding["stage_key"],
        "episode": task_binding["episode"],
        "scope": scope,
        "execution": execution,
        "model": "any",
        "channel": "any",
        "ceiling": {
            "amount": task_binding["estimated_cost"]["amount"],
            "currency": task_binding["estimated_cost"]["currency"],
        },
    }
    authorization["authorization_digest"] = queue._canonical_sha256(authorization)
    output_rel = f"生产数据/test-fixtures/{task.get('id') or 'task'}-{int(task.get('attempts') or 0)}.png"
    output_path = root / output_rel
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    ))
    record = {
        "shot": str(next(iter(task.get("affected_shots") or []), "fixture-target")),
        "target": output_rel,
        "input_fingerprint": digest,
        "submit_request_sha256": digest,
    }
    expectation = queue.paid_execution_contract.build_expectation(
        stage=str(task.get("stage_key") or ""),
        task_id=str(task.get("id") or ""),
        episode=queue.normalize_episode(str(task.get("episode") or "")),
        attempt=int(task.get("attempts") or 0),
        authorization_digest=authorization["authorization_digest"],
        records=[record],
    )
    updates = {
        **queue.paid_execution_contract.environment_for_expectation(expectation),
        "N2D_ROOT": str(root),
        "N2D_TASK_ID": str(task.get("id") or ""),
    }
    previous = {key: os.environ.get(key) for key in updates}
    try:
        os.environ.update(updates)
        queue.paid_execution_contract.enforce_expected_paid_request(
            stage=str(task.get("stage_key") or ""),
            identity=record["shot"],
            target=record["target"],
            input_fingerprint=record["input_fingerprint"],
            submit_request_sha256=record["submit_request_sha256"],
        )
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    receipts = queue.paid_execution_contract.verify_expected_receipts(root, expectation)
    output_sha = queue.paid_execution_contract._sha256_file(output_path)
    return {
        "status": "pass",
        "exit_code": 0,
        "execution_started": True,
        "finished_at": "2026-08-20T00:00:00+00:00",
        "authorization": authorization,
        "execution_binding": execution,
        "completion": {
            "output_verification": {"status": "pass", "issues": []},
            "post_gate": {"status": "pass" if gate_required else "not_applicable"},
            "paid_execution_expectation": expectation,
            "paid_execution_receipts": receipts,
            "producer_output_bindings": [{
                "path": output_rel,
                "exists": True,
                "sha256": output_sha,
                "bytes": output_path.stat().st_size,
                "issue": "",
            }],
        }
    }


def test_route_plan_and_budget_cap(tmp_path: Path) -> None:
    write_progress(tmp_path)
    estimates = queue.load_cost_estimates(str(tmp_path))
    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=None,
        stage_filters=None,
        cost_estimates=estimates,
        max_retries=2,
    )
    budget = queue.apply_budget(tasks, 4.0, "work_units")
    planned = queue.make_queue(str(tmp_path), tasks, max_concurrency=2, max_retries=2, budget=budget)

    assert [task["stage_key"] for task in planned["tasks"]] == ["voice", "image", "video"]
    assert [task["status"] for task in planned["tasks"]] == ["queued", "queued", "blocked_budget"]
    assert planned["budget"]["accepted_total"] == 4.0
    assert planned["batches"] == [[planned["tasks"][0]["id"], planned["tasks"][1]["id"]]]
    assert planned["coordination"]["backend"] == "local_file"


def test_stage_filter_and_episode_selector(tmp_path: Path) -> None:
    write_progress(tmp_path)
    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("2-3"),
        stage_filters={"video"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )

    assert len(tasks) == 1
    assert tasks[0]["episode"] == "第3集"
    assert tasks[0]["owner"] == "n2d-video"


def test_route_image_task_freezes_all_prompt_physical_shots(tmp_path: Path) -> None:
    write_progress(tmp_path)
    prompt = tmp_path / "出图" / "第2集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("## Clip_01 开场\n\n## 镜头 3 特写\n", encoding="utf-8")

    tasks = queue.route_tasks(
        str(tmp_path),
        episodes={"第2集"},
        stage_filters={"image"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )

    assert len(tasks) == 1
    assert tasks[0]["affected_shots"] == ["Clip_01", "Clip_03"]
    assert "--shots Clip_01,Clip_03" in tasks[0]["command"]


def test_route_review_after_compose(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )

    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=None,
        stage_filters={"review"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )

    assert len(tasks) == 1
    assert tasks[0]["stage_key"] == "review"
    assert tasks[0]["owner"] == "n2d-review"


def test_video_done_queues_compose_by_default(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )

    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=None,
        stage_filters={"compose"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )

    assert len(tasks) == 1
    assert tasks[0]["stage_key"] == "compose"


def test_video_done_does_not_queue_compose_when_explicitly_skipped(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 制作模式: 配音先行\n- 合成阶段: 跳过\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )

    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=None,
        stage_filters={"compose"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )

    assert tasks == []


def test_episode_selector_accepts_chinese_and_fullwidth_numbers(tmp_path: Path) -> None:
    assert queue.parse_episode_selector("一-三") == {"第1集", "第2集", "第3集"}
    assert queue.parse_episode_selector("第２集,第三集") == {"第2集", "第3集"}
    assert queue.episode_num("第三集") == 3
    assert queue.task_id("第三集", "image", "progress").startswith("003-")


def test_route_filter_matches_chinese_episode_row(tmp_path: Path) -> None:
    write_progress(tmp_path)
    text = (tmp_path / "_进度.md").read_text(encoding="utf-8").replace("第3集", "第三集")
    (tmp_path / "_进度.md").write_text(text, encoding="utf-8")

    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("3"),
        stage_filters={"video"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )

    assert len(tasks) == 1
    assert tasks[0]["episode"] == "第三集"


def test_targeted_rerun_and_claim_retry(tmp_path: Path) -> None:
    write_progress(tmp_path)
    tasks = queue.rerun_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("2") or set(),
        rerun_from="image",
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
        rerun_scope="只重跑 Clip_03 首帧",
        affected_artifacts=["出图/第2集/图片/Clip_03.png"],
        affected_shots=["Clip_03"],
    )
    budget = queue.apply_budget(tasks, None, None)
    ledger = queue.make_queue(str(tmp_path), tasks, max_concurrency=1, max_retries=1, budget=budget)
    queue.save_queue(str(tmp_path), ledger)

    loaded = queue.load_queue(str(tmp_path))
    claimed = queue.claim_tasks(loaded, limit=1)
    assert len(claimed) == 1
    assert claimed[0]["status"] == "running"
    assert claimed[0]["attempts"] == 1

    failed = queue.mark_task(loaded, claimed[0]["id"], "fail", "脸漂移")
    assert failed["status"] == "retry_queued"

    claimed_again = queue.claim_tasks(loaded, limit=1)
    assert claimed_again[0]["attempts"] == 2
    failed_again = queue.mark_task(loaded, claimed[0]["id"], "fail", "仍脸漂移")
    assert failed_again["status"] == "failed"
    assert failed_again["affected_shots"] == ["Clip_03"]
    assert failed_again["dead_letter"] is True
    assert failed_again["last_error_class"] in {"command_failed", "unknown"}


def test_script_stage1_rerun_is_agent_required_not_runner_claimable(tmp_path: Path) -> None:
    write_progress(tmp_path)
    tasks = queue.rerun_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("1") or set(),
        rerun_from="script_stage1",
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
        rerun_scope="skill 更新后重制到 image",
        affected_artifacts=[],
        affected_shots=[],
    )
    budget = queue.apply_budget(tasks, None, None)
    ledger = queue.make_queue(str(tmp_path), tasks, max_concurrency=1, max_retries=1, budget=budget)

    task = ledger["tasks"][0]
    assert task["stage_key"] == "script_stage1"
    assert task["status"] == "blocked_agent"
    assert task["runner_mode"] == "agent_required"
    assert task["agent_command"].startswith("n2d-script ")
    assert ledger["batches"] == []
    assert budget["accepted_total"] == 0.0
    assert queue.claim_tasks(ledger, limit=1) == []


def test_mark_pass_clears_previous_failure_metadata(tmp_path: Path) -> None:
    write_progress(tmp_path)
    task = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("image"),
        reason="rerun",
        priority=1,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
        rerun_scope="修脸",
    )
    ledger = queue.make_queue(str(tmp_path), [task], max_concurrency=1, max_retries=1, budget={})
    claimed = queue.claim_tasks(ledger, limit=1)
    failed = queue.mark_task(
        ledger,
        claimed[0]["id"],
        "fail",
        "exit_code=1",
        runner={"exit_code": 1},
    )
    assert failed["status"] == "retry_queued"
    assert failed["last_error_class"] == "command_failed"

    claimed_again = queue.claim_tasks(ledger, limit=1)
    passed = queue.mark_task(
        ledger,
        claimed_again[0]["id"],
        "pass",
        "exit_code=0",
        runner=production_completion(tmp_path, claimed_again[0], gate_required=True),
    )
    assert passed["status"] == "done"
    assert "last_error_class" not in passed
    assert "dead_letter" not in passed
    assert "dead_letter_at" not in passed


def test_production_mark_pass_without_completion_evidence_is_rejected(tmp_path: Path) -> None:
    write_progress(tmp_path)
    task = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("image"),
        reason="rerun",
        priority=1,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )
    ledger = queue.make_queue(str(tmp_path), [task], max_concurrency=1, max_retries=1, budget={})
    claimed = queue.claim_tasks(ledger, limit=1)

    with pytest.raises(ValueError, match="cannot be marked done"):
        queue.mark_task(ledger, claimed[0]["id"], "pass", "exit_code=0")

    assert ledger["tasks"][0]["status"] == "running"


def test_manual_review_mark_pass_without_human_acceptance_waits_outside_running(tmp_path: Path) -> None:
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
    claimed = queue.claim_tasks(ledger, limit=1)
    completion_without_acceptance = {
        "status": "pass",
        "exit_code": 0,
        "execution_started": False,
        "finished_at": "2026-08-20T00:00:00+00:00",
        "completion": {
            "output_verification": {"status": "pass", "issues": []},
            "post_gate": {"status": "pass"},
        }
    }

    waiting = queue.mark_task(
        ledger,
        claimed[0]["id"],
        "pass",
        "manual CLI attempted pass",
        runner=completion_without_acceptance,
    )

    assert waiting["status"] == "qa_blocked"
    assert waiting["completion_block_reason"] == "needs_acceptance_signoff"
    assert waiting["last_runner"]["completion"] == completion_without_acceptance["completion"]
    assert "worker" not in waiting and "lease_until" not in waiting
    assert waiting["status"] != "done"


def test_review_acceptance_reconciles_persisted_evidence_without_rerun(
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
    claimed = queue.claim_tasks(ledger, limit=1, worker="review-worker")
    completion = {
        "command": "review-once",
        "status": "pass",
        "exit_code": 0,
        "execution_started": False,
        "finished_at": "2026-08-20T00:00:00+00:00",
        "completion": {
            "output_verification": {"status": "pass", "issues": []},
            "post_gate": {"status": "pass"},
        },
    }
    monkeypatch.setattr(
        queue.acceptance_contract,
        "check_acceptance",
        lambda root, ep: {"status": "fail", "valid": False, "decision": "", "issues": ["missing"]},
    )
    waiting = queue.mark_task(ledger, claimed[0]["id"], "pass", runner=completion)
    assert waiting["status"] == "qa_blocked"

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
    done = queue.mark_task(ledger, task["id"], "pass")

    assert done["status"] == "done"
    assert done["attempts"] == 1
    assert done["last_runner"]["command"] == "review-once"
    assert done["completion_commit"]["acceptance"]["receipt_id"] == "receipt-1"
    assert queue.completion_commit_issue(done) is None
    assert "completion_block_reason" not in done


def test_completion_commit_rejects_contradictory_runner_and_detects_tampering(tmp_path: Path) -> None:
    write_progress(tmp_path)
    task = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("image"),
        reason="rerun",
        priority=1,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )
    ledger = queue.make_queue(str(tmp_path), [task], max_concurrency=1, max_retries=1, budget={})
    claimed = queue.claim_tasks(ledger, limit=1)
    contradictory = production_completion(tmp_path, claimed[0], gate_required=True)
    contradictory["status"] = "fail"
    contradictory["exit_code"] = 9

    with pytest.raises(ValueError, match="runner status must be pass"):
        queue.mark_task(ledger, claimed[0]["id"], "pass", runner=contradictory)

    done = queue.mark_task(
        ledger,
        claimed[0]["id"],
        "pass",
        runner=production_completion(tmp_path, claimed[0], gate_required=True),
    )
    assert done["completion_commit"]["content_fingerprint"].startswith("sha256:")
    assert queue.completion_commit_issue(done) is None

    done["completion_commit"]["completion"]["post_gate"]["status"] = "block"
    assert queue.completion_commit_issue(done) == "completion_commit digest mismatch"


def test_completion_commit_rechecks_paid_output_under_lock(tmp_path: Path) -> None:
    write_progress(tmp_path)
    task = queue.task_from_spec(
        str(tmp_path), "第1集", queue.find_stage("image"), reason="rerun", priority=1,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=1,
    )
    ledger = queue.make_queue(str(tmp_path), [task], max_concurrency=1, max_retries=1, budget={})
    claimed = queue.claim_tasks(ledger, limit=1)[0]
    evidence = production_completion(tmp_path, claimed, gate_required=True)
    output = tmp_path / evidence["completion"]["producer_output_bindings"][0]["path"]
    output.unlink()

    blocked = queue.mark_task(ledger, claimed["id"], "pass", runner=evidence)

    assert blocked["status"] == "qa_blocked"
    assert blocked["completion_block_reason"] == "output_changed_before_commit"
    assert "paid outputs changed" in blocked["last_note"]
    assert "completion_commit" not in claimed


@pytest.mark.parametrize("case", ["missing_column", "missing_row"])
def test_review_acceptance_missing_progress_contract_fails_closed(tmp_path: Path, case: str) -> None:
    if case == "missing_column":
        text = "| 集 | 视频 |\n|---|---|\n| 第1集 | ✅ |\n"
    else:
        text = "| 集 | 验收 |\n|---|---|\n| 第2集 | ⬜ |\n"
    (tmp_path / "_进度.md").write_text(text, encoding="utf-8")
    task = {"id": "001-review", "episode": "第1集", "stage_key": "review"}

    issue = queue._canonical_acceptance_issue({"root": str(tmp_path)}, task)

    assert issue is not None
    assert "progress" in issue


def test_task_idempotency_key_is_stable_for_same_scope(tmp_path: Path) -> None:
    estimates = queue.load_cost_estimates(str(tmp_path))
    a = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("image"),
        reason="rerun",
        priority=1,
        cost_estimates=estimates,
        max_retries=1,
        rerun_scope="修脸",
        affected_shots=["Clip_03"],
        affected_artifacts=["出图/第1集/图片/Clip_03.png"],
    )
    b = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("image"),
        reason="rerun",
        priority=2,
        cost_estimates=estimates,
        max_retries=1,
        rerun_scope="修脸",
        affected_artifacts=["出图/第1集/图片/Clip_03.png"],
        affected_shots=["Clip_03"],
    )

    assert a["idempotency_key"] == b["idempotency_key"]


def test_coordination_status_warns_shared_fs_without_atomic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "shared_fs")
    monkeypatch.setenv("N2D_QUEUE_LOCK", "flock")
    status = queue.coordination_backend_status(str(tmp_path))
    assert status["backend"] == "shared_fs"
    assert status["status"] == "warn"
    assert "atomic" in status["warning"]


def test_coordination_status_external_backend_is_declared_not_active(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "redis")
    monkeypatch.setenv("N2D_COORDINATION_DSN", "redis://localhost:6379/0")
    status = queue.coordination_backend_status(str(tmp_path))
    assert status["backend"] == "redis"
    assert status["status"] == "declared_not_active"
    assert status["dsn_present"] is True


def test_sqlite_coordination_claim_mark_heartbeat(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "sqlite")
    _saved_queue(tmp_path, max_concurrency=1)

    status = queue.coordination_backend_status(str(tmp_path))
    assert status["backend"] == "sqlite"
    assert status["status"] == "ok"
    assert status["db_path"].endswith("batch_queue.sqlite3")

    claimed = queue.claim(str(tmp_path), limit=1, worker="sqlite-worker", lease_seconds=10)
    assert len(claimed) == 1
    tid = claimed[0]["id"]
    old_lease = claimed[0]["lease_until"]
    assert (tmp_path / "生产数据" / "batch_queue.sqlite3").is_file()

    assert queue.renew(str(tmp_path), [tid], 600, "sqlite-worker") == 1
    loaded = queue.load_queue(str(tmp_path))
    task = next(t for t in loaded["tasks"] if t["id"] == tid)
    assert task["lease_until"] > old_lease

    marked = queue.mark(
        str(tmp_path),
        tid,
        "pass",
        runner=production_completion(tmp_path, claimed[0], gate_required=False),
        expected_worker="sqlite-worker",
        expected_attempt=1,
    )
    assert marked["status"] == "done"
    mirrored = json.loads((tmp_path / "生产数据" / "batch_queue.json").read_text(encoding="utf-8"))
    assert next(t for t in mirrored["tasks"] if t["id"] == tid)["status"] == "done"


def test_sqlite_coordination_dead_letter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "sqlite")
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="w", lease_seconds=10)
    tid = claimed[0]["id"]

    queue.mark(str(tmp_path), tid, "fail", expected_worker="w", expected_attempt=1)
    retry = queue.claim(str(tmp_path), limit=1, worker="w", lease_seconds=10)
    assert retry[0]["id"] == tid
    failed = queue.mark(str(tmp_path), tid, "fail", expected_worker="w", expected_attempt=2)

    assert failed["status"] == "retry_queued"  # max_retries=2 from _saved_queue; final fail happens after attempt 3
    third = queue.claim(str(tmp_path), limit=1, worker="w", lease_seconds=10)
    assert third[0]["id"] == tid
    dead = queue.mark(str(tmp_path), tid, "fail", expected_worker="w", expected_attempt=3)
    assert dead["status"] == "failed"
    assert dead["dead_letter"] is True


def test_sqlite_doctor_passes_and_detects_mirror_divergence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "sqlite")
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="doctor-worker", lease_seconds=10)
    assert claimed

    ok = queue.sqlite_doctor(str(tmp_path), write=True)
    assert ok["status"] == "pass"
    assert (tmp_path / "生产数据" / "sqlite_doctor.json").is_file()

    mirror_path = tmp_path / "生产数据" / "batch_queue.json"
    mirror = json.loads(mirror_path.read_text(encoding="utf-8"))
    mirror["tasks"][0]["status"] = "queued"
    mirror_path.write_text(json.dumps(mirror, ensure_ascii=False), encoding="utf-8")

    bad = queue.sqlite_doctor(str(tmp_path))
    assert bad["status"] == "fail"
    assert any("diverged" in item["message"] for item in bad["issues"])


def test_classify_error_treats_timeout_exit_codes_as_timeout() -> None:
    assert queue.classify_error("", {"exit_code": 124}) == "timeout"
    assert queue.classify_error("", {"exit_code": 137}) == "timeout"
    assert queue.classify_error("verification failed: missing output") == "output_contract"


def _saved_queue(tmp_path: Path, max_concurrency: int = 2):
    write_progress(tmp_path)
    tasks = queue.route_tasks(str(tmp_path), episodes=None, stage_filters=None,
                              cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=2)
    ledger = queue.make_queue(str(tmp_path), tasks, max_concurrency=max_concurrency, max_retries=2,
                              budget=queue.apply_budget(tasks, None, None))
    queue.save_queue(str(tmp_path), ledger)
    return ledger


def test_claim_sets_worker_and_lease_then_mark_clears(tmp_path: Path) -> None:
    _saved_queue(tmp_path)
    claimed = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=60)
    assert claimed and claimed[0]["worker"] == "w1"
    assert claimed[0]["lease_until"] > queue.now_ts()
    marked = queue.mark(
        str(tmp_path),
        claimed[0]["id"],
        "pass",
        runner=production_completion(tmp_path, claimed[0], gate_required=False),
    )
    assert marked["status"] == "done"
    assert "lease_until" not in marked and "worker" not in marked


def test_concurrent_claims_do_not_double_claim(tmp_path: Path) -> None:
    # 同一锁内重读：两次连续 claim 各拿不同任务，不重复（capacity=2）。
    _saved_queue(tmp_path, max_concurrency=2)
    a = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=60)
    b = queue.claim(str(tmp_path), limit=1, worker="w2", lease_seconds=60)
    ids_a = {t["id"] for t in a}
    ids_b = {t["id"] for t in b}
    assert ids_a and ids_b
    assert ids_a.isdisjoint(ids_b)  # 绝不双认领
    # 并发上限到顶：第三次拿不到
    assert queue.claim(str(tmp_path), limit=1, worker="w3", lease_seconds=60) == []


def test_two_workers_cannot_atomically_reserve_past_runtime_budget_cap(tmp_path: Path) -> None:
    write_progress(tmp_path)
    estimates = queue.load_cost_estimates(str(tmp_path))
    tasks = [
        queue.task_from_spec(
            str(tmp_path),
            "第1集",
            queue.find_stage(stage),
            reason="rerun",
            priority=index,
            cost_estimates=estimates,
            max_retries=1,
        )
        for index, stage in enumerate(("image", "video"), start=1)
    ]
    for task in tasks:
        task["estimated_cost"] = {"amount": 6.0, "unit": "work_units"}
        task["status"] = "queued"  # deliberately bypass planning trim; claim must still enforce cap
    ledger = queue.make_queue(
        str(tmp_path),
        tasks,
        max_concurrency=2,
        max_retries=1,
        budget={"limit": 10.0, "unit": "work_units"},
    )
    queue.save_queue(str(tmp_path), ledger)

    start = threading.Barrier(2)

    def _claim(worker: str):
        start.wait(timeout=5)
        return queue.claim(str(tmp_path), limit=1, worker=worker, lease_seconds=60)

    # Both workers cross the barrier together. Each public claim executes under queue_lock (or
    # BEGIN IMMEDIATE), so the loser must observe the winner's just-committed reservation.
    results = []
    threads = [
        threading.Thread(target=lambda worker=worker: results.append(_claim(worker)))
        for worker in ("budget-w1", "budget-w2")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert not any(thread.is_alive() for thread in threads)

    assert sum(len(rows) for rows in results) == 1
    loaded = queue.load_queue(str(tmp_path))
    assert sorted(task["status"] for task in loaded["tasks"]) == ["blocked_budget", "running"]
    assert loaded["budget"]["runtime_reserved_total"] == 6.0
    assert loaded["budget"]["runtime_available"] == 4.0


def test_preflight_failure_releases_runtime_budget_reservation(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="budget-worker", lease_seconds=60)
    assert claimed and claimed[0]["budget_reservation"]["status"] == "reserved"

    failed = queue.mark(
        str(tmp_path),
        claimed[0]["id"],
        "fail",
        "next_preflight blocked before command",
        runner={"exit_code": None, "execution_started": False, "error_class": "preflight_block"},
        expected_worker="budget-worker",
        expected_attempt=1,
    )

    loaded = queue.load_queue(str(tmp_path))
    assert failed["budget_reservation"]["status"] == "released"
    assert loaded["budget"]["runtime_reserved_total"] == 0.0
    assert loaded["budget"]["runtime_settled_total"] == 0.0


def test_command_failure_after_paid_boundary_settles_estimate_not_release(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="paid-worker", lease_seconds=60)
    estimate = float(claimed[0]["estimated_cost"]["amount"])

    failed = queue.mark(
        str(tmp_path),
        claimed[0]["id"],
        "fail",
        "exit_code=7",
        runner={"exit_code": 7, "execution_started": True, "error_class": "command_failed"},
        expected_worker="paid-worker",
        expected_attempt=1,
    )

    loaded = queue.load_queue(str(tmp_path))
    assert failed["budget_reservation"]["status"] == "settled"
    assert loaded["budget"]["runtime_reserved_total"] == 0.0
    assert loaded["budget"]["runtime_settled_total"] == estimate


def test_reclaim_expired_lease_returns_task_to_queue(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="dead", lease_seconds=60)
    tid = claimed[0]["id"]
    # 手动把租约设到过去，模拟 worker 崩溃
    loaded = queue.load_queue(str(tmp_path))
    for t in loaded["tasks"]:
        if t["id"] == tid:
            t["lease_until"] = queue.now_ts() - 1
    queue.save_queue(str(tmp_path), loaded)
    reclaimed = queue.reclaim(str(tmp_path))
    assert [t["id"] for t in reclaimed] == [tid]
    after = queue.load_queue(str(tmp_path))
    task = next(t for t in after["tasks"] if t["id"] == tid)
    assert task["status"] == "retry_queued"   # attempts=1 <= max_retries=2
    assert "lease_until" not in task
    # 回收后可被新 worker 再认领
    again = queue.claim(str(tmp_path), limit=1, worker="alive", lease_seconds=60)
    assert again[0]["id"] == tid and again[0]["worker"] == "alive"


def test_force_worker_reclaim_for_resume(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=9999)  # 租约没过期
    tid = claimed[0]["id"]
    # 不强制：租约未过期 → 不回收
    assert queue.reclaim(str(tmp_path), worker="w1", force_worker=False) == []
    # 强制本 worker（--resume 语义）→ 回收自己的残留 running
    reclaimed = queue.reclaim(str(tmp_path), worker="w1", force_worker=True)
    assert [t["id"] for t in reclaimed] == [tid]


def test_renew_extends_lease(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=10)
    tid = claimed[0]["id"]
    before = queue.load_queue(str(tmp_path))
    old = next(t for t in before["tasks"] if t["id"] == tid)["lease_until"]
    assert queue.renew(str(tmp_path), [tid], 600, "w1") == 1
    after = queue.load_queue(str(tmp_path))
    assert next(t for t in after["tasks"] if t["id"] == tid)["lease_until"] > old


def test_stale_worker_mark_is_rejected_after_reclaim(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    old_claim = queue.claim(str(tmp_path), limit=1, worker="dead", lease_seconds=60)
    tid = old_claim[0]["id"]
    loaded = queue.load_queue(str(tmp_path))
    for t in loaded["tasks"]:
        if t["id"] == tid:
            t["lease_until"] = queue.now_ts() - 1
    queue.save_queue(str(tmp_path), loaded)
    queue.reclaim(str(tmp_path))
    new_claim = queue.claim(str(tmp_path), limit=1, worker="alive", lease_seconds=60)
    assert new_claim[0]["id"] == tid

    try:
        queue.mark(str(tmp_path), tid, "pass", expected_worker="dead", expected_attempt=old_claim[0]["attempts"])
        assert False, "stale worker mark should have been rejected"
    except ValueError:
        pass
    after = queue.load_queue(str(tmp_path))
    task = next(t for t in after["tasks"] if t["id"] == tid)
    assert task["status"] == "running"
    assert task["worker"] == "alive"


def test_save_queue_is_atomic_no_leftover_tmp(tmp_path: Path) -> None:
    _saved_queue(tmp_path)
    pdir = tmp_path / "生产数据"
    leftovers = [p for p in pdir.iterdir() if ".tmp." in p.name]
    assert leftovers == []
    assert (pdir / "batch_queue.json").is_file()


def test_plan_merge_preserves_running_task(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    running = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=600)
    assert running

    # A later plan for a narrower stage must not overwrite the running ledger.
    tasks = queue.rerun_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("2") or set(),
        rerun_from="image",
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
        rerun_scope="新返工",
        affected_artifacts=[],
        affected_shots=[],
    )
    planned = queue.make_queue(
        str(tmp_path),
        tasks,
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget(tasks, None, None),
    )

    merged = queue.write_planned_queue(str(tmp_path), planned)

    assert any(t["id"] == running[0]["id"] and t["status"] == "running" for t in merged["tasks"])
    assert any(t["reason"] == "rerun" for t in merged["tasks"])


def test_plan_merge_reapplies_budget_to_full_ledger(tmp_path: Path) -> None:
    estimates = queue.load_cost_estimates(str(tmp_path))
    image = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("image"),
        reason="progress",
        priority=1,
        cost_estimates=estimates,
        max_retries=1,
    )
    existing = queue.make_queue(
        str(tmp_path),
        [image],
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget([image], 3.0, "work_units"),
    )
    queue.save_queue(str(tmp_path), existing)

    voice = queue.task_from_spec(
        str(tmp_path),
        "第2集",
        queue.find_stage("voice"),
        reason="progress",
        priority=2,
        cost_estimates=estimates,
        max_retries=1,
    )
    planned = queue.make_queue(
        str(tmp_path),
        [voice],
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget([voice], 3.0, "work_units"),
    )

    merged = queue.write_planned_queue(str(tmp_path), planned)

    by_stage = {(task["episode"], task["stage_key"]): task for task in merged["tasks"]}
    assert by_stage[("第1集", "image")]["status"] == "queued"
    assert by_stage[("第2集", "voice")]["status"] == "blocked_budget"
    assert merged["budget"]["scope"] == "ledger"
    assert merged["budget"]["accepted_total"] == 3.0
    assert merged["budget"]["estimated_total"] == 4.0
    assert merged["budget"]["blocked_tasks"] == 1


def _impact_plan(root: Path) -> dict:
    return {
        "kind": "n2d_asset_rerun_plan",
        "version": 1,
        "root": str(root),
        "assets": ["沈念"],
        "rerun_tasks": [
            {"episode": "第1集", "rerun_from": "image", "scope": "定妆沈念变更连锁·重出受影响镜头",
             "affected_artifacts": ["出图/第1集/图片/Clip_01.png"], "affected_shots": ["Clip_01"]},
            {"episode": "第1集", "rerun_from": "video", "scope": "定妆沈念变更连锁·重生已出视频 clip",
             "affected_artifacts": ["出视频/第1集/视频/Clip_01.mp4"], "affected_shots": ["Clip_01"]},
            {"episode": "第2集", "rerun_from": "image", "scope": "定妆沈念变更连锁·重出受影响镜头",
             "affected_artifacts": ["出图/第2集/图片/Clip_05.png"], "affected_shots": ["Clip_05"]},
        ],
    }


def test_tasks_from_asset_impact_builds_rerun_tasks(tmp_path: Path) -> None:
    """asset_impact --output-batch-tasks 的 JSON → 队列任务（字段透传、kind 校验、集过滤）。"""
    plan = _impact_plan(tmp_path)
    tasks = queue.tasks_from_asset_impact(
        str(tmp_path), plan,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=1,
    )
    assert [(t["episode"], t["stage_key"]) for t in tasks] == [
        ("第1集", "image"), ("第1集", "video"), ("第2集", "image")]
    assert all(t["reason"] == "rerun" for t in tasks)
    assert tasks[0]["affected_shots"] == ["Clip_01"]
    assert tasks[0]["rerun_scope"].startswith("定妆沈念变更连锁")
    # 集过滤
    only2 = queue.tasks_from_asset_impact(
        str(tmp_path), plan,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=1,
        episodes=queue.parse_episode_selector("2"),
    )
    assert [(t["episode"], t["stage_key"]) for t in only2] == [("第2集", "image")]
    # kind 校验
    try:
        queue.tasks_from_asset_impact(
            str(tmp_path), {"kind": "x"},
            cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=1)
        assert False, "kind mismatch should raise"
    except ValueError:
        pass


def test_plan_from_asset_impact_cli_writes_queue(tmp_path: Path) -> None:
    import json
    write_progress(tmp_path)
    plan_path = tmp_path / "impact_plan.json"
    plan_path.write_text(json.dumps(_impact_plan(tmp_path), ensure_ascii=False), encoding="utf-8")
    rc = queue.main(["plan", str(tmp_path), "--from-asset-impact", str(plan_path)])
    assert rc == 0
    loaded = queue.load_queue(str(tmp_path))
    by_id = {(t["episode"], t["stage_key"]): t for t in loaded["tasks"]}
    assert ("第1集", "image") in by_id and ("第1集", "video") in by_id and ("第2集", "image") in by_id
    task = by_id[("第1集", "video")]
    assert task["reason"] == "rerun"
    assert task["affected_artifacts"] == ["出视频/第1集/视频/Clip_01.mp4"]


def test_replace_refuses_running_without_force(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=600)
    planned = queue.make_queue(
        str(tmp_path),
        [],
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget([], None, None),
    )

    try:
        queue.write_planned_queue(str(tmp_path), planned, replace=True)
        assert False, "replace should refuse to clobber running work"
    except RuntimeError:
        pass

    replaced = queue.write_planned_queue(str(tmp_path), planned, replace=True, force=True)
    assert replaced["tasks"] == []


# ── T4: 回流闭环后半环（指纹 + resolved 回写 + 复检）──────────────────────────
q = queue
from n2d_contract import finding_fingerprint


def _findings_report(ep="第1集"):
    return {
        "kind": q.CONSISTENCY_FINDINGS_KIND, "episode": ep,
        "findings": [
            {"severity": "block", "dimension": "character_consistency",
             "return_to_stage": "image", "affected_shots": ["Clip_03"], "msg": "崩脸"},
        ],
    }


def test_consistency_tasks_carry_matching_fingerprint(tmp_path):
    rep = _findings_report()
    tasks = q.tasks_from_consistency_findings(str(tmp_path), rep, cost_estimates={}, max_retries=1)
    assert len(tasks) == 1
    fp = finding_fingerprint("第1集", "image", "character_consistency", "Clip_03")
    assert tasks[0]["finding_fingerprints"] == [fp]
    # task 端指纹 == audit 端重算的现存指纹（可对账）
    assert fp in q.report_active_fingerprints(rep)


def test_merge_reopens_recurring_done_task_no_stack(tmp_path):
    fp = finding_fingerprint("第1集", "image", "character_consistency")
    existing = {"tasks": [{"id": "001-image-rerun", "status": "done", "attempts": 1,
                           "finding_fingerprints": [fp], "history": []}]}
    planned = {"tasks": [{"id": "001-image-rerun", "status": "queued", "attempts": 0,
                          "finding_fingerprints": [fp], "rerun_scope": "重出崩脸", "history": []}]}
    merged = q.merge_queues(existing, planned)
    assert len(merged["tasks"]) == 1                      # 不堆叠
    t = merged["tasks"][0]
    assert t["status"] == "queued" and t["resolved"] is False
    assert any(h["action"] == "plan:reopen_recurring" for h in t["history"])


def test_merge_skips_in_flight_duplicate(tmp_path):
    fp = finding_fingerprint("第1集", "image", "character_consistency")
    existing = {"tasks": [{"id": "001-image-rerun", "status": "running", "attempts": 1,
                           "finding_fingerprints": [fp], "history": []}]}
    planned = {"tasks": [{"id": "001-image-rerun-x", "status": "queued", "attempts": 0,
                          "finding_fingerprints": [fp], "history": []}]}
    merged = q.merge_queues(existing, planned)
    assert len(merged["tasks"]) == 1                      # 在途同问题不重复入队
    assert merged["tasks"][0]["status"] == "running"


def test_reconcile_resolved_marks_and_reopens():
    fp_gone = finding_fingerprint("第1集", "image", "character_consistency")
    fp_still = finding_fingerprint("第2集", "image", "scene_consistency")
    queue = {"tasks": [
        {"id": "a", "status": "done", "finding_fingerprints": [fp_gone], "history": []},
        {"id": "b", "status": "done", "finding_fingerprints": [fp_still], "history": []},
        {"id": "c", "status": "queued", "finding_fingerprints": [fp_still], "history": []},  # 非 done 不碰
    ]}
    q.reconcile_resolved(queue, active_fingerprints={fp_still})
    a, b, c = queue["tasks"]
    assert a["resolved"] is True and a["status"] == "done"          # 问题消失 → resolved
    assert b["status"] == "queued" and b["resolved"] is False        # 仍在 → reopen
    assert c["status"] == "queued"                                   # queued 不动
    assert queue["recheck"] == {"resolved": 1, "reopened": 1, "reopened_coarse": 0, "at": queue["recheck"]["at"]}


def test_fingerprint_stable_across_shot_locator_granularity():
    """#2 根因修复：同一镜头换写法/帧位/产物路径 → 同一精确指纹，复检不再误判 resolved。"""
    base = finding_fingerprint("第1集", "image", "character_consistency", "Clip_03")
    for variant in ("Clip 3", "clip_03", "Clip_03_首帧", "Clip_03_尾帧", "镜头3",
                    "出图/第1集/图片/Clip_03.png"):
        assert finding_fingerprint("第1集", "image", "character_consistency", variant) == base
    # 不同镜头仍区分
    assert finding_fingerprint("第1集", "image", "character_consistency", "Clip_04") != base


def test_recheck_granularity_drift_no_false_resolved():
    """返工前 finding 定位 Clip_03、返工后审查写成 Clip_03_首帧：精确指纹归一后仍判 reopen。"""
    task_fp = finding_fingerprint("第2集", "image", "character_consistency", "Clip_03")
    active = {finding_fingerprint("第2集", "image", "character_consistency", "Clip_03_首帧")}
    queue = {"tasks": [{"id": "a", "status": "done", "finding_fingerprints": [task_fp], "history": []}]}
    q.reconcile_resolved(queue, active)
    assert queue["tasks"][0]["status"] == "queued"  # 没被误判 resolved


def test_recheck_coarse_fallback_reopens_when_bucket_still_dirty():
    """#2 安全网：精确指纹对不上，但 (集×阶段×维度) 桶仍有问题 → --coarse 下 reopen，不漏放。"""
    task_fp = finding_fingerprint("第3集", "image", "outfit_consistency", "无镜头号自由文本A")
    coarse_fp = finding_fingerprint("第3集", "image", "outfit_consistency")
    # 桶里现在是另一条无法归一到同精确指纹的描述，但同 (集,阶段,维度)
    active_fine = {finding_fingerprint("第3集", "image", "outfit_consistency", "另一段自由文本B")}
    active_coarse = {coarse_fp}
    queue = {"tasks": [{"id": "a", "status": "done",
                        "finding_fingerprints": [task_fp],
                        "coarse_fingerprints": [coarse_fp], "history": []}]}
    # 不开 coarse：精确对不上 → 误判 resolved（说明回退的必要性）
    q.reconcile_resolved({"tasks": [dict(queue["tasks"][0])]}, active_fine)
    # 开 coarse：桶仍脏 → reopen
    q.reconcile_resolved(queue, active_fine, coarse_active=active_coarse)
    assert queue["tasks"][0]["status"] == "queued"
    assert queue["recheck"]["reopened_coarse"] == 1
    assert queue["recheck"]["reopened"] == 0


def test_recheck_coarse_fallback_resolves_when_bucket_clean():
    """精确指纹消失且桶也干净 → 即便开 coarse 也判 resolved，能收敛。"""
    task_fp = finding_fingerprint("第3集", "image", "outfit_consistency", "Clip_07")
    coarse_fp = finding_fingerprint("第3集", "image", "outfit_consistency")
    queue = {"tasks": [{"id": "a", "status": "done",
                        "finding_fingerprints": [task_fp],
                        "coarse_fingerprints": [coarse_fp], "history": []}]}
    q.reconcile_resolved(queue, set(), coarse_active=set())
    assert queue["tasks"][0]["resolved"] is True
    assert queue["recheck"]["reopened_coarse"] == 0


def test_consistency_task_carries_coarse_fingerprints(tmp_path):
    rep = {"kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
           "auto_return_tasks": [{
               "return_to_stage": "image",
               "dimensions": ["character_consistency"],
               "affected_shots": ["Clip_03"],
           }]}
    tasks = q.tasks_from_consistency_findings(str(tmp_path), rep, cost_estimates={}, max_retries=1)
    assert tasks[0]["coarse_fingerprints"] == [
        finding_fingerprint("第1集", "image", "character_consistency")
    ]


def test_collect_active_fingerprints_from_disk(tmp_path):
    pdir = tmp_path / "生产数据"
    pdir.mkdir()
    (pdir / "consistency_findings_第1集.json").write_text(
        json.dumps(_findings_report()), encoding="utf-8")
    fps = q.collect_active_fingerprints(str(tmp_path))
    assert finding_fingerprint("第1集", "image", "character_consistency", "Clip_03") in fps


def test_consistency_ledger_root_causes_become_minimal_tasks(tmp_path):
    ledger = {
        "kind": q.CONSISTENCY_LEDGER_KIND,
        "episode": "第1集",
        "root_causes": [
            {
                "anchor": "CHAR_01",
                "severity": "block",
                "dimensions": ["character_consistency"],
                "suggested_return_to_stage": "image",
                "symptoms": [
                    {
                        "sev": "block",
                        "dim_key": "character_consistency",
                        "loc": "出图/第1集/图片/Clip_03.png",
                        "text": "CHAR_01 首帧脸漂",
                    },
                    {
                        "sev": "high",
                        "dim_key": "character_consistency",
                        "loc": "出视频/第1集/视频/Clip_03.mp4",
                        "text": "视频中像另一个人",
                    },
                ],
            },
            {
                "anchor": "PROP_01",
                "severity": "warn",
                "dimensions": ["multimodal_continuity"],
                "symptoms": [{"loc": "Clip_04", "text": "道具疑似变形"}],
            },
        ],
    }

    tasks = q.tasks_from_consistency_ledger(str(tmp_path), ledger, cost_estimates={}, max_retries=1)

    assert len(tasks) == 1
    task = tasks[0]
    assert task["stage_key"] == "image"
    assert task["affected_shots"] == ["Clip_03"]
    assert "--shots Clip_03" in task["command"]
    assert "根因锚点：CHAR_01" in task["rerun_scope"]
    assert finding_fingerprint("第1集", "image", "character_consistency", "Clip_03") in task["finding_fingerprints"]


def test_collect_active_fingerprints_includes_consistency_ledger(tmp_path):
    pdir = tmp_path / "生产数据"
    pdir.mkdir()
    (pdir / "consistency_ledger_第1集.json").write_text(
        json.dumps(
            {
                "kind": q.CONSISTENCY_LEDGER_KIND,
                "episode": "第1集",
                "root_causes": [
                    {
                        "anchor": "CHAR_02",
                        "severity": "high",
                        "dimensions": ["character_consistency"],
                        "return_to_stage": "image",
                        "affected_shots": ["Clip_05"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    fps = q.collect_active_fingerprints(str(tmp_path))
    assert finding_fingerprint("第1集", "image", "character_consistency", "Clip_05") in fps


def test_consistency_fingerprints_are_scoped_per_affected_shot(tmp_path):
    rep = {"kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
           "auto_return_tasks": [{
               "return_to_stage": "image",
               "dimensions": ["character_consistency"],
               "affected_shots": ["Clip_03", "Clip_05"],
               "scope": "两镜崩脸",
           }]}
    tasks = q.tasks_from_consistency_findings(str(tmp_path), rep, cost_estimates={}, max_retries=1)
    assert sorted(tasks[0]["finding_fingerprints"]) == sorted([
        finding_fingerprint("第1集", "image", "character_consistency", "Clip_03"),
        finding_fingerprint("第1集", "image", "character_consistency", "Clip_05"),
    ])

    active = q.report_active_fingerprints({
        "kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
        "auto_return_tasks": [{
            "return_to_stage": "image",
            "dimensions": ["character_consistency"],
            "affected_shots": ["Clip_05"],
        }],
    })
    queue_obj = {"tasks": [{"id": "a", "status": "done",
                            "finding_fingerprints": tasks[0]["finding_fingerprints"], "history": []}]}
    q.reconcile_resolved(queue_obj, active)
    assert queue_obj["tasks"][0]["status"] == "queued"


# ── T11: 最小范围返工命令注入 --shots ────────────────────────────────────────
def test_task_command_injects_affected_shots():
    rep = {"kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
           "findings": [{"severity": "block", "dimension": "character_consistency",
                         "return_to_stage": "image", "affected_shots": ["Clip_03", "Clip_05"], "msg": "崩脸"}]}
    tasks = q.tasks_from_consistency_findings(str("/x"), rep, cost_estimates={}, max_retries=1)
    assert tasks and "--shots Clip_03,Clip_05" in tasks[0]["command"]


def test_task_command_no_shots_suffix_when_none():
    rep = {"kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
           "findings": [{"severity": "block", "dimension": "style_consistency",
                         "return_to_stage": "image", "msg": "风格漂"}]}
    tasks = q.tasks_from_consistency_findings(str("/x"), rep, cost_estimates={}, max_retries=1)
    assert tasks and "--shots" not in tasks[0]["command"]


# --- F3: 多机锁策略（atomic O_EXCL + 陈旧锁接管·2026-06-26）---

def test_queue_lock_mode_selection(monkeypatch):
    monkeypatch.setenv("N2D_QUEUE_LOCK", "atomic")
    assert queue._queue_lock_mode() == "atomic"
    monkeypatch.setenv("N2D_QUEUE_LOCK", "flock")
    # flock 模式：有 fcntl 时为 flock，否则降 atomic
    assert queue._queue_lock_mode() in {"flock", "atomic"}
    monkeypatch.setenv("N2D_QUEUE_LOCK", "garbage")
    assert queue._queue_lock_mode() in {"flock", "atomic"}  # 非法→auto


def test_atomic_lock_mutual_exclusion(tmp_path, monkeypatch):
    monkeypatch.setenv("N2D_QUEUE_LOCK", "atomic")
    root = str(tmp_path)
    import contextlib
    with queue.queue_lock(root, timeout=1.0):
        # 持锁期间再取（短超时）→ TimeoutError（互斥）
        with contextlib.suppress(Exception):
            import pytest as _pt
        try:
            with queue.queue_lock(root, timeout=0.3, poll=0.05):
                assert False, "应互斥，不该拿到第二把锁"
        except TimeoutError:
            pass
    # 释放后可再取
    with queue.queue_lock(root, timeout=1.0):
        pass


def test_atomic_lock_breaks_stale_lock(tmp_path, monkeypatch):
    import os, time
    monkeypatch.setenv("N2D_QUEUE_LOCK", "atomic")
    monkeypatch.setattr(queue, "QUEUE_LOCK_TTL", 0.2)  # 0.2s 即陈旧（spec-loaded 模块不能 reload，直接 setattr）
    root = str(tmp_path)
    os.makedirs(queue.production_dir(root), exist_ok=True)
    # 造一把陈旧锁（持锁机器假装已死·mtime 很旧）
    lp = queue.lock_path(root)
    open(lp, "w").write("deadhost:9999:0")
    old = time.time() - 100
    os.utime(lp, (old, old))
    # 应能接管陈旧锁，不死锁
    with queue.queue_lock(root, timeout=2.0, poll=0.05):
        pass


def test_atomic_lock_protects_queue_rmw(tmp_path, monkeypatch):
    # atomic 模式下完整 route→make_queue→claim 链路正常（认领不丢/不重复·互斥有效）
    monkeypatch.setenv("N2D_QUEUE_LOCK", "atomic")
    write_progress(tmp_path)
    root = str(tmp_path)
    tasks = queue.route_tasks(root, episodes=None, stage_filters={"image"},
                              cost_estimates=queue.load_cost_estimates(root), max_retries=1)
    budget = queue.apply_budget(tasks, 9999.0, "work_units")
    planned = queue.make_queue(root, tasks, max_concurrency=2, max_retries=1, budget=budget)
    queue.save_queue(root, planned)
    claimed = queue.claim(root, limit=5, worker="m1:1")
    assert len(claimed) >= 1
    # 已认领的任务不会被第二个 worker 重复认领（atomic 锁互斥有效）
    again = queue.claim(root, limit=5, worker="m2:2")
    assert not (set(t["id"] for t in claimed) & set(t["id"] for t in again))


def test_job_receipt_reconcile_marks_external_success(tmp_path: Path) -> None:
    write_progress(tmp_path)
    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("1"),
        stage_filters={"voice"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )
    ledger = queue.make_queue(
        str(tmp_path),
        tasks,
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget(tasks, None, None),
    )
    queue.save_queue(str(tmp_path), ledger)
    task = ledger["tasks"][0]
    queue.append_job_receipt(str(tmp_path), {
        "task_id": task["id"],
        "idempotency_key": task["idempotency_key"],
        "external_job_id": "job-1",
        "status": "success",
    })

    dry = queue.reconcile_jobs(str(tmp_path), apply=False)
    assert dry["summary"]["proposed_pass"] == 0
    assert dry["summary"]["proposed_qa_blocked"] == 1
    assert queue.load_queue(str(tmp_path))["tasks"][0]["status"] == "queued"

    applied = queue.reconcile_jobs(str(tmp_path), apply=True)
    assert applied["summary"]["proposed_qa_blocked"] == 1
    assert queue.load_queue(str(tmp_path))["tasks"][0]["status"] == "qa_blocked"


# ── P2-1: 协调后端 adapter 接口 + 注册表 ─────────────────────────────────────
class _FakeBackend:
    """内存假后端，实现 CoordinationBackend 协议的 6 个方法，用于验证注册表分发。"""
    instances = []

    def __init__(self, root):
        self.root = root
        self.calls = []
        _FakeBackend.instances.append(self)

    def load_queue(self):
        self.calls.append("load_queue")
        return {"kind": "n2d_batch_queue", "tasks": [], "_via": "fake"}

    def sync_from_queue(self, q):
        self.calls.append("sync_from_queue")

    def claim(self, *, limit, worker, lease_seconds):
        self.calls.append("claim")
        return [{"id": "fake-1", "_via": "fake"}]

    def mark(self, task_id_value, status, note="", **kwargs):
        self.calls.append("mark")
        return {"id": task_id_value, "status": status, "_via": "fake"}

    def reclaim(self, *, worker=None, force_worker=False):
        self.calls.append("reclaim")
        return []

    def renew(self, task_ids, lease_seconds, worker=None):
        self.calls.append("renew")
        return 0


def _register_fake(monkeypatch, name="redis"):
    _FakeBackend.instances = []
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", name)
    queue.register_coordination_backend(name, _FakeBackend)
    monkeypatch.setattr(queue, "_COORDINATION_FACTORIES",
                        dict(queue._COORDINATION_FACTORIES), raising=False)
    # 上面的 copy 让 monkeypatch 结束后自动还原全局注册表，避免污染其它测试
    queue._COORDINATION_FACTORIES[name] = _FakeBackend


def test_protocol_isinstance_structural():
    fake = _FakeBackend("/x")
    assert isinstance(fake, queue.CoordinationBackend)
    assert not isinstance(object(), queue.CoordinationBackend)


def test_registered_external_backend_reports_active(tmp_path, monkeypatch):
    _register_fake(monkeypatch, "redis")
    status = queue.coordination_backend_status(str(tmp_path))
    assert status["backend"] == "redis"
    assert status["status"] == "ok"
    assert status["external_adapter"] is True


def test_unregistered_external_backend_reports_declared_not_active(tmp_path, monkeypatch):
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "object_store")
    # 没注册工厂 → 仍是死路声明，状态如实报 declared_not_active
    status = queue.coordination_backend_status(str(tmp_path))
    assert status["backend"] == "object_store"
    assert status["status"] == "declared_not_active"


def test_claim_mark_dispatch_through_registered_backend(tmp_path, monkeypatch):
    _register_fake(monkeypatch, "redis")
    claimed = queue.claim(str(tmp_path))
    assert claimed == [{"id": "fake-1", "_via": "fake"}]
    marked = queue.mark(str(tmp_path), "fake-1", "done")
    assert marked["_via"] == "fake" and marked["status"] == "done"
    # 确实走了假后端而非文件锁
    assert "claim" in _FakeBackend.instances[0].calls


def test_active_backend_none_for_file_modes(tmp_path, monkeypatch):
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "local_file")
    assert queue.active_coordination_backend(str(tmp_path)) is None
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "shared_fs")
    assert queue.active_coordination_backend(str(tmp_path)) is None


def test_sqlite_still_registered_by_default():
    assert "sqlite" in queue._COORDINATION_FACTORIES
    assert queue._COORDINATION_FACTORIES["sqlite"] is queue.SQLiteQueueBackend


def test_sqlite_status_warns_on_network_fs_and_documents_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("N2D_COORDINATION_BACKEND", "sqlite")
    st = queue.coordination_backend_status(str(tmp_path))
    # 本地盘 → ok，但 note 必须指明单机参考实现 + 多机走 redis/db
    assert st["backend"] == "sqlite"
    assert "redis/db" in st["note"]
    # 模拟 DB 落在网络 FS → warn
    monkeypatch.setattr(queue, "_network_fs_type", lambda p: "nfs4")
    st2 = queue.coordination_backend_status(str(tmp_path))
    assert st2["status"] == "warn" and st2["network_fs"] == "nfs4"
    assert "静默损坏" in st2["note"]


def test_network_fs_type_local_path_returns_empty(tmp_path):
    assert queue._network_fs_type(str(tmp_path)) == ""


# ── plan --from-events：未被后续 pass 承接的 generation fail 自动进重试队列（G10）──────


def _write_events(root: Path, records) -> None:
    d = root / "生产数据"
    d.mkdir(parents=True, exist_ok=True)
    (d / "production_events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )


def _gen_event(ep: str, asset: str, status: str, ts: str, stage: str = "image"):
    return {
        "kind": "n2d_production_event",
        "event": "generation",
        "episode": ep,
        "stage": stage,
        "ts": ts,
        "generation": {"asset": asset, "status": status, "provider": "dreamina_official_cli"},
    }


def test_tasks_from_events_picks_unrecovered_fail(tmp_path: Path) -> None:
    _write_events(tmp_path, [
        _gen_event("第1集", "出图/第1集/图片/Clip04_first.png", "fail", "2026-07-20T10:00:00Z"),
        _gen_event("第1集", "出图/第1集/图片/Clip05_first.png", "fail", "2026-07-20T10:01:00Z"),
        _gen_event("第1集", "出图/第1集/图片/Clip05_first.png", "pass", "2026-07-20T10:02:00Z"),
    ])
    tasks = queue.tasks_from_production_events(
        str(tmp_path), cost_estimates={}, max_retries=1)

    assert len(tasks) == 1, "后续 pass 已承接的资产不该再入队"
    task = tasks[0]
    assert task["stage_key"] == "image"
    assert task["reason"] == "generation_fail_retry"
    assert task["affected_artifacts"] == ["出图/第1集/图片/Clip04_first.png"]


def test_tasks_from_events_idempotent_across_replans(tmp_path: Path) -> None:
    _write_events(tmp_path, [
        _gen_event("第1集", "出图/第1集/图片/Clip04_first.png", "fail", "2026-07-20T10:00:00Z"),
    ])
    first = queue.tasks_from_production_events(str(tmp_path), cost_estimates={}, max_retries=1)
    second = queue.tasks_from_production_events(str(tmp_path), cost_estimates={}, max_retries=1)
    assert first[0]["idempotency_key"] == second[0]["idempotency_key"]

    # 新一次失败（新 ts）→ 新幂等键，允许再次排队
    _write_events(tmp_path, [
        _gen_event("第1集", "出图/第1集/图片/Clip04_first.png", "fail", "2026-07-21T09:00:00Z"),
    ])
    third = queue.tasks_from_production_events(str(tmp_path), cost_estimates={}, max_retries=1)
    assert third[0]["idempotency_key"] != first[0]["idempotency_key"]


def test_tasks_from_events_missing_file_returns_empty(tmp_path: Path) -> None:
    assert queue.tasks_from_production_events(str(tmp_path), cost_estimates={}, max_retries=1) == []
