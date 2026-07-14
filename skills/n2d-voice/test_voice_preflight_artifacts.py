from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("voice_preflight.py")
SPEC = importlib.util.spec_from_file_location("voice_preflight", SCRIPT)
voice_preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(voice_preflight)


def test_zero_voice_doctor_is_dry_run_then_removes_only_legacy_empty_files(tmp_path: Path) -> None:
    voice = tmp_path / "合成" / "第1集" / "配音"
    voice.mkdir(parents=True)
    bad_wav = voice / "Clip1_voice.wav"
    bad_json = voice / "Clip1_voice.json"
    valid = voice / "line_01.wav"
    nonempty_legacy = voice / "Clip2_voice.wav"
    bad_wav.write_bytes(b"")
    bad_json.write_bytes(b"")
    valid.write_bytes(b"")
    nonempty_legacy.write_bytes(b"audio")

    dry = voice_preflight.doctor_zero_voice(tmp_path, "第1集")
    assert dry["status"] == "block"
    assert bad_wav.exists() and bad_json.exists()
    fixed = voice_preflight.doctor_zero_voice(tmp_path, "第1集", apply=True)
    assert fixed["status"] == "fixed"
    assert not bad_wav.exists() and not bad_json.exists()
    assert valid.exists() and nonempty_legacy.exists()
