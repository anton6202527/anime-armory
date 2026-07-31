import json
from pathlib import Path
from unittest import mock

import accessibility_qc as aq


GOOD_SRT = """1
00:00:00,000 --> 00:00:02,000
今天从一杯咖啡开始

2
00:00:02,100 --> 00:00:04,000
[音乐渐强] 立即购买
"""


def _project(tmp_path: Path):
    root = tmp_path / "ad"
    (root / "需求").mkdir(parents=True)
    (root / "脚本").mkdir()
    (root / "合成").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps({
        "accessibility": {"meaningful_non_speech_audio": True},
    }), encoding="utf-8")
    (root / "_设置.md").write_text("- 字幕语言: 中文\n", encoding="utf-8")
    (root / "脚本" / "字幕_zh.srt").write_text(GOOD_SRT, encoding="utf-8")
    (root / "合成" / "成片_主片.mp4").write_bytes(b"video")
    plan = {"deliverables": [{"deliverable_id": "master", "expected_path": "合成/成片_主片.mp4", "exists": True}]}
    return root, plan


def test_parse_srt_has_monotonic_cues():
    cues = aq.parse_srt_text(GOOD_SRT)
    assert len(cues) == 2
    assert cues[0]["start"] == 0
    assert cues[1]["end"] == 4


def test_accessibility_report_accepts_structural_captions(tmp_path):
    root, plan = _project(tmp_path)
    with mock.patch.object(aq, "audio_present", return_value=True), \
         mock.patch.object(aq, "flash_screen", return_value={
             "sample_fps": 12, "frame_size": "64x36", "large_change_events": 0,
             "peak_transitions_per_second": 0, "possible_over_three_flashes": False,
         }):
        report = aq.build_report(root, plan)
    assert report["summary"]["block"] == 0
    assert report["caption"]["sha256"]


def test_audio_without_caption_blocks(tmp_path):
    root, plan = _project(tmp_path)
    (root / "脚本" / "字幕_zh.srt").unlink()
    with mock.patch.object(aq, "audio_present", return_value=True), \
         mock.patch.object(aq, "flash_screen", return_value=None):
        report = aq.build_report(root, plan)
    assert any(f["code"] == "caption_file_missing" and f["severity"] == "block" for f in report["findings"])


def test_flash_detector_only_warns_and_requires_human_followup(tmp_path):
    root, plan = _project(tmp_path)
    with mock.patch.object(aq, "audio_present", return_value=True), \
         mock.patch.object(aq, "flash_screen", return_value={
             "sample_fps": 12, "frame_size": "64x36", "large_change_events": 9,
             "peak_transitions_per_second": 9, "possible_over_three_flashes": True,
         }):
        report = aq.build_report(root, plan)
    finding = next(f for f in report["findings"] if f["code"] == "possible_flash_risk")
    assert finding["severity"] == "warn"


def test_sound_off_placement_still_requires_caption_file(tmp_path):
    root, plan = _project(tmp_path)
    plan["deliverables"][0]["platform_constraints"] = [{"captions_required": True, "sound_mode": "sound_off"}]
    (root / "脚本" / "字幕_zh.srt").unlink()
    with mock.patch.object(aq, "audio_present", return_value=False), \
         mock.patch.object(aq, "flash_screen", return_value=None):
        report = aq.build_report(root, plan)
    assert report["caption"]["required_by_placement"] is True
    assert any(f["code"] == "caption_file_missing" for f in report["findings"])


def test_wcag_aa_requires_approved_audio_description_and_rendered_text(tmp_path):
    root, plan = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["accessibility"].update({"target_level": "WCAG2.2-AA"})
    brief_path.write_text(json.dumps(brief), encoding="utf-8")
    with mock.patch.object(aq, "audio_present", return_value=True), \
         mock.patch.object(aq, "flash_screen", return_value=None):
        report = aq.build_report(root, plan)
    codes = {row["code"] for row in report["findings"] if row["severity"] == "block"}
    assert {"audio_description_missing", "rendered_text_accessibility_missing"} <= codes


def test_named_non_speech_event_must_be_covered_at_same_time(tmp_path):
    root, plan = _project(tmp_path)
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["accessibility"].update({
        "target_level": "WCAG2.2-A",
        "meaningful_non_speech_events": [{"start": 0.2, "end": 1.0, "caption": "门铃响"}],
    })
    brief_path.write_text(json.dumps(brief), encoding="utf-8")
    with mock.patch.object(aq, "audio_present", return_value=True), \
         mock.patch.object(aq, "flash_screen", return_value=None):
        report = aq.build_report(root, plan)
    assert any(row["code"] == "non_speech_event_uncovered" and row["severity"] == "block"
               for row in report["findings"])


def test_every_locale_caption_covers_localized_non_speech_events(tmp_path):
    root, plan = _project(tmp_path)
    (root / "脚本" / "字幕_en.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nStart with coffee\n", encoding="utf-8")
    (root / "合规").mkdir()
    (root / "合规" / "locale_matrix.json").write_text(json.dumps({
        "locales": {
            "zh-CN": {"subtitle_path": "脚本/字幕_zh.srt"},
            "en-US": {"subtitle_path": "脚本/字幕_en.srt"},
        }
    }), encoding="utf-8")
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["accessibility"].update({
        "non_speech_captioning_required": True,
        "meaningful_non_speech_events": [{
            "start": 2.1, "end": 4.0, "caption": "音乐渐强",
            "captions_by_locale": {"zh-CN": "音乐渐强", "en-US": "music swells"},
        }],
    })
    brief_path.write_text(json.dumps(brief), encoding="utf-8")
    with mock.patch.object(aq, "audio_present", return_value=True), \
         mock.patch.object(aq, "flash_screen", return_value=None):
        report = aq.build_report(root, plan)
    assert report["locale_captions"]["en-US"]["sha256"]
    assert any(row["code"] == "non_speech_event_uncovered" and "en-US" in row["msg"]
               for row in report["findings"])
