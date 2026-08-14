import importlib.util
import json
import base64
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("codex_image_runner.py")
SPEC = importlib.util.spec_from_file_location("codex_image_runner", MODULE_PATH)
codex_image_runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = codex_image_runner
SPEC.loader.exec_module(codex_image_runner)


def test_format_codex_failure_keeps_stdout_and_stderr():
    proc = subprocess.CompletedProcess(["codex"], 2, stdout="jsonl api error", stderr="stderr detail")
    msg = codex_image_runner.format_codex_failure(proc)
    assert "codex exit 2" in msg
    assert "stderr=stderr detail" in msg
    assert "stdout=jsonl api error" in msg


def test_run_codex_retries_transient_transport_failure(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if len(calls) == 1:
            return subprocess.CompletedProcess(cmd, 1, stdout='{"type":"error","message":"stream disconnected"}', stderr="tls handshake eof")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(codex_image_runner.time, "sleep", lambda _seconds: None)

    proc = codex_image_runner.run_codex(tmp_path, "prompt", 10, [])

    assert proc.returncode == 0
    assert len(calls) == 2
    assert calls[0] == calls[1]


def test_run_codex_retries_timeout_on_same_target(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(codex_image_runner.time, "sleep", lambda _seconds: None)

    proc = codex_image_runner.run_codex(tmp_path, "prompt", 10, [])

    assert proc.returncode == 0
    assert len(calls) == 2
    assert calls[0] == calls[1]


def test_run_codex_does_not_retry_non_transient_failure(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 1, stdout="content policy denied", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    proc = codex_image_runner.run_codex(tmp_path, "prompt", 10, [])

    assert proc.returncode == 1
    assert len(calls) == 1


def test_run_codex_retries_transient_failed_image_event(monkeypatch, tmp_path: Path) -> None:
    calls = []
    failed = "\n".join([
        json.dumps({"payload": {"type": "image_generation_end", "status": "failed", "result": ""}}),
        json.dumps({"payload": {"type": "agent_message", "message": "生成失败：image_gen 请求发生网络错误。"}}, ensure_ascii=False),
    ])

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if len(calls) == 1:
            return subprocess.CompletedProcess(cmd, 0, stdout=failed, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(codex_image_runner.time, "sleep", lambda _seconds: None)

    proc = codex_image_runner.run_codex(tmp_path, "prompt", 10, [])

    assert proc.returncode == 0
    assert len(calls) == 2
    assert calls[0] == calls[1]


def test_image_generation_failure_detail_keeps_non_retryable_status() -> None:
    stdout = json.dumps({
        "payload": {
            "type": "image_generation_end",
            "status": "failed",
            "result": "",
        }
    })

    detail = codex_image_runner.image_generation_failure_detail(stdout)

    assert detail == "image_generation_end status=failed"
    assert codex_image_runner.transient_codex_image_failure(detail) is False


def test_image_generation_failure_detail_reads_final_refusal_without_tool_event() -> None:
    stdout = json.dumps({
        "payload": {
            "type": "agent_message",
            "phase": "final_answer",
            "message": "失败：内置 image_gen 单次最多接收 5 张参考图，未生成文件。",
        }
    }, ensure_ascii=False)

    assert "最多接收 5 张" in codex_image_runner.image_generation_failure_detail(stdout)


def test_codex_reference_cap_balances_two_characters_and_location() -> None:
    section = codex_image_runner.ClipSection(
        "Clip_01", "## Clip_01", "动作瞬间：两人递交 PROP_01。", ""
    )
    target = codex_image_runner.Target(
        "Clip_01_first", "Clip_01", "firstframe", "out.png", section
    )
    rows = []
    sequence = 0
    for owner in ("CHAR_01/常态", "CHAR_02/常态"):
        for suffix in ("front", "expression", "side", "back"):
            rows.append({
                "role": "character",
                "owner": owner,
                "rel_path": f"{owner}_{suffix}.png",
                "priority": 30,
                "sequence": sequence,
            })
            sequence += 1
    rows.extend([
        {"role": "style", "owner": "STYLE_ANCHOR", "rel_path": "style.png", "priority": 60, "sequence": 8},
        {"role": "asset", "owner": "LOC_01", "rel_path": "location.png", "priority": 100, "sequence": 9},
        {"role": "asset", "owner": "LOC_01", "rel_path": "location_reverse.png", "priority": 100, "sequence": 10},
        {"role": "asset", "owner": "PROP_01", "rel_path": "prop.png", "priority": 100, "sequence": 11},
    ])

    selected = codex_image_runner.select_codex_reference_inputs(target, rows, 5)

    assert len(selected) == 5
    assert [row["owner"] for row in selected].count("CHAR_01/常态") == 2
    assert [row["owner"] for row in selected].count("CHAR_02/常态") == 1
    assert [row["owner"] for row in selected[-2:]] == ["LOC_01", "PROP_01"]


def test_codex_reference_cap_prefers_previous_anchor_for_midframe_relay() -> None:
    section = codex_image_runner.ClipSection(
        "Clip_05", "## Clip_05", "动作瞬间：墨线在谱页内逐步成虎。", ""
    )
    target = codex_image_runner.Target(
        "Clip_05_end_a2", "Clip_05", "midframe", "a2.png", section
    )
    rows = [
        {
            "role": "source_frame", "source": "same_clip_firstframe",
            "owner": "Clip_05", "rel_path": "first.png", "sequence": 0,
        },
        {
            "role": "source_frame", "source": "same_clip_previous_frame",
            "owner": "Clip_05", "rel_path": "a1.png", "sequence": 1,
        },
        {
            "role": "character", "owner": "CHAR_01/常态",
            "rel_path": "face.png", "priority": 30, "sequence": 2,
        },
        {
            "role": "asset", "owner": "LOC_01",
            "rel_path": "location.png", "priority": 100, "sequence": 3,
        },
        {
            "role": "asset", "owner": "VFX_百妖谱",
            "rel_path": "book.png", "priority": 100, "sequence": 4,
        },
        {
            "role": "style", "owner": "STYLE_ANCHOR",
            "rel_path": "style.png", "priority": 60, "sequence": 5,
        },
    ]

    selected = codex_image_runner.select_codex_reference_inputs(target, rows, 5)

    assert selected[0]["rel_path"] == "a1.png"
    assert all(row["rel_path"] != "first.png" for row in selected)


def test_codex_reference_cap_prefers_latest_anchor_for_tailframe_relay() -> None:
    section = codex_image_runner.ClipSection(
        "Clip_05", "## Clip_05", "动作瞬间：接续最后锚帧。", ""
    )
    target = codex_image_runner.Target(
        "Clip_05_end", "Clip_05", "tailframe", "end.png", section
    )
    rows = [
        {
            "role": "source_frame", "source": "same_clip_firstframe",
            "owner": "Clip_05", "rel_path": "first.png", "sequence": 0,
        },
        {
            "role": "source_frame", "source": "same_clip_anchor",
            "owner": "Clip_05", "rel_path": "a1.png", "sequence": 1,
        },
        {
            "role": "source_frame", "source": "same_clip_anchor",
            "owner": "Clip_05", "rel_path": "a2.png", "sequence": 2,
        },
        {
            "role": "character", "owner": "CHAR_01/常态",
            "rel_path": "face.png", "priority": 30, "sequence": 3,
        },
        {
            "role": "asset", "owner": "LOC_01",
            "rel_path": "location.png", "priority": 100, "sequence": 4,
        },
        {
            "role": "style", "owner": "STYLE_ANCHOR",
            "rel_path": "style.png", "priority": 60, "sequence": 5,
        },
    ]

    selected = codex_image_runner.select_codex_reference_inputs(target, rows, 5)

    assert selected[0]["rel_path"] == "a2.png"


def test_selected_relay_source_path_reports_actual_selected_anchor() -> None:
    rows = [
        {"role": "source_frame", "rel_path": "出图/第2集/图片/a1.png"},
        {"role": "character", "rel_path": "出图/共享/图片/face.png"},
    ]

    assert codex_image_runner.selected_relay_source_path(rows) == "出图/第2集/图片/a1.png"


def test_transient_codex_image_failure_recognizes_http_5xx_not_4xx() -> None:
    assert codex_image_runner.transient_codex_image_failure("imagegen returned HTTP 520") is True
    assert codex_image_runner.transient_codex_image_failure("imagegen returned HTTP 503") is True
    assert codex_image_runner.transient_codex_image_failure("imagegen returned HTTP 400") is False
    assert codex_image_runner.transient_codex_image_failure("内置 image_gen 网络请求失败") is True


def test_image_qc_python_prefers_configured_executable(tmp_path: Path, monkeypatch) -> None:
    fake_python = tmp_path / "python"
    fake_python.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_python.chmod(0o755)

    monkeypatch.setenv(codex_image_runner.IMAGE_QC_PYTHON_ENV, str(fake_python))

    assert codex_image_runner.image_qc_python() == str(fake_python)


def test_strict_single_image_review_reads_project_setting(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "- 图片验收模式: 逐张机器QC+实际目视\n",
        encoding="utf-8",
    )

    assert codex_image_runner.strict_single_image_review_enabled(tmp_path) is True


def test_strict_single_image_review_is_hard_floor_without_setting(tmp_path: Path) -> None:
    assert codex_image_runner.strict_single_image_review_enabled(tmp_path) is True


def test_strict_pending_review_requires_later_hash_bound_acceptance(tmp_path: Path) -> None:
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    generated = {
        "stage": "image",
        "event": "generation",
        "generation": {"asset": "出图/共享/图片/a.png", "status": "pass"},
        "meta": {"artifact_sha256": "a" * 64},
    }
    events.write_text(json.dumps(generated, ensure_ascii=False) + "\n", encoding="utf-8")

    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/共享/图片/b.png"
    ) == {"asset": "出图/共享/图片/a.png", "artifact_sha256": "a" * 64}
    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/共享/图片/a.png"
    ) is None

    accepted = {
        "stage": "image",
        "event": "qa",
        "generation": {"asset": "出图/共享/图片/a.png", "status": "accepted"},
        "meta": {"artifact_sha256": "a" * 64},
    }
    with events.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(accepted, ensure_ascii=False) + "\n")

    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/共享/图片/b.png"
    ) is None


def test_strict_pending_review_tracks_latest_successful_redraw(tmp_path: Path) -> None:
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    asset = "出图/共享/图片/a.png"
    records = [
        {
            "stage": "image",
            "event": "generation",
            "generation": {"asset": asset, "status": "pass"},
            "meta": {"artifact_sha256": "a" * 64},
        },
        {
            "stage": "image",
            "event": "qa",
            "generation": {"asset": asset, "status": "rejected"},
            "meta": {"artifact_sha256": "a" * 64},
        },
        {
            "stage": "image",
            "event": "redraw",
            "generation": {"asset": asset, "status": "pass"},
            "meta": {"artifact_sha256": "b" * 64},
        },
    ]
    events.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/共享/图片/b.png"
    ) == {"asset": asset, "artifact_sha256": "b" * 64}

    accepted = {
        "stage": "image",
        "event": "qa",
        "generation": {"asset": asset, "status": "accepted"},
        "meta": {"artifact_sha256": "b" * 64},
    }
    with events.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(accepted, ensure_ascii=False) + "\n")

    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/共享/图片/b.png"
    ) is None


def test_strict_pending_review_allows_explicitly_abandoned_optional_shared_view(
    tmp_path: Path,
) -> None:
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    asset = "出图/共享/图片/定妆_CHAR_02__常态_后45度.png"
    artifact_sha = "c" * 64
    records = [
        {
            "stage": "image",
            "event": "redraw",
            "generation": {"asset": asset, "status": "pass"},
            "meta": {"artifact_sha256": artifact_sha},
        },
        {
            "stage": "image",
            "event": "qa",
            "generation": {"asset": asset, "status": "rejected"},
            "meta": {
                "artifact_sha256": artifact_sha,
                "accepted_current_pixels": False,
                "terminal_disposition": "abandoned_optional",
            },
        },
    ]
    events.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_02",
                        "library_tier": "named_minimal",
                        "forms": [
                            {
                                "form": "常态",
                                "reference_group": {
                                    "rear_three_quarter": {
                                        "path": asset,
                                        "status": "planned",
                                        "visual_review": {
                                            "status": "rejected",
                                            "png_sha256": artifact_sha,
                                        },
                                    }
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/第1集/图片/Clip01_first.png"
    ) is None

    (tmp_path / asset).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / asset).write_bytes(b"still present")
    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/第1集/图片/Clip01_first.png"
    ) == {"asset": asset, "artifact_sha256": artifact_sha}


def test_strict_pending_review_allows_archived_stop_loss_shared_target(tmp_path: Path) -> None:
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    asset = "出图/共享/图片/定妆_道具_SPILLED_WINE_手持.png"
    artifact_sha = "d" * 64
    records = [
        {
            "stage": "image",
            "event": "redraw",
            "generation": {"asset": asset, "status": "pass"},
            "meta": {"artifact_sha256": artifact_sha},
        },
        {
            "stage": "image",
            "event": "qa",
            "generation": {"asset": asset, "status": "rejected"},
            "meta": {
                "artifact_sha256": artifact_sha,
                "accepted_current_pixels": False,
                "stop_loss": True,
            },
        },
    ]
    events.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/共享/图片/next.png"
    ) is None

    canonical = tmp_path / asset
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_bytes(b"still present")
    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/共享/图片/next.png"
    ) == {"asset": asset, "artifact_sha256": artifact_sha}


def test_strict_pending_review_stop_loss_never_skips_episode_frame(tmp_path: Path) -> None:
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    asset = "出图/第1集/图片/Clip01_first.png"
    artifact_sha = "e" * 64
    records = [
        {
            "stage": "image",
            "event": "generation",
            "generation": {"asset": asset, "status": "pass"},
            "meta": {"artifact_sha256": artifact_sha},
        },
        {
            "stage": "image",
            "event": "qa",
            "generation": {"asset": asset, "status": "rejected"},
            "meta": {
                "artifact_sha256": artifact_sha,
                "accepted_current_pixels": False,
                "stop_loss": True,
            },
        },
    ]
    events.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    assert codex_image_runner.strict_pending_image_review(
        tmp_path, "出图/共享/图片/next.png"
    ) == {"asset": asset, "artifact_sha256": artifact_sha}


def test_run_target_image_qc_uses_selected_python(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps(
            {
                "qc_environment": {"precision_level": "full"},
                "face_reference_coverage": {"missing": []},
                "checks": {},
                "lint": {"findings": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection("Clip_01", "## Clip_01", "body", "`Clip01.png`")
    target = codex_image_runner.Target(
        "Clip_01", "Clip_01", "firstframe", "出图/第1集/图片/Clip01.png", section
    )
    captured: dict[str, list[str]] = {}
    captured_env: dict[str, str] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured_env.update(kwargs.get("env") or {})
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.delenv("N2D_VLM_CMD", raising=False)
    monkeypatch.setattr(codex_image_runner, "image_qc_python", lambda: "/chosen/qc-python")
    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    assert codex_image_runner.run_target_image_qc(tmp_path, "第1集", target) is True
    assert captured["cmd"][0] == "/chosen/qc-python"
    assert captured_env["N2D_VLM_CMD"] == "off"


def test_run_target_image_qc_respects_explicit_vlm_cmd(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps(
            {
                "qc_environment": {"precision_level": "full"},
                "face_reference_coverage": {"missing": []},
                "checks": {},
                "lint": {"findings": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection("Clip_01", "## Clip_01", "body", "`Clip01.png`")
    target = codex_image_runner.Target(
        "Clip_01", "Clip_01", "firstframe", "出图/第1集/图片/Clip01.png", section
    )
    captured_env: dict[str, str] = {}

    def fake_run(cmd, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setenv("N2D_VLM_CMD", "python vlm.py --image {image} --prompt {prompt}")
    monkeypatch.setattr(codex_image_runner, "image_qc_python", lambda: "/chosen/qc-python")
    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    assert codex_image_runner.run_target_image_qc(tmp_path, "第1集", target) is True
    assert captured_env["N2D_VLM_CMD"].startswith("python vlm.py")


def _meta_from_record_cmd(cmd: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for idx, part in enumerate(cmd):
        if part == "--meta" and idx + 1 < len(cmd):
            key, _, value = cmd[idx + 1].partition("=")
            out[key] = value
    return out


def test_record_event_writes_strong_recipe_schema_meta(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "_设置.md").write_text("生图AI：Codex\n", encoding="utf-8")
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    artifact = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    write_tiny_png(artifact)
    section = codex_image_runner.ClipSection("Clip_01", "## Clip_01", "prompt body", "`Clip_01.png`")
    target = codex_image_runner.Target("Clip_01", "Clip_01", "firstframe", "出图/第1集/图片/Clip_01.png", section)
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_image_runner, "codex_backend_version", lambda: "codex 1.2.3")
    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    codex_image_runner.record_event(
        tmp_path,
        "第1集",
        target,
        status="pass",
        duration_sec=1.25,
        task_id="unit",
        seed="seed-1",
        temp_path=tmp_path / "tmp.png",
        reference_inputs=[],
    )

    meta = _meta_from_record_cmd(captured["cmd"])
    required = [
        "recipe_hash",
        "prompt_sha256",
        "reference_bundle_sha256",
        "input_fingerprint",
        "settings_sha256",
        "identity_registry_sha256",
        "asset_registry_sha256",
        "artifact_sha256",
        "adapter_version",
        "qc_version",
        "backend_version",
        "model_version",
        "seed_support",
    ]
    assert all(meta.get(key) for key in required)
    assert meta["backend_version"] == "codex 1.2.3"
    assert meta["seed_support"] == "unsupported_no_seed_api"


def test_log_unanchored_friction_writes_signal(tmp_path):
    """承载身份镜缺脸锚被 pre-spend 闸挡下时，应往作品根上报一条 n2d-image 现场摩擦信号。"""
    codex_image_runner.log_unanchored_friction(
        tmp_path, "第1集", "S03", ["CHAR_姜大人"], "Codex")
    sig = tmp_path / "生产数据" / "优化信号.jsonl"
    assert sig.is_file()
    rec = json.loads(sig.read_text(encoding="utf-8").strip().splitlines()[0])
    assert rec["kind"] == "n2d_friction_signal"
    assert rec["skill"] == "n2d-image" and rec["signal_kind"] == "defect"
    assert "CHAR_姜大人" in rec["what"] and "S03" in rec["what"]


def test_log_unanchored_friction_never_raises(tmp_path, monkeypatch):
    # work_root 为 None / 坏值也必须静默（采集绝不拖垮出图）。
    monkeypatch.chdir(tmp_path)
    codex_image_runner.log_unanchored_friction(None, "", "", [], "Codex")
    assert not (tmp_path / "None").exists()


def write_storyboard(root: Path) -> None:
    path = root / "脚本" / "第1集" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "id": "EP01_CLIP12",
                        "firstframe_png": "出图/第1集/图片/镜头12_炼化噬妖.png",
                        "continuity": {
                            "endframe_png": "出图/第1集/图片/镜头12_end.png",
                            "anchors": [
                                {"anchor_png": "出图/第1集/图片/镜头12_炼化噬妖_a1.png"},
                                {"anchor_png": "出图/第1集/图片/镜头12_炼化噬妖_a2.png"},
                            ],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_prompt(root: Path, body: str) -> None:
    path = root / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def write_valid_png(path: Path, fill: bytes = b"0") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = height = 512
    color = (fill * 3)[:3]
    raw = b"".join(b"\0" + color * width for _ in range(height))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return (
            struct.pack(">I", len(payload))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def test_image_progress_counts_shared_and_episode_targets(tmp_path: Path) -> None:
    shared_prompt = tmp_path / "出图" / "共享" / "prompt" / "风格锚.md"
    shared_prompt.parent.mkdir(parents=True)
    shared_prompt.write_text(
        "## 风格锚\n"
        "**目标存档**：`出图/共享/图片/风格锚_TEST.png`\n",
        encoding="utf-8",
    )
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png` `出图/第1集/图片/Clip01_end.png`\n",
    )
    write_valid_png(tmp_path / "出图" / "共享" / "图片" / "风格锚_TEST.png")
    write_valid_png(tmp_path / "出图" / "第1集" / "图片" / "Clip01_first.png")

    assert codex_image_runner.image_progress_counts(tmp_path, "第1集") == (2, 3)


def test_sync_image_progress_calls_progress_set(tmp_path: Path, monkeypatch) -> None:
    shared_prompt = tmp_path / "出图" / "共享" / "prompt" / "风格锚.md"
    shared_prompt.parent.mkdir(parents=True)
    shared_prompt.write_text(
        "## 风格锚\n"
        "**目标存档**：`出图/共享/图片/风格锚_TEST.png`\n",
        encoding="utf-8",
    )
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png` `出图/第1集/图片/Clip01_end.png`\n",
    )
    write_valid_png(tmp_path / "出图" / "共享" / "图片" / "风格锚_TEST.png")
    write_valid_png(tmp_path / "出图" / "第1集" / "图片" / "Clip01_first.png")
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    assert codex_image_runner.sync_image_progress(tmp_path, "第1集") == (2, 3)
    assert captured["cmd"][-3:] == ["第1集", "出图", "2/3"]
    assert captured["cmd"][1].endswith("skills/n2d/progress.py")


def test_sync_image_progress_refreshes_stale_existing_denominator(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "_进度.md").write_text(
        "| 集 | 字数 | 出图 |\n"
        "|---|---:|---|\n"
        "| 第1集 | 100 | 5/83 |\n",
        encoding="utf-8",
    )
    shared_prompt = tmp_path / "出图" / "共享" / "prompt" / "风格锚.md"
    shared_prompt.parent.mkdir(parents=True)
    shared_prompt.write_text(
        "## 风格锚\n"
        "**目标存档**：`出图/共享/图片/风格锚_TEST.png`\n",
        encoding="utf-8",
    )
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png` `出图/第1集/图片/Clip01_end.png`\n",
    )
    write_valid_png(tmp_path / "出图" / "共享" / "图片" / "风格锚_TEST.png")
    write_valid_png(tmp_path / "出图" / "第1集" / "图片" / "Clip01_first.png")
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    assert codex_image_runner.current_image_progress_total(tmp_path, "第1集") == 83
    assert codex_image_runner.sync_image_progress(tmp_path, "第1集") == (2, 3)
    assert captured["cmd"][-1] == "2/3"


def test_sync_image_progress_keeps_episode_only_denominator_when_shared_exists(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "_进度.md").write_text(
        "| 集 | 字数 | 出图 |\n"
        "|---|---:|---|\n"
        "| 第1集 | 100 | 1/2 |\n",
        encoding="utf-8",
    )
    shared_prompt = tmp_path / "出图" / "共享" / "prompt" / "风格锚.md"
    shared_prompt.parent.mkdir(parents=True)
    shared_prompt.write_text(
        "## 风格锚\n"
        "**目标存档**：`出图/共享/图片/风格锚_TEST.png`\n",
        encoding="utf-8",
    )
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png` `出图/第1集/图片/Clip01_end.png`\n",
    )
    write_valid_png(tmp_path / "出图" / "共享" / "图片" / "风格锚_TEST.png")
    write_valid_png(tmp_path / "出图" / "第1集" / "图片" / "Clip01_first.png")
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    assert codex_image_runner.sync_image_progress(tmp_path, "第1集") == (1, 2)
    assert captured["cmd"][-1] == "1/2"


def test_sync_image_progress_preserves_matching_existing_denominator(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "_进度.md").write_text(
        "| 集 | 字数 | 出图 |\n"
        "|---|---:|---|\n"
        "| 第1集 | 100 | 1/2 |\n",
        encoding="utf-8",
    )
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png` `出图/第1集/图片/Clip01_end.png`\n",
    )
    write_valid_png(tmp_path / "出图" / "第1集" / "图片" / "Clip01_first.png")
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    assert codex_image_runner.sync_image_progress(tmp_path, "第1集") == (1, 2)
    assert captured["cmd"][-1] == "1/2"


def write_tiny_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    ))


def test_prepare_reference_inputs_upscales_low_resolution_reference(tmp_path: Path) -> None:
    pytest.importorskip("PIL.Image")
    rel = "出图/共享/用户参考/CHAR_TEST_lowres.png"
    source = tmp_path / rel
    write_tiny_png(source)
    item = {
        "role": "character",
        "owner": "CHAR_TEST/常态",
        "source": "reference_bundle",
        "rel_path": rel,
        "abs_path": str(source),
        "sha256": codex_image_runner.file_sha256(source),
        "bytes": source.stat().st_size,
        "priority": 10,
        "sequence": 0,
    }

    prepared = codex_image_runner.prepare_reference_inputs(tmp_path, "第1集", [item], write=True)

    assert len(prepared) == 1
    out = prepared[0]
    quality = out["reference_quality"]
    assert quality["status"] == "enhanced"
    assert quality["enhanced"] is True
    assert quality["original_width"] == 1
    assert quality["original_height"] == 1
    assert quality["prepared_width"] == 1024
    assert quality["prepared_height"] == 1024
    assert out["prepared_rel_path"].startswith("生产数据/reference_enhanced/第1集/")
    assert Path(out["prepared_abs_path"]).is_file()
    assert out["prepared_sha256"] == codex_image_runner.file_sha256(Path(out["prepared_abs_path"]))


def test_build_codex_command_uses_prepared_reference_attachment(tmp_path: Path) -> None:
    original = tmp_path / "orig.png"
    enhanced = tmp_path / "enhanced.png"
    write_tiny_png(original)
    write_tiny_png(enhanced)
    inputs = [{
        "rel_path": "出图/共享/用户参考/orig.png",
        "abs_path": str(original),
        "prepared_rel_path": "生产数据/reference_enhanced/第1集/enhanced.png",
        "prepared_abs_path": str(enhanced),
    }]

    cmd = codex_image_runner.build_codex_command(tmp_path, "prompt", inputs)

    assert str(enhanced) in cmd
    assert str(original) not in cmd


def test_load_sections_falls_back_to_storyboard_targets(tmp_path: Path) -> None:
    write_storyboard(tmp_path)
    write_prompt(tmp_path, "## 镜头 12（EP01_CLIP12 · 炼化噬妖）\n正文，无目标行。\n")

    section = codex_image_runner.load_sections(tmp_path, "第1集")[0]

    assert "镜头12_炼化噬妖.png" in section.target_line
    assert "镜头12_炼化噬妖_a2.png" in section.target_line
    assert (
        codex_image_runner.target_for_shot("Clip_12", section, "第1集").rel_path
        == "出图/第1集/图片/镜头12_炼化噬妖.png"
    )
    assert (
        codex_image_runner.target_for_shot("Clip_12_a2", section, "第1集").rel_path
        == "出图/第1集/图片/镜头12_炼化噬妖_a2.png"
    )
    assert (
        codex_image_runner.target_for_shot("Clip_12_end", section, "第1集").rel_path
        == "出图/第1集/图片/镜头12_end.png"
    )


def test_target_for_shot_prefers_own_tail_over_relay_source_end() -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_05",
        title="relay clip",
        body="",
        target_line=(
            "`出图/第2集/图片/EP02_CLIP04_end.png` "
            "`出图/第2集/图片/EP02_CLIP04_end_a1.png` "
            "`出图/第2集/图片/Clip05_end.png`"
        ),
    )

    target = codex_image_runner.target_for_shot("Clip_05_end", section, "第2集")

    assert target.rel_path == "出图/第2集/图片/Clip05_end.png"
    assert target.mode == "tailframe"


def test_target_repair_preflight_binds_full_qc_failure_and_current_pixels(tmp_path: Path) -> None:
    target = codex_image_runner.Target(
        shot="Clip_05_end",
        clip="Clip_05",
        mode="tailframe",
        rel_path="出图/第2集/图片/Clip05_end.png",
        section=codex_image_runner.ClipSection("Clip_05", "", "", ""),
    )
    write_tiny_png(tmp_path / target.rel_path)
    report = tmp_path / "生产数据/image_qc/第2集/image_qc_第2集.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({
        "qc_environment": {"precision_level": "full"},
        "face_reference_coverage": {"missing": []},
        "checks": {
            "face": {"shots": [{"png": "图片/Clip05_end.png", "verdict": "block"}]},
            "hair": {"shots": []},
            "outfit": {"shots": []},
        },
    }), encoding="utf-8")

    assert codex_image_runner.run_target_repair_preflight(tmp_path, "第2集", target)
    receipts = list((tmp_path / "生产数据/image_preflight_receipts/第2集").glob("*.json"))
    assert len(receipts) == 1
    payload = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert payload["status"] == "passed_for_single_target_repair"
    assert payload["repair_findings"] == ["face:block"]
    assert payload["current_target_sha256"]


def test_load_sections_drops_appended_compiled_prompt(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip01.png`\n"
        "动作瞬间：两人隔桌递回木牌。\n"
        "### 后端编译提交 image prompt\n"
        "上一轮错误残留：武器入体、伤口、动作高潮。\n",
    )

    section = codex_image_runner.load_sections(tmp_path, "第1集")[0]

    assert "隔桌递回木牌" in section.body
    assert "上一轮错误残留" not in section.body


def test_nonviolent_action_does_not_trigger_cross_episode_or_weapon_guards() -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body=(
            "**剧本描述**：杂役大殿里递回木牌。\n"
            "**跨集接力源帧**：无跨集动作接力。\n"
            "动作瞬间：张老大用两指弹回木牌，贺平生承受冲击但不后退；"
            "人体完整性/解剖完整性合约：不得穿模，身体结构完整。\n"
            "禁止：刀柄附近不要出现漂浮手。\n"
        ),
        target_line="`出图/第1集/图片/Clip01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01_first",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip01.png",
        section=section,
    )

    assert codex_image_runner.source_frame_geometry_guidance(target) == ""
    assert codex_image_runner.weapon_body_contact_guidance(target) == ""
    assert "弹回木牌" in codex_image_runner.target_story_action_scope(target)


def test_explicit_prompt_target_line_wins_over_storyboard(tmp_path: Path) -> None:
    write_storyboard(tmp_path)
    write_prompt(
        tmp_path,
        "## 镜头 12（EP01_CLIP12 · 炼化噬妖）\n"
        "**目标**：`出图/第1集/图片/custom_first.png` `出图/第1集/图片/custom_end.png`\n",
    )

    section = codex_image_runner.load_sections(tmp_path, "第1集")[0]

    assert section.target_line == "`出图/第1集/图片/custom_first.png` `出图/第1集/图片/custom_end.png`"


def test_frame_count_line_can_supply_prompt_targets(tmp_path: Path) -> None:
    write_storyboard(tmp_path)
    write_prompt(
        tmp_path,
        "## 镜头 3（EP01_CLIP03 · 证据四连）\n"
        "**本镜出图张数**：3 张；首帧 `出图/第1集/图片/Clip03_first.png`；"
        "中段锚帧 `出图/第1集/图片/Clip03_mid.png`；尾帧 `出图/第1集/图片/Clip03_end.png`。\n",
    )

    section = codex_image_runner.load_sections(tmp_path, "第1集")[0]

    assert "Clip03_first.png" in section.target_line
    assert (
        codex_image_runner.target_for_shot("Clip_03_mid", section, "第1集").rel_path
        == "出图/第1集/图片/Clip03_mid.png"
    )


def test_custom_named_action_anchors_are_all_resolved_in_declared_order(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## 镜头 8（EP01_CLIP08 · 动作硬切）\n"
        "**目标落档**：`出图/第1集/图片/Clip08_first.png` "
        "`出图/第1集/图片/EP01_CLIP08_anchor01.png` "
        "`出图/第1集/图片/EP01_CLIP08_anchor_cut_0360.png` "
        "`出图/第1集/图片/EP01_CLIP08_anchor02.png` "
        "`出图/第1集/图片/Clip08_end.png`\n",
    )
    section = codex_image_runner.load_sections(tmp_path, "第1集")[0]

    targets = codex_image_runner.build_targets(tmp_path, "第1集", ["Clip_08"])

    assert [target.shot for target in targets] == [
        "Clip_08",
        "Clip_08_anchor01",
        "Clip_08_anchor_cut_0360",
        "Clip_08_anchor02",
        "Clip_08_end",
    ]
    assert [target.mode for target in targets] == [
        "firstframe", "midframe", "midframe", "midframe", "tailframe"
    ]
    assert codex_image_runner.target_for_shot(
        "Clip_08_anchor_cut_0360", section, "第1集"
    ).rel_path == "出图/第1集/图片/EP01_CLIP08_anchor_cut_0360.png"


def test_storyboard_anchor_beat_matches_custom_anchor_png(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(
        json.dumps(
            {
                "clips": [
                        {
                            "id": "EP01_CLIP08",
                            "shots": [
                                {
                                    "t": "3.6-4.2s",
                                    "desc": "姜月初误杀后骤然抬眼。",
                                    "lens": "CU",
                                    "video_prompt": "固定机位，呼吸微动。",
                                }
                            ],
                            "continuity": {
                            "anchors": [
                                {
                                    "anchor_png": "出图/第1集/图片/EP01_CLIP08_anchor_cut_0360.png",
                                    "at_sec": 3.6,
                                    "reason": "锁误杀反应硬切",
                                    "use": "edit_cut",
                                }
                            ]
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_08",
        title="## Clip_08",
        body="动作硬切。",
        target_line="`出图/第1集/图片/Clip08_first.png` `出图/第1集/图片/EP01_CLIP08_anchor_cut_0360.png`",
    )
    target = codex_image_runner.target_for_shot(
        "Clip_08_anchor_cut_0360", section, "第1集"
    )

    beat = codex_image_runner.storyboard_anchor_beat(tmp_path, "第1集", target)

    assert beat["anchor_index"] == 1
    assert beat["at_sec"] == 3.6
    assert beat["desc"] == "姜月初误杀后骤然抬眼。"


def test_covers_all_episode_targets_only_for_complete_target_set(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png` `出图/第1集/图片/Clip01_end.png`\n"
        "## Clip_02\n"
        "**目标**：`出图/第1集/图片/Clip02_first.png`\n",
    )

    partial = codex_image_runner.build_targets(tmp_path, "第1集", ["Clip_01"])
    full = codex_image_runner.build_targets(tmp_path, "第1集", ["Clip_01", "Clip_02"])

    assert codex_image_runner.covers_all_episode_targets(tmp_path, "第1集", partial) is False
    assert codex_image_runner.covers_all_episode_targets(tmp_path, "第1集", full) is True


def test_stale_episode_image_artifacts_flags_old_prompt_namespace(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## 镜头 1\n"
        "**目标**：`出图/第1集/图片/Clip01_first.png` "
        "`出图/第1集/图片/Clip01_mid.png` "
        "`出图/第1集/图片/Clip01_end.png`\n",
    )
    write_valid_png(tmp_path / "出图" / "第1集" / "图片" / "Clip01_first.png")
    write_valid_png(tmp_path / "出图" / "第1集" / "图片" / "Clip01_黑殿审问.png")

    assert codex_image_runner.stale_episode_image_artifacts(tmp_path, "第1集") == [
        "出图/第1集/图片/Clip01_黑殿审问.png"
    ]
    assert codex_image_runner.enforce_current_episode_image_namespace(tmp_path, "第1集") is False


def test_stale_episode_image_artifacts_keeps_declared_descriptive_target(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## 镜头 1\n"
        "**目标**：`出图/第1集/图片/Clip01_黑殿审问.png`\n",
    )
    write_valid_png(tmp_path / "出图" / "第1集" / "图片" / "Clip01_黑殿审问.png")

    assert codex_image_runner.stale_episode_image_artifacts(tmp_path, "第1集") == []
    assert codex_image_runner.enforce_current_episode_image_namespace(tmp_path, "第1集") is True


def test_build_targets_accepts_underscore_clip_headings_and_frame_ids(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_02（打斗锚点）\n"
        "**目标**：`出图/第1集/图片/Clip_02_first.png` "
        "`出图/第1集/图片/Clip_02_mid.png` "
        "`出图/第1集/图片/Clip_02_a1.png` "
        "`出图/第1集/图片/Clip_02_end.png`\n"
        "正文\n",
    )

    targets = codex_image_runner.build_targets(
        tmp_path,
        "第1集",
        ["Clip_02_mid", "Clip_02_a1", "Clip_02_end"],
    )

    assert [target.mode for target in targets] == ["midframe", "midframe", "tailframe"]
    assert [target.rel_path for target in targets] == [
        "出图/第1集/图片/Clip_02_mid.png",
        "出图/第1集/图片/Clip_02_a1.png",
        "出图/第1集/图片/Clip_02_end.png",
    ]


def test_build_targets_orders_same_clip_tail_after_midframes(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_02（打斗锚点）\n"
        "**目标**：`出图/第1集/图片/Clip_02_first.png` "
        "`出图/第1集/图片/Clip_02_a1.png` "
        "`出图/第1集/图片/Clip_02_a2.png` "
        "`出图/第1集/图片/Clip_02_end.png`\n"
        "正文\n",
    )

    targets = codex_image_runner.build_targets(
        tmp_path,
        "第1集",
        ["Clip_02_end", "Clip_02_a2", "Clip_02_a1"],
    )

    assert [target.rel_path for target in targets] == [
        "出图/第1集/图片/Clip_02_a1.png",
        "出图/第1集/图片/Clip_02_a2.png",
        "出图/第1集/图片/Clip_02_end.png",
    ]


def test_build_targets_expands_bare_clip_to_declared_frames(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_02（打斗锚点）\n"
        "**目标落档**：`出图/第1集/图片/Clip02_first.png` "
        "`出图/第1集/图片/Clip02_mid.png` "
        "`出图/第1集/图片/Clip02_end.png`\n"
        "正文\n",
    )

    targets = codex_image_runner.build_targets(tmp_path, "第1集", ["Clip_02"])

    assert [target.mode for target in targets] == ["firstframe", "midframe", "tailframe"]
    assert [target.rel_path for target in targets] == [
        "出图/第1集/图片/Clip02_first.png",
        "出图/第1集/图片/Clip02_mid.png",
        "出图/第1集/图片/Clip02_end.png",
    ]


def test_build_targets_accepts_explicit_first_frame_id_without_expanding(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_03（手动返工）\n"
        "**目标落档**：`出图/第1集/图片/Clip03_first.png` "
        "`出图/第1集/图片/Clip03_end.png`\n"
        "正文\n",
    )

    targets = codex_image_runner.build_targets(tmp_path, "第1集", ["Clip03_first"])

    assert [target.mode for target in targets] == ["firstframe"]
    assert [target.shot for target in targets] == ["Clip_03_first"]
    assert [target.rel_path for target in targets] == ["出图/第1集/图片/Clip03_first.png"]


def test_frame_role_note_distinguishes_multi_anchor_targets() -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_03",
        title="## Clip 03",
        body="body",
        target_line="`出图/第1集/图片/Clip_03_first.png` `出图/第1集/图片/Clip_03_mid.png` `出图/第1集/图片/Clip_03_a1.png` `出图/第1集/图片/Clip_03_end.png`",
    )
    first = codex_image_runner.Target("Clip_03", "Clip_03", "firstframe", "出图/第1集/图片/Clip_03_first.png", section)
    mid = codex_image_runner.Target("Clip_03_mid", "Clip_03", "midframe", "出图/第1集/图片/Clip_03_mid.png", section)
    action = codex_image_runner.Target("Clip_03_a1", "Clip_03", "midframe", "出图/第1集/图片/Clip_03_a1.png", section)
    end = codex_image_runner.Target("Clip_03_end", "Clip_03", "tailframe", "出图/第1集/图片/Clip_03_end.png", section)

    assert "首帧" in codex_image_runner.frame_role_note(first)
    assert "中段锚帧" in codex_image_runner.frame_role_note(mid)
    assert "动作关键锚帧 a1" in codex_image_runner.frame_role_note(action)
    assert "尾帧" in codex_image_runner.frame_role_note(end)


def test_codex_prompt_treats_user_character_references_as_face_only(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body="**目标**：`出图/第1集/图片/Clip_01.png`\n用户参考图。",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        "Clip_01",
        "Clip_01",
        "firstframe",
        "出图/第1集/图片/Clip_01.png",
        section,
    )

    prompt = codex_image_runner.build_codex_prompt(tmp_path, "第1集", target, tmp_path / "out.png", "seed-1")

    assert "用户提供的人物/主角参考图默认只作身份与身形锚" in prompt
    assert "基础身高、体型/身材比例、体态、脸型、五官比例" in prompt
    assert "不得继承参考图里的画风、照片/摄影风格、渲染风格、滤镜" in prompt
    assert "外部参考图的风格权重视为 0" in prompt
    assert "附件是真实视觉证据" in prompt
    assert "禁止把 A 的脸或身形套给 B" in prompt
    assert "禁止继承外部参考图衣装" in prompt or "不得继承参考图里的画风" in prompt
    assert "发型、服装、配饰和道具结构必须服从本项目角色定妆合同" in prompt
    assert "不得继承低清、像素化、模糊、压缩块、屏幕截图质感" in prompt
    # Internal sources and preprocessing stay in the full contract/receipt,
    # never in the text actually submitted to the image model.
    assert "_设置.md" not in prompt
    assert "registry" not in prompt
    assert "1024px" not in prompt
    assert "统一中性灰白/18%灰棚拍背景" not in prompt
    assert "同一深灰/雨窗影棚背景" not in prompt
    assert "same studio/rain-window background" not in prompt


def test_compiled_request_receipt_keeps_actual_text_params_attachment_hashes_and_history(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body="角色回头。",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        "Clip_01", "Clip_01", "firstframe", "出图/第1集/图片/Clip_01.png", section
    )
    compiled = {
        "backend": "codex",
        "compiled_request_sha256": "a" * 64,
        "negative_prompt": "文字",
        "request_params": {"aspect_ratio": "16:9"},
        "reference_inputs": [{"path": "face.png", "sha256": "b" * 64}],
    }

    receipt = codex_image_runner.write_compiled_request_receipt(
        tmp_path, "第1集", target, compiled, "actual submitted prompt"
    )
    latest = codex_image_runner.compiled_request_receipt_path(tmp_path, "第1集", target)
    data = json.loads(receipt.read_text(encoding="utf-8"))

    assert receipt.parent.name == "history" and receipt.is_file()
    assert latest.is_file()
    assert data["actual_submit_prompt"] == "actual submitted prompt"
    assert data["actual_submit_request"]["request_params"] == {"aspect_ratio": "16:9"}
    assert data["actual_submit_request"]["reference_inputs"][0]["sha256"] == "b" * 64
    assert len(data["request_params_sha256"]) == 64
    assert len(data["reference_inputs_sha256"]) == 64


def test_image_prompt_experiment_tag_requires_complete_pair(monkeypatch) -> None:
    monkeypatch.setenv("N2D_IMAGE_PROMPT_EXPERIMENT_ID", "EXP_compact")
    monkeypatch.delenv("N2D_IMAGE_PROMPT_VARIANT", raising=False)
    try:
        codex_image_runner.image_prompt_experiment_context()
    except ValueError:
        pass
    else:
        raise AssertionError("partial A/B tag must fail closed")

    monkeypatch.setenv("N2D_IMAGE_PROMPT_VARIANT", "B")
    assert codex_image_runner.image_prompt_experiment_context() == {
        "experiment_id": "EXP_compact",
        "variant": "B",
    }


def test_target_qc_retry_guidance_converts_face_block_to_force_rerun_prompt(tmp_path: Path) -> None:
    report = tmp_path / "生产数据" / "image_qc" / "第4集" / "image_qc_第4集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps(
            {
                "face_reference_coverage": {"missing": []},
                "checks": {
                    "face": {
                        "shots": [
                            {
                                "png": "图片/Clip06_mid.png",
                                "verdict": "block",
                                "score": 0.1919,
                                "floor": 0.5736,
                            }
                        ]
                    }
                },
                "lint": {"findings": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_06",
        title="## Clip_06",
        body="CHAR_05 青面郎君 狼妖从村道深处压出，姜月初回头反应。",
        target_line="`出图/第4集/图片/Clip06_mid.png`",
    )
    target = codex_image_runner.Target(
        "Clip_06_mid",
        "Clip_06",
        "midframe",
        "出图/第4集/图片/Clip06_mid.png",
        section,
    )

    guidance = codex_image_runner.target_qc_retry_guidance(tmp_path, "第4集", target)

    assert "QC 重抽纠偏" in guidance
    assert "face:block(score=0.1919,floor=0.5736)" in guidance
    assert "眼鼻嘴三角区" in guidance
    assert "对应野兽狼首结构" in guidance


def test_target_qc_retry_guidance_includes_face_warn_score(tmp_path: Path) -> None:
    report = tmp_path / "生产数据" / "image_qc" / "第4集" / "image_qc_第4集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps(
            {
                "face_reference_coverage": {
                    "missing": [
                        {
                            "png": "图片/Clip07_first.png",
                            "reason": "face_verdict_warn",
                        }
                    ]
                },
                "checks": {
                    "face": {
                        "shots": [
                            {
                                "png": "图片/Clip07_first.png",
                                "verdict": "warn",
                                "score": 0.5248,
                                "floor": 0.5736,
                            }
                        ]
                    }
                },
                "lint": {"findings": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_07",
        title="## Clip_07",
        body="青面郎君 狼妖登场，姜月初侧身对峙。",
        target_line="`出图/第4集/图片/Clip07_first.png`",
    )
    target = codex_image_runner.Target(
        "Clip_07",
        "Clip_07",
        "firstframe",
        "出图/第4集/图片/Clip07_first.png",
        section,
    )

    guidance = codex_image_runner.target_qc_retry_guidance(tmp_path, "第4集", target)

    assert "face_reference_coverage:face_verdict_warn" in guidance
    assert "face:warn(score=0.5248,floor=0.5736)" in guidance
    assert "脸部在画面中占比略增" in guidance
    assert "不要只给纯侧脸" in guidance


def test_target_qc_retry_guidance_includes_prop_shape_review(tmp_path: Path) -> None:
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps(
            {
                "face_reference_coverage": {"missing": []},
                "checks": {},
                "lint": {"findings": []},
                "prop_shape_review": {
                    "targets": [
                        {
                            "asset": "PROP_CARRYING_POLE",
                            "asset_name": "木扁担",
                            "png": "图片/Clip01_first.png",
                            "ref": "出图/共享/图片/定妆_道具_木扁担.png",
                            "must_not_have": ["现代物件", "文字水印", "结构漂移"],
                            "confirmed": False,
                        },
                        {
                            "asset": "PROP_OK",
                            "png": "图片/Clip01_first.png",
                            "confirmed": True,
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body="CHAR_01 少年在黑殿受审，旁边有木扁担。",
        target_line="`出图/第1集/图片/Clip01_first.png`",
    )
    target = codex_image_runner.Target(
        "Clip_01",
        "Clip_01",
        "firstframe",
        "出图/第1集/图片/Clip01_first.png",
        section,
    )

    guidance = codex_image_runner.target_qc_retry_guidance(tmp_path, "第1集", target)

    assert "prop_shape_review:PROP_CARRYING_POLE" in guidance
    assert "登记道具需要人工形状确认" in guidance
    assert "木扁担" in guidance
    assert "定妆_道具_木扁担.png" in guidance
    assert "PROP_OK" not in guidance


def test_target_qc_retry_guidance_consumes_hash_bound_executor_visual_rejection(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_02",
        title="## Clip_02",
        body="**剧本描述**：管事俯身下令。",
        target_line="`出图/第1集/图片/EP01_CLIP02.png`",
    )
    target = codex_image_runner.Target(
        "Clip_02_first",
        "Clip_02",
        "firstframe",
        "出图/第1集/图片/EP01_CLIP02.png",
        section,
    )
    image = tmp_path / target.rel_path
    write_valid_png(image)
    artifact_sha = codex_image_runner.optional_file_sha256(image)
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text(json.dumps({
        "event": "qa",
        "generation": {"asset": target.rel_path, "status": "rejected"},
        "qa": {"msg": "木牌消失；重抽必须保留完整旧木牌贴在少年胸前。"},
        "meta": {
            "artifact_sha256": artifact_sha,
            "review_kind": "executor_visual",
            "human_signoff": "false",
        },
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    guidance = codex_image_runner.target_qc_retry_guidance(tmp_path, "第1集", target)

    assert "executor_visual_rejection" in guidance
    assert "木牌消失" in guidance
    assert "完整旧木牌贴在少年胸前" in guidance


def test_compiled_retry_keeps_actual_pixel_rejection_ahead_of_objective_truncation(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_02",
        title="## Clip_02",
        body=(
            "**剧本描述**：" + "很长的剧情目的" * 40 + "\n"
            "**专项镜头模板**：shot_type=dialogue_shot_reverse；"
            "continuity_must=[\"左右站位不换\", \"木牌始终在少年胸前\"]；negative=[]。"
        ),
        target_line="`出图/第1集/图片/EP01_CLIP02.png`",
    )
    target = codex_image_runner.Target(
        "Clip_02_first",
        "Clip_02",
        "firstframe",
        "出图/第1集/图片/EP01_CLIP02.png",
        section,
    )

    compiled = codex_image_runner.compile_target_image_request(
        tmp_path,
        "第1集",
        target,
        [],
        retry_guidance=(
            "QC 重抽纠偏：\n"
            "- 上一次当前像素实际目视拒收原因：木牌消失；"
            "重抽必须保留完整旧木牌贴在少年胸前。"
        ),
    )

    prompt = str(compiled.get("prompt") or "")
    assert "返工硬约束（最高优先级）" in prompt
    assert "木牌消失" in prompt
    assert "完整旧木牌贴在少年胸前" in prompt
    assert "专项连续性硬约束" in prompt
    assert "木牌始终在少年胸前" in prompt


def test_clip02_first_compiler_replaces_later_state_and_complete_weapon_clauses(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_02",
        title="## 镜头 2",
        body=(
            "**剧本描述**：尸场空间一次建立。姜月初摸到囚服，压住惊惧。断刀封路，裴长青右前半跪。\n"
            "主体：姜月初·精瘦横刀站姿；虎山神·傲慢捕食者姿态。\n"
            "保持一致：WEAPON_01 完整横刀；CHAR_01: 面颊血污；CHAR_02: 被架起；CHAR_04: 带伤复生。\n"
            "**专项镜头模板**：continuity_must=[\"起：姜月初刚在尸场醒来，未持刀\", \"止：断刀封路\"]；negative=[]。"
        ),
        target_line="`出图/第1集/图片/Clip02_first.png`",
    )
    target = codex_image_runner.Target(
        "Clip_02_first", "Clip_02", "firstframe",
        "出图/第1集/图片/Clip02_first.png", section,
    )

    compiled = codex_image_runner.compile_target_image_request(
        tmp_path, "第1集", target, [], backend="dreamina",
        model="Seedream 5.0", channel="official_cli",
    )
    prompt = str(compiled.get("prompt") or "")

    assert "35mm低机位广角" in prompt
    assert "无血、空手、刚从尸堆侧躺撑起" in prompt
    assert "虎头人身巨人形态在远后景水平倒地伪死" in prompt
    assert "完整横刀尚未入画" in prompt
    assert "四足普通老虎" in prompt
    assert "CHAR_01: 面颊血污" not in prompt
    assert "CHAR_02: 被架起" not in prompt
    assert "CHAR_04: 带伤复生" not in prompt
    assert "精瘦横刀站姿" not in prompt


def test_continuity_must_rewrites_adult_minor_shoulder_contact_to_non_contact() -> None:
    body = (
        "十四岁少年与成年管事对话。\n"
        "**专项镜头模板**：continuity_must=[\"拍肩为张老大右手\", \"木牌始终在少年胸前\"]；negative=[]。"
    )

    clauses = codex_image_runner.section_continuity_must_for_model(body)

    assert "木牌始终在少年胸前" in clauses
    assert "成人右手只撑在少年身侧桌边，靠近但不接触少年身体" in clauses
    assert all("拍肩" not in item for item in clauses)


def test_continuity_must_keeps_story_contact_for_non_openai_backend() -> None:
    body = (
        "十四岁少年与成年管事对话。\n"
        "**专项镜头模板**：continuity_must=[\"拍肩为张老大右手\", \"木牌始终在少年胸前\"]；negative=[]。"
    )

    clauses = codex_image_runner.section_continuity_must_for_model(
        body,
        soften_adult_minor_contact=False,
    )

    assert clauses == ["拍肩为张老大右手", "木牌始终在少年胸前"]
    assert not any("不接触" in item for item in clauses)


def test_midframe_anchor_uses_subshot_starting_at_exact_edit_boundary(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP02",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "continuity": {"anchors": [
            {"at_sec": 4.8, "anchor_png": "出图/第1集/图片/EP01_CLIP02_a1.png"},
            {"at_sec": 6.1, "anchor_png": "出图/第1集/图片/EP01_CLIP02_a2.png"},
        ]},
        "shots": [
            {"t": "0-4.8s", "lens": "MCU", "desc": "张老大俯身下令"},
            {"t": "4.8-6.1s", "lens": "insert", "desc": "右手压在少年左肩"},
            {"t": "6.1-7.969s", "lens": "CU", "desc": "贺平生垂眼短促应下", "video_prompt": "少年仅一次轻微点头"},
        ],
    }]}, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生"}, {"id": "CHAR_02", "name": "张老大"},
    ]}, ensure_ascii=False), encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_02",
        title="## 镜头2",
        body=(
            "**目标落档**：`出图/第1集/图片/EP01_CLIP02_a2.png`\n"
            "**剧本描述**：张老大俯身下令 右手压在少年左肩 贺平生垂眼短促应下\n"
            "**专项镜头模板**：continuity_must=[\"拍肩为张老大右手\", \"木牌始终在少年胸前\"]；negative=[]。\n"
            "### 正向 prompt（中文）\n动作瞬间：张老大俯身下令 右手压在少年左肩 贺平生垂眼短促应下\n"
        ),
        target_line="`出图/第1集/图片/EP01_CLIP02_a2.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_02_a2", clip="Clip_02", mode="midframe",
        rel_path="出图/第1集/图片/EP01_CLIP02_a2.png", section=section,
    )

    beat = codex_image_runner.storyboard_anchor_beat(tmp_path, "第1集", target)
    compiled = codex_image_runner.compile_target_image_request(
        tmp_path, "第1集", target, [], backend="dreamina",
        model="Seedream 5.0", channel="official_cli",
    )
    prompt = str(compiled.get("prompt") or "")

    assert beat["desc"] == "贺平生垂眼短促应下"
    assert beat["single_reaction"] is True
    assert "少年仅一次轻微点头" in prompt
    assert "张老大及其手臂完全出画" in prompt
    assert "右手压在少年左肩" not in prompt
    assert "拍肩为张老大右手" not in prompt
    assert "中锚动作状态替换铁律" in prompt
    assert "不得同时保留旧姿态/旧位置又新增一套新姿态/新位置" in prompt
    assert "道具总数量、拓扑与归属严格不变" in prompt


def test_untimed_storyboard_subshots_map_first_and_midframe_deterministically(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP03",
        "duration": 10.8,
        "continuity": {"anchors": [{
            "at_sec": 5.4,
            "anchor_png": "出图/第1集/图片/EP01_CLIP03_a1.png",
            "source_duration": 10.8,
        }]},
        "shots": [
            {"id": "S03A", "lens": "OTS/CU 85mm", "desc": "姜月初警惕讥诮。"},
            {"id": "S03B", "lens": "OTS/MS 50mm", "desc": "裴长青报身份与条件。"},
            {"id": "S03C", "lens": "CU 85mm", "desc": "主角转为盘算。"},
        ],
    }]}, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text('{"characters": []}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_03", title="## 镜头 3", body="",
        target_line="`出图/第1集/图片/Clip03_first.png`",
    )
    first = codex_image_runner.Target(
        shot="Clip_03_first", clip="Clip_03", mode="firstframe",
        rel_path="出图/第1集/图片/Clip03_first.png", section=section,
    )
    mid = codex_image_runner.Target(
        shot="Clip_03_a1", clip="Clip_03", mode="midframe",
        rel_path="出图/第1集/图片/EP01_CLIP03_a1.png", section=section,
    )

    first_beat = codex_image_runner.storyboard_anchor_beat(tmp_path, "第1集", first)
    mid_beat = codex_image_runner.storyboard_anchor_beat(tmp_path, "第1集", mid)

    assert first_beat["desc"] == "姜月初警惕讥诮。"
    assert first_beat["lens"] == "OTS/CU 85mm"
    assert mid_beat["desc"] == "裴长青报身份与条件。"
    assert mid_beat["lens"] == "OTS/MS 50mm"


def test_firstframe_uses_first_faceless_storyboard_subshot_only(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP03",
        "character_ids": ["CHAR_01"],
        "shots": [
            {"t": "0-4.7s", "lens": "CU insert", "desc": "旧布包、一双空旧鞋和远处山门，不出现回忆人脸"},
            {"t": "4.7-11.6s", "lens": "MS", "desc": "贺平生在巨缸前握紧扁担"},
        ],
    }]}, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生"},
    ]}, ensure_ascii=False), encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_03", title="## 镜头 3",
        body=(
            "**目标落档**：`出图/第1集/图片/EP01_CLIP03.png`\n"
            "**资产身份注册层**：`CHAR_01/常态`\n"
            "**剧本描述**：旧布包和空鞋 贺平生握紧扁担\n"
            "### 正向 prompt（中文）\n动作瞬间：旧布包和空鞋 贺平生握紧扁担\n"
        ),
        target_line="`出图/第1集/图片/EP01_CLIP03.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_03_first", clip="Clip_03", mode="firstframe",
        rel_path="出图/第1集/图片/EP01_CLIP03.png", section=section,
    )

    beat = codex_image_runner.storyboard_anchor_beat(tmp_path, "第1集", target)
    compiled = codex_image_runner.compile_target_image_request(
        tmp_path, "第1集", target, [], backend="dreamina",
        model="Seedream 5.0", channel="official_cli",
    )
    prompt = str(compiled.get("prompt") or "")

    assert beat["frame_role"] == "first"
    assert beat["faceless_insert"] is True
    assert "旧布包、一双空旧鞋和远处山门" in prompt
    assert "贺平生在巨缸前握紧扁担" not in prompt
    assert "所有具名人物" in prompt


def test_storyboard_prop_and_hand_insert_is_detail_face_exempt(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP06",
        "character_ids": ["CHAR_01"],
        "continuity": {"anchors": [{
            "at_sec": 2.0,
            "anchor_png": "出图/第1集/图片/EP01_CLIP06_a1.png",
        }]},
        "shots": [
            {"t": "0-2.0s", "lens": "CU", "desc": "贺平生视线下移"},
            {"t": "2.0-4.5s", "lens": "insert·水面上方固定", "desc": "清水下的破损黑盆卡在砂石间，少年单手伸入浅水"},
        ],
    }]}, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生"},
    ]}, ensure_ascii=False), encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_06", title="## 镜头 6",
        body="**目标落档**：`出图/第1集/图片/EP01_CLIP06_a1.png`\n",
        target_line="`出图/第1集/图片/EP01_CLIP06_a1.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_06_a1", clip="Clip_06", mode="midframe",
        rel_path="出图/第1集/图片/EP01_CLIP06_a1.png", section=section,
    )

    beat = codex_image_runner.storyboard_anchor_beat(tmp_path, "第1集", target)

    assert beat["detail_insert"] is True
    assert beat["focus_ids"] == []


def test_firstframe_filters_prop_that_enters_in_later_subshot(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP06",
        "character_ids": ["CHAR_01"],
        "object_ids": ["PROP_01", "PROP_水桶", "PROP_扁担"],
        "continuity": {
            "start_state": "少年弯腰将两桶置于碎石地，扁担仍在肩后",
            "end_state": "少年双手托持破损黑盆",
        },
        "shots": [
            {"t": "0-2.0s", "lens": "CU", "desc": "少年忽然看向画左下方"},
            {"t": "2.0-4.5s", "lens": "insert", "desc": "破损黑盆卡在砂石间"},
        ],
    }]}, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生"},
    ]}, ensure_ascii=False), encoding="utf-8")
    (shared / "asset_registry.json").write_text(json.dumps({"assets": [
        {"id": "PROP_01", "name": "破损黑盆"},
        {"id": "PROP_水桶", "name": "水桶"},
        {"id": "PROP_扁担", "name": "扁担"},
    ]}, ensure_ascii=False), encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_06", title="## 镜头 6",
        body=(
            "**目标落档**：`出图/第1集/图片/EP01_CLIP06.png`\n"
            "场景：秀竹峰后山浅潭；破损黑盆；水桶；扁担。\n"
            "保持一致：裤脚溅湿、抱住破损黑盆。\n"
        ),
        target_line="`出图/第1集/图片/EP01_CLIP06.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_06_first", clip="Clip_06", mode="firstframe",
        rel_path="出图/第1集/图片/EP01_CLIP06.png", section=section,
    )

    beat = codex_image_runner.storyboard_anchor_beat(tmp_path, "第1集", target)
    compiled = codex_image_runner.compile_target_image_request(
        tmp_path, "第1集", target, [], backend="dreamina",
        model="Seedream 5.0", channel="official_cli",
    )
    prompt = str(compiled.get("prompt") or "")

    assert beat["visible_objects"] == ["水桶", "扁担"]
    assert beat["excluded_objects"] == ["破损黑盆"]
    assert "本帧当前状态硬约束：少年弯腰将两桶置于碎石地，扁担仍在肩后" in prompt
    assert "破损黑盆在本时点尚未入画" in prompt
    assert "抱住破损黑盆" not in prompt


def test_audience_only_prop_reveal_uses_character_hidden_underside(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP07",
        "character_ids": ["CHAR_01"],
        "object_ids": ["PROP_01"],
        "entity_schedule": {"knowledge_state": {
            "CHAR_01": ["仍不知盆底异常"],
            "AUDIENCE": ["第一次看见盆底青金幽光"],
        }},
        "continuity": {"anchors": [{
            "at_sec": 2.4,
            "anchor_png": "出图/第1集/图片/EP01_CLIP07_a1.png",
        }]},
        "shots": [
            {"t": "0-2.4s", "lens": "MS", "desc": "少年抱盆转身"},
            {"t": "2.4-3.9s", "lens": "ECU insert", "desc": "水滴滑过破损盆底，一缕青金幽光从细纹中亮起"},
        ],
    }]}, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生"},
    ]}, ensure_ascii=False), encoding="utf-8")
    (shared / "asset_registry.json").write_text(json.dumps({"assets": [
        {"id": "PROP_01", "name": "破损黑盆"},
    ]}, ensure_ascii=False), encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_07", title="## 镜头 7",
        body="**目标落档**：`出图/第1集/图片/EP01_CLIP07_a1.png`\n",
        target_line="`出图/第1集/图片/EP01_CLIP07_a1.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_07_a1", clip="Clip_07", mode="midframe",
        rel_path="出图/第1集/图片/EP01_CLIP07_a1.png", section=section,
    )

    beat = codex_image_runner.storyboard_anchor_beat(tmp_path, "第1集", target)
    compiled = codex_image_runner.compile_target_image_request(
        tmp_path, "第1集", target, [], backend="dreamina",
        model="Seedream 5.0", channel="official_cli",
    )
    prompt = str(compiled.get("prompt") or "")

    assert beat["audience_only_reveal"] is True
    assert "盆底外侧下表面" in prompt
    assert "观众独享信息铁律" in prompt
    assert "不得把异常画进角色可见的道具内腔/正面" in prompt


def test_firstframe_does_not_render_video_jump_cuts_as_triptych(tmp_path: Path) -> None:
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP05",
        "character_ids": ["CHAR_01"],
        "shots": [{
            "t": "0-2.5s",
            "lens": "WS·同构图跳切",
            "desc": "少年肩挑两桶侧身向画左行进，步幅变小",
            "video_prompt": "用三个清晰跳切表现时间，桶体数量、衣服和扁担不变",
        }],
    }]}, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生"},
    ]}, ensure_ascii=False), encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_05", title="## 镜头 5",
        body=(
            "**目标落档**：`出图/第1集/图片/EP01_CLIP05.png`\n"
            "**资产身份注册层**：`CHAR_01/常态`\n"
            "### 正向 prompt（中文）\n动作瞬间：劳作蒙太奇后到潭边放桶\n"
        ),
        target_line="`出图/第1集/图片/EP01_CLIP05.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_05_first", clip="Clip_05", mode="firstframe",
        rel_path="出图/第1集/图片/EP01_CLIP05.png", section=section,
    )

    compiled = codex_image_runner.compile_target_image_request(
        tmp_path, "第1集", target, [], backend="dreamina",
        model="Seedream 5.0", channel="official_cli",
    )
    prompt = str(compiled.get("prompt") or "")

    assert "少年肩挑两桶侧身向画左行进，步幅变小" in prompt
    assert "用三个清晰跳切表现时间" not in prompt
    assert "只生成一个连续相机画面" in prompt
    assert "禁止分屏、三联画、多格漫画、拼贴" in prompt


def test_codex_prompt_for_group_character_split_ref_forces_single_member(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="CHAR_PURSUER",
        title="## 大齐追兵",
        body=(
            "**目标存档**：`出图/共享/图片/定妆_CHAR_PURSUER__常态_45度.png`\n"
            "成年军士群像，群像不建立单一主角脸。"
        ),
        target_line="`出图/共享/图片/定妆_CHAR_PURSUER__常态_45度.png`",
    )
    target = codex_image_runner.Target(
        "CHAR_PURSUER::定妆_CHAR_PURSUER__常态_45度",
        "CHAR_PURSUER",
        "shared",
        "出图/共享/图片/定妆_CHAR_PURSUER__常态_45度.png",
        section,
    )
    target.aliases = {"CHAR_PURSUER/常态"}

    prompt = codex_image_runner.build_codex_prompt(tmp_path, "第1集", target, tmp_path / "out.png", "seed-1")

    assert "共享群像角色角度资产硬约束" in prompt
    assert "一名普通代表成员" in prompt
    assert "不得画成多人队列、三名军士并排" in prompt


def test_group_character_sheet_keeps_group_prompt() -> None:
    section = codex_image_runner.ClipSection(
        clip="CROWD",
        title="## 群像",
        body="多人群像 sheet，群像队伍。",
        target_line="`出图/共享/图片/定妆_CROWD_VALLEY_WORKERS__多人群像sheet.png`",
    )
    target = codex_image_runner.Target(
        "CROWD::定妆_CROWD_VALLEY_WORKERS__多人群像sheet",
        "CROWD",
        "shared",
        "出图/共享/图片/定妆_CROWD_VALLEY_WORKERS__多人群像sheet.png",
        section,
    )

    assert codex_image_runner.shared_group_member_variant_guidance(target) == ""


def test_codex_prompt_locks_source_frame_weapon_wound_geometry(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body=(
            "**目标**：`出图/第1集/图片/Clip01_first.png` "
            "`出图/第1集/图片/Clip01_mid.png`\n"
            "长刀仍插在裴长青胸口，刀柄轻颤。"
        ),
        target_line="`出图/第1集/图片/Clip01_first.png` `出图/第1集/图片/Clip01_mid.png`",
    )
    target = codex_image_runner.Target(
        "Clip_01_mid",
        "Clip_01",
        "midframe",
        "出图/第1集/图片/Clip01_mid.png",
        section,
    )

    prompt = codex_image_runner.build_codex_prompt(tmp_path, "第1集", target, tmp_path / "out.png", "seed-1")

    assert "源帧几何连续性硬锁" in prompt
    assert "同一武器/道具接触点、同一伤口位置" in prompt
    assert "源帧主体身份连续硬锁" in prompt
    assert "不是重新选角/重新换装" in prompt
    assert "同一脸型比例、同一发际线、同一发髻/发束轮廓" in prompt
    assert "同一衣领交叠方向、袖口卷边、腰带位置" in prompt
    assert "入体点硬锁" in prompt
    assert "禁止新增第二处伤口" in prompt
    assert "禁止把胸口伤改成腹部/腰部/肩部伤" in prompt


def test_codex_prompt_keeps_nonviolent_midframe_free_of_wound_boilerplate(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body=(
            "**剧本描述**：壮汉把木牌递回少年胸前，少年稳稳站住。\n"
            "动作瞬间：木牌必须入画；壮汉把木牌递回少年胸前，少年垂眼。"
        ),
        target_line="`出图/第1集/图片/Clip01_mid.png`",
    )
    target = codex_image_runner.Target(
        "Clip_01_mid",
        "Clip_01",
        "midframe",
        "出图/第1集/图片/Clip01_mid.png",
        section,
    )

    prompt = codex_image_runner.build_codex_prompt(tmp_path, "第1集", target, tmp_path / "out.png", "seed-1")

    assert "源帧几何连续性硬锁" in prompt
    assert "同一道具接触点、同一手握位置" in prompt
    assert "伤口" not in prompt
    assert "入体点" not in prompt
    assert "武器入体" not in prompt


def test_codex_prompt_locks_weapon_body_contact_even_on_firstframe(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body="长刀仍插在裴长青胸口，刀柄轻颤。",
        target_line="`出图/第1集/图片/Clip01_first.png`",
    )
    target = codex_image_runner.Target(
        "Clip_01",
        "Clip_01",
        "firstframe",
        "出图/第1集/图片/Clip01_first.png",
        section,
    )

    prompt = codex_image_runner.build_codex_prompt(tmp_path, "第1集", target, tmp_path / "out.png", "seed-1")

    assert "武器入体/接触点铁律" in prompt
    assert "只能有一个明确入体点或接触点" in prompt
    assert "本镜已指定胸口/胸前" in prompt
    assert "不得画成腹部、腰部、肩部" in prompt


def test_codex_prompt_does_not_add_source_frame_geometry_lock_to_firstframe(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body="长刀仍插在裴长青胸口。",
        target_line="`出图/第1集/图片/Clip01_first.png`",
    )
    target = codex_image_runner.Target(
        "Clip_01",
        "Clip_01",
        "firstframe",
        "出图/第1集/图片/Clip01_first.png",
        section,
    )

    prompt = codex_image_runner.build_codex_prompt(tmp_path, "第1集", target, tmp_path / "out.png", "seed-1")

    assert "源帧几何连续性硬锁" not in prompt
    assert "源帧主体身份连续硬锁" not in prompt
    assert "入体点硬锁" not in prompt
    assert "武器入体/接触点铁律" in prompt


def test_codex_prompt_requires_machine_checkable_face_for_action_character_shot(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_04",
        title="## Clip_04",
        body="`CHAR_01/囚犯初醒态` 与虎山神打斗，姜月初双手持刀错身斩击。",
        target_line="`出图/第1集/图片/Clip04_mid.png`",
    )
    target = codex_image_runner.Target(
        "Clip_04_mid",
        "Clip_04",
        "midframe",
        "出图/第1集/图片/Clip04_mid.png",
        section,
    )

    prompt = codex_image_runner.build_codex_prompt(tmp_path, "第1集", target, tmp_path / "out.png", "seed-1")

    assert "脸部机检可核验铁律" in prompt
    assert "眼鼻嘴三角区" in prompt
    assert "不得被头发/暗影/火花/刀光完全遮住" in prompt


def test_codex_prompt_locks_hand_limb_ownership_for_prop_contact(tmp_path: Path) -> None:
    section = codex_image_runner.ClipSection(
        clip="Clip_05",
        title="## Clip_05",
        body=(
            "`CHAR_01/囚犯初醒态` 姜月初跪倒，刀尖撑地，"
            "她抬起染血手指按在百妖谱金色古卷光面上。"
        ),
        target_line="`出图/第1集/图片/Clip05_end.png`",
    )
    target = codex_image_runner.Target(
        "Clip_05_end",
        "Clip_05",
        "tailframe",
        "出图/第1集/图片/Clip05_end.png",
        section,
    )

    prompt = codex_image_runner.build_codex_prompt(tmp_path, "第1集", target, tmp_path / "out.png", "seed-1")

    assert "手部/肢体归属铁律" in prompt
    assert "单个人形角色最多两条手臂两只手" in prompt
    assert "禁止额外手掌、镜像右手/镜像左手" in prompt
    assert "另一只手和武器的归属必须明确" in prompt


def test_shared_variant_note_specializes_spatial_map_and_scale_refs() -> None:
    spatial = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_LOC_YIZHOU_RUINED_HALL_布局图.png"
    )
    scale = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_WEAPON_LI_QIANYUAN_GREEN_SPEAR_握持比例.png"
    )
    prop_scale = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_道具_尸场物资包_比例.png"
    )
    prop_in_hand = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_道具_尸场物资包_手持.png"
    )
    active = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_WEAPON_LI_QIANYUAN_GREEN_SPEAR_青烟成枪.png"
    )

    assert "场景空间布局图" in spatial
    assert "禁止只生成普通仰拍/平视场景插画" in spatial
    assert "武器握持比例参考" in scale
    assert "禁止出现清晰可辨的人物五官/肖像脸" in scale
    assert "禁止把比例图画成角色立绘" in scale
    assert "道具尺度/比例参考" in prop_scale
    assert "无脸尺度参照" in prop_scale
    assert "禁止只复制主道具静物" in prop_scale
    assert "道具手持/携行参考" in prop_in_hand
    assert "禁止只画无人静物" in prop_in_hand
    assert "武器动态形态参考" in active
    assert "鞋靴" in codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_CHAR_TEST_45度.png"
    )


def test_shared_variant_note_locks_small_prop_to_single_palm_scale() -> None:
    body = "约一掌高（12至16厘米），可单手完整握持，宽度略窄于掌宽。"
    scale = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_道具_腰牌_比例.png", section_body=body
    )
    in_hand = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_道具_腰牌_手持.png", section_body=body
    )
    assert "产品独照" in scale and "完整成年手掌" in scale
    assert "只出现一只" in in_hand and "另一只手完全不入画" in in_hand
    assert "鞋靴" in codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_CHAR_TEST_三视图.png"
    )
    side = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_CHAR_TEST_侧.png"
    )
    assert "严格90°" in side
    assert "只能看到一只眼" in side
    assert "禁止前45°" in side
    assert "禁止凭空新增疤痕" in side
    back = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_CHAR_TEST_背.png"
    )
    assert "严格180°" in back
    assert "脸、双眼、鼻梁、嘴唇" in back
    assert "禁止后45°冒充正背面" in back


def test_shared_variant_note_keeps_architectural_fixture_installed_for_use_reference() -> None:
    body = "单扇窗框是墙上固定建筑构件，人站立可单手推开窗扇。"
    note = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_道具_WINDOW_LATTICE_手持.png", section_body=body
    )
    assert "完整安装" in note
    assert "禁止双手捧着整块" in note
    assert "多格拼板" in note
    rail_note = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_道具_STAIR_RAIL_手持.png",
        section_body="室内楼梯扶栏，暗褐老木，成人腰高，固定安装。",
    )
    assert "完整安装" in rail_note


def test_shared_variant_note_keeps_large_furniture_grounded_during_interaction() -> None:
    note = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_道具_DINING_TABLE_手持.png",
        section_body="长方木桌，厚桌面、四条桌腿与横撑。",
    )
    assert "四腿/底座完整落地" in note
    assert "禁止将整张桌" in note
    assert "多格拼板" in note


def test_shared_variant_note_requires_true_reverse_scene_view() -> None:
    note = codex_image_runner.shared_variant_note("出图/共享/图片/定妆_场景_屋内_反打.png")
    assert "摄影机必须移到" in note
    assert "未展示的对侧墙面" in note
    assert "禁止复制主视图" in note


def test_shared_variant_note_requires_true_reverse_fixture_structure() -> None:
    note = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_道具_场景木门_反面.png",
        section_body="北宋小民楼屋的旧木板门，固定安装在粗木门框内，正面有横向木闩。",
    )

    assert "真实背面结构参考" in note
    assert "加固横档" in note
    assert "不得把正面可见的横木门闩" in note
    assert "禁止镜像或复刻正面" in note


def test_shared_variant_note_does_not_invent_floor_plan_features() -> None:
    note = codex_image_runner.shared_variant_note("出图/共享/图片/定妆_场景_屋内_平面图.png")
    assert "只标出资产登记" in note
    assert "不得凭空新增破顶" in note
    assert "不得添加标题、图例栏、侧栏" in note
    assert "最多八个简短中文标签" in note
    assert "主交战区" not in note


def test_style_anchor_shared_aliases_include_short_names() -> None:
    aliases = codex_image_runner.shared_aliases(
        "## 统一风格锚",
        "",
        "出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png",
    )

    assert "风格锚" in aliases
    assert "STYLE_ANCHOR" in aliases


def test_mark_shared_reference_status_upgrades_string_registry_refs(tmp_path: Path) -> None:
    rel = "出图/共享/图片/定妆_VFX_TEST.png"
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "VFX_TEST",
                        "type": "vfx",
                        "reference_group": {"primary": rel},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    derivation = {"method": "generated", "source_path": "prompt"}

    codex_image_runner.mark_shared_reference_status(
        tmp_path, rel, "ready", derivation=derivation
    )

    data = json.loads((shared / "asset_registry.json").read_text(encoding="utf-8"))
    primary = data["assets"][0]["reference_group"]["primary"]
    assert primary == {"path": rel, "status": "ready", "derivation": derivation}


def test_mark_shared_reference_status_does_not_nest_existing_path_dict(tmp_path: Path) -> None:
    rel = "出图/共享/图片/定妆_CHAR_TEST.png"
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    (shared / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_TEST",
                        "forms": [
                            {
                                "form": "常态",
                                "reference_group": {
                                    "front": {"path": rel, "status": "needs_regen"}
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    codex_image_runner.mark_shared_reference_status(tmp_path, rel, "ready")

    data = json.loads((shared / "identity_registry.json").read_text(encoding="utf-8"))
    front = data["characters"][0]["forms"][0]["reference_group"]["front"]
    assert front == {"path": rel, "status": "ready"}


def test_mark_shared_reference_status_does_not_rewrite_derivation_source_refs(tmp_path: Path) -> None:
    rel = "出图/共享/图片/定妆_VFX_TEST.png"
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "VFX_TEST",
                        "type": "vfx",
                        "reference_group": {
                            "primary": {"path": rel, "status": "planned"}
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    derivation = {
        "method": "image2image",
        "source_refs": [rel, "出图/共享/图片/定妆_武器_TEST.png"],
    }

    codex_image_runner.mark_shared_reference_status(
        tmp_path, rel, "ready", derivation=derivation
    )

    data = json.loads((shared / "asset_registry.json").read_text(encoding="utf-8"))
    primary = data["assets"][0]["reference_group"]["primary"]
    assert primary["status"] == "ready"
    assert primary["derivation"] == derivation


def test_mark_shared_reference_status_refreshes_current_pixel_metadata(tmp_path: Path) -> None:
    rel = "出图/共享/图片/定妆_VFX_TEST.png"
    png = tmp_path / rel
    write_valid_png(png)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "VFX_TEST",
                        "type": "vfx",
                        "reference_group": {
                            "primary": {
                                "path": rel,
                                "status": "planned",
                                "sha256": "stale",
                                "width": 1,
                                "height": 1,
                            }
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    codex_image_runner.mark_shared_reference_status(tmp_path, rel, "ready")

    data = json.loads((shared / "asset_registry.json").read_text(encoding="utf-8"))
    primary = data["assets"][0]["reference_group"]["primary"]
    assert primary["sha256"] == codex_image_runner.file_sha256(png)
    assert primary["width"] == 512
    assert primary["height"] == 512


def test_reference_inputs_do_not_self_reference_target_being_regenerated(tmp_path: Path) -> None:
    rel = "出图/共享/图片/定妆_VFX_TEST.png"
    lineage_rel = "出图/共享/图片/旧_血统来源.png"
    write_valid_png(tmp_path / rel)
    write_valid_png(tmp_path / lineage_rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "VFX_TEST",
                        "type": "vfx",
                        "reference_group": {
                            "primary": {
                                "path": rel,
                                "status": "ready",
                                "derivation": {"source_path": lineage_rel},
                            }
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="VFX_TEST",
        title="## VFX_TEST",
        body="**资产引用注册层**：`VFX_TEST`",
        target_line=f"`{rel}`",
    )
    target = codex_image_runner.Target("VFX_TEST::定妆_VFX_TEST", "VFX_TEST", "shared", rel, section)
    target.aliases = {"VFX_TEST"}

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert all(item["rel_path"] != rel for item in inputs)
    assert all(item["rel_path"] != lineage_rel for item in inputs)


def test_style_source_references_attach_only_to_clean_style_anchor_target(tmp_path: Path) -> None:
    style_rel = "设定库/参考资料/视觉参考/style.jpg"
    write_valid_png(tmp_path / style_rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "style_anchor_registry.json").write_text(json.dumps({
        "source_style_references": [
            {
                "path": style_rel,
                "sha256": codex_image_runner.file_sha256(tmp_path / style_rel),
                "status": "ready",
                "use_policy": "style_source_only",
                "rights_status": "authorized",
                "eligible_for_generation": True,
                "backend_upload_allowed": True,
                "watermark_present": False,
            }
        ]
    }), encoding="utf-8")
    style_section = codex_image_runner.ClipSection(
        clip="STYLE_ANCHOR", title="## 风格锚", body="风格锚", target_line=""
    )
    style_target = codex_image_runner.Target(
        "STYLE_ANCHOR", "STYLE_ANCHOR", "shared",
        "出图/共享/图片/风格锚_测试.png", style_section,
    )
    shot_target = codex_image_runner.Target(
        "CHAR_01", "CHAR_01", "shared",
        "出图/共享/图片/定妆_CHAR_01.png", style_section,
    )

    style_bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", style_target)
    shot_bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", shot_target)

    assert any(style_rel in item.get("paths", []) for item in style_bundle["items"])
    assert all(style_rel not in item.get("paths", []) for item in shot_bundle["items"])


def test_pending_rights_status_is_never_ready_even_with_legacy_override_flag() -> None:
    for status in (
        "available_pending_rights_review",
        "user_provided_reference_pending_rights_review",
        "accepted_for_internal_generation_pending_rights_review",
    ):
        assert not codex_image_runner._status_ready(
            {"status": status},
            allow_pending_user_reference=True,
        )


def test_shared_asset_preflight_uses_compliance_not_full_image_gate(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, list[str]] = {}
    monkeypatch.setattr(codex_image_runner, "reference_manifest_generation_issues", lambda _root: [])

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout='{"status":"pass"}', stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    assert codex_image_runner.run_shared_asset_preflight(tmp_path, "第1集")
    command = captured["cmd"]
    assert command[1].endswith("skills/n2d/n2d-compliance/scripts/compliance.py")
    assert command[-3:] == ["--stage", "image", "--json"]
    assert "--stage" in command and command[command.index("--stage") + 1] == "image"
    assert "image_preflight" not in command


def test_shared_asset_preflight_blocks_reference_rights_before_compliance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        codex_image_runner,
        "reference_manifest_generation_issues",
        lambda _root: ["reference[user-1]:watermark_present_or_not_explicitly_false"],
    )

    def forbidden_run(*args, **kwargs):
        raise AssertionError("compliance subprocess must not run after reference-rights block")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", forbidden_run)

    assert not codex_image_runner.run_shared_asset_preflight(tmp_path, "第1集")


def test_shared_targets_preflight_is_nonwaivable_and_runs_before_generation(tmp_path: Path, monkeypatch) -> None:
    section = codex_image_runner.ClipSection(
        "STYLE_ANCHOR", "## 风格锚", "风格锚", "`出图/共享/图片/风格锚.png`"
    )
    target = codex_image_runner.Target(
        "STYLE_ANCHOR",
        "STYLE_ANCHOR",
        "shared",
        "出图/共享/图片/风格锚.png",
        section,
    )
    monkeypatch.setattr(codex_image_runner, "build_shared_targets", lambda *_args: [target])
    monkeypatch.setattr(codex_image_runner, "run_shared_asset_preflight", lambda *_args: False)

    def forbidden_process(*args, **kwargs):
        raise AssertionError("paid shared target ran before shared_asset_preflight passed")

    monkeypatch.setattr(codex_image_runner, "process_target", forbidden_process)

    assert codex_image_runner.main([
        str(tmp_path),
        "第1集",
        "--shared-targets",
        "STYLE_ANCHOR",
        "--skip-preflight",
    ]) == 1


def test_target_generation_lock_blocks_duplicate_paid_submission(tmp_path: Path) -> None:
    first = codex_image_runner.acquire_target_generation_lock(
        tmp_path, "出图/共享/图片/风格锚.png", 600
    )
    second = codex_image_runner.acquire_target_generation_lock(
        tmp_path, "出图/共享/图片/风格锚.png", 600
    )

    assert first is not None and first.is_file()
    assert second is None
    codex_image_runner.release_target_generation_lock(first)
    assert not first.exists()


def test_faceless_shared_scene_suppresses_character_refs_from_prompt_text(tmp_path: Path) -> None:
    face_rel = "出图/共享/图片/定妆_姜月初_脸部特写.png"
    scene_rel = "出图/共享/图片/定妆_姜月初识海阴山.png"
    write_valid_png(tmp_path / face_rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_JIANG_YUECHU",
                        "forms": [
                            {
                                "form": "战场形态",
                                "reference_group": {
                                    "face_anchor_refs": {"path": face_rel, "status": "ready"}
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "LOC_CONSCIOUSNESS_SEA",
                        "type": "scene",
                        "face_policy": "faceless",
                        "human_presence": "no_person_scene_plate",
                        "reference_group": {"primary": scene_rel},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="LOC_CONSCIOUSNESS_SEA",
        title="## LOC_CONSCIOUSNESS_SEA / 姜月初识海",
        body=(
            f"**目标存档**：`{scene_rel}`\n"
            "**资产引用注册层**：`LOC_CONSCIOUSNESS_SEA`；face_policy=`faceless`。\n"
            "分镜若需要女主背影，必须单独引用 `CHAR_JIANG_YUECHU` 对应形态入镜。\n"
        ),
        target_line=f"`{scene_rel}`",
    )
    target = codex_image_runner.Target(
        "LOC_CONSCIOUSNESS_SEA::定妆_姜月初识海阴山",
        "LOC_CONSCIOUSNESS_SEA",
        "shared",
        scene_rel,
        section,
    )
    target.aliases = {"LOC_CONSCIOUSNESS_SEA"}

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert all(item["kind"] != "character" for item in bundle["items"])
    assert all(item["rel_path"] != face_rel for item in inputs)


def test_cross_episode_handoff_source_frame_becomes_codex_input(tmp_path: Path) -> None:
    source_rel = "出图/第4集/图片/Clip11_end.png"
    write_valid_png(tmp_path / source_rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip_01",
        body=(
            "**目标落档**：`出图/第5集/图片/Clip01_first.png`\n"
            f"**跨集接力源帧**：`{source_rel}`；from=第4集/EP04_CLIP11；handoff_type=continuous_action_match_cut\n"
            "跨集动作接力：必须以 source_frame 几何底板承接上一集尾帧。"
        ),
        target_line="`出图/第5集/图片/Clip01_first.png`",
    )
    target = codex_image_runner.Target(
        "Clip_01",
        "Clip_01",
        "firstframe",
        "出图/第5集/图片/Clip01_first.png",
        section,
    )

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第5集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第5集", target, bundle)

    assert any(item["kind"] == "source_frame" and source_rel in item["paths"] for item in bundle["items"])
    assert inputs[0]["role"] == "source_frame"
    assert inputs[0]["rel_path"] == source_rel


def test_face_mood_only_form_excludes_outfit_references(tmp_path: Path) -> None:
    face_rel = "出图/共享/图片/定妆_姜月初_觉醒_脸部特写.png"
    front_rel = "出图/共享/图片/定妆_姜月初_觉醒.png"
    outfit_rel = "出图/共享/图片/定妆_姜月初_觉醒_半身.png"
    for rel in (face_rel, front_rel, outfit_rel):
        write_valid_png(tmp_path / rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_JIANG_YUECHU",
                        "forms": [
                            {
                                "form": "觉醒蓝调母本",
                                "reference_use_policy": "face_mood_only",
                                "reference_group": {
                                    "front": {"path": front_rel, "status": "ready"},
                                    "outfit": {"path": outfit_rel, "status": "ready"},
                                    "face_anchor_refs": {"path": face_rel, "status": "ready"},
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_11",
        title="## Clip 11",
        body="**资产身份注册层**：`CHAR_JIANG_YUECHU/觉醒蓝调母本*`。",
        target_line="`出图/第1集/图片/Clip_11.png`",
    )
    target = codex_image_runner.Target(
        "Clip_11",
        "Clip_11",
        "firstframe",
        "出图/第1集/图片/Clip_11.png",
        section,
    )

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert [item["rel_path"] for item in inputs] == [face_rel]


def test_asset_shared_target_waits_for_visual_review_even_with_makeup_filename() -> None:
    section = codex_image_runner.ClipSection("LOC_TEST", "## LOC_TEST", "", "")
    target = codex_image_runner.Target(
        "LOC_TEST::定妆_姜月初识海阴山",
        "LOC_TEST",
        "shared",
        "出图/共享/图片/定妆_姜月初识海阴山.png",
        section,
    )
    target.aliases = {"LOC_TEST"}

    assert codex_image_runner.status_after_shared_generation(target.rel_path, target) == "review_pending"


def test_character_shared_target_status_still_review_pending(monkeypatch) -> None:
    monkeypatch.delenv("N2D_HUMAN_REVIEWED_SHARED", raising=False)
    section = codex_image_runner.ClipSection("CHAR_01", "## CHAR_01", "", "")
    target = codex_image_runner.Target(
        "CHAR_01::定妆_沈念_常态",
        "CHAR_01",
        "shared",
        "出图/共享/图片/定妆_沈念_常态.png",
        section,
    )
    target.aliases = {"CHAR_01", "CHAR_01/常态"}

    assert codex_image_runner.status_after_shared_generation(target.rel_path, target) == "review_pending"


def test_primary_character_makeup_uses_strict_front_guard_not_action_gaze() -> None:
    section = codex_image_runner.ClipSection(
        "CHAR_01",
        "## CHAR_01",
        "角色动作镜可用 45° 侧脸，但本目标是共享主定妆。",
        "",
    )
    target = codex_image_runner.Target(
        "CHAR_01::定妆_沈念_常态",
        "CHAR_01",
        "shared",
        "出图/共享/图片/定妆_沈念_常态.png",
        section,
    )
    target.aliases = {"CHAR_01", "CHAR_01/常态"}

    guards = " ".join(codex_image_runner.model_facing_policy_guards(target, []))

    assert "身体、肩线和脸严格正对相机" in guards
    assert "头部偏转不超过 5 度" in guards
    assert "镜头为旁观者视角" not in guards


def test_real_quadruped_makeup_uses_animal_guard_not_human_front_plate() -> None:
    section = codex_image_runner.ClipSection(
        "BEAST_TIGER",
        "## 景阳冈猛虎",
        "景阳冈成年华南虎，真实四足野生猫科动物；四只虎掌全部着地，完整长尾。",
        "",
    )
    target = codex_image_runner.Target(
        "BEAST_TIGER::定妆_BEAST_TIGER__常态",
        "BEAST_TIGER",
        "shared",
        "出图/共享/图片/定妆_BEAST_TIGER__常态.png",
        section,
    )
    target.aliases = {"BEAST_TIGER", "BEAST_TIGER/常态"}

    guards = " ".join(codex_image_runner.model_facing_policy_guards(target, []))

    assert "真实四足动物正面母本" in guards
    assert "四只兽掌全部着地" in guards
    assert "禁止双足直立" in guards
    assert "不套用人物的鞋靴、服装、手部或直立姿态规则" in guards
    assert "身体、肩线和脸严格正对相机" not in guards
    assert "从头到鞋靴完整可见" not in guards
    note = codex_image_runner.shared_variant_note(target.rel_path, section_body=section.body)
    assert "真实四足动物的共享主参考图" in note
    assert "从耳尖、四掌到尾尖完整可见" in note
    assert "人物全身/标准立绘" not in note
    assert "鞋靴" not in note


def test_style_anchor_uses_control_board_note_and_skips_story_guards() -> None:
    section = codex_image_runner.ClipSection(
        "STYLE_ANCHOR",
        "## STYLE_ANCHOR",
        "写实国漫人物、城寨、刀兵与虎妖只描述下游适用语境；不要人物、妖物、建筑、兵器。",
        "",
    )
    target = codex_image_runner.Target(
        "STYLE_ANCHOR::风格锚_黑赤镇魔水墨妖谱",
        "STYLE_ANCHOR",
        "shared",
        "出图/共享/图片/风格锚_黑赤镇魔水墨妖谱.png",
        section,
    )
    target.aliases = {"STYLE_ANCHOR", "风格锚"}

    note = codex_image_runner.shared_variant_note(target.rel_path)
    guards = " ".join(codex_image_runner.model_facing_policy_guards(target, []))

    assert "抽象分区式视觉语言控制板" in note
    assert "人物全身/标准立绘" not in note
    assert "色卡" in guards
    assert "工作台" in guards
    assert "镜头为旁观者视角" not in guards
    assert "武器入体/接触点铁律" not in guards


def test_character_45_degree_reference_does_not_use_primary_front_guard() -> None:
    section = codex_image_runner.ClipSection("CHAR_01", "## CHAR_01", "", "")
    target = codex_image_runner.Target(
        "CHAR_01::定妆_沈念_常态_45度",
        "CHAR_01",
        "shared",
        "出图/共享/图片/定妆_沈念_常态_45度.png",
        section,
    )
    target.aliases = {"CHAR_01", "CHAR_01/常态"}

    guards = " ".join(codex_image_runner.model_facing_policy_guards(target, []))

    assert "共享角色正面主母本" not in guards


def test_broken_left_arm_guard_uses_character_left_and_preserves_limb_count() -> None:
    section = codex_image_runner.ClipSection(
        "CHAR_02",
        "## CHAR_02",
        "服装妆造：玄黑劲装；左臂不自然扭曲，胸腹有伤。",
        "",
    )
    target = codex_image_runner.Target(
        "CHAR_02::定妆_裴长青_常态",
        "CHAR_02",
        "shared",
        "出图/共享/图片/定妆_裴长青_常态.png",
        section,
    )
    target.aliases = {"CHAR_02", "CHAR_02/常态"}

    guards = " ".join(codex_image_runner.model_facing_policy_guards(target, []))

    assert "按角色自身左右计" in guards
    assert "画面观者右侧" in guards
    assert "恰好两条手臂两只手" in guards


def test_cold_open_blade_hook_guard_forces_insert_and_humanoid_tiger() -> None:
    section = codex_image_runner.ClipSection(
        "Clip_01",
        "## 镜头 1",
        "刀柄、发抖指节和衣料同轴。染血脸与后景虎妖巨影，痛苦但已决定。",
        "",
    )
    target = codex_image_runner.Target(
        "Clip_01_first",
        "Clip_01",
        "firstframe",
        "出图/第1集/图片/Clip01_first.png",
        section,
    )

    guards = codex_image_runner.model_facing_policy_guards(target, [])

    assert "85mm ECU/CU叙事插入" in guards[0]
    assert "刀尖悬停并明确指向" in guards[0]
    assert "虎头人身、直立双腿" in guards[0]
    assert "绝不是四足普通老虎" in guards[0]


def test_clip02_first_guard_forces_ten_minutes_earlier_corpse_field_establishing_shot() -> None:
    section = codex_image_runner.ClipSection(
        "Clip_02",
        "## 镜头 2",
        "尸场空间一次建立。姜月初摸到囚服，压住惊惧。断刀封路，裴长青右前半跪。",
        "",
    )
    target = codex_image_runner.Target(
        "Clip_02_first",
        "Clip_02",
        "firstframe",
        "出图/第1集/图片/Clip02_first.png",
        section,
    )

    guards = codex_image_runner.model_facing_policy_guards(target, [])

    joined = " ".join(guards[:3])
    assert "35mm低机位广角尸场建立镜" in guards[0]
    assert "空手摸无血残损囚服" in guards[0]
    assert "水平倒地伪死的虎头人身巨人" in guards[1]
    assert "两条人形手臂手掌" in guards[1]
    assert "水平长虎身或普通老虎" in guards[1]
    assert "禁止站立、复活、逼近" in guards[1]
    assert "一截断刀插地封路" in guards[2]
    assert "禁止完整长刀、第二把刀" in guards[2]
    assert "85mm海报群像" in joined


def test_clip04_first_guard_keeps_tiger_prone_and_broken_saber_offscreen() -> None:
    section = codex_image_runner.ClipSection(
        "Clip_04",
        "## 镜头 4",
        "50mm双人镜，姜月初绕到未伤右臂搀扶，伪死虎妖后景不消失。",
        "",
    )
    target = codex_image_runner.Target(
        "Clip_04_first",
        "Clip_04",
        "firstframe",
        "出图/第1集/图片/Clip04_first.png",
        section,
    )

    guards = codex_image_runner.model_facing_policy_guards(target, [])

    joined = " ".join(guards[:3])
    assert "两人尚未发生任何肢体接触或搀扶" in guards[0]
    assert "虎头侧贴地、双眼闭合" in guards[1]
    assert "两条人形手臂手掌" in guards[1]
    assert "禁止直立、坐起、悬浮、睁眼" in guards[1]
    assert "PROP_断刀已留在上一空间并保持画外" in guards[2]
    assert "禁止地面断刀、第二把刀" in guards[2]
    assert "不看镜头" in joined


def test_shared_scene_baseline_excludes_baked_system_gold_vfx() -> None:
    section = codex_image_runner.ClipSection(
        "LOC_01",
        "## LOC_01",
        "LOC_01 低位夕阳从画左后侧逆光，系统金光仅作局部剧情光。",
        "",
    )
    target = codex_image_runner.Target(
        "LOC_01::定妆_场景_夕照荒野尸场",
        "LOC_01",
        "shared",
        "出图/共享/图片/定妆_场景_夕照荒野尸场.png",
        section,
    )
    target.aliases = {"LOC_01"}

    guards = " ".join(codex_image_runner.model_facing_policy_guards(target, []))

    assert "无特效的环境底版" in guards
    assert "完全不出现系统金光" in guards
    assert "系统特效由后续镜头单独叠加" in guards


def test_shared_scene_resident_beast_keeps_registered_species_and_topology() -> None:
    section = codex_image_runner.ClipSection(
        "LOC_01",
        "## LOC_01",
        "常驻主体：`BEAST_01/实体_重伤复活`，远端虎山神尸体。",
        "",
    )
    target = codex_image_runner.Target(
        "LOC_01::定妆_场景_夕照荒野尸场",
        "LOC_01",
        "shared",
        "出图/共享/图片/定妆_场景_夕照荒野尸场.png",
        section,
    )
    target.aliases = {"LOC_01"}

    guards = " ".join(codex_image_runner.model_facing_policy_guards(target, []))

    assert "BEAST_01/实体_重伤复活" in guards
    assert "尸体/倒地状态只改变姿势" in guards
    assert "禁止把虎头人身妖物改成四足普通虎" in guards
    assert "共享角色正面主母本" not in guards
    assert "共享角色定妆使用统一规格" not in guards
    assert "武器入体/接触点铁律" not in guards
    assert "镜头为旁观者视角" not in guards
    assert "生产级场景主母本" in codex_image_runner.shared_variant_note(target.rel_path)
    assert "不得做上下/左右多格拼板" in codex_image_runner.shared_variant_note(target.rel_path)


def test_faceless_shared_scene_still_attaches_explicit_resident_beast_identity(tmp_path: Path) -> None:
    beast_rel = "出图/共享/图片/定妆_BEAST_01__实体_重伤复活.png"
    write_valid_png(tmp_path / beast_rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "identity_registry.json").write_text(
        json.dumps({"characters": [{
            "id": "BEAST_01",
            "forms": [{
                "form": "实体_重伤复活",
                "reference_group": {"front": {"path": beast_rel, "status": "ready"}},
            }],
        }]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text(
        json.dumps({"assets": [{
            "id": "LOC_01",
            "type": "scene",
            "face_policy": "faceless",
            "reference_group": {},
        }]}, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        "LOC_01",
        "## LOC_01",
        "常驻物件：`BEAST_01/实体_重伤复活`（虎头人身尸体）。",
        "",
    )
    target = codex_image_runner.Target(
        "LOC_01::定妆_场景_夕照荒野尸场",
        "LOC_01",
        "shared",
        "出图/共享/图片/定妆_场景_夕照荒野尸场.png",
        section,
    )
    target.aliases = {"LOC_01", "BEAST_01/实体_重伤复活"}

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    character = next(item for item in bundle["items"] if item["kind"] == "character")
    assert character["id"] == "BEAST_01"
    assert character["form"] == "实体_重伤复活"
    assert character["paths"] == [beast_rel]


def test_shared_first_interlock_blocks_review_failed_asset_reference(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip_01.png`\n"
        "**资产引用注册层**：`WEAPON_TEST` -> asset_registry.json。\n",
    )
    primary = "出图/共享/图片/定妆_WEAPON_TEST.png"
    scale = "出图/共享/图片/定妆_WEAPON_TEST_握持比例.png"
    write_valid_png(tmp_path / primary)
    write_valid_png(tmp_path / scale)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text(
        json.dumps({
            "assets": [{
                "id": "WEAPON_TEST",
                "type": "weapon",
                "reference_group": {
                    "primary": {"path": primary, "status": "ready"},
                    "scale_reference": {
                        "path": scale,
                        "status": "review_failed",
                        "review_reason": "identity face drift in scale sheet",
                    },
                },
                "weapon_profile": {"silhouette": "long halberd"},
                "constraints": {"scale": "fixed"},
                "self_check_passed": False,
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    issues = codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集")

    assert any("WEAPON_TEST" in issue and "复核失败参考图" in issue for issue in issues)
    assert any("WEAPON_TEST" in issue and "self_check_passed=false" in issue for issue in issues)


def test_shot_asset_refs_resolve_chinese_constraint_suffix_to_registered_id() -> None:
    refs = codex_image_runner._shot_asset_refs(
        "**资产引用注册层**：不要让 PROP_水桶结构/颜色/尺寸漂移；PROP_扁担保持稳定。",
        {"PROP_水桶", "PROP_扁担"},
    )

    assert refs == {"PROP_水桶", "PROP_扁担"}
    assert "PROP_水桶结构" not in refs


def test_controlled_multiref_derivation_prefers_expected_parent(tmp_path: Path) -> None:
    front = tmp_path / "出图" / "共享" / "图片" / "定妆_CHAR_TEST_front.png"
    turn = tmp_path / "出图" / "共享" / "图片" / "定妆_CHAR_TEST_三视图.png"
    write_tiny_png(front)
    write_tiny_png(turn)
    inputs = [
        {
            "rel_path": "出图/共享/图片/定妆_CHAR_TEST_front.png",
            "abs_path": str(front),
            "sha256": "front-sha",
            "priority": 120,
        },
        {
            "rel_path": "出图/共享/图片/定妆_CHAR_TEST_三视图.png",
            "abs_path": str(turn),
            "sha256": "turn-sha",
            "priority": 140,
        },
    ]

    angle = codex_image_runner.controlled_multiref_derivation(
        tmp_path, "出图/共享/图片/定妆_CHAR_TEST_侧.png", inputs
    )
    face = codex_image_runner.controlled_multiref_derivation(
        tmp_path, "出图/共享/图片/定妆_CHAR_TEST_脸部特写.png", inputs
    )

    assert angle["method"] == "controlled_multiref_generation"
    assert angle["source_path"] == "出图/共享/图片/定妆_CHAR_TEST_三视图.png"
    assert angle["source_sha256"] == "turn-sha"
    assert angle["crop_box"] == [0, 0, 1, 1]
    assert face["source_path"] == "出图/共享/图片/定妆_CHAR_TEST_front.png"
    assert face["reference_input_mode"] == "codex_exec_image_flags"


def test_controlled_multiref_derivation_treats_unsuffixed_makeup_as_front(tmp_path: Path) -> None:
    front = tmp_path / "出图" / "共享" / "图片" / "定妆_CHAR_TEST__常态.png"
    style = tmp_path / "出图" / "共享" / "图片" / "风格锚_冷灰写实3D国风漫剧.png"
    write_tiny_png(front)
    write_tiny_png(style)
    inputs = [
        {
            "rel_path": "出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png",
            "abs_path": str(style),
            "sha256": "style-sha",
            "priority": 10,
        },
        {
            "rel_path": "出图/共享/图片/定妆_CHAR_TEST__常态.png",
            "abs_path": str(front),
            "sha256": "front-sha",
            "priority": 200,
        },
    ]

    derivation = codex_image_runner.controlled_multiref_derivation(
        tmp_path, "出图/共享/图片/定妆_CHAR_TEST__常态_三视图.png", inputs
    )

    assert derivation["source_path"] == "出图/共享/图片/定妆_CHAR_TEST__常态.png"
    assert derivation["source_sha256"] == "front-sha"


def test_shared_targets_include_character_base_pack_and_registry_expressions(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "出图" / "共享" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "角色定妆.md").write_text(
        "# 角色定妆 Prompt\n\n"
        "## ① CHAR_01 沈念 / 林婉儿·常态（待生成）\n"
        "**目标存档**：`出图/共享/图片/定妆_沈念_常态.png`\n"
        "**身份注册**：`出图/共享/identity_registry.json` → `CHAR_01/常态`\n"
        "**角色定妆组**：正面主参考 `定妆_沈念_常态.png`；"
        "45°参考 `定妆_沈念_常态_45度.png`；"
        "侧面参考 `定妆_沈念_常态_侧.png`；"
        "背面参考 `定妆_沈念_常态_背.png`；"
        "服装参考 `定妆_沈念_常态_半身.png`；"
        "基础脸部参考 `定妆_沈念_常态_脸部特写.png`；"
        "人审拼版 `定妆_沈念_常态_三视图.png`。\n"
        "## ② CHAR_01 沈念 / 林婉儿·觉醒态（待生成）\n"
        "**目标存档**：`出图/共享/图片/定妆_沈念_觉醒态.png`\n"
        "**身份注册**：`出图/共享/identity_registry.json` → `CHAR_01/觉醒态`\n",
        encoding="utf-8",
    )
    (prompt_dir / "场景定妆.md").write_text("", encoding="utf-8")
    (prompt_dir / "道具定妆.md").write_text("", encoding="utf-8")
    (prompt_dir / "法宝定妆.md").write_text(
        "## WEAPON_TEST / 测试法宝\n"
        "**目标存档**：`出图/共享/图片/定妆_测试法宝.png`\n",
        encoding="utf-8",
    )
    (prompt_dir / "特效定妆.md").write_text("", encoding="utf-8")
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_01",
                        "forms": [
                            {
                                "form": "常态",
                                "reference_group": {
                                    "front": "出图/共享/图片/定妆_沈念_常态.png",
                                    "expressions": [
                                        {"emotion": "冷静", "path": "出图/共享/图片/定妆_沈念_常态_表情_冷静.png"}
                                    ],
                                },
                            },
                            {
                                "form": "觉醒态",
                                "reference_group": {
                                    "front": "出图/共享/图片/定妆_沈念_觉醒态.png",
                                    "expressions": [
                                        {"emotion": "怒", "path": "出图/共享/图片/定妆_沈念_觉醒态_表情_怒.png"}
                                    ],
                                },
                            },
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    targets = codex_image_runner.load_shared_sections(tmp_path)
    by_path = {target.rel_path: target for target in targets}

    assert "出图/共享/图片/定妆_沈念_常态_45度.png" in by_path
    assert "出图/共享/图片/定妆_沈念_常态_脸部特写.png" in by_path
    assert "出图/共享/图片/定妆_沈念_常态_表情_冷静.png" in by_path
    assert "出图/共享/图片/定妆_沈念_觉醒态_表情_怒.png" in by_path
    assert "出图/共享/图片/定妆_测试法宝.png" in by_path
    assert "45°" in by_path["出图/共享/图片/定妆_沈念_常态_45度.png"].variant_note
    assert by_path["出图/共享/图片/定妆_沈念_觉醒态.png"].section.title.startswith("## ②")
    assert by_path["出图/共享/图片/定妆_沈念_觉醒态_表情_怒.png"].section.title.startswith("## ②")


def test_shared_targets_include_group_mount_and_scene_nested_refs(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "出图" / "共享" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "角色定妆.md").write_text(
        "## 飞鹰门马队（`GROUP_飞鹰门马队/常态`）\n"
        "**目标存档**：`出图/共享/图片/定妆_GROUP_飞鹰门马队__常态.png`\n",
        encoding="utf-8",
    )
    (prompt_dir / "道具定妆.md").write_text(
        "## 飞鹰门马匹与火把（`MOUNT_GROUP_01`）\n"
        "**目标存档**：`出图/共享/图片/定妆_道具_飞鹰门马匹与火把.png`\n",
        encoding="utf-8",
    )
    (prompt_dir / "场景定妆.md").write_text(
        "## 荒野官道夜路（`LOC_02`）\n"
        "**目标存档**：`出图/共享/图片/定妆_场景_荒野官道夜路.png`\n",
        encoding="utf-8",
    )
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "GROUP_飞鹰门马队",
                        "forms": [
                            {
                                "form": "常态",
                                "reference_atlas": {
                                    "build_tier": "restricted_partial",
                                    "partial_refs": {
                                        "hand": {
                                            "path": "出图/共享/图片/定妆_GROUP_飞鹰门马队__常态_手部局部.png",
                                            "status": "planned",
                                        }
                                    },
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "MOUNT_GROUP_01",
                        "name": "飞鹰门马匹与火把",
                        "reference_group": {
                            "scale_ref": {
                                "path": "出图/共享/图片/定妆_道具_飞鹰门马匹与火把_比例.png",
                                "status": "planned",
                            }
                        },
                    },
                    {
                        "id": "LOC_02",
                        "name": "荒野官道夜路",
                        "scene_atlas": {
                            "base_views": {
                                "back": {
                                    "path": "出图/共享/图片/定妆_场景_荒野官道夜路_反打.png",
                                    "status": "planned",
                                },
                                "floor_plan": {
                                    "path": "出图/共享/图片/定妆_场景_荒野官道夜路_平面图.png",
                                    "status": "planned",
                                }
                            }
                        },
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    targets = codex_image_runner.load_shared_sections(tmp_path)
    by_path = {target.rel_path: target for target in targets}

    assert "出图/共享/图片/定妆_GROUP_飞鹰门马队__常态_手部局部.png" in by_path
    assert "出图/共享/图片/定妆_道具_飞鹰门马匹与火把_比例.png" in by_path
    assert "出图/共享/图片/定妆_场景_荒野官道夜路_反打.png" in by_path
    assert "出图/共享/图片/定妆_场景_荒野官道夜路_平面图.png" in by_path
    assert "手部局部参考" in by_path["出图/共享/图片/定妆_GROUP_飞鹰门马队__常态_手部局部.png"].variant_note
    assert "道具尺度/比例参考" in by_path["出图/共享/图片/定妆_道具_飞鹰门马匹与火把_比例.png"].variant_note
    assert "场景空间布局图" in by_path["出图/共享/图片/定妆_场景_荒野官道夜路_平面图.png"].variant_note


def test_restricted_partial_silhouette_form_does_not_require_full_basic_pack(tmp_path: Path) -> None:
    rel = "出图/共享/图片/定妆_群像_剪影.png"
    write_valid_png(tmp_path / rel)
    form = {
        "form": "群像剪影",
        "reference_group": {
            "restricted_partial": True,
            "silhouette": {"path": rel, "status": "ready"},
        },
        "reference_atlas": {
            "build_tier": "restricted_partial_silhouette",
            "base_views": {"silhouette": {"path": rel, "status": "ready"}},
        },
    }

    assert codex_image_runner._character_basic_pack_issues(tmp_path, "CHAR_GROUP", form) == []


def test_character_basic_pack_blocks_dirty_self_check(tmp_path: Path) -> None:
    form = {
        "form": "常态",
        "self_check_passed": False,
        "reference_group": {
            "front": {"path": "出图/共享/图片/定妆_沈念_常态.png", "status": "ready"}
        },
    }

    issues = codex_image_runner._character_basic_pack_issues(tmp_path, "CHAR_01", form)

    assert issues == ["CHAR_01/常态: 共享定妆 self_check_passed=false，先复核/重出共享库"]


def test_named_minimal_shared_interlock_only_adds_angles_when_shot_needs_them(tmp_path: Path) -> None:
    paths = {
        "front": "出图/共享/图片/定妆_短线角色.png",
        "outfit": "出图/共享/图片/定妆_短线角色_半身.png",
        "face": "出图/共享/图片/定妆_短线角色_脸部特写.png",
    }
    for rel in paths.values():
        write_valid_png(tmp_path / rel)
    form = {
        "form": "常态",
        "reference_group": {
            "front": {"path": paths["front"], "status": "ready"},
            "outfit": {"path": paths["outfit"], "status": "ready"},
            "face_anchor_refs": [{"path": paths["face"], "status": "ready"}],
        },
        "reference_atlas": {"build_tier": "named_minimal"},
    }

    assert codex_image_runner._character_basic_pack_issues(tmp_path, "CHAR_GUEST", form, "普通中景站立") == []
    closeup = codex_image_runner._character_basic_pack_issues(tmp_path, "CHAR_GUEST", form, "CU 近景反打")
    assert closeup and "three_quarter" in closeup[0]
    back_view = codex_image_runner._character_basic_pack_issues(tmp_path, "CHAR_GUEST", form, "背身离开")
    assert back_view and "back" in back_view[0]


def test_shared_target_skips_existing_png_without_force(tmp_path: Path, monkeypatch) -> None:
    final = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png"
    final.parent.mkdir(parents=True)
    final.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    registry.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_01",
                        "forms": [
                            {
                                "form": "常态",
                                "reference_group": {
                                    "front": {
                                        "path": "出图/共享/图片/定妆_沈念_常态.png",
                                        "status": "planned",
                                    }
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## CHAR_01 沈念",
        body="角色定妆",
        target_line="`出图/共享/图片/定妆_沈念_常态.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_01::定妆_沈念_常态",
        clip="CHAR_01",
        mode="shared",
        rel_path="出图/共享/图片/定妆_沈念_常态.png",
        section=section,
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("existing shared PNG should not call Codex")

    monkeypatch.setattr(codex_image_runner, "run_codex", fail_if_called)

    assert codex_image_runner.process_target(
        tmp_path,
        "第1集",
        target,
        task_id="new-task",
        timeout_sec=1,
        dry_run=False,
        force=False,
    )
    data = json.loads(registry.read_text(encoding="utf-8"))
    front = data["characters"][0]["forms"][0]["reference_group"]["front"]
    assert front["status"] == "review_pending"
    assert front["human_review"]["status"] == "pending"


def test_codex_blocks_text_only_character_split_makeup(tmp_path: Path, monkeypatch) -> None:
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## CHAR_01 沈念",
        body="角色定妆",
        target_line="`出图/共享/图片/CHAR_SHENNIAN_常态_45度.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_01::CHAR_SHENNIAN_常态_45度",
        clip="CHAR_01",
        mode="shared",
        rel_path="出图/共享/图片/CHAR_SHENNIAN_常态_45度.png",
        section=section,
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("text-only Codex must not generate split makeup refs")

    monkeypatch.setattr(codex_image_runner, "run_codex", fail_if_called)
    monkeypatch.delenv("N2D_ALLOW_CODEX_TEXT_MAKEUP_VARIANTS", raising=False)

    assert not codex_image_runner.process_target(
        tmp_path,
        "第1集",
        target,
        task_id="guard-test",
        timeout_sec=1,
        dry_run=False,
        force=False,
    )


def test_chinese_front_ref_allows_character_split_makeup() -> None:
    assert codex_image_runner.has_controlled_makeup_source(
        "出图/共享/图片/定妆_CHAR_SHEN_YAN__常态_45度.png",
        [{"rel_path": "出图/共享/图片/定妆_CHAR_SHEN_YAN__常态_正面.png"}],
    )


def test_shared_split_makeup_inputs_auto_include_same_source_parent(tmp_path: Path) -> None:
    parent = tmp_path / "出图" / "共享" / "图片" / "定妆_CHAR_WANG_DUN__常态.png"
    write_valid_png(parent)
    section = codex_image_runner.ClipSection(
        clip="CHAR_WANG_DUN",
        title="## 王敦（`CHAR_WANG_DUN/常态`）",
        body="## 王敦\n**目标存档**：`出图/共享/图片/定妆_CHAR_WANG_DUN__常态_45度.png`\n",
        target_line="`出图/共享/图片/定妆_CHAR_WANG_DUN__常态_45度.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_WANG_DUN::定妆_CHAR_WANG_DUN__常态_45度",
        clip="CHAR_WANG_DUN",
        mode="shared",
        rel_path="出图/共享/图片/定妆_CHAR_WANG_DUN__常态_45度.png",
        section=section,
    )

    inputs = codex_image_runner.codex_reference_inputs_for_target(
        tmp_path, "第1集", target, {"items": []}
    )

    assert inputs
    assert inputs[0]["rel_path"] == "出图/共享/图片/定妆_CHAR_WANG_DUN__常态.png"
    assert inputs[0]["source"] == "same_source_makeup_parent"
    assert codex_image_runner.has_controlled_makeup_source(target.rel_path, inputs)


def test_shared_turnaround_inputs_auto_include_same_source_views(tmp_path: Path) -> None:
    for suffix in ("", "_45度", "_侧", "_背", "_半身"):
        write_valid_png(
            tmp_path
            / "出图"
            / "共享"
            / "图片"
            / f"定妆_CHAR_WANG_DUN__常态{suffix}.png"
        )
    section = codex_image_runner.ClipSection(
        clip="CHAR_WANG_DUN",
        title="## 王敦（`CHAR_WANG_DUN/常态`）",
        body="## 王敦\n**目标存档**：`出图/共享/图片/定妆_CHAR_WANG_DUN__常态_三视图.png`\n",
        target_line="`出图/共享/图片/定妆_CHAR_WANG_DUN__常态_三视图.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_WANG_DUN::定妆_CHAR_WANG_DUN__常态_三视图",
        clip="CHAR_WANG_DUN",
        mode="shared",
        rel_path="出图/共享/图片/定妆_CHAR_WANG_DUN__常态_三视图.png",
        section=section,
    )

    inputs = codex_image_runner.codex_reference_inputs_for_target(
        tmp_path, "第1集", target, {"items": []}
    )
    rels = [item["rel_path"] for item in inputs]

    assert codex_image_runner.requires_controlled_makeup_derivation(target.rel_path)
    assert codex_image_runner.has_controlled_makeup_source(target.rel_path, inputs)
    assert codex_image_runner.requires_human_review_before_ready(target.rel_path)
    assert rels[:5] == [
        "出图/共享/图片/定妆_CHAR_WANG_DUN__常态.png",
        "出图/共享/图片/定妆_CHAR_WANG_DUN__常态_45度.png",
        "出图/共享/图片/定妆_CHAR_WANG_DUN__常态_侧.png",
        "出图/共享/图片/定妆_CHAR_WANG_DUN__常态_背.png",
        "出图/共享/图片/定妆_CHAR_WANG_DUN__常态_半身.png",
    ]


def test_shared_turnaround_with_front_and_face_anchor_uses_minimal_identity_payload(
    tmp_path: Path,
) -> None:
    base = "出图/共享/图片/定妆_CHAR_01__常态"
    refs = [
        f"{base}.png",
        f"{base}_半身.png",
        f"{base}_脸部特写_脸锚裁切.png",
        "出图/共享/图片/风格锚.png",
    ]
    for rel in refs:
        write_valid_png(tmp_path / rel)
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## 姜月初（`CHAR_01/常态`）",
        body="## 姜月初\n**目标存档**：`出图/共享/图片/定妆_CHAR_01__常态_三视图.png`\n",
        target_line="`出图/共享/图片/定妆_CHAR_01__常态_三视图.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_01::定妆_CHAR_01__常态_三视图",
        clip="CHAR_01",
        mode="shared",
        rel_path="出图/共享/图片/定妆_CHAR_01__常态_三视图.png",
        section=section,
    )
    bundle = {
        "items": [
            {"kind": "character", "id": "CHAR_01", "form": "常态", "paths": refs[:3]},
            {"kind": "style", "id": "STYLE_ANCHOR", "paths": refs[3:]},
        ]
    }

    inputs = codex_image_runner.codex_reference_inputs_for_target(
        tmp_path, "第1集", target, bundle
    )

    assert [item["rel_path"] for item in inputs] == [refs[0], refs[2]]
    assert inputs[0]["role"] in {"character", "source_frame"}
    assert inputs[1]["role"] == "character"


def test_reference_bundle_resolves_ready_character_and_asset_refs(tmp_path: Path) -> None:
    ref = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    prop = tmp_path / "出图" / "共享" / "图片" / "定妆_毒酒瓷瓶.png"
    prop.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
                "characters": [{
                    "id": "CHAR_01",
                    "forms": [{
                    "form": "常态",
                    "reference_group": {
                        "front": {"path": "出图/共享/图片/定妆_沈念_常态.png", "status": "ready"}
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text(
        json.dumps({
            "assets": [{
                "id": "PROP_01",
                "type": "prop",
                "reference_group": {"primary": {"path": "出图/共享/图片/定妆_毒酒瓷瓶.png", "status": "ready"}},
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body=(
            "**资产身份注册层**：`CHAR_01/常态*` -> identity_registry.json；"
            "`PROP_01` -> asset_registry.json。\n"
            "**参考图**：角色 `CHAR_01/常态`，道具 `PROP_01`。\n"
            "角色 CU 特写，手持道具。"
        ),
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert bundle["true_image_reference_support"] is True
    assert bundle["reference_input_mode"] == "codex_exec_image_flags"
    assert {item["kind"] for item in bundle["items"]} == {"character", "asset"}
    assert any("定妆_沈念_常态.png" in p for item in bundle["items"] for p in item["paths"])
    assert any("定妆_毒酒瓷瓶.png" in p for item in bundle["items"] for p in item["paths"])

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)
    codex_image_runner.attach_reference_inputs(bundle, inputs)
    cmd = codex_image_runner.build_codex_command(tmp_path, "prompt", inputs)

    assert bundle["cli_image_input_count"] == 2
    assert len(inputs) == 2
    assert "--image" in cmd
    assert any(str(ref) in part for part in cmd)
    assert any(str(prop) in part for part in cmd)
    assert inputs[0]["role"] == "character"


def test_reference_inputs_prioritize_character_identity_before_assets(tmp_path: Path) -> None:
    face_rel = "出图/共享/图片/定妆_沈念_常态_脸部特写.png"
    half_rel = "出图/共享/图片/定妆_沈念_常态_半身.png"
    style_rel = "出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png"
    prop_rel = "出图/共享/图片/PROP_TEST_瓷瓶.png"
    scene_rel = "出图/共享/图片/LOC_TEST_院落.png"
    for rel in (face_rel, half_rel, style_rel, prop_rel, scene_rel):
        write_valid_png(tmp_path / rel)
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="**目标**：`出图/第1集/图片/Clip_01.png`\n角色手持道具在院落中。",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )
    bundle = {
        "items": [
            {"kind": "asset", "id": "PROP_TEST", "paths": [prop_rel]},
            {"kind": "asset", "id": "LOC_TEST", "paths": [scene_rel]},
            {"kind": "style", "id": "STYLE_ANCHOR", "paths": [style_rel]},
            {"kind": "character", "id": "CHAR_01", "form": "常态", "paths": [half_rel, face_rel]},
        ]
    }

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert [item["rel_path"] for item in inputs] == [
        face_rel,
        half_rel,
        style_rel,
        prop_rel,
        scene_rel,
    ]


def test_reference_inputs_cap_character_variants_per_owner(tmp_path: Path) -> None:
    refs = [
        "出图/共享/图片/定妆_沈念_常态_脸部特写.png",
        "出图/共享/图片/定妆_沈念_常态_半身.png",
        "出图/共享/图片/定妆_沈念_常态.png",
        "出图/共享/图片/定妆_沈念_常态_表情_警觉.png",
        "出图/共享/图片/定妆_沈念_常态_表情_克制.png",
        "出图/共享/图片/定妆_沈念_常态_侧.png",
    ]
    prop_rel = "出图/共享/图片/PROP_TEST_瓷瓶.png"
    for rel in (*refs, prop_rel):
        write_valid_png(tmp_path / rel)
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="**目标**：`出图/第1集/图片/Clip_01.png`\n角色手持道具。",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )
    bundle = {
        "items": [
            {"kind": "character", "id": "CHAR_01", "form": "常态", "paths": refs},
            {"kind": "asset", "id": "PROP_TEST", "paths": [prop_rel]},
        ]
    }

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)
    paths = [item["rel_path"] for item in inputs]

    assert paths == [*refs[:4], prop_rel]
    assert refs[4] not in paths
    assert refs[5] not in paths


def test_shared_reference_inputs_include_project_style_anchor(tmp_path: Path) -> None:
    style_rel = "出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png"
    write_valid_png(tmp_path / style_rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "style_anchor_registry.json").write_text(
        json.dumps({
            "kind": "n2d_style_anchor_registry",
            "selected_anchor": {
                "path": style_rel,
                "status": "ready",
                "use_policy": "style_only",
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{"form": "常态", "reference_group": {}}],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    rel = "出图/共享/图片/定妆_沈念_常态.png"
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## CHAR_01 沈念",
        body=f"**目标存档**：`{rel}`\n角色定妆。",
        target_line=f"`{rel}`",
    )
    target = codex_image_runner.Target("CHAR_01::定妆_沈念_常态", "CHAR_01", "shared", rel, section)
    target.aliases = {"CHAR_01", "CHAR_01/常态"}

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)
    prompt = codex_image_runner.build_codex_prompt(
        tmp_path, "第1集", target, tmp_path / "out.png", "seed-1", bundle
    )

    assert any(item["kind"] == "style" for item in bundle["items"])
    assert inputs[0]["role"] == "style"
    assert inputs[0]["rel_path"] == style_rel
    assert "统一规格的定妆参考板" in prompt
    assert "不得继承风格锚里的具体人物身份" in prompt


def test_character_reference_overrides_duplicate_style_anchor_input(tmp_path: Path) -> None:
    style_rel = "出图/共享/图片/CHAR_01_定型参考.png"
    write_valid_png(tmp_path / style_rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "style_anchor_registry.json").write_text(
        json.dumps({
            "kind": "n2d_style_anchor_registry",
            "selected_anchor": {
                "path": style_rel,
                "status": "ready",
                "use_policy": "style_only",
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "external_visual_references": [{
                    "path": style_rel,
                    "sha256": codex_image_runner.file_sha256(tmp_path / style_rel),
                    "status": "ready",
                    "use_policy": "identity_reference",
                    "rights_status": "user_owned",
                    "eligible_for_generation": True,
                    "backend_upload_allowed": True,
                    "watermark_present": False,
                }],
                "forms": [{"form": "常态", "reference_group": {}}],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    rel = "出图/共享/图片/定妆_沈念_常态.png"
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## CHAR_01 沈念",
        body=f"**目标存档**：`{rel}`\n角色定妆。",
        target_line=f"`{rel}`",
    )
    target = codex_image_runner.Target("CHAR_01::定妆_沈念_常态", "CHAR_01", "shared", rel, section)
    target.aliases = {"CHAR_01", "CHAR_01/常态"}

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert inputs[0]["rel_path"] == style_rel
    assert inputs[0]["role"] == "character"
    assert inputs[0]["owner"] == "CHAR_01/常态"
    assert inputs[0]["upgraded_from_style_anchor"] is True


def test_style_anchor_registry_uses_selected_anchor_before_anchor_list(tmp_path: Path) -> None:
    selected_rel = "出图/共享/图片/STYLE_SELECTED.png"
    extra_rel = "出图/共享/图片/STYLE_EXTRA.png"
    write_valid_png(tmp_path / selected_rel)
    write_valid_png(tmp_path / extra_rel)
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "style_anchor_registry.json").write_text(
        json.dumps({
            "kind": "n2d_style_anchor_registry",
            "selected_anchor": {"path": selected_rel, "status": "ready"},
            "anchors": [
                {"path": selected_rel, "status": "ready"},
                {"path": extra_rel, "status": "ready"},
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    assert codex_image_runner.load_style_anchor_paths(tmp_path) == [selected_rel]


def test_shared_prop_board_guidance_blocks_people_for_primary_prop() -> None:
    section = codex_image_runner.ClipSection("PROP_TEST", "## PROP_TEST", "", "")
    target = codex_image_runner.Target(
        "PROP_TEST::定妆_道具_木扁担",
        "PROP_TEST",
        "shared",
        "出图/共享/图片/定妆_道具_木扁担.png",
        section,
    )
    target.aliases = {"PROP_TEST"}

    guidance = codex_image_runner.shared_prop_board_guidance(target)

    assert "只画干净物件本体" in guidance
    assert "禁止人物、手、肩膀" in guidance


def test_shared_prop_board_guidance_allows_faceless_scale_for_variant() -> None:
    section = codex_image_runner.ClipSection("PROP_TEST", "## PROP_TEST", "", "")
    target = codex_image_runner.Target(
        "PROP_TEST::定妆_道具_木扁担_手持",
        "PROP_TEST",
        "shared",
        "出图/共享/图片/定妆_道具_木扁担_手持.png",
        section,
    )
    target.aliases = {"PROP_TEST"}

    guidance = codex_image_runner.shared_prop_board_guidance(target)

    assert "可以出现无脸手部" in guidance
    assert "只画干净物件本体" not in guidance


def test_shared_prop_variant_attaches_primary_prop_parent(tmp_path: Path) -> None:
    rel = "出图/共享/图片/定妆_道具_木牌.png"
    parent = tmp_path / rel
    parent.parent.mkdir(parents=True)
    parent.write_bytes(b"approved-prop-primary")
    section = codex_image_runner.ClipSection("PROP_TEST", "## PROP_TEST", "", "")
    target = codex_image_runner.Target(
        "PROP_TEST::定妆_道具_木牌_比例",
        "PROP_TEST",
        "shared",
        "出图/共享/图片/定妆_道具_木牌_比例.png",
        section,
    )
    target.aliases = {"PROP_TEST"}

    inputs = codex_image_runner.codex_reference_inputs_for_target(
        tmp_path, "第1集", target, {"items": []}
    )

    assert [item["rel_path"] for item in inputs] == [rel]
    assert inputs[0]["role"] == "asset"
    assert inputs[0]["source"] == "same_prop_primary_parent"


def test_style_anchor_target_marks_registry_ready(tmp_path: Path) -> None:
    rel = "出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png"

    codex_image_runner.mark_style_anchor_ready(tmp_path, rel)

    data = json.loads((tmp_path / "出图" / "共享" / "style_anchor_registry.json").read_text(encoding="utf-8"))
    assert data["selected_anchor"]["path"] == rel
    assert data["selected_anchor"]["status"] == "ready"
    assert data["selected_anchor"]["use_policy"] == "style_only"


def test_shared_first_interlock_requires_ready_style_anchor_for_clip_spending(tmp_path: Path) -> None:
    prompt = tmp_path / "出图" / "第1集" / "prompt"
    prompt.mkdir(parents=True)
    (prompt / "01_分镜出图.md").write_text(
        "## Clip 01 起势\n"
        "**目标落档**：`出图/第1集/图片/Clip01_first.png`\n"
        "**参考图**：无人物。\n",
        encoding="utf-8",
    )
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")

    issues = codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集")
    assert any("风格锚" in issue for issue in issues)

    rel = "出图/共享/图片/风格锚_国漫写实.png"
    write_valid_png(tmp_path / rel)
    codex_image_runner.mark_style_anchor_ready(tmp_path, rel)
    issues = codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集")
    assert not any("风格锚" in issue for issue in issues)


def test_reference_bundle_prefers_form_qualified_refs_over_bare_character_id(tmp_path: Path) -> None:
    battle = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_战场形态.png"
    awakening = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_觉醒态.png"
    write_valid_png(battle)
    write_valid_png(awakening)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [
                    {
                        "form": "战场形态",
                        "reference_group": {
                            "front": {"path": "出图/共享/图片/定妆_沈念_战场形态.png", "status": "ready"}
                        },
                    },
                    {
                        "form": "觉醒态",
                        "reference_group": {
                            "front": {"path": "出图/共享/图片/定妆_沈念_觉醒态.png", "status": "ready"}
                        },
                    },
                ],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## CHAR_01 战场形态",
        body="**目标存档**：`出图/共享/图片/定妆_沈念_战场形态.png`",
        target_line="`出图/共享/图片/定妆_沈念_战场形态.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_01::定妆_沈念_战场形态",
        clip="CHAR_01",
        mode="shared",
        rel_path="出图/共享/图片/定妆_沈念_战场形态.png",
        section=section,
    )
    setattr(target, "aliases", {"CHAR_01", "CHAR_01/战场形态"})

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert [item["form"] for item in bundle["items"]] == ["战场形态"]
    assert all(item["rel_path"] != target.rel_path for item in inputs)
    assert all("觉醒态" not in item["rel_path"] for item in inputs)


def _reviewed_core_form(tmp_path: Path, refs: dict[str, str], face: str) -> dict:
    form_name = "常态"

    def reviewed(view: str, rel: str) -> dict:
        sha = codex_image_runner.file_sha256(tmp_path / rel)
        return {
            "path": rel,
            "status": "ready",
            "sha256": sha,
            "human_review": {
                "status": "accepted",
                "verdict": "pass",
                "character_id": "CHAR_01",
                "form": form_name,
                "library_tier": "core_full",
                "view": view,
                "path": rel,
                "reviewer": "art-director",
                "reviewed_at": "2026-07-14T12:00:00+00:00",
                "png_sha256": sha,
                "registry_binding_fingerprint": codex_image_runner.core_review_binding_fingerprint(
                    "CHAR_01", form_name, "core_full", view, rel, sha
                ),
                "registry_binding_fingerprint_kind": codex_image_runner.IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND,
                "review_contract": codex_image_runner.identity_review_contract_for_view(view),
                "criteria": sorted(codex_image_runner.identity_review_required_criteria(view)),
                "confirmation": {
                    "kind": "explicit_current_pixels_acceptance",
                    "accepted_current_pixels": True,
                },
            },
        }

    reference_group = {
        key: (reviewed(key, rel) if key in codex_image_runner.CHARACTER_SHARED_CORE_FIELDS else {
            "path": rel, "status": "ready",
        })
        for key, rel in refs.items()
    }
    reference_group["face_anchor_refs"] = [reviewed("expression", face)]
    return {
        "form": form_name,
        "self_check_passed": True,
        "reference_group": reference_group,
        "reference_atlas": {"build_tier": "core_full"},
    }


def test_shared_first_interlock_blocks_incomplete_character_pack(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip_01.png`\n"
        "**资产身份注册层**：`CHAR_01/常态*` -> identity_registry.json。\n"
        "**参考图**：角色 `CHAR_01/常态`。\n",
    )
    write_valid_png(tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png")
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "scope": "贯穿全篇女主",
                "library_tier": "core_full",
                "forms": [{
                    "form": "常态",
                    "self_check_passed": True,
                    "reference_group": {
                        "front": {"path": "出图/共享/图片/定妆_沈念_常态.png", "status": "ready"}
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")

    issues = codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集")

    assert issues
    assert any("共享定妆分档基础包未齐" in issue for issue in issues)
    assert any("three_quarter" in issue and "禁止生成 Clip 分镜图" in issue for issue in issues)


def test_shared_first_interlock_passes_when_character_pack_complete(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip_01.png`\n"
        "**资产身份注册层**：`CHAR_01/常态*` -> identity_registry.json。\n"
        "**参考图**：角色 `CHAR_01/常态`。\n",
    )
    refs = {
        "front": "出图/共享/图片/定妆_沈念_常态.png",
            "three_quarter": "出图/共享/图片/定妆_沈念_常态_45度.png",
            "side": "出图/共享/图片/定妆_沈念_常态_侧.png",
            "rear_three_quarter": "出图/共享/图片/定妆_沈念_常态_后45度.png",
            "back": "出图/共享/图片/定妆_沈念_常态_背.png",
        "turnaround": "出图/共享/图片/定妆_沈念_常态_三视图.png",
        "half_body": "出图/共享/图片/定妆_沈念_常态_半身.png",
    }
    for index, rel in enumerate(refs.values(), start=1):
        write_valid_png(tmp_path / rel, fill=bytes([index]))
    face = "出图/共享/图片/定妆_沈念_常态_脸部特写.png"
    write_valid_png(tmp_path / face, fill=b"\x80")
    style_anchor = "出图/共享/图片/风格锚_国漫写实.png"
    write_valid_png(tmp_path / style_anchor)
    codex_image_runner.mark_style_anchor_ready(tmp_path, style_anchor)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [_reviewed_core_form(tmp_path, refs, face)],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")

    assert codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集") == []

    registry_path = shared / "identity_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    form = registry["characters"][0]["forms"][0]
    form["reference_group"]["front"]["human_review"]["reviewer"] = "codex-agent"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    forged_reviewer = codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集")
    assert any("current_hash_review_receipts:front" in issue for issue in forged_reviewer)

    form["reference_group"]["front"]["human_review"]["reviewer"] = "art-director"
    form["reference_group"]["face_anchor_refs"][0]["human_review"]["criteria"] = []
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    forged_criteria = codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集")
    assert any("current_hash_review_receipts:expression" in issue for issue in forged_criteria)

    form["reference_group"]["face_anchor_refs"][0]["human_review"]["criteria"] = sorted(
        codex_image_runner.identity_review_required_criteria("expression")
    )
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    assert codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集") == []

    # `--skip-preflight` 只能跳过广义 dashboard gate，不能绕过逐视图当前 hash 收据。
    write_valid_png(tmp_path / refs["rear_three_quarter"], fill=b"1")
    stale = codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集")
    assert any("current_hash_review_receipts:rear_three_quarter" in issue for issue in stale)


def test_shared_first_interlock_accepts_authorized_executor_visual_receipts(tmp_path: Path) -> None:
    refs = {
        view: f"出图/共享/图片/{view}.png"
        for view in codex_image_runner.CHARACTER_SHARED_CORE_FIELDS
    }
    for index, rel in enumerate(refs.values(), start=1):
        write_valid_png(tmp_path / rel, fill=bytes([index]))
    face = "出图/共享/图片/expression.png"
    write_valid_png(tmp_path / face, fill=b"\x80")
    form = _reviewed_core_form(tmp_path, refs, face)

    for item in list(form["reference_group"].values()):
        rows = item if isinstance(item, list) else [item]
        for row in rows:
            if not isinstance(row, dict) or "human_review" not in row:
                continue
            receipt = row.pop("human_review")
            receipt.update({
                "reviewer": "executor:codex",
                "review_kind": "executor_visual",
                "reviewer_role": "ai_visual_executor",
                "human_signoff": False,
            })
            row["visual_review"] = receipt
    (tmp_path / "_设置.md").write_text(
        "- 图片验收模式：逐张机器QC+执行者实际像素目视后再继续  # source=explicit_user；用户明确要求\n",
        encoding="utf-8",
    )

    assert codex_image_runner._core_review_receipt_issues(tmp_path, "CHAR_01", form) == []


def test_shared_first_pre_spend_duplicate_png_sha_blocks_copied_views(tmp_path: Path) -> None:
    refs = {
        view: f"出图/共享/图片/{view}.png"
        for view in codex_image_runner.CHARACTER_SHARED_CORE_FIELDS
    }
    for index, rel in enumerate(refs.values(), start=1):
        write_valid_png(tmp_path / rel, fill=bytes([index]))
    # A byte-for-byte copy under a different filename must still fail.
    (tmp_path / refs["back"]).write_bytes((tmp_path / refs["side"]).read_bytes())
    face = "出图/共享/图片/expression.png"
    write_valid_png(tmp_path / face, fill=b"\x80")
    form = _reviewed_core_form(tmp_path, refs, face)

    issues = codex_image_runner._core_review_receipt_issues(tmp_path, "CHAR_01", form)

    assert any(item.startswith("duplicate_png_sha:back/side") for item in issues)
    assert not any(item.startswith("duplicate_canonical_realpath") for item in issues)


@pytest.mark.parametrize("mode", ["absolute", "path_escape", "symlink", "noncanonical"])
def test_shared_first_pre_spend_path_escape_symlink_and_noncanonical_are_blocked(
    tmp_path: Path,
    mode: str,
) -> None:
    refs = {
        view: f"出图/共享/图片/{view}.png"
        for view in codex_image_runner.CHARACTER_SHARED_CORE_FIELDS
    }
    for index, rel in enumerate(refs.values(), start=1):
        write_valid_png(tmp_path / rel, fill=bytes([index]))
    face = "出图/共享/图片/expression.png"
    write_valid_png(tmp_path / face, fill=b"\x80")
    form = _reviewed_core_form(tmp_path, refs, face)
    front = form["reference_group"]["front"]
    if mode == "absolute":
        front["path"] = str((tmp_path / refs["front"]).resolve())
        expected = "absolute_registry_evidence_path_not_allowed"
    elif mode == "path_escape":
        outside = tmp_path.parent / f"{tmp_path.name}_outside.png"
        write_valid_png(outside, fill=b"\x91")
        front["path"] = f"../{outside.name}"
        expected = "registry_evidence_path_outside_project_root"
    elif mode == "symlink":
        link = tmp_path / "出图" / "共享" / "图片" / "front_link.png"
        link.symlink_to(Path(refs["front"]).name)
        front["path"] = "出图/共享/图片/front_link.png"
        expected = "registry_evidence_path_not_canonical_project_relative"
    else:
        front["path"] = "出图/共享/图片/../图片/front.png"
        expected = "registry_evidence_path_not_canonical_project_relative"

    issues = codex_image_runner._core_review_receipt_issues(tmp_path, "CHAR_01", form)

    assert any(expected in item for item in issues)


def test_shared_first_interlock_ignores_char_ids_inside_makeup_filenames(tmp_path: Path) -> None:
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip_01.png`\n"
        "**角色身份注册层**：`CHAR_01/常态*` -> identity_registry.json。\n"
        "**参考图**：角色参考 `定妆_CHAR_01_HUMAN_脸部特写.png` 强度0.8。\n",
    )
    refs = {
        "front": "出图/共享/图片/定妆_沈念_常态.png",
            "three_quarter": "出图/共享/图片/定妆_沈念_常态_45度.png",
            "side": "出图/共享/图片/定妆_沈念_常态_侧.png",
            "rear_three_quarter": "出图/共享/图片/定妆_沈念_常态_后45度.png",
            "back": "出图/共享/图片/定妆_沈念_常态_背.png",
        "turnaround": "出图/共享/图片/定妆_沈念_常态_三视图.png",
        "half_body": "出图/共享/图片/定妆_沈念_常态_半身.png",
    }
    for index, rel in enumerate(refs.values(), start=1):
        write_valid_png(tmp_path / rel, fill=bytes([index]))
    face = "出图/共享/图片/定妆_CHAR_01_HUMAN_脸部特写.png"
    write_valid_png(tmp_path / face, fill=b"\x80")
    style_anchor = "出图/共享/图片/风格锚_国漫写实.png"
    write_valid_png(tmp_path / style_anchor)
    codex_image_runner.mark_style_anchor_ready(tmp_path, style_anchor)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [_reviewed_core_form(tmp_path, refs, face)],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")

    assert codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集") == []


def test_shared_image_paths_from_text_ignores_placeholder_makeup_paths() -> None:
    text = (
        "使用 `定妆_<角色>_脸部特写.png` 作为模板说明；"
        "真实参考 `定妆_CHAR_01_HUMAN_脸部特写.png`。"
    )
    assert codex_image_runner.shared_image_paths_from_text(text) == [
        "出图/共享/图片/定妆_CHAR_01_HUMAN_脸部特写.png"
    ]


def test_main_skip_preflight_cannot_bypass_shared_first_interlock(tmp_path: Path, monkeypatch) -> None:
    write_prompt(
        tmp_path,
        "## Clip_01\n"
        "**目标**：`出图/第1集/图片/Clip_01.png`\n"
        "**资产身份注册层**：`CHAR_01/常态*` -> identity_registry.json。\n"
        "**参考图**：角色 `CHAR_01/常态`。\n",
    )
    write_valid_png(tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png")
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{
                    "form": "常态",
                    "reference_group": {
                        "front": {"path": "出图/共享/图片/定妆_沈念_常态.png", "status": "ready"}
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Clip generation was called before shared library completion")

    monkeypatch.setattr(codex_image_runner, "process_target", fail_if_called)
    monkeypatch.setattr(codex_image_runner, "record_waiver", lambda *args, **kwargs: None)

    assert codex_image_runner.main([
        str(tmp_path),
        "第1集",
        "--shots",
        "Clip_01",
        "--skip-preflight",
    ]) == 1


def test_reference_bundle_does_not_attach_pending_rights_external_reference_or_lineage(tmp_path: Path) -> None:
    active = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png"
    active.parent.mkdir(parents=True)
    active.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    lineage = tmp_path / "设定库" / "reference_images" / "user_ref.jpg"
    lineage.parent.mkdir(parents=True)
    lineage.write_bytes(b"\xff\xd8\xff" + b"0" * 64)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "external_visual_references": [{
                    "path": "设定库/reference_images/user_ref.jpg",
                    "sha256": codex_image_runner.file_sha256(lineage),
                    "status": "accepted_for_internal_generation_pending_rights_review",
                    "use_policy": "identity_reference",
                    "rights_status": "authorized",
                    "eligible_for_generation": True,
                    "backend_upload_allowed": True,
                    "watermark_present": False,
                }],
                "forms": [{
                    "form": "常态",
                    "reference_group": {
                        "front": {
                            "path": "出图/共享/图片/定妆_沈念_常态.png",
                            "status": "ready",
                            "source_refs": ["设定库/reference_images/user_ref.jpg"],
                        },
                        "side": {
                            "path": "出图/共享/图片/定妆_沈念_常态_侧.png",
                            "status": "planned",
                            "source_image": "出图/共享/图片/定妆_沈念_常态.png",
                        },
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## CHAR_01 沈念",
        body="**目标存档**：`出图/共享/图片/定妆_沈念_常态_侧.png`",
        target_line="`出图/共享/图片/定妆_沈念_常态_侧.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_01::定妆_沈念_常态_侧",
        clip="CHAR_01",
        mode="shared",
        rel_path="出图/共享/图片/定妆_沈念_常态_侧.png",
        section=section,
    )
    setattr(target, "aliases", {"CHAR_01", "CHAR_01/常态"})

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert [item["rel_path"] for item in inputs] == ["出图/共享/图片/定妆_沈念_常态.png"]


def test_reference_bundle_resolves_chinese_asset_id_from_prompt_contract(tmp_path: Path) -> None:
    prop = tmp_path / "出图" / "共享" / "图片" / "定妆_急报卷轴.png"
    prop.parent.mkdir(parents=True)
    prop.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (shared / "asset_registry.json").write_text(
        json.dumps({
            "assets": [{
                "id": "PROP_急报卷轴",
                "type": "prop",
                "reference_group": {"primary": {"path": "出图/共享/图片/定妆_急报卷轴.png", "status": "ready"}},
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_05",
        title="## Clip 05",
        body=(
            "- 参考图入参清单：selected `出图/共享/图片/定妆_急报卷轴.png`。\n"
            "- 资产引用注册层：`PROP_急报卷轴`。\n"
            "急报卷轴压在案几上。\n"
        ),
        target_line="`出图/第1集/图片/Clip_05.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_05",
        clip="Clip_05",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_05.png",
        section=section,
    )

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)
    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert bundle["items"][0]["id"] == "PROP_急报卷轴"
    assert inputs[0]["rel_path"] == "出图/共享/图片/定妆_急报卷轴.png"


def _write_carried_identity_fixtures(tmp_path: Path, asset: dict) -> codex_image_runner.Target:
    """Shared fixture: a locked 沈念 face anchor + a VFX asset that depicts her."""
    face = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_脸部特写.png"
    face.parent.mkdir(parents=True)
    face.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{
                    "form": "冷宫废妃常态",
                    "reference_group": {
                        "face_anchor_refs": [
                            {"path": "出图/共享/图片/定妆_沈念_脸部特写.png", "status": "ready"}
                        ]
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text(
        json.dumps({"assets": [asset]}, ensure_ascii=False), encoding="utf-8"
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_99",
        title="## ① VFX_01 万妖血脉觉醒前兆",
        body="**目标存档**：`出图/共享/图片/定妆_万妖血脉觉醒前兆.png`\nVFX 定妆图，左腕暗金细纹。",
        target_line="`出图/共享/图片/定妆_万妖血脉觉醒前兆.png`",
    )
    target = codex_image_runner.Target(
        shot="VFX_01::定妆_万妖血脉觉醒前兆",
        clip="VFX_01",
        mode="shared",
        rel_path="出图/共享/图片/定妆_万妖血脉觉醒前兆.png",
        section=section,
    )
    setattr(target, "aliases", {"VFX_01", "万妖血脉觉醒前兆"})
    return target


def test_vfx_asset_inherits_carried_character_face_via_explicit_field(tmp_path: Path) -> None:
    target = _write_carried_identity_fixtures(tmp_path, {
        "id": "VFX_01",
        "type": "vfx",
        "name": "万妖血脉觉醒前兆",
        "carries_identity": ["CHAR_01/冷宫废妃常态"],
        "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
    })

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert bundle["carried_identity"] == ["CHAR_01/冷宫废妃常态"]
    assert any(item["kind"] == "character" and item["id"] == "CHAR_01" for item in bundle["items"])
    assert any("定妆_沈念_脸部特写.png" in p for item in bundle["items"] for p in item["paths"])

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)
    assert any(str(i.get("role")) == "character" for i in inputs)


def test_vfx_asset_infers_carried_identity_from_structure_when_field_absent(tmp_path: Path) -> None:
    # Legacy registry: no carries_identity field, but the structure text names CHAR_01.
    target = _write_carried_identity_fixtures(tmp_path, {
        "id": "VFX_01",
        "type": "vfx",
        "name": "万妖血脉觉醒前兆",
        "constraints": {"structure": "暗金细纹从 CHAR_01 左腕旧疤裂出"},
        "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
    })

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert "CHAR_01" in bundle["carried_identity"]
    assert any("定妆_沈念_脸部特写.png" in p for item in bundle["items"] for p in item["paths"])


def test_non_whitelisted_type_person_plate_infers_carried_identity(tmp_path: Path) -> None:
    # type-whitelist hole: a PROP whose type ('prop') is NOT identity-bearing, but
    # whose plate clearly renders her face (a mirror reflection), must still inherit
    # the face anchor via person-context inference.
    target = _write_carried_identity_fixtures(tmp_path, {
        "id": "PROP_09",
        "type": "prop",
        "name": "铜镜",
        "constraints": {"structure": "铜镜映出 CHAR_01 的脸，面容清冷"},
        "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
    })
    setattr(target, "aliases", {"PROP_09"})

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert "CHAR_01" in bundle["carried_identity"]
    assert any("定妆_沈念_脸部特写.png" in p for item in bundle["items"] for p in item["paths"])


def test_non_identity_asset_does_not_infer_carried_identity(tmp_path: Path) -> None:
    # A LOC plate that merely mentions a character must NOT pull a face into a room.
    target = _write_carried_identity_fixtures(tmp_path, {
        "id": "LOC_09",
        "type": "location",
        "name": "冷宫寝屋",
        "constraints": {"structure": "CHAR_01 的寝宫，空镜"},
        "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
    })
    setattr(target, "aliases", {"LOC_09", "冷宫寝屋"})

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert bundle["carried_identity"] == []
    assert all(item["kind"] != "character" for item in bundle["items"])


def test_tailframe_reference_inputs_include_first_and_midframe_sources(tmp_path: Path) -> None:
    first = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    mid = tmp_path / "出图" / "第1集" / "图片" / "Clip_01_mid.png"
    end = tmp_path / "出图" / "第1集" / "图片" / "Clip_01_end.png"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    mid.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="**资产身份注册层**：无人物。",
        target_line=(
            "`出图/第1集/图片/Clip_01.png` "
            "`出图/第1集/图片/Clip_01_mid.png` "
            "`出图/第1集/图片/Clip_01_end.png`"
        ),
    )
    target = codex_image_runner.Target(
        shot="Clip_01_end",
        clip="Clip_01",
        mode="tailframe",
        rel_path="出图/第1集/图片/Clip_01_end.png",
        section=section,
    )
    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert [item["rel_path"] for item in inputs] == [
        "出图/第1集/图片/Clip_01.png",
        "出图/第1集/图片/Clip_01_mid.png",
    ]
    assert {item["source"] for item in inputs} == {"same_clip_firstframe", "same_clip_anchor"}


def test_firstframe_reference_inputs_include_explicit_previous_clip_source(tmp_path: Path) -> None:
    source = tmp_path / "出图" / "第1集" / "图片" / "Clip_07.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    ref = tmp_path / "出图" / "共享" / "图片" / "CHAR_01.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{
                    "form": "觉醒态",
                    "reference_group": {
                        "front": {"path": "出图/共享/图片/CHAR_01.png", "status": "ready"}
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    write_prompt(
        tmp_path,
        "## Clip 07（EP01_CLIP07）\n"
        "**目标**：`出图/第1集/图片/Clip_07.png`\n\n"
        "## Clip 08（EP01_CLIP08）\n"
        "**目标**：`出图/第1集/图片/Clip_08.png`\n"
        "**生成方式**：image2image / 多图参考派生，以 Clip_07 成图或脸部特写为母图。\n"
        "**资产身份注册层**：`CHAR_01/觉醒态*` -> `identity_registry.json`。\n",
    )
    sections = codex_image_runner.load_sections(tmp_path, "第1集")
    section = codex_image_runner.section_for(sections, "Clip_08")
    target = codex_image_runner.target_for_shot("Clip_08", section, "第1集")
    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert inputs[0]["rel_path"] == "出图/第1集/图片/Clip_07.png"
    assert inputs[0]["role"] == "source_frame"
    assert inputs[0]["source"] == "explicit_source_clip"
    assert "出图/共享/图片/CHAR_01.png" in [item["rel_path"] for item in inputs]


def test_full_wingspan_makeup_derivation_accepts_same_source_refs() -> None:
    refs = [
        {"rel_path": "出图/共享/图片/定妆_CHAR_YUNLING_GOLDEN_ROC_front.png"},
        {"rel_path": "出图/共享/图片/定妆_CHAR_YUNLING_GOLDEN_ROC_三视图.png"},
    ]

    assert codex_image_runner.has_controlled_makeup_source(
        "出图/共享/图片/定妆_CHAR_YUNLING_GOLDEN_ROC_全身翼展.png",
        refs,
    )


def test_rear_three_quarter_is_controlled_derivation_with_specific_guidance() -> None:
    rel = "出图/共享/图片/定妆_沈念_常态_后45度.png"

    assert codex_image_runner.requires_controlled_makeup_derivation(rel)
    assert codex_image_runner.has_controlled_makeup_source(
        rel,
        [{"rel_path": "出图/共享/图片/定妆_沈念_常态_三视图.png"}],
    )
    guidance = codex_image_runner.shared_variant_note(rel)
    assert "后3/4" in guidance
    assert "禁止前3/4" in guidance
    assert "作为一个整体" in guidance
    assert "禁止只有头部回转" in guidance
    assert "不得画成脸颊树枝状黑线" in guidance


def test_turnaround_guidance_requires_five_angle_alignment() -> None:
    guidance = codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_沈念_常态_三视图.png"
    )

    assert "正面、前3/4、侧面、后3/4、背面五角" in guidance
    assert "脚底线" in guidance and "身体中心线" in guidance


def test_expression_sheet_uses_same_source_and_six_expression_guidance() -> None:
    rel = "出图/共享/图片/定妆_沈念_常态_表情_六联表.png"

    assert codex_image_runner.requires_controlled_makeup_derivation(rel)
    assert codex_image_runner.requires_human_review_before_ready(rel)
    assert codex_image_runner.controlled_makeup_parent_candidates(rel)[0].endswith(
        "定妆_沈念_常态.png"
    )
    guidance = codex_image_runner.shared_variant_note(rel)
    assert "2×3" in guidance
    assert all(emotion in guidance for emotion in ("冷静", "警觉", "震惊", "隐忍", "将哭", "决绝"))
    assert "不烤入文字标签" in guidance


def test_back_view_form_turnaround_is_not_misclassified_as_split_ref() -> None:
    assert not codex_image_runner.requires_controlled_makeup_derivation(
        "出图/共享/图片/定妆_江剑_背影_三视图.png"
    )
    assert not codex_image_runner.requires_controlled_makeup_derivation(
        "出图/共享/图片/定妆_江剑_背影.png"
    )
    assert codex_image_runner.requires_controlled_makeup_derivation(
        "出图/共享/图片/定妆_江剑_背影_背.png"
    )
    assert codex_image_runner.requires_controlled_makeup_derivation(
        "出图/共享/图片/定妆_江剑_背影_侧背.png"
    )
    assert codex_image_runner.requires_controlled_makeup_derivation(
        "出图/共享/图片/定妆_远景修士剪影_sheet.png"
    )

    refs = [{"rel_path": "出图/共享/图片/定妆_江剑_背影_三视图.png"}]
    assert codex_image_runner.has_controlled_makeup_source(
        "出图/共享/图片/定妆_江剑_背影_侧背.png",
        refs,
    )


def test_target_image_qc_blocks_pixel_outfit_by_default(tmp_path: Path, monkeypatch) -> None:
    target_png = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    target_png.parent.mkdir(parents=True)
    target_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "face_reference_coverage": {"missing": []},
            "checks": {
                "outfit": {"shots": [{
                    "png": "图片/Clip_01.png",
                    "verdict": "block",
                    "score": 0.49,
                    "floor": 0.69,
                }]}
            },
            "lint": {"findings": []},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    monkeypatch.setattr(codex_image_runner.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))
    assert not codex_image_runner.run_target_image_qc(tmp_path, "第1集", target)


def test_target_image_qc_allows_noface_for_non_character_target(tmp_path: Path, monkeypatch) -> None:
    target_png = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    target_png.parent.mkdir(parents=True)
    target_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "face_reference_coverage": {"missing": []},
            "checks": {
                "face": {"shots": [{
                    "png": "图片/Clip_01.png",
                    "verdict": "noface",
                }]}
            },
            "lint": {"findings": []},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    monkeypatch.setattr(codex_image_runner.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))

    assert codex_image_runner.run_target_image_qc(tmp_path, "第1集", target)


def test_target_image_qc_blocks_character_coverage_noface(tmp_path: Path, monkeypatch) -> None:
    target_png = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    target_png.parent.mkdir(parents=True)
    target_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "face_reference_coverage": {
                "missing": [{
                    "png": "图片/Clip_01.png",
                    "reason": "face_verdict_noface",
                }]
            },
            "checks": {
                "face": {"shots": [{
                    "png": "图片/Clip_01.png",
                    "verdict": "noface",
                }]}
            },
            "lint": {"findings": []},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    monkeypatch.setattr(codex_image_runner.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))

    assert not codex_image_runner.run_target_image_qc(tmp_path, "第1集", target)


def test_target_image_qc_blocks_unconfirmed_current_pixel_prop_review(tmp_path: Path, monkeypatch) -> None:
    target_png = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    target_png.parent.mkdir(parents=True)
    target_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "face_reference_coverage": {"missing": []},
            "checks": {},
            "prop_shape_review": {"targets": [{
                "png": "图片/Clip_01.png",
                "asset": "VFX_双眼墨虎",
                "confirmed": False,
            }]},
            "lint": {"findings": []},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    monkeypatch.setattr(
        codex_image_runner.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""),
    )

    assert not codex_image_runner.run_target_image_qc(tmp_path, "第1集", target)


def test_target_image_qc_can_strictly_block_pixel_outfit(tmp_path: Path, monkeypatch) -> None:
    target_png = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    target_png.parent.mkdir(parents=True)
    target_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "face_reference_coverage": {"missing": []},
            "checks": {
                "outfit": {"shots": [{
                    "png": "图片/Clip_01.png",
                    "verdict": "block",
                    "score": 0.49,
                    "floor": 0.69,
                }]}
            },
            "lint": {"findings": []},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    monkeypatch.setattr(codex_image_runner.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))
    monkeypatch.setenv("N2D_TARGET_QC_STRICT_PIXEL", "1")

    assert not codex_image_runner.run_target_image_qc(tmp_path, "第1集", target)


def test_codex_high_risk_character_shot_passes_auditable_image_inputs(tmp_path: Path, monkeypatch) -> None:
    ref = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    other_ref = tmp_path / "出图" / "共享" / "图片" / "定妆_小禾_常态.png"
    other_ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({
            "characters": [
                {
                    "id": "CHAR_01",
                    "forms": [{
                        "form": "常态",
                        "reference_group": {
                            "front": {"path": "出图/共享/图片/定妆_沈念_常态.png", "status": "ready"}
                        },
                    }],
                },
                {
                    "id": "CHAR_02",
                    "forms": [{
                        "form": "常态",
                        "reference_group": {
                            "front": {"path": "出图/共享/图片/定妆_小禾_常态.png", "status": "ready"}
                        },
                    }],
                },
            ]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body=(
            "**资产身份注册层**：`CHAR_01/常态*` -> identity_registry.json。\n"
            "`CHAR_01/常态` CU 面部特写，惊恐落泪。\n"
            "**尾帧专用重抽提示**：本镜不生成 `CHAR_02/常态`。"
        ),
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    seen = {}

    def fake_run_codex(repo, prompt, timeout_sec, reference_inputs):
        seen["reference_inputs"] = list(reference_inputs)
        raw = b"\x89PNG\r\n\x1a\n" + b"2" * 64
        payload = base64.b64encode(raw).decode("ascii")
        stdout = json.dumps({"payload": {"type": "image_generation_end", "result": payload}})
        return subprocess.CompletedProcess(["codex"], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(codex_image_runner, "run_codex", fake_run_codex)

    assert codex_image_runner.process_target(
        tmp_path,
        "第1集",
        target,
        task_id="risk-test",
        timeout_sec=1,
        dry_run=False,
        force=False,
    )
    assert len(seen["reference_inputs"]) == 1
    assert seen["reference_inputs"][0]["rel_path"] == "出图/共享/图片/定妆_沈念_常态.png"

    final = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    assert codex_image_runner.png_valid(final)
    assert (
        tmp_path
        / "生产数据"
        / "codex_reference_bundles"
        / "第1集"
        / "Clip_01.json"
    ).is_file()
    manifest = json.loads((
        tmp_path
        / "生产数据"
        / "codex_reference_bundles"
        / "第1集"
        / "Clip_01.json"
    ).read_text(encoding="utf-8"))
    assert manifest["cli_image_input_count"] == 1
    assert manifest["cli_image_inputs"][0]["rel_path"] == "出图/共享/图片/定妆_沈念_常态.png"


# ── 人物脸一致性铁律：face_policy 解析 + owner-aware 承载脸锚 ──
import codex_image_runner as _rfp


def test_face_policy_faceless_for_scale_plate():
    a = {"id": "WEAPON_H", "type": "weapon", "owner": "CHAR_J", "name": "戟",
         "reference_group": {"scale_reference": "图片/定妆_WEAPON_H_握持比例.png"}}
    assert _rfp.resolve_face_policy(a) == "faceless"
    assert _rfp._asset_carried_identities(a) == []   # faceless 不折脸锚


def test_face_policy_face_locked_folds_owner():
    a = {"id": "WEAPON_X", "type": "weapon", "owner": "CHAR_JIANG_YUECHU",
         "name": "持械动作参考", "reference_group": {"primary": "图片/定妆_WEAPON_X_动作_持.png"}}
    assert _rfp.resolve_face_policy(a, "图片/定妆_WEAPON_X_动作_持.png") == "face_locked"
    assert _rfp._asset_carried_identities(a) == ["CHAR_JIANG_YUECHU"]   # owner 折入（治盲区脸漂）


def test_face_policy_none_for_plain_weapon():
    a = {"id": "WEAPON_Z", "type": "weapon", "name": "纯武器美术",
         "reference_group": {"primary": "图片/定妆_WEAPON_Z.png"}}
    assert _rfp.resolve_face_policy(a) == "none"
    assert _rfp._asset_carried_identities(a) == []


def test_face_policy_explicit_wins():
    a = {"id": "W", "type": "weapon", "owner": "CHAR_J", "name": "戟 握持比例", "face_policy": "face_locked"}
    assert _rfp.resolve_face_policy(a) == "face_locked"


def test_vfx_on_body_face_locked_via_explicit_carry():
    # 渲染在人身上的 VFX（万妖血脉脸漂案）走显式 carries_identity 声明 → face_locked + 折该角色脸
    a = {"id": "VFX_AURA", "type": "vfx", "carries_identity": "CHAR_A", "name": "血脉光环 上身"}
    assert _rfp.resolve_face_policy(a) == "face_locked"
    assert _rfp._asset_carried_identities(a) == ["CHAR_A"]


def test_pure_effect_vfx_is_none_not_overflagged():
    # 纯能量特效（青烟/白气/龙珠·无脸·无 owner·无声明）→ none，绝不误锁成 face_locked 而误拦既有资产
    a = {"id": "VFX_LI_GREEN_SMOKE", "type": "vfx", "name": "李乾元青烟缠身特效",
         "constraints": {"structure": "青绿色烟雾，包裹轮廓"}}
    assert _rfp.resolve_face_policy(a) == "none"


def test_scene_with_character_axis_text_not_face_locked():
    # 场景图描述顺带提到"角色运动轴线"不算出脸 → none（不误锁场景）
    a = {"id": "LOC_HALL", "type": "scene", "name": "益州府坍塌大堂",
         "constraints": {"axis_rules": "角色默认左→右推进，人物站位居中"}}
    assert _rfp.resolve_face_policy(a) == "none"
