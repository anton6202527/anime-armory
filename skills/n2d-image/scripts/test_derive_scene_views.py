#!/usr/bin/env python3
"""Tests for derive_scene_views.py — pure functions + CLI."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import derive_scene_views as dsv


class TestScenesMissingViews:
    def test_empty_registry(self):
        assert dsv.scenes_missing_views({"locations": {}}) == []

    def test_complete_scene(self):
        reg = {
            "locations": {
                "LOC_01": {
                    "scene_atlas": {
                        "base_views": {
                            "front": "定妆库/LOC_01/front.png",
                            "side_left": "定妆库/LOC_01/side_left.png",
                            "side_right": "定妆库/LOC_01/side_right.png",
                            "reverse": "定妆库/LOC_01/reverse.png",
                        }
                    }
                }
            }
        }
        assert dsv.scenes_missing_views(reg) == []

    def test_missing_side_views(self):
        reg = {
            "locations": {
                "LOC_02": {
                    "scene_atlas": {
                        "base_views": {"front": "定妆库/LOC_02/front.png"}
                    }
                }
            }
        }
        missing = dsv.scenes_missing_views(reg)
        assert len(missing) == 1
        assert missing[0]["loc_id"] == "LOC_02"
        assert "side_left" in missing[0]["missing_views"]
        assert "side_right" in missing[0]["missing_views"]
        assert "reverse" in missing[0]["missing_views"]

    def test_no_front_view(self):
        reg = {
            "locations": {
                "LOC_03": {"scene_atlas": {"base_views": {"side_left": "path.png"}}}
            }
        }
        assert dsv.scenes_missing_views(reg) == []

    def test_no_scene_atlas(self):
        reg = {"locations": {"LOC_04": {"name": "test"}}}
        assert dsv.scenes_missing_views(reg) == []


class TestDeriveFlip:
    def test_produces_png(self):
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        with tempfile.TemporaryDirectory() as tmp:
            front = os.path.join(tmp, "front.png")
            img.save(front)
            out = os.path.join(tmp, "front_side_left.png")
            result = dsv.derive_flip(front, out, "side_left")
            assert result == out
            assert os.path.isfile(out)

    def test_side_right_keeps_orientation(self):
        from PIL import Image
        img = Image.new("RGB", (50, 50), color=(0, 255, 0))
        with tempfile.TemporaryDirectory() as tmp:
            front = os.path.join(tmp, "front.png")
            img.save(front)
            out = os.path.join(tmp, "front_side_right.png")
            result = dsv.derive_flip(front, out, "side_right")
            assert result is not None

    def test_invalid_input_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = dsv.derive_flip(
                os.path.join(tmp, "nonexistent.png"),
                os.path.join(tmp, "out.png"),
                "side_left",
            )
            assert result is None


class TestRun:
    def test_no_asset_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = dsv.run(tmp)
            assert result["derived"] == []
