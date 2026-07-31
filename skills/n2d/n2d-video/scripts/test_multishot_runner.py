from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("multishot_runner.py")
spec = importlib.util.spec_from_file_location("multishot_runner", SCRIPT)
multishot_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(multishot_runner)


def _prompt_block(number: int, duration: float) -> str:
    return f"""
## Clip {number:02d}（时长 {duration}s · EP01_CLIP{number:02d}）

**首帧**：`出图/第1集/图片/Clip_{number:02d}.png`

### 视频 prompt（中文，目标=Seedance）
```text
主动作：角色完成第 {number} 个连续动作。镜头：沿同一轴线缓慢跟随。
```
"""


def _project(tmp_path: Path) -> Path:
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(
        "# clips\n" + _prompt_block(1, 2.0) + _prompt_block(2, 2.5), encoding="utf-8"
    )
    (prompt_dir / "multishot_plan.json").write_text(json.dumps({
        "kind": "n2d_multishot_plan",
        "version": 2,
        "active": True,
        "model_handled_seams": ["Clip_02"],
        "groups": [{
            "group_id": "MSG_01",
            "backend": "seedance",
            "members": ["Clip_01", "Clip_02"],
            "activated": True,
        }],
    }, ensure_ascii=False), encoding="utf-8")
    wrapper = tmp_path / "seedance-wrapper"
    wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    wrapper.chmod(0o755)
    registry = tmp_path / "生产数据" / "video_execution_adapters.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "kind": "n2d_video_execution_adapter_registry",
        "version": 2,
        "adapters": {
            "seedance": {
                "adapter_id": "seedance_test_v2",
                "execution_backend": "seedance",
                "provider": "test",
                "command": [str(wrapper)],
                "operations": [
                    "submit", "query", "cancel",
                    "multishot_submit", "multishot_query", "multishot_cancel",
                ],
                "capabilities": {"multishot": True},
            }
        },
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_prepare_writes_executable_group_and_per_clip_lineage(tmp_path: Path) -> None:
    root = _project(tmp_path)

    manifest = multishot_runner.prepare(root, "第1集", "MSG_01")

    assert manifest["status"] == "prepared"
    assert manifest["execution_adapter"]["state"] == "automated_ready"
    assert manifest["submit_duration"] == 4.5
    assert [shot["clip"] for shot in manifest["shots"]] == ["Clip_01", "Clip_02"]
    assert all(Path(shot["prompt_file"]).is_file() for shot in manifest["shots"])
    assert all(len(shot["prompt_sha256"]) == 64 for shot in manifest["shots"])
    group_prompt = Path(manifest["prompt_file"]).read_text(encoding="utf-8")
    assert "SHOT 1 [Clip_01 | 2.000s]" in group_prompt
    assert "SHOT 2 [Clip_02 | 2.500s]" in group_prompt


def test_multishot_dry_run_uses_stable_v2_request(tmp_path: Path) -> None:
    root = _project(tmp_path)
    manifest = multishot_runner.prepare(root, "第1集", "MSG_01")
    path = multishot_runner.manifest_path(root, "第1集", "MSG_01")

    first = multishot_runner._invoke(root, path, manifest, "multishot_submit", dry_run=True)
    second = multishot_runner._invoke(root, path, manifest, "multishot_submit", dry_run=True)

    assert first["adapter_id"] == "seedance_test_v2"
    assert first["request_path"] == second["request_path"]
    request = json.loads(Path(first["request_path"]).read_text(encoding="utf-8"))
    assert request["operation"] == "multishot_submit"
    assert [shot["clip"] for shot in request["shots"]] == ["Clip_01", "Clip_02"]
    assert first["cmd_argv"][-2:] == ["--request", first["request_path"]]
