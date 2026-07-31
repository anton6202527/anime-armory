#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import source_semantics_gate as gate


def test_guess_classical_chinese_requires_normalization() -> None:
    text = "太祖曰：吾闻其人也，遂命左右召之。既至，众皆拜，曰：善哉。"
    language, reasons = gate.guess_source_language(text)
    assert language == "文言/古汉语"
    assert reasons


def test_guess_latin_foreign_text() -> None:
    language, reasons = gate.guess_source_language("The old house stood by the river, and nobody returned at night.")
    assert language == "英文/拉丁字母外语"
    assert "latin_script_majority" in reasons


def test_validate_blocks_unfilled_required_segments(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    source = root / "source.md"
    source.write_text("The old house stood by the river.", encoding="utf-8")
    records, text = gate.load_source_texts(root, [source])
    report = gate.scaffold_report(
        root,
        "第1话",
        records,
        text,
        "英文/拉丁字母外语",
        ["latin_script_majority"],
        "中文",
        False,
        3,
    )
    verdict, issues = gate.validate_report(report)
    assert verdict == "block"
    assert any("meaning_zh" in item for item in issues)


def test_validate_passes_filled_report(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    source = root / "source.md"
    source.write_text("The old house stood by the river.", encoding="utf-8")
    records, text = gate.load_source_texts(root, [source])
    report = gate.scaffold_report(
        root,
        "第1话",
        records,
        text,
        "英文/拉丁字母外语",
        ["latin_script_majority"],
        "中文",
        False,
        3,
    )
    report["glossary_reviewed"] = True
    report["ambiguity_reviewed"] = True
    report["segments"][0].update(
        {
            "meaning_zh": "老房子立在河边。",
            "text_target": "河边那栋老屋，还在。",
            "adaptation_decision": "成旁白",
            "adaptation_note": "压缩成开场旁白，并保留地点信息。",
        }
    )
    verdict, issues = gate.validate_report(json.loads(json.dumps(report, ensure_ascii=False)))
    assert verdict == "pass"
    assert issues == []


def test_default_sources_skip_manifest(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source_dir = root / "源本"
    source_dir.mkdir(parents=True)
    (source_dir / "source_manifest.json").write_text('{"kind":"manifest"}', encoding="utf-8")
    (source_dir / "story.txt").write_text("第一章 正文", encoding="utf-8")
    paths = gate.candidate_source_paths(root, [])
    assert [path.name for path in paths] == ["story.txt"]


def test_scaffold_slices_source_by_chapter_heading(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    source = root / "source.txt"
    source.write_text(
        "# === 抓取来源信息 (provenance) ===\n"
        "# source_url: example\n"
        "# ================================================================\n\n"
        "第1章 旧事\n一曰旧事。\n\n第2章 新事\n二曰新事。\n\n第3章 后事\n三曰后事。",
        encoding="utf-8",
    )
    records, text = gate.load_source_texts(root, [source])
    report = gate.scaffold_report(
        root,
        "第2话",
        records,
        text,
        "文言/古汉语",
        ["manual_source_language"],
        "中文",
        True,
        3,
    )
    excerpts = [segment["source_excerpt"] for segment in report["segments"]]
    assert any("第2章 新事" in item for item in excerpts)
    assert all("source_url" not in item for item in excerpts)
    assert all("第1章" not in item for item in excerpts)


def test_docx_source_is_discovered_and_extracted(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source_dir = root / "源本"
    source_dir.mkdir(parents=True)
    docx = source_dir / "古书.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>第1章 第一回</w:t></w:r></w:p>
    <w:p><w:r><w:t>太祖曰：</w:t><w:tab/><w:t>善哉。</w:t></w:r></w:p>
    <w:p><w:r><w:t>第2章 第二回</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(docx, "w") as archive:
        archive.writestr("word/document.xml", document_xml)

    paths = gate.candidate_source_paths(root, [])
    assert paths == [docx]
    records, text = gate.load_source_texts(root, paths)
    assert records[0]["format"] == "docx"
    assert "第1章 第一回" in text
    assert "太祖曰：\t善哉。" in text

    report = gate.scaffold_report(
        root,
        "第1话",
        records,
        text,
        "文言/古汉语",
        ["manual_source_language"],
        "中文",
        True,
        4,
    )
    excerpts = [segment["source_excerpt"] for segment in report["segments"]]
    assert any("太祖曰" in item for item in excerpts)
    assert all("第2章" not in item for item in excerpts)


def test_explicit_wikisource_wrapper_noise_is_removed_from_docx_and_txt(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source_dir = root / "源本"
    source_dir.mkdir(parents=True)

    docx = source_dir / "source.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>第1章 正文</w:t></w:r></w:p>
    <w:p><w:r><w:t>Public domainPublic domainfalsefalse</w:t></w:r></w:p>
    <w:p><w:r><w:t>且听下回分解。</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(docx, "w") as archive:
        archive.writestr("word/document.xml", document_xml)

    txt = source_dir / "source.txt"
    txt.write_text(
        "第1章 正文\n\nPublic domain\nPublic domain\nfalse\nfalse\n\n且听下回分解。",
        encoding="utf-8",
    )

    for path in (docx, txt):
        cleaned = gate.read_text(path)
        assert "Public domain" not in cleaned
        assert "falsefalse" not in cleaned.replace("\n", "")
        assert "第1章 正文" in cleaned
        assert "且听下回分解。" in cleaned
        assert all(
            "publicdomainpublicdomainfalsefalse"
            not in gate._wrapper_signature_key(segment)
            for segment in gate.split_segments(gate.strip_source_provenance(cleaned))
        )


def test_wrapper_cleanup_preserves_public_domain_prose_and_partial_tokens() -> None:
    text = (
        "The editor said this chapter is in the public domain.\n"
        "Public domain.\n"
        "false false\n"
        "角色念道：Public domainPublic domainfalsefalse，不可当作包装。"
    )
    assert gate.strip_explicit_source_wrapper_noise(text) == text


def _contract(source_path: str = "源本/story.txt") -> dict:
    return {
        "chapter": "第1话",
        "chapter_type": "serial",
        "format_profile": "vertical_serial",
        "source_mode": "adapted",
        "source_spans": [{"span_id": "SPAN_001", "source_path": source_path, "start": "第二章", "end": "第三章"}],
        "reader_promise": "反击",
        "core_conflict": "封锁",
        "turning_point": "旧友出现",
        "payoff": "出口打开",
        "ending_mode": "decision",
        "budget": {"unit": "panels", "soft_range": [20, 40]},
        "entry_state": {"story": "trapped"},
        "continuity_delta": [{"entity_id": "STORY_MAIN", "field": "state", "from": "trapped", "to": "escaped", "panel_id": "P001", "reason": "door opened"}],
        "exit_state": {"story": "escaped"},
        "status": "confirmed",
    }


def _scaffold_from_contract(root: Path, contract: dict) -> dict:
    records, selections = gate.load_contract_source_spans(root, contract)
    source_text = "\n\n".join(item.get("text", "") for item in selections if item.get("status") == "read")
    return gate.scaffold_report(
        root, "第1话", records, source_text, "现代中文", ["manual_source_language"], "中文", False, 12,
        chapter_contract_data=contract, source_selections=selections,
    )


def test_contract_source_spans_override_chapter_number_and_support_cross_range(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = root / "源本" / "story.txt"
    source.parent.mkdir(parents=True)
    source.write_text(
        "第一章 一\n不应入选\n第二章 二\n正文二\n第三章 三\n正文三\n第四章 四\n不应入选",
        encoding="utf-8",
    )
    report = _scaffold_from_contract(root, _contract())
    excerpts = "\n".join(segment["source_excerpt"] for segment in report["segments"])
    assert "正文二" in excerpts and "正文三" in excerpts
    assert "不应入选" not in excerpts
    assert report["source_slice"]["strategy"] == "split_blueprint.source_spans"
    assert report["source_files"][0]["sha256"]


def test_split_segments_never_silently_truncates_after_twelve() -> None:
    text = "\n\n".join(f"第{i}段内容。" for i in range(1, 21))
    segments = gate.split_segments(text, 12)
    assert len(segments) == 20
    assert "第20段内容" in segments[-1]


def test_missing_or_unmatched_contract_source_is_deterministic_block(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    missing = _scaffold_from_contract(root, _contract())
    verdict, issues = gate.validate_report(missing)
    assert verdict == "block"
    assert any("source file" in issue or "source span" in issue for issue in issues)

    source = root / "源本" / "story.txt"
    source.parent.mkdir(parents=True)
    source.write_text("第一章\n只有第一章", encoding="utf-8")
    unmatched = _scaffold_from_contract(root, _contract())
    verdict2, issues2 = gate.validate_report(unmatched)
    assert verdict2 == "block"
    assert any("source span" in issue for issue in issues2)


def test_adaptation_decisions_and_panel_segment_coverage(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = root / "源本" / "story.txt"
    source.parent.mkdir(parents=True)
    source.write_text("第二章\n甲做事。\n\n乙回应。\n第三章\n丙收尾。", encoding="utf-8")
    report = _scaffold_from_contract(root, _contract())
    for segment in report["segments"]:
        segment["adaptation_decision"] = "成画面"
        segment["adaptation_note"] = "保留为画面动作"
    verdict, issues = gate.validate_report(report)
    assert verdict == "pass" and issues == []
    assert report["panel_coverage"]["status"] == "pending_panel_script"

    first_id = report["segments"][0]["segment_id"]
    panel_script = {"panels": [{"panel_id": "P001", "source_segment_refs": [first_id]}]}
    verdict2, issues2 = gate.validate_report(report, panel_script)
    assert verdict2 == "block"
    assert any("lack panel coverage" in issue for issue in issues2)

    panel_script["panels"][0]["source_segment_refs"] = [segment["segment_id"] for segment in report["segments"]]
    verdict3, issues3 = gate.validate_report(report, panel_script)
    assert verdict3 == "pass" and issues3 == []


def test_deleted_or_deferred_segment_does_not_require_panel_reference(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = root / "源本" / "story.txt"
    source.parent.mkdir(parents=True)
    source.write_text("第二章\n甲。\n\n乙。\n第三章\n丙。", encoding="utf-8")
    report = _scaffold_from_contract(root, _contract())
    for segment in report["segments"]:
        segment["adaptation_decision"] = "删除"
        segment["adaptation_note"] = "经合同决定删除"
    coverage, issues = gate.validate_panel_coverage(report, {"panels": []})
    assert coverage["status"] == "pass"
    assert issues == []


def test_explicit_original_bridge_panel_can_have_no_source_ref(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = root / "源本" / "story.txt"
    source.parent.mkdir(parents=True)
    source.write_text("第二章\n甲。\n第三章\n乙。", encoding="utf-8")
    report = _scaffold_from_contract(root, _contract())
    for segment in report["segments"]:
        segment["adaptation_decision"] = "删除"
        segment["adaptation_note"] = "当前话不采用"
    panel_script = {"panels": [{
        "panel_id": "P001", "adaptation_origin": "original_bridge", "adaptation_note": "补一格空间承接",
    }]}
    coverage, issues = gate.validate_panel_coverage(report, panel_script)
    assert coverage["status"] == "pass" and issues == []


def test_source_or_contract_sha_change_makes_existing_report_stale(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = root / "源本" / "story.txt"
    source.parent.mkdir(parents=True)
    source.write_text("第二章\n正文二。\n第三章\n正文三。", encoding="utf-8")
    contract = _contract()
    report = _scaffold_from_contract(root, contract)
    assert gate.refresh_staleness(root, report, contract) == []
    source.write_text("第二章\n正文改了。\n第三章\n正文三。", encoding="utf-8")
    assert any("source SHA changed" in reason for reason in gate.refresh_staleness(root, report, contract))
    changed_contract = json.loads(json.dumps(contract, ensure_ascii=False))
    changed_contract["reader_promise"] = "改变后的承诺"
    assert any("chapter contract SHA changed" in reason for reason in gate.refresh_staleness(root, report, changed_contract))
