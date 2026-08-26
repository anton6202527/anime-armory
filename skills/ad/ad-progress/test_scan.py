#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad-progress scan helpers tests."""

import scan


def test_block_status_has_red_marker():
    assert scan.state_of("🔴block") == scan.BLOCK
    assert scan.state_of("block") == scan.BLOCK
    assert scan.marker(scan.BLOCK) == "🔴"


def test_rough_status_stays_partial():
    assert scan.state_of("⏳rough") == scan.PARTIAL
    assert scan.marker(scan.PARTIAL) == "⏳"


def test_release_verdict_display_source_is_read_only(tmp_path):
    root = tmp_path / "ad"
    root.mkdir()
    verdict = scan.release_verdict(str(root))
    assert verdict["status"] == "blocked"
    assert verdict["complete"] is False
    assert not (root / "生产数据" / "release_verdict.json").exists()
