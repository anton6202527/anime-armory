from __future__ import annotations

import json
from pathlib import Path

import video_execution_adapter as vea


def _registry(root: Path, command: str = "seedance-wrapper") -> None:
    path = root / "生产数据" / "video_execution_adapters.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": vea.REGISTRY_KIND,
        "version": 2,
        "adapters": {
            "seedance": {
                "adapter_id": "seedance_direct_v2",
                "execution_backend": "seedance",
                "provider": "seedance-api",
                "command": [command],
                "operations": [
                    "submit", "query", "cancel",
                    "multishot_submit", "multishot_query", "multishot_cancel",
                ],
                "capabilities": {"idempotency": "provider", "multishot": True},
                "result_contract": {
                    "submit_id": "task.id",
                    "status": "task.status",
                    "output_path": "task.output",
                    "error": "task.error",
                },
            },
        },
    }, ensure_ascii=False), encoding="utf-8")


def test_unregistered_route_is_not_claimed_automated(tmp_path: Path) -> None:
    status = vea.execution_status(tmp_path, "Veo 3.1", "Google Gemini API", which=lambda _: None)

    assert status["state"] == "unregistered"
    assert status["automated"] is False
    assert status["route_executable"] is False


def test_project_wrapper_is_ready_only_when_command_exists(tmp_path: Path) -> None:
    _registry(tmp_path)

    missing = vea.execution_status(tmp_path, "Seedance 2.0", "", which=lambda _: None)
    ready = vea.execution_status(tmp_path, "Seedance 2.0", "", which=lambda _: "/opt/n2d/seedance-wrapper")

    assert missing["state"] == "registered_missing_command"
    assert ready["state"] == "automated_ready"
    assert ready["supports_cancel"] is True
    assert ready["supports_multishot"] is True


def test_multishot_only_wrapper_can_be_ready_for_multishot_operation_set(tmp_path: Path) -> None:
    _registry(tmp_path)
    path = tmp_path / "生产数据" / "video_execution_adapters.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["adapters"]["seedance"]["operations"] = ["multishot_submit", "multishot_query"]
    path.write_text(json.dumps(data), encoding="utf-8")

    standard = vea.execution_status(tmp_path, "seedance", which=lambda _: "/bin/wrapper")
    multishot = vea.execution_status(
        tmp_path, "seedance", which=lambda _: "/bin/wrapper",
        required_operations=("multishot_submit", "multishot_query"),
    )

    assert standard["state"] == "registered_incomplete"
    assert multishot["state"] == "automated_ready"


def test_standard_request_is_idempotent_and_wrapper_uses_request_file(tmp_path: Path) -> None:
    _registry(tmp_path, command="seedance-wrapper")
    adapter = vea.adapter_for(tmp_path, "seedance")
    assert adapter is not None
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("主动作：抬眼。镜头：缓推。", encoding="utf-8")
    manifest = {"episode": "第1集", "model_version": "seedance-2", "channel": "direct"}
    item = {
        "clip": "Clip_01", "prompt_file": str(prompt), "image": "first.png",
        "end_image": "last.png", "submit_duration": 5, "target": "Clip_01.mp4",
    }

    req1 = vea.build_request(operation="submit", root=tmp_path, manifest=manifest, item=item, adapter=adapter)
    req2 = vea.build_request(operation="submit", root=tmp_path, manifest=manifest, item=item, adapter=adapter)
    path = vea.write_request(tmp_path, "第1集", req1)

    assert req1["idempotency_key"] == req2["idempotency_key"]
    assert req1["inputs"]["frames"] == ["first.png", "last.png"]
    assert vea.wrapper_args(adapter, "submit", path) == ["seedance-wrapper", "submit", "--request", str(path)]


def test_result_contract_and_failure_classification(tmp_path: Path) -> None:
    _registry(tmp_path)
    adapter = vea.adapter_for(tmp_path, "seedance")
    assert adapter is not None
    result = vea.normalize_result(adapter, {
        "task": {"id": "job-1", "status": "running", "output": "/tmp/out.mp4", "error": ""},
    })

    assert result["submit_id"] == "job-1"
    assert result["output_path"] == "/tmp/out.mp4"
    assert vea.classify_failure(1, {}, "HTTP 429 rate limit")["retryable"] is True
    assert vea.classify_failure(1, {}, "401 unauthorized")["class"] == "auth"
    assert vea.classify_failure(1, {}, "unexpected disconnect after submit")["paid_state_uncertain"] is True
