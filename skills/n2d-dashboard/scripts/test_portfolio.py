"""portfolio 聚合纯函数单测。
cd skills/n2d-dashboard/scripts && python -m pytest test_portfolio.py
"""
import portfolio as pf


def _work(name, *, eps, fin_ep, fin_min, cost, attempts=0, one_pass=0, redraw=0,
          plays=0, net=None, first=None, last=None):
    return {"name": name, "finished_episodes": fin_ep, "finished_min": fin_min,
            "first_ts": first, "last_ts": last,
            "totals": {"episode_count": eps, "generation_attempts": attempts,
                       "one_pass_count": one_pass, "redraw_count": redraw,
                       "cost_totals": cost, "release_plays": plays,
                       "release_net_totals": net or {}}}


def test_cost_summed_per_unit_across_works():
    p = pf.aggregate_portfolio([
        _work("A", eps=2, fin_ep=2, fin_min=4.0, cost={"积分": 1200, "CNY": 5.0}),
        _work("B", eps=3, fin_ep=1, fin_min=2.0, cost={"积分": 800}),
    ])
    assert p["cost_totals"] == {"积分": 2000.0, "CNY": 5.0}
    assert p["total_finished_episodes"] == 3 and p["total_finished_min"] == 6.0


def test_cost_per_finished_min_portfolio():
    p = pf.aggregate_portfolio([_work("A", eps=1, fin_ep=1, fin_min=4.0, cost={"积分": 2000})])
    assert p["cost_per_finished_min"]["积分"] == 500.0  # 2000/4


def test_weighted_one_pass_rate_not_simple_average():
    # A: 1/10, B: 9/10 → 加权 10/20=0.5（简单平均会是 0.5 也巧合，故用不等样本）
    p = pf.aggregate_portfolio([
        _work("A", eps=1, fin_ep=1, fin_min=1, cost={}, attempts=100, one_pass=10),
        _work("B", eps=1, fin_ep=1, fin_min=1, cost={}, attempts=10, one_pass=9),
    ])
    assert p["one_pass_rate"] == round(19 / 110, 4)  # 加权（19/110），非 (0.1+0.9)/2=0.5


def test_throughput_from_calendar_span():
    p = pf.aggregate_portfolio([
        _work("A", eps=4, fin_ep=4, fin_min=8, cost={}, first="2026-06-01T00:00:00", last="2026-06-05T00:00:00"),
    ])
    th = p["throughput"]
    assert th["span_days"] == 4.0
    assert th["episodes_per_day"] == 1.0          # 4 集 / 4 天
    assert th["finished_min_per_day"] == 2.0      # 8 分钟 / 4 天


def test_throughput_span_floor_avoids_astronomical_rate():
    # 同一时刻出 3 集 → 跨度地板=1小时，不算出天文吞吐
    p = pf.aggregate_portfolio([
        _work("A", eps=3, fin_ep=3, fin_min=6, cost={}, first="2026-06-01T10:00:00", last="2026-06-01T10:00:00"),
    ])
    assert p["throughput"]["span_days"] == round(1 / 24, 2)


def test_recoup_ratio_per_unit():
    p = pf.aggregate_portfolio([
        _work("A", eps=1, fin_ep=1, fin_min=1, cost={"CNY": 100}, net={"CNY": 250}),
    ])
    assert p["recoup_ratio"]["CNY"] == 2.5


def test_empty_portfolio():
    p = pf.aggregate_portfolio([])
    assert p["work_count"] == 0 and p["cost_totals"] == {} and p["throughput"]["episodes_per_day"] is None


def test_span_days_missing_endpoint():
    assert pf.span_days(None, "2026-06-01T00:00:00") is None
    assert pf.span_days("2026-06-01T00:00:00", "2026-06-02T00:00:00") == 1.0
