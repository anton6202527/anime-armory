from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import dependency_index


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def fixture(root: Path) -> None:
    panel = {"panel_id": "P001", "description": "甲持刀入门"}
    write_json(root / "脚本/第1话/panel_script.json", {"panels": [panel]})
    write_json(root / "排版/第1话/layout.json", {"segments": [{"page_id": "page_1", "panels": [{"panel_id": "P001"}]}]})
    translation_path = root / "排版/第1话/lettering_translations.json"
    write_json(translation_path, {"translations": {
        "panel:P001.dialogue:1": {"text_en": "Who goes there?", "source_text_sha256": "source-v1"},
    }})
    write_json(root / "排版/第1话/lettering.json", {
        "source_bindings": {"translation_map": {"path": str(translation_path.relative_to(root))}},
        "items": [{
            "panel_id": "P001", "content_ref": "panel:P001.dialogue:1",
            "source_text": "来者何人", "text": "来者何人",
        }],
    })
    image = root / "出图/共享/图片/CHAR_A__front.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), "red").save(image)
    result = root / "出图/第1话/panels/P001.png"
    result.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), "white").save(result)
    write_json(root / "出图/共享/identity_registry.json", {"assets": {"CHAR_A": {"name": "甲", "views": {"front": str(image.relative_to(root))}}}})
    write_json(root / "出图/第1话/prompt/panel_jobs.json", {"jobs": [{
        "panel_id": "P001", "execution_input_sha256": "job-v1", "result_path": str(result.relative_to(root)),
        "references": [{"id": "CHAR_A", "path": str(image.relative_to(root))}],
    }]})


def test_reference_pixel_change_targets_only_consuming_panel(tmp_path: Path) -> None:
    fixture(tmp_path)
    before = dependency_index.build_index(tmp_path)
    Image.new("RGB", (32, 32), "blue").save(tmp_path / "出图/共享/图片/CHAR_A__front.png")
    after = dependency_index.build_index(tmp_path)
    impacts = dependency_index.compare_indices(before, after)
    assert impacts[0]["chapter"] == "第1话"
    assert impacts[0]["panel_targets"] == ["P001"]
    assert impacts[0]["from_stage"] == "image"
    assert "reference_or_registry_asset_changed" in impacts[0]["panels"][0]["reasons"]


def test_dialogue_change_routes_panel_to_script(tmp_path: Path) -> None:
    fixture(tmp_path)
    before = dependency_index.build_index(tmp_path)
    write_json(tmp_path / "脚本/第1话/panel_script.json", {"panels": [{"panel_id": "P001", "description": "乙持刀入门"}]})
    after = dependency_index.build_index(tmp_path)
    impacts = dependency_index.compare_indices(before, after)
    assert impacts[0]["from_stage"] == "script"
    assert impacts[0]["page_targets"] == ["page_1"]


def test_translation_map_targets_only_consumed_content_refs(tmp_path: Path) -> None:
    fixture(tmp_path)
    before = dependency_index.build_index(tmp_path)
    translation_path = tmp_path / "排版/第1话/lettering_translations.json"
    payload = json.loads(translation_path.read_text(encoding="utf-8"))
    payload["translations"]["unused.ref"] = {"text_en": "unused", "source_text_sha256": "unused"}
    write_json(translation_path, payload)
    after_unused = dependency_index.build_index(tmp_path)
    assert dependency_index.compare_indices(before, after_unused) == []

    payload["translations"]["panel:P001.dialogue:1"]["text_en"] = "Identify yourself."
    write_json(translation_path, payload)
    after_used = dependency_index.build_index(tmp_path)
    impacts = dependency_index.compare_indices(after_unused, after_used)
    assert impacts[0]["panel_targets"] == ["P001"]
    assert impacts[0]["from_stage"] == "compose"
    assert impacts[0]["panels"][0]["reasons"] == ["lettering_changed"]
