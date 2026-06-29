from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("backend_smoke.py")
spec = importlib.util.spec_from_file_location("backend_smoke", SCRIPT)
backend_smoke = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(backend_smoke)


def test_record_and_status_smoke_evidence(tmp_path: Path) -> None:
    payload = backend_smoke.record_smoke(
        str(tmp_path),
        "video",
        "veo",
        channel="gemini",
        status="pass",
        capabilities={"supports_first_frame": True, "supports_last_frame": True},
        source="unit",
        checked_at="2026-06-26",
    )

    status = backend_smoke.smoke_status(
        str(tmp_path),
        "video",
        "veo",
        channel="gemini",
        required_capabilities=["supports_first_frame"],
        today=dt.date(2026, 6, 26),
    )

    assert payload["capability_evidence_id"]
    assert status["status"] == "fresh"
    assert status["capability_evidence_id"] == payload["capability_evidence_id"]
    latest = tmp_path / "生产数据" / "backend_smoke" / "video_veo__via_gemini_latest.json"
    assert json.loads(latest.read_text(encoding="utf-8"))["status"] == "pass"


def test_status_detects_missing_capability_and_stale_smoke(tmp_path: Path) -> None:
    backend_smoke.record_smoke(
        str(tmp_path),
        "image",
        "codex",
        status="pass",
        capabilities={"supports_image_reference": True},
        checked_at="2026-06-01",
    )

    missing = backend_smoke.smoke_status(
        str(tmp_path),
        "image",
        "codex",
        required_capabilities=["supports_edit"],
        today=dt.date(2026, 6, 2),
    )
    stale = backend_smoke.smoke_status(
        str(tmp_path),
        "image",
        "codex",
        today=dt.date(2026, 6, 20),
        max_age_days=7,
    )

    assert missing["status"] == "missing_capability"
    assert stale["status"] == "stale"


def test_failed_smoke_blocks_status(tmp_path: Path) -> None:
    backend_smoke.record_smoke(
        str(tmp_path),
        "video",
        "kling",
        status="fail",
        checked_at="2026-06-26",
    )

    status = backend_smoke.smoke_status(
        str(tmp_path),
        "video",
        "kling",
        today=dt.date(2026, 6, 26),
    )

    assert status["status"] == "failed"


def test_manual_pass_without_proof_blocked_in_strict(tmp_path):
    # 手录 pass、无 live_probe、无 output_asset → 默认 fresh，但 require_proof 下判 unverified（证声明不证活性）。
    backend_smoke.record_smoke(str(tmp_path), "video", "kling", status="pass")
    lenient = backend_smoke.smoke_status(str(tmp_path), "video", "kling")
    assert lenient["status"] == "fresh"
    strict = backend_smoke.smoke_status(str(tmp_path), "video", "kling", require_proof=True)
    assert strict["status"] == "unverified", strict


def test_manual_pass_with_real_asset_passes_strict(tmp_path):
    asset = tmp_path / "out.mp4"
    asset.write_bytes(b"x")
    backend_smoke.record_smoke(str(tmp_path), "video", "kling", status="pass", output_asset="out.mp4")
    strict = backend_smoke.smoke_status(str(tmp_path), "video", "kling", require_proof=True)
    assert strict["status"] == "fresh", strict


def test_claimed_asset_missing_blocks_even_lenient(tmp_path):
    # 声明 output_asset 但产物不在 → asset_missing（报废 endpoint 凭一句 pass 绿、产物却没了）。
    backend_smoke.record_smoke(str(tmp_path), "image", "gpt_image_2", status="pass", output_asset="生产数据/gone.png")
    st = backend_smoke.smoke_status(str(tmp_path), "image", "gpt_image_2")
    assert st["status"] == "asset_missing", st


def test_live_probe_proof_type_passes_strict_without_asset(tmp_path):
    # 模拟 adapter 探活成功的记录（proof_type=live_probe）→ 无 output_asset 也过严档。
    backend_smoke.record_smoke(str(tmp_path), "image", "gpt_image_2", status="pass", proof_type="live_probe")
    strict = backend_smoke.smoke_status(str(tmp_path), "image", "gpt_image_2", require_proof=True)
    assert strict["status"] == "fresh", strict


def test_profile_smoke_records_event_and_checks_alternative_caps(tmp_path: Path) -> None:
    backend_smoke.record_smoke(
        str(tmp_path),
        "video",
        "veo",
        channel="gemini",
        status="pass",
        profile="frame_control",
        capabilities={"supports_first_frame": True, "supports_last_frame": True},
        proof_type="live_probe",
        checked_at="2026-06-26",
    )

    status = backend_smoke.smoke_status(
        str(tmp_path),
        "video",
        "veo",
        channel="gemini",
        profile="frame_control",
        today=dt.date(2026, 6, 26),
        require_proof=True,
    )
    latest = tmp_path / "生产数据" / "backend_smoke" / "video_veo__via_gemini__profile_frame_control_latest.json"
    events = (tmp_path / "生产数据" / "production_events.jsonl").read_text(encoding="utf-8").splitlines()

    assert status["status"] == "fresh"
    assert status["smoke_profile"] == "frame_control"
    assert latest.is_file()
    assert json.loads(events[-1])["stage"] == "backend_smoke"
    assert json.loads(events[-1])["meta"]["smoke_profile"] == "frame_control"


def test_frame_control_profile_requires_one_timeline_control_cap(tmp_path: Path) -> None:
    backend_smoke.record_smoke(
        str(tmp_path),
        "video",
        "runway",
        status="pass",
        profile="frame_control",
        capabilities={"supports_first_frame": True, "supports_last_frame": False, "supports_native_mid_anchors": False},
        checked_at="2026-06-26",
    )

    status = backend_smoke.smoke_status(
        str(tmp_path),
        "video",
        "runway",
        profile="frame_control",
        today=dt.date(2026, 6, 26),
    )

    assert status["status"] == "missing_capability"
    assert "supports_last_frame" in status["message"]
