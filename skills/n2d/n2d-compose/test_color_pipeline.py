from __future__ import annotations

import json
from pathlib import Path

import color_pipeline as color


def test_default_contract_has_deterministic_rec709_output() -> None:
    contract = color.default_contract()
    assert color.output_tags(contract) == {
        "color_primaries": "bt709",
        "color_transfer": "bt709",
        "color_space": "bt709",
        "color_range": "tv",
        "pixel_format": "yuv420p",
    }
    assert color.ffmpeg_output_args(contract)[-2:] == ["-pix_fmt", "yuv420p"]


def test_pending_master_is_not_a_compose_block(tmp_path: Path) -> None:
    color.write_missing(tmp_path)
    result = color.analyze(tmp_path, "第1集")
    assert result["status"] == "pending_master"
    assert result["issues"] == []


def test_master_missing_color_tags_blocks_review(tmp_path: Path) -> None:
    color.write_missing(tmp_path)
    master = tmp_path / "合成" / "第1集" / "成片_第1集_zh.mp4"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"video")

    class Result:
        returncode = 0
        stdout = json.dumps({"streams": [{"pix_fmt": "yuv420p"}]})
        stderr = ""

    result = color.analyze(tmp_path, "第1集", runner=lambda *a, **k: Result())
    assert result["status"] == "block"
    assert any(row["code"] == "color_primaries_missing" for row in result["issues"])


def test_matching_master_tags_pass(tmp_path: Path) -> None:
    color.write_missing(tmp_path)
    master = tmp_path / "合成" / "第1集" / "成片_第1集_zh.mp4"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"video")

    class Result:
        returncode = 0
        stdout = json.dumps({"streams": [{
            "pix_fmt": "yuv420p", "color_space": "bt709", "color_transfer": "bt709",
            "color_primaries": "bt709", "color_range": "tv",
        }]})
        stderr = ""

    assert color.analyze(tmp_path, "第1集", runner=lambda *a, **k: Result())["status"] == "pass"
