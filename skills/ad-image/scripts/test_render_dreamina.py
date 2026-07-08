#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_dreamina helper tests; no real Dreamina calls."""

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_dreamina as rd  # noqa: E402


def test_extract_sections_and_build_prompt(tmp_path):
    path = tmp_path / "镜头01.md"
    path.write_text(
        "# t\n\n"
        "## 画面 prompt\nphone on desk\n\n"
        "## 身份锁定句\n同一 logo\n\n"
        "## 负向\n不要乱码\n",
        encoding="utf-8",
    )
    prompt = rd.build_prompt(path)

    assert "phone on desk" in prompt
    assert "同一 logo" in prompt
    assert "不要乱码" in prompt
    assert "Vertical 9:16" in prompt


def test_run_dreamina_text2image_parses_success():
    payload = {
        "submit_id": "sid",
        "gen_status": "success",
        "result_json": {"images": [{"image_url": "https://example.test/a.png", "width": 1, "height": 2}]},
    }
    with mock.patch("render_dreamina.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(["dreamina"], 0, json.dumps(payload), "")
        out = rd.run_dreamina_text2image("prompt", ratio="9:16", resolution_type="2k", model_version="5.0", poll=1)

    assert out["submit_id"] == "sid"
    assert run.call_args.args[0][0:2] == ["dreamina", "text2image"]


def test_run_dreamina_text2image_blocks_no_image():
    payload = {"submit_id": "sid", "gen_status": "success", "result_json": {"images": []}}
    with mock.patch("render_dreamina.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(["dreamina"], 0, json.dumps(payload), "")
        try:
            rd.run_dreamina_text2image("prompt", ratio="9:16", resolution_type="2k", model_version="5.0", poll=1)
        except RuntimeError as exc:
            assert "no image_url" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")
