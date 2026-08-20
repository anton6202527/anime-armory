#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import review


def test_review_gaze_validator_keeps_specific_spatial_targets() -> None:
    assert review.is_vague_gaze_target("看前方") is True
    assert review.is_vague_gaze_target("和尚看画右前方云路") is False
    assert review.is_vague_gaze_target("僧道看街巷前方未点亮的灯架") is False


def test_review_raw_bubble_acceptance_reads_current_double_gate(tmp_path: Path, monkeypatch) -> None:
    from PIL import Image

    chapter = "第1话"
    panel = tmp_path / "出图" / chapter / "panels" / "P001.png"
    panel.parent.mkdir(parents=True)
    Image.new("RGB", (100, 100), (30, 70, 110)).save(panel)
    monkeypatch.setattr(review.panel_acceptance, "likely_blank_bubble_regions", lambda _path: [{"x": 1}])
    monkeypatch.setattr(review.panel_acceptance, "likely_large_edge_blank_bands", lambda _path: [])
    job = {
        "panel_id": "P001",
        "size": {"width": 100, "height": 100},
        "resolution_policy": "按最终画布",
        "references": [],
        "result_path": str(panel.relative_to(tmp_path)),
    }
    post_qc = review.panel_acceptance.post_qc_panel(tmp_path, chapter, job, panel, [], [])
    job.update(
        {
            "status": review.panel_acceptance.status_after_post_qc(post_qc),
            "artifact_sha256": review.panel_acceptance.file_sha256(panel),
            "post_qc": post_qc,
        }
    )
    jobs = {"jobs": [job]}
    jobs_path = tmp_path / "出图" / chapter / "prompt" / "panel_jobs.json"
    review.panel_acceptance.write_json(jobs_path, jobs)
    review.panel_acceptance.accept_panel_review(
        tmp_path, chapter, jobs, jobs_path, "P001", "visual_qc", "亮部是计划内雾光，不是空白气泡。"
    )

    accepted = review.load_raw_bubble_acceptance(tmp_path, chapter)

    assert accepted["P001"]["status"] == "accepted"
    assert accepted["P001"]["authorized"] is True
    assert accepted["P001"]["accepted_by"] == "visual_qc"
    assert accepted["P001"]["reason"] == "亮部是计划内雾光，不是空白气泡。"
    assert accepted["P001"]["source"] == f"生产数据/panel_qc/{chapter}/P001.json"


def test_review_legacy_unbound_acceptance_is_disclosure_only(tmp_path: Path) -> None:
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
    accepted = review.load_raw_bubble_acceptance(tmp_path, chapter)

    assert accepted["P001"]["reason"] == "legacy reason"
    assert accepted["P001"]["authorized"] is False
    assert accepted["P001"]["status"] == "legacy_unbound_or_stale"
    assert accepted["P001"]["source"] == f"生产数据/raw_bubble_acceptance_{chapter}.json"
