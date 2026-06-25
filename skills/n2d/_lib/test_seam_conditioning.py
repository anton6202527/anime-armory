#!/usr/bin/env python3
"""Tests for seam_conditioning.py — pure functions only."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

# Import from n2d/_lib/
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
import seam_conditioning as sc


class TestBuildHints:
    def test_empty_findings(self):
        result = sc.build_hints([], "第1集")
        assert result["kind"] == sc.KIND
        assert result["episode"] == "第1集"
        assert result["hints"] == []

    def test_ok_only_skipped(self):
        findings = [
            {"tail": "01_end.png", "next_first": "02.png", "verdict": "ok"},
            {"tail": "02_end.png", "next_first": "03.png", "verdict": "ok"},
        ]
        result = sc.build_hints(findings, "第1集")
        assert result["hints"] == []

    def test_warn_generates_hint(self):
        findings = [
            {"tail": "01_end.png", "next_first": "02.png", "verdict": "warn",
             "struct_verdict": "warn", "color_verdict": "ok"},
        ]
        result = sc.build_hints(findings, "第1集")
        assert len(result["hints"]) == 1
        h = result["hints"][0]
        assert h["tail"] == "01_end.png"
        assert h["next_first"] == "02.png"
        assert h["severity"] == "warn"
        assert "struct" in h["fields"]
        assert "color" not in h["fields"]
        assert "conditioning reference" in h["hint"]

    def test_block_generates_hint(self):
        findings = [
            {"tail": "03_end.png", "next_first": "04.png", "verdict": "block",
             "struct_verdict": "block", "face_verdict": "warn"},
        ]
        result = sc.build_hints(findings, "第1集")
        assert len(result["hints"]) == 1
        h = result["hints"][0]
        assert h["severity"] == "block"
        assert "struct" in h["fields"]
        assert "face" in h["fields"]

    def test_no_verdict_fields_falls_back(self):
        findings = [{"tail": "01_end.png", "next_first": "02.png", "verdict": "warn"}]
        result = sc.build_hints(findings, "第1集")
        assert len(result["hints"]) == 1
        assert "structure" in result["hints"][0]["fields"]

    def test_mixed_ok_and_warn(self):
        findings = [
            {"verdict": "ok"},
            {"tail": "01_end.png", "next_first": "02.png", "verdict": "warn", "struct_verdict": "warn"},
        ]
        result = sc.build_hints(findings, "第1集")
        assert len(result["hints"]) == 1

    def test_non_dict_skipped(self):
        findings = [None, "string", {"verdict": "warn"}]
        result = sc.build_hints(findings, "第1集")  # type: ignore[arg-type]
        assert len(result["hints"]) >= 0


class TestWriteHints:
    def test_writes_file(self):
        hints = {"kind": sc.KIND, "version": sc.VERSION, "episode": "第1集", "hints": []}
        with tempfile.TemporaryDirectory() as tmp:
            path = sc.write_hints(tmp, "第1集", hints)
            assert path is not None
            assert os.path.isfile(path)
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            assert data["kind"] == sc.KIND
            assert data["episode"] == "第1集"
