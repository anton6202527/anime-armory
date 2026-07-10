#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inherit_contract as ic  # noqa: E402
from mv_video_prompt_compiler import compile_prompt, render_markdown  # noqa: E402


def compiled_take(backend="Seedance 2.0"):
    payload = compile_prompt({
        "clip_id": "Clip_001",
        "backend": backend,
        "mode": "image2video",
        "primary_action": "主角向画右转身",
        "camera_motion": "中景缓推",
        "rhythm": "动作峰值对齐 0.8s downbeat",
        "end_state": "人物停稳看向画右",
        "negative_elements": ["换脸", "原生人声"],
    })
    take = {
        "prompt_source_kind": "compiled_submit_prompt",
        "submit_prompt": payload["prompt"],
        "source_contract_sha256": payload["source_contract_sha256"],
    }
    return render_markdown(payload), take


def test_compiled_prompt_passes_and_keeps_external_song_policy():
    text, take = compiled_take()
    assert ic.check_compiled_prompt(text, take, "Seedance 2.0") == []


def test_missing_compiler_blocks():
    findings = ic.check_compiled_prompt("完整合同", {}, "Seedance 2.0")
    assert any(f["code"] == "missing_compiled_submit_prompt" for f in findings)


def test_backend_or_manifest_drift_blocks():
    text, take = compiled_take("Seedance 2.0")
    take["submit_prompt"] = "drift"
    codes = {f["code"] for f in ic.check_compiled_prompt(text, take, "Runway Gen-4")}
    assert "prompt_backend_mismatch" in codes
    assert "manifest_submit_prompt_mismatch" in codes
