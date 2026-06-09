"""song_check 机检单测。从脚本自身目录跑：
    cd skills/song-review/scripts && python -m pytest test_song_check.py
"""
import os, json, wave, array, math, tempfile, shutil
import song_check as sc

BLOCK, WARN = sc.BLOCK, sc.WARN


def write_wav(path, *, seconds=35, rate=48000, ch=2, kind="tone"):
    n = int(seconds * rate)
    a = array.array("h")
    full = 32767
    for i in range(n):
        if kind == "silent":
            v = 0
        elif kind == "clip":
            v = full if (i // 64) % 2 == 0 else -full   # 方波，贴满量程 → 削波
        elif kind == "lead_silence" and i < 5 * rate:
            v = 0
        elif kind == "tail_silence" and i >= n - 5 * rate:
            v = 0
        else:  # tone：约 -6dBFS 正弦
            v = int(0.5 * full * math.sin(2 * math.pi * 220 * i / rate))
        for _ in range(ch):
            a.append(v)
    with wave.open(path, "wb") as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(a.tobytes())


CLEAN_LYRICS = """# 歌词

[verse1]
晨钟惊起了一山的霜花
师父的背影还留在云上家
他说剑要藏好心别太慌
十年磨一剑只为出鞘光芒

[chorus]
我仗剑下山闯一闯人间
江湖那么大我走在最前
风雪也好刀光也好不闪
少年眼里只有山高水远

[outro]
（竹笛淡出）
"""


def make_project(tmp, *, lyrics=CLEAN_LYRICS, meta=None, wav="tone", structure=None):
    root = os.path.join(tmp, "曲")
    os.makedirs(os.path.join(root, "词"), exist_ok=True)
    os.makedirs(os.path.join(root, "歌"), exist_ok=True)
    open(os.path.join(root, "创作蓝图.md"), "w").write("# 蓝图\n")
    open(os.path.join(root, "_进度.md"), "w").write("# 进度\n作曲 song-compose 已出歌\n")
    open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8").write(lyrics)
    if meta is None:
        meta = {"title": "曲", "vocal_source": "synthetic", "rights_status": "original"}
    if structure is not None:
        meta["structure"] = structure
    json.dump(meta, open(os.path.join(root, "_meta.json"), "w", encoding="utf-8"))
    if wav is not None:
        write_wav(os.path.join(root, "歌", "song.wav"), kind=wav)
    return root


def run(root, **kw):
    sc.findings.clear()
    meta = sc.load_json(os.path.join(root, "_meta.json"))
    prog = open(os.path.join(root, "_进度.md"), encoding="utf-8").read()
    sc.check_completeness(root)
    sc.check_lyrics(root, meta, kw.get("spread", sc.SPREAD_MAX))
    sc.check_audio(root, prog, meta)
    sc.check_take_manifest(root)
    sc.check_compliance(root, meta)
    sc.check_ai_usage(root, meta)
    return list(sc.findings)


def sev_dims(findings, sev):
    return {d for s, d, _, _ in findings if s == sev}


def test_clean_project_no_block():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp))
        assert not [x for x in f if x[0] == BLOCK], f
    finally:
        shutil.rmtree(tmp)


def test_placeholder_blocks():
    tmp = tempfile.mkdtemp()
    try:
        ly = CLEAN_LYRICS.replace("少年眼里只有山高水远", "（待填这句副歌）")
        f = run(make_project(tmp, lyrics=ly))
        assert any(s == BLOCK and d == "词" for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_missing_chorus_blocks():
    tmp = tempfile.mkdtemp()
    try:
        ly = CLEAN_LYRICS.replace("[chorus]", "[verse2]")
        f = run(make_project(tmp, lyrics=ly))
        assert any(s == BLOCK and "副歌" in m for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_silent_wav_blocks():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp, wav="silent"))
        assert any(s == BLOCK and d == "音频" for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_clipping_wav_flagged():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp, wav="clip"))
        assert any(d == "音频" and "削波" in m for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_missing_vocal_source_blocks():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp, meta={"title": "曲", "rights_status": "original"}))
        assert any(s == BLOCK and d == "合规" for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_unauthorized_real_voice_blocks():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp, meta={"title": "曲", "vocal_source": "real singer 周某", "rights_status": "original"}))
        assert any(s == BLOCK and d == "合规" for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_line_spread_warns():
    tmp = tempfile.mkdtemp()
    try:
        ly = """# 歌词

[verse1]
短
这一行明显要长出去很多很多字啊真的

[chorus]
我仗剑下山闯一闯人间
江湖那么大我走在最前
"""
        f = run(make_project(tmp, lyrics=ly))
        assert any(s == WARN and d == "词" and "极差" in m for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_structure_mismatch_warns():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp, structure=["intro", "verse1", "chorus", "verse2", "outro"]))
        assert any(s == WARN and "structure" in m for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_low_samplerate_warns():
    tmp = tempfile.mkdtemp()
    try:
        root = make_project(tmp, wav=None)
        write_wav(os.path.join(root, "歌", "song.wav"), rate=22050, kind="tone")
        f = run(root)
        assert any(d == "音频" and "采样率" in m for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_target_duration_warns():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp, meta={
            "title": "曲",
            "vocal_source": "synthetic",
            "rights_status": "original",
            "target_duration_seconds": 120,
        }))
        assert any(d == "音频" and "偏离目标" in m for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_edge_silence_warns():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp, wav="lead_silence"))
        assert any(d == "音频" and "开头静音" in m for s, d, l, m in f), f
    finally:
        shutil.rmtree(tmp)


def test_missing_take_manifest_warns_without_blocking():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_project(tmp))
        assert any(s == WARN and d == "挑版" for s, d, l, m in f), f
        assert not [x for x in f if x[0] == BLOCK], f
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    for name, fn in tests:
        fn()
    print(f"OK ({len(tests)} tests)")
