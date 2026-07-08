#!/usr/bin/env python3
"""cd skills/n2d-review/scripts && python3 -m pytest test_resident_presence.py

场景常驻陈设在场检测——纯逻辑（提取 + 场景级聚合）。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resident_presence as rp


REG = {
    "LOC_A": {"id": "LOC_A", "name": "破殿", "scene_dna": {"resident_assets": ["残匾", "碎梁"]}},
    "LOC_B": {"id": "LOC_B", "scene_dna": {"resident_assets": []}},        # 空 → 不收
    "LOC_C": {"id": "LOC_C", "scene_dna": {}},                              # 无字段 → 不收
    "PROP_X": {"id": "PROP_X", "scene_dna": {"resident_assets": ["x"]}},   # 非 LOC → 不收
}


def test_scene_resident_assets_only_nonempty_loc():
    assert rp.scene_resident_assets(REG) == {
        "LOC_A": [{"asset": "残匾", "phrase": "残匾"}, {"asset": "碎梁", "phrase": "碎梁"}]
    }


def test_scene_resident_assets_keeps_detect_phrase():
    reg = {"LOC_A": {"id": "LOC_A", "scene_dna": {"resident_assets": [
        {"asset": "残匾", "detect_phrase": "破损木匾"},
    ]}}}
    assert rp.scene_resident_assets(reg) == {"LOC_A": [{"asset": "残匾", "phrase": "破损木匾"}]}


def test_scene_resident_assets_empty_registry():
    assert rp.scene_resident_assets({}) == {}


def _manifest():
    return {"probes": [
        {"scene": "破殿", "shot": "s1.png", "expected_assets": [{"asset": "残匾"}, {"asset": "碎梁"}]},
        {"scene": "破殿", "shot": "s2.png", "expected_assets": [{"asset": "残匾"}, {"asset": "碎梁"}]},
    ], "findings": []}


def test_aggregate_flags_asset_absent_in_all_shots():
    m = _manifest()
    m["findings"] = [
        {"shot": "s1.png", "asset": "残匾", "present": False},
        {"shot": "s2.png", "asset": "残匾", "present": False},
        {"shot": "s1.png", "asset": "碎梁", "present": False},  # 仅 s1 缺 → 不算丢
    ]
    rows = rp.aggregate_scene_findings(m)
    assert len(rows) == 1 and rows[0]["asset"] == "残匾"
    assert rows[0]["present"] is False and rows[0]["expected"] is True
    assert rows[0]["severity"] == "warn" and "破殿" in rows[0]["shot"]


def test_aggregate_core_scene_blocks():
    m = _manifest()
    m["findings"] = [{"shot": "s1.png", "asset": "残匾", "present": False},
                     {"shot": "s2.png", "asset": "残匾", "present": False}]
    rows = rp.aggregate_scene_findings(m, core_scenes=["破殿"])
    assert rows and rows[0]["severity"] == "block"


def test_aggregate_no_backend_no_findings():
    # findings 空（后端没跑）→ 无缺席证据 → 不凭空 block。
    assert rp.aggregate_scene_findings(_manifest()) == []


def test_aggregate_all_present_no_findings():
    m = _manifest()
    m["findings"] = [{"shot": "s1.png", "asset": "残匾", "present": True}]  # present:True 不计入缺席
    assert rp.aggregate_scene_findings(m) == []


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
