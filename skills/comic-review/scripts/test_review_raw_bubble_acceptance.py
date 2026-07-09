#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import review


def test_review_raw_bubble_acceptance_reads_panel_qc_manual_review(tmp_path: Path) -> None:
    chapter = "第1话"
    qc_dir = tmp_path / "生产数据" / "panel_qc" / chapter
    qc_dir.mkdir(parents=True)
    (qc_dir / "P001.json").write_text(
        """{
          "panel_id": "P001",
          "verdict": "warn",
          "manual_review": {
            "reviewed_by": "visual_qc",
            "reviewed_at": "2026-07-09T12:00:00",
            "verdict": "pass",
            "reason": "亮部是计划内雾光，不是空白气泡。"
          }
        }""",
        encoding="utf-8",
    )

    accepted = review.load_raw_bubble_acceptance(tmp_path, chapter)

    assert accepted["P001"]["status"] == "accepted"
    assert accepted["P001"]["accepted_by"] == "visual_qc"
    assert accepted["P001"]["reason"] == "亮部是计划内雾光，不是空白气泡。"
    assert accepted["P001"]["source"] == f"生产数据/panel_qc/{chapter}/P001.json"


def test_review_raw_bubble_acceptance_panel_qc_overrides_legacy_file(tmp_path: Path) -> None:
    chapter = "第1话"
    production = tmp_path / "生产数据"
    production.mkdir()
    (production / f"raw_bubble_acceptance_{chapter}.json").write_text(
        """{
          "accepted_findings": [
            {
              "panel_id": "P001",
              "code": "raw_bubble_candidate",
              "reason": "legacy reason"
            }
          ]
        }""",
        encoding="utf-8",
    )
    qc_dir = production / "panel_qc" / chapter
    qc_dir.mkdir(parents=True)
    (qc_dir / "P001.json").write_text(
        """{
          "panel_id": "P001",
          "manual_review": {
            "verdict": "pass",
            "reason": "panel-level review reason"
          }
        }""",
        encoding="utf-8",
    )

    accepted = review.load_raw_bubble_acceptance(tmp_path, chapter)

    assert accepted["P001"]["reason"] == "panel-level review reason"
    assert accepted["P001"]["source"] == f"生产数据/panel_qc/{chapter}/P001.json"
