from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "first_frame_video.py"
SPEC = importlib.util.spec_from_file_location("app_first_frame_video", SCRIPT)
assert SPEC and SPEC.loader
video = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(video)


def acceptance(data: dict) -> dict:
    digest = data["output"]["sha256"]
    return {
        "reviewer_kind": "human", "reviewer_name": "李小雨", "verdict": "accepted",
        "input_sha256": data["job"]["source_sha256"], "output_sha256": digest,
        "criteria": ["首帧连续", "身份稳定"], "blocks": [], "reviewed_at": "2026-08-22T11:00:00+08:00",
        "confirmation": {"kind": "current_artifact_bytes", "artifact_sha256": digest, "current_pixels_reviewed": True, "decision": "accept", "statement": "我已查看当前视频并接受这些确切字节。"},
    }


class FirstFrameVideoReceiptTests(unittest.TestCase):
    def test_machine_complete_then_explicit_human_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            frame, output = base / "frame.png", base / "output.mp4"
            frame.write_bytes(b"frame pixels")
            output.write_bytes(b"video bytes")
            data = video.build(frame)
            video.prepare(data, base)
            data["output"].update(path=output.name, sha256=video.sha256(output), review="machine_complete")
            video.refresh(data, base)
            self.assertNotEqual(data["steps"]["generation"], "done")
            self.assertEqual(video.validate(data, base), [])
            data["steps"]["generation"] = "done"
            self.assertTrue(any("steps 与" in error for error in video.validate(data, base)))
            video.refresh(data, base)
            video.accept_output(data, base, "李小雨", "我已查看当前视频并接受这些确切字节。", True)
            self.assertEqual(data["steps"]["generation"], "done")
            self.assertEqual(video.validate(data, base), [])
            output.write_bytes(b"replaced video")
            video.refresh(data, base)
            self.assertNotEqual(data["steps"]["generation"], "done")
            self.assertTrue(video.validate(data, base))

    def test_delegated_and_v1_accepted_cannot_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            frame, output = base / "frame.png", base / "output.mp4"
            frame.write_bytes(b"frame")
            output.write_bytes(b"video")
            data = video.build(frame)
            video.prepare(data, base)
            data["output"].update(path=output.name, sha256=video.sha256(output), review="accepted")
            data["output"]["acceptance_receipt"] = acceptance(data)
            data["output"]["acceptance_receipt"]["reviewer_kind"] = "delegated_agent"
            video.refresh(data, base)
            self.assertNotEqual(data["steps"]["generation"], "done")
            self.assertTrue(video.validate(data, base))

            legacy = base / "legacy.json"
            data["schema"] = "app-first-frame-video/v1"
            legacy.write_text(json.dumps(data), encoding="utf-8")
            migrated = video.read_json(legacy)
            self.assertEqual(migrated["output"]["review"], "machine_complete")
            self.assertIn("legacy_acceptance_receipt", migrated["output"])


if __name__ == "__main__":
    unittest.main()
