#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import os
import tempfile

import feedback_ingest


def test_feedback_ingest_summarizes_csv():
    with tempfile.TemporaryDirectory() as root:
        csv_path = os.path.join(root, "feedback.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["take_id", "plays", "completes", "saves", "shares", "comment"])
            writer.writeheader()
            writer.writerow({"take_id": "take_01", "plays": "100", "completes": "45", "saves": "5", "shares": "3", "comment": "副歌好记"})
        rows = feedback_ingest.read_rows(csv_path)
        events = feedback_ingest.normalize_rows(rows, platform="抖音", source_name="test")
        summary = feedback_ingest.summarize(events, root)
        assert summary["event_count"] == 1
        group = summary["groups"][0]
        assert group["completion_rate"] == 0.45
        assert "save_signal" in group["signals"]
        feedback_ingest.write_outputs(root, events, summary)
        assert os.path.exists(os.path.join(root, "发行", "feedback_summary.json"))
