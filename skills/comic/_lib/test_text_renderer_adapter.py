import json
from pathlib import Path

from PIL import Image

from text_renderer_adapter import render_text_rgba, select_renderer, suitability, validate_glyph_coverage


def test_draft_renderer_cannot_claim_rtl_publication():
    result = suitability(language_mode="Arabic", direction="rtl", available={"adapter_id": "pillow_draft", "status": "draft_only", "supports": ["cjk_horizontal"]})
    assert result["suitable"] is False
    assert result["publication_claim_allowed"] is False


def test_vertical_requires_real_vertical_capability():
    result = suitability(
        language_mode="Japanese", direction="ltr", writing_mode="vertical-rl",
        available={"adapter_id": "pango", "status": "executable", "supports": ["cjk_horizontal", "complex_shaping"]},
    )
    assert result["required_capabilities"] == ["vertical_cjk"]
    assert result["publication_claim_allowed"] is False


def test_registered_renderer_is_executed_and_receipted(tmp_path: Path):
    runner = tmp_path / "renderer.py"
    runner.write_text(
        "#!/usr/bin/env python3\n"
        "import argparse\nfrom PIL import Image\n"
        "p=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--output');a=p.parse_args()\n"
        "Image.new('RGBA',(32,16),(255,255,255,0)).save(a.output,'PNG')\n",
        encoding="utf-8",
    )
    runner.chmod(0o755)
    registry = tmp_path / "生产数据" / "text_renderer_adapters.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"adapters": [{
        "id": "fixture", "protocol": "comic_text_rgba_v1", "command": [str(runner)],
        "supports": ["cjk_horizontal", "latin_horizontal", "complex_shaping", "rtl", "vertical_cjk"],
    }]}), encoding="utf-8")
    selection = select_renderer(language_mode="Japanese", direction="ltr", writing_mode="vertical-rl", root=tmp_path)
    assert selection["adapter_id"] == "fixture" and selection["publication_claim_allowed"]
    output = tmp_path / "out.png"
    receipt = render_text_rgba({"text": "縦書き", "language_mode": "Japanese", "writing_mode": "vertical-rl"}, output, root=tmp_path)
    assert receipt["status"] == "rendered"
    assert receipt["output_sha256"] and Image.open(output).size == (32, 16)


def test_glyph_coverage_is_truthfully_unavailable_without_font():
    receipt = validate_glyph_coverage("hello", font_path="")
    assert receipt["status"] == "unavailable"
    assert receipt["text_sha256"]
