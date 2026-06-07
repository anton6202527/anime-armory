"""Run from this dir:  python -m pytest test_mechanical_check.py"""
import os
import json
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


# ---- 对账引擎（跨 skill 格式契约）：check_subtitles / check_completeness ----

def _mk(root, ep, zh_cues, manifest):
    """在 tmp 作品根写出 字幕_中文.srt + 时长清单.json 供对账函数读取。"""
    os.makedirs(os.path.join(root, "脚本", ep), exist_ok=True)
    os.makedirs(os.path.join(root, "出视频", ep, "配音"), exist_ok=True)
    if zh_cues is not None:
        srt = "\n\n".join(f"{i}\n{a} --> {z}\n{t}" for i, (a, z, t) in enumerate(zh_cues, 1))
        open(os.path.join(root, "脚本", ep, "字幕_中文.srt"), "w", encoding="utf-8").write(srt)
    if manifest is not None:
        json.dump(manifest, open(os.path.join(root, "出视频", ep, "配音", "时长清单.json"),
                                 "w", encoding="utf-8"), ensure_ascii=False)


def _blocks(substr):
    return [f for f in mc.findings if f[0] == mc.BLOCK and substr in f[3]]


def test_check_subtitles_count_mismatch_blocks(tmp_path):
    mc.findings.clear()
    root, ep = str(tmp_path), "第1集"
    zh = [("00:00:00,000", "00:00:01,000", "你好"), ("00:00:01,200", "00:00:02,000", "再见")]
    man = [{"文本": "你好", "start": 0.0}, {"文本": "再见", "start": 1.2}, {"文本": "多余", "start": 2.2}]
    _mk(root, ep, zh, man)
    mc.check_subtitles(root, ep, man, 20, 42)
    assert _blocks("≠ 配音句数")          # 字幕 2 条 ≠ 配音 3 句 → 阻断


def test_check_subtitles_multiline_cue_matches_manifest(tmp_path):
    # finalize 把长句折成两行；对账时换行/空格须规整掉，不得误报 文本≠（这是真实格式契约）
    mc.findings.clear()
    root, ep = str(tmp_path), "第1集"
    zh = [("00:00:00,000", "00:00:02,000", "本宫倒要看看，\n谁敢动我")]
    man = [{"文本": "本宫倒要看看，谁敢动我", "start": 0.0}]
    _mk(root, ep, zh, man)
    mc.check_subtitles(root, ep, man, 40, 42)
    assert not _blocks("字幕文本≠配音文本")


def test_check_subtitles_text_mismatch_blocks(tmp_path):
    mc.findings.clear()
    root, ep = str(tmp_path), "第1集"
    zh = [("00:00:00,000", "00:00:01,000", "你好")]
    man = [{"文本": "完全不同的台词", "start": 0.0}]
    _mk(root, ep, zh, man)
    mc.check_subtitles(root, ep, man, 20, 42)
    assert _blocks("字幕文本≠配音文本")


def test_check_completeness_placeholder_blocks(tmp_path):
    mc.findings.clear()
    root, ep = str(tmp_path), "第1集"
    man = [{"文本": "你好", "line_wav": "line_00.wav", "占位": True}]
    _mk(root, ep, None, man)
    mc.check_completeness(root, ep, man)
    assert _blocks("占位音色")
