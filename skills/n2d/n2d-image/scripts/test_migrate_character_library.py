import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("migrate_character_library.py")
SPEC = importlib.util.spec_from_file_location("migrate_character_library", SCRIPT)
migrate_character_library = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(migrate_character_library)


def _write_project(root: Path) -> None:
    old = root / "设定库" / "character_assets" / "CHAR_HERO__hero"
    old.mkdir(parents=True)
    (old / "manifest.json").write_text(json.dumps({
        "kind": "n2d_project_character_asset_bundle",
        "character_id": "CHAR_HERO",
        "directories": {},
    }, ensure_ascii=False), encoding="utf-8")
    registry = root / "出图" / "共享" / "identity_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "kind": "n2d_identity_registry",
        "characters": [{
            "id": "CHAR_HERO",
            "name": "主角",
            "scope": "核心主角/全篇长线",
            "asset_bundle": {
                "manifest": "设定库/character_assets/CHAR_HERO__hero/manifest.json",
                "package_dir": "设定库/character_assets/CHAR_HERO__hero",
            },
            "forms": [{"reference_atlas": {"build_tier": "standard_full"}}],
        }],
    }, ensure_ascii=False), encoding="utf-8")
    (root / "notes.md").write_text("见 `设定库/character_assets/CHAR_HERO__hero`。\n", encoding="utf-8")


def test_migration_dry_run_does_not_write(tmp_path: Path) -> None:
    _write_project(tmp_path)

    report = migrate_character_library.migrate(tmp_path, apply=False)

    assert report["ok"] and report["move"]
    assert (tmp_path / "设定库" / "character_assets").is_dir()
    assert not (tmp_path / "角色库").exists()


def test_migration_moves_once_rewrites_and_adds_tiers(tmp_path: Path) -> None:
    _write_project(tmp_path)

    report = migrate_character_library.migrate(tmp_path, apply=True)

    assert report["ok"] and not report["legacy_directory_remaining"]
    assert (tmp_path / "角色库" / "CHAR_HERO__hero" / "manifest.json").is_file()
    assert "设定库/character_assets" not in (tmp_path / "notes.md").read_text(encoding="utf-8")
    registry = json.loads((tmp_path / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    char = registry["characters"][0]
    assert char["library_tier"] == "core_full"
    assert char["asset_bundle"]["manifest"].startswith("角色库/")
    assert char["forms"][0]["reference_atlas"]["build_tier"] == "core_full"
    manifest = json.loads((tmp_path / "角色库" / "CHAR_HERO__hero" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["library_tier"] == "core_full"
    assert (tmp_path / "角色库" / "README.md").is_file()


def test_migration_refuses_two_live_trees(tmp_path: Path) -> None:
    _write_project(tmp_path)
    (tmp_path / "角色库").mkdir()

    report = migrate_character_library.migrate(tmp_path, apply=True)

    assert not report["ok"] and report["status"] == "conflict"
    assert (tmp_path / "设定库" / "character_assets").is_dir()
