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


def test_frame_changed_after_registration_blocks(tmp_path):
    """已登记 take 的首帧 SHA 与当前 PNG 不一致 → block（出图→出视频像素级绑定）。"""
    root = tmp_path
    (root / "出图").mkdir()
    image_rel = "出图/Clip_001.png"
    (root / image_rel).write_bytes(b"new pixels")
    clip = {"clip_id": "Clip_001", "image_path": image_rel}
    job = {"clip_id": "Clip_001",
           "takes": [{"take_id": "take_01", "video_sha256": "f" * 64,
                      "first_frame_sha256": "0" * 64, "prompt_path": ""}]}
    findings = ic.check_clip(str(root), clip, job, None, {})
    assert any(f["code"] == "frame_changed_after_registration" for f in findings)


def test_frame_binding_fresh_no_block(tmp_path):
    import hashlib
    root = tmp_path
    (root / "出图").mkdir()
    image_rel = "出图/Clip_001.png"
    (root / image_rel).write_bytes(b"same pixels")
    sha = hashlib.sha256(b"same pixels").hexdigest()
    clip = {"clip_id": "Clip_001", "image_path": image_rel}
    job = {"clip_id": "Clip_001",
           "takes": [{"take_id": "take_01", "video_sha256": "f" * 64,
                      "first_frame_sha256": sha, "prompt_path": ""}]}
    codes = {f["code"] for f in ic.check_clip(str(root), clip, job, None, {})}
    assert "frame_changed_after_registration" not in codes
    assert "missing_frame_registration_hash" not in codes


def test_legacy_take_without_binding_warns_not_blocks(tmp_path):
    root = tmp_path
    (root / "出图").mkdir()
    image_rel = "出图/Clip_001.png"
    (root / image_rel).write_bytes(b"pixels")
    clip = {"clip_id": "Clip_001", "image_path": image_rel}
    job = {"clip_id": "Clip_001",
           "takes": [{"take_id": "take_01", "video_sha256": "f" * 64, "prompt_path": ""}]}
    findings = ic.check_clip(str(root), clip, job, None, {})
    rows = [f for f in findings if f["code"] == "missing_frame_registration_hash"]
    assert rows and all(f["level"] == "warn" for f in rows)
