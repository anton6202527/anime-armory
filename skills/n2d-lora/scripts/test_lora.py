import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("lora.py")
spec = importlib.util.spec_from_file_location("n2d_lora", SCRIPT)
lora = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(lora)


def _png(path: Path, width=1024, height=1024):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _root(tmp_path: Path):
    root = tmp_path / "制漫剧" / "测试剧"
    refs = {
        "front": "出图/共享/图片/定妆_沈念.png",
        "side": "出图/共享/图片/定妆_沈念_侧.png",
        "back": "出图/共享/图片/定妆_沈念_背.png",
        "outfit": "出图/共享/图片/定妆_沈念_半身.png",
        "turnaround": "出图/共享/图片/定妆_沈念_三视图.png",
    }
    for rel in refs.values():
        _png(root / rel)
    registry = {
        "kind": "n2d_asset_identity_registry",
        "version": 1,
        "characters": [
            {
                "id": "CHAR_SHEN",
                "name": "沈念",
                "scope": "全篇",
                "forms": [
                    {
                        "form": "常态",
                        "asset_key": "沈念",
                        "anchor_phrase": "凤眼薄唇·月白旧宫装",
                        "reference_group": refs,
                        "identity_adapters": {"lora": {"status": "not_needed"}},
                        "angle_policy": {},
                        "drift_forbidden": ["face_shape"],
                    }
                ],
            }
        ],
    }
    lora.write_json(root / "出图/共享/identity_registry.json", registry)
    return root


def test_lora_lifecycle_registers_ready_binding(tmp_path):
    root = _root(tmp_path)
    assert lora.main(["init", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--base-model", "sdxl"]) == 0
    assert lora.main(["dataset", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--copy-references"]) == 0
    assert lora.main(["train-job", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--provider", "manual"]) == 0
    model = root / "设定库/lora/CHAR_SHEN/常态/CHAR_SHEN_normal_v1.safetensors"
    model.write_bytes(b"fake-model")
    assert lora.main(["validate", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--model-path", str(model), "--approved"]) == 1
    report = json.loads((root / "设定库/lora/CHAR_SHEN/常态/validation_report.json").read_text(encoding="utf-8"))
    assert report["verdict"] == "block"
    assert "dataset_warnings_unresolved" in report["blocks"]
    assert lora.main([
        "validate",
        str(root),
        "--character-id",
        "CHAR_SHEN",
        "--form",
        "常态",
        "--model-path",
        str(model),
        "--approved",
        "--allow-dataset-warnings",
    ]) == 1
    report = json.loads((root / "设定库/lora/CHAR_SHEN/常态/validation_report.json").read_text(encoding="utf-8"))
    assert "dataset_warnings_override_notes_missing" in report["blocks"]
    assert lora.main([
        "validate",
        str(root),
        "--character-id",
        "CHAR_SHEN",
        "--form",
        "常态",
        "--model-path",
        str(model),
        "--approved",
        "--allow-dataset-warnings",
        "--notes",
        "test fixture only has seed references",
    ]) == 0
    assert lora.main(["register", str(root), "--character-id", "CHAR_SHEN", "--form", "常态"]) == 0

    registry = json.loads((root / "出图/共享/identity_registry.json").read_text(encoding="utf-8"))
    binding = registry["characters"][0]["forms"][0]["identity_adapters"]["lora"]
    assert binding["status"] == "ready"
    assert binding["model_path"].endswith(".safetensors")
    assert binding["trigger"]
    assert binding["model_hash"]
    assert binding["validation_report"].endswith("validation_report.json")


def test_lora_force_register_writes_candidate_override_not_ready(tmp_path):
    root = _root(tmp_path)
    assert lora.main(["init", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--base-model", "sdxl"]) == 0
    out_dir = root / "设定库" / "lora" / "CHAR_SHEN" / "常态"
    lora.write_json(
        out_dir / "validation_report.json",
        {
            "kind": "n2d_lora_validation_report",
            "version": 1,
            "character_id": "CHAR_SHEN",
            "form": "常态",
            "model_path": "设定库/lora/CHAR_SHEN/常态/missing.safetensors",
            "model_sha256": "bad-hash",
            "base_model": "",
            "trigger": "",
            "dataset_manifest": "",
            "train_job": "",
            "verdict": "block",
            "warnings": ["dataset_has_warnings"],
            "blocks": ["model_path_missing"],
            "manual_review": {"approved": True, "allow_dataset_warnings": False},
        },
    )

    assert lora.main(["register", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--force"]) == 0

    registry = json.loads((root / "出图/共享/identity_registry.json").read_text(encoding="utf-8"))
    binding = registry["characters"][0]["forms"][0]["identity_adapters"]["lora"]
    assert binding["status"] == "candidate"
    assert binding["manual_override"]["forced"] is True
    assert "validation_verdict_not_pass:block" in binding["manual_override"]["reasons"]
    assert "missing_report_field:base_model" in binding["manual_override"]["reasons"]
    assert "missing_report_field:trigger" in binding["manual_override"]["reasons"]
    assert "dataset_warnings_without_override" in binding["manual_override"]["reasons"]
    assert "model_path_missing" in binding["manual_override"]["reasons"]


def test_suggest_without_drift_report_hints_identity_write(tmp_path, capsys):
    root = _root(tmp_path)

    assert lora.main(["suggest", str(root)]) == 1

    out = capsys.readouterr().out
    assert "identity_drift_report.json" in out
    assert "skills/n2d-identity/scripts/identity.py" in out


def test_suggest_prints_recommendations_from_drift_report(tmp_path, capsys):
    root = _root(tmp_path)
    report = {
        "kind": "n2d_identity_drift_report",
        "available": True,
        "characters": {},
        "recommendations": [
            {
                "type": "lora_upgrade",
                "character": "沈念",
                "character_id": "CHAR_SHEN",
                "character_name": "沈念",
                "form": "常态",
                "lora_status": "candidate",
                "bad_episodes": ["第1集", "第2集"],
                "first_bad_episode": "第2集",
                "reason": "2 集脸部相似度低于阈值",
                "next_command": "python3 skills/n2d-lora/scripts/lora.py init 'x' --character-id CHAR_SHEN --form '常态'",
            }
        ],
    }
    lora.write_json(root / "生产数据" / "identity_drift_report.json", report)

    assert lora.main(["suggest", str(root)]) == 0

    out = capsys.readouterr().out
    assert "CHAR_SHEN" in out
    assert "lora.py init" in out


def test_suggest_with_empty_recommendations_is_ok(tmp_path, capsys):
    root = _root(tmp_path)
    lora.write_json(
        root / "生产数据" / "identity_drift_report.json",
        {"kind": "n2d_identity_drift_report", "available": True, "characters": {}, "recommendations": []},
    )

    assert lora.main(["suggest", str(root)]) == 0
    assert "无 LoRA 升档建议" in capsys.readouterr().out


def test_lora_register_rejects_dataset_warning_override_without_notes(tmp_path):
    root = _root(tmp_path)
    out_dir = root / "设定库" / "lora" / "CHAR_SHEN" / "常态"
    model = out_dir / "CHAR_SHEN_normal_v1.safetensors"
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_bytes(b"fake-model")
    lora.write_json(
        out_dir / "validation_report.json",
        {
            "kind": "n2d_lora_validation_report",
            "version": 1,
            "character_id": "CHAR_SHEN",
            "form": "常态",
            "model_path": "设定库/lora/CHAR_SHEN/常态/CHAR_SHEN_normal_v1.safetensors",
            "model_sha256": lora.sha256(model),
            "base_model": "sdxl",
            "trigger": "shen_v1",
            "dataset_manifest": "设定库/lora/CHAR_SHEN/常态/dataset_manifest.json",
            "train_job": "",
            "verdict": "pass",
            "warnings": ["dataset_has_warnings", "dataset_warnings_overridden"],
            "blocks": [],
            "manual_review": {"approved": True, "allow_dataset_warnings": True, "notes": ""},
        },
    )

    assert lora.main(["register", str(root), "--character-id", "CHAR_SHEN", "--form", "常态"]) == 2
