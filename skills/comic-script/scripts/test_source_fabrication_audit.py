from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("source_fabrication_audit.py")
SPEC = importlib.util.spec_from_file_location("comic_source_fabrication_audit", MODULE_PATH)
assert SPEC and SPEC.loader
sfa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sfa)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def project(root: Path, panels: list[dict], *, source: str = "", registry_alias: str = "", bible: str = "") -> Path:
    write_json(root / "脚本" / "第2话" / "panel_script.json", {"panels": panels})
    if source:
        (root / "源本").mkdir(parents=True, exist_ok=True)
        (root / "源本" / "选段.txt").write_text(source, encoding="utf-8")
    assets = {}
    if registry_alias:
        assets["MON_X"] = {"id": "MON_X", "type": "monster", "display_name": registry_alias}
    write_json(root / "出图" / "共享" / "identity_registry.json", {"assets": assets})
    if bible:
        (root / "设定库").mkdir(parents=True, exist_ok=True)
        (root / "设定库" / "story_bible.md").write_text(bible, encoding="utf-8")
    return root


def codes(report: dict) -> list[str]:
    return [f["code"] for f in report["findings"]]


def test_fabricated_title_in_dialogue_warns(tmp_path: Path) -> None:
    project(tmp_path, [{"panel_id": "P001", "text_target": "玄冥长老驾到！"}], source="妇独居，知为狐。")
    report = sfa.audit(tmp_path, "第2话")
    assert codes(report) == ["fabricated_entity_candidate"]
    assert report["findings"][0]["term"] == "玄冥长老"
    assert report["summary"]["warn"] == 1


def test_term_present_in_source_is_clean(tmp_path: Path) -> None:
    project(tmp_path, [{"panel_id": "P001", "narration": "白莲教主现身。"}], source="世传白莲教主徐鸿儒。")
    assert codes(sfa.audit(tmp_path, "第2话")) == []


def test_term_in_panel_source_excerpt_is_clean(tmp_path: Path) -> None:
    project(tmp_path, [{
        "panel_id": "P001", "dialogue": "见过青云掌门。",
        "source_excerpt": "S001：青云掌门赴会。",
    }])
    assert codes(sfa.audit(tmp_path, "第2话")) == []


def test_registry_or_bible_accounted_terms_downgrade_to_info(tmp_path: Path) -> None:
    project(
        tmp_path,
        [{"panel_id": "P001", "text_target": "长鬣道长与赤霞仙子同至。"}],
        source="狐来，媪觉。",
        registry_alias="长鬣道长",
        bible="# 设定\n新增角色：赤霞仙子（合并原文两名婢女）。",
    )
    report = sfa.audit(tmp_path, "第2话")
    assert codes(report) == ["adaptation_new_term_accounted", "adaptation_new_term_accounted"]
    assert report["summary"]["warn"] == 0


def test_fabricated_term_in_description_warns_as_visual(tmp_path: Path) -> None:
    project(tmp_path, [{"panel_id": "P003", "description": "画面中黑风王爷立于门前。"}], source="夜半门响。")
    report = sfa.audit(tmp_path, "第2话")
    assert codes(report) == ["fabricated_entity_candidate"]
    assert "画出来" in report["findings"][0]["message"]


def test_generic_and_connective_prefixes_are_ignored(tmp_path: Path) -> None:
    project(tmp_path, [{"panel_id": "P001", "narration": "那位夫人要是长老便罢。"}], source="有妇人焉。")
    assert codes(sfa.audit(tmp_path, "第2话")) == []


def test_bracketed_new_title_is_flagged_once_across_panels(tmp_path: Path) -> None:
    project(tmp_path, [
        {"panel_id": "P001", "text_target": "此乃《万妖真经》！"},
        {"panel_id": "P002", "narration": "《万妖真经》再现。"},
    ], source="书生读书。")
    report = sfa.audit(tmp_path, "第2话")
    assert codes(report) == ["fabricated_entity_candidate"]


def test_missing_panel_script_yields_empty_report(tmp_path: Path) -> None:
    report = sfa.audit(tmp_path, "第2话")
    assert report["findings"] == []
    assert report["summary"]["panels"] == 0
