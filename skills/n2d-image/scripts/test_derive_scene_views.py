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

    def test_relative_outputs_are_anchored_to_project_root(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as cwd:
            shared = os.path.join(root, "出图", "共享")
            images = os.path.join(shared, "图片")
            os.makedirs(images)
            front_rel = "出图/共享/图片/定妆_测试场景.png"
            Image.new("RGB", (64, 64), color=(32, 64, 96)).save(os.path.join(root, front_rel))
            registry = {
                "assets": [
                    {
                        "id": "LOC_TEST",
                        "type": "location",
                        "scene_atlas": {"base_views": {"front": {"path": front_rel, "status": "ready"}}},
                    }
                ]
            }
            with open(os.path.join(shared, "asset_registry.json"), "w", encoding="utf-8") as fh:
                json.dump(registry, fh, ensure_ascii=False)

            old_cwd = os.getcwd()
            try:
                os.chdir(cwd)
                result = dsv.run(root)
            finally:
                os.chdir(old_cwd)

            assert {d["view"] for d in result["derived"]} == {"side_left", "side_right", "reverse"}
            assert os.path.isfile(os.path.join(root, "出图/共享/图片/定妆_测试场景_side_right.png"))
            assert not os.path.exists(os.path.join(cwd, "出图"))
