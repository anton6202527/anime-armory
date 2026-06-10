#!/usr/bin/env python3
"""Tests for n2d telemetry helpers.

Run from this directory:
    cd skills/common && python3 -m pytest test_n2d_telemetry.py
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from n2d_telemetry import (  # noqa: E402
    VALID_EVENTS,
    Timer,
    record_event,
    _dashboard_script,
)


# ── VALID_EVENTS whitelist ──
def test_record_event_rejects_unknown_event(tmp_path):
    # "gate" is not in the whitelist → ValueError (programming error, not silent)
    assert "gate" not in VALID_EVENTS
    with pytest.raises(ValueError):
        record_event(str(tmp_path), "第1集", "image", event="gate")


def test_record_event_accepts_valid_event(tmp_path):
    # A whitelisted event spawns a fire-and-forget Popen; just assert no raise.
    assert "generation" in VALID_EVENTS
    record_event(str(tmp_path), "第1集", "image", event="generation")


def test_valid_events_contains_expected_members():
    for ev in ("generation", "redraw", "qa", "cost", "duration", "manual",
               "release", "revenue"):
        assert ev in VALID_EVENTS


# ── Timer context manager ──
def test_timer_elapsed_nonnegative_float():
    t = Timer()
    with t:
        e = t.elapsed()
    assert isinstance(e, float)
    assert e >= 0


def test_timer_duration_set_after_with():
    with Timer() as t:
        pass
    assert isinstance(t.duration, float)
    assert t.duration >= 0


def test_timer_elapsed_before_enter_is_zero():
    # No start_time yet → elapsed() returns 0.0
    assert Timer().elapsed() == 0.0


# ── _dashboard_script path ──
def test_dashboard_script_path_ends_with_dashboard_py():
    p = _dashboard_script()
    assert os.path.isabs(p)
    assert p.endswith("dashboard.py")
