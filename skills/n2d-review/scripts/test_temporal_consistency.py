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


def test_identity_precision_verdict_flags_closeup_without_embedding():
    assert tc.identity_precision_verdict(closeup=True, min_id=None) == "warn"
    assert tc.identity_precision_verdict(closeup=True, min_id=0.8) == "ok"
    assert tc.identity_precision_verdict(closeup=False, min_id=None) == "ok"


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


# ── 接缝意图真值源（P-3 chain 优先，storyboard legacy fallback）单测 ──

def test_seam_strictness_canonical():
    assert tc.seam_strictness(None) == "strict"
    assert tc.seam_strictness({"seam_mode": "match_on_action"}) == "info"
    assert tc.seam_strictness({"seam_mode": "continuous_take_relay"}) == "strict"
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
        {"id": "EP01_CLIP03", "continuity": {"transition": "hard_cut", "need_endframe": True}},
        {"id": "EP01_CLIP04", "continuity": {"need_endframe": True}},
        "junk",
    ]}), encoding="utf-8")
    intents = tc.load_seam_intents(str(tmp_path), "第1集")
    assert intents[1]["transition"] == "match_cut" and not intents[1]["relay"]
    assert intents[2]["relay"] is True
    assert intents[3]["transition"] == "hard_cut" and not intents[3]["relay"]
    assert intents[4]["transition"] is None and intents[4]["relay"] is True
    assert tc.load_seam_intents(str(tmp_path), "第99集") == {}


def test_anchor_png_names_are_not_first_frames():
    assert tc._is_anchor_png_name("Clip_02_左腕旧疤_mid.png") is True
    assert tc._is_anchor_png_name("Clip_02_左腕旧疤_a1.png") is True
    assert tc._is_anchor_png_name("Clip_02_左腕旧疤.png") is False
    assert tc._is_anchor_png_name("Clip_02_end.png") is False


def test_seam_analyze_does_not_treat_nonrelay_endframe_as_contradiction(tmp_path):
    import json
    import pytest
    Image = pytest.importorskip("PIL.Image")
    pics = tmp_path / "出图" / "第1集" / "图片"
    pics.mkdir(parents=True)
    # 非 relay 仍可有 end frame 作为本镜落幅参考；跨帧差异只降 info，不构成矛盾。
    Image.new("RGB", (64, 64), (200, 30, 30)).save(pics / "镜头1_end.png")
    Image.new("RGB", (64, 64), (30, 30, 200)).save(pics / "镜头2_首帧.png")
    sb = tmp_path / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP01_CLIP01", "continuity": {"transition": "match_cut"}},
        {"id": "EP01_CLIP02", "continuity": {"transition": "hard_cut"}},
    ]}), encoding="utf-8")
    res = tc.seam_analyze(str(tmp_path), "第1集")
    assert res["contradictions"] == []
    assert all(s["verdict"] == "info" for s in res["seams"])  # storyboard 为准，不 block

    # 改成声明接力 → 无矛盾，红蓝色跳必须升 warn/block
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP01_CLIP01", "need_end_frame": True},
        {"id": "EP01_CLIP02"},
    ]}), encoding="utf-8")
    res2 = tc.seam_analyze(str(tmp_path), "第1集")
    assert res2["contradictions"] == []
    assert any(s["verdict"] in ("warn", "block") for s in res2["seams"])


def test_load_seam_intents_prefers_p3_chain(tmp_path):
    import json

    d = tmp_path / "脚本" / "第1集"
    d.mkdir(parents=True)
    (d / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_01", "continuity": {"transition": "relay", "need_endframe": True}},
    ]}), encoding="utf-8")
    (d / "continuity_chain.json").write_text(json.dumps({"seams": [{
        "scope": "intra_episode", "from_episode": "第1集", "from_clip": "Clip_01",
        "to_clip": "Clip_02", "transition": "视线切", "seam_mode": "eyeline_cut",
        "seam_evidence": {"eyeline_source": "A", "eyeline_target": "门", "axis": "A-B"},
    }]}), encoding="utf-8")

    intents = tc.load_seam_intents(str(tmp_path), "第1集")

    assert intents[1]["source"] == "continuity_chain"
    assert intents[1]["seam_mode"] == "eyeline_cut"
    assert intents[1]["relay"] is False


def test_adaptive_frame_count_floor_and_density():
    # 无时长 → floor
    assert tc.adaptive_frame_count(None) == tc.DEFAULT_FRAMES
    assert tc.adaptive_frame_count(0) == tc.DEFAULT_FRAMES
    # 短镜（3s）不低于 floor
    assert tc.adaptive_frame_count(3.0) == tc.DEFAULT_FRAMES
    # 长镜 ≈1帧/秒
    assert tc.adaptive_frame_count(15.0) == 15
    # 近景加密 ×1.5
    assert tc.adaptive_frame_count(10.0, closeup=True) == 15
    assert tc.adaptive_frame_count(10.0, closeup=False) == 10
    # cap 封顶
    assert tc.adaptive_frame_count(120.0) == tc.SAMPLE_CAP
    assert tc.adaptive_frame_count(120.0, closeup=True) == tc.SAMPLE_CAP


def test_is_closeup_lens_markers():
    assert tc._is_closeup_lens("CU 50mm 缓推") is True
    assert tc._is_closeup_lens("特写反打") is True
    assert tc._is_closeup_lens("WS 远景") is False
    assert tc._is_closeup_lens("") is False


# ---- 跨镜动作接力 match-on-action（T6·边缘质心位移）----

def test_weighted_centroid_uniform_is_center():
    # 2x2 全等权 → 质心居中 (0.5,0.5)
    c = tc.weighted_centroid([1, 1, 1, 1], cols=2)
    assert c is not None and abs(c[0] - 0.5) < 1e-9 and abs(c[1] - 0.5) < 1e-9


def test_weighted_centroid_corner_mass():
    # 全部质量在左上角 (0,0) → 归一质心 (0,0)
    c = tc.weighted_centroid([5, 0, 0, 0], cols=2)
    assert c == (0.0, 0.0)
    # 全部质量在右下角 → (1,1)
    c2 = tc.weighted_centroid([0, 0, 0, 7], cols=2)
    assert abs(c2[0] - 1.0) < 1e-9 and abs(c2[1] - 1.0) < 1e-9


def test_weighted_centroid_guards():
    assert tc.weighted_centroid([0, 0, 0, 0], cols=2) is None   # 总权重 0
    assert tc.weighted_centroid([1, 2, 3], cols=2) is None       # 长度非整数倍
    assert tc.weighted_centroid([1, 1], cols=0) is None          # cols<=0


def test_centroid_shift():
    assert tc.centroid_shift((0.0, 0.0), (0.0, 0.0)) == 0.0
    assert abs(tc.centroid_shift((0.0, 0.0), (0.3, 0.4)) - 0.5) < 1e-9
    assert tc.centroid_shift(None, (0.1, 0.1)) is None
    assert tc.centroid_shift((0.1, 0.1), None) is None


def test_action_match_verdict_bands():
    assert tc.action_match_verdict(0.05) == "ok"
    assert tc.action_match_verdict(0.20) == "warn"     # > WARN(0.16), <= BLOCK(0.30)
    assert tc.action_match_verdict(0.40) == "block"    # > BLOCK
    assert tc.action_match_verdict(None) is None       # 算不出 → 不臆造


def test_action_match_verdict_custom_thresholds():
    assert tc.action_match_verdict(0.1, warn=0.05, block=0.2) == "warn"
    assert tc.action_match_verdict(0.25, warn=0.05, block=0.2) == "block"


# ── 掣肘二：高动作/大表情跨度镜的片内时序 BLOCK 降级（度量偏好静止的反制）──

def test_relax_temporal_verdict_downgrades_block_only():
    assert tc.relax_temporal_verdict("block", True) == "warn"   # 高动作镜：block→warn
    assert tc.relax_temporal_verdict("block", False) == "block" # 普通镜：不放松
    assert tc.relax_temporal_verdict("warn", True) == "warn"    # warn 不动
    assert tc.relax_temporal_verdict("ok", True) == "ok"        # ok 不动


def test_is_large_expression_span():
    assert tc._is_large_expression_span({"continuity": {"expression_span": "大"}})
    assert tc._is_large_expression_span({"expression_span": "large"})
    assert not tc._is_large_expression_span({"expression_span": "小"})
    assert not tc._is_large_expression_span({})


def test_motion_relax_map_from_storyboard(tmp_path):
    import json, os
    sb = {"clips": [
        {"id": "Clip_01", "continuity": {"expression_span": "大"}, "shots": []},
        {"id": "Clip_02", "shots": [{"desc": "他挥拳猛击对手面门"}]},
        {"id": "Clip_03", "shots": [{"desc": "两人静静对视"}]},
    ]}
    d = tmp_path / "脚本" / "第1集"
    d.mkdir(parents=True)
    (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    m = tc.motion_relax_map(str(tmp_path), "第1集")
    assert 1 in m and "大表情跨度" in m[1]
    # Clip_02 命中动作 beat（需 _spec 可用）；静态 Clip_03 不应放松
    assert 3 not in m
