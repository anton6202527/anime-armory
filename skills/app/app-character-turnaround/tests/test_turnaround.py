from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "turnaround.py"
SPEC = importlib.util.spec_from_file_location("app_character_turnaround", SCRIPT)
assert SPEC and SPEC.loader
turnaround = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(turnaround)


def receipt(view: dict, source_sha: str) -> dict:
    digest = view["output_sha256"]
    return {
        "reviewer_kind": "human",
        "reviewer_name": "王小明",
        "verdict": "accepted",
        "view_id": view["id"],
        "source_sha256": source_sha,
        "output_sha256": digest,
        "criteria": ["身份一致", "服装结构一致"],
        "blocks": [],
        "reviewed_at": "2026-08-22T10:00:00+08:00",
        "confirmation": {
            "kind": "current_artifact_bytes",
            "artifact_sha256": digest,
            "current_pixels_reviewed": True,
            "decision": "accept",
            "statement": "我已逐像素查看当前图片并接受这些确切字节。",
        },
    }


class TurnaroundReceiptTests(unittest.TestCase):
    def test_three_machine_outputs_require_three_current_pixel_human_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source.png"
            source.write_bytes(b"source pixels")
            data = turnaround.initial_payload("角色", str(source))
            turnaround.prepare(data, base)
            for view in data["views"]:
                output = base / f"{view['id']}.png"
                output.write_bytes(f"pixels:{view['id']}".encode())
                view.update(status="machine_complete", review="machine_complete", output_path=output.name, output_sha256=turnaround.file_sha(output))
            turnaround.refresh_steps(data, base)
            self.assertNotEqual(data["steps"]["generation"], "done")
            self.assertEqual(turnaround.validate(data, base), [])
            data["steps"]["generation"] = "done"
            self.assertTrue(any("steps 与" in error for error in turnaround.validate(data, base)))
            turnaround.refresh_steps(data, base)

            turnaround.accept_views(data, base, "王小明", "我已逐张查看三张当前图片并接受这些确切字节。", True)
            self.assertEqual(data["steps"]["generation"], "done")
            self.assertEqual(turnaround.validate(data, base), [])

            (base / "back.png").write_bytes(b"changed pixels")
            turnaround.refresh_steps(data, base)
            self.assertNotEqual(data["steps"]["generation"], "done")
            self.assertTrue(turnaround.validate(data, base))

    def test_delegated_or_naive_receipt_cannot_accept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source.png"
            output = base / "front.png"
            source.write_bytes(b"source")
            output.write_bytes(b"front")
            data = turnaround.initial_payload("角色", str(source))
            view = data["views"][0]
            view.update(status="accepted", review="accepted", output_path=output.name, output_sha256=turnaround.file_sha(output))
            view["acceptance_receipt"] = receipt(view, data["source"]["sha256"])
            view["acceptance_receipt"]["reviewer_kind"] = "delegated_agent"
            view["acceptance_receipt"]["reviewed_at"] = "2026-08-22T10:00:00"
            self.assertTrue(any("具名真人" in error for error in turnaround.validate(data, base)))

    def test_v1_accepted_migrates_fail_closed_and_preserves_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old.json"
            path.write_text(json.dumps({
                "schema": "app-character-turnaround/v1",
                "skill": "app-character-turnaround",
                "views": [{"id": "front", "status": "accepted", "review": "accepted", "output_path": "front.png", "output_sha256": "a" * 64}],
            }), encoding="utf-8")
            migrated = turnaround.read_json(path)
            self.assertEqual(migrated["schema"], turnaround.SCHEMA)
            self.assertEqual(migrated["views"][0]["status"], "machine_complete")
            self.assertIn("legacy_acceptance_receipt", migrated["views"][0])


if __name__ == "__main__":
    unittest.main()
