"""score_pacing 单测（确定性路径，覆盖四个卡点指标 + 机器预评分）。
从脚本自身目录跑：
    cd skills/mv-score/scripts && python -m pytest test_score_pacing.py
或直接：
    python3 test_score_pacing.py
"""
import json
import os
import shutil
import tempfile

import score_pacing as sp

pacing = sp.pacing


BEATGRID = {
    "song": "歌/song.wav",
    "duration": 24.0,
    "bpm": 120,
    "meter": 4,
    "downbeats": [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0],
    "beats": [round(i * 0.5, 3) for i in range(49)],
}

# 副歌快切（2s/刀）、主歌长镜（4s/刀），切点都踩在 downbeat 上 → 健康节奏
GOOD_PLAN = {
    "clips": [
        {"clip_id": "Clip_001", "section": "verse1", "start": 0.0, "end": 4.0, "duration": 4.0},
        {"clip_id": "Clip_002", "section": "verse1", "start": 4.0, "end": 8.0, "duration": 4.0},
        {"clip_id": "Clip_003", "section": "chorus", "start": 8.0, "end": 10.0, "duration": 2.0},
        {"clip_id": "Clip_004", "section": "chorus", "start": 10.0, "end": 12.0, "duration": 2.0},
        {"clip_id": "Clip_005", "section": "chorus", "start": 12.0, "end": 14.0, "duration": 2.0},
        {"clip_id": "Clip_006", "section": "chorus", "start": 14.0, "end": 16.0, "duration": 2.0},
        {"clip_id": "Clip_007", "section": "verse2", "start": 16.0, "end": 20.0, "duration": 4.0},
        {"clip_id": "Clip_008", "section": "verse2", "start": 20.0, "end": 24.0, "duration": 4.0},
    ]
}


def write_proj(tmp, plan=GOOD_PLAN, beatgrid=BEATGRID, meta=None, song=False):
    root = os.path.join(tmp, "曲")
    for d in ("分镜", "节拍", "歌"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    json.dump(plan, open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8"))
    json.dump(beatgrid, open(os.path.join(root, "节拍", "beatgrid.json"), "w", encoding="utf-8"))
    meta = meta or {"title": "曲", "structure": ["verse1", "chorus", "verse2"]}
    json.dump(meta, open(os.path.join(root, "_meta.json"), "w", encoding="utf-8"))
    return root


# ---- pure pacing engine ----

def test_equal_length_cv_flags_uniform():
    plan = {"clips": [{"duration": 3.0} for _ in range(6)]}
    cv, suspicious, n = pacing.equal_length_cv(plan)
    assert suspicious and n == 6 and cv == 0.0


def test_equal_length_cv_ok_when_varied():
    _cv, suspicious, _n = pacing.equal_length_cv(GOOD_PLAN)
    assert not suspicious


def test_equal_length_cv_too_few_not_judged():
    _cv, suspicious, n = pacing.equal_length_cv({"clips": [{"duration": 3.0}, {"duration": 3.0}]})
    assert not suspicious and n == 2


def test_planned_duration_vs_song_match():
    total, song, diff, mismatch = pacing.planned_duration_vs_song(GOOD_PLAN, 24.0)
    assert total == 24.0 and song == 24.0 and diff == 0.0 and mismatch is False


def test_planned_duration_vs_song_mismatch():
    _t, _s, _d, mismatch = pacing.planned_duration_vs_song(GOOD_PLAN, 60.0)
    assert mismatch is True


def test_planned_duration_no_song_len():
    total, song, diff, mismatch = pacing.planned_duration_vs_song(GOOD_PLAN, None)
    assert total == 24.0 and song is None and diff is None and mismatch is None


def test_downbeat_alignment_high_on_grid():
    aligned, total, ratio = pacing.clip_downbeat_alignment(GOOD_PLAN, BEATGRID)
    # 7 internal boundaries, all on downbeats
    assert total == 7 and ratio == 1.0 and aligned == 7


def test_downbeat_alignment_low_off_grid():
    off = {"clips": [
        {"start": 0.0, "end": 1.3, "duration": 1.3},
        {"start": 1.3, "end": 2.7, "duration": 1.4},
        {"start": 2.7, "end": 4.1, "duration": 1.4},
        {"start": 4.1, "end": 5.5, "duration": 1.4},
    ]}
    grid = {"downbeats": [10.0, 20.0]}
    _a, total, ratio = pacing.clip_downbeat_alignment(off, grid)
    assert total == 3 and ratio == 0.0


def test_chorus_verse_density_chorus_faster():
    d = pacing.chorus_verse_density(GOOD_PLAN)
    # chorus 4 clips / 8s = 0.5 ; verse 4 clips / 16s = 0.25 ; contrast 2.0
    assert d["ok"] is True and d["contrast"] and d["contrast"] > 1


def test_chorus_verse_density_chorus_too_slow():
    slow = {"clips": [
        {"section": "verse1", "start": 0.0, "end": 2.0, "duration": 2.0},
        {"section": "verse1", "start": 2.0, "end": 4.0, "duration": 2.0},
        {"section": "chorus", "start": 4.0, "end": 12.0, "duration": 8.0},
    ]}
    d = pacing.chorus_verse_density(slow)
    assert d["ok"] is False


# ---- score_pacing integration ----

def test_build_payload_good_high_score():
    tmp = tempfile.mkdtemp()
    try:
        root = write_proj(tmp)
        payload = sp.build_payload(root)
        assert payload["pacing_score"] >= 9.0
        assert payload["song_len_source"] == "beatgrid"
        assert payload["metrics"]["chorus_verse_density"]["ok"] is True
    finally:
        shutil.rmtree(tmp)


def test_build_payload_writes_json_via_main(monkeypatch=None):
    tmp = tempfile.mkdtemp()
    try:
        root = write_proj(tmp)
        payload = sp.build_payload(root)
        out = os.path.join(root, "评分", "pacing_prescore.json")
        sp.mv_utils.write_json(out, payload)
        assert os.path.exists(out)
        loaded = json.load(open(out, encoding="utf-8"))
        assert loaded["kind"] == "mv_pacing_prescore"
    finally:
        shutil.rmtree(tmp)


def test_build_payload_bad_plan_penalized():
    tmp = tempfile.mkdtemp()
    try:
        # uniform durations + off-grid + chorus not faster
        bad = {"clips": [
            {"clip_id": f"Clip_{i:03d}", "section": "chorus" if i > 3 else "verse1",
             "start": i * 3.0, "end": (i + 1) * 3.0, "duration": 3.0}
            for i in range(8)
        ]}
        root = write_proj(tmp, plan=bad, beatgrid={"duration": 24.0, "downbeats": [100.0]})
        payload = sp.build_payload(root)
        assert payload["pacing_score"] < 9.0
    finally:
        shutil.rmtree(tmp)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"ok - {len(tests)} tests")


if __name__ == "__main__":
    main()
