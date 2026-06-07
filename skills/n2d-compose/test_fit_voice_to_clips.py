"""从本目录跑：cd skills/n2d-compose && python -m pytest test_fit_voice_to_clips.py"""
from fit_voice_to_clips import plan, shot_num, aggregate_reals


def test_shot_num_orders_naturally():
    assert sorted(["镜头10", "镜头2", "镜头1"], key=shot_num) == ["镜头1", "镜头2", "镜头10"]


def test_pad_when_real_shorter_or_equal():
    rows = plan([("镜头1", 5.0)], {"镜头1": (4.0, "a.wav")})
    assert rows[0]["action"] == "pad" and rows[0]["over"] == 0.0


def test_silent_slot_when_no_line():
    rows = plan([("镜头1", 3.0)], {})  # 该镜头无台词
    assert rows[0]["action"] == "pad" and rows[0]["wav"] is None


def test_stretch_within_max():
    rows = plan([("镜头1", 4.0)], {"镜头1": (4.8, "a.wav")}, max_stretch=1.25)
    r = rows[0]
    assert r["action"] == "stretch" and abs(r["ratio"] - 1.2) < 1e-6


def test_overflow_beyond_max():
    rows = plan([("镜头1", 4.0)], {"镜头1": (6.0, "a.wav")}, max_stretch=1.25)
    assert rows[0]["action"] == "overflow" and rows[0]["over"] == 2.0


def test_minor_flag_small_overflow_inside_tolerance():
    # 槽位 5s，真音超 0.2s（< tol=max(0.5,0.3)）→ 标 minor（几乎无感的提速）
    rows = plan([("镜头1", 5.0)], {"镜头1": (5.2, "a.wav")}, tol_frac=0.10, tol_min=0.3)
    assert rows[0]["action"] == "stretch" and rows[0]["minor"] is True


def test_fitted_total_equals_locked_total():
    # 拟合后每段=槽位长，故总长必等于锁定槽位总长（与真音长无关）→ 与视频对齐的关键保证
    slots = [("镜头1", 5.0), ("镜头2", 3.0), ("镜头3", 4.0)]
    reals = {"镜头1": (4.2, "a"), "镜头2": (3.9, "b"), "镜头3": (4.0, "c")}
    rows = plan(slots, reals)
    assert abs(sum(r["slot"] for r in rows) - 12.0) < 1e-9


# ---- aggregate_reals：多句同镜头不再丢音（B1 回归）----

def test_aggregate_sums_all_lines_in_a_shot():
    # 镜头1 含两句，镜头2 一句；按 finalize 口径 ∑(句时长+句后留拍)
    man = [
        {"镜头": "镜头1", "line_wav": "line_00.wav", "时长": 2.0, "gap_after": 0.4},
        {"镜头": "镜头1", "line_wav": "line_01.wav", "时长": 3.0, "gap_after": 0.0},
        {"镜头": "镜头2", "line_wav": "line_02.wav", "时长": 1.5, "gap_after": 0.0},
    ]
    durs = {"/v/line_00.wav": 2.0, "/v/line_01.wav": 3.0, "/v/line_02.wav": 1.5}
    reals = aggregate_reals(man, "/v", lambda p: durs.get(p, 0.0))
    # 关键：镜头1 两句都计入（2.0+0.4 + 3.0 = 5.4），不再只剩最后一句的 3.0
    assert abs(reals["镜头1"][0] - 5.4) < 1e-9
    assert len(reals["镜头1"][1]) == 2          # parts 保留两句，build_fitted 会全拼回
    assert abs(reals["镜头2"][0] - 1.5) < 1e-9


def test_aggregate_multiline_drives_plan_on_full_duration():
    # 多句镜头的拟合判定应基于全镜头真音，而非末句
    man = [
        {"镜头": "镜头1", "line_wav": "a", "时长": 2.0, "gap_after": 0.4},
        {"镜头": "镜头1", "line_wav": "b", "时长": 3.0, "gap_after": 0.0},
    ]
    reals = aggregate_reals(man, "", lambda p: {"a": 2.0, "b": 3.0}.get(p, 0.0))
    rows = plan([("镜头1", 5.0)], reals)          # 槽位 5.0 < 真音 5.4 → 需提速
    assert rows[0]["real"] == 5.4 and rows[0]["action"] == "stretch"


def test_aggregate_missing_wav_falls_back_to_manifest_duration():
    # line_wav 探测失败(0) → 退回清单 时长 字段，并以 None 标记静音占位
    man = [{"镜头": "镜头1", "line_wav": "x", "时长": 2.5, "gap_after": 0.0}]
    reals = aggregate_reals(man, "", lambda p: 0.0)
    assert abs(reals["镜头1"][0] - 2.5) < 1e-9
    assert reals["镜头1"][1][0][0] is None
