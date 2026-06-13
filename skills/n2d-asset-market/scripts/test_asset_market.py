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


def _asset_registry():
    return {
        "kind": "n2d_asset_reference_registry",
        "version": 1,
        "assets": [
            {
                "id": "LOC_COLD_PALACE",
                "type": "scene",
                "name": "冷宫寝殿",
                "scope": "第1集起复用",
                "reference_group": {
                    "primary": "出图/共享/图片/定妆_冷宫寝殿.png",
                    "spatial_map": "出图/共享/图片/定妆_冷宫寝殿_布局图.png",
                },
                "spatial_layout": {"anchors": {"A1": "门口"}},
                "constraints": {"layout": "床榻到门口横轴", "light_anchor": "画左烛火"},
                "drift_forbidden": ["layout", "axis", "light_direction"],
            },
            {
                "id": "PROP_TRAY",
                "type": "prop",
                "name": "赐死托盘",
                "owner": "CHAR_LIU",
                "current_state": "held_by_hand",
                "reference_group": {
                    "primary": "出图/共享/图片/定妆_赐死托盘.png",
                },
                "lifecycle": {"states": ["intact", "broken"]},
                "constraints": {"structure": "三件套数量锁定；毒酒壶唯一短颈圆口；匕首一柄一刃"},
                "drift_forbidden": ["item_count", "flask_single_round_mouth"],
            },
        ],
    }


def _source_asset_project(tmp_path: Path):
    root = tmp_path / "制漫剧" / "源资产剧"
    registry = _asset_registry()
    for asset in registry["assets"]:
        for rel in asset["reference_group"].values():
            _write_png(root / rel)
    market.write_json(root / "出图/共享/asset_registry.json", registry)
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
    # 失效字段必须 pop 彻底移除（残留空串会被 schema 对账当成已登记）
    for stale in ("model_path", "model_hash", "validation_report", "train_job", "card"):
        assert stale not in l
    assert l["base_model"] == "flux" and l["trigger"] == "t"   # 重训参考保留


def test_export_and_import_scene_pack_merges_asset_registry(tmp_path):
    source = _source_asset_project(tmp_path)
    library = tmp_path / "资产库"

    rc = market.main([
        "export-scene",
        str(source),
        "--asset-id",
        "LOC_COLD_PALACE",
        "--library",
        str(library),
        "--slug",
        "冷宫寝殿",
    ])
    assert rc == 0
    pack = library / "scenes" / "冷宫寝殿" / "asset_pack.json"
    data = json.loads(pack.read_text(encoding="utf-8"))
    assert data["asset_type"] == "scene"
    assert data["files"][0]["exists"] is True

    target = tmp_path / "制漫剧" / "新资产剧"
    rc = market.main([
        "import-scene",
        str(target),
        str(pack.parent),
        "--as-id",
        "LOC_NEW_ROOM",
        "--as-name",
        "新冷宫",
    ])
    assert rc == 0

    registry = json.loads((target / "出图/共享/asset_registry.json").read_text(encoding="utf-8"))
    asset = registry["assets"][0]
    assert asset["id"] == "LOC_NEW_ROOM"
    assert asset["name"] == "新冷宫"
    assert asset["reference_group"]["primary"] == "出图/共享/图片/定妆_新冷宫.png"
    assert (target / "出图/共享/图片/定妆_新冷宫.png").is_file()
    assert asset["source_asset_slug"] == "冷宫寝殿"


def test_export_and_import_prop_pack_can_override_owner(tmp_path):
    source = _source_asset_project(tmp_path)
    library = tmp_path / "资产库"
    assert market.main([
        "export-prop",
        str(source),
        "--asset-id",
        "PROP_TRAY",
        "--library",
        str(library),
        "--slug",
        "赐死托盘",
    ]) == 0
    pack = library / "props" / "赐死托盘" / "asset_pack.json"

    target = tmp_path / "制漫剧" / "新资产剧"
    assert market.main([
        "import-prop",
        str(target),
        str(pack.parent),
        "--as-id",
        "PROP_NEW_TRAY",
        "--as-name",
        "新赐死托盘",
        "--owner",
        "CHAR_NEW_LIU",
    ]) == 0

    registry = json.loads((target / "出图/共享/asset_registry.json").read_text(encoding="utf-8"))
    asset = registry["assets"][0]
    assert asset["id"] == "PROP_NEW_TRAY"
    assert asset["owner"] == "CHAR_NEW_LIU"
    assert asset["reference_group"]["primary"] == "出图/共享/图片/定妆_新赐死托盘.png"


def test_import_scene_rejects_non_loc_id(tmp_path):
    source = _source_asset_project(tmp_path)
    library = tmp_path / "资产库"
    assert market.main([
        "export-scene",
        str(source),
        "--asset-id",
        "LOC_COLD_PALACE",
        "--library",
        str(library),
        "--slug",
        "冷宫寝殿",
    ]) == 0

    rc = market.main([
        "import-scene",
        str(tmp_path / "制漫剧" / "新资产剧"),
        str(library / "scenes" / "冷宫寝殿"),
        "--as-id",
        "ROOM_01",
        "--as-name",
        "错误前缀场景",
    ])

    assert rc == 2
