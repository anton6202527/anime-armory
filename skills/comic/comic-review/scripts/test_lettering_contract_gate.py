#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import gate


def test_compose_gate_merges_lettering_contract_blockers(tmp_path: Path) -> None:
    chapter = "第1话"
    root = tmp_path / "作品"
    script_path = root / "脚本" / chapter / "panel_script.json"
    lettering_path = root / "排版" / chapter / "lettering.json"
    script_path.parent.mkdir(parents=True)
    lettering_path.parent.mkdir(parents=True)
    script_path.write_text(
        json.dumps(
            {
                "chapter": chapter,
                "panels": [
                    {
                        "panel_id": "P001",
                        "dialogue": [{"speaker": "甲", "text_target": "当前台词"}],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # A legacy artifact can exist and be included in a fresh stage fingerprint,
    # but it still cannot prove that its text came from the current script.
    lettering_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "comic_lettering",
                "chapter": chapter,
                "items": [{"item_id": "L001", "text": "旧台词"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    findings: list[dict] = []
    notes: list[str] = []

    gate.run_lettering_contract_check(root, chapter, findings, notes)

    codes = {item.get("code") for item in findings}
    assert "lettering_schema_legacy" in codes
    assert "lettering_content_ref_missing" in codes
    assert all(item.get("severity") == "block" for item in findings if item.get("code") in codes)
    assert notes and notes[0].startswith("lettering contract:")


def test_compose_gate_rejects_manifest_rendered_from_old_lettering(
    tmp_path: Path,
    monkeypatch,
) -> None:
    chapter = "第1话"
    root = tmp_path / "作品"
    chapter_dir = root / "排版" / chapter
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "lettering.json").write_text('{"schema_version": 2}\n', encoding="utf-8")
    (chapter_dir / "export_manifest.json").write_text(
        json.dumps(
            {
                "rendered": [{"path": f"排版/{chapter}/长图/longstrip.webp"}],
                "missing_panels": [],
                "lettering_sha256": "old-lettering-sha",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "run_image", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "run_lettering_contract_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "check_manifest_profile", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "run_lettering_geometry_qc", lambda *args, **kwargs: None)
    findings: list[dict] = []

    gate.run_compose(root, chapter, findings, [], no_refresh=True)

    assert "manifest_lettering_stale" in {item.get("code") for item in findings}
