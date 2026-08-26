from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).with_name("spend_probe.py")
SPEC = importlib.util.spec_from_file_location("n2d_spend_probe_tests", SCRIPT)
assert SPEC and SPEC.loader
probe_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe_mod)


def _runtime(status: str = "pass"):
    calls = {"verify": 0, "consume": 0}
    task = {
        "id": "001-image-progress",
        "idempotency_key": "current-image",
        "episode": "第1集",
        "stage_key": "image",
        "status": "queued",
        "priority": 1,
        "command": "producer",
        "reason": "progress",
        "estimated_cost": {"amount": 1, "unit": "work_units"},
        "rerun_scope": "",
        "affected_artifacts": [],
        "affected_shots": [],
        "finding_fingerprints": [],
    }

    def verify(root, auth, **request):
        calls["verify"] += 1
        return {
            "status": status,
            "issues": [] if status == "pass" else ["spend envelope input_sha256 mismatch"],
            "request": request,
            "usage": {"attempts": 0, "calls": 0, "cost": 0},
        }

    def consume(*args, **kwargs):
        calls["consume"] += 1
        raise AssertionError("read-only probe must never consume")

    fields = (
        "idempotency_key", "episode", "stage_key", "command", "runner_command",
        "reason", "estimated_cost", "rerun_scope", "affected_artifacts",
        "affected_shots", "finding_fingerprints", "producer_manifest", "physical_clips",
    )
    projection = lambda row: {key: row.get(key) for key in fields}
    digest = lambda row: "sha256:" + hashlib.sha256(
        json.dumps(projection(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    queue = SimpleNamespace(
        ACTIVE_STATUSES={"queued", "running", "provider_pending", "retry_queued", "qa_blocked"},
        normalize_episode=lambda value: value,
        load_queue=lambda root: {"tasks": [task]},
        load_cost_estimates=lambda root: {},
        route_tasks=lambda *args, **kwargs: [dict(task, status="queued", attempts=0)],
        task_plan_projection=projection,
        task_plan_digest=digest,
    )
    runtime = SimpleNamespace(
        queue_mod=queue,
        load_config=lambda root, path: {"commands": {"image": "producer"}},
        _bind_execution_context=lambda task, config: task.update({
            "_runner_execution_model": "GPT Image 2",
            "_runner_execution_channel": "Codex CLI",
        }),
        resolve_command=lambda root, task, config, override: "producer",
        bind_production_execution_context=lambda root, task, config, command: task.update({
            "_runner_producer_contract": {"kind": "exact"},
        }),
        _authorization_from_config=lambda task, config, root: {
            "version": 2,
            "envelope_id": "image-phase",
            "authorization_digest": "sha256:" + "a" * 64,
        },
        _phase_consumption_kwargs=lambda task: {
            "stage": "image",
            "model": "GPT Image 2",
            "channel": "Codex CLI",
            "input_sha256": "sha256:" + "b" * 64,
            "scope": {"episode": "第1集"},
            "consumption_id": "001-image-progress:1",
            "attempt_id": "1",
            "calls": 1,
            "cost": 1,
            "currency": "work_units",
        },
        spend_envelope_mod=SimpleNamespace(verify=verify, consume=consume),
    )
    return runtime, calls


def test_probe_rebuilds_current_binding_and_never_consumes(tmp_path: Path) -> None:
    runtime, calls = _runtime("pass")

    result = probe_mod.probe(str(tmp_path), "第1集", "image", runtime=runtime)

    assert result["status"] == "authorized"
    assert result["read_only"] is True and result["consumed"] is False
    assert result["model"] == "GPT Image 2"
    assert result["input_sha256"] == "sha256:" + "b" * 64
    assert calls == {"verify": 1, "consume": 0}


def test_probe_reports_current_binding_mismatch_as_blocked(tmp_path: Path) -> None:
    runtime, calls = _runtime("blocked")

    result = probe_mod.probe(str(tmp_path), "第1集", "image", runtime=runtime)

    assert result["status"] == "blocked"
    assert "input_sha256 mismatch" in result["verification"]["issues"][0]
    assert calls == {"verify": 1, "consume": 0}


def test_probe_uses_fresh_plan_when_active_queue_task_is_stale(tmp_path: Path) -> None:
    runtime, calls = _runtime("blocked")
    old = runtime.queue_mod.load_queue("")["tasks"][0]
    old["command"] = "producer --old-input"
    current = dict(old, command="producer --current-input")
    runtime.queue_mod.route_tasks = lambda *args, **kwargs: [current]
    selected = []

    def bind_current(root, task, config, command):
        selected.append(task["command"])
        task["_runner_producer_contract"] = {"kind": "exact-current"}

    runtime.bind_production_execution_context = bind_current

    result = probe_mod.probe(str(tmp_path), "第1集", "image", runtime=runtime)

    assert selected == ["producer --current-input"]
    assert result["status"] == "blocked"
    assert calls == {"verify": 1, "consume": 0}


def test_probe_authorizes_query_only_recovery_for_existing_submit_id(tmp_path: Path) -> None:
    runtime, calls = _runtime("blocked")
    runtime.spend_envelope_mod.verify = lambda *_a, **_k: {
        "status": "blocked",
        "issues": ["consumption_id has uncertain in_flight provider state; provider replay blocked"],
    }
    runtime.provider_recovery_checkpoint = lambda *_a, **_k: {
        "state": "provider_pending",
        "provider_submit_id": "job-123",
    }
    runtime._only_recoverable_in_flight_issues = lambda issues: all(
        "in_flight provider state" in str(issue) for issue in issues
    )

    result = probe_mod.probe(str(tmp_path), "第1集", "image", runtime=runtime)

    assert result["status"] == "authorized_recovery"
    assert result["provider_recovery"]["provider_submit_id"] == "job-123"
    assert calls["consume"] == 0


def test_probe_critical_governance_interlock_runs_before_envelope_verify(tmp_path: Path) -> None:
    runtime, calls = _runtime("pass")
    runtime.production_governance_interlock = lambda _root: {
        "status": "blocked",
        "violations": [{"level": "critical", "kind": "stop_loss"}],
    }

    result = probe_mod.probe(str(tmp_path), "第1集", "image", runtime=runtime)

    assert result["status"] == "blocked_governance"
    assert calls == {"verify": 0, "consume": 0}
