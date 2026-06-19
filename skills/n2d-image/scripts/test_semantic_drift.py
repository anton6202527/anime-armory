"""semantic_drift 单测——cosine + 调色板×语义判定 + 注入 stub embedder 的端到端 evaluate_pairs。

cd skills/n2d-image/scripts && python3 -m pytest test_semantic_drift.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("semantic_drift.py")
spec = importlib.util.spec_from_file_location("semantic_drift", SCRIPT)
sd = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(sd)


def test_cosine_basic_and_guards():
    assert sd.cosine([1, 0], [1, 0]) == 1.0
    assert abs(sd.cosine([1, 0], [0, 1])) < 1e-9
    assert sd.cosine([1, 0], [-1, 0]) == -1.0
    # 守卫：空/零向量/长度不等 → None
    assert sd.cosine([], [1]) is None
    assert sd.cosine([0, 0], [1, 1]) is None
    assert sd.cosine([1, 2, 3], [1, 2]) is None


def test_semantic_finding_truth_table():
    floor = 0.55
    # palette 未报 + 语义低 → warn（palette 漏掉的结构漂）
    f = sd.semantic_finding("ok", 0.3, floor)
    assert f and f["level"] == "warn" and f["code"] == "semantic_drift_low"
    assert sd.semantic_finding(None, 0.3, floor)["code"] == "semantic_drift_low"
    # palette 报了 + 语义高 → info（疑似只灯光/天气）
    g = sd.semantic_finding("warn", 0.9, floor)
    assert g and g["level"] == "info" and g["code"] == "semantic_drift_lighting"
    assert sd.semantic_finding("block", 0.8, floor)["code"] == "semantic_drift_lighting"
    # 两者一致 → None（不加噪）
    assert sd.semantic_finding("ok", 0.9, floor) is None      # 都说没漂
    assert sd.semantic_finding("block", 0.2, floor) is None    # 都说漂了
    # cos=None（嵌入失败）→ None
    assert sd.semantic_finding("ok", None, floor) is None


def test_pairs_from_payload_pulls_all_shots():
    payload = {"checks": {
        "scene": {"shots": [{"png": "图片/Clip_01.png", "scene": "LOC_01", "verdict": "ok"}]},
        "multimodal": {"shots": [{"png": "图片/Clip_02.png", "asset": "PROP_01", "verdict": "warn"}]},
    }}
    pairs = sd._pairs_from_payload(payload)
    assert {p["kind"] for p in pairs} == {"scene", "asset"}
    assert any(p["palette_verdict"] == "ok" for p in pairs)   # 全镜，不止 block/warn


def test_model_download_is_opt_in(monkeypatch):
    monkeypatch.delenv("N2D_ALLOW_MODEL_DOWNLOAD", raising=False)
    assert sd.allow_model_download() is False
    monkeypatch.setenv("N2D_ALLOW_MODEL_DOWNLOAD", "1")
    assert sd.allow_model_download() is True


def test_evaluate_pairs_flags_palette_missed_drift():
    # 同色场景：参考与本镜结构不同 → 语义低，但 palette 说 ok → 应 warn semantic_drift_low
    vecs = {
        "ref/LOC_01.png": [1.0, 0.0, 0.0],
        "abs/图片/Clip_01.png": [0.0, 1.0, 0.0],   # 与参考正交 → cosine 0 < floor
        "ref/LOC_02.png": [1.0, 0.0, 0.0],
        "abs/图片/Clip_02.png": [0.99, 0.01, 0.0],  # 与参考几乎同向 → cosine≈1 ≥ floor
    }
    pairs = [
        {"kind": "scene", "asset": "LOC_01", "png": "图片/Clip_01.png", "palette_verdict": "ok"},
        {"kind": "scene", "asset": "LOC_02", "png": "图片/Clip_02.png", "palette_verdict": "block"},
    ]
    res = sd.evaluate_pairs(
        pairs,
        embed=lambda p: vecs.get(p),
        resolve_ref=lambda hint: f"ref/{hint}.png",
        shot_abspath=lambda rel: f"abs/{rel}",
    )
    assert res["available"] and res["compared"] == 2
    codes = {f["code"] for f in res["findings"]}
    # Clip_01：palette ok 但语义低 → semantic_drift_low
    assert "semantic_drift_low" in codes
    # Clip_02：palette block 但语义高 → semantic_drift_lighting（降噪）
    assert "semantic_drift_lighting" in codes


def test_analyze_degrades_without_embedder(tmp_path):
    # 无嵌入后端注入且自动加载失败时 → available False、跳过、不抛
    res = sd.analyze(tmp_path, "第1集", {"checks": {}}, embedder=None)
    # load_embedder 在无 torch 的系统 Python 上返回 None → available False
    if not res["available"]:
        assert res["compared"] == 0 and res["findings"] == []
