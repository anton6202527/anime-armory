"""从本目录跑：cd skills/n2d-compose && python -m pytest test_fit_voice_to_clips.py"""
from fit_voice_to_clips import plan, shot_num


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
