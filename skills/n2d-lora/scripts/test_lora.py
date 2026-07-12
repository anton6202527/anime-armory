import importlib.util
import json
import zipfile
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
                        "identity_adapters": {"lora": {"status": "not_needed", "reason": "old reference-group fallback"}},
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
    registry = json.loads((root / "出图/共享/identity_registry.json").read_text(encoding="utf-8"))
    binding = registry["characters"][0]["forms"][0]["identity_adapters"]["lora"]
    assert binding["status"] == "candidate"
    assert "reason" not in binding
    assert binding["lifecycle_note"].startswith("LoRA lifecycle initialized")
    assert lora.main(["dataset", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--copy-references"]) == 0
    assert lora.main(["train-job", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--provider", "manual"]) == 0
    registry = json.loads((root / "出图/共享/identity_registry.json").read_text(encoding="utf-8"))
    binding = registry["characters"][0]["forms"][0]["identity_adapters"]["lora"]
    assert "reason" not in binding
    assert binding["lifecycle_note"].startswith("LoRA train job planned")
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
    assert "reason" not in binding
    assert "lifecycle_note" not in binding


def test_lora_dataset_copies_atlas_face_and_expression_refs(tmp_path):
    root = _root(tmp_path)
    extra = {
        "three_quarter": "出图/共享/图片/定妆_沈念_45度.png",
        "face": "出图/共享/图片/定妆_沈念_脸部特写.png",
        "expression": "出图/共享/图片/定妆_沈念_表情_克制.png",
    }
    for rel in extra.values():
        _png(root / rel)
    reg_path = root / "出图/共享/identity_registry.json"
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    form = registry["characters"][0]["forms"][0]
    form["reference_group"]["three_quarter"] = extra["three_quarter"]
    form["reference_group"]["face_anchor_refs"] = [{"label": "基础脸锚", "path": extra["face"], "status": "ready"}]
    form["reference_atlas"] = {
        "base_views": {"three_quarter": {"path": extra["three_quarter"], "status": "ready"}},
        "expression_refs": [{"label": "克制", "path": extra["expression"], "status": "ready"}],
    }
    lora.write_json(reg_path, registry)

    assert lora.main(["init", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--base-model", "sdxl"]) == 0
    assert lora.main(["dataset", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--copy-references"]) == 0

    manifest = json.loads((root / "设定库/lora/CHAR_SHEN/常态/dataset_manifest.json").read_text(encoding="utf-8"))
    roles = {item["role"] for item in manifest["items"]}
    copied_roles = {item["role"] for item in manifest["copied_references"]}
    assert {"three_quarter", "face_anchor", "expression"} <= roles
    assert {"three_quarter", "face_anchor", "expression"} <= copied_roles


def test_lora_package_writes_cloud_upload_bundle(tmp_path):
    root = _root(tmp_path)
    assert lora.main(["init", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--base-model", "sdxl"]) == 0
    assert lora.main(["dataset", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--copy-references"]) == 0
    assert lora.main(["train-job", str(root), "--character-id", "CHAR_SHEN", "--form", "常态", "--provider", "fal"]) == 0

    out = root / "生产数据" / "lora_cloud_packages" / "test_package"
    assert lora.main([
        "package",
        str(root),
        "--character-id",
        "CHAR_SHEN",
        "--form",
        "常态",
        "--provider",
        "fal",
        "--output-dir",
        str(out),
    ]) == 0

    manifest = json.loads((out / "package_manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "n2d_lora_cloud_package"
    assert manifest["provider"] == "fal"
    assert manifest["dataset_count"] >= 5
    assert (out / "dataset.zip").is_file()
    with zipfile.ZipFile(out / "dataset.zip") as zf:
        names = set(zf.namelist())
    assert any(name.startswith("dataset/seed_front") and name.endswith(".png") for name in names)
    assert any(name.startswith("dataset/seed_front") and name.endswith(".txt") for name in names)
    job = json.loads((root / "设定库/lora/CHAR_SHEN/常态/train_job.json").read_text(encoding="utf-8"))
    assert job["cloud_package"]["manifest"].endswith("package_manifest.json")
    assert job["cloud_package"]["dataset_archive_sha256"] == manifest["dataset_archive_sha256"]


def test_lora_package_default_dir_stays_under_project_production_data(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.chdir(tmp_path)
    rel_root = root.relative_to(tmp_path).as_posix()
    assert lora.main(["init", rel_root, "--character-id", "CHAR_SHEN", "--form", "常态", "--base-model", "sdxl"]) == 0
    assert lora.main(["dataset", rel_root, "--character-id", "CHAR_SHEN", "--form", "常态", "--copy-references"]) == 0
    assert lora.main(["train-job", rel_root, "--character-id", "CHAR_SHEN", "--form", "常态", "--provider", "fal"]) == 0
    assert lora.main(["package", rel_root, "--character-id", "CHAR_SHEN", "--form", "常态", "--provider", "fal"]) == 0

    packages = list((root / "生产数据" / "lora_cloud_packages").glob("CHAR_SHEN__常态__fal__*/package_manifest.json"))
    assert len(packages) == 1
    assert not (root / rel_root).exists()
    manifest = json.loads(packages[0].read_text(encoding="utf-8"))
    assert manifest["dataset_archive"].startswith("生产数据/lora_cloud_packages/")


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


def test_lora_exception_scope_writes_and_checks_manifest(tmp_path):
    root = _root(tmp_path)

    assert lora.main([
        "exception-scope",
        str(root),
        "第1集",
        "--character-id",
        "CHAR_SHEN",
        "--form",
        "常态",
        "--clip",
        "Clip_03,Clip_08",
        "--reason",
        "hero shot needs the approved LoRA for one close-up",
        "--project-image-model",
        "GPT Image 2",
        "--lora-base-model",
        "flux-dev",
        "--style-bridge",
        "match series_grade and run full image_qc before video",
    ]) == 0

    path = root / "生产数据" / "lora_exception_scope_第1集.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_lora_exception_scope"
    assert data["clips"] == ["Clip_03", "Clip_08"]
    assert data["not_a_project_model_switch"] is True
    assert lora.main(["exception-scope", str(root), "第1集", "--check"]) == 0


def test_lora_exception_scope_validator_rejects_project_switch_shape():
    blocks = lora.validate_exception_scope({
        "kind": "n2d_lora_exception_scope",
        "episode": "第1集",
        "character_id": "CHAR_SHEN",
        "clips": ["Clip_03"],
        "reason": "hero",
        "project_image_model": "GPT Image 2",
        "lora_base_model": "flux-dev",
        "style_bridge": "grade bridge",
        "scope": "whole_episode",
        "not_a_project_model_switch": False,
    })

    assert "scope must be hero_shots_only" in blocks
    assert "not_a_project_model_switch must be true" in blocks


def _dataset_manifest_with_n_images(tmp_path, n):
    root = _root(tmp_path)
    out_dir = root / "设定库" / "lora" / "CHAR_SHEN" / "常态"
    dataset_dir = out_dir / "dataset"
    for i in range(n):
        img = dataset_dir / f"seed_front_{i:02d}.png"
        _png(img)
        img.with_suffix(".txt").write_text(f"shen_nian, front reference, {i}\n", encoding="utf-8")
    registry = lora.load_registry(root)
    char, form = lora.find_character_form(registry, character_id="CHAR_SHEN", form_name="常态")
    return lora.build_dataset_manifest(root, out_dir, char, form, "shen_nian")


def test_dataset_overfit_watch_above_30_images(tmp_path):
    manifest = _dataset_manifest_with_n_images(tmp_path, 31)
    warns = manifest["summary"]["warnings"]
    assert "dataset_above_30_images_overfit_watch" in warns
    assert "dataset_above_recommended_50_images_overfit_risk" not in warns
    assert manifest["recommended"]["sweet_spot_max_images"] == 30


def test_dataset_no_overfit_watch_at_30_images(tmp_path):
    manifest = _dataset_manifest_with_n_images(tmp_path, 30)
    warns = manifest["summary"]["warnings"]
    assert "dataset_above_30_images_overfit_watch" not in warns


def test_identity_qc_check_states(tmp_path):
    root = _root(tmp_path)
    # 空目录 → no_samples（或缺依赖时 unavailable，两者都不臆造分）
    qc_dir = root / "生产数据" / "lora_qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    res = lora.identity_qc_check(root, {"items": []}, qc_dir)
    assert res["status"] in {"no_samples", "unavailable"}
    assert res["median_cosine"] is None
    # 有样图但数据集无 front/closeup/side 锚 → no_reference_anchors（或 unavailable）
    _png(qc_dir / "sample1.png")
    res2 = lora.identity_qc_check(root, {"items": [{"role": "outfit", "file": "x.png"}]}, qc_dir)
    assert res2["status"] in {"no_reference_anchors", "unavailable"}
