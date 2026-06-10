#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for collect_market_baseline.py — OFFLINE only, no network.

Run from this directory:
    cd skills/novel-score/scripts && python3 -m pytest test_collect_market_baseline.py
"""
import os
import json
import tempfile
from argparse import Namespace, ArgumentTypeError

import pytest

import collect_market_baseline as cmb


def _args(**overrides):
    """Build a fully-populated fake args Namespace; OFFLINE-safe defaults."""
    base = dict(
        source=[],
        defaults=False,
        no_manual_required=True,
        allow_fetch_errors=True,
        note=[],
        target_platform="红果/抖音 商业爽文向",
        date="2026-01-01",
        expires_after_days=21,
        timeout=0.01,
        max_signals=80,
    )
    base.update(overrides)
    return Namespace(**base)


# ---- parse_source ----

def test_parse_source_two_parts():
    platform, url, use_for = cmb.parse_source("番茄|https://example.com/rank")
    assert platform == "番茄"
    assert url == "https://example.com/rank"
    assert use_for == "web_novel_rank"


def test_parse_source_three_parts():
    platform, url, use_for = cmb.parse_source("红果短剧|https://x.com/r|short_drama_rank")
    assert platform == "红果短剧"
    assert url == "https://x.com/r"
    assert use_for == "short_drama_rank"


def test_parse_source_strips_whitespace():
    platform, url, use_for = cmb.parse_source(" 番茄 | https://x.com/r | web_novel_rank ")
    assert platform == "番茄"
    assert url == "https://x.com/r"
    assert use_for == "web_novel_rank"


def test_parse_source_bad_format_raises():
    with pytest.raises(ArgumentTypeError):
        cmb.parse_source("just_a_platform_no_url")


# ---- coverage_warnings ----

def test_coverage_warning_when_short_drama_platform_uncovered():
    # 红果/抖音 target, no sources, no notes -> warning present
    result = cmb.collect(_args(source=[], note=[], defaults=False))
    assert result["coverage_warnings"], "expected non-empty coverage_warnings"
    assert "红果" in result["coverage_warnings"][0]


def test_note_covering_short_drama_suppresses_warning():
    result = cmb.collect(_args(note=["红果短剧榜本周热门：复仇逆袭题材占多数"]))
    assert result["coverage_warnings"] == []


def test_no_warning_when_platform_not_short_drama():
    result = cmb.collect(_args(target_platform="番茄网文向"))
    assert result["coverage_warnings"] == []


# ---- MANUAL_REQUIRED placeholder rows ----

def test_manual_required_rows_appended_with_defaults():
    # defaults=True + no_manual_required=False -> placeholder rows appended.
    # timeout tiny + allow_fetch_errors -> fetch failures tolerated, rows still appended.
    result = cmb.collect(_args(
        defaults=True,
        no_manual_required=False,
        allow_fetch_errors=True,
        timeout=0.01,
    ))
    manual_rows = [s for s in result["sources"] if s.get("status") == "manual_required"]
    assert len(manual_rows) == len(cmb.MANUAL_REQUIRED_SOURCES)
    platforms = {s["platform"] for s in manual_rows}
    assert "红果短剧" in platforms
    assert "抖音漫剧/短剧" in platforms


def test_default_source_rows_present_even_on_fetch_error():
    result = cmb.collect(_args(
        defaults=True,
        no_manual_required=True,
        allow_fetch_errors=True,
        timeout=0.01,
    ))
    # The 3 DEFAULT_SOURCES still produce rows (with fetch_error status), no manual rows
    default_platforms = {p for p, _, _ in cmb.DEFAULT_SOURCES}
    seen = {s["platform"] for s in result["sources"]}
    assert default_platforms.issubset(seen)
    assert all(s.get("status") != "manual_required" for s in result["sources"])


def test_no_manual_required_flag_suppresses_placeholders():
    result = cmb.collect(_args(defaults=True, no_manual_required=True, timeout=0.01))
    assert not [s for s in result["sources"] if s.get("status") == "manual_required"]


# ---- write_artifacts ----

def test_write_artifacts_writes_both_files_and_md_warning_section():
    result = cmb.collect(_args(source=[], note=[], defaults=False))  # has warnings
    assert result["coverage_warnings"]
    out_dir = tempfile.mkdtemp()
    json_path, md_path = cmb.write_artifacts(result, out_dir)
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
    assert json_path.endswith("market_baseline_2026-01-01.json")

    with open(json_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["kind"] == "novel_market_baseline"
    assert loaded["baseline_date"] == "2026-01-01"

    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    assert "覆盖告警" in md


def test_write_artifacts_no_warning_section_when_clean():
    result = cmb.collect(_args(target_platform="番茄网文向"))
    assert result["coverage_warnings"] == []
    out_dir = tempfile.mkdtemp()
    _, md_path = cmb.write_artifacts(result, out_dir)
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    assert "覆盖告警" not in md
