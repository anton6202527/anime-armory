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
