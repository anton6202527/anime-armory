#!/usr/bin/env python3
"""Tests for state_pixel_verify.py — pure functions only."""
from __future__ import annotations

import pytest
import state_pixel_verify as spv


class TestBuildJudgePrompt:
    def test_format(self):
        prompt = spv.build_judge_prompt("沈念", "流血")
        assert "沈念" in prompt
        assert "流血" in prompt
        assert "yes" in prompt
        assert "no" in prompt
        assert "uncertain" in prompt


class TestParseStateVerdict:
    def test_yes_variants(self):
        assert spv.parse_state_verdict("yes") == "yes"
        assert spv.parse_state_verdict("YES.") == "yes"
        assert spv.parse_state_verdict("是的") == "yes"
        assert spv.parse_state_verdict("有") == "yes"

    def test_no_variants(self):
        assert spv.parse_state_verdict("no") == "no"
        assert spv.parse_state_verdict("NO.") == "no"
        assert spv.parse_state_verdict("不是") == "no"
        assert spv.parse_state_verdict("否") == "no"

    def test_uncertain_variants(self):
        assert spv.parse_state_verdict("uncertain") == "uncertain"
        assert spv.parse_state_verdict("不确定") == "uncertain"
        assert spv.parse_state_verdict("无法判断") == "uncertain"
        assert spv.parse_state_verdict("maybe") == "uncertain"

    def test_unparseable(self):
        assert spv.parse_state_verdict("gibberish123") is None
        assert spv.parse_state_verdict("The answer is yes but with caveats") is None


class TestStateVerdictToFinding:
    def test_no_is_block(self):
        f = spv.state_verdict_to_finding("no", "受伤", "clip_01")
        assert f["verdict"] == "block"
        assert "未呈现" in f["msg"]

    def test_uncertain_is_warn(self):
        f = spv.state_verdict_to_finding("uncertain", "觉醒", "clip_02")
        assert f["verdict"] == "warn"
        assert "无法确定" in f["msg"]

    def test_yes_is_ok(self):
        f = spv.state_verdict_to_finding("yes", "泪", "clip_03")
        assert f["verdict"] == "ok"


class TestProbeVlm:
    def test_returns_bool(self):
        assert isinstance(spv._probe_vlm(), bool)
