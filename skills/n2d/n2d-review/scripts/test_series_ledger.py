#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""series_ledger 单测。 cd skills/n2d/n2d-review/scripts && python3 -m pytest test_series_ledger.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import series_ledger as sl  # noqa: E402


def _ledger(block=0, high=0, medium=0, status=None):
    counts = {"block": block, "high": high, "medium": medium}
    if status is None:
        status = "blocked" if (block or high) else "pass"
    return {"counts": counts, "delivery_surface": {"status": status}}


_CLEAN_IDENTITY = {"available": True, "characters": {}}  # 跨集脸漂报告存在且无 block 角色


# ── 纯聚合 ───────────────────────────────────────────────────────────────────
def test_all_pass_series_is_deliverable():
    # 多集季须有跨集脸漂报告才可交付（缺=头号风险未核验，见 test_missing_identity_report_*）。
    ledger = sl.build_series_ledger(episode_ledgers=[
        ("第1集", _ledger()),
        ("第2集", _ledger(medium=2)),
    ], identity_drift=_CLEAN_IDENTITY)
    assert ledger["delivery_surface"]["status"] == "pass"
    assert ledger["counts"] == {"block": 0, "high": 0, "medium": 2}
    assert ledger["ledgers_present"] == 2


def test_missing_identity_report_blocks_multi_episode_season():
    # 修：多集季缺 identity_drift_report → 跨集脸漂未核验 = 阻断（对称于缺集 ledger），不再静默放行。
    ledger = sl.build_series_ledger(episode_ledgers=[("第1集", _ledger()), ("第2集", _ledger())])
    assert ledger["delivery_surface"]["status"] == "blocked"
    assert ledger["delivery_surface"]["blocking"]["identity_report_missing"] is True


def test_missing_identity_report_does_not_block_single_episode():
    # 单集无跨集语义 → 缺报告不挡（避免早期作品误挡）。
    ledger = sl.build_series_ledger(episode_ledgers=[("第1集", _ledger())])
    assert ledger["delivery_surface"]["status"] == "pass"


def test_child_pass_cannot_mask_real_high_count():
    # 修：子 ledger 报 status=pass 却 counts.high>0 → 季级仍 blocked（high 独立阻断不被子 pass 覆盖）。
    ledger = sl.build_series_ledger(episode_ledgers=[
        ("第1集", _ledger(high=2, status="pass")),
    ], identity_drift=_CLEAN_IDENTITY)
    assert ledger["delivery_surface"]["status"] == "blocked"
    assert "第1集" in ledger["delivery_surface"]["blocking"]["episodes_blocked"]


def test_episode_block_blocks_series():
    ledger = sl.build_series_ledger(episode_ledgers=[
        ("第1集", _ledger()),
        ("第2集", _ledger(block=1)),
    ])
    s = ledger["delivery_surface"]
    assert s["status"] == "blocked"
    assert s["blocking"]["episodes_blocked"] == ["第2集"]
    assert ledger["counts"]["block"] == 1


def test_high_only_also_blocks():
    ledger = sl.build_series_ledger(episode_ledgers=[("第1集", _ledger(high=1))])
    assert ledger["delivery_surface"]["status"] == "blocked"


def test_missing_episode_ledger_blocks_signoff():
    ledger = sl.build_series_ledger(episode_ledgers=[
        ("第1集", _ledger()),
        ("第2集", None),  # 脚本已出但未签收
    ])
    s = ledger["delivery_surface"]
    assert s["status"] == "blocked"
    assert s["blocking"]["episodes_missing_ledger"] == ["第2集"]
    ep2 = next(e for e in ledger["episodes"] if e["episode"] == "第2集")
    assert ep2["present"] is False and ep2["status"] == "missing"


def test_identity_block_character_blocks_series():
    drift = {
        "available": True,
        "characters": {
            "沈念": {"total_block": 2, "total_warn": 0, "first_bad_episode": "第12集"},
            "路人": {"total_block": 0, "total_warn": 3, "first_bad_episode": "第4集"},
        },
    }
    ledger = sl.build_series_ledger(
        episode_ledgers=[("第1集", _ledger())],
        identity_drift=drift,
    )
    s = ledger["delivery_surface"]
    assert s["status"] == "blocked"
    chars = [c["character"] for c in s["blocking"]["identity_block_characters"]]
    assert chars == ["沈念"]
    assert s["blocking"]["identity_block_characters"][0]["first_bad_episode"] == "第12集"
    # warn 级角色只进观察、不阻断
    warns = [c["character"] for c in ledger["cross_episode"]["identity_drift"]["warn_characters"]]
    assert warns == ["路人"]


def test_weakest_episodes_ordering():
    ledger = sl.build_series_ledger(episode_ledgers=[
        ("第1集", _ledger()),
        ("第2集", _ledger(high=1)),
        ("第3集", None),
        ("第4集", _ledger(block=3)),
    ])
    weak = ledger["delivery_surface"]["weakest_episodes"]
    # 缺签收的排最前，再按 block/high 降序；pass 集不进列表
    assert weak[0] == "第3集"
    assert "第1集" not in weak
    assert set(weak) == {"第3集", "第4集", "第2集"}


def test_retention_is_observed_not_blocking():
    ledger = sl.build_series_ledger(
        episode_ledgers=[("第1集", _ledger())],
        retention={"status": "weak_tail"},
    )
    assert ledger["delivery_surface"]["status"] == "pass"  # 留存不阻断签收
    assert ledger["cross_episode"]["retention"]["status"] == "weak_tail"


# ── I/O round-trip ───────────────────────────────────────────────────────────
def test_run_writes_files_and_discovers(tmp_path):
    root = str(tmp_path)
    prod = os.path.join(root, "生产数据")
    os.makedirs(os.path.join(root, "脚本", "第1集"))
    os.makedirs(os.path.join(root, "脚本", "第2集"))
    os.makedirs(prod)
    with open(os.path.join(prod, "consistency_ledger_第1集.json"), "w", encoding="utf-8") as f:
        json.dump(_ledger(), f)
    # 第2集 故意不出 ledger → 应被发现为 missing 并阻断
    ledger = sl.run(root)
    assert os.path.isfile(os.path.join(prod, "series_ledger.json"))
    assert os.path.isfile(os.path.join(prod, "series_ledger.md"))
    assert [e["episode"] for e in ledger["episodes"]] == ["第1集", "第2集"]
    assert ledger["delivery_surface"]["status"] == "blocked"
    assert ledger["delivery_surface"]["blocking"]["episodes_missing_ledger"] == ["第2集"]


def test_main_strict_exit_code(tmp_path):
    root = str(tmp_path)
    prod = os.path.join(root, "生产数据")
    os.makedirs(os.path.join(root, "脚本", "第1集"))
    os.makedirs(prod)
    with open(os.path.join(prod, "consistency_ledger_第1集.json"), "w", encoding="utf-8") as f:
        json.dump(_ledger(block=1), f)
    assert sl.main([root, "--strict"]) == 1
    assert sl.main([root]) == 0  # 非 strict 只读报告


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
