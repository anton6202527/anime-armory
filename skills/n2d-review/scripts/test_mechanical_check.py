"""Run from this dir:  python -m pytest test_mechanical_check.py"""
import mechanical_check as mc


def test_tc_to_sec():
    assert mc.tc_to_sec("00:00:00,000") == 0
    assert abs(mc.tc_to_sec("00:01:02,500") - 62.5) < 1e-6
    assert abs(mc.tc_to_sec("01:00:00,000") - 3600) < 1e-6


def test_parse_srt(tmp_path):
    p = tmp_path / "s.srt"
    p.write_text("1\n00:00:00,000 --> 00:00:01,500\n你好\n\n"
                 "2\n00:00:01,600 --> 00:00:03,000\nworld\nline2\n", encoding="utf-8")
    cues = mc.parse_srt(str(p))
    assert len(cues) == 2
    assert cues[0]["text"] == "你好"
    assert abs(cues[0]["end"] - 1.5) < 1e-6
    assert cues[1]["text"] == "world\nline2"


def test_parse_srt_missing():
    assert mc.parse_srt("/no/such/file.srt") is None


def test_placeholder_regex():
    assert mc.PLACEHOLDER.search("（待精修：依据 voiceover）")
    assert mc.PLACEHOLDER.search("placeholder text")
    assert not mc.PLACEHOLDER.search("正常的字幕文本")
