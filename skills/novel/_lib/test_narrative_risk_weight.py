# -*- coding: utf-8 -*-
"""cd skills/novel/_lib && python3 -m pytest test_narrative_risk_weight.py"""
import narrative_risk_weight as nrw


def test_chapter_position_and_midspan():
    assert nrw.chapter_position(1, 100) < 0.1
    assert nrw.is_midspan(nrw.chapter_position(50, 100))   # 中段
    assert not nrw.is_midspan(nrw.chapter_position(5, 100))  # 开头
    assert not nrw.is_midspan(nrw.chapter_position(98, 100))  # 结尾
    assert nrw.chapter_position(7, 0) == 0.0  # total<=0 安全


def test_lexical_entropy_bounds_and_ordering():
    assert nrw.lexical_entropy("") == 0.0
    assert nrw.lexical_entropy("啊") == 0.0
    low = nrw.lexical_entropy("啊啊啊啊啊啊啊啊啊啊")     # 重复→低
    high = nrw.lexical_entropy("青山隐隐水迢迢秋尽江南草未凋")  # 多样→高
    assert 0.0 <= low <= high <= 1.0
    assert high > low


def test_build_churn_map_counts_structured_deltas():
    ledger = {"chapter_deltas": {
        "第1章": {"character_changes": [{"name": "A"}]},
        "第50章": {"character_changes": [{"name": "A"}, {"name": "B"}, {"name": "C"}]},
    }}
    world = {"major_changes": [{"key": "国号", "value": "魏", "established_at": "第50章"}]}
    churn = nrw.build_churn_map(ledger, world)
    assert churn[1] == 1
    assert churn[50] == 4  # 3 character_changes + 1 world fact


def test_build_churn_map_handles_list_form_and_missing():
    assert nrw.build_churn_map(None) == {}
    ledger = {"chapter_deltas": [{"chapter": "第3章", "character_changes": [{"name": "X"}]}]}
    assert nrw.build_churn_map(ledger)[3] == 1


def test_prioritize_alerts_orders_midspan_and_blocking_first():
    total = 100
    churn = {50: 9, 90: 1, 5: 1}
    alerts = [
        {"type": "x", "chapter": 5, "severity": "advisory"},     # 开头·低
        {"type": "y", "chapter": 50, "severity": "advisory"},    # 中段+高churn
        {"type": "z", "chapter": 90, "severity": "阻断级"},       # 结尾但阻断级
    ]
    ordered = nrw.prioritize_alerts(alerts, total, churn_map=churn)
    # 阻断级永远排第一（即便结尾低优先）
    assert ordered[0]["chapter"] == 90 and ordered[0]["severity"] == "阻断级"
    # 中段+高churn 的 advisory 排在开头低优先 advisory 之前
    adv = [a for a in ordered if a["severity"] != "阻断级"]
    assert adv[0]["chapter"] == 50
    mid = next(a for a in alerts if a["chapter"] == 50)
    assert "midspan" in mid["priority_factors"] and "high_churn" in mid["priority_factors"]
    assert mid["priority"] > adv[1]["priority"]


def test_prioritize_never_touches_severity():
    alerts = [{"type": "x", "chapter": 50, "severity": "advisory"}]
    nrw.prioritize_alerts(alerts, 100, churn_map={50: 9})
    assert alerts[0]["severity"] == "advisory"  # 只加 priority，绝不升阻断


def test_percentile_all_equal_no_false_hotspots():
    # churn 全相等 → 不挑"异常高"章（避免均匀churn全标热点）
    churn = {i: 2 for i in range(1, 11)}
    thr = nrw._percentile_threshold(churn.values())
    assert thr == float("inf")


def test_risk_hotspots_returns_midspan_and_high_churn():
    hot = nrw.risk_hotspots(100, churn_map={50: 9, 51: 8, 5: 1})
    chapters = {r["chapter"] for r in hot}
    assert 50 in chapters and 51 in chapters
    # 每条都至少命中一个代理
    assert all(r["factors"] for r in hot)
    # 空/非法 total 安全
    assert nrw.risk_hotspots(0, churn_map={1: 9}) == []
