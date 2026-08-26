import importlib.util
import json
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("image_prompt_pack.py")
SPEC = importlib.util.spec_from_file_location("image_prompt_pack_project_scope", MODULE_PATH)
ipp = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = ipp
SPEC.loader.exec_module(ipp)


def test_character_free_and_asset_free_story_returns_empty_defs(tmp_path: Path) -> None:
    story = {"clips": [{"id": "Clip_01", "description": "无人物无道具的空镜"}]}

    assert ipp.derive_character_defs(tmp_path, story) == {}
    assert ipp.derive_asset_defs(tmp_path, story) == {}


def test_missing_character_and_asset_ids_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ipp.PromptPackContractError, match="CHAR_MISSING"):
        ipp.derive_character_defs(tmp_path, {"clips": [{"character_ids": ["CHAR_MISSING"]}]})
    with pytest.raises(ipp.PromptPackContractError, match="PROP_MISSING"):
        ipp.derive_asset_defs(tmp_path, {"clips": [{"object_ids": ["PROP_MISSING"]}]})


def test_modern_project_definition_never_inherits_ancient_fallback(tmp_path: Path) -> None:
    story = {
        "clips": [{"character_ids": ["CHAR_DESIGNER"]}],
        "character_materials": {
            "CHAR_DESIGNER": {
                "name": "林然",
                "profile": "当代上海产品设计师，短卷发，银灰连帽卫衣，黑色阔腿裤"
            }
        },
    }

    cfg = ipp.derive_character_defs(tmp_path, story)["CHAR_DESIGNER"]
    serialized = json.dumps(cfg, ensure_ascii=False)

    assert "林然" in serialized
    assert "银灰连帽卫衣" in serialized
    assert "古装" not in serialized
    assert "道袍" not in serialized
    assert "王敦" not in serialized


def test_demo_fixture_is_not_loaded_by_production_module() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "demo_project_defs.json").read_text(encoding="utf-8"))

    assert fixture["fixture_only"] is True
    assert ipp.CHARACTER_DEFS == {}
    assert ipp.ASSET_DEFS == {}
    assert ipp.ASSET_ID_HINTS == {}
