#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import character_consistency


def test_character_manual_acceptance_downgrades_matching_finding(tmp_path: Path) -> None:
    chapter = "第1话"
    production = tmp_path / "生产数据"
    production.mkdir()
    (production / f"character_consistency_acceptance_{chapter}.json").write_text(
        """{
          "accepted_findings": [
            {
              "code": "face_fingerprint_low",
              "character_id": "CHAR_MAIN",
              "panel_id": "P003",
              "accepted_by": "visual_qc",
              "accepted_at": "2026-07-09T12:00:00",
              "reason": "低机位和雨水遮挡导致启发式低分，脸型与发际线人审通过。",
              "evidence": "生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg"
            }
          ]
        }""",
        encoding="utf-8",
    )
    findings = [
        {
            "severity": "warn",
            "dimension": "character_consistency",
            "code": "face_fingerprint_low",
            "character_id": "CHAR_MAIN",
            "panel_id": "P003",
            "artifact": "出图/第1话/panels/P003.png",
            "reason": "score=0.401",
            "return_to_stage": "image",
            "suggested_fix": "重抽。",
        },
        {
            "severity": "warn",
            "dimension": "character_consistency",
            "code": "outfit_fingerprint_low",
            "character_id": "CHAR_MAIN",
            "panel_id": "P003",
            "artifact": "出图/第1话/panels/P003.png",
            "reason": "score=0.301",
            "return_to_stage": "image",
            "suggested_fix": "重抽。",
        },
    ]
    notes: list[str] = []

    character_consistency.apply_manual_acceptances(tmp_path, chapter, findings, notes)

    assert findings[0]["severity"] == "info"
    assert findings[0]["machine_severity"] == "warn"
    assert findings[0]["manual_acceptance"]["accepted_by"] == "visual_qc"
    assert findings[1]["severity"] == "warn"
    assert notes
