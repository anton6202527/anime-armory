#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import json
import os
import tempfile

import ingest_reader_events as ing


def test_csv_ingest_flags_dropoff_and_negative_comments():
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "events.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["章节", "event", "count", "评论"])
            writer.writeheader()
            writer.writerow({"章节": "第1章", "event": "start", "count": "100", "评论": ""})
            writer.writerow({"章节": "第1章", "event": "complete", "count": "42", "评论": ""})
            writer.writerow({"章节": "第1章", "event": "drop", "count": "45", "评论": ""})
            writer.writerow({"章节": "第1章", "event": "comment", "count": "1", "评论": "这里太拖，看不下去"})
            writer.writerow({"章节": "第1章", "event": "comment", "count": "1", "评论": "主角有点降智"})
        rows = ing.read_input(csv_path)
        normalized = ing.normalize_rows(rows, input_path=csv_path, source_name="小流量", platform="红果")
        summary = ing.build_summary(
            normalized,
            platform="红果",
            source_name="小流量",
            min_sample=20,
            low_completion=0.55,
            high_drop=0.35,
        )
        ch1 = summary["chapters"][0]
        assert ch1["completion_rate"] == 0.42
        assert ch1["drop_rate"] == 0.45
        assert "low_completion" in ch1["flags"]
        assert "high_drop" in ch1["flags"]
        assert "negative_comment_spike" in ch1["flags"]
        assert summary["weakest_chapters"] == [1]


def test_jsonl_rates_without_counts_are_preserved():
    with tempfile.TemporaryDirectory() as tmp:
        jsonl_path = os.path.join(tmp, "events.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"chapter": 2, "completion_rate": "61%", "drop_rate": "12%"}, ensure_ascii=False) + "\n")
        normalized = ing.normalize_rows(
            ing.read_input(jsonl_path),
            input_path=jsonl_path,
            source_name="表单",
            platform="内测",
        )
        summary = ing.build_summary(
            normalized,
            platform="内测",
            source_name="表单",
            min_sample=20,
            low_completion=0.55,
            high_drop=0.35,
        )
        assert summary["chapters"][0]["chapter"] == 2
        assert summary["chapters"][0]["completion_rate"] == 0.61
        assert summary["chapters"][0]["drop_rate"] == 0.12


def test_main_writes_artifacts():
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "events.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("chapter,event,count\n1,start,30\n1,complete,25\n")
        argv = ["ingest_reader_events.py", tmp, "--input", csv_path, "--platform", "测试", "--source-name", "批次A"]
        import sys
        old_argv = sys.argv
        sys.argv = argv
        try:
            assert ing.main() == 0
        finally:
            sys.argv = old_argv
        summary_path = os.path.join(tmp, "评分", "reader_telemetry_summary.json")
        assert os.path.exists(summary_path)
        with open(summary_path, encoding="utf-8") as f:
            payload = json.load(f)
        assert payload["kind"] == "novel_reader_telemetry_summary"
        assert payload["records_ingested"] == 2
