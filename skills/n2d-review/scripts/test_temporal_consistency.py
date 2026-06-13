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


# ── 接缝色彩量化指标（#5 扩展）单测 ──

def test_hist_cosine_distance_identical_is_zero():
    h = [0.1, 0.2, 0.3, 0.4]
    assert abs(tc.hist_cosine_distance(h, h)) < 1e-9


def test_hist_cosine_distance_orthogonal_is_one():
    assert abs(tc.hist_cosine_distance([1.0, 0.0], [0.0, 1.0]) - 1.0) < 1e-9


def test_hist_cosine_distance_guards():
    assert tc.hist_cosine_distance([], [1.0]) is None        # 维度不等
    assert tc.hist_cosine_distance([0.0, 0.0], [1.0, 1.0]) is None  # 全零


def test_color_verdict_bands():
    assert tc.color_verdict(0.05) == "ok"
    assert tc.color_verdict(0.20) == "warn"     # > SEAM_COLOR_WARN
    assert tc.color_verdict(0.40) == "block"    # > SEAM_COLOR_BLOCK
    assert tc.color_verdict(None) == "ok"        # 缺图不臆造


def test_face_seam_verdict_bands():
    assert tc.face_seam_verdict(0.90) == "ok"     # 高余弦=同人同表情区间
    assert tc.face_seam_verdict(0.45) == "warn"   # < SEAM_FACE_WARN_COS(0.50) 脸偏
    assert tc.face_seam_verdict(0.30) == "block"  # < SEAM_FACE_BLOCK_COS(0.35) 基本另一张脸
    assert tc.face_seam_verdict(None) is None      # 缺 insightface / 无脸 → 不臆造，交人判
    assert tc.face_seam_verdict(0.60, warn_cos=0.70, block_cos=0.50) == "warn"  # 阈值可调


def test_worse_takes_higher_severity():
    assert tc._worse("ok", "warn") == "warn"
    assert tc._worse("warn", "block") == "block"
    assert tc._worse("block", "ok") == "block"


# ── 接缝阈值自标定（本集分布离群上界）单测 ──

def test_seam_relative_floor_needs_enough_samples():
    assert tc.seam_relative_floor([10, 12, 11]) is None          # < min_count
    assert tc.seam_relative_floor([]) is None
    assert tc.seam_relative_floor([10, None, 12, None]) is None  # None 不算样本


def test_seam_relative_floor_median_plus_mad():
    # med=11, MAD=1 → floor = 11 + max(3×1, 4) = 15；离群 40 > 15
    floor = tc.seam_relative_floor([10, 10, 12, 11, 40])
    assert floor == 15.0


def test_seam_relative_floor_all_equal_uses_min_margin():
    # MAD=0 → min_margin 保底，避免全相同分布零容忍
    assert tc.seam_relative_floor([10, 10, 10, 10]) == 14.0


def test_apply_relative_outlier_only_tightens():
    assert tc.apply_relative_outlier("ok", 40, 15.0) == "warn"    # 收紧
    assert tc.apply_relative_outlier("ok", 10, 15.0) == "ok"      # 分布内
    assert tc.apply_relative_outlier("block", 40, 15.0) == "block"  # 从不降级
    assert tc.apply_relative_outlier("warn", 40, 15.0) == "warn"
    assert tc.apply_relative_outlier("ok", 40, None) == "ok"      # 未标定不动


# ── 光位签名诚实降级（不假报 ok）单测 ──

def test_lighting_signature_is_skipped_not_ok():
    assert tc.analyze_lighting_signature("x.png", {"any": "sig"}) == "skipped"


def test_count_lighting_signatures():
    reg = {"assets": [
        {"id": "LOC_01", "constraints": {"lighting_signature": "画左暖光"}},
        {"id": "PROP_01", "constraints": {}},
        "not-a-dict",
    ]}
    assert tc.count_lighting_signatures(reg) == 1
    assert tc.count_lighting_signatures(None) == 0
    assert tc.count_lighting_signatures({}) == 0


# ── 单对接缝机检（需 Pillow，本机有；缺则跳过） ──

def test_seam_pair_check_same_and_color_jump(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image")
    red = tmp_path / "镜头1_end.png"
    red2 = tmp_path / "镜头2.png"
    blue = tmp_path / "镜头3.png"
    Image.new("RGB", (64, 64), (200, 30, 30)).save(red)
    Image.new("RGB", (64, 64), (200, 30, 30)).save(red2)
    Image.new("RGB", (64, 64), (30, 30, 200)).save(blue)
    same = tc.seam_pair_check(str(red), str(red2))
    assert same is not None and same["verdict"] == "ok" and same["dist"] <= tc.SEAM_WARN
    jump = tc.seam_pair_check(str(red), str(blue))
    # 纯色图 dHash（灰度结构）几乎不变，但色彩通道必须抓住红→蓝的剪辑点闪光
    assert jump is not None and jump["color_verdict"] in ("warn", "block")
    assert jump["verdict"] in ("warn", "block")


# ── 接缝意图真值源（storyboard 唯一真值）单测 ──

def test_seam_strictness_canonical():
    assert tc.seam_strictness(None) == "strict"
    assert tc.seam_strictness({"transition": "match_cut"}) == "info"
    assert tc.seam_strictness({"transition": "relay"}) == "strict"
    assert tc.seam_strictness({"transition": "match_cut", "relay": True}) == "strict"
    assert tc.seam_strictness({"transition": ""}) == "strict"


def test_load_seam_intents_parses_storyboard(tmp_path):
    import json, os
    d = tmp_path / "脚本" / "第1集"
    d.mkdir(parents=True)
    (d / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP01_CLIP01", "continuity": {"transition": "match_cut"}},
        {"id": "EP01_CLIP02", "need_end_frame": True, "continuity": {"transition": "接力"}},
        "junk",
    ]}), encoding="utf-8")
    intents = tc.load_seam_intents(str(tmp_path), "第1集")
    assert intents[1]["transition"] == "match_cut" and not intents[1]["relay"]
    assert intents[2]["relay"] is True
    assert tc.load_seam_intents(str(tmp_path), "第99集") == {}


def test_seam_analyze_reports_truth_source_contradiction(tmp_path):
    import json
    import pytest
    Image = pytest.importorskip("PIL.Image")
    pics = tmp_path / "出图" / "第1集" / "图片"
    pics.mkdir(parents=True)
    # 镜头1 有接力尾帧 _end.png，但 storyboard 声明 match_cut → 矛盾 + dHash 降 info
    Image.new("RGB", (64, 64), (200, 30, 30)).save(pics / "镜头1_end.png")
    Image.new("RGB", (64, 64), (30, 30, 200)).save(pics / "镜头2_首帧.png")
    sb = tmp_path / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP01_CLIP01", "continuity": {"transition": "match_cut"}},
        {"id": "EP01_CLIP02", "continuity": {"transition": "hard_cut"}},
    ]}), encoding="utf-8")
    res = tc.seam_analyze(str(tmp_path), "第1集")
    assert len(res["contradictions"]) == 1 and res["contradictions"][0]["shot"] == 1
    assert all(s["verdict"] == "info" for s in res["seams"])  # storyboard 为准，不 block

    # 改成声明接力 → 无矛盾，红蓝色跳必须升 warn/block
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP01_CLIP01", "need_end_frame": True},
        {"id": "EP01_CLIP02"},
    ]}), encoding="utf-8")
    res2 = tc.seam_analyze(str(tmp_path), "第1集")
    assert res2["contradictions"] == []
    assert any(s["verdict"] in ("warn", "block") for s in res2["seams"])
