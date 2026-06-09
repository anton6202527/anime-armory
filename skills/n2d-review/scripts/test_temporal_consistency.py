"""temporal_consistency 纯数学单测（无需 ffmpeg/insightface）。
cd skills/n2d-review/scripts && python -m pytest test_temporal_consistency.py
"""
import temporal_consistency as tc


def test_pairwise_absdiff():
    got = tc.pairwise_consecutive_absdiff([0.1, 0.3, 0.2])
    assert len(got) == 2 and abs(got[0] - 0.2) < 1e-9 and abs(got[1] - 0.1) < 1e-9
    assert tc.pairwise_consecutive_absdiff([0.5]) == []
    assert tc.pairwise_consecutive_absdiff([]) == []


def test_flicker_constant_is_zero():
    assert tc.flicker_index([0.4, 0.4, 0.4, 0.4]) == 0.0
    assert tc.flicker_index([0.4]) == 0.0


def test_flicker_alternating_positive():
    # 0,1,0,1 → 每跳=1，均值=1
    assert tc.flicker_index([0.0, 1.0, 0.0, 1.0]) == 1.0


def test_tci_range():
    assert tc.temporal_consistency_index([0.5, 0.5, 0.5]) == 1.0  # 无闪=1
    assert tc.temporal_consistency_index([0.0, 1.0]) == 0.5       # flicker=1 → 1/2
    assert 0.0 < tc.temporal_consistency_index([0.0, 0.2, 0.0]) <= 1.0


def test_min_consecutive_cosine():
    a = [1.0, 0.0]; b = [1.0, 0.0]; c = [0.0, 1.0]
    # 相邻对: (a,b)=1.0, (b,c)=0.0 → min=0.0
    assert abs(tc.min_consecutive_cosine([a, b, c]) - 0.0) < 1e-9
    assert tc.min_consecutive_cosine([a]) is None
    assert abs(tc.min_consecutive_cosine([a, b]) - 1.0) < 1e-9


def test_verdict_identity_and_flicker():
    # 身份稳 + 不闪 → ok
    assert tc.verdict(0.9, 0.0, id_floor=0.6, flicker_max=0.06) == "ok"
    # 身份轻漂(0.55<0.6 但 ≥0.5) → warn
    assert tc.verdict(0.55, 0.0, id_floor=0.6, flicker_max=0.06) == "warn"
    # 身份重漂(<0.5) → block
    assert tc.verdict(0.45, 0.0, id_floor=0.6, flicker_max=0.06) == "block"
    # 闪烁超 1.5x → block
    assert tc.verdict(0.9, 0.10, id_floor=0.6, flicker_max=0.06) == "block"
    # 闪烁轻超 → warn
    assert tc.verdict(0.9, 0.07, id_floor=0.6, flicker_max=0.06) == "warn"
    # 无脸数据(None)但闪烁ok → ok
    assert tc.verdict(None, 0.0, id_floor=0.6, flicker_max=0.06) == "ok"


def test_shot_num_parses_both_namings():
    import temporal_consistency as t
    assert t._shot_num("镜头7_小禾冲入.png") == 7
    assert t._shot_num("镜头6A_end.png") == 6
    assert t._shot_num("Clip_12.png") == 12
    assert t._shot_num("封面.png") is None
