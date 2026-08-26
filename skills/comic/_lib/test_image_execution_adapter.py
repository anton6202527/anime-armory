import json
from pathlib import Path

from image_execution_adapter import KIND, resolve_execution_adapter


def test_unknown_backend_is_not_silently_codex(tmp_path: Path):
    result = resolve_execution_adapter(tmp_path, "Gemini Image", "custom API", repo_root=tmp_path)
    assert result["status"] == "planning_only"
    assert result["command"] == []


def test_known_and_project_registered_adapters(tmp_path: Path):
    known = resolve_execution_adapter(tmp_path, "GPT Image 2", "Codex CLI", repo_root=tmp_path)
    assert known["adapter_id"] == "codex_cli"
    registry = tmp_path / "生产数据" / "image_execution_adapters.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "kind": KIND, "adapters": [{
            "adapter_id": "gemini_wrapper", "model": "Gemini Image", "channel": "custom API",
            "command": ["./tools/gemini-wrapper"],
        }]
    }), encoding="utf-8")
    custom = resolve_execution_adapter(tmp_path, "Gemini Image", "custom API", repo_root=tmp_path)
    assert custom["status"] == "executable"
    assert custom["command"] == ["./tools/gemini-wrapper"]


def test_registry_preserves_only_explicit_feature_evidence(tmp_path: Path):
    registry = tmp_path / "生产数据" / "image_execution_adapters.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "kind": KIND, "adapters": [{
            "adapter_id": "subject_runner", "model": "Seedream Subject", "channel": "custom API",
            "command": ["./subject-runner"],
            "features": {"image_inputs": True, "persistent_subject": True, "subject_id_parameter": "--subject-id"},
            "feature_evidence": {"verified_at": "2026-08-26", "source": "subject-runner --help"},
        }]
    }), encoding="utf-8")
    result = resolve_execution_adapter(tmp_path, "Seedream Subject", "custom API", repo_root=tmp_path)
    assert result["features"]["persistent_subject"] is True
    assert result["features"]["subject_id_parameter"] == "--subject-id"
    assert result["feature_evidence"]["source"] == "subject-runner --help"
