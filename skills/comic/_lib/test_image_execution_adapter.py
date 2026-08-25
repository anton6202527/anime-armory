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
