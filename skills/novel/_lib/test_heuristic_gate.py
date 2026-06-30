# -*- coding: utf-8 -*-
"""test_heuristic_gate — B10 降级守卫回归。

Run: cd skills/novel/_lib && python3 -m pytest test_heuristic_gate.py
"""
import heuristic_gate as hg


def test_classify_deterministic_vs_heuristic():
    assert hg.classify_confidence("timeline_event_disorder") == "deterministic"
    assert hg.classify_confidence("foreshadowing_overdue") == "deterministic"
    assert hg.classify_confidence("deceased_reactivation") == "heuristic"
    assert hg.classify_confidence("某个还没造出来的检测") == "heuristic"  # 默认保守=heuristic


def test_annotate_does_not_override_explicit():
    alerts = [{"type": "deceased_reactivation", "severity": "阻断级", "confidence": "deterministic"}]
    hg.annotate_confidence(alerts)
    assert alerts[0]["confidence"] == "deterministic"  # detector 自裁不被覆盖


def test_heuristic_blocking_downgraded():
    alerts = [{"type": "deceased_reactivation", "severity": "阻断级", "entity": "李慕白",
               "chapter": 3, "note": "复活"}]
    alerts, downgrades = hg.enforce(alerts)
    assert alerts[0]["severity"] == "建议级"
    assert alerts[0]["downgraded_from"] == "阻断级"
    assert "B10" in alerts[0]["note"]
    assert downgrades == [{"type": "deceased_reactivation", "entity": "李慕白",
                           "chapter": 3, "from": "阻断级", "to": "建议级"}]


def test_deterministic_blocking_preserved():
    alerts = [{"type": "timeline_event_disorder", "severity": "阻断级", "chapter": 9}]
    alerts, downgrades = hg.enforce(alerts)
    assert alerts[0]["severity"] == "阻断级"  # 确定性证据闸不被降级
    assert downgrades == []
    assert hg.count_blocking(alerts) == 1


def test_heuristic_advisory_untouched():
    alerts = [{"type": "location_jump", "severity": "建议级"}]
    alerts, downgrades = hg.enforce(alerts)
    assert alerts[0]["severity"] == "建议级"
    assert downgrades == []


def test_policy_is_idempotent():
    alerts = [{"type": "promise_broken", "severity": "阻断级", "note": "x"}]
    hg.enforce(alerts)
    first = dict(alerts[0])
    hg.apply_confidence_policy(alerts)  # 再来一次
    assert alerts[0]["severity"] == "建议级"
    assert alerts[0]["note"] == first["note"]  # note 不重复追加


def test_count_blocking_after_policy():
    alerts = [
        {"type": "deceased_reactivation", "severity": "阻断级"},   # → 降级
        {"type": "foreshadowing_overdue", "severity": "阻断级"},   # 确定性·保留
        {"type": "hook_stale", "severity": "建议级"},
    ]
    alerts, _ = hg.enforce(alerts)
    assert hg.count_blocking(alerts) == 1


def test_structured_fact_types_keep_blocking_after_enforce():
    # A1/A2 结构化原子事实闸：登记进 DETERMINISTIC_TYPES → enforce 后保留阻断级
    import heuristic_gate as H
    for t in ("deceased_ledger_reactivation", "world_fact_interval_conflict"):
        assert t in H.DETERMINISTIC_TYPES
        alerts = [{"type": t, "severity": "阻断级"}]   # 无显式 confidence → 按 type 归类
        H.enforce(alerts)
        assert alerts[0]["severity"] == "阻断级"        # 确定性·不降级
        assert H.count_blocking(alerts) == 1


def test_explicit_deterministic_confidence_survives_even_unregistered():
    import heuristic_gate as H
    alerts = [{"type": "some_new_structured_check", "severity": "阻断级", "confidence": "deterministic"}]
    H.enforce(alerts)
    assert alerts[0]["severity"] == "阻断级"            # 显式 deterministic 标签不被降级
