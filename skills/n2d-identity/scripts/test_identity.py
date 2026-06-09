import hashlib
import json
from pathlib import Path

import identity

MODEL_BYTES = b"fake-lora-model"
MODEL_HASH = hashlib.sha256(MODEL_BYTES).hexdigest()


def _registry():
    return {
        "kind": "n2d_asset_identity_registry",
        "version": 1,
        "characters": [
            {
                "id": "CHAR_WANG",
                "name": "王敦",
                "scope": "全篇",
                "forms": [
                    {
                        "form": "常态",
                        "asset_key": "王敦",
                        "anchor_phrase": "圆脸微胖·短束发·旧青袍",
                        "reference_group": {
                            "front": "出图/共享/图片/定妆_王敦.png",
                            "side": "出图/共享/图片/定妆_王敦_侧.png",
                            "back": "出图/共享/图片/定妆_王敦_背.png",
                            "outfit": "出图/共享/图片/定妆_王敦_半身.png",
                            "turnaround": "出图/共享/图片/定妆_王敦_三视图.png",
                        },
                        "identity_adapters": {
                            "image": {
                                "codex": {"mode": "reference_group", "status": "fallback_reference_group"},
                                "kling": {"mode": "character_id", "status": "registered", "id": "img_klg_wang"},
                            },
                            "video": {
                                "dreamina": {"mode": "first_last_frame", "status": "fallback_reference_group"},
                                "kling": {"mode": "character_id", "status": "registered", "id": "vid_klg_wang"},
                                "seedance": {"mode": "face_lock", "status": "unregistered", "reference": ""},
                                "veo": {"mode": "reference_controls", "status": "unregistered", "id": ""},
                            },
                            "lora": {
                                "status": "ready",
                                "base_model": "flux",
                                "model_path": "models/wang.safetensors",
                                "trigger": "wangdun_char",
                                "dataset": "datasets/wang/dataset_manifest.json",
                                "model_hash": MODEL_HASH,
                                "validation_report": "models/wang_validation_report.json",
                            },
                        },
                        "angle_policy": {"allowed": ["front"], "risky": ["deep_shadow"], "requires_extra_reference": ["side"]},
                        "drift_forbidden": ["face_shape", "hairstyle", "outfit_palette"],
                    }
                ],
            }
        ],
    }


def _root(tmp_path: Path):
    root = tmp_path / "制漫剧" / "测试剧"
    for rel in _registry()["characters"][0]["forms"][0]["reference_group"].values():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
    model = root / "models/wang.safetensors"
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_bytes(MODEL_BYTES)
    report = {
        "kind": "n2d_lora_validation_report",
        "verdict": "pass",
        "model_path": "models/wang.safetensors",
        "model_sha256": MODEL_HASH,
        "warnings": [],
        "manual_review": {"approved": True},
    }
    (root / "models/wang_validation_report.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return root


def test_adapter_matrix_links_reference_group_native_video_and_lora(tmp_path):
    root = _root(tmp_path)
    matrix = identity.build_adapter_matrix(root, _registry(), generated_at="2026-06-08T00:00:00Z")

    form = matrix["forms"][0]
    assert form["reference_group_ready"] is True
    assert form["image_bindings"]["kling"]["ready"] is True
    assert form["image_bindings"]["kling"]["binding"] == "character_id"
    assert form["image_bindings"]["codex"]["binding"] == "reference_group"
    assert form["video_bindings"]["kling"]["ready"] is True
    assert form["video_bindings"]["kling"]["binding"] == "character_id"
    assert form["video_bindings"]["seedance"]["binding"] == "fallback_reference_group"
    assert form["lora_binding"]["ready"] is True
    assert form["gaps"] == []
    assert matrix["summary"]["forms_with_native_image_ready"] == 1
    assert matrix["summary"]["forms_with_native_video_ready"] == 1


def test_lora_ready_dataset_warning_override_requires_notes(tmp_path):
    root = _root(tmp_path)
    report_path = root / "models" / "wang_validation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["warnings"] = ["dataset_has_warnings"]
    report["manual_review"] = {"approved": True, "allow_dataset_warnings": True, "notes": ""}
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    matrix = identity.build_adapter_matrix(root, _registry())
    form = matrix["forms"][0]

    assert form["lora_binding"]["ready"] is False
    assert "lora:ready_dataset_warnings_override_notes_missing" in form["gaps"]
    assert matrix["summary"]["forms_with_lora_ready"] == 0


def test_registered_adapter_without_handle_is_gap(tmp_path):
    root = _root(tmp_path)
    data = _registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["video"]["kling"] = {
        "mode": "character_id",
        "status": "registered",
        "id": "",
    }

    matrix = identity.build_adapter_matrix(root, data)
    gaps = matrix["forms"][0]["gaps"]

    assert "video.kling:ready_without_handle" in gaps


def test_invalid_backend_mode_is_gap(tmp_path):
    root = _root(tmp_path)
    data = _registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["video"]["seedance"] = {
        "mode": "character_id",
        "status": "registered",
        "id": "wrong",
    }

    matrix = identity.build_adapter_matrix(root, data)
    assert "video.seedance:invalid_mode:seedance.character_id" in matrix["forms"][0]["gaps"]


def test_drift_summary_finds_first_bad_episode(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    face_results = {
        "第1集": {"available": True, "shots": [{"char": "王敦", "verdict": "ok", "score": 0.8, "floor": 0.7}]},
        "第2集": {"available": True, "shots": [{"char": "王敦", "verdict": "block", "score": 0.5, "floor": 0.7}]},
    }

    report = identity.summarize_face_results(root, ["第1集", "第2集"], face_results, generated_at="x")

    assert report["characters"]["王敦"]["first_bad_episode"] == "第2集"
    assert report["characters"]["王敦"]["total_block"] == 1


def test_parse_episodes_accepts_chinese_and_fullwidth_numbers():
    available = ["第1集", "第二集", "第３集"]

    assert identity.parse_episodes("一-三", available) == ["第1集", "第二集", "第３集"]
    assert identity.parse_episodes("第２集,第三集", available) == ["第二集", "第３集"]


def test_write_outputs(tmp_path):
    root = _root(tmp_path)
    matrix = identity.build_adapter_matrix(root, _registry())
    drift = identity.summarize_face_results(root, ["第1集"], {"第1集": {"available": True, "shots": []}})

    paths = identity.write_outputs(root, matrix, drift)

    assert paths["matrix_json"].is_file()
    assert paths["drift_md"].is_file()
    assert "角色身份 Adapter Matrix" in paths["matrix_md"].read_text(encoding="utf-8")
    assert list((root / "生产数据").glob("*.tmp.*")) == []
