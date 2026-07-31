#!/usr/bin/env python3
"""cd skills/n2d/n2d-review/scripts && python3 -m pytest test_scene_embed.py

场景语义嵌入(DINOv2) SCNX 升级——纯逻辑（均值 + cosine 跨集漂移 + 优雅降级）。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_embed as se


def test_mean_embedding_basic():
    assert se.mean_embedding([[1, 2], [3, 4]]) == [2.0, 3.0]
    assert se.mean_embedding([]) == []
    assert se.mean_embedding([[1, 0]]) == [1.0, 0.0]


def test_mean_embedding_skips_dim_mismatch():
    # 维度不一的条目被跳过（以首条维度为准）
    assert se.mean_embedding([[1, 1], [9, 9, 9], [3, 3]]) == [2.0, 2.0]


def test_drift_stable_scene_no_rows():
    means = {"第1集": {"殿": [1.0, 0.0]}, "第2集": {"殿": [1.0, 0.0]}}
    assert se.scene_embed_drift_rows(means, "第2集") == []


def test_drift_non_core_warns():
    means = {"第1集": {"殿": [1.0, 0.0, 0.0]}, "第2集": {"殿": [0.0, 1.0, 0.0]}}
    rows = se.scene_embed_drift_rows(means, "第2集")
    assert len(rows) == 1 and rows[0]["verdict"] == "warn"
    assert rows[0]["evidence"] == "embedding" and "语义嵌入漂移" in rows[0]["msg"]


def test_drift_core_scene_blocks():
    means = {"第1集": {"殿": [1.0, 0.0, 0.0]}, "第2集": {"殿": [1.0, 0.0, 0.0]},
             "第3集": {"殿": [0.0, 1.0, 0.0]}}
    rows = se.scene_embed_drift_rows(means, "第3集", core_scenes=["殿"])
    assert rows and rows[0]["verdict"] == "block" and "跨3集语义" in rows[0]["shot"]


def test_drift_first_episode_no_prior():
    assert se.scene_embed_drift_rows({"第1集": {"殿": [1.0, 0.0]}}, "第1集") == []


def test_scene_embed_means_degrades_without_sidecar(tmp_path):
    assert se.scene_embed_means(str(tmp_path), "第1集") == {}


def test_scene_embed_means_groups_by_scene(tmp_path):
    # 后端回填后的 sidecar → 按场景取均值
    prod = tmp_path / "生产数据"
    prod.mkdir()
    payload = {"kind": se.SCENE_EMBED_KIND, "probes": [
        {"shot": "a.png", "scene": "殿", "embedding": [1.0, 0.0]},
        {"shot": "b.png", "scene": "殿", "embedding": [3.0, 0.0]},
        {"shot": "c.png", "scene": "厅", "embedding": [0.0, 2.0]},
        {"shot": "d.png", "scene": "厅", "embedding": None},  # 未回填 → 跳过
    ]}
    (prod / "scene_embed_第1集.json").write_text(json.dumps(payload), encoding="utf-8")
    means = se.scene_embed_means(str(tmp_path), "第1集")
    assert means == {"殿": [2.0, 0.0], "厅": [0.0, 2.0]}


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
