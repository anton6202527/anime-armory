import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import voice_analysis as va


def test_extract_energy_does_not_turn_failed_ffmpeg_green(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"wav")
    monkeypatch.setattr(
        va.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr="mean_volume: -10.0 dB\nmax_volume: -1.0 dB", stdout=""),
    )

    result = va.extract_energy(wav)

    assert result["status"] == "error"
    assert result["energy_score"] is None


def test_analysis_uses_line_wav_and_marks_plugins_unmeasured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wav = tmp_path / "line_00.wav"
    wav.write_bytes(b"actual-line")
    manifest = [{"idx": 0, "角色": "甲", "文本": "别回头", "时长": 1.0, "line_wav": "line_00.wav"}]
    monkeypatch.setattr(va, "extract_energy", lambda path: {"status": "measured", "mean_db": -20, "max_db": -2, "energy_score": 0.8})
    monkeypatch.setattr(va, "probe_duration", lambda path: {"status": "measured", "duration_sec": 1.0, "returncode": 0})
    for key in ("N2D_VOICE_ASR_CMD", "N2D_VOICE_SPEAKER_CMD", "N2D_VOICE_PROSODY_CMD"):
        monkeypatch.delenv(key, raising=False)

    flow = va.analyze_emotion_flow(tmp_path, manifest, tmp_path / "emotion_flow.json")
    evidence = json.loads((tmp_path / "voice_quality_evidence.json").read_text(encoding="utf-8"))

    assert flow[0]["line_wav"].endswith("line_00.wav")
    assert flow[0]["analysis_status"] == "unmeasured"
    assert evidence["status"] == "unmeasured"
    assert evidence["summary"]["analyzed_lines"] == 1
    assert evidence["lines"][0]["line_wav_sha256"]


def test_asr_cer_contract() -> None:
    assert va.character_error_rate("令牌是真的", "令牌是真的") == 0
    assert va.character_error_rate("令牌是真的", "令牌是假") > 0


def test_key_lines_require_best_of_n_and_actual_listening_receipt(tmp_path: Path) -> None:
    wav_dir = tmp_path / "voice"
    wav_dir.mkdir()
    wav = wav_dir / "line_00.wav"
    wav.write_bytes(b"take")
    manifest = [{
        "idx": 0, "角色": "甲", "文本": "别回头！", "情绪": "紧张", "钩子": "cold_open",
        "line_wav": "line_00.wav",
    }]
    manifest_path = tmp_path / "时长清单.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    plan_path = tmp_path / "key_line_best_of_n_plan.json"
    receipt_path = tmp_path / "voice_listening_receipt.json"

    plan = va.build_key_line_best_of_n_plan(manifest, 3, manifest_path=manifest_path)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    receipt = va.record_listening_receipt(
        wav_dir, manifest, receipt_path,
        reviewer_kind="executor_audio", listened_indices=[0], review_notes=["三次听辨后确认爆破音清楚。"],
        manifest_path=manifest_path, plan_path=plan_path,
    )
    check = va.validate_listening_receipt(
        wav_dir, manifest, receipt_path, manifest_path=manifest_path, plan_path=plan_path,
    )

    assert plan["key_lines"][0]["candidate_count"] == 3
    assert plan["key_lines"][0]["selection_requires_actual_listening"] is True
    assert receipt["status"] == "reviewed"
    assert receipt["listened_lines"][0]["sha256"]
    assert receipt["final_user_acceptance"] is False
    assert check["status"] == "pass"


def test_listening_validator_rejects_forged_and_stale_receipts(tmp_path: Path) -> None:
    wav_dir = tmp_path / "voice"
    wav_dir.mkdir()
    wav = wav_dir / "line_00.wav"
    wav.write_bytes(b"take-v1")
    manifest = [{
        "idx": 0, "角色": "甲", "文本": "别回头！", "情绪": "紧张", "钩子": "cold_open",
        "line_wav": "line_00.wav",
    }]
    manifest_path = tmp_path / "时长清单.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    plan_path = tmp_path / "key_line_best_of_n_plan.json"
    plan_path.write_text(
        json.dumps(va.build_key_line_best_of_n_plan(manifest, manifest_path=manifest_path), ensure_ascii=False),
        encoding="utf-8",
    )
    receipt_path = tmp_path / "voice_listening_receipt.json"
    va.record_listening_receipt(
        wav_dir, manifest, receipt_path,
        reviewer_kind="human", listened_indices=[0], review_notes=["完整听辨当前关键句。"],
        manifest_path=manifest_path, plan_path=plan_path,
    )

    forged = json.loads(receipt_path.read_text(encoding="utf-8"))
    forged.update({
        "kind": "forged",
        "version": 999,
        "reviewer_kind": "robot",
        "reviewed_at": "2026-08-26T10:00:00",
        "review_notes": "听过",
        "key_line_coverage": 1.0,
    })
    forged["listened_lines"] = []
    receipt_path.write_text(json.dumps(forged, ensure_ascii=False), encoding="utf-8")

    check = va.validate_listening_receipt(
        wav_dir, manifest, receipt_path, manifest_path=manifest_path, plan_path=plan_path,
    )
    assert check["status"] == "block"
    assert any("kind" in issue for issue in check["issues"])
    assert any("version" in issue for issue in check["issues"])
    assert any("reviewer_kind" in issue for issue in check["issues"])
    assert any("时区" in issue for issue in check["issues"])
    assert any("尚未全部" in issue for issue in check["issues"])

    # Even a once-valid receipt becomes stale when the current line bytes change.
    va.record_listening_receipt(
        wav_dir, manifest, receipt_path,
        reviewer_kind="human", listened_indices=[0], review_notes=["完整听辨当前关键句。"],
        manifest_path=manifest_path, plan_path=plan_path,
    )
    wav.write_bytes(b"take-v2")
    stale = va.validate_listening_receipt(
        wav_dir, manifest, receipt_path, manifest_path=manifest_path, plan_path=plan_path,
    )
    assert stale["status"] == "block"
    assert any("SHA" in issue for issue in stale["issues"])


def test_listening_validator_blocks_stale_manifest_and_plan(tmp_path: Path) -> None:
    wav_dir = tmp_path / "voice"
    wav_dir.mkdir()
    (wav_dir / "line_00.wav").write_bytes(b"take")
    manifest = [{
        "idx": 0, "角色": "甲", "文本": "别回头！", "情绪": "紧张", "钩子": "cold_open",
        "line_wav": "line_00.wav",
    }]
    manifest_path = tmp_path / "时长清单.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    plan_path = tmp_path / "key_line_best_of_n_plan.json"
    plan_path.write_text(
        json.dumps(va.build_key_line_best_of_n_plan(manifest, manifest_path=manifest_path), ensure_ascii=False),
        encoding="utf-8",
    )
    receipt_path = tmp_path / "voice_listening_receipt.json"
    va.record_listening_receipt(
        wav_dir, manifest, receipt_path,
        reviewer_kind="executor_audio", listened_indices=[0], review_notes=["听辨完成。"],
        manifest_path=manifest_path, plan_path=plan_path,
    )
    changed = [dict(manifest[0], 文本="别回头！快走！")]
    manifest_path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")

    check = va.validate_listening_receipt(
        wav_dir, changed, receipt_path, manifest_path=manifest_path, plan_path=plan_path,
    )

    assert check["status"] == "block"
    assert any("plan manifest.contract_sha256" in issue for issue in check["issues"])
    assert any("receipt manifest.contract_sha256" in issue for issue in check["issues"])


def test_no_key_lines_are_explicitly_not_applicable_and_do_not_require_receipt(tmp_path: Path) -> None:
    manifest = [{"idx": 0, "角色": "甲", "文本": "天气很好", "情绪": "neutral", "钩子": "", "line_wav": "missing.wav"}]
    manifest_path = tmp_path / "时长清单.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    plan_path = tmp_path / "key_line_best_of_n_plan.json"
    plan_path.write_text(
        json.dumps(va.build_key_line_best_of_n_plan(manifest, manifest_path=manifest_path), ensure_ascii=False),
        encoding="utf-8",
    )

    check = va.validate_listening_receipt(
        tmp_path / "voice", manifest, tmp_path / "missing_receipt.json",
        manifest_path=manifest_path, plan_path=plan_path,
    )

    assert check["status"] == "not_applicable"
    assert check["issues"] == []


def test_render_voice_revalidates_listening_before_writing_done_progress() -> None:
    source = Path(__file__).with_name("render_voice.py").read_text(encoding="utf-8")

    assert source.index("validate_listening_receipt(") < source.index("progress_value =")
    assert "or not _listening_ready" in source
    assert "status=_voice_event_status" in source
