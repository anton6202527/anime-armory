from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import registry_v2


def test_migration_adds_structured_character_contract_and_normalizes_types() -> None:
    migrated, info = registry_v2.migrate_registry({
        "schema_version": 1,
        "assets": {
            "CHAR_A": {"id": "CHAR_A", "type": "character", "status": "ready", "views": {}},
            "VFX_FIRE": {"id": "VFX_FIRE", "type": "fx"},
            "FX_SMOKE": {"id": "FX_SMOKE"},
            "SYS_UI": {"id": "SYS_UI"},
            "PROP_SWORD": {"id": "PROP_SWORD"},
            "OUTFIT_RED": {"id": "OUTFIT_RED"},
        },
    })
    char = migrated["assets"]["CHAR_A"]
    assert migrated["schema_version"] == 2 and info["from_version"] == 1
    assert char["status"] == "needs_approval"
    assert set(char["default_binding"]) == {"form_id", "outfit_id", "expression_id", "state_id"}
    assert char["default_binding"]["state_id"] in char["states"]
    assert migrated["assets"]["VFX_FIRE"]["type"] == "vfx"
    assert migrated["assets"]["FX_SMOKE"]["type"] == "vfx"
    assert migrated["assets"]["SYS_UI"]["type"] == "system_asset"
    assert migrated["assets"]["PROP_SWORD"]["type"] == "prop"
    assert migrated["assets"]["OUTFIT_RED"]["type"] == "outfit"
    assert registry_v2.validate_registry(migrated)["valid"] is True


def test_validator_blocks_unknown_state_links() -> None:
    migrated, _ = registry_v2.migrate_registry({"assets": {"CHAR_A": {"id": "CHAR_A", "type": "character"}}})
    migrated["assets"]["CHAR_A"]["states"]["STATE_BASE"]["outfit_id"] = "OUTFIT_UNKNOWN"
    report = registry_v2.validate_registry(migrated)
    assert report["valid"] is False
    assert any(item["code"] == "state_outfit_id_unknown" for item in report["issues"])


def test_empty_registry_is_valid_and_contains_no_fake_ready_assets() -> None:
    registry = registry_v2.new_registry(source="test")
    assert registry_v2.validate_registry(registry)["valid"] is True
    assert registry["assets"] == {}
    assert registry["schema_meta"]["initialized_by"] == "test"


def test_character_upsert_scaffolds_stable_default_binding_without_images() -> None:
    registry, change = registry_v2.upsert_asset(
        registry_v2.new_registry(),
        "char_lin",
        display_name="林冲",
        description="八十万禁军教头",
        library_tier="core_full",
        character_dna="豹头环眼，身材修长结实",
        forbidden_inheritance="不得继承演员脸或临时手持兵器",
    )
    character = registry["assets"]["CHAR_LIN"]
    assert change["created"] is True and change["asset_type"] == "character"
    assert character["status"] == "needs_reference"
    assert character["reference_images"] == []
    assert character["default_binding"] == {
        "form_id": "FORM_BASE",
        "outfit_id": "OUTFIT_BASE",
        "expression_id": "EXPR_NEUTRAL",
        "state_id": "STATE_BASE",
    }
    assert character["states"]["STATE_BASE"]["outfit_id"] == "OUTFIT_BASE"
    assert registry_v2.validate_registry(registry)["valid"] is True


def test_character_upsert_uses_existing_custom_variants_as_defaults() -> None:
    registry = registry_v2.new_registry()
    registry["assets"]["CHAR_CUSTOM"] = {
        "id": "CHAR_CUSTOM",
        "type": "character",
        "forms": {"FORM_ADULT": {"id": "FORM_ADULT"}},
        "outfits": {"OUTFIT_ROBE": {"id": "OUTFIT_ROBE"}},
        "expressions": {"EXPR_CALM": {"id": "EXPR_CALM"}},
        "states": {},
    }
    updated, _ = registry_v2.upsert_asset(registry, "CHAR_CUSTOM", display_name="自定义角色")
    binding = updated["assets"]["CHAR_CUSTOM"]["default_binding"]
    assert binding["form_id"] == "FORM_ADULT"
    assert binding["outfit_id"] == "OUTFIT_ROBE"
    assert binding["expression_id"] == "EXPR_CALM"
    assert updated["assets"]["CHAR_CUSTOM"]["states"][binding["state_id"]]["form_id"] == "FORM_ADULT"
    assert registry_v2.validate_registry(updated)["valid"] is True


def test_non_character_upsert_infers_all_supported_asset_types() -> None:
    registry = registry_v2.new_registry()
    expected = {
        "LOC_TEMPLE": "location",
        "PROP_SWORD": "prop",
        "STYLE_SONG": "style",
    }
    for asset_id in expected:
        registry, change = registry_v2.upsert_asset(registry, asset_id, display_name=asset_id)
        assert change["asset_type"] == expected[asset_id]
        assert registry["assets"][asset_id]["status"] == "needs_reference"
        assert registry["assets"][asset_id]["reference_images"] == []
    assert registry_v2.validate_registry(registry)["valid"] is True


def test_cli_init_and_upsert_can_bootstrap_missing_project(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    assert registry_v2.main([str(root), "init", "--write", "--json"]) == 0
    path = root / "出图" / "共享" / "identity_registry.json"
    assert path.is_file()
    assert registry_v2.main([
        str(root), "upsert", "--asset-id", "CHAR_LIN", "--name", "林冲",
        "--tier", "recurring_standard", "--write", "--json",
    ]) == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["assets"]["CHAR_LIN"]["library_tier"] == "recurring_standard"
    assert data["assets"]["CHAR_LIN"]["default_binding"]["state_id"] == "STATE_BASE"
