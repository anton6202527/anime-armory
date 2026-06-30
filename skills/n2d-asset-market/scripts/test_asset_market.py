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
            {
                "id": "WEAPON_FROST_SWORD",
                "type": "magic_weapon",
                "name": "霜纹长剑",
                "owner": "CHAR_SHEN",
                "reference_group": {
                    "primary": "出图/共享/图片/定妆_霜纹长剑.png",
                    "wielding": "出图/共享/图片/定妆_霜纹长剑_握持比例.png",
                },
                "weapon_profile": {
                    "silhouette": "窄长直剑，短护手，一手半握柄",
                    "palette": {"blade": "#D8E3E7", "accent": "#5BAFA8"},
                },
                "constraints": {"structure": "一柄一刃，窄长直剑，青色剑穗"},
                "drift_forbidden": ["blade_shape", "hilt", "palette"],
            },
            {
                "id": "OUTFIT_OFFICIAL_ROBE",
                "type": "costume",
                "name": "玄青窄袖官袍",
                "reference_group": {
                    "primary": "出图/共享/图片/定妆_玄青窄袖官袍.png",
                    "details": "出图/共享/图片/定妆_玄青窄袖官袍_领袖腰封.png",
                },
                "outfit_profile": {
                    "silhouette": "直身窄袖官袍",
                    "layers": ["玄青外袍", "灰白内衬"],
                    "palette": {"primary": "#24373A", "accent": "#B8B2A1"},
                },
                "constraints": {"structure": "交领+窄袖+暗银腰封+玄青主色"},
                "drift_forbidden": ["silhouette", "collar", "sleeve", "palette"],
            },
            {
                "id": "VFX_FROST_TRAIL",
                "type": "effect",
                "name": "青白剑气拖尾",
                "reference_group": {
                    "primary": "出图/共享/图片/定妆_青白剑气拖尾.png",
                },
                "vfx_params": {"color_target": {"h": 190, "s": 0.35, "v": 0.95}, "trail": "短拖尾"},
                "constraints": {"structure": "青白冷光细线拖尾，不爆炸成火焰"},
                "drift_forbidden": ["color", "trail", "shape"],
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


def test_export_and_import_weapon_pack_accepts_weapon_alias_and_owner_override(tmp_path):
    source = _source_asset_project(tmp_path)
    library = tmp_path / "资产库"

    rc = market.main([
        "export-weapon",
        str(source),
        "--asset-id",
        "WEAPON_FROST_SWORD",
        "--library",
        str(library),
        "--slug",
        "霜纹长剑",
    ])
    assert rc == 0
    pack = library / "weapons" / "霜纹长剑" / "asset_pack.json"
    data = json.loads(pack.read_text(encoding="utf-8"))
    assert data["asset_type"] == "weapon"
    assert data["asset_registry_fragment"]["assets"][0]["type"] == "magic_weapon"
    assert all(f["exists"] for f in data["files"])

    target = tmp_path / "制漫剧" / "新武器剧"
    assert market.main([
        "import-weapon",
        str(target),
        str(pack.parent),
        "--as-id",
        "WEAPON_THUNDER_SWORD",
        "--as-name",
        "雷纹长剑",
        "--owner",
        "CHAR_NEW",
    ]) == 0

    registry = json.loads((target / "出图/共享/asset_registry.json").read_text(encoding="utf-8"))
    asset = registry["assets"][0]
    assert asset["id"] == "WEAPON_THUNDER_SWORD"
    assert asset["type"] == "magic_weapon"
    assert asset["owner"] == "CHAR_NEW"
    assert asset["reference_group"]["primary"] == "出图/共享/图片/定妆_雷纹长剑.png"
    assert asset["reference_group"]["wielding"] == "出图/共享/图片/定妆_雷纹长剑_wielding.png"
    assert asset["weapon_profile"]["silhouette"] == "窄长直剑，短护手，一手半握柄"
    assert (target / "出图/共享/图片/定妆_雷纹长剑.png").is_file()


def test_export_and_import_outfit_pack_accepts_costume_alias(tmp_path):
    source = _source_asset_project(tmp_path)
    library = tmp_path / "资产库"

    assert market.main([
        "export-outfit",
        str(source),
        "--asset-id",
        "OUTFIT_OFFICIAL_ROBE",
        "--library",
        str(library),
        "--slug",
        "玄青窄袖官袍",
    ]) == 0
    pack = library / "outfits" / "玄青窄袖官袍" / "asset_pack.json"
    data = json.loads(pack.read_text(encoding="utf-8"))
    assert data["asset_type"] == "outfit"
    assert data["asset_registry_fragment"]["assets"][0]["type"] == "costume"

    target = tmp_path / "制漫剧" / "新服装剧"
    assert market.main([
        "import-outfit",
        str(target),
        str(pack.parent),
        "--as-id",
        "OUTFIT_GUARD_ROBE",
        "--as-name",
        "玄青侍卫袍",
    ]) == 0

    registry = json.loads((target / "出图/共享/asset_registry.json").read_text(encoding="utf-8"))
    asset = registry["assets"][0]
    assert asset["id"] == "OUTFIT_GUARD_ROBE"
    assert asset["type"] == "costume"
    assert asset["reference_group"]["primary"] == "出图/共享/图片/定妆_玄青侍卫袍.png"
    assert asset["reference_group"]["details"] == "出图/共享/图片/定妆_玄青侍卫袍_details.png"
    assert asset["outfit_profile"]["silhouette"] == "直身窄袖官袍"
    assert (target / "出图/共享/图片/定妆_玄青侍卫袍.png").is_file()


def test_export_and_import_vfx_pack_accepts_effect_alias(tmp_path):
    source = _source_asset_project(tmp_path)
    library = tmp_path / "资产库"

    assert market.main([
        "export-vfx",
        str(source),
        "--asset-id",
        "VFX_FROST_TRAIL",
        "--library",
        str(library),
        "--slug",
        "青白剑气拖尾",
    ]) == 0
    pack = library / "vfx" / "青白剑气拖尾" / "asset_pack.json"
    data = json.loads(pack.read_text(encoding="utf-8"))
    assert data["asset_type"] == "vfx"
    assert data["asset_registry_fragment"]["assets"][0]["type"] == "effect"

    target = tmp_path / "制漫剧" / "新特效剧"
    assert market.main([
        "import-vfx",
        str(target),
        str(pack.parent),
        "--as-id",
        "VFX_THUNDER_TRAIL",
        "--as-name",
        "雷蓝剑气拖尾",
    ]) == 0

    registry = json.loads((target / "出图/共享/asset_registry.json").read_text(encoding="utf-8"))
    asset = registry["assets"][0]
    assert asset["id"] == "VFX_THUNDER_TRAIL"
    assert asset["type"] == "effect"
    assert asset["reference_group"]["primary"] == "出图/共享/图片/定妆_雷蓝剑气拖尾.png"
    assert asset["vfx_params"]["trail"] == "短拖尾"
    assert (target / "出图/共享/图片/定妆_雷蓝剑气拖尾.png").is_file()


def _combat_registry():
    return {
        "kind": "n2d_combat_registry",
        "version": 1,
        "combat_sets": [
            {
                "combat_id": "COMBAT_万妖妖力近战",
                "name": "万妖妖力近战",
                "element_skin": "暗金妖力",
                "rhythm_preset": {"speed_curve": "蓄力慢→出招快→命中顿→收势留白", "hit_stop_frames": 4},
                "bound_weapons": ["WEAPON_DAGGER"],
                "bound_vfx": ["VFX_DARKGOLD"],
                "moves": [
                    {
                        "move_id": "SM_01",
                        "name": "噬腕·夺刃",
                        "type": "命中类",
                        "five_frame_template": ["起手", "发力", "命中", "受击", "收势"],
                        "action_choreography": {
                            "attack_path": "画左前景弧线向画右上挑刺",
                            "impact_frame": "命中帧",
                            "contact_points": ["短匕刃↔太监腕"],
                            "force_direction": "沈念(画左)→太监(画右)",
                            "recovery_beat": "起身留白",
                        },
                        "keyframe_refs": {
                            "起手": "出图/第2集/图片/镜头31_起手.png",
                            "命中": "出图/第2集/图片/镜头32_命中.png",
                        },
                    }
                ],
            }
        ],
    }


def _combat_asset_registry():
    return {
        "kind": "n2d_asset_reference_registry",
        "version": 1,
        "assets": [
            {
                "id": "WEAPON_DAGGER",
                "type": "weapon",
                "name": "短匕",
                "reference_group": {"primary": "出图/共享/图片/定妆_短匕.png"},
                "weapon_profile": {"silhouette": "单刃直身短匕"},
                "drift_forbidden": ["变长剑"],
            },
            {
                "id": "VFX_DARKGOLD",
                "type": "vfx",
                "name": "暗金妖力",
                "reference_group": {"primary": "出图/共享/图片/定妆_暗金妖力.png"},
                "drift_forbidden": ["换色"],
            },
        ],
    }


def _source_combat_project(tmp_path: Path):
    root = tmp_path / "制漫剧" / "源打斗剧"
    market.write_json(root / "出图/共享/combat_registry.json", _combat_registry())
    asset_reg = _combat_asset_registry()
    for asset in asset_reg["assets"]:
        for rel in asset["reference_group"].values():
            _write_png(root / rel)
    market.write_json(root / "出图/共享/asset_registry.json", asset_reg)
    return root


def test_export_and_import_combat_pack_reskins_and_merges(tmp_path):
    source = _source_combat_project(tmp_path)
    library = tmp_path / "资产库"

    rc = market.main([
        "export-combat",
        str(source),
        "--library",
        str(library),
        "--slug",
        "万妖妖力近战",
    ])
    assert rc == 0
    pack = library / "combat" / "万妖妖力近战" / "asset_pack.json"
    data = json.loads(pack.read_text(encoding="utf-8"))
    assert data["asset_type"] == "combat"
    # 绑定的 WEAPON_/VFX_ 都进了 pack，参考图都拷进来了
    bound = data["asset_registry_fragment"]["assets"]
    assert {a["id"] for a in bound} == {"WEAPON_DAGGER", "VFX_DARKGOLD"}
    assert all(f["exists"] for f in data["files"])

    target = tmp_path / "制漫剧" / "新打斗剧"
    rc = market.main([
        "import-combat",
        str(target),
        str(pack.parent),
        "--as-id",
        "COMBAT_雷霆近战",
    ])
    assert rc == 0

    creg = json.loads((target / "出图/共享/combat_registry.json").read_text(encoding="utf-8"))
    cset = creg["combat_sets"][0]
    assert cset["combat_id"] == "COMBAT_雷霆近战"
    assert cset["source_combat_slug"] == "万妖妖力近战"
    # reskin 重置：关键帧被清空、标记需重出；五帧+编排骨架保留
    move = cset["moves"][0]
    assert move["keyframe_refs"] == {}
    assert move["needs_keyframe_regen"] is True
    assert move["action_choreography"]["force_direction"] == "沈念(画左)→太监(画右)"
    assert move["five_frame_template"] == ["起手", "发力", "命中", "受击", "收势"]

    # 绑定 WEAPON_/VFX_ 合并进新剧 asset_registry，参考图落到新剧路径
    areg = json.loads((target / "出图/共享/asset_registry.json").read_text(encoding="utf-8"))
    ids = {a["id"] for a in areg["assets"]}
    assert {"WEAPON_DAGGER", "VFX_DARKGOLD"} <= ids
    assert (target / "出图/共享/图片/定妆_短匕.png").is_file()
    assert (target / "出图/共享/图片/定妆_暗金妖力.png").is_file()


def test_import_combat_duplicate_id_requires_replace(tmp_path):
    source = _source_combat_project(tmp_path)
    library = tmp_path / "资产库"
    assert market.main(["export-combat", str(source), "--library", str(library), "--slug", "套路A"]) == 0
    pack = library / "combat" / "套路A"
    target = tmp_path / "制漫剧" / "目标剧"
    assert market.main(["import-combat", str(target), str(pack)]) == 0
    # 同 combat_id 再导入应被拒（除非 --replace）
    assert market.main(["import-combat", str(target), str(pack)]) == 2
    assert market.main(["import-combat", str(target), str(pack), "--replace"]) == 0
