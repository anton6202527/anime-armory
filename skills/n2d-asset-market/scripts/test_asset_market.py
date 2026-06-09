import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("market.py")
spec = importlib.util.spec_from_file_location("asset_market", SCRIPT)
market = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(market)


def _write_png(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n")


def _registry():
    return {
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
                        "anchor_phrase": "凤眼薄唇·月白旧宫装·左腕淡疤",
                        "reference_group": {
                            "front": "出图/共享/图片/定妆_沈念.png",
                            "side": "出图/共享/图片/定妆_沈念_侧.png",
                            "back": "出图/共享/图片/定妆_沈念_背.png",
                            "outfit": "出图/共享/图片/定妆_沈念_半身.png",
                            "turnaround": "出图/共享/图片/定妆_沈念_三视图.png",
                        },
                        "identity_adapters": {
                            "image": {"kling": {"mode": "subject_library", "status": "registered", "id": "old_subject"}},
                            "video": {"kling": {"mode": "character_id", "status": "registered", "id": "old_video"}},
                            "lora": {"status": "ready", "base_model": "flux", "model_path": "old.safetensors", "trigger": "old"},
                        },
                        "angle_policy": {"allowed": ["front"], "risky": ["deep_shadow"]},
                        "drift_forbidden": ["face_shape", "hairstyle", "outfit_palette"],
                    }
                ],
            }
        ],
    }


def _source_project(tmp_path: Path):
    root = tmp_path / "制漫剧" / "源剧"
    registry = _registry()
    for rel in registry["characters"][0]["forms"][0]["reference_group"].values():
        _write_png(root / rel)
    market.write_json(root / "出图/共享/identity_registry.json", registry)
    return root


def test_export_and_import_character_pack_resets_native_adapters(tmp_path):
    source = _source_project(tmp_path)
    library = tmp_path / "资产库"

    rc = market.main([
        "export-character",
        str(source),
        "--character-id",
        "CHAR_SHEN",
        "--library",
        str(library),
        "--slug",
        "冷宫废妃",
    ])
    assert rc == 0
    pack = library / "characters" / "冷宫废妃" / "asset_pack.json"
    data = json.loads(pack.read_text(encoding="utf-8"))
    assert data["asset_type"] == "character"
    assert data["files"][0]["exists"] is True

    target = tmp_path / "制漫剧" / "新剧"
    rc = market.main([
        "import-character",
        str(target),
        str(pack.parent),
        "--as-id",
        "CHAR_NEW",
        "--as-name",
        "新女主",
    ])
    assert rc == 0

    registry = json.loads((target / "出图/共享/identity_registry.json").read_text(encoding="utf-8"))
    char = registry["characters"][0]
    form = char["forms"][0]
    assert char["id"] == "CHAR_NEW"
    assert char["name"] == "新女主"
    assert form["reference_group"]["front"] == "出图/共享/图片/定妆_新女主.png"
    assert (target / "出图/共享/图片/定妆_新女主.png").is_file()
    assert form["identity_adapters"]["video"]["kling"]["status"] == "unregistered"
    assert form["identity_adapters"]["image"]["codex"]["status"] == "fallback_reference_group"


def test_import_character_preserve_adapters_demotes_ready_handles(tmp_path):
    source = _source_project(tmp_path)
    library = tmp_path / "资产库"
    assert market.main([
        "export-character",
        str(source),
        "--character-id",
        "CHAR_SHEN",
        "--library",
        str(library),
        "--slug",
        "冷宫废妃",
    ]) == 0
    pack = library / "characters" / "冷宫废妃" / "asset_pack.json"

    assert market.main([
        "import-character",
        str(tmp_path / "制漫剧" / "无原因"),
        str(pack.parent),
        "--as-id",
        "CHAR_NO_REASON",
        "--as-name",
        "无原因",
        "--preserve-adapters",
    ]) == 2

    target = tmp_path / "制漫剧" / "新剧"
    rc = market.main([
        "import-character",
        str(target),
        str(pack.parent),
        "--as-id",
        "CHAR_NEW",
        "--as-name",
        "新女主",
        "--preserve-adapters",
        "--preserve-reason",
        "same IP migration review",
    ])
    assert rc == 0

    registry = json.loads((target / "出图/共享/identity_registry.json").read_text(encoding="utf-8"))
    adapters = registry["characters"][0]["forms"][0]["identity_adapters"]
    assert adapters["image"]["kling"]["status"] == "candidate"
    assert adapters["image"]["kling"]["id"] == "old_subject"
    assert adapters["image"]["kling"]["preserve_review"]["reason"] == "same IP migration review"
    assert adapters["video"]["kling"]["status"] == "candidate"
    assert adapters["video"]["kling"]["id"] == "old_video"
    assert adapters["video"]["kling"]["preserve_review"]["previous_status"] == "registered"
    assert adapters["lora"]["status"] == "candidate"
    assert adapters["lora"]["preserve_review"]["previous_status"] == "ready"


def test_reset_lora_clears_all_audit_fields():
    lora = market.reset_identity_adapters()["lora"]
    for k in ("model_hash", "validation_report", "train_job", "card", "model_path"):
        assert lora[k] == ""
    assert lora["status"] == "not_needed" and "notes" in lora


def test_downgrade_clears_stale_lora_path_keeps_base(tmp_path):
    ad = {"lora": {"status": "ready", "base_model": "flux", "model_path": "/old/x.safetensors",
                   "trigger": "t", "dataset": "d", "model_hash": "h",
                   "validation_report": "v.json", "train_job": "j.json"}}
    out = market.downgrade_preserved_adapters(ad, reason="import", pack_path=Path("p"))
    l = out["lora"]
    assert l["status"] == "candidate"
    assert l["model_path"] == "" and l["model_hash"] == "" and l["validation_report"] == ""
    assert l["base_model"] == "flux" and l["trigger"] == "t"   # 重训参考保留
