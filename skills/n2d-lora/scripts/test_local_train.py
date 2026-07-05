import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("local_train.py")
spec = importlib.util.spec_from_file_location("n2d_local_train", SCRIPT)
local_train = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(local_train)


def _write_ready_tokenizers(cache_dir: Path) -> None:
    required = ("tokenizer_config.json", "special_tokens_map.json", "tokenizer.json", "merges.txt", "vocab.json")
    for model_id in local_train.SDXL_TOKENIZER_IDS:
        path = cache_dir / local_train.local_tokenizer_name(model_id)
        path.mkdir(parents=True, exist_ok=True)
        for name in required:
            (path / name).write_text("{}", encoding="utf-8")


def _write_project(root: Path) -> None:
    lora_dir = root / "设定库" / "lora" / "CHAR_TEST" / "normal"
    dataset_dir = lora_dir / "dataset"
    dataset_dir.mkdir(parents=True)
    (lora_dir / "dataset_manifest.json").write_text(
        json.dumps(
            {
                "dataset_dir": "设定库/lora/CHAR_TEST/normal/dataset",
                "summary": {"images": 15, "warnings": [], "ready_for_training": True},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (lora_dir / "train_job.json").write_text(
        json.dumps(
            {
                "dataset_manifest": "设定库/lora/CHAR_TEST/normal/dataset_manifest.json",
                "output_dir": "设定库/lora/CHAR_TEST/normal",
                "expected_model_path": "设定库/lora/CHAR_TEST/normal/CHAR_TEST_normal_v1.safetensors",
                "trigger": "char_test_normal_v1",
                "hyperparameters": {"steps": 1000, "rank": 8, "learning_rate": "5e-4"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_prepare_disables_shuffle_when_caching_text_encoder_outputs(tmp_path):
    root = tmp_path / "project"
    _write_project(root)
    tokenizers = tmp_path / "tokenizers"
    _write_ready_tokenizers(tokenizers)
    sdscripts = tmp_path / "sd-scripts"
    sdscripts.mkdir()
    (sdscripts / "sdxl_train_network.py").write_text("# fake trainer\n", encoding="utf-8")
    checkpoint = tmp_path / "sdxl.safetensors"
    checkpoint.write_bytes(b"fake")

    assert local_train.main(
        [
            "prepare",
            str(root),
            "--character-id",
            "CHAR_TEST",
            "--form",
            "normal",
            "--sdscripts-home",
            str(sdscripts),
            "--checkpoint",
            str(checkpoint),
            "--tokenizer-cache-dir",
            str(tokenizers),
            "--unet-only",
            "--cache-text-encoder-outputs",
        ]
    ) == 0

    lora_dir = root / "设定库" / "lora" / "CHAR_TEST" / "normal"
    config = (lora_dir / "sdxl_dataset_config.toml").read_text(encoding="utf-8")
    job = json.loads((lora_dir / "train_job.json").read_text(encoding="utf-8"))
    command = job["local_training"]["command"]

    assert "shuffle_caption = false" in config
    assert "--cache_text_encoder_outputs" in command
    assert "--shuffle_caption" not in command
    assert job["local_training"]["caption_shuffle_disabled_for_text_encoder_cache"] is True
