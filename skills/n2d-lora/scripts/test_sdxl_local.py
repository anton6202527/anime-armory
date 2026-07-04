import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("sdxl_local.py")
spec = importlib.util.spec_from_file_location("n2d_sdxl_local", SCRIPT)
sdxl = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(sdxl)


def test_write_profile_marks_sdxl_as_sidechain(tmp_path):
    root = tmp_path / "剧"
    assert sdxl.main(["write-profile", str(root), "--comfy-home", str(tmp_path / "ComfyUI"), "--env", "sdxl-test"]) == 0

    data = json.loads((root / "生产数据/local_sdxl_profile.json").read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_local_sdxl_profile"
    assert data["not_a_project_model_switch"] is True
    assert "hero_shot_sidechain" in data["purpose"]
    assert data["backend"]["model_family"] == "sdxl"


def test_workflow_writes_comfyui_api_prompt_with_lora(tmp_path):
    root = tmp_path / "剧"
    assert sdxl.main([
        "workflow",
        str(root),
        "第1集",
        "--clip",
        "Clip_03",
        "--character-id",
        "CHAR_SHEN",
        "--form",
        "常态",
        "--checkpoint",
        "sdxl.safetensors",
        "--lora",
        "shen.safetensors",
        "--trigger",
        "shen_v1",
        "--prompt",
        "hero close-up, same face",
    ]) == 0

    path = root / "生产数据/comfyui_workflows/第1集_Clip_03_sdxl_lora.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    prompt = data["prompt"]
    assert data["kind"] == "n2d_comfyui_sdxl_workflow"
    assert data["not_a_project_model_switch"] is True
    assert prompt["1"]["class_type"] == "CheckpointLoaderSimple"
    assert prompt["2"]["class_type"] == "LoraLoader"
    assert prompt["2"]["inputs"]["lora_name"] == "shen.safetensors"
    assert "shen_v1" in prompt["3"]["inputs"]["text"]


def test_record_output_writes_gate_visible_sidechain_event(tmp_path):
    root = tmp_path / "剧"
    png = root / "出图/第1集/图片/EP01_CLIP03_sdxl.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    png.write_bytes(b"fake")

    assert sdxl.main([
        "record-output",
        str(root),
        "第1集",
        "--clip",
        "Clip_03",
        "--output",
        str(png),
        "--character-id",
        "CHAR_SHEN",
        "--form",
        "常态",
        "--lora-model",
        "shen.safetensors",
        "--workflow",
        "workflow.json",
    ]) == 0

    line = (root / "生产数据/production_events.jsonl").read_text(encoding="utf-8").strip()
    event = json.loads(line)
    assert event["provider"] == "ComfyUI SDXL LoRA"
    assert event["method"] == "sdxl_lora"
    assert event["generation"]["backend"] == "comfyui"
    assert event["generation"]["model"] == "sdxl"
    assert event["generation"]["clip"] == "Clip_03"


def test_route_falls_back_to_project_backend_when_local_training_incomplete(tmp_path, monkeypatch):
    root = tmp_path / "剧"
    root.mkdir()
    (root / "_设置.md").write_text("- 生图AI：Dreamina/即梦官方 CLI\n", encoding="utf-8")
    monkeypatch.setattr(sdxl, "conda_env_exists", lambda _env: False)

    assert sdxl.main([
        "route",
        str(root),
        "--comfy-home",
        str(tmp_path / "missing-comfy"),
        "--env",
        "missing-env",
        "--write",
    ]) == 0

    data = json.loads((root / "生产数据/lora_runtime_route.json").read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_lora_runtime_route"
    assert data["decision"]["route"] == "cloud_image_generation_fallback"
    assert data["decision"]["use_local_lora_training"] is False
    assert data["fallback"]["image_backend"] == "Dreamina/即梦官方 CLI"
    assert "conda_env_missing" in data["local_training"]["missing_requirements"]
    assert data["fallback"]["do_not_block_image_generation_on_missing_local_lora"] is True


def test_route_prefers_local_lora_training_when_environment_is_complete(tmp_path, monkeypatch):
    root = tmp_path / "剧"
    dataset = root / "设定库/lora/CHAR_SHEN/常态/dataset_manifest.json"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(
        json.dumps({"summary": {"images": 18, "warnings": [], "ready_for_training": True}}, ensure_ascii=False),
        encoding="utf-8",
    )
    comfy = tmp_path / "ComfyUI"
    (comfy / "models/checkpoints").mkdir(parents=True)
    (comfy / "main.py").write_text("# fake comfy\n", encoding="utf-8")
    (comfy / "models/checkpoints/sdxl.safetensors").write_bytes(b"fake")
    trainer = tmp_path / "sdxl_train_network.py"
    trainer.write_text("# fake trainer\n", encoding="utf-8")
    monkeypatch.setattr(sdxl, "conda_env_exists", lambda _env: True)
    monkeypatch.setattr(
        sdxl,
        "torch_probe",
        lambda _env: {"probe_ok": True, "torch": "test", "mps_built": True, "mps_available": True},
    )

    assert sdxl.main([
        "route",
        str(root),
        "--comfy-home",
        str(comfy),
        "--env",
        "sdxl-comfy",
        "--character-id",
        "CHAR_SHEN",
        "--form",
        "常态",
        "--trainer-cmd",
        f"python3 {trainer}",
        "--write",
    ]) == 0

    data = json.loads((root / "生产数据/lora_runtime_route.json").read_text(encoding="utf-8"))
    assert data["decision"]["route"] == "local_lora_training"
    assert data["decision"]["use_local_lora_training"] is True
    assert data["local_training"]["provider"] == "local_sdxl"
    assert data["local_training"]["checks"]["dataset"]["available"] is True

    scoped = root / "生产数据/lora_runtime_route_CHAR_SHEN__常态.json"
    scoped_data = json.loads(scoped.read_text(encoding="utf-8"))
    assert scoped_data["character_id"] == "CHAR_SHEN"
    assert scoped_data["form"] == "常态"
    assert scoped_data["decision"]["route"] == "local_lora_training"
