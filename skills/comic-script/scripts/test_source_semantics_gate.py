#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
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
