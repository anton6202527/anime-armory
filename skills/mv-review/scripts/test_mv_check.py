"""mv_check 机检单测（覆盖 stdlib 确定性路径；clip/成片 的 ffprobe 路径在真机 demo 跑）。
从脚本自身目录跑：
    cd skills/mv-review/scripts && python -m pytest test_mv_check.py
或直接：
    python3 test_mv_check.py
"""
import os, json, wave, array, tempfile, shutil
import mv_check as mc

BLOCK, WARN = mc.BLOCK, mc.WARN


def write_wav(path, seconds=6, rate=8000):
    n = int(seconds * rate)
    a = array.array("h", [0] * n)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(a.tobytes())


LYRICS = """# 歌词

[verse1]
晨钟惊起一山霜
师父背影留云上

[chorus]
我仗剑下山闯人间
江湖那么大走最前
"""

LRC = "[00:01.00]我仗剑下山闯人间\n[00:03.00]江湖那么大走最前\n"

BEATGRID = {
    "song": "歌/song.wav", "duration": 6.0, "bpm": 120, "meter": 4,
    "beats": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
    "downbeats": [0.5, 2.5, 4.5],
}
STRUCTURE = ["verse1", "chorus"]


def make_mv(tmp, *, lyrics=LYRICS, lrc=LRC, beatgrid=None, meta=None,
            song=True, structure=STRUCTURE, progress="# 进度\n"):
    root = os.path.join(tmp, "曲")
    for d in ("词", "歌", "节拍", "字幕", "分镜", "出视频", "合规"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    open(os.path.join(root, "视觉蓝图.md"), "w").write("# 蓝图\n")
    open(os.path.join(root, "_进度.md"), "w", encoding="utf-8").write(progress)
    if lyrics is not None:
        open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8").write(lyrics)
    if lrc is not None:
        open(os.path.join(root, "字幕", "lyrics.lrc"), "w", encoding="utf-8").write(lrc)
    bg = BEATGRID if beatgrid is None else beatgrid
    if bg is not None:
        if bg == "CORRUPT":
            open(os.path.join(root, "节拍", "beatgrid.json"), "w").write("{not json")
        else:
            json.dump(bg, open(os.path.join(root, "节拍", "beatgrid.json"), "w"))
    if song:
        write_wav(os.path.join(root, "歌", "song.wav"))
    if meta is None:
        meta = {"title": "曲", "aspect": "9:16", "structure": structure,
                "has_song": True, "has_lyrics": True}
    json.dump(meta, open(os.path.join(root, "_meta.json"), "w", encoding="utf-8"))
    return root


def run(root):
    mc.findings.clear()
    meta = mc.load_json(os.path.join(root, "_meta.json"))
    songlen = mc.wav_duration(os.path.join(root, "歌", "song.wav"))
    mc.check_completeness(root)
    ll = mc.check_lyrics_and_meta(root, meta)
    mc.check_beatgrid(root, songlen)
    mc.check_plan_manifests(root, songlen)
    mc.check_video_jobs(root)
    mc.check_clips(root, songlen)
    mc.check_subtitles(root, songlen, ll)
    mc.check_alignment_report(root)
    mc.check_final(root, meta, songlen)
    mc.check_ai_usage(root)
    return list(mc.findings)


def has(f, sev=None, dim=None, sub=None):
    return any((sev is None or s == sev) and (dim is None or d == dim)
               and (sub is None or sub in m) for s, d, l, m in f)


def test_clean_no_block():
    tmp = tempfile.mkdtemp()
    try:
        assert not [x for x in run(make_mv(tmp)) if x[0] == BLOCK], run(make_mv(tmp))
    finally:
        shutil.rmtree(tmp)


def test_beatgrid_corrupt_blocks():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, beatgrid="CORRUPT")), BLOCK, "卡点")
    finally:
        shutil.rmtree(tmp)


def test_bpm_out_of_range_warns():
    tmp = tempfile.mkdtemp()
    try:
        bg = dict(BEATGRID, bpm=300)
        assert has(run(make_mv(tmp, beatgrid=bg)), WARN, sub="半速/倍速")
    finally:
        shutil.rmtree(tmp)


def test_beats_non_monotonic_warns():
    tmp = tempfile.mkdtemp()
    try:
        bg = dict(BEATGRID, beats=[0.5, 0.4, 1.0])
        assert has(run(make_mv(tmp, beatgrid=bg)), WARN, sub="递增")
    finally:
        shutil.rmtree(tmp)


def test_beatgrid_duration_mismatch_warns():
    tmp = tempfile.mkdtemp()
    try:
        bg = dict(BEATGRID, duration=30.0)   # 歌只有 6s
        assert has(run(make_mv(tmp, beatgrid=bg)), WARN, "卡点", "歌长")
    finally:
        shutil.rmtree(tmp)


def test_subtitle_placeholder_blocks():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, lrc="[00:01.00]（待填这句）\n")), BLOCK, "字幕")
    finally:
        shutil.rmtree(tmp)


def test_subtitle_out_of_range_warns():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, lrc="[00:01.00]行一\n[00:59.00]越界行\n")), WARN, "字幕", "越界")
    finally:
        shutil.rmtree(tmp)


def test_subtitle_disorder_warns():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, lrc="[00:03.00]后\n[00:01.00]前\n")), WARN, "字幕")
    finally:
        shutil.rmtree(tmp)


def test_lyrics_placeholder_blocks():
    tmp = tempfile.mkdtemp()
    try:
        ly = LYRICS.replace("江湖那么大走最前", "TODO 这句副歌")
        assert has(run(make_mv(tmp, lyrics=ly)), BLOCK)
    finally:
        shutil.rmtree(tmp)


def test_structure_mismatch_warns():
    tmp = tempfile.mkdtemp()
    try:
        assert has(run(make_mv(tmp, structure=["intro", "verse1", "chorus", "outro"])), WARN, sub="structure")
    finally:
        shutil.rmtree(tmp)


def test_meta_has_song_stale_warns():
    tmp = tempfile.mkdtemp()
    try:
        meta = {"title": "曲", "aspect": "9:16", "structure": STRUCTURE, "has_song": False, "has_lyrics": True}
        assert has(run(make_mv(tmp, meta=meta)), WARN, sub="has_song" if False else "未更新")
    finally:
        shutil.rmtree(tmp)


def test_missing_final_with_compose_progress_warns():
    tmp = tempfile.mkdtemp()
    try:
        f = run(make_mv(tmp, progress="# 进度\nmv-compose 已合成成片\n"))
        assert has(f, WARN, "音画")
    finally:
        shutil.rmtree(tmp)


def test_duplicate_plan_clip_id_blocks():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        plan = {
            "clips": [
                {"clip_id": "Clip_001", "start": 0.0, "end": 3.0, "duration": 3.0},
                {"clip_id": "Clip_001", "start": 3.0, "end": 6.0, "duration": 3.0},
            ]
        }
        json.dump(plan, open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert has(run(root), BLOCK, "规划", "clip_id 重复")
    finally:
        shutil.rmtree(tmp)


def test_timeline_missing_selected_video_warns():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        plan = {"clips": [{"clip_id": "Clip_001", "start": 0.0, "end": 6.0, "duration": 6.0}]}
        timeline = {"clips": [{"clip_id": "Clip_001", "video_path": "出视频/视频/Clip_001.mp4"}]}
        json.dump(plan, open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(timeline, open(os.path.join(root, "分镜", "timeline_manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert has(run(root), WARN, "规划", "video_path 尚不存在")
    finally:
        shutil.rmtree(tmp)


def test_selected_video_job_missing_clip_blocks():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        manifest = {
            "jobs": [{
                "clip_id": "Clip_001",
                "selected_take": "take_01",
                "selected_video_path": "出视频/视频/Clip_001.mp4",
            }]
        }
        json.dump(manifest, open(os.path.join(root, "出视频", "jobs_manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert has(run(root), BLOCK, "规划", "selected_take 已选但成品 clip 不存在")
    finally:
        shutil.rmtree(tmp)


def test_alignment_report_warnings_surface():
    tmp = tempfile.mkdtemp()
    try:
        root = make_mv(tmp)
        report = {"lyric_lines": 2, "aligned_lines": 1, "unused_word_segments": 3, "warnings": ["歌词与演唱疑似不一致"]}
        json.dump(report, open(os.path.join(root, "字幕", "alignment_report.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert has(run(root), WARN, "字幕", "歌词与演唱疑似不一致")
    finally:
        shutil.rmtree(tmp)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"ok - {len(tests)} tests")


if __name__ == "__main__":
    main()
