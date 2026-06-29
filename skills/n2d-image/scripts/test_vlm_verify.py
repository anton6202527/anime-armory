"""vlm_verify 单测——verdict 解析 + 严重度判定 + canonical 构造 + 注入 stub judge 的 evaluate_pairs。

cd skills/n2d-image/scripts && python3 -m pytest test_vlm_verify.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("vlm_verify.py")
spec = importlib.util.spec_from_file_location("vlm_verify", SCRIPT)
vv = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(vv)


def test_parse_verdict_json_and_fence():
    v = vv.parse_verdict('{"match": false, "confidence": 0.8, "mismatches": ["缺左腕疤"], "reason": "x"}')
    assert v["match"] is False and v["confidence"] == 0.8 and v["mismatches"] == ["缺左腕疤"]
    # ```json fence``` + 前后噪声容忍
    fenced = vv.parse_verdict('好的：```json\n{"match": true, "confidence": 1.2}\n``` 完毕')
    assert fenced["match"] is True
    assert fenced["confidence"] == 1.0  # clamp 到 [0,1]


def test_parse_verdict_guards():
    assert vv.parse_verdict("not json") is None
    assert vv.parse_verdict('{"confidence": 0.5}') is None  # 缺 match
    assert vv.parse_verdict(None) is None
    assert vv.parse_verdict({"match": True}) == {"match": True, "confidence": 0.0, "mismatches": [], "reason": ""}


def test_verdict_finding_severity():
    # 关键 × 不符 × 高置信 → block
    f = vv.verdict_finding("沈念", "character", "图片/x.png",
                           {"match": False, "confidence": 0.7, "mismatches": ["窄袖→交领"], "reason": ""},
                           is_key=True, block_floor=0.6)
    assert f["level"] == "block" and f["code"] == "vlm_semantic_mismatch"
    # 关键 × 不符 × 低置信 → warn
    f2 = vv.verdict_finding("沈念", "character", "图片/x.png",
                            {"match": False, "confidence": 0.4, "mismatches": ["x"]},
                            is_key=True, block_floor=0.6)
    assert f2["level"] == "warn" and f2["code"] == "vlm_semantic_review"
    # 非关键 × 不符 × 高置信 → warn（不 block 非关键）
    f3 = vv.verdict_finding("路人", "asset", "图片/x.png",
                            {"match": False, "confidence": 0.9}, is_key=False, block_floor=0.6)
    assert f3["level"] == "warn"
    # 吻合 / None → 不加噪
    assert vv.verdict_finding("沈念", "character", "p", {"match": True, "confidence": 0.9}, True) is None
    assert vv.verdict_finding("沈念", "character", "p", None, True) is None


def test_canonical_builders():
    ch = {"name": "沈念"}
    form = {"character_dna": {"face": "凤眼薄唇", "accessories": "左腕旧疤是核心识别点"},
            "anchor_phrase": "月白粗布旧宫装"}
    c = vv.canonical_from_character(ch, form)
    assert "凤眼薄唇" in c and "左腕旧疤" in c and "anchor: 月白粗布旧宫装" in c
    asset = {"name": "冷宫寝殿", "scene_dna": {"landmarks": ["破败木榻", "旧铜镜"]}}
    a = vv.canonical_from_asset(asset)
    assert "冷宫寝殿" in a and "破败木榻" in a


def test_resolve_canonical_exact_and_substring():
    cmap = {"沈念": {"kind": "character", "canonical": "C"}, "冷宫寝殿": {"kind": "asset", "canonical": "A"}}
    assert vv.resolve_canonical("沈念", cmap)["canonical"] == "C"
    assert vv.resolve_canonical("沈念（常态）", cmap)["canonical"] == "C"  # hint 含 key
    assert vv.resolve_canonical("查无此人", cmap) is None


def test_evaluate_pairs_end_to_end_with_stub_judge():
    cmap = {
        "沈念": {"kind": "character", "canonical": "凤眼薄唇；左腕旧疤"},
        "冷宫寝殿": {"kind": "asset", "canonical": "破败木榻；旧铜镜"},
    }
    pairs = [
        {"name": "沈念", "png": "图片/c01.png"},
        {"name": "冷宫寝殿", "png": "图片/loc01.png"},
        {"name": "无设定", "png": "图片/x.png"},  # resolve 不到 → 跳过
    ]

    def judge(abspath, canonical, kind):
        if "左腕旧疤" in canonical:  # 角色沈念：判崩设定
            return {"match": False, "confidence": 0.85, "mismatches": ["缺左腕疤"], "reason": "疤丢了"}
        return {"match": True, "confidence": 0.95}

    res = vv.evaluate_pairs(pairs, cmap, judge, shot_abspath=lambda r: "/abs/" + r, block_floor=0.6)
    assert res["available"] is True
    assert res["judged"] == 2  # 两个能 resolve 的都判了
    assert res["block"] == 1
    assert any(f["level"] == "block" and "沈念" in f["msg"] for f in res["findings"])


def test_analyze_skips_without_backend(tmp_path):
    # 无 judge（且无 N2D_VLM_CMD）→ available=False，不阻断
    res = vv.analyze(tmp_path, "第1集", {"checks": {}}, judge=None)
    # load_judge 在无 env 时返回 None
    if res["available"]:
        # 若运行环境恰好配了 N2D_VLM_CMD，至少不应崩
        assert "findings" in res
    else:
        assert res["judged"] == 0 and res["findings"] == []


def test_load_judge_auto_mlxvlm_template(monkeypatch):
    monkeypatch.delenv("N2D_VLM_CMD", raising=False)
    monkeypatch.setattr(vv, "_n2dvlm_env_exists", lambda: True)
    cmd = vv._auto_vlm_cmd()
    assert "vlm_cmd_mlxvlm.py" in cmd
    assert "--image {image}" in cmd
    assert "--prompt {prompt}" in cmd
    assert vv.load_judge() is not None


def test_load_judge_can_disable_auto(monkeypatch):
    monkeypatch.setenv("N2D_VLM_CMD", "off")
    monkeypatch.setattr(vv, "_n2dvlm_env_exists", lambda: True)
    assert vv.load_judge() is None


def test_pairs_from_payload_dedup():
    payload = {"checks": {
        "face": {"shots": [{"name": "沈念", "png": "p1.png"}]},
        "outfit": {"shots": [{"char": "沈念", "png": "p1.png"}]},  # 同 (name,png) → 去重
        "scene": {"shots": [{"scene": "冷宫寝殿", "png": "p2.png"}]},
    }}
    pairs = vv._pairs_from_payload(payload)
    keys = {(p["name"], p["png"]) for p in pairs}
    assert ("沈念", "p1.png") in keys and ("冷宫寝殿", "p2.png") in keys
    assert len(pairs) == 2


def test_merge_shot_canonical_any_fail_wins():
    # 一镜判多个资产：任一不符 → 整镜 canonical_pass=False（fidelity-gate 取最严）
    mask = {}
    vv.merge_shot_canonical(mask, "镜头03.png", True, 0.90)
    vv.merge_shot_canonical(mask, "镜头03.png", False, 0.70)
    assert mask["镜头03.png"]["canonical_pass"] is False
    assert mask["镜头03.png"]["confidence"] == 0.9  # 置信取最大


def test_merge_shot_canonical_all_pass():
    mask = {}
    vv.merge_shot_canonical(mask, "a.png", True, 0.8)
    vv.merge_shot_canonical(mask, "a.png", True, 0.6)
    assert mask["a.png"]["canonical_pass"] is True


def test_merge_shot_canonical_ignores_blank_png():
    mask = {}
    vv.merge_shot_canonical(mask, "", True, 0.9)
    assert mask == {}


def test_verdict_finding_carries_structured_png():
    # G3：finding 带结构化 png/name/confidence，供 canonical 通过表无歧义消费（不靠正则抠 msg）
    verdict = {"match": False, "confidence": 0.9, "mismatches": ["发色错"], "reason": ""}
    fnd = vv.verdict_finding("沈念", "character", "镜头01.png", verdict, is_key=True, block_floor=0.6)
    assert fnd["level"] == "block"
    assert fnd["png"] == "镜头01.png" and fnd["name"] == "沈念" and fnd["confidence"] == 0.9


def test_vote_disagreement_formula():
    # <3 票不算分歧
    assert vv.vote_disagreement([{"match": True}, {"match": False}]) == 0.0
    # 3 票全一致 → 0
    assert vv.vote_disagreement([{"match": False}] * 3) == 0.0
    # 3 票 2:1 → 1 - 2/3
    assert abs(vv.vote_disagreement([{"match": False}, {"match": False}, {"match": True}]) - (1 - 2 / 3)) < 1e-9


def test_aggregate_votes_majority_and_union():
    # 单票原样返回（votes=1 零行为变化，无 vote_disagreement 键）
    one = vv.aggregate_votes([{"match": False, "confidence": 0.8, "mismatches": ["a"], "reason": "r"}])
    assert one["match"] is False and "vote_disagreement" not in one
    # 全失败 → None
    assert vv.aggregate_votes([None, None]) is None
    # 多数 match=False，mismatches 取并集，分歧度留痕
    agg = vv.aggregate_votes([
        {"match": False, "confidence": 0.9, "mismatches": ["缺疤"], "reason": "x"},
        {"match": False, "confidence": 0.7, "mismatches": ["发色"], "reason": ""},
        {"match": True, "confidence": 0.5, "mismatches": []},
    ])
    assert agg["match"] is False
    assert set(agg["mismatches"]) == {"缺疤", "发色"}
    assert agg["n_votes"] == 3 and agg["vote_disagreement"] == round(1 - 2 / 3, 3)
    assert abs(agg["confidence"] - 0.8) < 1e-9  # 仅多数侧(0.9,0.7)均值


def test_judge_verdict_votes_aggregation():
    calls = {"n": 0}

    def flaky_judge(_a, _c, _k):
        calls["n"] += 1
        # 第1次判过，后两次判崩 → 多数 match=False
        return {"match": True, "confidence": 0.6} if calls["n"] == 1 else {
            "match": False, "confidence": 0.9, "mismatches": ["发色"]}

    agg = vv.judge_verdict(flaky_judge, "/abs/x.png", "黑长直、红衣", "character", votes=3)
    assert calls["n"] == 3 and agg["match"] is False and agg["n_votes"] == 3


def test_verdict_finding_high_disagreement_downgrades_block_to_warn():
    # 高置信本应 block，但投票分歧≥floor → 降级 warn 人判（不硬挡）
    verdict = {"match": False, "confidence": 0.9, "mismatches": ["x"], "vote_disagreement": 0.5}
    fnd = vv.verdict_finding("沈念", "character", "p.png", verdict, is_key=True,
                             block_floor=0.6, vote_disagree_floor=0.34)
    assert fnd["level"] == "warn" and fnd["code"] == "vlm_semantic_review"
    assert fnd["vote_disagreement"] == 0.5 and "分歧" in fnd["msg"]
    # 分歧低 → 仍 block
    verdict2 = {"match": False, "confidence": 0.9, "mismatches": ["x"], "vote_disagreement": 0.0}
    fnd2 = vv.verdict_finding("沈念", "character", "p.png", verdict2, is_key=True,
                              block_floor=0.6, vote_disagree_floor=0.34)
    assert fnd2["level"] == "block"


def test_evaluate_pairs_emits_shot_canonical():
    canon = {"沈念": {"kind": "character", "canonical": "黑长直、红衣"}}

    def judge(_abspath, _canon, _kind):
        return {"match": False, "confidence": 0.9, "mismatches": ["发色"], "reason": ""}

    pairs = [{"name": "沈念", "png": "镜头01.png"}]
    res = vv.evaluate_pairs(pairs, canon, judge, lambda r: "/abs/" + r, block_floor=0.6)
    assert res["shot_canonical"]["镜头01.png"]["canonical_pass"] is False
