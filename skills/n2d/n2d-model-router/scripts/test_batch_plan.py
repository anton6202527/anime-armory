"""batch_plan 纯函数单测。
cd skills/n2d/n2d-model-router/scripts && python -m pytest test_batch_plan.py
"""
import batch_plan as bp


def _clip(cid, urgency, secs, backend="seedance"):
    return {"clip_id": cid, "urgency_tier": urgency, "duration_sec": secs, "backend": backend}


def test_only_batch_eligible_clips_included():
    clips = [_clip("C1", "batch_24h", 8), _clip("C2", "realtime", 8), _clip("C3", "batch_24h", 5)]
    plan = bp.build_batch_plan(clips)
    assert plan["summary"]["batch_eligible_clips"] == 2
    assert {r["clip_id"] for r in plan["clips"]} == {"C1", "C3"}
    assert plan["summary"]["batch_eligible_seconds"] == 13.0


def test_discount_default_50pct():
    plan = bp.build_batch_plan([_clip("C1", "batch_24h", 10)], rate_per_sec=1.0, unit="积分")
    s = plan["summary"]
    assert s["discount_factor"] == 0.5 and s["discount_pct"] == 50.0
    assert s["est_cost_realtime"] == 10.0 and s["est_cost_batch"] == 5.0 and s["est_savings"] == 5.0


def test_no_rate_reports_volume_not_money():
    plan = bp.build_batch_plan([_clip("C1", "batch_24h", 10)])  # 无 rate
    s = plan["summary"]
    assert s["batch_eligible_seconds"] == 10.0
    assert s["est_cost_realtime"] is None and s["est_savings"] is None  # 不臆造钱
    assert plan["clips"][0]["est_cost_batch"] is None


def test_custom_discount_factor():
    plan = bp.build_batch_plan([_clip("C1", "batch_24h", 10)], factor=0.3, rate_per_sec=2.0)
    assert plan["summary"]["est_cost_batch"] == 6.0  # 20 * 0.3
    assert plan["summary"]["discount_pct"] == 70.0


def test_apply_discount_no_rate_all_none():
    d = bp.apply_discount(None, 10, 0.5)
    assert d == {"realtime": None, "batch": None, "savings": None}


def test_empty_or_no_batch_clips():
    assert bp.build_batch_plan([])["summary"]["batch_eligible_clips"] == 0
    assert bp.build_batch_plan([_clip("C1", "realtime", 8)])["summary"]["batch_eligible_clips"] == 0
