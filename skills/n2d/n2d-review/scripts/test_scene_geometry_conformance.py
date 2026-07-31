#!/usr/bin/env python3
"""cd skills/n2d/n2d-review/scripts && python3 -m pytest test_scene_geometry_conformance.py

场景几何(floor_plan/门窗)一致性——纯逻辑（开口解析 + 场景级 conformance 聚合）。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_geometry_conformance as sg


def test_parse_openings_real_prose():
    ops = sg.parse_openings("主要入口在画左下；破顶开口在上方。", "A6殿门，D4殿心，E1破顶。")
    by = {(o["label"], o["h"]) for o in ops}
    assert ("门", "left") in by          # 入口在画左
    assert ("开口", None) in by          # 破顶开口在上方（h 无、v=top）
    # 去冗余：floor_plan「殿门」的无侧位 门 被带侧位的 门 吸收
    assert ("门", None) not in by


def test_parse_openings_empty():
    assert sg.parse_openings("", "") == []
    assert sg.parse_openings("一片空地，没有任何结构。", "") == []


def test_conformance_orientation_drift_core_blocks():
    ops = [{"label": "门", "phrase": "door", "h": "left", "v": None}]
    rows = sg.conformance_findings("殿", ops, {"门": ["right", "right"]}, is_core=True)
    assert len(rows) == 1 and rows[0]["kind"] == "朝向漂" and rows[0]["verdict"] == "block"


def test_conformance_correct_side_no_finding():
    ops = [{"label": "门", "phrase": "door", "h": "left", "v": None}]
    assert sg.conformance_findings("殿", ops, {"门": ["left"]}) == []


def test_conformance_missing_structure():
    ops = [{"label": "门", "phrase": "door", "h": "left", "v": None}]
    rows = sg.conformance_findings("殿", ops, {"窗": ["left"]})  # 门 never detected
    assert len(rows) == 1 and rows[0]["kind"] == "缺席"


def test_conformance_no_backend_no_findings():
    ops = [{"label": "门", "phrase": "door", "h": "left", "v": None}]
    assert sg.conformance_findings("殿", ops, {}) == []   # detected 空 → 不凭空 block


def test_conformance_unknown_side_not_penalized():
    # 后端无侧位（unknown）→ 不判朝向漂（侧位不可知就别瞎拦）
    ops = [{"label": "门", "phrase": "door", "h": "left", "v": None}]
    assert sg.conformance_findings("殿", ops, {"门": ["unknown"]}) == []


def test_aggregate_reads_detected_and_core():
    manifest = {"scene_openings": {"殿": [{"label": "门", "phrase": "door", "h": "left", "v": None}]},
                "detected": {"殿": {"门": ["right"]}}}
    rows = sg.aggregate(manifest, core_scenes=["殿"])
    assert rows and rows[0]["verdict"] == "block"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
