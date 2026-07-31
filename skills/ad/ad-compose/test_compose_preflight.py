import json
from pathlib import Path
from unittest import mock

import compose_preflight as cp


BT709 = {
    "color_primaries": "bt709", "color_transfer": "bt709", "color_space": "bt709",
    "color_range": "tv", "field_order": "progressive", "pix_fmt": "yuv420p",
}
HDR = {
    "color_primaries": "bt2020", "color_transfer": "smpte2084", "color_space": "bt2020nc",
    "color_range": "tv", "field_order": "progressive", "pix_fmt": "yuv420p10le",
}


def _project(tmp_path: Path, policy=None):
    root = tmp_path / "ad"
    (root / "需求").mkdir(parents=True)
    (root / "出视频" / "分镜" / "视频").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps({"color_management": policy or {"mode": "sdr_bt709"}}), encoding="utf-8")
    (root / "出视频" / "分镜" / "视频" / "S1.mp4").write_bytes(b"clip")
    return root


def test_bt709_sources_pass_color_preflight(tmp_path):
    root = _project(tmp_path)
    with mock.patch.object(cp, "probe_color", return_value=BT709):
        report = cp.color_preflight(root)
    assert report["summary"]["block"] == 0


def test_hdr_source_requires_explicit_conversion_evidence(tmp_path):
    root = _project(tmp_path)
    with mock.patch.object(cp, "probe_color", return_value=HDR):
        report = cp.color_preflight(root)
    assert any(f["code"] == "color_conversion_plan_missing" for f in report["findings"])


def test_hdr_source_with_conversion_plan_passes_preflight(tmp_path):
    root = _project(tmp_path, {"mode": "explicit_conversion", "conversion_evidence": "合规/color-plan.md"})
    (root / "合规").mkdir()
    (root / "合规" / "color-plan.md").write_text("HDR to SDR trim and review", encoding="utf-8")
    with mock.patch.object(cp, "probe_color", return_value=HDR):
        report = cp.color_preflight(root)
    assert report["summary"]["block"] == 0
