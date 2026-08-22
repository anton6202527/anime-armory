from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import wave
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audio_video.py"
SPEC = importlib.util.spec_from_file_location("app_audio_video", SCRIPT)
assert SPEC and SPEC.loader
audio_video = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audio_video)


def write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(8000); stream.writeframes(b"\0\0" * 8000)


def acceptance(data: dict) -> dict:
    digest = data["output"]["sha256"]
    return {
        "reviewer_kind": "human", "reviewer_name": "赵小川", "verdict": "accepted",
        "audio_sha256": data["job"]["audio_sha256"], "timeline_sha256": data["job"]["timeline_sha256"], "output_sha256": digest,
        "criteria": ["节拍命中", "音轨完整"], "blocks": [], "reviewed_at": "2026-08-22T12:00:00+08:00",
        "confirmation": {"kind": "current_artifact_bytes", "artifact_sha256": digest, "current_pixels_reviewed": True, "decision": "accept", "statement": "我已查看当前视频并接受这些确切字节。"},
    }


class AudioVideoReceiptTests(unittest.TestCase):
    def test_current_file_and_human_receipt_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            audio, output = base / "track.wav", base / "output.mp4"
            write_wav(audio); output.write_bytes(b"video bytes")
            data = audio_video.build(audio)
            audio_video.prepare(data, base)
            data["output"].update(path=output.name, sha256=audio_video.file_sha(output), review="machine_complete")
            audio_video.refresh(data, base)
            self.assertNotEqual(data["steps"]["generation"], "done")
            self.assertEqual(audio_video.validate(data, base), [])
            data["steps"]["generation"] = "done"
            self.assertTrue(any("steps 与" in error for error in audio_video.validate(data, base)))
            audio_video.refresh(data, base)
            audio_video.accept_output(data, base, "赵小川", "我已查看当前视频并接受这些确切字节。", True)
            self.assertEqual(data["steps"]["generation"], "done")
            self.assertEqual(audio_video.validate(data, base), [])
            data["output"]["acceptance_receipt"]["reviewed_at"] = "2026-08-22T12:00:00"
            audio_video.refresh(data, base)
            self.assertNotEqual(data["steps"]["generation"], "done")
            self.assertTrue(audio_video.validate(data, base))

    def test_v1_acceptance_is_preserved_but_downgraded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            path.write_text(json.dumps({"schema": "app-audio-video/v1", "skill": "app-audio-video", "output": {"review": "accepted", "path": "old.mp4", "sha256": "a" * 64}}), encoding="utf-8")
            migrated = audio_video.read_json(path)
            self.assertEqual(migrated["schema"], audio_video.SCHEMA)
            self.assertEqual(migrated["output"]["review"], "machine_complete")
            self.assertIn("legacy_acceptance_receipt", migrated["output"])


if __name__ == "__main__":
    unittest.main()
