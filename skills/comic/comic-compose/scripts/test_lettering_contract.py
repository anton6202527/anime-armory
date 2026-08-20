#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_lettering
import export_longstrip
import lettering_contract


CHAPTER = "第1话"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project_payloads() -> tuple[dict, dict, dict]:
    panel_script = {
        "chapter": CHAPTER,
        "panels": [
            {
                "panel_id": "P001",
                "narration_target": "夜色降临。",
                "dialogue": [
                    {"speaker": "甲", "text_target": "走吧。", "tone": "克制"},
                    {"speaker": "乙", "text_target": "走吧。", "tone": "催促"},
                ],
                "sfx": [{"text_target": "咔", "source": "门锁"}],
            }
        ],
    }
    layout = {
        "segments": [
            {
                "panels": [
                    {
                        "panel_id": "P001",
                        "bubble_slots": [
                            {"slot_id": "N1", "type": "narration", "content_ref": "panel:P001.narration"},
                            {"slot_id": "D1", "type": "dialogue", "content_ref": "panel:P001.dialogue:1", "speaker": "甲"},
                            {"slot_id": "D2", "type": "dialogue", "content_ref": "panel:P001.dialogue:2", "speaker": "乙"},
                            {"slot_id": "S1", "type": "sfx", "content_ref": "panel:P001.sfx:1"},
                        ],
                    }
                ]
            }
        ]
    }
    finishing = {
        "panels": [
            {
                "panel_id": "P001",
                "lettering_sfx_plan": {"mode": "drawn_sfx", "shape": "angular"},
            }
        ]
    }
    return panel_script, layout, finishing


def build_project(
    tmp_path: Path,
    translations: dict[str, object] | None = None,
    *,
    editorial_overrides: dict[str, dict] | None = None,
) -> tuple[Path, dict]:
    root = tmp_path / "作品"
    panel_script, layout, finishing = project_payloads()
    panel_path = root / "脚本" / CHAPTER / "panel_script.json"
    layout_path = root / "排版" / CHAPTER / "layout.json"
    finishing_path = root / "出图" / CHAPTER / "finishing" / "finishing_plan.json"
    translation_path = root / "排版" / CHAPTER / "lettering_translations.json"
    lettering_path = root / "排版" / CHAPTER / "lettering.json"
    write_json(panel_path, panel_script)
    write_json(layout_path, layout)
    write_json(finishing_path, finishing)
    if translations is not None:
        write_json(translation_path, {"translations": translations})
    bindings = {
        "panel_script": lettering_contract.binding_for_path(root, panel_path),
        "layout": lettering_contract.binding_for_path(root, layout_path),
        "finishing_plan": lettering_contract.binding_for_path(root, finishing_path),
        "translation_map": lettering_contract.binding_for_path(root, translation_path),
    }
    lettering = build_lettering.build_lettering(
        panel_script,
        layout,
        translations or {},
        "中上英下",
        build_lettering.finishing_by_panel(finishing),
        source_bindings=bindings,
        editorial_overrides=editorial_overrides,
    )
    write_json(lettering_path, lettering)
    return root, lettering


def finding_codes(report: dict) -> set[str]:
    return {str(item.get("code")) for item in report.get("findings") or []}


def bound_translation(text_en: str, source_text: str) -> dict[str, str]:
    return {
        "text_en": text_en,
        "source_text_sha256": lettering_contract.sha256_text(source_text),
    }


def test_build_entry_writes_all_current_source_bindings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "入口作品"
    panel_script, layout, finishing = project_payloads()
    write_json(root / "脚本" / CHAPTER / "panel_script.json", panel_script)
    write_json(root / "排版" / CHAPTER / "layout.json", layout)
    write_json(root / "出图" / CHAPTER / "finishing" / "finishing_plan.json", finishing)
    monkeypatch.setattr(sys, "argv", ["build_lettering.py", str(root), "--chapter", CHAPTER])

    assert build_lettering.main() == 0

    lettering = json.loads((root / "排版" / CHAPTER / "lettering.json").read_text(encoding="utf-8"))
    assert lettering["schema_version"] == 2
    assert set(lettering["source_bindings"]) == set(lettering_contract.REQUIRED_BINDINGS)
    assert lettering["source_bindings"]["translation_map"] == {
        "path": f"排版/{CHAPTER}/lettering_translations.json",
        "exists": False,
        "sha256": "",
    }
    assert lettering_contract.analyze(root, CHAPTER)["verdict"] == "pass"


def test_every_text_type_has_stable_ref_and_source_sha_and_ref_translation(tmp_path: Path) -> None:
    translations = {
        "panel:P001.narration": bound_translation("Night fell.", "夜色降临。"),
        "panel:P001.dialogue:1": bound_translation("Let's go.", "走吧。"),
        "panel:P001.dialogue:2": bound_translation("Move. Now.", "走吧。"),
        "panel:P001.sfx:1": bound_translation("CLICK", "咔"),
    }
    root, lettering = build_project(tmp_path, translations)

    by_ref = {item["content_ref"]: item for item in lettering["items"]}
    assert set(by_ref) == set(translations)
    assert by_ref["panel:P001.dialogue:1"]["text_en"] == "Let's go."
    assert by_ref["panel:P001.dialogue:2"]["text_en"] == "Move. Now."
    assert all(item["source_text_sha256"] == lettering_contract.sha256_text(item["source_text"]) for item in by_ref.values())
    assert all(item["translation_binding"]["resolution"] == "content_ref_sha256" for item in by_ref.values())
    assert lettering["translation_usage"] == {
        "content_ref_count": 4,
        "legacy_text_key_count": 0,
        "legacy_content_refs": [],
        "unbound_content_ref_count": 0,
        "unbound_content_refs": [],
        "stale_content_ref_count": 0,
        "stale_content_refs": [],
        "invalid_content_ref_count": 0,
        "invalid_content_refs": [],
    }
    assert all(
        set(lettering["source_bindings"][name]) == {"path", "exists", "sha256"}
        for name in lettering_contract.REQUIRED_BINDINGS
    )
    assert lettering_contract.analyze(root, CHAPTER)["verdict"] == "pass"


def test_legacy_text_key_is_compatible_but_warned(tmp_path: Path) -> None:
    root, lettering = build_project(tmp_path, {"走吧。": "Let's go."})

    dialogue = [item for item in lettering["items"] if item["type"] == "dialogue"]
    assert [item["text_en"] for item in dialogue] == ["Let's go.", "Let's go."]
    assert all(item["translation_binding"]["resolution"] == "legacy_text_key" for item in dialogue)
    report = lettering_contract.analyze(root, CHAPTER)
    assert report["verdict"] == "warn"
    assert "lettering_translation_legacy_text_key" in finding_codes(report)


def test_unbound_content_ref_string_is_not_applied_and_warns(tmp_path: Path) -> None:
    root, lettering = build_project(tmp_path, {"panel:P001.dialogue:1": "Let's go."})
    item = next(item for item in lettering["items"] if item["content_ref"] == "panel:P001.dialogue:1")

    assert "text_en" not in item
    assert item["translation_binding"]["resolution"] == "content_ref_unbound"
    report = lettering_contract.analyze(root, CHAPTER)
    assert report["verdict"] == "warn"
    assert "lettering_translation_content_ref_unbound" in finding_codes(report)


def test_same_content_ref_old_translation_becomes_stale_after_script_rebuild(tmp_path: Path) -> None:
    root, _lettering = build_project(
        tmp_path,
        {"panel:P001.dialogue:1": bound_translation("Let's go.", "走吧。")},
    )
    panel_path = root / "脚本" / CHAPTER / "panel_script.json"
    layout_path = root / "排版" / CHAPTER / "layout.json"
    finishing_path = root / "出图" / CHAPTER / "finishing" / "finishing_plan.json"
    translation_path = root / "排版" / CHAPTER / "lettering_translations.json"
    panel_script = json.loads(panel_path.read_text(encoding="utf-8"))
    panel_script["panels"][0]["dialogue"][0]["text_target"] = "别走。"
    write_json(panel_path, panel_script)
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    finishing = json.loads(finishing_path.read_text(encoding="utf-8"))
    translations = build_lettering.load_translation_map(translation_path)
    bindings = {
        "panel_script": lettering_contract.binding_for_path(root, panel_path),
        "layout": lettering_contract.binding_for_path(root, layout_path),
        "finishing_plan": lettering_contract.binding_for_path(root, finishing_path),
        "translation_map": lettering_contract.binding_for_path(root, translation_path),
    }

    rebuilt = build_lettering.build_lettering(
        panel_script,
        layout,
        translations,
        "中上英下",
        build_lettering.finishing_by_panel(finishing),
        source_bindings=bindings,
    )
    write_json(root / "排版" / CHAPTER / "lettering.json", rebuilt)
    item = next(item for item in rebuilt["items"] if item["content_ref"] == "panel:P001.dialogue:1")

    assert item["source_text"] == "别走。"
    assert "text_en" not in item, "旧位置译文不得静默套到新原句"
    assert item["translation_binding"]["resolution"] == "content_ref_stale"
    report = lettering_contract.analyze(root, CHAPTER)
    assert report["verdict"] == "block"
    assert "lettering_translation_source_stale" in finding_codes(report)


@pytest.mark.parametrize("binding_name", ["panel_script", "layout", "finishing_plan", "translation_map"])
def test_any_bound_input_change_invalidates_lettering(tmp_path: Path, binding_name: str) -> None:
    root, _lettering = build_project(
        tmp_path,
        {"panel:P001.dialogue:1": bound_translation("Let's go.", "走吧。")},
    )
    binding_paths = {
        "panel_script": root / "脚本" / CHAPTER / "panel_script.json",
        "layout": root / "排版" / CHAPTER / "layout.json",
        "finishing_plan": root / "出图" / CHAPTER / "finishing" / "finishing_plan.json",
        "translation_map": root / "排版" / CHAPTER / "lettering_translations.json",
    }
    payload = json.loads(binding_paths[binding_name].read_text(encoding="utf-8"))
    payload["changed_after_lettering"] = True
    write_json(binding_paths[binding_name], payload)

    report = lettering_contract.analyze(root, CHAPTER)

    assert report["verdict"] == "block"
    assert "lettering_source_binding_stale" in finding_codes(report)


def test_script_text_change_is_detected_even_if_gate_is_rerun(tmp_path: Path) -> None:
    root, _lettering = build_project(tmp_path)
    panel_path = root / "脚本" / CHAPTER / "panel_script.json"
    panel_script = json.loads(panel_path.read_text(encoding="utf-8"))
    panel_script["panels"][0]["dialogue"][0]["text_target"] = "别走。"
    write_json(panel_path, panel_script)

    report = lettering_contract.analyze(root, CHAPTER)

    assert report["verdict"] == "block"
    assert "lettering_source_binding_stale" in finding_codes(report)
    assert "lettering_source_text_stale" in finding_codes(report)


def test_silent_text_edit_blocks_without_editorial_override(tmp_path: Path) -> None:
    root, lettering = build_project(tmp_path)
    dialogue = next(item for item in lettering["items"] if item["content_ref"] == "panel:P001.dialogue:1")
    dialogue["text"] = "我擅自改了。"
    dialogue["text_zh"] = "我擅自改了。"
    write_json(root / "排版" / CHAPTER / "lettering.json", lettering)

    report = lettering_contract.analyze(root, CHAPTER)

    assert report["verdict"] == "block"
    assert "lettering_text_diverged_without_override" in finding_codes(report)


def test_editorial_override_is_sha_bound_and_becomes_stale_with_source(tmp_path: Path) -> None:
    source_sha = lettering_contract.sha256_text("走吧。")
    override = {
        "content_ref": "panel:P001.dialogue:1",
        "source_text_sha256": source_sha,
        "replacement": {"text": "现在出发。", "text_zh": "现在出发。"},
        "reason": "口语节奏优化",
        "reviewed_by": "责任编辑",
        "reviewed_at": "2026-08-20T10:00:00+08:00",
    }
    root, lettering = build_project(
        tmp_path,
        editorial_overrides={"panel:P001.dialogue:1": override},
    )
    item = next(item for item in lettering["items"] if item["content_ref"] == "panel:P001.dialogue:1")
    assert item["text_zh"] == "现在出发。"
    assert lettering_contract.analyze(root, CHAPTER)["verdict"] == "pass"

    panel_path = root / "脚本" / CHAPTER / "panel_script.json"
    panel_script = json.loads(panel_path.read_text(encoding="utf-8"))
    panel_script["panels"][0]["dialogue"][0]["text_target"] = "快走。"
    write_json(panel_path, panel_script)
    report = lettering_contract.analyze(root, CHAPTER)
    assert "lettering_editorial_override_invalid" in finding_codes(report)


def test_export_manifest_binds_current_lettering_sha(tmp_path: Path) -> None:
    root, _lettering = build_project(tmp_path)
    panel_dir = root / "出图" / CHAPTER / "panels"
    out_dir = root / "排版" / CHAPTER / "长图"
    page_dir = root / "排版" / CHAPTER / "pages"
    panel_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    page_dir.mkdir(parents=True)
    lettering_path = root / "排版" / CHAPTER / "lettering.json"

    manifest = export_longstrip.build_manifest(
        root,
        CHAPTER,
        root / "排版" / CHAPTER / "layout.json",
        panel_dir,
        out_dir,
        page_dir,
        0,
        lettering_path,
        "",
        ["webp"],
    )

    assert manifest["lettering_sha256"] == lettering_contract.sha256_file(lettering_path)


def test_export_entry_refuses_stale_lettering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _lettering = build_project(tmp_path)
    panel_path = root / "脚本" / CHAPTER / "panel_script.json"
    panel_script = json.loads(panel_path.read_text(encoding="utf-8"))
    panel_script["panels"][0]["narration_target"] = "天已经亮了。"
    write_json(panel_path, panel_script)
    monkeypatch.setattr(sys, "argv", ["export_longstrip.py", str(root), "--chapter", CHAPTER])

    assert export_longstrip.main() == 2
    assert not (root / "排版" / CHAPTER / "export_manifest.json").exists()
