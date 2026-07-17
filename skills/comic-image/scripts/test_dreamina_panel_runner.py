#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dreamina_panel_runner helpers; no real paid requests."""
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
import dreamina_panel_runner as runner  # noqa: E402


def test_closest_ratio_uses_panel_geometry():
    assert runner.closest_ratio(1296, 1040) == "4:3"
    assert runner.closest_ratio(1040, 1296) == "3:4"
    assert runner.closest_ratio(1080, 1920) == "9:16"


def test_submit_id_from_json_and_text():
    assert runner.submit_id_from('{"submit_id":"abc-123"}') == "abc-123"
    assert runner.submit_id_from("submit_id = xyz") == "xyz"


def test_run_dreamina_passes_all_references_and_downloads(tmp_path):
    submit = subprocess.CompletedProcess(
        ["dreamina"],
        0,
        json.dumps({"submit_id": "sid", "gen_status": "success", "credit_count": 1}),
        "",
    )
    query = subprocess.CompletedProcess(["dreamina"], 0, '{"gen_status":"success"}', "")
    source = tmp_path / "source.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

    calls = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        if cmd[1] == "image2image":
            return submit
        download_dir = Path(cmd[cmd.index("--download_dir") + 1])
        download_dir.mkdir(parents=True, exist_ok=True)
        (download_dir / "result.png").write_bytes(source.read_bytes())
        return query

    with mock.patch("dreamina_panel_runner.subprocess.run", side_effect=fake_run):
        ok, submit_id, payload, error = runner.run_dreamina(
            "prompt",
            [tmp_path / "a.png", tmp_path / "b.png"],
            tmp_path / "out.png",
            ratio="4:3",
            resolution_type="2k",
            model_version="5.0",
            poll_sec=1,
            timeout_sec=10,
        )

    assert ok and not error
    assert submit_id == "sid"
    assert payload["credit_count"] == 1
    assert (tmp_path / "out.png").is_file()
    assert calls[0][calls[0].index("--images") + 1] == f"{tmp_path / 'a.png'},{tmp_path / 'b.png'}"
