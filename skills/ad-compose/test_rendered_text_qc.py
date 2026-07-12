import json
import shutil
import subprocess
from pathlib import Path

import pytest

import rendered_text_qc as rt


def _video(path: Path, duration=2):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg required for final-pixel integration")
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"color=c=black:s=320x240:d={duration}", "-c:v", "mpeg4", str(path)], check=True)


def _project(tmp_path: Path):
    root = tmp_path / "ad"
    _video(root / "合成" / "成片_主片.mp4")
    (root / "合成" / "delivery_plan.json").write_text(json.dumps({"deliverables": [{
        "deliverable_id": "master", "expected_path": "合成/成片_主片.mp4", "status": "rendered"
    }]}), encoding="utf-8")
    (root / "脚本").mkdir()
    (root / "脚本" / "字幕_zh.srt").write_text(
        "1\n00:00:00,200 --> 00:00:01,800\n立即购买\n", encoding="utf-8")
    (root / "脚本" / "storyboard.json").write_text(json.dumps({"shots": [{"shot_id": "S1", "duration": 2}]}), encoding="utf-8")
    (root / "需求").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps({"mandatories": {}}), encoding="utf-8")
    evidence = root / "证据" / "final-pixel-review.md"
    evidence.parent.mkdir()
    evidence.write_text("具名逐项确认：文字、对比度、时长、遮挡", encoding="utf-8")
    plan = {"schema_version": 1, "kind": "ad_rendered_text_plan", "checks": [{
        "id": "master:subtitle:001", "deliverable_id": "master", "kind": "subtitle",
        "expected_text": "立即购买", "timestamp": 1.0, "start": 0.2, "end": 1.8,
        "bbox_norm": [0.2, 0.7, 0.6, 0.15], "safe_zone_norm": [0.1, 0.1, 0.8, 0.8],
        "min_contrast": 4.5, "observed_text": "立即购买", "observed_by": "审片甲",
        "observed_evidence": "证据/final-pixel-review.md", "contrast_approved": True,
        "duration_approved": True, "occlusion_approved": True,
    }]}
    path = root / "合规" / "rendered_text_plan.json"
    path.parent.mkdir()
    path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return root, plan


def test_rendered_text_qc_uses_final_encoded_pixels_and_named_review(tmp_path):
    root, plan = _project(tmp_path)
    report = rt.build(root, plan)
    assert report["summary"]["block"] == 0
    assert report["checks"][0]["frame_sha256"]
    assert report["checks"][0]["duration_seconds"] == pytest.approx(1.6)


def test_rendered_text_qc_blocks_missing_human_contrast_duration_occlusion(tmp_path):
    root, plan = _project(tmp_path)
    plan["checks"][0]["occlusion_approved"] = False
    report = rt.build(root, plan)
    assert any(row["code"] == "rendered_manual_confirmation_missing" for row in report["findings"])


def test_rendered_text_template_includes_each_final_subtitle_cue(tmp_path):
    root, _ = _project(tmp_path)
    generated = rt.template(root)
    subtitles = [row for row in generated["checks"] if row["kind"] == "subtitle"]
    assert len(subtitles) == 1
    assert subtitles[0]["expected_text"] == "立即购买"
    assert subtitles[0]["occlusion_approved"] is False


def test_rendered_text_plan_cannot_omit_an_approved_subtitle_cue(tmp_path):
    root, plan = _project(tmp_path)
    plan["checks"] = [{**plan["checks"][0], "id": "master:custom:only"}]
    report = rt.build(root, plan)
    assert any(row["code"] == "rendered_text_contract_uncovered" for row in report["findings"])
