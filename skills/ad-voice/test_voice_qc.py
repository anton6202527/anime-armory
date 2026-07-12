import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice_qc as vq  # noqa: E402


def test_voice_qc_detects_duration_and_silence(monkeypatch, tmp_path):
    root = tmp_path / "ad"
    (root / "配音").mkdir(parents=True)
    (root / "配音" / "line_01.wav").write_bytes(b"wav")
    (root / "配音" / "vo.wav").write_bytes(b"wav")
    (root / "配音" / "时长清单.json").write_text(json.dumps({
        "has_placeholder": False,
        "lines": [{"idx": 1, "line_wav": "line_01.wav", "seconds": 1.0, "voice_key": "VO"}],
    }), encoding="utf-8")
    monkeypatch.setattr(vq.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(vq, "probe", lambda path: {
        "streams": [{"codec_type": "audio", "sample_rate": "48000", "channels": 1}],
        "format": {"duration": "1.0"},
    })
    monkeypatch.setattr(vq, "volume", lambda path: {"mean_db": -20.0, "max_db": -1.0})

    payload = vq.inspect(root)

    assert payload["summary"]["block"] == 0
    assert payload["qc_environment"]["precision_level"] == "full"


def test_formal_silent_voice_blocks_with_json_safe_levels(monkeypatch, tmp_path):
    root = tmp_path / "ad"
    (root / "配音").mkdir(parents=True)
    (root / "配音" / "line_01.wav").write_bytes(b"wav")
    (root / "配音" / "vo.wav").write_bytes(b"wav")
    (root / "配音" / "时长清单.json").write_text(json.dumps({
        "has_placeholder": False,
        "lines": [{"idx": 1, "line_wav": "line_01.wav", "seconds": 1.0, "voice_key": "VO"}],
    }), encoding="utf-8")
    monkeypatch.setattr(vq.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(vq, "probe", lambda path: {
        "streams": [{"codec_type": "audio", "sample_rate": "48000", "channels": 1}],
        "format": {"duration": "1.0"},
    })
    monkeypatch.setattr(vq, "volume", lambda path: {"mean_db": None, "max_db": None})
    payload = vq.inspect(root)
    assert any(f["code"] == "voice_line_silent" for f in payload["findings"])
    json.dumps(payload, allow_nan=False)
