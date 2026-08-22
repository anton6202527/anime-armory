from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workbench.py"
SPEC = importlib.util.spec_from_file_location("app_script_workbench", SCRIPT)
assert SPEC and SPEC.loader
workbench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workbench)


def authoring_raw(*, policy: str = "delegated", final_prompt: str = "当前镜头最终提示词") -> dict:
    return {
        "title": "测试故事",
        "global_style": "写实电影光影",
        "acceptance_policy": policy,
        "delivery_spec": {
            "container": "mp4",
            "mime_type": "video/mp4",
            "aspect_ratio": "16:9",
            "resolution": "1080p",
            "require_audio": False,
        },
        "shots": [{
            "id": "shot-01",
            "duration": 8,
            "visual": "主角穿过雨夜街道",
            "scale": "中景",
            "lighting": "冷色路灯",
            "dialogue": "",
            "sound": "雨声",
            "camera": "缓慢跟拍",
            "final_prompt": final_prompt,
            "color": "green",
        }],
        "assets": [],
    }


def make_complete_document(
    base_dir: Path,
    *,
    policy: str = "delegated",
    reviewer: str = "human",
    reviewer_name: str = "王小明",
    human_final: bool = True,
    with_asset: bool = False,
) -> dict:
    shot_path = base_dir / "shot-01.mp4"
    master_path = base_dir / "master.mp4"
    shot_path.write_bytes(b"real-shot-video")
    master_path.write_bytes(b"real-final-master")
    raw = authoring_raw(policy=policy)
    if with_asset:
        asset_path = base_dir / "character.png"
        asset_path.write_bytes(b"real-character-image")
        raw["assets"] = [{
            "id": "asset-1",
            "kind": "character",
            "name": "主角",
            "description": "黑色风衣",
            "prompt": "角色设定图",
            "status": "machine_complete",
            "source": "upload",
            "path": asset_path.name,
            "sha256": workbench.file_sha256(asset_path),
        }]
    data = workbench.build(raw, base_dir)
    root_hash = data["content_sha256"]
    shot_hash = workbench.file_sha256(shot_path)
    master_hash = workbench.file_sha256(master_path)
    qc_receipt_path = base_dir / "qc-receipt.json"
    qc_receipt_path.write_bytes(workbench.canonical_json({
        "content_sha256": root_hash,
        "master_sha256": master_hash,
        "verdict": "pass",
    }).encode("utf-8"))
    qc_receipt_hash = workbench.file_sha256(qc_receipt_path)
    data["jobs"] = [{
        "id": "job-shot-01",
        "kind": "shot_video",
        "shot_id": "shot-01",
        "input_sha256": root_hash,
        "status": "succeeded",
        "run_id": "run-1",
        "error": "",
    }]
    data["results"] = [{
        "id": "result-shot-01",
        "kind": "shot_video",
        "shot_id": "shot-01",
        "input_sha256": root_hash,
        "path": shot_path.name,
        "sha256": shot_hash,
        "review": "accepted" if reviewer == "human" else "machine_complete",
        "machine_receipt": {
            "reviewer_kind": "delegated_agent",
            "verdict": "pass",
            "content_sha256": root_hash,
            "output_sha256": shot_hash,
            "checks": ["首帧连续", "身份稳定", "动作完整"],
            "blocks": [],
            "completed_at": "2026-08-21T12:00:00+08:00",
        },
        "acceptance_receipt": {
            "reviewer_kind": reviewer,
            "reviewer_name": reviewer_name,
            "verdict": "accepted",
            "content_sha256": root_hash,
            "output_sha256": shot_hash,
            "criteria": ["首帧连续", "身份稳定", "动作完整"],
            "blocks": [],
            "reviewed_at": "2026-08-21T12:00:00+08:00",
            "confirmation": {
                "kind": "current_artifact_bytes",
                "artifact_sha256": shot_hash,
                "current_pixels_reviewed": True,
                "decision": "accept",
                "statement": "我已查看当前视频并确认接受这些确切字节。",
            },
        },
        "notes": "",
    }]
    data["master"] = {
        "status": "machine_complete",
        "input_sha256": root_hash,
        "path": master_path.name,
        "sha256": master_hash,
        "mime_type": "video/mp4",
        "duration": 8,
    }
    data["qc_receipt"] = {
        "verdict": "pass",
        "reviewer_kind": reviewer,
        "content_sha256": root_hash,
        "master_sha256": master_hash,
        "checks": ["全部镜头齐全", "母版可解码", "无阻断项"],
        "blocks": [],
        "notes": "",
        "reviewed_at": "2026-08-21T12:01:00+08:00",
        "receipt_path": qc_receipt_path.name,
        "receipt_sha256": qc_receipt_hash,
    }
    if with_asset:
        asset_hash = data["assets"][0]["sha256"]
        data["assets"][0]["status"] = "accepted"
        data["assets"][0]["acceptance_receipt"] = {
            "reviewer_kind": "human",
            "reviewer_name": reviewer_name,
            "verdict": "accepted",
            "content_sha256": root_hash,
            "output_sha256": asset_hash,
            "criteria": ["脸型一致", "服装结构一致"],
            "blocks": [],
            "reviewed_at": "2026-08-21T12:00:30+08:00",
            "confirmation": {
                "kind": "current_artifact_bytes",
                "artifact_sha256": asset_hash,
                "current_pixels_reviewed": True,
                "decision": "accept",
                "statement": "我已查看当前图片像素并确认接受这些确切字节。",
            },
        }
    if human_final:
        data["final_acceptance_receipt"] = {
            "reviewer_kind": "human",
            "reviewer_name": reviewer_name,
            "verdict": "accepted",
            "content_sha256": root_hash,
            "output_sha256": master_hash,
            "criteria": ["最终母版完整", "音画符合交付规格"],
            "blocks": [],
            "reviewed_at": "2026-08-21T12:02:00+08:00",
            "confirmation": {
                "kind": "current_artifact_bytes",
                "artifact_sha256": master_hash,
                "current_pixels_reviewed": True,
                "decision": "accept",
                "statement": "我已查看当前最终母版并确认接受这些确切字节。",
            },
        }
    workbench.refresh_document(data, base_dir)
    return data


class WorkbenchV3Tests(unittest.TestCase):
    def test_legacy_schemas_migrate_without_completion(self) -> None:
        for schema in (
            "app-script-workbench/v1",
            "n2d-script-workbench/v1",
            "app-n2d-script-workbench/v1",
        ):
            with self.subTest(schema=schema):
                raw = authoring_raw()
                raw.update({
                    "schema": schema,
                    "skill": "n2d-script-workbench" if schema.startswith("n2d-") else "app-script-workbench",
                    "style_locked": True,
                    "steps": {"shots": "done", "assets": "done", "prompts": "done"},
                    "state": "complete",
                })
                data = workbench.build(raw)
                self.assertEqual(data["schema"], workbench.SCHEMA)
                self.assertNotEqual(data["state"], "complete")
                self.assertEqual(data["state"], "ready")
                self.assertNotIn("steps", data)
                self.assertNotIn("style_locked", data)
                self.assertEqual(data["jobs"], [])
                self.assertEqual(data["results"], [])

    def test_v2_acceptance_migrates_to_recoverable_machine_evidence_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            old = make_complete_document(base)
            old["schema"] = "app-script-workbench/v2"
            old["completion"] = {"definition": "app-script-workbench/final-master/v1"}
            old["results"][0].pop("machine_receipt")
            old["final_acceptance_receipt"] = {}
            old["master"]["status"] = "ready"
            migrated = workbench.build(old, base)
            self.assertEqual(migrated["schema"], workbench.SCHEMA)
            self.assertNotEqual(migrated["state"], "complete")
            self.assertEqual(migrated["results"][0]["review"], "machine_complete")
            self.assertIn("legacy_acceptance_receipt", migrated["results"][0])
            self.assertTrue(migrated["migration"]["human_acceptance_reconfirmation_required"])

    def test_canonical_hash_ignores_runtime_layout_timestamps_and_color(self) -> None:
        data = workbench.build(authoring_raw())
        original = data["content_sha256"]
        data["state"] = "running"
        data["jobs"] = [{"arbitrary": "runtime"}]
        data["layout"] = {"x": 4, "y": 9}
        data["updated_at"] = "tomorrow"
        data["shots"][0]["color"] = "purple"
        self.assertEqual(workbench.content_sha256(data), original)
        data["global_style"] = "水彩动画"
        self.assertNotEqual(workbench.content_sha256(data), original)

    def test_canonical_json_is_sorted_compact_and_utf8(self) -> None:
        value = {"z": 1, "中文": "雨", "a": {"b": 2, "a": 1}}
        self.assertEqual(workbench.canonical_json(value), '{"a":{"a":1,"b":2},"z":1,"中文":"雨"}')

    def test_delegated_receipts_stop_at_machine_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base, reviewer="delegated_agent", reviewer_name="delegated_agent", human_final=False)
            self.assertEqual(data["state"], "machine_complete")
            self.assertEqual(workbench.machine_completion_gaps(data, base), [])
            self.assertTrue(workbench.completion_gaps(data, base))
            self.assertEqual(workbench.validate(data, base), [])

    def test_named_human_current_artifact_receipt_completes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base, policy="human")
            self.assertEqual(data["state"], "complete")

    def test_final_acceptance_requires_named_human_timezone_and_exact_sha(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for mutation in ("delegated", "anonymous", "naive_time", "wrong_sha"):
                with self.subTest(mutation=mutation):
                    data = make_complete_document(base)
                    receipt = data["final_acceptance_receipt"]
                    if mutation == "delegated":
                        receipt["reviewer_kind"] = "delegated_agent"
                    elif mutation == "anonymous":
                        receipt["reviewer_name"] = ""
                    elif mutation == "naive_time":
                        receipt["reviewed_at"] = "2026-08-21T12:02:00"
                    else:
                        receipt["confirmation"]["artifact_sha256"] = "a" * 64
                    workbench.refresh_document(data, base)
                    self.assertNotEqual(data["state"], "complete")
                    self.assertTrue(workbench.completion_gaps(data, base))

    def test_authoring_change_invalidates_all_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base)
            old_hash = data["content_sha256"]
            data["shots"][0]["visual"] = "主角停在雨夜路口"
            changed = workbench.refresh_document(data, base)
            self.assertTrue(changed)
            self.assertNotEqual(data["content_sha256"], old_hash)
            self.assertEqual(data["jobs"][0]["status"], "stale")
            self.assertEqual(data["results"][0]["review"], "stale")
            self.assertEqual(data["master"]["status"], "stale")
            self.assertEqual(data["qc_receipt"]["verdict"], "stale")
            self.assertEqual(data["state"], "ready")

    def test_compose_after_style_edit_is_a_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base)
            old_hash = data["content_sha256"]
            data["global_style"] = "手绘水彩动画"
            workbench.compose_document(data, base)
            self.assertNotEqual(data["content_sha256"], old_hash)
            self.assertIn("手绘水彩动画", data["shots"][0]["final_prompt"])
            self.assertEqual(data["results"][0]["review"], "stale")
            self.assertNotIn("style_locked", data)

    def test_changed_master_bytes_invalidate_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base)
            (base / "master.mp4").write_bytes(b"changed-final-master")
            workbench.refresh_document(data, base)
            self.assertEqual(data["master"]["status"], "stale")
            self.assertEqual(data["qc_receipt"]["verdict"], "stale")
            self.assertNotEqual(data["state"], "complete")

    def test_changed_asset_bytes_invalidate_all_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base, with_asset=True)
            self.assertEqual(data["state"], "complete")
            (base / "character.png").write_bytes(b"replaced-character-image")
            workbench.refresh_document(data, base)
            self.assertEqual(data["assets"][0]["status"], "stale")
            self.assertEqual(data["jobs"][0]["status"], "stale")
            self.assertEqual(data["results"][0]["review"], "stale")
            self.assertEqual(data["master"]["status"], "stale")
            self.assertEqual(data["qc_receipt"]["verdict"], "stale")
            self.assertEqual(data["state"], "draft")

    def test_each_shot_requires_a_current_machine_complete_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base)
            data["shots"].append({
                "id": "shot-02",
                "duration": 6,
                "visual": "主角回望",
                "scale": "近景",
                "lighting": "冷色路灯",
                "dialogue": "",
                "sound": "雨声",
                "camera": "固定机位",
                "final_prompt": "回望镜头",
                "color": "",
            })
            workbench.refresh_document(data, base)
            self.assertNotEqual(data["state"], "complete")
            self.assertTrue(any("shot-02" in gap for gap in workbench.completion_gaps(data, base)))

    def test_qc_block_never_completes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base)
            data["qc_receipt"]["verdict"] = "block"
            data["qc_receipt"]["blocks"] = ["音画不同步"]
            workbench.refresh_document(data, base)
            self.assertEqual(data["state"], "needs_revision")
            self.assertTrue(workbench.completion_gaps(data, base))

    def test_qc_pass_requires_path_sha_and_current_receipt_file_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for missing_field in ("receipt_path", "receipt_sha256"):
                with self.subTest(missing_field=missing_field):
                    data = make_complete_document(base)
                    data["qc_receipt"].pop(missing_field)
                    self.assertFalse(workbench.qc_receipt_passes(data, base))
                    self.assertTrue(any("qc_receipt pass" in error for error in workbench.validate(data, base)))

            data = make_complete_document(base)
            receipt_path = base / data["qc_receipt"]["receipt_path"]
            receipt_path.write_bytes(b"tampered-qc-receipt")
            self.assertFalse(workbench.qc_receipt_passes(data, base))
            self.assertTrue(any("qc_receipt pass" in error for error in workbench.validate(data, base)))
            workbench.refresh_document(data, base)
            self.assertEqual(data["qc_receipt"]["verdict"], "stale")
            self.assertNotEqual(data["state"], "complete")

    def test_qc_receipt_normalization_keeps_required_locator_fields(self) -> None:
        receipt = workbench.normalize_qc_receipt(None)
        self.assertEqual(receipt["receipt_path"], "")
        self.assertEqual(receipt["receipt_sha256"], "")

    def test_malformed_block_field_is_never_erased(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base)
            data["qc_receipt"]["blocks"] = "音画不同步"
            rebuilt = workbench.build(data, base)
            self.assertEqual(rebuilt["qc_receipt"]["blocks"], ["音画不同步"])
            self.assertNotEqual(rebuilt["state"], "complete")
            self.assertTrue(workbench.validate(rebuilt, base))

    def test_missing_reviewer_is_not_fabricated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = make_complete_document(base)
            data["results"][0]["acceptance_receipt"].pop("reviewer_kind")
            data["qc_receipt"].pop("reviewer_kind")
            rebuilt = workbench.build(data, base)
            self.assertEqual(rebuilt["results"][0]["acceptance_receipt"]["reviewer_kind"], "")
            self.assertEqual(rebuilt["qc_receipt"]["reviewer_kind"], "")
            self.assertNotEqual(rebuilt["state"], "complete")

    def test_machine_complete_asset_requires_sha_and_durable_locator(self) -> None:
        raw = authoring_raw()
        raw["assets"] = [{
            "id": "asset-1",
            "kind": "character",
            "name": "主角",
            "description": "黑色风衣",
            "prompt": "角色设定图",
            "status": "ready",
            "source": "canvas",
            "imageUrl": "blob:temporary-preview",
            "sha256": "a" * 64,
        }]
        data = workbench.build(raw)
        self.assertEqual(data["assets"][0]["status"], "pending")
        self.assertEqual(data["state"], "draft")

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            image = base / "character.png"
            image.write_bytes(b"real-image-pixels")
            raw["assets"][0].update({
                "path": image.name,
                "sha256": workbench.file_sha256(image),
                "status": "ready",
                "source": "upload",
            })
            data = workbench.build(raw, base)
            self.assertEqual(data["assets"][0]["status"], "machine_complete")
            self.assertEqual(data["state"], "ready")

    def test_complete_command_does_not_fabricate_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            document = base / "story.script-workbench.json"
            workbench.write_json(document, workbench.build(authoring_raw(), base))
            process = subprocess.run(
                [sys.executable, str(SCRIPT), "complete", str(document), "--write"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(process.returncode, 1)
            response = json.loads(process.stdout)
            self.assertFalse(response["complete"])
            saved = json.loads(document.read_text(encoding="utf-8"))
            self.assertNotEqual(saved["state"], "complete")
            self.assertEqual(saved["results"], [])


if __name__ == "__main__":
    unittest.main()
