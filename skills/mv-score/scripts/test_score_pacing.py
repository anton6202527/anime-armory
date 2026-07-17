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


# ---- pre-spend 闸门：纯函数 ----

def test_normalize_threshold_scales_ten_point():
    assert sp.normalize_threshold(8) == 80.0
    assert sp.normalize_threshold(80) == 80.0
    assert sp.normalize_threshold(None) is None


def test_pacing_score_pct():
    assert sp.pacing_score_pct(10.0) == 100.0
    assert sp.pacing_score_pct(7.0) == 70.0


def test_map_semantic_dim_stage():
    assert sp.map_semantic_dim_stage("视觉记忆点") == "mv-script"
    assert sp.map_semantic_dim_stage("Visual Hook") == "mv-script"
    assert sp.map_semantic_dim_stage("崩脸") == "mv-image"
    assert sp.map_semantic_dim_stage("单曲视觉一致性") == "mv-image"
    assert sp.map_semantic_dim_stage("踩鼓点率") is None


def test_decide_block_none_threshold_never_blocks():
    report = pacing.pacing_report(GOOD_PLAN, BEATGRID, 24.0)
    score, _ = sp.pacing_score(report)
    blocked, stages, reasons = sp.decide_block(score, report, [], None)
    assert blocked is False and stages == [] and reasons == []


def test_decide_block_good_plan_passes():
    report = pacing.pacing_report(GOOD_PLAN, BEATGRID, 24.0)
    score, _ = sp.pacing_score(report)
    blocked, _stages, _r = sp.decide_block(score, report, [], 80)
    assert blocked is False


def test_decide_block_bad_pacing_returns_mv_plan():
    # 等长 + 偏离歌长 + 副歌不快 → 卡点命门，回 mv-plan
    bad = {"clips": [{"section": "chorus" if i > 3 else "verse1", "duration": 3.0,
                      "start": i * 3.0, "end": (i + 1) * 3.0} for i in range(8)]}
    report = pacing.pacing_report(bad, {"duration": 24.0, "downbeats": [100.0]}, 60.0)
    score, _ = sp.pacing_score(report)
    blocked, stages, reasons = sp.decide_block(score, report, [], 80)
    assert blocked is True and "mv-plan" in stages and reasons


def test_decide_block_low_semantic_dim_routes_to_stage():
    report = pacing.pacing_report(GOOD_PLAN, BEATGRID, 24.0)
    score, _ = sp.pacing_score(report)
    low = sp.low_semantic_dims({"崩脸": 40, "视觉记忆点": 55}, 80.0)
    blocked, stages, _r = sp.decide_block(score, report, low, 80)
    assert blocked is True and "mv-image" in stages and "mv-script" in stages


def test_low_semantic_dims_filters_by_threshold():
    low = sp.low_semantic_dims({"崩脸": 90, "视觉记忆点": 55}, 80.0)
    assert [d["dim"] for d in low] == ["视觉记忆点"]


def test_pacing_affected_clips_flags_off_downbeat():
    off = {"clips": [
        {"clip_id": "Clip_001", "start": 0.0, "end": 1.3, "duration": 1.3},
        {"clip_id": "Clip_002", "start": 1.3, "end": 2.7, "duration": 1.4},
    ]}
    grid = {"downbeats": [10.0, 20.0]}
    report = pacing.pacing_report(off, grid, None)
    clips = sp.pacing_affected_clips(off, grid, report)
    ids = {c["clip_id"] for c in clips}
    assert "Clip_002" in ids
    assert all(c["return_to_stage"] == "mv-plan" for c in clips)


def test_pacing_affected_clips_flags_duration_outlier():
    plan = {"clips": [
        {"clip_id": "Clip_001", "start": 0.0, "end": 2.0, "duration": 2.0},
        {"clip_id": "Clip_002", "start": 2.0, "end": 4.0, "duration": 2.0},
        {"clip_id": "Clip_003", "start": 4.0, "end": 6.0, "duration": 2.0},
        {"clip_id": "Clip_OUT", "start": 6.0, "end": 16.0, "duration": 10.0},
    ]}
    report = pacing.pacing_report(plan, {"downbeats": []}, None)
    clips = sp.pacing_affected_clips(plan, {"downbeats": []}, report)
    outliers = [c for c in clips if c["reason"] == "duration_outlier"]
    assert any(c["clip_id"] == "Clip_OUT" for c in outliers)


def test_semantic_affected_clips_named_and_wildcard():
    low = [{"dim": "崩脸", "score": 40, "clips": ["Clip_003"]}, {"dim": "视觉记忆点", "score": 55}]
    out = sp.semantic_affected_clips(low)
    by = {(c["clip_id"], c["return_to_stage"]) for c in out}
    assert ("Clip_003", "mv-image") in by
    assert ("*", "mv-script") in by


# ---- 闸门 exit code 集成 ----

def test_build_payload_no_threshold_not_blocked():
    tmp = tempfile.mkdtemp()
    try:
        root = write_proj(tmp)
        payload = sp.build_payload(root)
        assert payload["blocked"] is False
        assert payload["return_to_stages"] == []
    finally:
        shutil.rmtree(tmp)


def test_build_payload_good_plan_passes_threshold():
    tmp = tempfile.mkdtemp()
    try:
        root = write_proj(tmp)
        payload = sp.build_payload(root, threshold=80)
        assert payload["blocked"] is False
    finally:
        shutil.rmtree(tmp)


def test_build_payload_bad_plan_blocks_threshold():
    tmp = tempfile.mkdtemp()
    try:
        bad = {"clips": [
            {"clip_id": f"Clip_{i:03d}", "section": "chorus" if i > 3 else "verse1",
             "start": i * 3.0, "end": (i + 1) * 3.0, "duration": 3.0}
            for i in range(8)
        ]}
        root = write_proj(tmp, plan=bad, beatgrid={"duration": 24.0, "downbeats": [100.0]})
        payload = sp.build_payload(root, threshold=80)
        assert payload["blocked"] is True
        assert "mv-plan" in payload["return_to_stages"]
        assert payload["affected_clips"]
    finally:
        shutil.rmtree(tmp)


def test_build_payload_semantic_dim_blocks_and_routes():
    tmp = tempfile.mkdtemp()
    try:
        root = write_proj(tmp)
        payload = sp.build_payload(root, threshold=80, dim_scores={"崩脸": 40})
        assert payload["blocked"] is True
        assert "mv-image" in payload["return_to_stages"]
        assert any(c["return_to_stage"] == "mv-image" for c in payload["affected_clips"])
    finally:
        shutil.rmtree(tmp)


def test_enqueue_writes_mv_rework_queue():
    tmp = tempfile.mkdtemp()
    try:
        bad = {"clips": [
            {"clip_id": f"Clip_{i:03d}", "section": "chorus" if i > 3 else "verse1",
             "start": i * 3.0, "end": (i + 1) * 3.0, "duration": 3.0}
            for i in range(8)
        ]}
        root = write_proj(tmp, plan=bad, beatgrid={"duration": 24.0, "downbeats": [100.0]})
        payload = sp.build_payload(root, threshold=80)
        out, queue = sp.write_enqueue(root, payload)
        assert os.path.exists(out)
        assert queue["kind"] == "mv_score_rework_queue"
        assert any(t["return_to_stage"] == "mv-plan" for t in queue["tasks"])
        loaded = json.load(open(out, encoding="utf-8"))
        assert loaded["blocked"] is True
    finally:
        shutil.rmtree(tmp)


def test_late_cut_bias_flags_systematic_late_cuts():
    # 切点全部落在 downbeat 之后 0.10s（对齐窗口 ±0.15s 内、超晚切容差 0.04s）→ 全晚切
    late_plan = {"clips": [
        {"clip_id": "C1", "section": "verse", "start": 0.0, "end": 4.10, "duration": 4.10},
        {"clip_id": "C2", "section": "verse", "start": 4.10, "end": 8.10, "duration": 4.0},
        {"clip_id": "C3", "section": "verse", "start": 8.10, "end": 12.10, "duration": 4.0},
        {"clip_id": "C4", "section": "verse", "start": 12.10, "end": 24.0, "duration": 11.9},
    ]}
    late, aligned, ratio = pacing.late_cut_bias(late_plan, BEATGRID)
    assert aligned == 3 and late == 3 and ratio == 1.0


def test_late_cut_bias_quiet_on_grid_or_early():
    # 压拍切（GOOD_PLAN）→ 零晚切
    late, aligned, ratio = pacing.late_cut_bias(GOOD_PLAN, BEATGRID)
    assert late == 0 and ratio == 0.0
    # 提前 2-3 帧落刀（-0.10s）是专业手法 → 不算晚切
    early_plan = {"clips": [
        {"clip_id": "C1", "section": "verse", "start": 0.0, "end": 3.90, "duration": 3.90},
        {"clip_id": "C2", "section": "verse", "start": 3.90, "end": 7.90, "duration": 4.0},
        {"clip_id": "C3", "section": "verse", "start": 7.90, "end": 24.0, "duration": 16.1},
    ]}
    late, aligned, ratio = pacing.late_cut_bias(early_plan, BEATGRID)
    assert aligned == 2 and late == 0 and ratio == 0.0


def test_late_cut_bias_none_without_aligned_cuts():
    late, aligned, ratio = pacing.late_cut_bias({"clips": []}, BEATGRID)
    assert ratio is None


def test_pacing_report_includes_late_cut_bias():
    report = pacing.pacing_report(GOOD_PLAN, BEATGRID, 24.0)
    assert "late_cut_bias" in report
    assert report["late_cut_bias"]["ratio"] == 0.0


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"ok - {len(tests)} tests")


if __name__ == "__main__":
    main()
