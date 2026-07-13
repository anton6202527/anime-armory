import importlib.util
import json
import base64
import subprocess
import sys
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


def test_run_codex_does_not_retry_non_transient_failure(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 1, stdout="content policy denied", stderr="")

    monkeypatch.setattr(codex_image_runner.subprocess, "run", fake_run)

    proc = codex_image_runner.run_codex(tmp_path, "prompt", 10, [])

    assert proc.returncode == 1
    assert len(calls) == 1


def test_image_qc_python_prefers_configured_executable(tmp_path: Path, monkeypatch) -> None:
    fake_python = tmp_path / "python"
    fake_python.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_python.chmod(0o755)

    monkeypatch.setenv(codex_image_runner.IMAGE_QC_PYTHON_ENV, str(fake_python))

    assert codex_image_runner.image_qc_python() == str(fake_python)


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
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + fill * 64)


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
    assert "鞋靴" in codex_image_runner.shared_variant_note(
        "出图/共享/图片/定妆_CHAR_TEST_三视图.png"
    )


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
            {"path": style_rel, "status": "ready", "use_policy": "style_source_only"}
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
                "external_visual_references": [{"path": style_rel, "status": "ready"}],
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
        "back": "出图/共享/图片/定妆_沈念_常态_背.png",
        "turnaround": "出图/共享/图片/定妆_沈念_常态_三视图.png",
        "half_body": "出图/共享/图片/定妆_沈念_常态_半身.png",
    }
    for rel in refs.values():
        write_valid_png(tmp_path / rel)
    face = "出图/共享/图片/定妆_沈念_常态_脸部特写.png"
    write_valid_png(tmp_path / face)
    style_anchor = "出图/共享/图片/风格锚_国漫写实.png"
    write_valid_png(tmp_path / style_anchor)
    codex_image_runner.mark_style_anchor_ready(tmp_path, style_anchor)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{
                    "form": "常态",
                    "reference_group": {
                        **{key: {"path": rel, "status": "ready"} for key, rel in refs.items()},
                        "face_anchor_refs": [{"path": face, "status": "ready"}],
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")

    assert codex_image_runner.shared_first_interlock_issues(tmp_path, "第1集") == []


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
        "back": "出图/共享/图片/定妆_沈念_常态_背.png",
        "turnaround": "出图/共享/图片/定妆_沈念_常态_三视图.png",
        "half_body": "出图/共享/图片/定妆_沈念_常态_半身.png",
    }
    for rel in refs.values():
        write_valid_png(tmp_path / rel)
    face = "出图/共享/图片/定妆_CHAR_01_HUMAN_脸部特写.png"
    write_valid_png(tmp_path / face)
    style_anchor = "出图/共享/图片/风格锚_国漫写实.png"
    write_valid_png(tmp_path / style_anchor)
    codex_image_runner.mark_style_anchor_ready(tmp_path, style_anchor)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{
                    "form": "常态",
                    "reference_group": {
                        **{key: {"path": rel, "status": "ready"} for key, rel in refs.items()},
                        "face_anchor_refs": [{"path": face, "status": "ready"}],
                    },
                }],
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


def test_reference_bundle_does_not_attach_non_ready_path_metadata(tmp_path: Path) -> None:
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
                    "status": "lineage_only_after_shared_front_generation",
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


def test_target_image_qc_treats_pixel_outfit_as_advisory_by_default(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.delenv("N2D_TARGET_QC_STRICT_PIXEL", raising=False)

    assert codex_image_runner.run_target_image_qc(tmp_path, "第1集", target)


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
