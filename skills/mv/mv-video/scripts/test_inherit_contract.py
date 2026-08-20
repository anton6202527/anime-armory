#!/usr/bin/env python3
import hashlib
import json
import base64
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inherit_contract as ic  # noqa: E402
from mv_video_prompt_compiler import compile_prompt, render_markdown  # noqa: E402


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_inherit_contract_import_isolated_from_prior_video_imports():
    code = (
        "import importlib.util;"
        f"p={str(Path(ic.__file__))!r};"
        "s=importlib.util.spec_from_file_location('isolated_mv_inherit',p);"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "assert m.provider_evidence.EVIDENCE_SCHEMA_VERSION == 2"
    )
    proc = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr


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


def test_old_manifest_can_audit_compiler_v1_without_silent_upgrade():
    text, take = compiled_take("Seedance 2.0")
    legacy = text.replace("version=2", "version=1", 1)
    findings = ic.check_compiled_prompt(legacy, take, "Seedance 2.0", allow_legacy=True)
    assert any(f["code"] == "legacy_prompt_compiler_v1" and f["level"] == "warn" for f in findings)
    assert not any(f["code"] == "incompatible_prompt_compiler" for f in findings)


def test_report_uses_portable_root_and_keeps_legacy_manifest_auditable(tmp_path):
    report = ic.build_report(str(tmp_path))
    assert report["root_rel"] == "."
    assert "root" not in report
    assert any(
        row["code"] == "legacy_manifest_freshness_not_bound"
        for row in report["manifest_findings"]
    )


def _registered_job(root, image_rel, sha, *, receipt_schema=2, include_evidence=True):
    controls = {
        "duration_seconds": 4.0, "fps": 24, "resolution": "720p", "mode": "image2video",
        "quality_tier": "fast", "input_roles": [
            {"role": "start_frame", "path": image_rel, "sha256": sha, "use": "first_frame"},
        ], "audio": {"mv_policy": "external_song_track"}, "adaptations": [],
    }
    control_hash = ic.video_capabilities.stable_hash(controls)
    route = {"provider_id": "bytedance.dreamina", "channel_kind": "web"}
    provider_job_id = "job-1"
    submitted_at = "2026-08-20T12:00:00+08:00"
    receipt = {
        "schema_version": receipt_schema, "kind": "mv_video_submit_receipt",
        "template_only": False, "job_id": "Clip_001/take_01", "take_id": "take_01",
        "model": "Seedance 2.0", "channel": "即梦/Dreamina",
        "provider_id": "bytedance.dreamina", "provider_job_id": provider_job_id,
        "provider_status": "succeeded",
        "submitted_at": submitted_at,
        "compiled_request_controls_sha256": control_hash, "request_controls": controls,
        "submitted_refs": [{"role": "start_frame", "path": image_rel, "sha256": sha,
                            "confirmed_submitted": True}],
    }
    if include_evidence:
        evidence_rel = "出视频/provider_evidence/Clip_001_take_01.provider.png"
        evidence_path = root / evidence_rel
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(PNG_BYTES)
        evidence = {
            "schema_version": 2,
            "kind": "provider_ui_capture",
            "execution_transport": "web",
            "adapter_id": "named_ui_observation.v1",
            "route_sha256": "",
            "path": evidence_rel,
            "sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            "ui_observation": {
                "reviewer": "test web operator",
                "notes": "read completed task row and output preview in provider UI",
                "observed_at": submitted_at,
                "submitted_at": submitted_at,
                "provider_id": "bytedance.dreamina",
                "provider_job_id": provider_job_id,
                "model": "Seedance 2.0",
                "status": "succeeded",
                "capture_method": "browser_screenshot",
            },
            "selected_asset": {
                "sha256": "f" * 64,
                "bound_by": "test download operator",
                "notes": "bound exact registered output bytes to this completed UI task",
            },
        }
        receipt["provider_evidence"] = evidence
        normalized, errors = ic.provider_evidence.validate_provider_evidence(
            str(root), route, receipt, "f" * 64
        )
        assert errors == []
        receipt["provider_evidence"] = normalized
    receipt["receipt_sha256"] = ic.video_capabilities.stable_hash(receipt)
    return {
        "clip_id": "Clip_001", "video_model": "Seedance 2.0", "backend": "即梦/Dreamina",
        "provider_route": route,
        "takes": [{
            "take_id": "take_01", "video_sha256": "f" * 64, "prompt_path": "",
            "provider_route": route, "compiled_request_controls": controls,
            "compiled_request_controls_sha256": control_hash, "submit_receipt": receipt,
        }],
    }


def test_submitted_reference_changed_after_registration_blocks(tmp_path):
    """Only an attested provider ref is evidence; changing that file blocks."""
    root = tmp_path
    (root / "出图").mkdir()
    image_rel = "出图/Clip_001.png"
    (root / image_rel).write_bytes(b"new pixels")
    clip = {"clip_id": "Clip_001", "image_path": image_rel}
    findings = ic.check_clip(str(root), clip, _registered_job(root, image_rel, "0" * 64), None, {}, 4)
    assert any(f["code"] == "submitted_reference_changed" for f in findings)


def test_frame_binding_fresh_no_block(tmp_path):
    root = tmp_path
    (root / "出图").mkdir()
    image_rel = "出图/Clip_001.png"
    (root / image_rel).write_bytes(b"same pixels")
    sha = hashlib.sha256(b"same pixels").hexdigest()
    clip = {"clip_id": "Clip_001", "image_path": image_rel}
    codes = {f["code"] for f in ic.check_clip(
        str(root), clip, _registered_job(root, image_rel, sha), None, {}, 4
    )}
    assert "submitted_reference_changed" not in codes
    assert "missing_actual_submit_receipt" not in codes
    assert not any(code.startswith("provider_evidence_") for code in codes)


def test_formal_v1_receipt_is_readable_but_not_completion_evidence(tmp_path):
    root = tmp_path
    (root / "出图").mkdir()
    image_rel = "出图/Clip_001.png"
    (root / image_rel).write_bytes(b"same pixels")
    sha = hashlib.sha256(b"same pixels").hexdigest()
    job = _registered_job(root, image_rel, sha, receipt_schema=1, include_evidence=False)
    codes = {row["code"] for row in ic.check_submit_receipt(root, job["takes"][0], job)}
    assert "provider_evidence_receipt_schema_required" in codes
    assert "provider_evidence_missing" in codes


def test_provider_artifact_drift_or_rewritten_time_still_blocks(tmp_path):
    root = tmp_path
    (root / "出图").mkdir()
    image_rel = "出图/Clip_001.png"
    (root / image_rel).write_bytes(b"same pixels")
    sha = hashlib.sha256(b"same pixels").hexdigest()
    job = _registered_job(root, image_rel, sha)
    take = job["takes"][0]
    evidence_path = root / take["submit_receipt"]["provider_evidence"]["path"]
    evidence_path.write_text("{}", encoding="utf-8")
    codes = {row["code"] for row in ic.check_submit_receipt(root, take, job)}
    assert "provider_evidence_sha256_mismatch" in codes

    job = _registered_job(root, image_rel, sha)
    take = job["takes"][0]
    take["submit_receipt"]["submitted_at"] = "2026-08-20T13:00:00+08:00"
    body = dict(take["submit_receipt"])
    body.pop("receipt_sha256", None)
    take["submit_receipt"]["receipt_sha256"] = ic.video_capabilities.stable_hash(body)
    codes = {row["code"] for row in ic.check_submit_receipt(root, take, job)}
    assert "provider_evidence_submitted_at_mismatch" in codes


def test_legacy_take_without_binding_warns_not_blocks(tmp_path):
    root = tmp_path
    (root / "出图").mkdir()
    image_rel = "出图/Clip_001.png"
    (root / image_rel).write_bytes(b"pixels")
    clip = {"clip_id": "Clip_001", "image_path": image_rel}
    job = {"clip_id": "Clip_001",
           "takes": [{"take_id": "take_01", "video_sha256": "f" * 64, "prompt_path": ""}]}
    findings = ic.check_clip(str(root), clip, job, None, {})
    rows = [f for f in findings if f["code"] == "legacy_registration_has_no_submit_receipt"]
    assert rows and all(f["level"] == "warn" for f in rows)
