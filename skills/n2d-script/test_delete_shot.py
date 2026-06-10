#!/usr/bin/env python3
"""Tests for delete_shot.py reflow (CLI-only script → invoked via subprocess).

Builds a minimal work dir mimicking the layout delete_shot reads:
  合成/<ep>/配音/时长清单.json + line_NN.wav
  脚本/<ep>/voiceover.txt
  脚本/<ep>/字幕_英文.srt
Then deletes one shot and asserts the 时长清单 reflow renumbers the remaining
entries (no off-by-one) and drops the targeted one. line_*.wav files are
renamed to a contiguous sequence; the deleted shot's wav is moved to 废料/.

Run from this directory:
    cd skills/n2d-script && python3 -m pytest test_delete_shot.py
"""
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _no_ffmpeg_env(tmp_path):
    """Env with an empty PATH so shutil.which('ffmpeg') returns None.

    The dummy line_*.wav files we write are not valid audio; with real ffmpeg
    on PATH the re-stitch step (check=True) would crash on them. Hiding ffmpeg
    drives the script's no-ffmpeg branch (voice_zh.wav → .stale) while still
    exercising the deterministic 时长清单 reflow + line-wav rename + EN-subtitle
    index-synced deletion, then finalize_storyboard (pure python). We use
    sys.executable (absolute) so python is unaffected by the empty PATH.
    """
    env = dict(os.environ)
    env["PATH"] = str(tmp_path / "_emptybin")
    os.makedirs(env["PATH"], exist_ok=True)
    return env


def _build_work(root, ep):
    conf = os.path.join(root, "合成", ep, "配音")
    sdir = os.path.join(root, "脚本", ep)
    os.makedirs(conf, exist_ok=True)
    os.makedirs(sdir, exist_ok=True)

    # 时长清单: 3 lines across 3 distinct shots; include start/end so
    # finalize_storyboard consumes the real timeline (no placeholder lines).
    manifest = [
        {"idx": 0, "镜头": "镜头1", "文本": "第一句。", "时长": 2.0,
         "start": 0.0, "end": 2.0, "gap_after": 0.4, "line_wav": "line_00.wav"},
        {"idx": 1, "镜头": "镜头2", "文本": "第二句。", "时长": 2.0,
         "start": 2.4, "end": 4.4, "gap_after": 0.4, "line_wav": "line_01.wav"},
        {"idx": 2, "镜头": "镜头3", "文本": "第三句。", "时长": 2.0,
         "start": 4.8, "end": 6.8, "gap_after": 0.0, "line_wav": "line_02.wav"},
    ]
    json.dump(manifest, open(os.path.join(conf, "时长清单.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # line wavs (content is irrelevant; only renames/moves are tested)
    for i in range(3):
        with open(os.path.join(conf, f"line_{i:02d}.wav"), "wb") as f:
            f.write(b"RIFF0000WAVE")

    # voiceover.txt: one line per shot, tagged so shot_of() matches
    with open(os.path.join(sdir, "voiceover.txt"), "w", encoding="utf-8") as f:
        f.write("[镜头1·甲·平] 第一句。\n")
        f.write("[镜头2·乙·平] 第二句。\n")
        f.write("[镜头3·丙·平] 第三句。\n")

    # 字幕_英文.srt: 3 blocks, index-synced with manifest
    en = (
        "1\n00:00:00,000 --> 00:00:02,000\nLine one\n\n"
        "2\n00:00:02,400 --> 00:00:04,400\nLine two\n\n"
        "3\n00:00:04,800 --> 00:00:06,800\nLine three\n"
    )
    with open(os.path.join(sdir, "字幕_英文.srt"), "w", encoding="utf-8") as f:
        f.write(en)

    return conf, sdir


def test_delete_middle_shot_reflows(tmp_path):
    root, ep = str(tmp_path), "第1集"
    conf, sdir = _build_work(root, ep)

    r = subprocess.run(
        [sys.executable, os.path.join(_HERE, "delete_shot.py"), root, ep, "镜头2"],
        capture_output=True, text=True, env=_no_ffmpeg_env(tmp_path),
    )
    assert r.returncode == 0, f"delete_shot failed: {r.stdout}\n{r.stderr}"

    # 时长清单 reflow: 3 → 2 entries, renumbered idx 0,1 contiguously, 镜头2 gone
    man = json.load(open(os.path.join(conf, "时长清单.json"), encoding="utf-8"))
    assert len(man) == 2
    assert [r["idx"] for r in man] == [0, 1]
    assert [r["line_wav"] for r in man] == ["line_00.wav", "line_01.wav"]
    assert [r["镜头"] for r in man] == ["镜头1", "镜头3"]
    # remaining entries keep their original text/时长 (durations unchanged)
    assert man[0]["文本"] == "第一句。" and man[1]["文本"] == "第三句。"
    assert man[0]["时长"] == 2.0 and man[1]["时长"] == 2.0

    # line wavs on disk are the contiguous renamed set
    wavs = sorted(f for f in os.listdir(conf) if f.startswith("line_") and f.endswith(".wav"))
    assert wavs == ["line_00.wav", "line_01.wav"]

    # deleted shot's wav (originally line_01.wav) moved to 废料/
    waste = os.path.join(root, "废料", "合成", ep, "配音")
    assert os.path.exists(os.path.join(waste, "line_01.wav"))

    # voiceover.txt no longer references 镜头2
    vo = open(os.path.join(sdir, "voiceover.txt"), encoding="utf-8").read()
    assert "镜头2" not in vo
    assert "镜头1" in vo and "镜头3" in vo

    # 字幕_英文.srt: index-synced deletion drops the 2nd block (no off-by-one)
    en = open(os.path.join(sdir, "字幕_英文.srt"), encoding="utf-8").read()
    assert "Line one" in en and "Line three" in en
    assert "Line two" not in en


def test_delete_unknown_shot_noop(tmp_path):
    root, ep = str(tmp_path), "第1集"
    conf, _ = _build_work(root, ep)
    r = subprocess.run(
        [sys.executable, os.path.join(_HERE, "delete_shot.py"), root, ep, "镜头99"],
        capture_output=True, text=True, env=_no_ffmpeg_env(tmp_path),
    )
    # No matching shot → exits without rewriting the manifest
    assert r.returncode != 0 or "无改动" in r.stdout
    man = json.load(open(os.path.join(conf, "时长清单.json"), encoding="utf-8"))
    assert len(man) == 3
