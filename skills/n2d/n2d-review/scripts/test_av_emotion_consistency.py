#!/usr/bin/env python3
"""Tests for av_emotion_consistency.py — pure functions only."""
from __future__ import annotations

import pytest
import av_emotion_consistency as avec


class TestEmotionMatch:
    def test_angry_match(self):
        assert avec.emotion_match("angry", "angry")
        assert avec.emotion_match("angry", "disgusted")
        assert avec.emotion_match("angry", "fearful")

    def test_angry_mismatch(self):
        assert not avec.emotion_match("angry", "happy")
        assert not avec.emotion_match("angry", "neutral")

    def test_neutral_wide(self):
        assert avec.emotion_match("neutral", "neutral")

    def test_case_insensitive(self):
        assert avec.emotion_match("ANGRY", "ANGRY")
        assert avec.emotion_match("Sad", "SAD")

    def test_unknown_audio_emotion(self):
        assert avec.emotion_match("unknown_emo", "neutral")


class TestEmotionMismatchVerdict:
    def test_match_returns_none(self):
        assert avec.emotion_mismatch_verdict("angry", "fearful") is None
        assert avec.emotion_mismatch_verdict("happy", "happy") is None

    def test_strong_audio_neutral_visual_warns(self):
        assert avec.emotion_mismatch_verdict("angry", "neutral") == "warn"
        assert avec.emotion_mismatch_verdict("fearful", "neutral") == "warn"
        # sad visual "happy" is a mismatch; neutral is valid for sad
        assert avec.emotion_mismatch_verdict("sad", "happy") == "ok"

    def test_mild_mismatch_ok(self):
        assert avec.emotion_mismatch_verdict("happy", "neutral") == "ok"
        assert avec.emotion_mismatch_verdict("serious", "happy") == "ok"


class TestProbeEmotionModel:
    def test_returns_bool(self):
        assert isinstance(avec._probe_emotion_model(), bool)
